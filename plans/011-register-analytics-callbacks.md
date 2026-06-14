# Plan 011 — Register Analytics and Visualization Callbacks

**Slug:** register-analytics-callbacks
**Commit:** 1e84782
**Priority:** P1
**Effort:** M
**Risk:** LOW — adds imports and delegation calls; all callback logic already exists and is self-contained
**Category:** UX / correctness
**Status:** TODO
**Depends on:** Plan 008 (startup crash fix — `register_analytics_callbacks` stub must be fixed first)

---

## Problem

Four callback modules containing real analytics logic exist but are never imported or called, leaving all analytical visualizations permanently empty:

| Module | Contains | Registered? |
|--------|----------|-------------|
| `app/callbacks/visualization_callbacks.py` | Phase B–F analytics (Moran's I, distributions, anomalies, decomposition, bootstrap CI) via `@callback` decorators + `register_visualization_callbacks()` | **NO** — module never imported |
| `app/callbacks/analytics_integration.py` | Phase C–F chart callbacks for Analytics tab via module-level `@callback` decorators | **NO** — module never imported |
| `app/callbacks/hidden_analysis_methods.py` | Moran's I callback + register function `register_morans_i_callbacks(app, dm_instance)` | **NO** — module never imported |
| `app/callbacks/gis.py` | GIS dashboard callbacks | **NO** — module never imported |

All 26 `visualization_asset()` charts (in `dash_layouts.py`) produce `dcc.Graph` with pattern IDs like `{"type": "visualization-graph", "index": chart_id}`. No callback populates them because the wiring module was never imported.

The fix is to expand `register_analytics_callbacks()` (currently a stub `pass`) to import and delegate to these modules.

---

## Implementation

### Step 1 — Expand `register_analytics_callbacks` in `app/callbacks/analytics.py`

The function signature was fixed in Plan 008 to `def register_analytics_callbacks(app, dm=None)`. Now give it a body.

**Before (`app/callbacks/analytics.py:538–540`):**
```python
def register_analytics_callbacks(app, dm=None):
    """Register analytics-related callbacks with the Dash app."""
    pass
```

**After:**
```python
def register_analytics_callbacks(app, dm=None):
    """Register analytics-related callbacks with the Dash app."""
    # Import triggers @callback decorator registration for module-level callbacks
    import app.callbacks.analytics_integration  # noqa: F401
    import app.callbacks.visualization_callbacks  # noqa: F401

    # Call explicit registration functions that need the app or dm instance
    from app.callbacks.visualization_callbacks import register_visualization_callbacks
    register_visualization_callbacks()

    if dm is not None:
        try:
            from app.callbacks.hidden_analysis_methods import register_morans_i_callbacks
            register_morans_i_callbacks(app, dm)
        except Exception as e:
            logger.warning(f"Moran's I callbacks skipped (dm unavailable): {e}")

    logger.info("Analytics callbacks registered")
```

Important: The `logger` variable is already available at module scope in `analytics.py` (it is defined earlier in the file via `import logging; logger = logging.getLogger(__name__)`). Verify this before writing — if not present, add `import logging; logger = logging.getLogger(__name__)` near the top of the file.

### Step 2 — Import GIS callbacks (optional, wrap in try/except)

GIS callbacks (`app/callbacks/gis.py`) require geospatial dependencies that may not be installed. Import with a guard inside `register_analytics_callbacks`:

```python
    try:
        import app.callbacks.gis  # noqa: F401
    except ImportError as e:
        logger.warning(f"GIS callbacks skipped (missing dependency): {e}")
```

Add this after the `register_visualization_callbacks()` call in Step 1.

---

## Files in scope

- `app/callbacks/analytics.py` — expand `register_analytics_callbacks` body (lines 538–540)

## Files explicitly out of scope

- `app/callbacks/analytics_integration.py` — do not modify; it self-registers via `@callback`
- `app/callbacks/visualization_callbacks.py` — do not modify; `register_visualization_callbacks()` already exists
- `app/callbacks/hidden_analysis_methods.py` — do not modify; only call its register function
- `app/callbacks/gis.py` — do not modify
- `app/dash_app.py` — already calls `register_analytics_callbacks(app, dm)` correctly after Plan 008

---

## Verification

```bash
# Confirm logger exists in analytics.py before the function
grep -n "^logger\|^import logging" app/callbacks/analytics.py | head -5

# Syntax check
python -c "import ast; ast.parse(open('app/callbacks/analytics.py').read()); print('OK')"

# Confirm imports are present in the function body
grep -n "analytics_integration\|visualization_callbacks\|register_visualization\|register_morans" app/callbacks/analytics.py

# Run tests
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

---

## Done criteria

- [ ] `grep -c "analytics_integration" app/callbacks/analytics.py` returns ≥ 1
- [ ] `grep -c "visualization_callbacks" app/callbacks/analytics.py` returns ≥ 1
- [ ] `grep -c "register_visualization_callbacks" app/callbacks/analytics.py` returns ≥ 1
- [ ] `python -c "import ast; ast.parse(open('app/callbacks/analytics.py').read()); print('OK')"` exits 0
- [ ] `python -m pytest tests/ -q --tb=short` passes at same pre-existing failure count

---

## Escape hatches

- If importing `analytics_integration` raises a `DuplicateCallbackOutput` error, it means the callbacks are already registered elsewhere. In that case, wrap the import in `try/except` and log a warning rather than crashing.
- If `hidden_analysis_methods.py` fails to import (missing `pysal` or similar), the `try/except` guard in Step 1 handles it — do not remove the guard.
- If the `logger` variable does not exist in `analytics.py` at module scope, add `import logging; logger = logging.getLogger(__name__)` at the top of the file (before the class definitions).
