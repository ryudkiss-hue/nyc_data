"""dash_app/pages/home.py — Program Dashboard"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import plotly.express as px
import pandas as pd

from dash_app.data import db

dash.register_page(__name__, path="/", name="Dashboard", order=0)

QUICK_DATASETS = [
    {"icon": "🚧", "title": "Sidewalk Violations",  "desc": "311 sidewalk defect complaints", "domain": "data.cityofnewyork.us", "id": "erm2-nwe9", "label": "complaints_311"},
    {"icon": "🚲", "title": "Bike Route Projects",  "desc": "Planned & completed bike lanes",  "domain": "data.cityofnewyork.us", "id": "s5uu-3ajy", "label": "bike_routes"},
    {"icon": "🚗", "title": "Traffic Volume",       "desc": "Daily traffic counts by borough", "domain": "data.cityofnewyork.us", "id": "btm5-ppia", "label": "traffic_volume"},
    {"icon": "🌉", "title": "Bridge Inspections",   "desc": "NYC bridge condition ratings",    "domain": "data.cityofnewyork.us", "id": "bhad-7uzz", "label": "bridge_inspections"},
]

layout = dbc.Container([
    html.Div([
        html.H1("🏠 Program Dashboard", className="nyc-page-title"),
        html.P("Launch an analysis pipeline with one click, or upload your own dataset.", className="nyc-page-sub"),
    ], className="nyc-page-header"),

    html.H5("⚡ Quick Start", style={"fontWeight": 700, "color": "var(--text-heading)", "marginBottom": "12px"}),
    dbc.Row([
        dbc.Col(html.Div([
            html.Div(ds["icon"], className="qs-icon"),
            html.Div(ds["title"], className="qs-title"),
            html.Div(ds["desc"], className="qs-desc"),
            html.Div(style={"height": "12px"}),
            dbc.Button("Load Dataset", id={"type": "qs-btn", "index": i},
                       size="sm", color="primary", outline=True, className="w-100"),
        ], className="qs-card"), md=3, sm=6, xs=12, className="mb-3")
        for i, ds in enumerate(QUICK_DATASETS)
    ]),

    dcc.Loading(html.Div(id="home-status"), type="circle", color="var(--accent)"),
    html.Div(className="divider-nyc"),

    html.H5("📁 Upload Dataset", style={"fontWeight": 700, "marginBottom": "12px", "color": "var(--text-heading)"}),
    dcc.Upload(
        id="home-upload",
        children=html.Div([
            html.Div("⬆️", style={"fontSize": "2rem"}),
            html.Div("Drag & drop CSV or Parquet, or click to browse",
                     style={"color": "var(--text-muted)", "fontSize": "0.85rem", "marginTop": "8px"}),
        ], style={"textAlign": "center", "padding": "28px"}),
        style={"border": "2px dashed var(--border-color)", "borderRadius": "12px",
               "background": "var(--bg-secondary)", "cursor": "pointer", "marginBottom": "20px"},
        multiple=False,
    ),

    html.Div(className="divider-nyc"),
    html.H5("🦆 DuckDB Tables", style={"fontWeight": 700, "marginBottom": "12px", "color": "var(--text-heading)"}),
    html.Div(id="home-tables"),
    html.Div(className="divider-nyc"),
    html.Div(id="home-preview"),
], fluid=True)


@callback(
    Output("home-status",  "children"),
    Output("session-store","data"),
    Input({"type": "qs-btn", "index": dash.ALL}, "n_clicks"),
    Input("home-upload",   "contents"),
    State("home-upload",   "filename"),
    State("token-store",   "data"),
    prevent_initial_call=True,
)
def load_data(qs_clicks, upload_contents, upload_name, token):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    tid = ctx.triggered_id

    if isinstance(tid, dict) and tid.get("type") == "qs-btn":
        ds = QUICK_DATASETS[tid["index"]]
        try:
            df = db.parallel_socrata_fetch(ds["domain"], ds["id"], max_rows=2000, token=token)
            if df.empty:
                return dbc.Alert("No data returned.", color="warning", dismissable=True), dash.no_update
            db.upsert_df(df, ds["label"])
            store = {"label": ds["label"], "table_name": ds["label"],
                     "records": df.head(500).to_dict("records"),
                     "columns": list(df.columns), "row_count": len(df)}
            return dbc.Alert(f"✅ {ds['title']} — {len(df):,} rows loaded to `{ds['label']}`",
                             color="success", dismissable=True, duration=6000), store
        except Exception as e:
            return dbc.Alert(f"❌ {e}", color="danger", dismissable=True), dash.no_update

    if tid == "home-upload" and upload_contents:
        import base64, io
        _, content_string = upload_contents.split(",")
        decoded = base64.b64decode(content_string)
        fname = upload_name or "upload.csv"
        try:
            df = pd.read_parquet(io.BytesIO(decoded)) if fname.endswith(".parquet") else pd.read_csv(io.BytesIO(decoded))
            label = fname.rsplit(".", 1)[0]
            db.upsert_df(df, label)
            store = {"label": label, "table_name": label,
                     "records": df.head(500).to_dict("records"),
                     "columns": list(df.columns), "row_count": len(df)}
            return dbc.Alert(f"✅ {fname} — {len(df):,} rows", color="success", dismissable=True, duration=6000), store
        except Exception as e:
            return dbc.Alert(f"❌ {e}", color="danger", dismissable=True), dash.no_update

    return dash.no_update, dash.no_update


@callback(Output("home-tables", "children"), Input("session-store", "data"))
def refresh_tables(_):
    tables = db.list_tables()
    if not tables:
        return html.P("No tables yet.", style={"color": "var(--text-muted)"})
    rows = [{"Table": t, "Rows": f"{db.table_row_count(t):,}"} for t in tables]
    return dag.AgGrid(rowData=rows,
                      columnDefs=[{"field": "Table", "flex": 2}, {"field": "Rows", "flex": 1}],
                      dashGridOptions={"domLayout": "autoHeight"},
                      className="ag-theme-alpine-dark", style={"width": "100%"})


@callback(Output("home-preview", "children"), Input("session-store", "data"))
def show_preview(store):
    if not store or not store.get("records"):
        return html.Div()
    df = pd.DataFrame(store["records"])
    if df.empty:
        return html.Div()
    num_cols = df.select_dtypes("number").columns.tolist()
    cat_cols = df.select_dtypes("object").columns.tolist()
    metrics = dbc.Row([
        dbc.Col(html.Div([
            html.Div(f"{df[c].mean():,.1f}", className="nyc-metric-value"),
            html.Div(f"Avg {c}", className="nyc-metric-label"),
        ], className="nyc-metric"), md=3, sm=6) for c in num_cols[:4]
    ], className="mb-3") if num_cols else html.Div()
    chart = html.Div()
    if cat_cols:
        vc = df[cat_cols[0]].value_counts().head(10).reset_index()
        vc.columns = [cat_cols[0], "count"]
        fig = px.bar(vc, x=cat_cols[0], y="count", title=f"Top 10: {cat_cols[0]}", template="plotly_dark", height=260)
        fig.update_layout(margin=dict(l=0, r=0, t=36, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        chart = dcc.Graph(figure=fig, config={"displayModeBar": False})
    return html.Div([
        html.H5(f"📋 {store['label']} — {store['row_count']:,} rows",
                style={"fontWeight": 700, "color": "var(--text-heading)", "marginBottom": "12px"}),
        metrics, chart, html.Div(style={"height": "12px"}),
        dag.AgGrid(rowData=store["records"],
                   columnDefs=[{"field": c, "sortable": True, "filter": True, "resizable": True}
                                for c in store["columns"]],
                   defaultColDef={"minWidth": 80},
                   dashGridOptions={"pagination": True, "paginationPageSize": 25},
                   className="ag-theme-alpine-dark", style={"height": "360px", "width": "100%"}),
    ])
