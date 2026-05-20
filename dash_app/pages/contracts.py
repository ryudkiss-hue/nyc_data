"""Contract progress and budget from Analyst Pack."""

import json

import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from dash_app.data.analyst_pack import latest_pack_dir, load_manifest, load_pack_file

dash.register_page(__name__, path="/contracts", name="Contracts", order=2)

pack = latest_pack_dir()
manifest = load_manifest(pack)
analytics = {}
if pack and (pack / "contract_analytics.json").exists():
    analytics = json.loads((pack / "contract_analytics.json").read_text(encoding="utf-8"))

progress = analytics.get("progress", [])
budget = analytics.get("budget", {})
productivity = analytics.get("productivity", {})

charts = []
if progress:
    fig = px.bar(
        x=[p.get("contract_id", "?") for p in progress],
        y=[p.get("pct_complete", 0) for p in progress],
        labels={"x": "Contract", "y": "% Complete"},
        title="Contract progress",
        template="plotly_dark",
    )
    fig.update_layout(margin=dict(l=40, r=20, t=40, b=40), height=280)
    charts.append(dcc.Graph(figure=fig, config={"displayModeBar": False}))

if budget:
    cpi = budget.get("cost_performance_index", 0)
    fig2 = go.Figure(
        go.Indicator(
            mode="number+delta",
            value=round(cpi, 2),
            title={"text": "Cost Performance Index (CPI)"},
            delta={"reference": 1.0},
        )
    )
    fig2.update_layout(template="plotly_dark", height=200, margin=dict(l=20, r=20, t=40, b=20))
    charts.append(dcc.Graph(figure=fig2, config={"displayModeBar": False}))

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
    ],
    className="mb-3 g-3",
)

layout = dbc.Container(
    [
        html.H1("Contracts", className="nyc-page-title"),
        html.P(f"Pack date: {manifest.get('run_date', 'n/a')}", className="nyc-page-sub"),
        cards if budget or productivity else html.Div(),
        *charts if charts else [html.P("No contract analytics in latest pack.")],
        html.Hr(),
        html.H2("Status report", style={"fontSize": "1.1rem"}),
        html.Pre(
            load_pack_file("contract_status.md", pack) or "Enable contract_report in analyst profile.",
            style={"whiteSpace": "pre-wrap", "maxHeight": "360px", "overflow": "auto"},
        ),
    ],
    fluid=True,
)
