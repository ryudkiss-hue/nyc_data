"""dash_app/pages/pipeline.py — Data ingestion, CDC, deduplication, cleaning"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import dask.dataframe as dd
import pandas as pd
from dash import Input, Output, State, callback, dcc, html

from dash_app.data import db

dash.register_page(__name__, path="/pipeline", name="Data Pipeline", order=7)

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("🔄 Data Pipeline", className="nyc-page-title"),
                html.P(
                    "Parallel Socrata ingestion (Dask), change data capture, deduplication, and data cleaning.",
                    className="nyc-page-sub",
                ),
            ],
            className="nyc-page-header",
        ),
        dbc.Tabs(
            [
                dbc.Tab(label="⬇️ Ingest", tab_id="ingest", className="nyc-tabs"),
                dbc.Tab(label="🔍 CDC", tab_id="cdc", className="nyc-tabs"),
                dbc.Tab(label="🧹 Clean", tab_id="clean", className="nyc-tabs"),
                dbc.Tab(label="♻️ Deduplicate", tab_id="dedupe", className="nyc-tabs"),
            ],
            id="pipe-tabs",
            active_tab="ingest",
            className="nyc-tabs mb-3",
        ),
        html.Div(id="pipe-tab-content"),
        dcc.Store(id="pipe-ingest-store"),
    ],
    fluid=True,
)


@callback(
    Output("pipe-tab-content", "children"),
    Input("pipe-tabs", "active_tab"),
    Input("session-store", "data"),
)
def render_tab(tab, _):
    tables = [{"label": t, "value": t} for t in db.list_tables()]

    # ── Ingest ──────────────────────────────────────────────────────────────
    if tab == "ingest":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label(
                                    "Domain",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dbc.Input(id="pi-domain", value="data.cityofnewyork.us", size="sm"),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Dataset ID (4x4)",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dbc.Input(id="pi-id", placeholder="e.g. erm2-nwe9", size="sm"),
                            ],
                            md=3,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Max rows",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dbc.Input(id="pi-rows", type="number", value=5000, size="sm"),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Save as table",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dbc.Input(id="pi-table-name", placeholder="table_name", size="sm"),
                            ],
                            md=3,
                        ),
                    ],
                    className="mb-2",
                ),
                dbc.Button(
                    "🚀 Fetch (Dask parallel)",
                    id="pi-fetch-btn",
                    color="primary",
                    size="sm",
                    className="mb-3",
                ),
                dcc.Loading(html.Div(id="pi-status"), type="circle", color="var(--accent)"),
                html.Div(id="pi-result"),
            ]
        )

    # ── CDC ─────────────────────────────────────────────────────────────────
    if tab == "cdc":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label(
                                    "Baseline table (old)",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dcc.Dropdown(
                                    id="cdc-old-sel",
                                    options=tables,
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "New table / fetch same",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dcc.Dropdown(
                                    id="cdc-new-sel",
                                    options=tables,
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Primary key column",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dbc.Input(id="cdc-pk", placeholder=":id or unique col", size="sm"),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            [
                                html.Div(style={"height": "22px"}),
                                dbc.Button(
                                    "Detect Changes", id="cdc-btn", color="warning", size="sm"
                                ),
                            ],
                            md=2,
                        ),
                    ],
                    className="mb-3",
                ),
                dcc.Loading(html.Div(id="cdc-result"), type="dot"),
            ]
        )

    # ── Clean ───────────────────────────────────────────────────────────────
    if tab == "clean":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label(
                                    "Table to clean",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dcc.Dropdown(
                                    id="cl-table-sel",
                                    options=tables,
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=5,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Save result as",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dbc.Input(
                                    id="cl-out-name", placeholder="cleaned_table_name", size="sm"
                                ),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Div(style={"height": "22px"}),
                                dbc.Button("🧹 Clean", id="cl-btn", color="info", size="sm"),
                            ],
                            md=3,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Checklist(
                    id="cl-ops",
                    options=[
                        {"label": "Standardise borough names", "value": "boro"},
                        {"label": "Lowercase column names", "value": "cols"},
                        {"label": "Strip leading/trailing whitespace", "value": "strip"},
                        {"label": "Drop fully-null columns", "value": "nullcols"},
                        {"label": "Convert numeric strings", "value": "nums"},
                    ],
                    value=["boro", "cols", "strip"],
                    inline=False,
                    style={
                        "fontSize": "0.82rem",
                        "color": "var(--text-primary)",
                        "marginBottom": "12px",
                    },
                ),
                dcc.Loading(html.Div(id="cl-result"), type="dot"),
            ]
        )

    # ── Dedupe ──────────────────────────────────────────────────────────────
    if tab == "dedupe":
        return html.Div(
            [
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
                                    id="dd-table-sel",
                                    options=tables,
                                    style={"background": "var(--bg-secondary)"},
                                ),
                            ],
                            md=5,
                        ),
                        dbc.Col(
                            [
                                html.Label(
                                    "Key columns (blank = all)",
                                    style={
                                        "fontSize": "0.78rem",
                                        "fontWeight": 600,
                                        "color": "var(--text-muted)",
                                    },
                                ),
                                dbc.Input(id="dd-cols", placeholder="col1, col2 …", size="sm"),
                            ],
                            md=4,
                        ),
                        dbc.Col(
                            [
                                html.Div(style={"height": "22px"}),
                                dbc.Button(
                                    "♻️ Deduplicate", id="dd-btn", color="secondary", size="sm"
                                ),
                            ],
                            md=3,
                        ),
                    ],
                    className="mb-3",
                ),
                dcc.Loading(html.Div(id="dd-result"), type="dot"),
            ]
        )

    return html.Div()


# ── Ingest callback ───────────────────────────────────────────────────────────
@callback(
    Output("pi-status", "children"),
    Output("pi-result", "children"),
    Input("pi-fetch-btn", "n_clicks"),
    State("pi-domain", "value"),
    State("pi-id", "value"),
    State("pi-rows", "value"),
    State("pi-table-name", "value"),
    State("token-store", "data"),
    prevent_initial_call=True,
)
def ingest(_, domain, dsid, rows, tname, token):
    if not dsid:
        return dbc.Alert("Enter a dataset ID.", color="warning"), html.Div()
    try:
        df = db.parallel_socrata_fetch(
            domain or "data.cityofnewyork.us", dsid, max_rows=int(rows or 5000), token=token
        )
        label = tname or dsid.replace("-", "_")
        db.upsert_df(df, label)
        grid = dag.AgGrid(
            rowData=df.head(200).to_dict("records"),
            columnDefs=[{"field": c} for c in df.columns],
            dashGridOptions={
                "domLayout": "autoHeight",
                "pagination": True,
                "paginationPageSize": 25,
            },
            className="ag-theme-alpine-dark",
            style={"width": "100%"},
        )
        return (
            dbc.Alert(
                f"✅ {len(df):,} rows → DuckDB `{label}`",
                color="success",
                dismissable=True,
                duration=5000,
            ),
            grid,
        )
    except Exception as e:
        return dbc.Alert(f"❌ {e}", color="danger", dismissable=True), html.Div()


# ── CDC callback ─────────────────────────────────────────────────────────────
@callback(
    Output("cdc-result", "children"),
    Input("cdc-btn", "n_clicks"),
    State("cdc-old-sel", "value"),
    State("cdc-new-sel", "value"),
    State("cdc-pk", "value"),
    prevent_initial_call=True,
)
def detect_cdc(_, old_t, new_t, pk):
    if not old_t or not new_t:
        return dbc.Alert("Select both tables.", color="warning")
    try:
        old_df = db.query_df(f'SELECT * FROM "{old_t}"')
        new_df = db.query_df(f'SELECT * FROM "{new_t}"')
        pk = pk.strip() if pk else None
        shared_cols = [c for c in old_df.columns if c in new_df.columns]

        if pk and pk in old_df.columns:
            old_ids = set(old_df[pk].astype(str))
            new_ids = set(new_df[pk].astype(str))
            added = new_df[new_df[pk].astype(str).isin(new_ids - old_ids)]
            removed = old_df[old_df[pk].astype(str).isin(old_ids - new_ids)]
            ddf_old = dd.from_pandas(old_df.set_index(pk)[shared_cols], npartitions=2)
            ddf_new = dd.from_pandas(new_df.set_index(pk)[shared_cols], npartitions=2)
            merged = ddf_old.join(ddf_new, lsuffix="_old", rsuffix="_new", how="inner").compute()
            modified_mask = any(
                (merged[f"{c}_old"].astype(str) != merged[f"{c}_new"].astype(str)).any()
                for c in shared_cols
                if f"{c}_old" in merged.columns
            )
            n_mod = int(modified_mask) if isinstance(modified_mask, bool) else int(modified_mask)
        else:
            added = pd.DataFrame()
            removed = pd.DataFrame()
            n_mod = 0

        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div(
                                        str(len(added)),
                                        className="nyc-metric-value",
                                        style={"color": "var(--success)"},
                                    ),
                                    html.Div("Added", className="nyc-metric-label"),
                                ],
                                className="nyc-metric",
                            ),
                            md=3,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div(
                                        str(len(removed)),
                                        className="nyc-metric-value",
                                        style={"color": "var(--danger)"},
                                    ),
                                    html.Div("Removed", className="nyc-metric-label"),
                                ],
                                className="nyc-metric",
                            ),
                            md=3,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div(
                                        str(n_mod),
                                        className="nyc-metric-value",
                                        style={"color": "var(--warning)"},
                                    ),
                                    html.Div("Modified", className="nyc-metric-label"),
                                ],
                                className="nyc-metric",
                            ),
                            md=3,
                        ),
                    ],
                    className="mb-3",
                ),
                (
                    dag.AgGrid(
                        rowData=added.head(100).to_dict("records"),
                        columnDefs=[{"field": c} for c in added.columns],
                        dashGridOptions={"domLayout": "autoHeight"},
                        className="ag-theme-alpine-dark",
                        style={"width": "100%"},
                    )
                    if not added.empty
                    else html.Div()
                ),
            ]
        )
    except Exception as e:
        return dbc.Alert(f"❌ {e}", color="danger", dismissable=True)


# ── Clean callback ────────────────────────────────────────────────────────────
@callback(
    Output("cl-result", "children"),
    Input("cl-btn", "n_clicks"),
    State("cl-table-sel", "value"),
    State("cl-ops", "value"),
    State("cl-out-name", "value"),
    prevent_initial_call=True,
)
def clean_data(_, table, ops, out_name):
    if not table:
        return dbc.Alert("Select a table.", color="warning")
    try:
        df = db.query_df(f'SELECT * FROM "{table}"')
        ops = ops or []
        if "cols" in ops:
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        if "strip" in ops:
            df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)
        if "nullcols" in ops:
            df = df.dropna(axis=1, how="all")
        if "nums" in ops:
            for c in df.select_dtypes("object").columns:
                converted = pd.to_numeric(df[c], errors="coerce")
                if converted.notna().mean() > 0.7:
                    df[c] = converted
        if "boro" in ops:
            BORO_MAP = {
                "bk": "Brooklyn",
                "bklyn": "Brooklyn",
                "brooklyn": "Brooklyn",
                "bx": "Bronx",
                "bronx": "Bronx",
                "bronx": "Bronx",
                "mn": "Manhattan",
                "manhattan": "Manhattan",
                "qn": "Queens",
                "queens": "Queens",
                "si": "Staten Island",
                "staten island": "Staten Island",
                "staten is": "Staten Island",
            }
            for c in df.select_dtypes("object").columns:
                if "boro" in c.lower() or "borough" in c.lower():
                    df[c] = (
                        df[c]
                        .str.strip()
                        .str.lower()
                        .map(lambda v: BORO_MAP.get(v, v) if isinstance(v, str) else v)
                    )
        label = out_name or f"{table}_cleaned"
        db.upsert_df(df, label)
        return dbc.Alert(
            f"✅ Cleaned → `{label}` ({len(df):,} rows, {len(df.columns)} cols)",
            color="success",
            dismissable=True,
            duration=6000,
        )
    except Exception as e:
        return dbc.Alert(f"❌ {e}", color="danger", dismissable=True)


# ── Dedupe callback ───────────────────────────────────────────────────────────
@callback(
    Output("dd-result", "children"),
    Input("dd-btn", "n_clicks"),
    State("dd-table-sel", "value"),
    State("dd-cols", "value"),
    prevent_initial_call=True,
)
def dedupe(_, table, cols_str):
    if not table:
        return dbc.Alert("Select a table.", color="warning")
    try:
        df = db.query_df(f'SELECT * FROM "{table}"')
        pre = len(df)
        key_cols = (
            [c.strip() for c in cols_str.split(",")] if cols_str and cols_str.strip() else None
        )
        df = df.drop_duplicates(subset=key_cols)
        label = f"{table}_deduped"
        db.upsert_df(df, label)
        return dbc.Alert(
            f"✅ Removed {pre - len(df):,} duplicates → `{label}` ({len(df):,} rows)",
            color="success",
            dismissable=True,
            duration=6000,
        )
    except Exception as e:
        return dbc.Alert(f"❌ {e}", color="danger", dismissable=True)
