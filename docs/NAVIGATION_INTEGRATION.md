# 4-View Navigation System Integration Guide

**Task 10 Deliverable:** Multi-view sidebar navigation for role-based dashboard layout.

This document explains how the main navigation component integrates with the Dash routing system and how to implement Task 11 (routing) and Task 12 (layout reorganization).

---

## Architecture Overview

```
┌─ app/dash_app.py (main app layout)
│  ├─ dcc.Location (manages pathname)
│  ├─ render_main_navigation() [Task 10]
│  │  └─ 4 nav buttons → links to /views/{view}
│  └─ dmc.AppShellMain (content area)
│     └─ page-content (updated by routing callback)
│
├─ app/callbacks/navigation.py (routing callbacks)
│  └─ @app.callback(Output("page-content", "children"), Input("url", "pathname"))
│     └─ Routes /views/{view} → render_layout_{view}()
│
├─ app/dash_layouts.py
│  ├─ render_layout_executive() [Task 12]
│  ├─ render_layout_operations() [Task 12]
│  ├─ render_layout_analyst() [Task 12]
│  └─ render_layout_data() [Task 12]
│
└─ app/components/main_navigation.py [Task 10] ✓ COMPLETE
   ├─ get_navigation_items() — 4 nav item definitions
   ├─ render_main_navigation() — sidebar component
   └─ register_navigation_callbacks() — active state styling
```

---

## Component: 4-View Navigation

**File:** `app/components/main_navigation.py`
**Status:** ✓ COMPLETE (Task 10)

### Navigation Items (4 Views)

```python
get_navigation_items()  # Returns:

[
    {
        "id": "nav-executive",
        "label": "Executive Summary",
        "view": "executive",
        "route": "/views/executive",
        "icon": "mdi:chart-line",
        "description": "Leadership overview - 7 headline Metrics",
        "color": "blue",
        "badge": None,
    },
    {
        "id": "nav-operations",
        "label": "Operations",
        "view": "operations",
        "route": "/views/operations",
        "icon": "mdi:factory",
        "description": "Daily ops monitoring - 15 Metrics",
        "color": "orange",
        "badge": None,
    },
    {
        "id": "nav-analyst",
        "label": "Analyst Tools",
        "view": "analyst",
        "route": "/views/analyst",
        "icon": "mdi:chart-box-multiple",
        "description": "Deep analysis - 8 dashboards + tools",
        "color": "cyan",
        "badge": "new",
    },
    {
        "id": "nav-data",
        "label": "Data",
        "view": "data",
        "route": "/views/data",
        "icon": "mdi:database-check",
        "description": "Quality & governance",
        "color": "grape",
        "badge": None,
    },
]
```

### Rendering

```python
from app.components.main_navigation import (
    render_main_navigation,
    render_navigation_store,
    get_navigation_css,
)

# In app/dash_app.py layout:
app.layout = dmc.MantineProvider(
    children=[
        dcc.Location(id="url", refresh=False),
        render_navigation_store(),  # Session storage for nav state
        html.Style(get_navigation_css()),  # Mobile + responsive CSS
        
        dmc.AppShell(
            navbar={"width": 300, "breakpoint": "sm"},
            children=[
                render_header(),
                dmc.AppShellNavbar(
                    children=[render_main_navigation()]  # Sidebar
                ),
                dmc.AppShellMain(id="page-content", children=[html.Div()]),
            ],
        ),
    ],
)
```

### Callbacks Included

1. **Active View Highlighting** — `update_nav_active_styles(pathname)`
   - Reads: `url.pathname`
   - Writes: `{nav-item}-container.style` (border + background color)
   - Effect: Highlights active nav item on page load and navigation

2. **Mobile Menu Toggle** — `toggle_mobile_nav_visibility(pathname)`
   - Shows/hides hamburger menu on responsive breakpoints
   - CSS handles actual display; callback ensures Dash-side sync

---

## Task 11: Update Dash App Routing

**Objective:** Connect navigation clicks to view layouts via URL routing.

### Step 1: Update `app/dash_app.py` Layout

Replace the current `dmc.AppShellNavbar` with the new navigation:

```python
# Before:
render_sidebar()  # Old flat navbar with 13 items

# After:
dmc.AppShellNavbar(
    children=[render_main_navigation()]  # New 4-view navigation
)
```

### Step 2: Update `app/callbacks/navigation.py`

Modify the routing callback to handle `/views/{view}` routes:

```python
def render_page_content(pathname):
    """Route /views/{view} to view-specific layouts."""
    
    if pathname.startswith("/views/"):
        view = pathname.split("/")[2]  # Extract 'executive', 'operations', etc.
        
        if view == "executive":
            return render_layout_executive()
        elif view == "operations":
            return render_layout_operations()
        elif view == "analyst":
            return render_layout_analyst()
        elif view == "data":
            return render_layout_data()
    
    # Backward compatibility: support old routes
    if pathname == "/":
        return render_layout_executive()  # Default to executive
    # ... rest of old routing ...
    
    return dmc.Center(dmc.Text("404: Not Found", c="red"))
```

### Step 3: Register Navigation Callbacks

In `app/callbacks/navigation.py`:

```python
from app.components.main_navigation import register_navigation_callbacks as register_main_nav

def register_navigation_callbacks(app):
    """Register all navigation callbacks."""
    
    # Main 4-view navigation styling
    register_main_nav(app)
    
    # Routing callback (from current navigation.py)
    @app.callback(Output("page-content", "children"), Input("url", "pathname"))
    def render_page_content(pathname):
        # ... routing logic ...
```

---

## Task 12: Reorganize Layouts into Role-Specific Views

**Objective:** Create 4 view-specific layouts in `app/dash_layouts.py`.

### View 1: Executive Summary

**Audience:** Leadership, program managers
**Content:** 7 headline Metrics + summary charts

```python
def render_layout_executive():
    """
    Executive Summary (7-Metric snapshot).
    
    Metrics:
    - inspection_coverage
    - sla_compliance
    - critical_violations_pending
    - ramp_completion_rate
    - unresolved_conflicts
    - budget_burn_rate
    - public_complaints_30d
    """
    return dmc.Stack(
        children=[
            dmc.Title("Executive Summary", order=1),
            render_metric_dashboard(),  # 7 Metrics only
            # Summary charts (charts TBD in Task 12)
        ]
    )
```

### View 2: Operations

**Audience:** Operations managers, supervisors
**Content:** 15 Metrics + operational dashboards

```python
def render_layout_operations():
    """
    Operations Dashboard (15 Metrics: 5 inspection + 6 violation + 5 contractor).
    
    Components:
    - Inspection metrics (5 Metrics)
    - Violation tracking (6 Metrics)
    - Contractor coordination (5 Metrics)
    """
    return dmc.Stack(
        children=[
            dmc.Title("Operations", order=1),
            # Inspection Metric section
            render_inspection_metrics(),  # 5 Metrics
            # Violation Metric section
            render_violation_metrics(),  # 6 Metrics
            # Contractor Metric section
            render_contractor_metrics(),  # 5 Metrics
        ]
    )
```

### View 3: Analyst Tools

**Audience:** Project analysts
**Content:** 8 analyst dashboards + conflict triage + work order export

```python
def render_layout_analyst():
    """
    Analyst Tools (8 dashboards + utilities).
    
    Components (already exist from Tasks 6-9):
    1. Inspection Management Dashboard
    2. Violation Management Dashboard
    3. Contractor Dashboard
    4. Budget Tracking Dashboard
    5. Ramp Progress Dashboard
    6. Data Quality Dashboard
    7. Geographic Analysis Dashboard
    8. Compliance Dashboard
    9. Conflict Triage Component (Task 6)
    10. Work Order Export Component (Task 7)
    """
    return dmc.Stack(
        children=[
            dmc.Title("Analyst Tools", order=1),
            render_filter_bar(),
            
            # 8 analyst dashboards (from dash_layouts.py)
            dmc.Tabs(
                [
                    dmc.TabsList([
                        dmc.TabsTab("Inspections", value="inspection"),
                        dmc.TabsTab("Violations", value="violation"),
                        dmc.TabsTab("Contractors", value="contractor"),
                        dmc.TabsTab("Budget", value="budget"),
                        dmc.TabsTab("Ramp", value="ramp"),
                        dmc.TabsTab("Quality", value="quality"),
                        dmc.TabsTab("Geographic", value="geographic"),
                        dmc.TabsTab("Compliance", value="compliance"),
                    ]),
                    dmc.TabsPanel(value="inspection", children=[
                        # Inspection Management Dashboard
                    ]),
                    # ... rest of tabs ...
                ]
            ),
            
            # Utilities
            dmc.Divider(label="Utilities", labelPosition="center"),
            dmc.Group([
                render_conflict_triage_component(),  # Task 6
                render_work_order_export_component(),  # Task 7
            ]),
        ]
    )
```

### View 4: Data

**Audience:** Data engineers, quality managers
**Content:** Data quality metrics, geographic analysis, dataset registry

```python
def render_layout_data():
    """
    Data Quality & Governance (schema drift, freshness, quality score).
    
    Components:
    - Data quality scorecard
    - Dataset freshness tracking
    - Schema drift detection
    - Geographic analysis
    - Bias detection (future)
    """
    return dmc.Stack(
        children=[
            dmc.Title("Data Governance", order=1),
            # Data quality metrics
            render_data_quality_scorecard(),
            # Freshness tracking
            render_dataset_freshness(),
            # Schema drift
            render_schema_drift_report(),
            # Geographic analysis
            render_geographic_data_quality(),
        ]
    )
```

---

## Integration Checklist (Tasks 10-12)

- [x] Task 10: Create main navigation component
  - [x] `render_main_navigation()` with 4 views
  - [x] `get_navigation_items()` data structure
  - [x] Active state callbacks
  - [x] Mobile responsiveness
  - [x] Tests (70+ assertions)

- [ ] Task 11: Update Dash routing
  - [ ] Modify `app/dash_app.py` to use `render_main_navigation()`
  - [ ] Update `app/callbacks/navigation.py` with `/views/{view}` routing
  - [ ] Test navigation click → URL update
  - [ ] Verify active state highlighting
  - [ ] Test mobile hamburger menu

- [ ] Task 12: Create view-specific layouts
  - [ ] `render_layout_executive()` (7 Metrics)
  - [ ] `render_layout_operations()` (15 Metrics)
  - [ ] `render_layout_analyst()` (8 dashboards + 2 tools)
  - [ ] `render_layout_data()` (quality + geographic)
  - [ ] Integrate existing components (Tasks 6-9)
  - [ ] Test all 4 views render correctly

---

## Testing the Navigation

### Unit Tests

Run comprehensive test suite:

```bash
pytest tests/test_main_navigation.py -v

# Should pass:
# ✓ Navigation renders with 4 views
# ✓ Nav items display correct labels/icons
# ✓ Active view is highlighted
# ✓ Sidebar is responsive/collapsible
# ✓ CSS responsive breakpoints work
# ✓ Accessibility features (aria-labels, focus states)
```

### Integration Tests (Task 11)

After routing is connected:

```bash
pytest tests/test_integration_navigation.py -v

# Should test:
# ✓ Click on nav item → URL updates to /views/{view}
# ✓ Direct URL visit (e.g., /views/operations) → correct layout renders
# ✓ Active nav item matches current pathname
# ✓ Mobile hamburger menu appears on small screens
# ✓ Backward compatibility: old routes still work
```

### Manual Testing (Task 11)

1. Start app: `python app/dash_app.py`
2. Click "Executive Summary" → URL changes to `/views/executive`, view highlights
3. Click "Operations" → URL changes to `/views/operations`
4. Click "Analyst Tools" → URL changes to `/views/analyst` (with "new" badge)
5. Click "Data" → URL changes to `/views/data`
6. Resize window to <768px → hamburger menu appears
7. Check Firefox DevTools → all aria-labels and focus states present

---

## Backward Compatibility

Old routes (/, /const, /labor, /reports, etc.) should still work in Task 11:

```python
def render_page_content(pathname):
    # New 4-view routes (Task 11)
    if pathname.startswith("/views/"):
        view = pathname.split("/")[2]
        if view == "executive": return render_layout_executive()
        elif view == "operations": return render_layout_operations()
        # ...
    
    # Old routes (backward compatibility)
    if pathname == "/":
        return layout_dashboard()  # or render_layout_executive()
    elif pathname == "/const":
        return layout_construction()
    # ... rest of old routes ...
```

---

## Navigation Data Flow

```
User clicks nav item "Operations"
    ↓
href="/views/operations" → dcc.Location updates pathname
    ↓
routing callback: render_page_content("/views/operations")
    ↓
returns render_layout_operations() component
    ↓
dmc.AppShellMain content updates
    ↓
update_nav_active_styles callback fires
    ↓
nav-operations-container gets border + background highlight
    ↓
User sees highlighted nav item + new view loaded
```

---

## File Summary

| File | Task | Status | Lines | Purpose |
|------|------|--------|-------|---------|
| `app/components/main_navigation.py` | 10 | ✓ Done | 500 | 4-view sidebar nav + callbacks + CSS |
| `tests/test_main_navigation.py` | 10 | ✓ Done | 450 | 70+ unit tests for navigation |
| `app/dash_app.py` | 11 | Pending | — | Replace `render_sidebar()` with `render_main_navigation()` |
| `app/callbacks/navigation.py` | 11 | Pending | — | Update routing for `/views/{view}` |
| `app/dash_layouts.py` | 12 | Pending | — | Add 4 `render_layout_{view}()` functions |

---

## Key Design Decisions

1. **Route Convention:** `/views/{view}` instead of `/{view}` to clearly separate new 4-view routing from legacy routes
2. **Active State:** CSS border + background color (not text color) for accessibility
3. **Mobile:** Hamburger menu hidden by CSS; Dash callback ensures sync
4. **Badges:** "new" badge on Analyst Tools to draw attention
5. **Descriptions:** Each nav item has tooltip-friendly description for accessibility
6. **Extensibility:** `get_navigation_items()` returns data structure, easy to add/modify views

---

## Future Enhancements

- Task 13: Add role-based access control (hide Analyst Tools from non-analysts)
- Task 14: Live data integration tests across all 4 views
- Task 15: Dark mode toggle (CSS already supports `@media (prefers-color-scheme: dark)`)
- Task 16: Keyboard shortcuts (e.g., Alt+E for Executive, Alt+O for Operations)
- Task 17: View-specific filters (different filter presets per view)

---

**Created:** 2026-06-17
**Task:** 10 (Design 4-view navigation layout)
**Status:** Complete ✓
**Tests:** 70+ assertions passing
**Next:** Task 11 (Implement routing)
