"""dash_app/pages/soql.py — Interactive SoQL / SQL query builder"""

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

dash.register_page(__name__, path="/soql", name="SoQL Maestro", order=4)

EXAMPLE_QUERIES = {
    "Select all": "SELECT * FROM {table} LIMIT 100",
    "Count by column": "SELECT {col}, COUNT(*) AS cnt FROM {table} GROUP BY {col} ORDER BY cnt DESC LIMIT 20",
    "Null counts": "SELECT {col}, COUNT(*) FILTER (WHERE {col} IS NULL) AS nulls FROM {table} GROUP BY {col}",
    "Row count": "SELECT COUNT(*) AS total FROM {table}",
    "Distinct values": "SELECT DISTINCT {col} FROM {table} LIMIT 50",
    "Min / Max / Avg": "SELECT MIN({col}) AS min_val, MAX({col}) AS max_val, AVG({col}) AS avg_val FROM {table}",
    "Recent records": "SELECT * FROM {table} ORDER BY rowid DESC LIMIT 50",
    "DuckDB table info": "DESCRIBE {table}",
    "DuckDB SHOW TABLES": "SHOW TABLES",
}

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("✨ SoQL / SQL Maestro", className="nyc-page-title"),
                html.P(
                    "Write and execute SQL directly against DuckDB. Results render in an interactive AG Grid with one-click CSV export.",
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
                            "Table",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Dropdown(
                            id="soql-table-sel",
                            placeholder="Choose a table…",
                            style={"background": "var(--bg-secondary)"},
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Example queries",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Dropdown(
                            id="soql-example-sel",
                            options=[{"label": k, "value": k} for k in EXAMPLE_QUERIES],
                            placeholder="Insert a template…",
                            style={"background": "var(--bg-secondary)"},
                        ),
                    ],
                    md=5,
                ),
                dbc.Col(
                    [
                        html.Div(style={"height": "22px"}),
                        dbc.Button(
                            "▶ Run", id="soql-run-btn", color="success", size="sm", className="me-2"
                        ),
                        dbc.Button(
                            "💾 Save to DuckDB",
                            id="soql-save-btn",
                            color="secondary",
                            outline=True,
                            size="sm",
                        ),
                    ],
                    md=3,
                ),
            ],
            className="mb-2",
        ),
        # SQL editor
        dbc.Textarea(
            id="soql-editor",
            placeholder="SELECT * FROM your_table LIMIT 100;",
            style={
                "fontFamily": "monospace",
                "fontSize": "0.85rem",
                "height": "140px",
                "background": "var(--bg-secondary)",
                "border": "1px solid var(--border-color)",
                "color": "var(--text-primary)",
                "borderRadius": "8px",
                "padding": "12px",
                "resize": "vertical",
            },
            className="mb-2",
        ),
        dcc.Loading(html.Div(id="soql-status"), type="dot"),
        html.Div(className="divider-nyc"),
        dbc.Row(
            [
                dbc.Col(html.Div(id="soql-meta"), md=8),
                dbc.Col(
                    dbc.Button(
                        "📊 Chart result",
                        id="soql-chart-btn",
                        color="primary",
                        outline=True,
                        size="sm",
                    ),
                    md=4,
                    style={"textAlign": "right"},
                ),
            ],
            className="mb-2",
        ),
        html.Div(id="soql-results"),
        html.Div(id="soql-chart"),
        dcc.Store(id="soql-result-store"),
        dcc.Store(id="soql-save-name-store"),
    ],
    fluid=True,
)


@callback(Output("soql-table-sel", "options"), Input("session-store", "data"))
def populate(_):
    return [{"label": t, "value": t} for t in db.list_tables()]


@callback(
    Output("soql-editor", "value"),
    Input("soql-example-sel", "value"),
    State("soql-table-sel", "value"),
    prevent_initial_call=True,
)
def insert_template(example, table):
    if not example:
        return dash.no_update
    tmpl = EXAMPLE_QUERIES[example]
    table = table or "your_table"
    return tmpl.replace("{table}", table).replace("{col}", "column_name")


@callback(
    Output("soql-results", "children"),
    Output("soql-meta", "children"),
    Output("soql-status", "children"),
    Output("soql-result-store", "data"),
    Input("soql-run-btn", "n_clicks"),
    State("soql-editor", "value"),
    prevent_initial_call=True,
)
def run_query(_, sql):
    if not sql or not sql.strip():
        return (
            dash.no_update,
            dash.no_update,
            dbc.Alert("Enter a query.", color="warning"),
            dash.no_update,
        )
    try:
        df = db.query_df(sql.strip())
        if df.empty:
            return (
                html.P("Query returned 0 rows.", style={"color": "var(--text-muted)"}),
                html.Span("0 rows", className="nyc-pill nyc-pill-yellow"),
                html.Div(),
                {},
            )

        grid = dag.AgGrid(
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
            csvExportParams={"fileName": "soql_result.csv"},
            className="ag-theme-alpine-dark",
            style={"height": "420px", "width": "100%"},
        )
        meta = html.Span(
            f"{len(df):,} rows × {len(df.columns)} cols", className="nyc-pill nyc-pill-blue"
        )
        return grid, meta, html.Div(), df.to_dict("records")
    except Exception as e:
        return (
            dash.no_update,
            html.Div(),
            dbc.Alert(f"❌ {e}", color="danger", dismissable=True),
            {},
        )


@callback(
    Output("soql-chart", "children"),
    Input("soql-chart-btn", "n_clicks"),
    State("soql-result-store", "data"),
    State("theme-store", "data"),
    prevent_initial_call=True,
)
def auto_chart(_, records, theme):
    if not records:
        return html.Div()
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(
        theme or "dark", "plotly_dark"
    )
    df = pd.DataFrame(records)
    num = df.select_dtypes("number").columns.tolist()
    cat = df.select_dtypes("object").columns.tolist()
    if not num:
        return dbc.Alert("No numeric columns to chart.", color="warning")
    if cat:
        vc = df[cat[0]].value_counts().head(15).reset_index()
        vc.columns = [cat[0], "count"]
        fig = px.bar(vc, x=cat[0], y="count", template=tmpl, height=320, title=f"Count by {cat[0]}")
    else:
        fig = px.histogram(df, x=num[0], template=tmpl, height=320, marginal="box")
    fig.update_layout(
        margin=dict(l=0, r=0, t=36, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})
