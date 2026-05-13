"""dash_app/pages/settings.py — System health, credentials, module status"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import importlib, platform

from dash_app.data import db

dash.register_page(__name__, path="/settings", name="Settings", order=99)

CORE_DEPS = ["dash", "plotly", "duckdb", "pandas", "dask", "requests", "tenacity", "pydantic"]
OPT_DEPS  = ["streamlit_folium", "shapely", "sklearn", "psycopg", "langchain_core",
             "qiskit", "openpyxl", "scipy", "numpy", "pyarrow"]

TOOLKIT_MODULES = [
    ("socrata_toolkit.core",       "core"),
    ("socrata_toolkit.analysis",   "analysis"),
    ("socrata_toolkit.engineering","engineering"),
    ("socrata_toolkit.pipeline",   "pipeline"),
    ("socrata_toolkit.governance", "governance"),
    ("socrata_toolkit.spatial",    "spatial"),
    ("socrata_toolkit.ai",         "ai"),
    ("socrata_toolkit.cleaning",   "cleaning"),
    ("socrata_toolkit.cli",        "cli"),
]

def _check(mod: str) -> bool:
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False

def _badge(ok: bool) -> html.Span:
    if ok:
        return html.Span("✅ OK",    className="nyc-pill nyc-pill-green ms-2")
    return html.Span("❌ missing", className="nyc-pill nyc-pill-red ms-2")


layout = dbc.Container([
    html.Div([
        html.H1("⚙️ Settings", className="nyc-page-title"),
        html.P("Manage credentials, inspect module health, and monitor the DuckDB connection.", className="nyc-page-sub"),
    ], className="nyc-page-header"),

    dbc.Row([
        # Left column
        dbc.Col([
            # API Credentials
            dbc.Card([
                dbc.CardHeader("🔑 API Credentials"),
                dbc.CardBody([
                    dbc.Label("Socrata App Token", style={"fontSize": "0.8rem", "fontWeight": 600}),
                    dbc.Input(id="cfg-socrata-token", type="password",
                              value=os.getenv("SOCRATA_APP_TOKEN", ""),
                              placeholder="Increases Socrata rate limits", className="mb-3"),
                    dbc.Label("OpenAI API Key", style={"fontSize": "0.8rem", "fontWeight": 600}),
                    dbc.Input(id="cfg-openai-key", type="password",
                              value=os.getenv("OPENAI_API_KEY", ""),
                              placeholder="Required for NL→SQL", className="mb-3"),
                    dbc.Label("MotherDuck Token", style={"fontSize": "0.8rem", "fontWeight": 600}),
                    dbc.Input(id="cfg-motherduck", type="password",
                              value=os.getenv("MOTHERDUCK_TOKEN", ""),
                              placeholder="Enables cloud DuckDB"),
                ]),
            ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)", "marginBottom": "16px"}),

            # Database info
            dbc.Card([
                dbc.CardHeader("🦆 Database"),
                dbc.CardBody([
                    html.P([
                        html.Strong("Backend: "),
                        "☁️ MotherDuck" if db.is_motherduck() else "💾 Local DuckDB",
                    ], style={"fontSize": "0.85rem"}),
                    html.Div(id="cfg-db-info"),
                    dbc.Button("🔄 Refresh", id="cfg-refresh-db", color="secondary", outline=True, size="sm", className="mt-2"),
                ]),
            ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"}),
        ], md=5),

        # Right column — health check
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    "🩺 System Health ",
                    dbc.Button("Run Doctor", id="cfg-run-doctor", color="primary", size="sm", className="ms-2"),
                ]),
                dbc.CardBody(html.Div(id="cfg-doctor-results",
                                      children=html.P("Click 'Run Doctor' to check all dependencies.",
                                                       style={"color": "var(--text-muted)", "fontSize": "0.82rem"}))),
            ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)", "marginBottom": "16px"}),

            dbc.Card([
                dbc.CardHeader("📦 Toolkit Modules"),
                dbc.CardBody(html.Div(id="cfg-toolkit-status",
                                      children=html.P("Click 'Run Doctor' above.",
                                                       style={"color": "var(--text-muted)", "fontSize": "0.82rem"}))),
            ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"}),
        ], md=7),
    ]),

    html.Div(className="divider-nyc"),
    html.P([
        html.Strong("Platform: "), platform.system(), " ", platform.release(), " | ",
        html.Strong("Python: "), platform.python_version(),
    ], style={"fontSize": "0.75rem", "color": "var(--text-muted)"}),
], fluid=True)


@callback(Output("cfg-db-info", "children"), Input("cfg-refresh-db", "n_clicks"))
def refresh_db(_):
    tables = db.list_tables()
    rows   = [{"Table": t, "Rows": f"{db.table_row_count(t):,}"} for t in tables]
    if not rows:
        return html.P("No tables.", style={"color": "var(--text-muted)", "fontSize": "0.82rem"})
    return html.Ul([html.Li(f"{r['Table']} ({r['Rows']} rows)",
                             style={"fontSize": "0.8rem", "color": "var(--text-primary)"}) for r in rows])


@callback(
    Output("cfg-doctor-results", "children"),
    Output("cfg-toolkit-status", "children"),
    Input("cfg-run-doctor", "n_clicks"),
    prevent_initial_call=True,
)
def run_doctor(_):
    def _row(name, ok):
        return html.Div([
            html.Code(name, style={"fontSize": "0.78rem"}),
            _badge(ok),
        ], style={"marginBottom": "4px"})

    core_rows = [_row(m, _check(m)) for m in CORE_DEPS]
    opt_rows  = [_row(m, _check(m)) for m in OPT_DEPS]

    doctor = html.Div([
        html.P("Core", style={"fontWeight": 700, "fontSize": "0.8rem", "color": "var(--text-muted)", "marginBottom": "4px"}),
        *core_rows,
        html.Hr(style={"borderColor": "var(--border-color)", "margin": "8px 0"}),
        html.P("Optional", style={"fontWeight": 700, "fontSize": "0.8rem", "color": "var(--text-muted)", "marginBottom": "4px"}),
        *opt_rows,
    ])

    toolkit_rows = [_row(label, _check(mod)) for mod, label in TOOLKIT_MODULES]
    toolkit = html.Div(toolkit_rows)

    return doctor, toolkit
