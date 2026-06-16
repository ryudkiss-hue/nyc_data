"""
Unified Dash Application for NYC DOT SIM Workflows.

Production dashboard consolidating all 30+ visualizations from Phase 1.
Serves as primary UI (Streamlit is legacy support).

Features:
- Multi-page layout (Home, Violations, Ramps, Permits, GIS, Analytics)
- All visualizations use standardized units system
- Real-time data source annotations
- PDF/Excel/PNG export
- Light/dark theme toggle
- Responsive design (1920x1080+)
"""

import logging
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

logger = logging.getLogger(__name__)

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
)

app.title = "NYC DOT SIM Workflows"

# Define app layout
app.layout = dbc.Container(
    [
        dbc.Row([
            dbc.Col([
                html.H1("NYC DOT Sidewalk Inspection & Management Workflows", className="mb-2"),
                html.P("Production Dashboard | Real-time Data Analysis | Phase 1 Complete",
                       className="text-muted")
            ], width=12)
        ], className="mb-4 pt-4"),

        dbc.Row([
            dbc.Col([
                dbc.Nav([
                    dbc.NavLink("Home", href="/", active="exact", className="nav-link"),
                    dbc.NavLink("Violations", href="/violations", active="exact", className="nav-link"),
                    dbc.NavLink("Ramps", href="/ramps", active="exact", className="nav-link"),
                    dbc.NavLink("Permits", href="/permits", active="exact", className="nav-link"),
                    dbc.NavLink("Geographic", href="/geographic", active="exact", className="nav-link"),
                    dbc.NavLink("Analytics", href="/analytics", active="exact", className="nav-link"),
                    dbc.NavLink("Settings", href="/settings", active="exact", className="nav-link ms-auto"),
                ], vertical=False, pills=True, className="mb-4"),
            ], width=12)
        ], className="border-bottom pb-3"),

        # Page content placeholder
        html.Div(id="page-content", className="mt-4"),

        # Hidden div to store theme preference
        dcc.Store(id="theme-store", data={"theme": "light"}),

        # Footer
        dbc.Row([
            dbc.Col([
                html.Hr(className="mt-5"),
                html.P([
                    "Data: NYC Open Data (Socrata) | Updated: 2026-06-11 | "
                    "Phase 1 Complete | Cache: DuckDB | ",
                    html.A("GitHub", href="https://github.com/ryudkiss-hue/nyc_data", target="_blank"),
                ], className="text-muted small")
            ], width=12)
        ]),
    ],
    fluid=True,
    className="mt-4",
)

# Callback for page routing
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")],
    prevent_initial_call=False
)
def display_page(pathname):
    """Route to appropriate page based on pathname."""
    if pathname == "/" or pathname is None:
        from .layouts.home import layout as home_layout
        return home_layout
    elif pathname == "/violations":
        from .layouts.violations import layout as violations_layout
        return violations_layout
    elif pathname == "/ramps":
        from .layouts.ramps import layout as ramps_layout
        return ramps_layout
    elif pathname == "/permits":
        from .layouts.permits import layout as permits_layout
        return permits_layout
    elif pathname == "/geographic":
        from .layouts.gis import layout as gis_layout
        return gis_layout
    elif pathname == "/analytics":
        from .layouts.analytics import layout as analytics_layout
        return analytics_layout
    elif pathname == "/settings":
        from .layouts.settings import layout as settings_layout
        return settings_layout
    else:
        return dbc.Alert("404: Page not found", color="danger")

if __name__ == "__main__":
    logger.info("Starting NYC DOT SIM Workflows Dashboard")
    logger.info("Running on http://127.0.0.1:8050")
    app.run_server(debug=True, host="127.0.0.1", port=8050)
