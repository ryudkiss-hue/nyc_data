"""SQL Studio callbacks — execute DuckDB queries against the local warehouse."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import dash_mantine_components as dmc
import pandas as pd
from dash import Input, Output, State, callback, html, no_update

logger = logging.getLogger(__name__)

_DB_PATH: str | None = None


def _get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH:
        return _DB_PATH
    path = os.environ.get("DUCKDB_PATH") or str(
        Path(__file__).resolve().parents[2] / "nyc_dot_analytics.duckdb"
    )
    if not os.path.isabs(path):
        path = str((Path(__file__).resolve().parents[2] / path).resolve())
    _DB_PATH = path
    return path


def _run_query(sql: str, limit: int = 1000) -> pd.DataFrame:
    import duckdb
    db = _get_db_path()
    con = duckdb.connect(db, read_only=True)
    try:
        df = con.execute(sql).fetchdf()
        return df.head(limit)
    finally:
        con.close()


def _render_table(df: pd.DataFrame) -> html.Div:
    cols = df.columns.tolist()
    headers = [html.Th(c, style={"whiteSpace": "nowrap", "padding": "6px 12px"}) for c in cols]
    rows = []
    for _, r in df.iterrows():
        cells = [
            html.Td(
                str(r[c])[:120] if r[c] is not None else "—",
                style={"padding": "4px 12px", "whiteSpace": "nowrap"},
            )
            for c in cols
        ]
        rows.append(html.Tr(cells))
    return html.Div([
        dmc.Text(f"Returned {len(df):,} rows × {len(cols)} columns", size="sm", c="dimmed", mb="xs"),
        html.Div(
            html.Table(
                [html.Thead(html.Tr(headers)), html.Tbody(rows)],
                style={
                    "borderCollapse": "collapse", "width": "100%",
                    "fontSize": "12px", "fontFamily": "monospace",
                },
            ),
            style={"overflowX": "auto", "maxHeight": "500px", "overflowY": "auto",
                   "border": "1px solid #dee2e6", "borderRadius": "6px"},
        ),
    ])


@callback(
    Output("sql-results-output", "children"),
    Output("sql-loading-overlay", "visible"),
    Input("btn-run-sql", "n_clicks"),
    Input("btn-clear-sql", "n_clicks"),
    State("sql-query-input", "value"),
    prevent_initial_call=True,
)
def execute_sql_query(run_clicks, clear_clicks, sql: str | None):
    from dash import ctx
    if not ctx.triggered_id:
        return no_update, False

    if ctx.triggered_id == "btn-clear-sql":
        return html.Div(), False

    if not sql or not sql.strip():
        return dmc.Alert("Enter a SQL query above.", color="yellow"), False

    # Safety: block mutations (no DDL/DML on read-only connection anyway, but be explicit)
    upper = sql.strip().upper()
    if any(upper.startswith(kw) for kw in ("DROP", "DELETE", "TRUNCATE", "INSERT", "UPDATE", "ALTER", "CREATE")):
        return dmc.Alert(
            "Only SELECT queries are permitted in the SQL Studio.",
            color="red", title="Read-Only Mode",
        ), False

    try:
        df = _run_query(sql)
        if df.empty:
            return dmc.Alert("Query returned 0 rows.", color="blue"), False
        return _render_table(df), False
    except Exception as e:
        logger.error(f"SQL query error: {e}", exc_info=True)
        return dmc.Alert(
            str(e)[:500],
            color="red",
            title="Query Error",
        ), False
