"""
dash_app/app.py
───────────────
NYC DOT Sidewalk Toolkit — primary analyst GUI (Dash)

  python dash_app/app.py
  gunicorn "dash_app.app:server"
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
import dash_bootstrap_components as dbc
import plotly.io as pio
from dash import Dash, Input, Output, State, callback, dcc, html

_DEBUG = os.getenv("NYC_DOT_DEBUG", "").lower() in ("1", "true", "yes")

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
    ],
    suppress_callback_exceptions=True,
    title="NYC DOT Sidewalk Toolkit",
    update_title=None,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": "NYC DOT Sidewalk Inspection & Management — Analyst Pack dashboard",
        },
    ],
)
server = app.server

pio.templates.default = "plotly_dark"

NAV = [
    {"label": "Home", "icon": "bi bi-house", "path": "/"},
    {"label": "Construction", "icon": "bi bi-cone-striped", "path": "/construction"},
    {"label": "Contracts", "icon": "bi bi-file-earmark-text", "path": "/contracts"},
    {"label": "Metrics", "icon": "bi bi-speedometer2", "path": "/metrics"},
    {"label": "Inquiries", "icon": "bi bi-chat-left-text", "path": "/inquiries"},
    {"label": "Settings", "icon": "bi bi-gear", "path": "/settings"},
]

if _DEBUG:
    NAV.extend(
        [
            {"label": "Map View", "icon": "bi bi-map", "path": "/geospatial"},
            {"label": "Dev tools", "icon": "bi bi-grid", "path": "/devtools"},
        ]
    )


def build_sidebar(collapsed: bool = False) -> html.Div:
    nav_items = []
    for item in NAV:
        content = [
            html.I(className=f"{item['icon']} nyc-nav-icon", **{"aria-hidden": "true"}),
            html.Span(item["label"], className="nyc-nav-label") if not collapsed else None,
        ]
        nav_items.append(
            dcc.Link(
                content,
                href=item["path"],
                className="nyc-nav-link",
                id={"type": "nav-link", "href": item["path"]},
                **{"aria-label": item["label"]},
            )
        )

    return html.Div(
        id="nyc-sidebar",
        className="sidebar-collapsed" if collapsed else "",
        children=[
            html.Div(
                [
                    html.Div(
                        [html.I(className="bi bi-buildings-fill", **{"aria-hidden": "true"})],
                        className="nyc-logo-icon",
                    ),
                    (
                        html.Div(
                            [
                                html.Div("NYC DOT", className="nyc-logo-title"),
                                html.Div("Sidewalk Toolkit", className="nyc-logo-sub"),
                            ],
                            className="nyc-logo-text",
                        )
                        if not collapsed
                        else None
                    ),
                ],
                className="nyc-logo-section",
            ),
            html.Nav(nav_items, className="nyc-nav-container", **{"aria-label": "Main"}),
            html.Div(
                [
                    html.Button(
                        [
                            html.I(
                                className=(
                                    "bi bi-chevron-left" if not collapsed else "bi bi-chevron-right"
                                ),
                                **{"aria-hidden": "true"},
                            ),
                            html.Span("Collapse") if not collapsed else None,
                        ],
                        id="sidebar-toggle",
                        className="nyc-collapse-btn",
                        **{"aria-label": "Toggle sidebar"},
                    )
                ],
                className="nyc-sidebar-footer",
            ),
        ],
    )


def build_header() -> html.Header:
    return html.Header(
        id="nyc-header",
        children=[
            html.Div(
                html.Div(
                    "NYC DOT — Sidewalk Inspection & Management",
                    className="nyc-header-title",
                ),
                className="nyc-header-left",
            ),
        ],
    )


app.layout = html.Div(
    id="app-root",
    **{"data-theme": "dark"},
    children=[
        html.A("Skip to main content", href="#nyc-content", className="skip-link"),
        dcc.Store(id="sidebar-store", data=False, storage_type="local"),
        dcc.Store(id="app-ready-store", data=True),
        dcc.Location(id="url"),
        html.Div(
            id="layout-container",
            style={"display": "flex"},
            children=[
                html.Div(id="sidebar-container", children=build_sidebar()),
                html.Div(
                    id="main-container",
                    children=[
                        build_header(),
                        html.Main(dash.page_container, id="nyc-content", tabIndex=-1),
                    ],
                ),
            ],
        ),
    ],
)


@callback(
    Output("sidebar-container", "children"),
    Output("sidebar-store", "data"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-store", "data"),
    prevent_initial_call=True,
)
def toggle_sidebar(n, is_collapsed):
    return build_sidebar(not is_collapsed), not is_collapsed


@callback(
    Output("sidebar-container", "children", allow_duplicate=True),
    Input("sidebar-store", "data"),
    prevent_initial_call=True,
)
def init_sidebar(is_collapsed):
    return build_sidebar(is_collapsed)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
