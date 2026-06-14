# Plan 012 — WCAG 2.1 AA Accessibility Fixes

**Slug:** accessibility-fixes
**Commit:** 1e84782
**Priority:** P2
**Effort:** S
**Risk:** LOW — CSS additions and HTML attribute additions; no logic changes
**Category:** accessibility
**Status:** TODO

---

## Problem

Three confirmed WCAG 2.1 AA violations in the Dash app:

### A — Aggressive hover animation without `prefers-reduced-motion` guard (`app/assets/custom.css:47–52`)

```css
.mantine-Paper-root:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 0 20px 32px -8px rgba(0, 0, 0, 0.12), 0 12px 12px -8px rgba(0, 0, 0, 0.06) !important;
    border-color: var(--mission-cyan) !important;
    background: #FFFFFF !important;
}
```

Every `dmc.Paper` in the app (KPI cards, visualization containers, the sidebar worker panel) jumps 8px upward and scales 2% on hover. This violates WCAG 2.1 SC 2.3.3 (Animation from Interactions) for users who have set `prefers-reduced-motion: reduce` in their OS. The Streamlit theme (`app/ui/theme.py:135–137`) correctly guards its animations — the Dash CSS does not.

### B — No skip link in Dash layout (`app/dash_app.py`)

`app/ui/theme.py` defines `render_skip_link()` for the Streamlit app. The Dash app has no skip link at all. Users navigating by keyboard must tab through 13 nav links and the header command bar before reaching page content. This violates WCAG 2.1 SC 2.4.1 (Bypass Blocks).

### C — Theme toggle ActionIcon has no accessible label (`app/dash_layouts.py:162`)

```python
dmc.ActionIcon(DashIconify(icon="mdi:theme-light-dark"), variant="outline", id="btn-toggle-theme", color="dark", size="sm"),
```

An icon-only button with no `aria-label` is invisible to screen readers. This violates WCAG 2.1 SC 4.1.2 (Name, Role, Value).

---

## Implementation

### Step 1 — Add `prefers-reduced-motion` guard to `app/assets/custom.css`

Append at the end of the file:

```css
/* WCAG 2.1 SC 2.3.3 — Disable motion for users who request it */
@media (prefers-reduced-motion: reduce) {
    .mantine-Paper-root:hover {
        transform: none;
    }
    * {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
    }
}
```

### Step 2 — Add skip link to Dash layout (`app/dash_app.py`)

Add a skip-to-content link as the first child of the MantineProvider in `app/dash_app.py`. It should appear before `dcc.Location`.

**Before (inside `app.layout = dmc.MantineProvider(...)`):**
```python
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="store-data-loaded", ...),
```

**After:**
```python
    children=[
        html.A(
            "Skip to main content",
            href="#page-content",
            style={
                "position": "absolute",
                "left": "-9999px",
                "zIndex": "9999",
                "padding": "8px 16px",
                "background": "#003087",
                "color": "#fff",
                "textDecoration": "none",
                "borderRadius": "4px",
                ":focus": {"left": "12px", "top": "12px"},
            },
            **{"aria-label": "Skip to main content"},
        ),
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="store-data-loaded", ...),
```

Note: Dash's inline style dict does not support `:focus` pseudo-selector. Add CSS in `custom.css` for the skip link focus state instead:

In `app/assets/custom.css`, add after the `prefers-reduced-motion` block:

```css
/* Skip link (WCAG 2.4.1) */
a[href="#page-content"] {
    position: absolute;
    left: -9999px;
    z-index: 9999;
    padding: 8px 16px;
    background: #003087;
    color: #fff !important;
    text-decoration: none;
    border-radius: 4px;
    font-weight: 700;
}
a[href="#page-content"]:focus {
    left: 12px;
    top: 12px;
}
```

And simplify the `html.A` in `dash_app.py` (remove the style dict, CSS handles it):

```python
        html.A(
            "Skip to main content",
            href="#page-content",
            **{"aria-label": "Skip to main content"},
        ),
```

`id="page-content"` already exists on `dmc.AppShellMain` at `dash_app.py:135` — `href="#page-content"` will correctly jump to it.

### Step 3 — Add `aria-label` to theme toggle ActionIcon (`app/dash_layouts.py`)

**Before (`app/dash_layouts.py:162`):**
```python
dmc.ActionIcon(DashIconify(icon="mdi:theme-light-dark"), variant="outline", id="btn-toggle-theme", color="dark", size="sm"),
```

**After:**
```python
dmc.ActionIcon(DashIconify(icon="mdi:theme-light-dark"), variant="outline", id="btn-toggle-theme", color="dark", size="sm", **{"aria-label": "Toggle light/dark theme"}),
```

---

## Files in scope

- `app/assets/custom.css` — add `prefers-reduced-motion` guard + skip link CSS
- `app/dash_app.py` — add `html.A` skip link as first child of MantineProvider
- `app/dash_layouts.py` — add `aria-label` to ActionIcon

## Files explicitly out of scope

- `app/ui/theme.py` — Streamlit-only; has its own skip link; do not touch
- Any analytics or callback files

---

## Verification

```bash
# CSS contains prefers-reduced-motion
grep -n "prefers-reduced-motion" app/assets/custom.css
# Expected: at least 2 lines (the @media query)

# Skip link present in layout
grep -n "Skip to main content" app/dash_app.py
# Expected: 1 match

# aria-label on theme toggle
grep -n "btn-toggle-theme" app/dash_layouts.py
# Expected: line should contain aria-label

# Syntax checks
python -c "import ast; ast.parse(open('app/dash_app.py').read()); print('OK')"
python -c "import ast; ast.parse(open('app/dash_layouts.py').read()); print('OK')"

# Run tests
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

---

## Done criteria

- [ ] `grep -c "prefers-reduced-motion" app/assets/custom.css` returns ≥ 2
- [ ] `grep -c "Skip to main content" app/dash_app.py` returns 1
- [ ] `grep -c "aria-label.*Toggle" app/dash_layouts.py` returns 1
  (or `grep -c "aria-label" app/dash_layouts.py` returns ≥ 1 on the ActionIcon line)
- [ ] `python -m pytest tests/ -q --tb=short` passes at same pre-existing failure count
