"""Contract progress and budget from Analyst Pack — interactive EVM exploration."""

import json

import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from dash_app.components.explainers import evm_explainer_diagram
from dash_app.components.interactive import param_checkbox, param_slider, tip_card
from dash_app.components.shell import empty_state, page_shell
from dash_app.data.analyst_pack import latest_pack_dir, load_manifest, load_pack_file
from dash_app.data.pack_loader import load_pack_tables, resolve_pack_dir

dash.register_page(__name__, path="/contracts", name="Contracts", order=3)

pack = latest_pack_dir()
manifest = load_manifest(pack)
_tables = load_pack_tables(pack)
analytics = _tables.get("contract_analytics", {}) if isinstance(_tables.get("contract_analytics"), dict) else {}
if pack and (pack / "contract_analytics.json").exists() and not analytics:
    analytics = json.loads((pack / "contract_analytics.json").read_text(encoding="utf-8"))

progress = analytics.get("progress", [])
budget = analytics.get("budget", {})
productivity = analytics.get("productivity", {})

_has_data = bool(progress or budget or productivity)

layout = dbc.Container(
    [
        *page_shell(
            "Contracts",
            "EVM-style contract progress, budget CPI, and status report from the Analyst Pack.",
            page_key="contracts",
            pack_dir=pack,
            children=[
                evm_explainer_diagram(),
                tip_card(
                    "Reporting window",
                    "Adjust the day window to focus recent contract activity in charts (preview filter on progress rows).",
                    id="contracts-window-tip",
                ),
                (
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    param_slider(
                                        "Reporting window (days)",
                                        7,
                                        365,
                                        7,
                                        90,
                                        "contracts-window-days",
                                        aria_label="Reporting window in days",
                                    ),
                                    md=4,
                                ),
                                dbc.Col(
                                    param_checkbox(
                                        "Show CPI vs productivity chart",
                                        "contracts-show-productivity",
                                        default=True,
                                        aria_label="Toggle productivity comparison chart",
                                    ),
                                    md=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dcc.Loading(
                            type="default",
                            color="var(--accent)",
                            children=[
                                html.Div(id="contracts-cards"),
                                html.Div(id="contracts-charts"),
                            ],
                        ),
                        html.Hr(),
                        html.H2("Status report", style={"fontSize": "1.1rem"}),
                        html.Pre(
                            load_pack_file("contract_status.md", pack)
                            or "Enable contract_report in analyst profile.",
                            style={"whiteSpace": "pre-wrap", "maxHeight": "360px", "overflow": "auto"},
                        ),
                        dcc.Store(id="contracts-analytics-store", data=analytics),
                    ]
                    if _has_data
                    else [
                        empty_state(
                            "No contract analytics in the latest pack — enable contract_report in your analyst profile.",
                            show_demo=False,
                        )
                    ]
                ),
            ],
        ),
    ],
    fluid=True,
)


@callback(
    Output("contracts-analytics-store", "data"),
    Input("pack-route-store", "data"),
    Input("url", "pathname"),
)
def refresh_contracts_analytics(pack_override, pathname):
    if pathname not in ("/contracts",):
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    pack = resolve_pack_dir(pack_override) if pack_override else resolve_pack_dir()
    if not pack:
        return {}
    tables = load_pack_tables(pack)
    analytics = tables.get("contract_analytics", {}) if isinstance(tables.get("contract_analytics"), dict) else {}
    if pack and (pack / "contract_analytics.json").exists() and not analytics:
        analytics = json.loads((pack / "contract_analytics.json").read_text(encoding="utf-8"))
    return analytics


@callback(
    Output("contracts-window-days-value", "children"),
    Input("contracts-window-days", "value"),
)
def contracts_window_label(v):
    return f"{int(v)} days" if v is not None else "—"


@callback(
    Output("contracts-cards", "children"),
    Output("contracts-charts", "children"),
    Input("contracts-analytics-store", "data"),
    Input("contracts-window-days", "value"),
    Input("contracts-show-productivity", "value"),
)
def update_contracts(analytics, window_days, show_prod):
    analytics = analytics or {}
    progress = analytics.get("progress", [])
    budget = analytics.get("budget", {})
    productivity = analytics.get("productivity", {})
    window = int(window_days or 90)

    cards = dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3("Budget", className="h6"),
                            html.P(f"Planned: ${budget.get('total_planned', 0):,.0f}"),
                            html.P(f"Actual: ${budget.get('total_actual', 0):,.0f}"),
                        ]
                    )
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3("Productivity", className="h6"),
                            html.P(f"Sq ft/day: {productivity.get('sqft_per_day', 'n/a')}"),
                            html.P(f"Cost/sq ft: {productivity.get('cost_per_sqft', 'n/a')}"),
                        ]
                    )
                ),
                md=4,
            ),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3("Window", className="h6"),
                            html.P(f"Preview filter: last {window} days"),
                        ]
                    )
                ),
                md=4,
            ),
        ],
        className="mb-3 g-3",
    ) if budget or productivity else html.Div()

    charts = []
    filtered = progress
    if progress and any("days_ago" in p for p in progress):
        filtered = [p for p in progress if int(p.get("days_ago", 0)) <= window]
    elif progress:
        filtered = progress[: max(1, len(progress) * window // 365)]

    if filtered:
        fig = px.bar(
            x=[p.get("contract_id", "?") for p in filtered],
            y=[p.get("pct_complete", 0) for p in filtered],
            labels={"x": "Contract", "y": "% Complete"},
            title=f"Contract progress (≈{window}-day view)",
            template="plotly_dark",
        )
        fig.update_layout(margin=dict(l=40, r=20, t=40, b=40), height=280)
        charts.append(dcc.Graph(figure=fig, config={"displayModeBar": False}))

    if budget:
        cpi = budget.get("cost_performance_index", 0)
        fig2 = go.Figure(
            go.Indicator(
                mode="number+delta",
                value=round(float(cpi), 2),
                title={"text": "Cost Performance Index (CPI)"},
                delta={"reference": 1.0},
            )
        )
        fig2.update_layout(template="plotly_dark", height=200, margin=dict(l=20, r=20, t=40, b=20))
        charts.append(dcc.Graph(figure=fig2, config={"displayModeBar": False}))

    if show_prod and productivity:
        fig3 = go.Figure(
            data=[
                go.Bar(name="CPI ref", x=["CPI"], y=[1.0], marker_color="#4a9eff"),
                go.Bar(
                    name="Productivity index",
                    x=["Sq ft/day"],
                    y=[float(productivity.get("sqft_per_day") or 0) / 100.0],
                    marker_color="#5cdb95",
                ),
            ]
        )
        fig3.update_layout(
            template="plotly_dark",
            height=220,
            title="CPI reference vs productivity (scaled)",
            barmode="group",
        )
        charts.append(dcc.Graph(figure=fig3, config={"displayModeBar": False}))

    if not charts:
        charts = [html.P("No contract analytics in latest pack.")]
    return cards, charts
