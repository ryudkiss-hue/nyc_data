"""
dash_app/app.py
───────────────
NYC DOT Data Assistant — Dash + Plotly + DuckDB/MotherDuck

Entry point:
  development  →  python dash_app/app.py
  production   →  gunicorn "dash_app.app:server"
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
import dash_bootstrap_components as dbc
import plotly.io as pio
from dash import Dash, Input, Output, State, callback, dcc, html

# ── Dash app ──────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
    ],
    suppress_callback_exceptions=True,
    title="NYC DOT Data Assistant",
    update_title=None,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": "NYC Department of Transportation Data Assistant — powered by Dash, Plotly, DuckDB",
        },
    ],
)
server = app.server  # WSGI entry for gunicorn

# Default Plotly template
pio.templates.default = "plotly_dark"

# ── Navigation config ─────────────────────────────────────────────────────────
NAV = [
    {"label": "Dashboard", "icon": "bi bi-house", "path": "/"},
    {"label": "Reconciler", "icon": "bi bi-git", "path": "/reconciler", "badge": "Core"},
    {"label": "Data Analysis", "icon": "bi bi-bar-chart", "path": "/analysis"},
    {"label": "KPI Tracker", "icon": "bi bi-lightning", "path": "/kpis"},
    {
        "label": "Quantum Optimizer",
        "icon": "bi bi-lightning-charge",
        "path": "/quantum",
        "badge": "AI+",
    },
    {"label": "Work Board", "icon": "bi bi-clipboard", "path": "/tasks"},
    {"label": "Map View", "icon": "bi bi-map", "path": "/geospatial"},
    {"label": "Data Explorer", "icon": "bi bi-database", "path": "/pipeline"},
    {"label": "Reports", "icon": "bi bi-file-text", "path": "/reports"},
    {"label": "System Health", "icon": "bi bi-shield-check", "path": "/health"},
    {"label": "Dev Tools", "icon": "bi bi-terminal", "path": "/devtools"},
]

PLOTLY_THEMES = {
    "dark": "plotly_dark",
    "light": "simple_white",
    "sepia": "ggplot2",
}


def build_sidebar(collapsed: bool = False) -> html.Div:
    nav_items = []
    for item in NAV:
        label = item["label"]
        icon = item["icon"]
        path = item["path"]
        badge = item.get("badge")

        content = [
            html.I(className=f"{icon} nyc-nav-icon"),
            html.Span(label, className="nyc-nav-label") if not collapsed else None,
        ]
        if badge and not collapsed:
            content.append(dbc.Badge(badge, pill=True, className="ms-auto nyc-nav-badge"))

        nav_items.append(
            dcc.Link(
                content,
                href=path,
                className="nyc-nav-link",
                id={"type": "nav-link", "href": path},
            )
        )

    return html.Div(
        id="nyc-sidebar",
        className="sidebar-collapsed" if collapsed else "",
        children=[
            # Logo Section
            html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="bi bi-buildings-fill",
                                style={"fontSize": "1.2rem", "color": "white"},
                            ),
                        ],
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
            # Navigation
            html.Div(nav_items, className="nyc-nav-container"),
            # Bottom Section (Collapse Toggle)
            html.Div(
                [
                    html.Button(
                        [
                            html.I(
                                className=(
                                    "bi bi-chevron-left" if not collapsed else "bi bi-chevron-right"
                                )
                            ),
                            html.Span("Collapse") if not collapsed else None,
                        ],
                        id="sidebar-toggle",
                        className="nyc-collapse-btn",
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
                [
                    html.I(className="bi bi-list lg-hidden", id="mobile-toggle"),
                    html.Div(
                        "NYC DOT — Sidewalk Inspection & Management",
                        className="nyc-header-title d-none d-sm-block",
                    ),
                ],
                className="nyc-header-left",
            ),
            html.Div(
                [
                    html.Button(html.I(className="bi bi-bell"), className="nyc-header-icon-btn"),
                    html.Div(
                        [
                            html.I(className="bi bi-person-fill", style={"color": "white"}),
                        ],
                        className="nyc-user-avatar",
                    ),
                ],
                className="nyc-header-right",
            ),
        ],
    )


# ── Root layout ───────────────────────────────────────────────────────────────
app.layout = html.Div(
    id="app-root",
    **{"data-theme": "dark"},
    children=[
        # Global stores
        dcc.Store(id="theme-store", data="dark", storage_type="local"),
        dcc.Store(id="sidebar-store", data=False, storage_type="local"),
        dcc.Store(
            id="token-store", data=os.getenv("SOCRATA_APP_TOKEN", ""), storage_type="session"
        ),
        dcc.Store(id="session-store", data=None, storage_type="session"),
        dcc.Store(
            id="auth-store",
            data={"is_authenticated": True, "user": "Richard Yudkiss"},
            storage_type="session",
        ),
        dcc.Store(id="app-ready-store", data=False),
        dcc.Location(id="url"),
        # ── Loading Overlay ───────────────────────────────────────────────────
        html.Div(
            id="app-loading-overlay",
            children=[
                html.Div(
                    [
                        html.Div(className="nyc-spinner mb-3"),
                        html.P(
                            "Loading NYC DOT Toolkit…", className="text-xs text-muted-foreground"
                        ),
                    ],
                    className="d-flex flex-column align-items-center",
                ),
            ],
            className="nyc-loading-overlay",
        ),
        # ── Global Toaster (Notifications) ────────────────────────────────────
        html.Div(id="nyc-toaster-container", className="nyc-toaster"),
        # ── Main App Layout ───────────────────────────────────────────────────
        html.Div(
            id="layout-container",
            style={"display": "none"},  # Hidden until ready
            children=[
                # Sidebar wrapper
                html.Div(id="sidebar-container", children=build_sidebar()),
                # Main content wrapper
                html.Div(
                    id="main-container",
                    children=[
                        build_header(),
                        html.Main(
                            dash.page_container,
                            id="nyc-content",
                        ),
                    ],
                ),
            ],
        ),
        # ── AI Assistant Widget ──────────────────────────────────────────────────
        html.Div(
            [
                dbc.Button(
                    [html.I(className="bi bi-robot me-2"), "AI Assistant"],
                    id="ai-toggle-btn",
                    color="primary",
                    className="rounded-pill shadow-lg nyc-animate-fade-up",
                ),
            ],
            style={"position": "fixed", "bottom": "30px", "right": "30px", "zIndex": 1000},
        ),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("🤖 NYC Data AI Agent")),
                dbc.ModalBody(
                    [
                        html.Div(
                            id="ai-chat-history",
                            style={"height": "350px", "overflowY": "auto", "padding": "10px"},
                            className="mb-3",
                        ),
                        dbc.InputGroup(
                            [
                                dbc.Input(id="ai-user-input", placeholder="Ask about NYC data..."),
                                dbc.Button("Send", id="ai-send-btn", color="primary"),
                            ]
                        ),
                    ]
                ),
            ],
            id="ai-modal",
            is_open=False,
            size="lg",
        ),
    ],
)


# ── Theme callback ────────────────────────────────────────────────────────────
@callback(
    Output("app-root", "data-theme"),
    Output("theme-store", "data"),
    Output("theme-dark", "className"),
    Output("theme-light", "className"),
    Output("theme-sepia", "className"),
    Input("theme-dark", "n_clicks"),
    Input("theme-light", "n_clicks"),
    Input("theme-sepia", "n_clicks"),
    Input("theme-store", "data"),
    prevent_initial_call=False,
)
def switch_theme(n_dark, n_light, n_sepia, stored):
    ctx = dash.callback_context
    triggered = ctx.triggered_id if ctx.triggered_id else "theme-store"

    theme_map = {
        "theme-dark": "dark",
        "theme-light": "light",
        "theme-sepia": "sepia",
        "theme-store": stored or "dark",
    }
    theme = theme_map.get(triggered, "dark")

    def cls(t):
        return "nyc-theme-btn active" if t == theme else "nyc-theme-btn"

    pio.templates.default = PLOTLY_THEMES.get(theme, "plotly_dark")

    return theme, theme, cls("dark"), cls("light"), cls("sepia")


# ── Sidebar collapse callback ────────────────────────────────────────────────
@callback(
    Output("sidebar-container", "children"),
    Output("sidebar-store", "data"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-store", "data"),
    prevent_initial_call=True,
)
def toggle_sidebar(n, is_collapsed):
    new_state = not is_collapsed
    return build_sidebar(new_state), new_state


# ── Initial sidebar state callback ───────────────────────────────────────────
@callback(
    Output("sidebar-container", "children", allow_duplicate=True),
    Input("sidebar-store", "data"),
    prevent_initial_call=True,
)
def init_sidebar(is_collapsed):
    return build_sidebar(is_collapsed)


# ── App readiness / Loading sequence callback ────────────────────────────────
@callback(
    Output("app-loading-overlay", "style"),
    Output("layout-container", "style"),
    Output("app-ready-store", "data"),
    Input("auth-store", "data"),
    Input("url", "pathname"),
    State("app-ready-store", "data"),
)
def handle_app_loading(auth, pathname, is_ready):
    if is_ready:
        return {"display": "none"}, {"display": "flex"}, True

    # Simulate a brief loading delay for "impressive" effect
    import time

    time.sleep(1.0)

    return {"display": "none"}, {"display": "flex"}, True


# ── Token store callback ──────────────────────────────────────────────────────
@callback(
    Output("token-store", "data"),
    Input("socrata-token-input", "value"),
)
def store_token(val):
    return val or ""


# ── AI Assistant Callbacks ───────────────────────────────────────────────────
@app.callback(
    Output("ai-modal", "is_open"),
    Input("ai-toggle-btn", "n_clicks"),
    State("ai-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_ai_modal(n, is_open):
    return not is_open


@app.callback(
    Output("ai-chat-history", "children"),
    Input("ai-send-btn", "n_clicks"),
    State("ai-user-input", "value"),
    State("ai-chat-history", "children"),
    prevent_initial_call=True,
)
def handle_ai_chat(n, message, history):
    if not message:
        return history
    history = history or []

    user_msg = html.Div(
        [html.B("You: "), html.Span(message)], className="mb-2 p-2 bg-secondary-nyc rounded"
    )

    # Simulated AI logic
    import socrata_toolkit.ai as st_ai

    bot = st_ai.SocrataLLMChatbot()
    response = bot.chat(message)

    bot_msg = html.Div(
        [html.B("AI: "), html.Span(response)], className="mb-2 p-2 bg-primary rounded border-nyc"
    )

    return history + [user_msg, bot_msg]


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
