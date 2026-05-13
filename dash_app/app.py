"""
dash_app/app.py
───────────────
NYC DOT Data Assistant — Dash + Plotly + DuckDB/MotherDuck

Entry point:
  development  →  python dash_app/app.py
  production   →  gunicorn "dash_app.app:server"
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import Dash, html, dcc, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc
import plotly.io as pio

from dash_app.data import db

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
        {"name": "description", "content": "NYC Department of Transportation Data Assistant — powered by Dash, Plotly, DuckDB"},
    ],
)
server = app.server  # WSGI entry for gunicorn

# Default Plotly template
pio.templates.default = "plotly_dark"

# ── Navigation config ─────────────────────────────────────────────────────────
NAV = [
    ("Overview",        [
        ("🏠", "Dashboard",    "/"),
    ]),
    ("Analytics & AI",  [
        ("📊", "Analytics",    "/analytics"),
        ("🤖", "AI Assistant", "/ai"),
        ("✨", "SoQL Maestro", "/soql"),
        ("⚡", "Quantum",      "/quantum"),
    ]),
    ("Operations",      [
        ("🗺️", "Geospatial",   "/geospatial"),
        ("✅", "Task Board",   "/tasks"),
        ("🔄", "Data Pipeline","/pipeline"),
    ]),
    ("Governance",      [
        ("🔬", "Governance",   "/governance"),
        ("📋", "Reports",      "/reports"),
    ]),
    ("Data Management", [
        ("🛠️", "Engineering",  "/engineering"),
        ("📤", "Export",       "/export"),
    ]),
    ("System",          [
        ("⚙️", "Settings",     "/settings"),
        ("🔗", "Dev Tools",    "/devtools"),
    ]),
]

PLOTLY_THEMES = {
    "dark":  "plotly_dark",
    "light": "simple_white",
    "sepia": "ggplot2",
}


def build_sidebar() -> html.Div:
    nav_items = []
    for section, pages in NAV:
        nav_items.append(
            html.Div(section, className="nyc-nav-section-title")
        )
        for icon, label, href in pages:
            nav_items.append(
                dcc.Link(
                    [html.Span(icon, style={"width": "20px", "display": "inline-block"}), label],
                    href=href,
                    className="nyc-nav-link",
                    id={"type": "nav-link", "href": href},
                )
            )

    tables = db.list_tables()
    db_badge = html.Span(
        f"{'☁️ MotherDuck' if db.is_motherduck() else '🦆 DuckDB local'} · {len(tables)} tables",
        style={"fontSize": "0.68rem", "color": "var(--text-muted)"},
    )

    return html.Div(
        id="nyc-sidebar",
        children=[
            # Logo
            html.Div([
                html.Div("🏙️ NYC DOT", className="nyc-logo-title"),
                html.Div("Data Assistant", className="nyc-logo-sub"),
            ], className="nyc-logo"),

            # Nav
            html.Div(nav_items, style={"padding": "8px 0"}),

            # Divider
            html.Hr(style={"borderColor": "var(--border-color)", "margin": "8px 0"}),

            # Theme toggle
            html.Div("Theme", className="nyc-nav-section-title"),
            html.Div([
                html.Button("🌙", id="theme-dark",  className="nyc-theme-btn active", n_clicks=0, title="Dark"),
                html.Button("☀️", id="theme-light", className="nyc-theme-btn",        n_clicks=0, title="Light"),
                html.Button("📜", id="theme-sepia", className="nyc-theme-btn",        n_clicks=0, title="Sepia"),
            ], className="nyc-theme-row"),

            html.Hr(style={"borderColor": "var(--border-color)", "margin": "8px 0"}),

            # Socrata token
            html.Div("Socrata Token", className="nyc-nav-section-title"),
            html.Div(
                dbc.Input(
                    id="socrata-token-input",
                    type="password",
                    placeholder="Optional — increases rate limits",
                    value=os.getenv("SOCRATA_APP_TOKEN", ""),
                    size="sm",
                    style={
                        "background": "var(--bg-tertiary)",
                        "border": "1px solid var(--border-color)",
                        "color": "var(--text-primary)",
                        "fontSize": "0.75rem",
                    },
                ),
                style={"padding": "0 12px 8px"},
            ),

            # DB info
            html.Div(db_badge, style={"padding": "4px 16px 16px"}),
        ],
    )


# ── Root layout ───────────────────────────────────────────────────────────────
app.layout = html.Div(
    id="app-root",
    **{"data-theme": "dark"},
    children=[
        # Global stores
        dcc.Store(id="theme-store",   data="dark",  storage_type="local"),
        dcc.Store(id="token-store",   data=os.getenv("SOCRATA_APP_TOKEN", ""), storage_type="session"),
        dcc.Store(id="session-store", data=None,    storage_type="session"),   # {label, records, columns, table_name}
        dcc.Location(id="url"),

        dbc.Row([
            # Sidebar col
            dbc.Col(build_sidebar(), width=2, style={"padding": 0}),
            # Content col
            dbc.Col(
                html.Div(
                    dash.page_container,
                    id="nyc-content",
                ),
                width=10,
                style={"padding": 0},
            ),
        ], style={"margin": 0, "flexWrap": "nowrap"}),
    ],
)


# ── Theme callback ────────────────────────────────────────────────────────────
@callback(
    Output("app-root",     "data-theme"),
    Output("theme-store",  "data"),
    Output("theme-dark",   "className"),
    Output("theme-light",  "className"),
    Output("theme-sepia",  "className"),
    Input("theme-dark",    "n_clicks"),
    Input("theme-light",   "n_clicks"),
    Input("theme-sepia",   "n_clicks"),
    Input("theme-store",   "data"),
    prevent_initial_call=False,
)
def switch_theme(n_dark, n_light, n_sepia, stored):
    ctx = dash.callback_context
    triggered = ctx.triggered_id if ctx.triggered_id else "theme-store"

    theme_map = {
        "theme-dark":  "dark",
        "theme-light": "light",
        "theme-sepia": "sepia",
        "theme-store": stored or "dark",
    }
    theme = theme_map.get(triggered, "dark")

    def cls(t): return "nyc-theme-btn active" if t == theme else "nyc-theme-btn"
    pio.templates.default = PLOTLY_THEMES.get(theme, "plotly_dark")

    return theme, theme, cls("dark"), cls("light"), cls("sepia")


# ── Token store callback ──────────────────────────────────────────────────────
@callback(
    Output("token-store", "data"),
    Input("socrata-token-input", "value"),
)
def store_token(val):
    return val or ""


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
