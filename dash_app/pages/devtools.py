"""dash_app/pages/devtools.py — DuckDB REPL, schema browser, Dask info"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import duckdb
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, dcc, html

from dash_app.data import db

dash.register_page(__name__, path="/devtools", name="Dev Tools", order=12)

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("🔗 Developer Tools", className="nyc-page-title"),
                html.P(
                    "Raw DuckDB SQL REPL, full schema browser, database statistics, and Dask environment info.",
                    className="nyc-page-sub",
                ),
            ],
            className="nyc-page-header",
        ),
        dbc.Tabs(
            [
                dbc.Tab(label="💻 SQL REPL", tab_id="repl"),
                dbc.Tab(label="🗂️ Schema Browser", tab_id="schema"),
                dbc.Tab(label="📊 DB Stats", tab_id="stats"),
                dbc.Tab(label="⚙️ Dask Info", tab_id="dask"),
            ],
            id="dev-tabs",
            active_tab="repl",
            className="nyc-tabs mb-3",
        ),
        html.Div(id="dev-content"),
    ],
    fluid=True,
)


@callback(Output("dev-content", "children"), Input("dev-tabs", "active_tab"))
def render(tab):
    if tab == "repl":
        return html.Div(
            [
                dbc.Textarea(
                    id="dev-sql",
                    placeholder="-- Write any DuckDB SQL here\nSELECT 42 AS answer;",
                    rows=8,
                    style={
                        "fontFamily": "monospace",
                        "fontSize": "0.85rem",
                        "background": "var(--bg-secondary)",
                        "color": "var(--text-primary)",
                        "border": "1px solid var(--border-color)",
                        "borderRadius": "8px",
                        "padding": "12px",
                        "resize": "vertical",
                        "width": "100%",
                    },
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Button(
                                "▶ Execute",
                                id="dev-run-btn",
                                color="success",
                                size="sm",
                                className="mt-2",
                            ),
                            md=2,
                        ),
                        dbc.Col(
                            dbc.Button(
                                "📋 Copy SQL",
                                id="dev-copy-btn",
                                color="secondary",
                                outline=True,
                                size="sm",
                                className="mt-2",
                            ),
                            md=2,
                        ),
                    ]
                ),
                dcc.Loading(
                    html.Div(id="dev-repl-result", style={"marginTop": "12px"}), type="dot"
                ),
            ]
        )

    if tab == "schema":
        return html.Div(
            [
                dbc.Button(
                    "🔄 Refresh",
                    id="dev-schema-refresh",
                    color="secondary",
                    outline=True,
                    size="sm",
                    className="mb-3",
                ),
                html.Div(id="dev-schema-content"),
            ]
        )

    if tab == "stats":
        return html.Div(
            [
                dbc.Button(
                    "📊 Load Stats", id="dev-stats-btn", color="info", size="sm", className="mb-3"
                ),
                dcc.Loading(html.Div(id="dev-stats-content"), type="dot"),
            ]
        )

    if tab == "dask":
        import platform

        import dask

        info = {
            "Dask version": dask.__version__,
            "Python version": platform.python_version(),
            "DuckDB version": duckdb.__version__,
            "MotherDuck": "Yes" if db.is_motherduck() else "No (local)",
            "DB path": db._conn_string(),
            "Tables": ", ".join(db.list_tables()) or "(none)",
        }
        rows = [{"Key": k, "Value": v} for k, v in info.items()]
        return dag.AgGrid(
            rowData=rows,
            columnDefs=[{"field": "Key", "flex": 1}, {"field": "Value", "flex": 2}],
            dashGridOptions={"domLayout": "autoHeight"},
            className="ag-theme-alpine-dark",
            style={"width": "100%"},
        )
    return html.Div()


@callback(
    Output("dev-repl-result", "children"),
    Input("dev-run-btn", "n_clicks"),
    State("dev-sql", "value"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)
def run_sql(_, sql, theme):
    if not sql or not sql.strip():
        return dbc.Alert("Enter SQL.", color="warning")
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(
        theme or "dark", "plotly_dark"
    )
    try:
        df = db.query_df(sql.strip())
        if df.empty:
            return dbc.Alert("Query returned 0 rows.", color="info")
        return html.Div(
            [
                html.P(
                    f"{len(df):,} rows × {len(df.columns)} cols",
                    style={
                        "fontSize": "0.78rem",
                        "color": "var(--text-muted)",
                        "marginBottom": "6px",
                    },
                ),
                dag.AgGrid(
                    rowData=df.to_dict("records"),
                    columnDefs=[
                        {"field": c, "sortable": True, "filter": True, "resizable": True}
                        for c in df.columns
                    ],
                    defaultColDef={"minWidth": 80},
                    dashGridOptions={
                        "pagination": True,
                        "paginationPageSize": 50,
                        "enableRangeSelection": True,
                    },
                    csvExportParams={"fileName": "repl_result.csv"},
                    className="ag-theme-alpine-dark",
                    style={"height": "400px", "width": "100%"},
                ),
            ]
        )
    except Exception as e:
        return dbc.Alert(f"❌ {e}", color="danger", dismissable=True)


@callback(Output("dev-schema-content", "children"), Input("dev-schema-refresh", "n_clicks"))
def refresh_schema(_):
    tables = db.list_tables()
    if not tables:
        return dbc.Alert("No tables in DuckDB.", color="info")
    accordions = []
    for t in tables:
        try:
            schema = db.table_schema(t)
            cnt = db.table_row_count(t)
            col_pills = [
                html.Span(
                    f"{r.get('column_name', '')} ({r.get('column_type', '')})",
                    className="nyc-pill nyc-pill-blue me-1 mb-1",
                    style={"display": "inline-block"},
                )
                for _, r in schema.iterrows()
            ]
            accordions.append(
                dbc.AccordionItem(
                    [
                        html.P(
                            f"{cnt:,} rows | {len(schema)} columns",
                            style={"fontSize": "0.78rem", "color": "var(--text-muted)"},
                        ),
                        html.Div(col_pills, style={"marginTop": "8px"}),
                    ],
                    title=t,
                )
            )
        except Exception:
            pass
    return dbc.Accordion(
        accordions,
        flush=True,
        start_collapsed=True,
        style={
            "background": "var(--bg-secondary)",
            "border": "1px solid var(--border-color)",
            "borderRadius": "8px",
        },
    )


@callback(
    Output("dev-stats-content", "children"),
    Input("dev-stats-btn", "n_clicks"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)
def load_stats(_, theme):
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(
        theme or "dark", "plotly_dark"
    )
    tables = db.list_tables()
    if not tables:
        return dbc.Alert("No tables.", color="info")
    rows = []
    for t in tables:
        try:
            cnt = db.table_row_count(t)
            schema = db.table_schema(t)
            rows.append({"Table": t, "Rows": cnt, "Columns": len(schema)})
        except Exception:
            pass
    df = pd.DataFrame(rows)
    fig = px.bar(
        df,
        x="Table",
        y="Rows",
        template=tmpl,
        height=300,
        title="Rows per Table",
        color="Rows",
        color_continuous_scale="Blues",
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
                rowData=df.to_dict("records"),
                columnDefs=[{"field": c, "sortable": True} for c in df.columns],
                dashGridOptions={"domLayout": "autoHeight"},
                className="ag-theme-alpine-dark",
                style={"width": "100%", "marginTop": "12px"},
            ),
        ]
    )
