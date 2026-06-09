from dash import Input, Output, State, callback, no_update
import dash_mantine_components as dmc
from app.dash_layouts import (
    layout_construction,
    layout_copilot,
    layout_dashboard,
    layout_engineering,
    layout_gis,
    layout_labor,
    layout_nlp,
    layout_reports,
    layout_settings,
    layout_sql_tools,
    layout_stats,
    layout_toolbox,
    layout_tutorials,
)

def register_navigation_callbacks(app):
    @app.callback(
        Output("mantine-provider", "forceColorScheme"),
        Input("btn-toggle-theme", "n_clicks"),
        State("mantine-provider", "forceColorScheme"),
        prevent_initial_call=True
    )
    def toggle_theme(n_clicks, current):
        return "dark" if current == "light" else "light"

    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname")
    )
    def render_page_content(pathname):
        if pathname == "/": return layout_dashboard()
        elif pathname == "/const": return layout_construction()
        elif pathname == "/labor": return layout_labor()
        elif pathname == "/reports": return layout_reports()
        elif pathname == "/stats": return layout_stats()
        elif pathname == "/geo": return layout_gis()
        elif pathname == "/eng": return layout_engineering()
        elif pathname == "/sql": return layout_sql_tools()
        elif pathname == "/nlp": return layout_nlp()
        elif pathname == "/tutorials": return layout_tutorials()
        elif pathname == "/settings": return layout_settings()
        elif pathname == "/copilot": return layout_copilot()
        elif pathname == "/toolbox": return layout_toolbox()
        return dmc.Text("404: Not Found", c="red")

    @app.callback(
        [Output(f"nav-{id}", "active") for id in ["dash", "const", "labor", "reports", "stats", "geo", "eng", "sql", "nlp", "tutorials", "settings", "toolbox", "copilot"]],
        Input("url", "pathname")
    )
    def update_nav_active(pathname):
        paths = ["/", "/const", "/labor", "/reports", "/stats", "/geo", "/eng", "/sql", "/nlp", "/tutorials", "/settings", "/toolbox", "/copilot"]
        return [pathname == p for p in paths]

    @app.callback(
        Output("audit-log-terminal", "children", allow_duplicate=True),
        Input("url", "pathname"),
        State("audit-log-terminal", "children"),
        prevent_initial_call="initial_duplicate"
    )
    def heartbeat_callback(path, current_log):
        # Industrial heartbeat for session tracking
        return no_update

    app.clientside_callback(
        """
        function(selected_tier) {
            var elements = document.getElementsByClassName('viz-container');
            for (var i = 0; i < elements.length; i++) {
                if (selected_tier === 'ALL') {
                    elements[i].style.display = 'block';
                } else {
                    if (elements[i].classList.contains('viz-tier-' + selected_tier)) {
                        elements[i].style.display = 'block';
                    } else {
                        elements[i].style.display = 'none';
                    }
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("global-tier-filter", "id"),
        Input("global-tier-filter", "value"),
        prevent_initial_call=True
    )
