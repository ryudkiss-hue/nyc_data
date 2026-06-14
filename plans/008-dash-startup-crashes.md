# Plan 008 — Fix Dash Startup Crashes

**Slug:** dash-startup-crashes
**Commit:** 1e84782
**Priority:** P0
**Effort:** S
**Risk:** LOW — surgical removals and one signature fix; no logic changes
**Category:** correctness/bugs
**Status:** TODO

---

## Problem

The Dash app crashes on startup with two separate errors before any page loads:

### Bug A — TypeError: too many arguments (`dash_app.py:182`)

`dash_app.py:182` calls `register_analytics_callbacks(app, dm)` with two positional arguments. The function signature at `app/callbacks/analytics.py:538` is:

```python
def register_analytics_callbacks(app):
    """Register analytics-related callbacks with the Dash app."""
    pass
```

Python raises `TypeError: register_analytics_callbacks() takes 1 positional argument but 2 were given` when the module loads. The app never starts.

### Bug B — Duplicate `Output("page-content", "children")` callback

`dash_app.py:172–177` registers a module-level `@app.callback` for `Output("page-content", "children")`:

```python
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    return render_page_content(pathname)
```

`app/callbacks/navigation.py:31–49` registers an *identical* output inside `register_navigation_callbacks(app)`:

```python
def register_navigation_callbacks(app):
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def render_page_content(pathname):
        if pathname == "/": return layout_dashboard()
        ...
```

`register_navigation_callbacks(app)` is called at `dash_app.py:180`. The module-level decorator in `dash_app.py` runs at import time; then when `register_navigation_callbacks` is called, Dash raises `DuplicateCallbackOutput` and refuses to start.

---

## Implementation

### Step 1 — Fix analytics callback signature (`app/callbacks/analytics.py`)

Change line 538 to accept the optional `dm` parameter (keep body as `pass` — a separate plan wires real callbacks):

**Before (`app/callbacks/analytics.py:538`):**
```python
def register_analytics_callbacks(app):
    """Register analytics-related callbacks with the Dash app."""
    pass
```

**After:**
```python
def register_analytics_callbacks(app, dm=None):
    """Register analytics-related callbacks with the Dash app."""
    pass
```

### Step 2 — Remove duplicate routing callback (`app/dash_app.py`)

Delete the module-level `@app.callback` block at lines 172–177. The authoritative routing lives in `app/callbacks/navigation.py` (registered via `register_navigation_callbacks(app)` at `dash_app.py:180`).

**Before (`app/dash_app.py:142–177`, showing full surrounding context):**
```python
# --- ROUTING ENGINE ---
def render_page_content(pathname):
    if pathname == "/":
        return layout_dashboard()
    elif pathname == "/const":
        return layout_construction()
    elif pathname == "/labor":
        return layout_labor()
    elif pathname == "/reports":
        return layout_reports()
    elif pathname == "/stats":
        return layout_stats()
    elif pathname == "/geo":
        return layout_gis()
    elif pathname == "/eng":
        return layout_engineering()
    elif pathname == "/sql":
        return layout_sql_tools()
    elif pathname == "/nlp":
        return layout_nlp()
    elif pathname == "/settings":
        return layout_settings()
    elif pathname == "/tutorials":
        return layout_tutorials()
    elif pathname == "/toolbox":
        return layout_toolbox()
    elif pathname == "/copilot":
        return layout_copilot()
    return dmc.Center(dmc.Text("404: Mission target not found.", size="xl", fw=700, c="red"))

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    return render_page_content(pathname)
```

**After — keep the helper function, remove the duplicate callback:**
```python
# --- ROUTING ENGINE ---
def render_page_content(pathname):
    if pathname == "/":
        return layout_dashboard()
    elif pathname == "/const":
        return layout_construction()
    elif pathname == "/labor":
        return layout_labor()
    elif pathname == "/reports":
        return layout_reports()
    elif pathname == "/stats":
        return layout_stats()
    elif pathname == "/geo":
        return layout_gis()
    elif pathname == "/eng":
        return layout_engineering()
    elif pathname == "/sql":
        return layout_sql_tools()
    elif pathname == "/nlp":
        return layout_nlp()
    elif pathname == "/settings":
        return layout_settings()
    elif pathname == "/tutorials":
        return layout_tutorials()
    elif pathname == "/toolbox":
        return layout_toolbox()
    elif pathname == "/copilot":
        return layout_copilot()
    return dmc.Center(dmc.Text("404: Mission target not found.", size="xl", fw=700, c="red"))
```

(The `@app.callback ... def display_page` block is deleted entirely. `navigation.py` handles the routing callback.)

---

## Files in scope

- `app/callbacks/analytics.py` — add `dm=None` parameter to `register_analytics_callbacks`
- `app/dash_app.py` — remove duplicate `@app.callback` block (lines 172–177)

## Files explicitly out of scope

- `app/callbacks/navigation.py` — do not touch; it is the correct routing implementation
- `app/dash_layouts.py` — no changes needed
- Any test files

---

## Verification

```bash
# Syntax check
python -c "import ast; ast.parse(open('app/callbacks/analytics.py').read()); print('analytics.py OK')"
python -c "import ast; ast.parse(open('app/dash_app.py').read()); print('dash_app.py OK')"

# Confirm no duplicate Output definition
grep -n "Output.*page-content" app/dash_app.py app/callbacks/navigation.py
# Expected: only navigation.py should have the callback decorator line

# Confirm signature accepts two args
python -c "
import sys; sys.path.insert(0, 'src'); sys.path.insert(0, 'app')
from app.callbacks.analytics import register_analytics_callbacks
register_analytics_callbacks(None, None)
print('Signature OK')
"

# Run tests
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

---

## Done criteria

- [ ] `python -c "from app.callbacks.analytics import register_analytics_callbacks; register_analytics_callbacks(None, None)"` exits with code 0
- [ ] `grep -c "def display_page" app/dash_app.py` returns 0
- [ ] `grep -n "Output.*page-content" app/dash_app.py` returns no lines with `@app.callback`
- [ ] `python -m pytest tests/ -q --tb=short` passes (or fails with same pre-existing count as commit `1e84782`)

---

## Escape hatches

- If removing `display_page` causes a test import failure, check whether any test file imports `display_page` directly from `dash_app` — if so, export it from `navigation.py` instead.
- If `navigation.py` routing is missing any path that `dash_app.py`'s `render_page_content` handled, add it to `navigation.py` before deleting from `dash_app.py`.
