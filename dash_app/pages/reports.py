"""dash_app/pages/reports.py — Report generation and download"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dcc, html

from dash_app.data import db

dash.register_page(__name__, path="/reports", name="Reports", order=9)

REPORT_TYPES = [
    {"label": "📋 Executive Summary", "value": "executive"},
    {"label": "📊 Data Quality Report", "value": "quality"},
    {"label": "🔄 Pipeline Status Report", "value": "pipeline"},
    {"label": "📈 Analytics Summary", "value": "analytics"},
    {"label": "🏗️ Contract Progress", "value": "contract"},
]

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("📋 Reports", className="nyc-page-title"),
                html.P(
                    "Generate formatted Markdown reports from DuckDB data and download them.",
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
                            id="rep-table-sel",
                            placeholder="Select DuckDB table…",
                            style={"background": "var(--bg-secondary)"},
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Report type",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Dropdown(
                            id="rep-type-sel",
                            options=REPORT_TYPES,
                            value="executive",
                            clearable=False,
                            style={"background": "var(--bg-secondary)"},
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Author / Agency",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dbc.Input(id="rep-author", value="NYC DOT", size="sm"),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div(style={"height": "22px"}),
                        dbc.Button("📝 Generate", id="rep-gen-btn", color="primary", size="sm"),
                    ],
                    md=1,
                ),
            ],
            className="mb-3",
        ),
        dcc.Loading(html.Div(id="rep-status"), type="dot"),
        dcc.Download(id="rep-download"),
        html.Div(className="divider-nyc"),
        dbc.Row(
            [
                dbc.Col(
                    html.H5(
                        "📄 Report Preview",
                        style={"fontWeight": 700, "color": "var(--text-heading)"},
                    ),
                    md=8,
                ),
                dbc.Col(
                    dbc.Button(
                        "⬇️ Download .md",
                        id="rep-dl-btn",
                        color="secondary",
                        outline=True,
                        size="sm",
                    ),
                    md=4,
                    style={"textAlign": "right"},
                ),
            ],
            className="mb-2",
        ),
        html.Div(id="rep-preview"),
        dcc.Store(id="rep-content-store"),
    ],
    fluid=True,
)


@callback(Output("rep-table-sel", "options"), Input("session-store", "data"))
def populate(_):
    return [{"label": t, "value": t} for t in db.list_tables()]


@callback(
    Output("rep-preview", "children"),
    Output("rep-status", "children"),
    Output("rep-content-store", "data"),
    Input("rep-gen-btn", "n_clicks"),
    State("rep-table-sel", "value"),
    State("rep-type-sel", "value"),
    State("rep-author", "value"),
    prevent_initial_call=True,
)
def generate_report(_, table, rtype, author):
    if not table:
        return html.Div(), dbc.Alert("Select a dataset.", color="warning"), ""
    try:
        df = db.query_df(f'SELECT * FROM "{table}" LIMIT 10000')
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        md = _build_report(df, table, rtype, author or "NYC DOT", now)
        preview = dbc.Card(
            dbc.CardBody(
                dcc.Markdown(md, style={"fontSize": "0.83rem", "color": "var(--text-primary)"}),
            ),
            style={
                "background": "var(--bg-secondary)",
                "border": "1px solid var(--border-color)",
                "maxHeight": "600px",
                "overflowY": "auto",
            },
        )
        return (
            preview,
            dbc.Alert("✅ Report generated", color="success", dismissable=True, duration=3000),
            md,
        )
    except Exception as e:
        return html.Div(), dbc.Alert(f"❌ {e}", color="danger", dismissable=True), ""


@callback(
    Output("rep-download", "data"),
    Input("rep-dl-btn", "n_clicks"),
    State("rep-content-store", "data"),
    State("rep-table-sel", "value"),
    prevent_initial_call=True,
)
def download_report(_, md, table):
    if not md:
        return dash.no_update
    fname = f"{table or 'report'}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    return dcc.send_string(md, fname)


def _build_report(df: pd.DataFrame, table: str, rtype: str, author: str, ts: str) -> str:
    num_cols = df.select_dtypes("number").columns.tolist()
    cat_cols = df.select_dtypes("object").columns.tolist()
    completeness = round((1 - df.isnull().mean().mean()) * 100, 1)

    header = f"""# NYC DOT — {rtype.replace("_", " ").title()} Report
**Dataset:** `{table}`  **Generated:** {ts}  **Author:** {author}

---
"""
    if rtype == "executive":
        return header + f"""## Executive Summary

| Metric | Value |
|--------|-------|
| Total Records | {len(df):,} |
| Columns | {len(df.columns)} |
| Completeness | {completeness}% |
| Numeric Columns | {len(num_cols)} |
| Text Columns | {len(cat_cols)} |

## Key Statistics

{"".join(f"- **{c}**: avg={df[c].mean():,.2f}, min={df[c].min()}, max={df[c].max()}{chr(10)}" for c in num_cols[:5])}

## Data Quality Assessment

{"✅ Good" if completeness >= 80 else ("⚠️ Fair" if completeness >= 60 else "❌ Poor")} — {completeness}% of all fields are populated.

## Recommendations

1. Review null values in columns exceeding 20% nulls
2. Validate numeric ranges against domain expectations
3. Schedule regular refresh from source API
"""
    if rtype == "quality":
        null_breakdown = "\n".join(
            f"| {c} | {round(df[c].isnull().mean() * 100, 1)}% | {df[c].nunique()} |"
            for c in df.columns[:20]
        )
        return header + f"""## Data Quality Report

### Summary Scores

| Dimension | Score |
|-----------|-------|
| Completeness | {completeness}% |
| Uniqueness | {round((df.nunique() / max(len(df), 1)).mean() * 100, 1)}% |
| Row Count | {len(df):,} |

### Column Null Analysis

| Column | Null % | Unique Values |
|--------|--------|---------------|
{null_breakdown}
"""
    if rtype == "pipeline":
        tables = db.list_tables()
        tbl_list = "\n".join(f"- `{t}` — {db.table_row_count(t):,} rows" for t in tables)
        return header + f"""## Pipeline Status Report

### Active DuckDB Tables ({len(tables)})

{tbl_list}

### Last Refresh
Fetched from source at {ts}. Dataset `{table}` contains {len(df):,} records.
"""
    # analytics / contract fallback
    stats = "\n".join(
        f"| {c} | {df[c].mean():,.2f} | {df[c].min()} | {df[c].max()} |" for c in num_cols[:8]
    )
    return header + f"""## Analytics Summary

| Column | Mean | Min | Max |
|--------|------|-----|-----|
{stats if stats else "| — | — | — | — |"}

*Generated by NYC DOT Data Assistant*
"""
