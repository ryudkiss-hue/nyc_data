# Plan 009 — Wire the Filter System into the Dashboard

**Slug:** filter-system-integration
**Commit:** 1e84782
**Priority:** P1
**Effort:** M
**Risk:** LOW — adds calls to existing, tested functions; removes duplicate store definitions
**Category:** UX / correctness
**Status:** TODO
**Depends on:** Plan 008 (startup crashes must be fixed first)

---

## Problem

The filter system was built but never connected to the app. Three issues together make filters completely non-functional:

### Issue A — Duplicate `dcc.Store(id="store-global-filters")` definitions

Three files define this store with *different* schemas:

| File | Line | Schema | Storage |
|------|------|--------|---------|
| `app/dash_app.py` | 123 | `{"boro": "ALL", "cat": "ALL", "date_range": []}` | session |
| `app/components/filter_system.py` | 134 | `{"boroughs": [...], "date_start": None, "date_end": None, "metric_type": "all"}` | memory |
| `app/dash_layouts_analytics_integration.py` | 472 | `{}` | memory (default) |

If `render_filter_bar()` or `render_analytics_stores()` are ever called, Dash will raise `DuplicateCallbackOutput` for the store ID.

### Issue B — `render_filter_bar()` never called

`app/components/filter_system.py:49` defines `render_filter_bar()` which renders a complete borough/date/metric filter UI. It is exported in `app/components/__init__.py:13` but never called from any layout function.

### Issue C — `register_filter_callbacks()` never called

`app/components/filter_system.py:161` defines `register_filter_callbacks()` which wires the Apply/Reset buttons to write `store-global-filters`. It is exported but never called from `dash_app.py`. Callbacks using `Input("store-global-filters", "data")` therefore never fire.

---

## Implementation

### Step 1 — Remove duplicate store from `filter_system.py`

`render_filter_bar()` in `filter_system.py` internally renders a `dcc.Store(id="store-global-filters")`. The authoritative store is already in `dash_app.py:123`. Remove the store from `filter_system.py` and update the filter schema in `dash_app.py` to match what `register_filter_callbacks()` writes.

**In `app/components/filter_system.py`**, delete lines 132–142 (the `dcc.Store` block inside `render_filter_bar()`):

```python
            # Hidden store for global filters (broadcasted to all callbacks)
            dcc.Store(
                id="store-global-filters",
                data={
                    "boroughs": ["MN", "BK", "BX", "QN", "SI"],
                    "date_start": None,
                    "date_end": None,
                    "metric_type": "all",
                },
                storage_type="memory",
            ),

            # Loading indicator
```

After deletion the block should read directly:

```python
            # Loading indicator
```

### Step 2 — Update `dash_app.py` store schema to match filter callbacks

`register_filter_callbacks()` writes `{"boroughs": [...], "date_start": ..., "date_end": ..., "metric_type": ...}`. The store in `dash_app.py:123` uses a different schema (`boro`, `cat`, `date_range`). All downstream callbacks (in `export_callbacks.py`, `visualization_callbacks.py`, `analytics_integration.py`, `hidden_analysis_methods.py`, `kpi_cards.py`) read `filters.get("boroughs")`, `filters.get("date_start")` etc., matching the filter_system schema.

**In `app/dash_app.py`, change line 123:**

Before:
```python
        dcc.Store(id="store-global-filters", data={"boro": "ALL", "cat": "ALL", "date_range": []}, storage_type="session"),
```

After:
```python
        dcc.Store(
            id="store-global-filters",
            data={"boroughs": ["MN", "BK", "BX", "QN", "SI"], "date_start": None, "date_end": None, "metric_type": "all"},
            storage_type="session",
        ),
```

### Step 3 — Remove duplicate store from `dash_layouts_analytics_integration.py`

In `app/dash_layouts_analytics_integration.py:472`, the `render_analytics_stores()` function also defines a `dcc.Store(id="store-global-filters")`. Remove just that store (keep `analytics-refresh-trigger`):

**Before (`app/dash_layouts_analytics_integration.py:466–474`):**
```python
def render_analytics_stores() -> html.Div:
    """
    Render hidden stores for filter synchronization.
    Used by all analytics integration callbacks.
    """
    return html.Div([
        dcc.Store(id="store-global-filters", data={}),
        dcc.Store(id="analytics-refresh-trigger", data={}),
    ], style={"display": "none"})
```

**After:**
```python
def render_analytics_stores() -> html.Div:
    """
    Render hidden stores for analytics refresh signals.
    Note: store-global-filters is defined in dash_app.py layout root.
    """
    return html.Div([
        dcc.Store(id="analytics-refresh-trigger", data={}),
    ], style={"display": "none"})
```

### Step 4 — Add `render_filter_bar()` to `layout_dashboard()`

In `app/dash_layouts.py`, import and call `render_filter_bar()` at the top of the dashboard layout.

Add to the imports at the top of `app/dash_layouts.py` (after the existing imports):
```python
from app.components.filter_system import render_filter_bar
```

In `layout_dashboard()` (currently starts at line 243), insert `render_filter_bar()` as the first child before the KPI grid:

**Before (inside `layout_dashboard()`, after `fluid=True, pt="md",`):**
```python
        children=[
            dmc.Text("EXECUTIVE TELEMETRICS", fw=900, size="xl", mb="lg", c="black"),
            dmc.SimpleGrid(
```

**After:**
```python
        children=[
            dmc.Text("EXECUTIVE TELEMETRICS", fw=900, size="xl", mb="lg", c="black"),
            render_filter_bar(),
            dmc.SimpleGrid(
```

### Step 5 — Register filter callbacks in `dash_app.py`

Add import and call in `app/dash_app.py`.

Add to imports (near the other component imports):
```python
from app.components.filter_system import register_filter_callbacks
```

Add after the existing `register_*` calls (around line 184, after `register_copilot_callbacks(app)`):
```python
register_filter_callbacks()
```

---

## Files in scope

- `app/components/filter_system.py` — remove duplicate `dcc.Store` block from `render_filter_bar()`
- `app/dash_app.py` — update store schema, add import + `register_filter_callbacks()` call
- `app/dash_layouts.py` — add `render_filter_bar()` import + call in `layout_dashboard()`
- `app/dash_layouts_analytics_integration.py` — remove duplicate store from `render_analytics_stores()`

## Files explicitly out of scope

- `app/callbacks/export_callbacks.py` — reads `store-global-filters` already; schema change aligns it
- `app/callbacks/visualization_callbacks.py` — same
- Any test files

---

## Verification

```bash
# Confirm only one store-global-filters in layout root
python -c "
import ast, sys
src = open('app/dash_app.py').read()
tree = ast.parse(src)
print('dash_app.py parses OK')
"

# Confirm no duplicate store ID in filter_system.py
grep -n "store-global-filters" app/components/filter_system.py
# Expected: only lines referencing the Output/Input/State ids, NOT a dcc.Store definition

grep -n "store-global-filters" app/dash_layouts_analytics_integration.py
# Expected: no dcc.Store line remains (only comments if any)

# Confirm render_filter_bar is called
grep -n "render_filter_bar" app/dash_layouts.py
# Expected: both import and call present

# Confirm register_filter_callbacks is called
grep -n "register_filter_callbacks" app/dash_app.py
# Expected: import + call lines present

# Run tests
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

---

## Done criteria

- [ ] `grep -c "dcc.Store.*store-global-filters" app/components/filter_system.py` returns 0
- [ ] `grep -c "dcc.Store.*store-global-filters" app/dash_layouts_analytics_integration.py` returns 0
- [ ] `grep -c "render_filter_bar" app/dash_layouts.py` returns 2 (import + call)
- [ ] `grep -c "register_filter_callbacks" app/dash_app.py` returns 2 (import + call)
- [ ] `python -m pytest tests/ -q --tb=short` passes at same pre-existing failure count

---

## Escape hatches

- If `render_filter_bar()` raises an import error for a missing component, trace the import chain from `app/components/__init__.py` and fix the circular import if present.
- If `register_filter_callbacks()` raises a `DuplicateCallbackOutput` for `store-global-filters`, verify Step 3 was completed (the analytics integration store must be removed first).
- Do NOT modify `register_filter_callbacks()` internals — the callback logic is correct; only the wiring is missing.
