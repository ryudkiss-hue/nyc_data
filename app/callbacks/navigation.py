import dash_mantine_components as dmc
from dash import Input, Output, State, no_update

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
        prevent_initial_call=True,
    )
    def toggle_theme(n_clicks, current):
        return "dark" if current == "light" else "light"

    @app.callback(
        Output("page-content", "children"),
        Output("store-page-rendered", "data"),
        Input("url", "pathname"),
    )
    def render_page_content(pathname):
        if pathname == "/":
            return layout_dashboard(), pathname
        elif pathname == "/const":
            return layout_construction(), pathname
        elif pathname == "/labor":
            return layout_labor(), pathname
        elif pathname == "/reports":
            return layout_reports(), pathname
        elif pathname == "/stats":
            return layout_stats(), pathname
        elif pathname == "/geo":
            return layout_gis(), pathname
        elif pathname == "/eng":
            return layout_engineering(), pathname
        elif pathname == "/sql":
            return layout_sql_tools(), pathname
        elif pathname == "/nlp":
            return layout_nlp(), pathname
        elif pathname == "/tutorials":
            return layout_tutorials(), pathname
        elif pathname == "/settings":
            return layout_settings(), pathname
        elif pathname == "/copilot":
            return layout_copilot(), pathname
        elif pathname == "/toolbox":
            return layout_toolbox(), pathname
        return dmc.Text("404: Not Found", c="red"), pathname

    @app.callback(
        [
            Output(f"nav-{id}", "active")
            for id in [
                "dash",
                "const",
                "labor",
                "reports",
                "stats",
                "geo",
                "eng",
                "sql",
                "nlp",
                "tutorials",
                "settings",
                "toolbox",
                "copilot",
            ]
        ],
        Input("url", "pathname"),
    )
    def update_nav_active(pathname):
        paths = [
            "/",
            "/const",
            "/labor",
            "/reports",
            "/stats",
            "/geo",
            "/eng",
            "/sql",
            "/nlp",
            "/tutorials",
            "/settings",
            "/toolbox",
            "/copilot",
        ]
        return [pathname == p for p in paths]

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
        prevent_initial_call=True,
    )
