# Plan 010 — Activate Dynamic KPI Cards

**Slug:** kpi-cards-activation
**Commit:** 1e84782
**Priority:** P1
**Effort:** M
**Risk:** LOW — replaces hardcoded strings with an existing, functional component; no data pipeline changes
**Category:** UX / correctness
**Status:** TODO
**Depends on:** Plan 008 (startup crashes), Plan 009 (filter system — KPI cards react to filter changes)

---

## Problem

The dashboard landing page (`layout_dashboard()` in `app/dash_layouts.py:243–265`) shows four hardcoded KPI cards with static, fabricated values:

```python
create_kpi_card("ACTIVE DATASETS", "26", color="blue"),
create_kpi_card("SODA HANDSHAKE", "AUTHENTICATED", color="green"),
create_kpi_card("TOTAL ROWSET", "1,242,102", delta="+4.2%"),
create_kpi_card("SODA VERSION", "3.0", color="indigo"),
```

A complete, dynamic KPI card system already exists at `app/components/kpi_cards.py`:
- `render_kpi_dashboard()` — renders 18 KPI cards across 4 categories (Inspection Performance, Quality Metrics, Ramp Accessibility, Spatial Patterns) with loading states
- `register_kpi_callbacks()` — wires `Input("store-global-filters", "data")` → `fetch_kpi_data()` → updates all 18 cards dynamically

Neither is called anywhere in the app. The hardcoded cards are also jargon-heavy ("SODA HANDSHAKE", "SODA VERSION") and not useful to analysts.

---

## Implementation

### Step 1 — Import dynamic KPI components in `dash_layouts.py`

Add to the imports at the top of `app/dash_layouts.py`:

```python
from app.components.kpi_cards import render_kpi_dashboard
```

### Step 2 — Replace hardcoded KPI grid in `layout_dashboard()`

**Before (`app/dash_layouts.py` inside `layout_dashboard()`):**
```python
            dmc.SimpleGrid(
                cols=4, spacing="lg",
                children=[
                    create_kpi_card("ACTIVE DATASETS", "26", color="blue"),
                    create_kpi_card("SODA HANDSHAKE", "AUTHENTICATED", color="green"),
                    create_kpi_card("TOTAL ROWSET", "1,242,102", delta="+4.2%"),
                    create_kpi_card("SODA VERSION", "3.0", color="indigo"),
                ]
            ),
```

**After:**
```python
            render_kpi_dashboard(),
```

The `render_kpi_dashboard()` function already produces a `html.Div` containing a `dmc.Stack` of 4 KPI category sections with 18 individual cards and a `dcc.Loading` wrapper. Do not pass any arguments.

### Step 3 — Register KPI callbacks in `dash_app.py`

Add import in `app/dash_app.py` (near the other component imports):
```python
from app.components.kpi_cards import register_kpi_callbacks
```

Add the call after the existing `register_*` lines (after `register_copilot_callbacks(app)`):
```python
register_kpi_callbacks()
```

Note: `register_kpi_callbacks()` uses `@callback` (module-level Dash decorator), not `@app.callback`, so it takes no `app` argument.

---

## Files in scope

- `app/dash_layouts.py` — add import, replace hardcoded grid with `render_kpi_dashboard()`
- `app/dash_app.py` — add import + `register_kpi_callbacks()` call

## Files explicitly out of scope

- `app/components/kpi_cards.py` — do not modify; it is correct as-is
- `app/services/motherduck_service.py` — if KPI fetch fails at runtime, it degrades gracefully (returns empty, cards show `—`) without a code change

---

## Verification

```bash
# Confirm import added
grep -n "render_kpi_dashboard\|register_kpi_callbacks" app/dash_layouts.py app/dash_app.py

# Confirm hardcoded cards are gone
grep -n "SODA HANDSHAKE\|SODA VERSION\|TOTAL ROWSET" app/dash_layouts.py
# Expected: no matches

# Confirm hardcoded create_kpi_card calls are gone from dashboard
grep -n "create_kpi_card.*26\|create_kpi_card.*AUTHENTICATED" app/dash_layouts.py
# Expected: no matches

# Syntax check
python -c "import ast; ast.parse(open('app/dash_layouts.py').read()); print('OK')"
python -c "import ast; ast.parse(open('app/dash_app.py').read()); print('OK')"

# Run tests
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

---

## Done criteria

- [ ] `grep -c "SODA HANDSHAKE" app/dash_layouts.py` returns 0
- [ ] `grep -c "render_kpi_dashboard" app/dash_layouts.py` returns 2 (import + call)
- [ ] `grep -c "register_kpi_callbacks" app/dash_app.py` returns 2 (import + call)
- [ ] `python -m pytest tests/ -q --tb=short` passes at same pre-existing failure count

---

## Escape hatches

- `create_kpi_card` helper is used elsewhere in `dash_layouts.py` (other views) — do NOT remove the function definition, only remove the 4 specific calls in `layout_dashboard()`.
- If `render_kpi_dashboard()` raises an import error, verify `app/components/__init__.py` exports it (it does at line 10); the issue is likely a circular import — trace and fix by moving the import inside the function body temporarily.
