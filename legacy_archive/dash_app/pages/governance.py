"""dash_app/pages/governance.py — Data quality, schema, SLA, freshness, anomalies"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, dcc, html

from dash_app.data import db
from dash_app.pages._env import legacy_pages_enabled

if legacy_pages_enabled():
    dash.register_page(__name__, path="/governance", name="Governance", order=50)

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("🔬 Governance & Quality", className="nyc-page-title"),
                html.P(
                    "Data quality scorecards, schema drift detection, SLA tracking, and freshness monitoring.",
                    className="nyc-page-sub",
                ),
            ],
            className="nyc-page-header",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label(
                            "Dataset",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Dropdown(
                            id="gov-table-sel",
                            placeholder="Select a DuckDB table…",
                            style={"background": "var(--bg-secondary)"},
                        ),
                    ],
                    md=5,
                ),
                dbc.Col(
                    dbc.Button("Analyse", id="gov-analyse-btn", color="primary", className="mt-4"),
                    md=2,
                ),
            ],
            className="mb-3",
        ),
        dcc.Loading(html.Div(id="gov-output"), type="circle", color="var(--accent)"),
    ],
    fluid=True,
)


@callback(Output("gov-table-sel", "options"), Input("session-store", "data"))
def populate(_):
    return [{"label": t, "value": t} for t in db.list_tables()]


@callback(
    Output("gov-output", "children"),
    Input("gov-analyse-btn", "n_clicks"),
    State("gov-table-sel", "value"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)
def analyse(_, table, theme):
    if not table:
        return dbc.Alert("Select a table first.", color="warning")
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(
        theme or "dark", "plotly_dark"
    )
    try:
        df = db.query_df(f'SELECT * FROM "{table}" LIMIT 50000')
    except Exception as e:
        return dbc.Alert(f"❌ {e}", color="danger")

    num_cols = df.select_dtypes("number").columns.tolist()
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]

    # Scores
    completeness = round((1 - df.isnull().mean().mean()) * 100, 1)
    uniqueness = round((df.nunique() / max(len(df), 1)).mean() * 100, 1)
    validity = round(min(completeness, uniqueness), 1)
    overall = round((completeness + uniqueness + validity) / 3, 1)

    score_cards = dbc.Row(
        [
            dbc.Col(
                html.Div(
                    [
                        html.Div(f"{overall}", className="nyc-metric-value"),
                        html.Div("Overall", className="nyc-metric-label"),
                    ],
                    className="nyc-metric",
                ),
                md=3,
            ),
            dbc.Col(
                html.Div(
                    [
                        html.Div(f"{completeness}%", className="nyc-metric-value"),
                        html.Div("Completeness", className="nyc-metric-label"),
                    ],
                    className="nyc-metric",
                ),
                md=3,
            ),
            dbc.Col(
                html.Div(
                    [
                        html.Div(f"{uniqueness}%", className="nyc-metric-value"),
                        html.Div("Uniqueness", className="nyc-metric-label"),
                    ],
                    className="nyc-metric",
                ),
                md=3,
            ),
            dbc.Col(
                html.Div(
                    [
                        html.Div(f"{validity}%", className="nyc-metric-value"),
                        html.Div("Validity", className="nyc-metric-label"),
                    ],
                    className="nyc-metric",
                ),
                md=3,
            ),
        ],
        className="mb-3",
    )

    # Progress bar
    prog_color = "success" if overall >= 80 else ("warning" if overall >= 60 else "danger")
    progress = dbc.Progress(
        value=overall,
        label=f"{overall}/100",
        color=prog_color,
        className="mb-3",
        style={"height": "20px"},
    )

    # Null % chart
    null_df = pd.DataFrame(
        {
            "column": df.columns,
            "null_pct": (df.isnull().mean() * 100).round(1),
        }
    ).sort_values("null_pct", ascending=False)
    fig_null = px.bar(
        null_df,
        x="column",
        y="null_pct",
        title="Null % per Column",
        template=tmpl,
        height=260,
        color="null_pct",
        color_continuous_scale="Reds",
    )
    fig_null.update_layout(
        margin=dict(l=0, r=0, t=36, b=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    # Freshness
    freshness_section = html.Div()
    if date_cols:
        dc = date_cols[0]
        try:
            dates = pd.to_datetime(df[dc], errors="coerce").dropna()
            if not dates.empty:
                from datetime import datetime

                last = dates.max()
                age = (datetime.now() - last.to_pydatetime().replace(tzinfo=None)).days
                f_status = "🟢 Fresh" if age < 7 else ("🟡 Stale" if age < 30 else "🔴 Very Stale")
                freshness_section = html.Div(
                    [
                        html.H6(
                            "📅 Data Freshness", style={"fontWeight": 700, "marginTop": "16px"}
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Div(
                                        [
                                            html.Div(
                                                str(last.date()),
                                                className="nyc-metric-value",
                                                style={"fontSize": "1.1rem"},
                                            ),
                                            html.Div("Last Record", className="nyc-metric-label"),
                                        ],
                                        className="nyc-metric",
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div(
                                        [
                                            html.Div(str(age), className="nyc-metric-value"),
                                            html.Div("Days Old", className="nyc-metric-label"),
                                        ],
                                        className="nyc-metric",
                                    ),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div(
                                        [
                                            html.Div(
                                                f_status,
                                                className="nyc-metric-value",
                                                style={"fontSize": "1rem"},
                                            ),
                                            html.Div("Status", className="nyc-metric-label"),
                                        ],
                                        className="nyc-metric",
                                    ),
                                    md=3,
                                ),
                            ]
                        ),
                    ]
                )
        except Exception:
            pass

    # Schema table
    schema_df = pd.DataFrame(
        {
            "Column": df.columns,
            "Type": df.dtypes.astype(str).values,
            "Null %": (df.isnull().mean() * 100).round(1).values,
            "Unique": df.nunique().values,
            "Sample": [
                str(df[c].dropna().iloc[0]) if df[c].notna().any() else "" for c in df.columns
            ],
        }
    )
    schema_grid = dag.AgGrid(
        rowData=schema_df.to_dict("records"),
        columnDefs=[
            {"field": c, "sortable": True, "filter": True, "resizable": True}
            for c in schema_df.columns
        ],
        defaultColDef={"minWidth": 80},
        dashGridOptions={"domLayout": "autoHeight"},
        className="ag-theme-alpine-dark",
        style={"width": "100%"},
    )

    return html.Div(
        [
            score_cards,
            progress,
            dcc.Graph(figure=fig_null, config={"displayModeBar": False}),
            freshness_section,
            html.H6(
                "📋 Schema", style={"fontWeight": 700, "marginTop": "16px", "marginBottom": "8px"}
            ),
            schema_grid,
        ]
    )
