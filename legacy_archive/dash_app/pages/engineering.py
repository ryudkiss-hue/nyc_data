"""dash_app/pages/engineering.py — Schema registry, cost estimation, contractor scorecards"""

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
    dash.register_page(__name__, path="/engineering", name="Engineering", order=56)

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("🛠️ Engineering", className="nyc-page-title"),
                html.P(
                    "Schema registry browser, DuckDB table insights, cost estimation, and contractor scorecards.",
                    className="nyc-page-sub",
                ),
            ],
            className="nyc-page-header",
        ),
        dbc.Tabs(
            [
                dbc.Tab(label="📋 Schema Registry", tab_id="schema"),
                dbc.Tab(label="💰 Cost Estimator", tab_id="cost"),
                dbc.Tab(label="🏆 Scorecards", tab_id="scores"),
                dbc.Tab(label="📊 Data Profile", tab_id="profile"),
            ],
            id="eng-tabs",
            active_tab="schema",
            className="nyc-tabs mb-3",
        ),
        html.Div(id="eng-content"),
    ],
    fluid=True,
)


@callback(
    Output("eng-content", "children"),
    Input("eng-tabs", "active_tab"),
    Input("session-store", "data"),
)
def render(tab, _):
    tables = [{"label": t, "value": t} for t in db.list_tables()]

    if tab == "schema":
        rows = []
        for t in db.list_tables():
            try:
                schema = db.table_schema(t)
                cnt = db.table_row_count(t)
                for _, r in schema.iterrows():
                    rows.append(
                        {
                            "Table": t,
                            "Column": r.get("column_name", ""),
                            "Type": r.get("column_type", ""),
                            "Null?": r.get("null", ""),
                            "Rows": cnt,
                        }
                    )
            except Exception:
                pass
        if not rows:
            return dbc.Alert(
                "No tables in DuckDB yet. Load a dataset from the Dashboard.", color="info"
            )
        return dag.AgGrid(
            rowData=rows,
            columnDefs=[
                {"field": c, "sortable": True, "filter": True, "resizable": True}
                for c in ["Table", "Column", "Type", "Null?", "Rows"]
            ],
            defaultColDef={"minWidth": 80},
            dashGridOptions={"pagination": True, "paginationPageSize": 30},
            className="ag-theme-alpine-dark",
            style={"height": "520px", "width": "100%"},
        )

    if tab == "cost":
        return html.Div(
            [
                html.P(
                    "Estimate project cost based on scope, materials, and crew size.",
                    style={"color": "var(--text-muted)", "fontSize": "0.85rem"},
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Project type"),
                                dcc.Dropdown(
                                    id="eng-proj-type",
                                    options=[
                                        {"label": "Sidewalk Repair", "value": 150},
                                        {"label": "Pothole Fill", "value": 80},
                                        {"label": "Bridge Inspection", "value": 5000},
                                        {"label": "Signal Install", "value": 12000},
                                        {"label": "Road Resurfacing", "value": 350},
                                        {"label": "Bike Lane Paint", "value": 200},
                                    ],
                                    value=150,
                                    clearable=False,
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label("Sq ft / Units"),
                                dbc.Input(id="eng-units", type="number", value=100, size="sm"),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            [
                                html.Label("Crew size"),
                                dbc.Input(id="eng-crew", type="number", value=4, size="sm"),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            [
                                html.Label("Days"),
                                dbc.Input(id="eng-days", type="number", value=2, size="sm"),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            [
                                html.Div(style={"height": "22px"}),
                                dbc.Button(
                                    "Estimate", id="eng-cost-btn", color="success", size="sm"
                                ),
                            ],
                            md=2,
                        ),
                    ],
                    className="mb-3",
                ),
                dcc.Loading(html.Div(id="eng-cost-result"), type="dot"),
            ]
        )

    if tab == "scores":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Dataset (for scoring)"),
                                dcc.Dropdown(
                                    id="eng-score-table",
                                    options=tables,
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=5,
                        ),
                        dbc.Col(
                            [
                                html.Label("Contractor column"),
                                dcc.Dropdown(
                                    id="eng-contractor-col",
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Div(style={"height": "22px"}),
                                dbc.Button("Score", id="eng-score-btn", color="primary", size="sm"),
                            ],
                            md=3,
                        ),
                    ],
                    className="mb-3",
                ),
                dcc.Loading(html.Div(id="eng-scores-result"), type="dot"),
            ]
        )

    if tab == "profile":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Table"),
                                dcc.Dropdown(
                                    id="eng-profile-table",
                                    options=tables,
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=5,
                        ),
                        dbc.Col(
                            [
                                html.Div(style={"height": "22px"}),
                                dbc.Button(
                                    "Profile", id="eng-profile-btn", color="info", size="sm"
                                ),
                            ],
                            md=2,
                        ),
                    ],
                    className="mb-3",
                ),
                dcc.Loading(html.Div(id="eng-profile-result"), type="dot"),
            ]
        )
    return html.Div()


@callback(
    Output("eng-cost-result", "children"),
    Input("eng-cost-btn", "n_clicks"),
    State("eng-proj-type", "value"),
    State("eng-units", "value"),
    State("eng-crew", "value"),
    State("eng-days", "value"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)
def estimate_cost(_, unit_cost, units, crew, days, theme):
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(
        theme or "dark", "plotly_dark"
    )
    uc, u, c, d = float(unit_cost or 150), int(units or 100), int(crew or 4), int(days or 2)
    materials = uc * u
    labour = c * d * 8 * 75  # $75/hr per worker
    overhead = (materials + labour) * 0.15
    contingency = (materials + labour) * 0.10
    total = materials + labour + overhead + contingency
    breakdown = pd.DataFrame(
        {
            "Item": ["Materials", "Labour", "Overhead (15%)", "Contingency (10%)", "TOTAL"],
            "Cost": [materials, labour, overhead, contingency, total],
        }
    )
    fig = px.bar(
        breakdown[:-1],
        x="Item",
        y="Cost",
        template=tmpl,
        height=280,
        title="Cost Breakdown",
        color="Cost",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=36, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(f"${materials:,.0f}", className="nyc-metric-value"),
                                html.Div("Materials", className="nyc-metric-label"),
                            ],
                            className="nyc-metric",
                        ),
                        md=3,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(f"${labour:,.0f}", className="nyc-metric-value"),
                                html.Div("Labour", className="nyc-metric-label"),
                            ],
                            className="nyc-metric",
                        ),
                        md=3,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    f"${total:,.0f}",
                                    className="nyc-metric-value",
                                    style={"color": "var(--accent)"},
                                ),
                                html.Div("TOTAL", className="nyc-metric-label"),
                            ],
                            className="nyc-metric",
                        ),
                        md=3,
                    ),
                ],
                className="mb-3",
            ),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ]
    )


@callback(
    Output("eng-contractor-col", "options"),
    Input("eng-score-table", "value"),
    prevent_initial_call=True,
)
def populate_contractor_col(table):
    if not table:
        return []
    df = db.query_df(f'SELECT * FROM "{table}" LIMIT 1')
    return [{"label": c, "value": c} for c in df.select_dtypes("object").columns]


@callback(
    Output("eng-scores-result", "children"),
    Input("eng-score-btn", "n_clicks"),
    State("eng-score-table", "value"),
    State("eng-contractor-col", "value"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)
def score_contractors(_, table, col, theme):
    if not table or not col:
        return dbc.Alert("Select table and contractor column.", color="warning")
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(
        theme or "dark", "plotly_dark"
    )
    df = db.query_df(f'SELECT * FROM "{table}"')
    counts = df[col].value_counts().reset_index()
    counts.columns = [col, "job_count"]
    num_cols = df.select_dtypes("number").columns.tolist()
    if num_cols:
        avg_val = df.groupby(col)[num_cols[0]].mean().reset_index()
        avg_val.columns = [col, "avg_value"]
        counts = counts.merge(avg_val, on=col, how="left")
    counts["score"] = (counts["job_count"] / counts["job_count"].max() * 100).round(1)
    counts = counts.sort_values("score", ascending=False).head(20)
    fig = px.bar(
        counts,
        x=col,
        y="score",
        template=tmpl,
        height=320,
        title="Contractor Scores",
        color="score",
        color_continuous_scale="RdYlGn",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=36, b=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return html.Div(
        [
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
            dag.AgGrid(
                rowData=counts.to_dict("records"),
                columnDefs=[
                    {"field": c, "sortable": True, "resizable": True} for c in counts.columns
                ],
                dashGridOptions={"domLayout": "autoHeight"},
                className="ag-theme-alpine-dark",
                style={"width": "100%", "marginTop": "12px"},
            ),
        ]
    )


@callback(
    Output("eng-profile-result", "children"),
    Input("eng-profile-btn", "n_clicks"),
    State("eng-profile-table", "value"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)
def profile(_, table, theme):
    if not table:
        return dbc.Alert("Select a table.", color="warning")
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(
        theme or "dark", "plotly_dark"
    )
    df = db.query_df(f'SELECT * FROM "{table}" LIMIT 50000')
    prof = pd.DataFrame(
        {
            "Column": df.columns,
            "Type": df.dtypes.astype(str).values,
            "Null %": (df.isnull().mean() * 100).round(1).values,
            "Unique": df.nunique().values,
            "Min": [str(df[c].min()) for c in df.columns],
            "Max": [str(df[c].max()) for c in df.columns],
            "Sample": [
                str(df[c].dropna().iloc[0])[:40] if df[c].notna().any() else "" for c in df.columns
            ],
        }
    )
    fig = px.bar(
        prof,
        x="Column",
        y="Null %",
        template=tmpl,
        height=260,
        title="Null % per Column",
        color="Null %",
        color_continuous_scale="Reds",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=36, b=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return html.Div(
        [
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
            dag.AgGrid(
                rowData=prof.to_dict("records"),
                columnDefs=[
                    {"field": c, "sortable": True, "filter": True, "resizable": True}
                    for c in prof.columns
                ],
                defaultColDef={"minWidth": 80},
                dashGridOptions={"domLayout": "autoHeight"},
                className="ag-theme-alpine-dark",
                style={"width": "100%", "marginTop": "12px"},
            ),
        ]
    )
