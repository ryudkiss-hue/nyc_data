"""Settings — UI preferences, credentials, module health."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import importlib
import platform

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from dash_app.components.shell import page_shell
from dash_app.data import db
from dash_app.data.analyst_pack import list_configured_roles, load_role_kpi_dashboard
from dash_app.data.ui_prefs import export_all_prefs, import_all_prefs, load_ui_prefs, save_ui_prefs

dash.register_page(__name__, path="/settings", name="Settings", order=5)

CORE_DEPS = ["dash", "plotly", "duckdb", "pandas", "dask", "requests", "tenacity", "pydantic"]
OPT_DEPS = [
    "streamlit_folium",
    "shapely",
    "sklearn",
    "psycopg",
    "langchain_core",
    "openpyxl",
    "scipy",
    "numpy",
    "pyarrow",
]

TOOLKIT_MODULES = [
    ("socrata_toolkit.core", "core"),
    ("socrata_toolkit.analysis", "analysis"),
    ("socrata_toolkit.engineering", "engineering"),
    ("socrata_toolkit.pipeline", "pipeline"),
    ("socrata_toolkit.governance", "governance"),
    ("socrata_toolkit.spatial", "spatial"),
    ("socrata_toolkit.ai", "ai"),
    ("socrata_toolkit.cleaning", "cleaning"),
    ("socrata_toolkit.cli", "cli"),
]

_prefs = load_ui_prefs()
_theme = _prefs.get("theme", "dark")
_font_scale = _prefs.get("font_scale", "normal")
_offline = bool(_prefs.get("offline_mode", False))


def _check(mod: str) -> bool:
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def _badge(ok: bool) -> html.Span:
    if ok:
        return html.Span("OK", className="nyc-pill nyc-pill-green ms-2")
    return html.Span("missing", className="nyc-pill nyc-pill-red ms-2")


def _role_kpi_panel() -> html.Div:
    roles = list_configured_roles()
    pack_role = load_role_kpi_dashboard()
    items = []
    for r in roles:
        jid = r.get("jid") or "—"
        active = pack_role.get("role_id") == r.get("role_id")
        badge = html.Span(" active pack", className="nyc-pill nyc-pill-green ms-1") if active else None
        items.append(
            html.Li(
                [html.Strong(r["display_name"]), f" (jid-{jid})", badge],
                style={"fontSize": "0.82rem", "marginBottom": "4px"},
            )
        )
    if not items:
        return html.P(
            "No config/role_profiles/*.yaml found.",
            style={"fontSize": "0.82rem", "color": "var(--text-muted)"},
        )
    hint = html.P(
        "Set role: sw_project_analyst in config/analyst_profile.yaml for jid-42159 duties.",
        style={"fontSize": "0.75rem", "color": "var(--text-muted)", "marginTop": "8px"},
    )
    return html.Div([html.Ul(items), hint])


def _readiness_card() -> dbc.Card:
    from socrata_toolkit.core.readiness import run_readiness_checks

    report = run_readiness_checks()
    rows = []
    for axis, score in sorted(report.get("axis_scores", {}).items()):
        pct = min(100.0, float(score))
        rows.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(axis.replace("_", " ").title(), style={"fontWeight": 600}),
                            html.Span(f"{pct:.0f}%", style={"float": "right"}),
                        ],
                        style={"fontSize": "0.82rem", "marginBottom": "4px"},
                    ),
                    html.Div(
                        html.Div(className="nyc-readiness-fill", style={"width": f"{pct}%"}),
                        className="nyc-readiness-bar",
                        **{"aria-label": f"{axis} readiness {pct:.0f} percent"},
                    ),
                ],
                className="mb-3",
            )
        )
    overall = report.get("overall_score", 0)
    return dbc.Card(
        [
            dbc.CardHeader("Quality readiness"),
            dbc.CardBody(
                [
                    html.P(
                        f"Overall automated score: {overall:.0f}% — run `socrata readiness` for full JSON.",
                        style={"fontSize": "0.85rem"},
                    ),
                    *rows,
                    html.P(
                        report.get("note", ""),
                        style={"fontSize": "0.75rem", "color": "var(--text-muted)", "marginTop": "8px"},
                    ),
                ]
            ),
        ],
        style={
            "background": "var(--bg-secondary)",
            "border": "1px solid var(--border-color)",
            "marginBottom": "16px",
        },
    )


def _ui_prefs_card() -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader("Appearance & offline"),
            dbc.CardBody(
                [
                    dbc.Label("Theme", style={"fontSize": "0.8rem", "fontWeight": 600}),
                    dbc.RadioItems(
                        id="set-theme",
                        options=[
                            {"label": "Dark", "value": "dark"},
                            {"label": "Light", "value": "light"},
                        ],
                        value=_theme if _theme in ("dark", "light") else "dark",
                        inline=True,
                        className="mb-3",
                    ),
                    dbc.Label("Font scale", style={"fontSize": "0.8rem", "fontWeight": 600}),
                    dbc.RadioItems(
                        id="set-font-scale",
                        options=[
                            {"label": "Normal", "value": "normal"},
                            {"label": "Large", "value": "large"},
                        ],
                        value=_font_scale,
                        inline=True,
                        className="mb-3 nyc-scale-radios",
                    ),
                    dbc.Checklist(
                        id="set-offline-mode",
                        options=[{"label": "Offline mode (skip live Socrata on pack run)", "value": "on"}],
                        value=["on"] if _offline else [],
                        switch=True,
                        className="mb-3",
                    ),
                    html.Hr(style={"borderColor": "var(--border-color)"}),
                    dbc.Label("Export / import preferences", style={"fontSize": "0.8rem", "fontWeight": 600}),
                    html.Div(
                        [
                            html.Button("Export JSON", id="set-export-prefs", className="nyc-btn-secondary me-2"),
                            dcc.Upload(
                                id="set-import-upload",
                                children=html.Button("Import JSON", className="nyc-btn-secondary"),
                                multiple=False,
                            ),
                        ],
                        className="mb-2",
                    ),
                    dcc.Download(id="set-download-prefs"),
                    html.Pre(id="set-prefs-msg", className="nyc-explore-snippet"),
                    html.Hr(style={"borderColor": "var(--border-color)"}),
                    html.P("First-time setup:", style={"fontSize": "0.85rem"}),
                    html.Code("socrata setup-wizard", style={"display": "block", "marginBottom": "8px"}),
                    html.A(
                        "WINDOWS_INSTALLER.md",
                        href=f"file:///{str(Path(__file__).resolve().parents[2] / 'docs' / 'WINDOWS_INSTALLER.md').replace(chr(92), '/')}",
                        target="_blank",
                        className="nyc-nav-link",
                    ),
                ]
            ),
        ],
        style={
            "background": "var(--bg-secondary)",
            "border": "1px solid var(--border-color)",
            "marginBottom": "16px",
        },
    )


layout = dbc.Container(
    [
        *page_shell(
            "Settings",
            "Theme, offline mode, credentials, and system health.",
            page_key="settings",
            children=[
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                _readiness_card(),
                                _ui_prefs_card(),
                                dbc.Card(
                                    [
                                        dbc.CardHeader("API Credentials"),
                                        dbc.CardBody(
                                            [
                                                dbc.Label("Socrata App Token", style={"fontSize": "0.8rem", "fontWeight": 600}),
                                                dbc.Input(
                                                    id="cfg-socrata-token",
                                                    type="password",
                                                    value=os.getenv("SOCRATA_APP_TOKEN", ""),
                                                    placeholder="Increases Socrata rate limits",
                                                    className="mb-3",
                                                ),
                                                dbc.Label("OpenAI API Key", style={"fontSize": "0.8rem", "fontWeight": 600}),
                                                dbc.Input(
                                                    id="cfg-openai-key",
                                                    type="password",
                                                    value=os.getenv("OPENAI_API_KEY", ""),
                                                    placeholder="Required for NL→SQL",
                                                    className="mb-3",
                                                ),
                                                dbc.Label("MotherDuck Token", style={"fontSize": "0.8rem", "fontWeight": 600}),
                                                dbc.Input(
                                                    id="cfg-motherduck",
                                                    type="password",
                                                    value=os.getenv("MOTHERDUCK_TOKEN", ""),
                                                    placeholder="Enables cloud DuckDB",
                                                ),
                                            ]
                                        ),
                                    ],
                                    style={
                                        "background": "var(--bg-secondary)",
                                        "border": "1px solid var(--border-color)",
                                        "marginBottom": "16px",
                                    },
                                ),
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Database"),
                                        dbc.CardBody(
                                            [
                                                html.P(
                                                    [
                                                        html.Strong("Backend: "),
                                                        "MotherDuck" if db.is_motherduck() else "Local DuckDB",
                                                    ],
                                                    style={"fontSize": "0.85rem"},
                                                ),
                                                html.Div(id="cfg-db-info"),
                                                dbc.Button(
                                                    "Refresh",
                                                    id="cfg-refresh-db",
                                                    color="secondary",
                                                    outline=True,
                                                    size="sm",
                                                    className="mt-2",
                                                ),
                                            ]
                                        ),
                                    ],
                                    style={
                                        "background": "var(--bg-secondary)",
                                        "border": "1px solid var(--border-color)",
                                    },
                                ),
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Team / role KPIs"),
                                        dbc.CardBody(id="cfg-role-kpis", children=_role_kpi_panel()),
                                    ],
                                    style={
                                        "background": "var(--bg-secondary)",
                                        "border": "1px solid var(--border-color)",
                                        "marginTop": "16px",
                                    },
                                ),
                            ],
                            md=5,
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardHeader(
                                            [
                                                "System Health ",
                                                dbc.Button(
                                                    "Run Doctor",
                                                    id="cfg-run-doctor",
                                                    color="primary",
                                                    size="sm",
                                                    className="ms-2",
                                                ),
                                            ]
                                        ),
                                        dbc.CardBody(
                                            html.Div(
                                                id="cfg-doctor-results",
                                                children=html.P(
                                                    "Click 'Run Doctor' to check all dependencies.",
                                                    style={"color": "var(--text-muted)", "fontSize": "0.82rem"},
                                                ),
                                            )
                                        ),
                                    ],
                                    style={
                                        "background": "var(--bg-secondary)",
                                        "border": "1px solid var(--border-color)",
                                        "marginBottom": "16px",
                                    },
                                ),
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Toolkit Modules"),
                                        dbc.CardBody(
                                            html.Div(
                                                id="cfg-toolkit-status",
                                                children=html.P(
                                                    "Click 'Run Doctor' above.",
                                                    style={"color": "var(--text-muted)", "fontSize": "0.82rem"},
                                                ),
                                            )
                                        ),
                                    ],
                                    style={
                                        "background": "var(--bg-secondary)",
                                        "border": "1px solid var(--border-color)",
                                    },
                                ),
                            ],
                            md=7,
                        ),
                    ]
                ),
                dbc.Card(
                    [
                        dbc.CardHeader("Interactive exploration"),
                        dbc.CardBody(
                            html.Ul(
                                [
                                    html.Li(dcc.Link("Explore (what-if sandbox)", href="/explore")),
                                    html.Li(
                                        html.A(
                                            "USER_MANUAL — Interactive exploration",
                                            href=f"file:///{str(Path(__file__).resolve().parents[2] / 'docs' / 'USER_MANUAL.md').replace(chr(92), '/')}",
                                            target="_blank",
                                        )
                                    ),
                                ],
                                style={"fontSize": "0.82rem"},
                            )
                        ),
                    ],
                    style={
                        "background": "var(--bg-secondary)",
                        "border": "1px solid var(--border-color)",
                        "marginTop": "16px",
                    },
                ),
                html.Div(className="divider-nyc"),
                html.P(
                    [
                        html.Strong("Platform: "),
                        platform.system(),
                        " ",
                        platform.release(),
                        " | ",
                        html.Strong("Python: "),
                        platform.python_version(),
                    ],
                    style={"fontSize": "0.75rem", "color": "var(--text-muted)"},
                ),
            ],
        ),
    ],
    fluid=True,
)


@callback(
    Output("ui-prefs-store", "data"),
    Output("offline-banner-store", "data"),
    Input("set-theme", "value"),
    Input("set-font-scale", "value"),
    Input("set-offline-mode", "value"),
)
def persist_ui_prefs(theme, font_scale, offline_vals):
    prefs = load_ui_prefs()
    prefs["theme"] = theme or "dark"
    prefs["font_scale"] = font_scale or "normal"
    prefs["offline_mode"] = bool(offline_vals and "on" in offline_vals)
    save_ui_prefs(prefs)
    return prefs, prefs["offline_mode"]


@callback(
    Output("set-download-prefs", "data"),
    Input("set-export-prefs", "n_clicks"),
    prevent_initial_call=True,
)
def export_prefs(_):
    return dict(content=json.dumps(export_all_prefs(), indent=2), filename="nyc_dot_ui_prefs.json")


@callback(
    Output("set-prefs-msg", "children"),
    Output("ui-prefs-store", "data", allow_duplicate=True),
    Input("set-import-upload", "contents"),
    State("set-import-upload", "filename"),
    prevent_initial_call=True,
)
def import_prefs(contents, filename):
    if not contents:
        return "No file uploaded.", no_update
    import base64

    try:
        _, b64 = contents.split(",", 1)
        data = json.loads(base64.b64decode(b64).decode("utf-8"))
        import_all_prefs(data)
        prefs = load_ui_prefs()
        return f"Imported {filename or 'preferences'}. Reload may apply theme to charts.", prefs
    except Exception as exc:
        return f"Import failed: {exc}", no_update


@callback(Output("cfg-db-info", "children"), Input("cfg-refresh-db", "n_clicks"))
def refresh_db(_):
    tables = db.list_tables()
    rows = [{"Table": t, "Rows": f"{db.table_row_count(t):,}"} for t in tables]
    if not rows:
        return html.P("No tables.", style={"color": "var(--text-muted)", "fontSize": "0.82rem"})
    return html.Ul(
        [
            html.Li(
                f"{r['Table']} ({r['Rows']} rows)",
                style={"fontSize": "0.8rem", "color": "var(--text-primary)"},
            )
            for r in rows
        ]
    )


@callback(
    Output("cfg-doctor-results", "children"),
    Output("cfg-toolkit-status", "children"),
    Input("cfg-run-doctor", "n_clicks"),
    prevent_initial_call=True,
)
def run_doctor(_):
    def _row(name, ok):
        return html.Div(
            [html.Code(name, style={"fontSize": "0.78rem"}), _badge(ok)],
            style={"marginBottom": "4px"},
        )

    core_rows = [_row(m, _check(m)) for m in CORE_DEPS]
    opt_rows = [_row(m, _check(m)) for m in OPT_DEPS]
    doctor = html.Div(
        [
            html.P("Core", style={"fontWeight": 700, "fontSize": "0.8rem", "color": "var(--text-muted)"}),
            *core_rows,
            html.Hr(style={"borderColor": "var(--border-color)", "margin": "8px 0"}),
            html.P("Optional", style={"fontWeight": 700, "fontSize": "0.8rem", "color": "var(--text-muted)"}),
            *opt_rows,
        ]
    )
    toolkit_rows = [_row(label, _check(mod)) for mod, label in TOOLKIT_MODULES]
    return doctor, html.Div(toolkit_rows)
