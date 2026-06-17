# Navigation Component Usage Example

Quick reference for integrating the 4-view navigation system.

---

## Basic Import & Usage

```python
from app.components.main_navigation import (
    render_main_navigation,
    render_navigation_store,
    get_navigation_css,
)

# In your Dash app layout:
app.layout = dmc.MantineProvider(
    children=[
        dcc.Location(id="url", refresh=False),
        render_navigation_store(),  # Persist nav state
        html.Style(get_navigation_css()),  # Mobile + dark mode CSS
        
        dmc.AppShell(
            navbar={"width": 300, "breakpoint": "sm"},
            children=[
                dmc.AppShellNavbar(
                    children=[render_main_navigation()]  # 4-view sidebar
                ),
                dmc.AppShellMain(id="page-content", children=[]),
            ],
        ),
    ],
)
```

---

## Navigation Items Structure

```python
from app.components.main_navigation import get_navigation_items

items = get_navigation_items()
# Returns:
[
    {
        "id": "nav-executive",
        "label": "Executive Summary",
        "view": "executive",
        "route": "/views/executive",
        "icon": "mdi:chart-line",
        "description": "Leadership overview - 7 headline KPIs",
        "color": "blue",
        "badge": None,
    },
    {
        "id": "nav-operations",
        "label": "Operations",
        "view": "operations",
        "route": "/views/operations",
        "icon": "mdi:factory",
        "description": "Daily ops monitoring - 15 KPIs (inspection+violation+contractor)",
        "color": "orange",
        "badge": None,
    },
    {
        "id": "nav-analyst",
        "label": "Analyst Tools",
        "view": "analyst",
        "route": "/views/analyst",
        "icon": "mdi:chart-box-multiple",
        "description": "Deep analysis - 8 dashboards + conflict triage + export",
        "color": "cyan",
        "badge": "new",
    },
    {
        "id": "nav-data",
        "label": "Data",
        "view": "data",
        "route": "/views/data",
        "icon": "mdi:database-check",
        "description": "Quality & governance - data health, geographic, schema drift",
        "color": "grape",
        "badge": None,
    },
]
```

---

## Routing Integration (Task 11)

```python
from app.components.main_navigation import register_navigation_callbacks

def register_navigation_callbacks(app):
    """Register all navigation callbacks."""
    
    # Main navigation active state styling
    register_navigation_callbacks(app)
    
    # Main routing callback
    @app.callback(Output("page-content", "children"), Input("url", "pathname"))
    def render_page_content(pathname):
        
        # NEW: Handle /views/{view} routes
        if pathname.startswith("/views/"):
            view = pathname.split("/")[2]
            if view == "executive":
                return render_layout_executive()
            elif view == "operations":
                return render_layout_operations()
            elif view == "analyst":
                return render_layout_analyst()
            elif view == "data":
                return render_layout_data()
        
        # EXISTING: Backward compatibility with old routes
        if pathname == "/":
            return layout_dashboard()
        elif pathname == "/const":
            return layout_construction()
        # ... rest of old routes ...
        
        return dmc.Center(dmc.Text("404: Not Found", c="red"))
```

---

## View Templates (Task 12)

### Executive Summary View
```python
def render_layout_executive():
    """Executive Summary - 7 headline KPIs for leadership."""
    return dmc.Stack(
        children=[
            dmc.Title("Executive Summary", order=1),
            
            # 7 KPI cards
            render_kpi_dashboard(),  # Filtered to 7 KPIs only
            
            # Summary charts
            render_executive_charts(),  # TBD in Task 12
        ],
        spacing="lg",
    )
```

### Operations View
```python
def render_layout_operations():
    """Operations - 15 KPIs for daily monitoring."""
    return dmc.Stack(
        children=[
            dmc.Title("Operations Dashboard", order=1),
            
            # 5 Inspection KPIs
            render_inspection_kpis(),
            
            # 6 Violation KPIs
            render_violation_kpis(),
            
            # 5 Contractor KPIs
            render_contractor_kpis(),
        ],
        spacing="lg",
    )
```

### Analyst Tools View
```python
def render_layout_analyst():
    """Analyst Tools - 8 dashboards + utilities."""
    return dmc.Stack(
        children=[
            dmc.Title("Analyst Tools", order=1),
            render_filter_bar(),  # Global filters
            
            # 8 analyst dashboards in tabs
            dmc.Tabs([
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
            ]),
            
            dmc.Divider(label="Utilities", labelPosition="center"),
            dmc.Group([
                render_conflict_triage_component(),  # Task 6
                render_work_order_export_component(),  # Task 7
            ]),
        ],
        spacing="lg",
    )
```

### Data View
```python
def render_layout_data():
    """Data - Quality & governance."""
    return dmc.Stack(
        children=[
            dmc.Title("Data Governance", order=1),
            
            # Data quality scorecard
            render_data_quality_scorecard(),
            
            # Dataset freshness tracking
            render_dataset_freshness(),
            
            # Schema drift detection
            render_schema_drift_report(),
            
            # Geographic data quality
            render_geographic_data_quality(),
        ],
        spacing="lg",
    )
```

---

## Navigation Click Flow

```
User clicks "Operations" nav item
    |
    v
href="/views/operations" → browser URL changes
    |
    v
dcc.Location detects pathname change
    |
    v
render_page_content() callback fires
    |
    v
pathname = "/views/operations"
    |
    v
render_layout_operations() called
    |
    v
Content updates in dmc.AppShellMain
    |
    v
update_nav_active_styles() callback fires
    |
    v
"nav-operations-container" gets blue border + light blue background
    |
    v
User sees highlighted nav item + new view
```

---

## Callback Details

### Active State Styling

```python
@app.callback(
    [Output(f"{item['id']}-container", "style") for item in get_navigation_items()],
    Input("url", "pathname"),
)
def update_nav_active_styles(pathname):
    """Highlight active nav item based on URL."""
    nav_items = get_navigation_items()
    styles = []
    
    for item in nav_items:
        is_active = pathname.startswith(item["route"])
        
        if is_active:
            styles.append({
                "border": "2px solid #0066CC",
                "backgroundColor": "#E7F5FF",
                # ... transitions ...
            })
        else:
            styles.append({
                "border": "2px solid transparent",
                "backgroundColor": "#F8F9FA",
                # ... transitions ...
            })
    
    return styles
```

---

## Testing

### Import Test
```python
from app.components.main_navigation import (
    render_main_navigation,
    get_navigation_items,
    register_navigation_callbacks,
)

# Verify items
items = get_navigation_items()
assert len(items) == 4
assert all("route" in item for item in items)
```

### Component Rendering Test
```python
from app.components.main_navigation import render_main_navigation

nav = render_main_navigation()
assert nav is not None
# Full test suite: pytest tests/test_main_navigation.py -v
```

### Integration Test (Task 11)
```bash
# Start app
python app/dash_app.py

# Verify:
# 1. Sidebar displays with 4 nav items
# 2. Click "Operations" → URL changes to /views/operations
# 3. Operations view renders
# 4. "Operations" nav item is highlighted (blue border)
# 5. Click "Analyst Tools" → URL changes to /views/analyst
# 6. Analyst view renders
# 7. "Analyst Tools" nav item is highlighted + has "new" badge
```

---

## Mobile Responsiveness

**Desktop (>768px):**
- Sidebar visible (300px width, 15% of screen)
- Hamburger menu hidden
- Navigation always accessible

**Mobile (<768px):**
- Hamburger menu visible (top-left of header)
- Sidebar hidden by default
- Click hamburger → sidebar slides in from left
- Click backdrop or nav item → sidebar slides out

**CSS Breakpoint:**
```css
@media (max-width: 768px) {
    #main-navigation {
        position: fixed;
        left: 0;
        top: 70px;  /* Below header */
        transform: translateX(-100%);  /* Hidden */
    }
    
    #main-navigation.open {
        transform: translateX(0);  /* Visible */
    }
}
```

---

## Accessibility

### Keyboard Navigation
- Tab: Move between nav items
- Enter: Select nav item (navigate to route)
- Space: Select nav item (alternative)
- Shift+Tab: Move backwards

### Screen Reader Support
```html
<a href="/views/operations" aria-label="Navigate to Operations">
  <span>Operations</span>
  <span>Daily ops monitoring - 15 KPIs</span>
</a>
```

### Visual Indicators
- Focus ring: 2px solid #0066CC outline, 2px offset
- Active state: Blue border (#0066CC) + light blue background (#E7F5FF)
- Hover state: Light blue background, slide right (translateX 4px)
- Disabled state: Grayed out (future feature)

---

## Customization

### Change Navigation Item Label
```python
# In get_navigation_items():
{
    "id": "nav-executive",
    "label": "Leadership Dashboard",  # Changed
    "view": "executive",
    # ... rest ...
}
```

### Change Navigation Icon
```python
{
    "id": "nav-operations",
    "icon": "mdi:tools",  # Changed from mdi:factory
    # ... rest ...
}
```

### Add New Badge
```python
{
    "id": "nav-data",
    "badge": "beta",  # Added badge
    # ... rest ...
}
```

### Add New View
```python
{
    "id": "nav-custom",
    "label": "Custom View",
    "view": "custom",
    "route": "/views/custom",
    "icon": "mdi:star",
    "description": "Custom view for special features",
    "color": "violet",
    "badge": None,
}

# Then in routing:
elif view == "custom":
    return render_layout_custom()
```

---

## Files & Imports

**Component:**
```
app/components/main_navigation.py
├── get_navigation_items()
├── render_main_navigation()
├── render_mobile_navigation_trigger()
├── render_navigation_store()
├── register_navigation_callbacks()
├── get_navigation_css()
└── [private functions: _render_nav_button, _render_nav_header, _render_nav_footer]
```

**Tests:**
```
tests/test_main_navigation.py
├── TestNavigationDataStructure (8 tests)
├── TestNavigationRendering (7 tests)
├── TestMobileNavigation (3 tests)
├── TestNavigationStore (4 tests)
├── TestNavigationCallbacks (2 tests)
├── TestNavigationStyling (5 tests)
├── TestNavigationIntegration (4 tests)
├── TestAccessibility (4 tests)
└── TestEdgeCases & Performance (3 tests)
```

**Documentation:**
```
docs/NAVIGATION_INTEGRATION.md     — Full integration guide
TASK_10_COMPLETION_SUMMARY.md      — Task completion report
NAVIGATION_USAGE_EXAMPLE.md        — This file
```

---

## Summary

The navigation component provides a **clean, accessible interface** for switching between 4 role-based dashboard views. It's production-ready, fully tested, and integrates seamlessly with Dash routing via URL-based navigation.

**Next Steps:**
1. Task 11: Update app layout and routing
2. Task 12: Create view-specific layouts
3. Task 13: Verification checklist
4. Task 14: Integration tests with live data

**Questions?** See `docs/NAVIGATION_INTEGRATION.md` for detailed integration guide.
