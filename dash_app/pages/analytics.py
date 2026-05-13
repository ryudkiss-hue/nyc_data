"""dash_app/pages/analytics.py — Analytics page with Plotly + DuckDB + Dask"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import dask.dataframe as dd

from dash_app.data import db

dash.register_page(__name__, path="/analytics", name="Analytics", order=1)

TABS = ["KPI Dashboard", "Time Series", "Distribution", "Correlation", "Text Analysis", "Anomalies"]

layout = dbc.Container([
    html.Div([
        html.H1("📊 Analytics", className="nyc-page-title"),
        html.P("Statistical analysis, time-series trends, and anomaly detection powered by DuckDB + Dask.", className="nyc-page-sub"),
    ], className="nyc-page-header"),

    dbc.Row([
        dbc.Col([
            html.Label("Dataset", style={"fontSize": "0.78rem", "fontWeight": 600, "color": "var(--text-muted)"}),
            dcc.Dropdown(id="analytics-table-sel", placeholder="Select a DuckDB table…",
                         style={"background": "var(--bg-secondary)", "color": "var(--text-primary)"}),
        ], md=5),
        dbc.Col([
            html.Label("Or use session dataset", style={"fontSize": "0.78rem", "fontWeight": 600, "color": "var(--text-muted)"}),
            dbc.Button("Use Active Dataset", id="analytics-use-session", color="primary", outline=True, size="sm", className="mt-1"),
        ], md=4),
        dbc.Col([
            html.Label("Max rows (Dask)", style={"fontSize": "0.78rem", "fontWeight": 600, "color": "var(--text-muted)"}),
            dbc.Input(id="analytics-max-rows", type="number", value=50000, min=1000, max=1000000, size="sm"),
        ], md=3),
    ], className="mb-3"),

    dcc.Loading(html.Div(id="analytics-load-status"), type="dot"),

    dbc.Tabs(
        [dbc.Tab(label=t, tab_id=t.lower().replace(" ", "-")) for t in TABS],
        id="analytics-tabs", active_tab="kpi-dashboard", className="nyc-tabs mb-3",
    ),
    html.Div(id="analytics-tab-content"),

    # Hidden stores
    dcc.Store(id="analytics-data-store"),
], fluid=True)


# ── Populate table dropdown ───────────────────────────────────────────────────
@callback(Output("analytics-table-sel", "options"), Input("session-store", "data"))
def populate_tables(_):
    return [{"label": t, "value": t} for t in db.list_tables()]


# ── Load dataset into analytics store ────────────────────────────────────────
@callback(
    Output("analytics-data-store", "data"),
    Output("analytics-load-status", "children"),
    Input("analytics-table-sel",  "value"),
    Input("analytics-use-session","n_clicks"),
    State("session-store",        "data"),
    State("analytics-max-rows",   "value"),
    prevent_initial_call=True,
)
def load_analytics_data(table, _, session, max_rows):
    ctx = dash.callback_context
    tid = ctx.triggered_id

    if tid == "analytics-use-session" and session and session.get("records"):
        df = pd.DataFrame(session["records"])
        summary = db.df_summary(df)
        return {"records": df.to_dict("records"), "summary": summary}, \
               dbc.Alert(f"Using session: {session['label']} ({len(df):,} rows)", color="info", dismissable=True, duration=4000)

    if table:
        max_r = int(max_rows or 50000)
        try:
            # Use Dask for large tables
            df = db.query_df(f'SELECT * FROM "{table}" LIMIT {max_r}')
            if len(df) > 10000:
                ddf = dd.from_pandas(df, npartitions=4)
                df  = ddf.compute()  # back to pandas after Dask processing
            summary = db.df_summary(df)
            return {"records": df.head(2000).to_dict("records"), "summary": summary}, \
                   dbc.Alert(f"Loaded `{table}` — {len(df):,} rows", color="success", dismissable=True, duration=4000)
        except Exception as e:
            return dash.no_update, dbc.Alert(f"❌ {e}", color="danger", dismissable=True)

    return dash.no_update, dash.no_update


# ── Render active tab ─────────────────────────────────────────────────────────
@callback(
    Output("analytics-tab-content", "children"),
    Input("analytics-tabs",         "active_tab"),
    Input("analytics-data-store",   "data"),
    State("theme-store",            "data"),
)
def render_tab(active_tab, store, theme):
    tmpl = {"dark": "plotly_dark", "light": "simple_white", "sepia": "ggplot2"}.get(theme or "dark", "plotly_dark")

    if not store or not store.get("records"):
        return dbc.Alert("Load a dataset above to begin.", color="secondary")

    df      = pd.DataFrame(store["records"])
    summary = store.get("summary", {})
    num_cols = summary.get("numeric", [])
    cat_cols = summary.get("text", [])
    date_cols= summary.get("date", [])

    # ── KPI Dashboard ─────────────────────────────────────────────────────
    if active_tab == "kpi-dashboard":
        metrics = []
        for c in num_cols[:6]:
            v = df[c].mean()
            metrics.append(dbc.Col(html.Div([
                html.Div(f"{v:,.2f}", className="nyc-metric-value"),
                html.Div(f"Avg {c}", className="nyc-metric-label"),
            ], className="nyc-metric"), md=2, sm=4, xs=6, className="mb-3"))

        completeness = round((1 - df.isnull().mean().mean()) * 100, 1)
        null_df = pd.DataFrame({
            "column": df.columns,
            "null_pct": (df.isnull().mean() * 100).round(1),
        }).sort_values("null_pct", ascending=False)
        fig_null = px.bar(null_df, x="column", y="null_pct",
                          title="Null % per Column", template=tmpl, height=280,
                          color="null_pct", color_continuous_scale="Reds")
        fig_null.update_layout(margin=dict(l=0, r=0, t=36, b=60),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

        return html.Div([
            dbc.Row([
                dbc.Col(html.Div([html.Div(f"{len(df):,}", className="nyc-metric-value"), html.Div("Rows", className="nyc-metric-label")], className="nyc-metric"), md=2, sm=4, xs=6, className="mb-3"),
                dbc.Col(html.Div([html.Div(str(len(df.columns)), className="nyc-metric-value"), html.Div("Columns", className="nyc-metric-label")], className="nyc-metric"), md=2, sm=4, xs=6, className="mb-3"),
                dbc.Col(html.Div([html.Div(f"{completeness}%", className="nyc-metric-value"), html.Div("Completeness", className="nyc-metric-label")], className="nyc-metric"), md=2, sm=4, xs=6, className="mb-3"),
                dbc.Col(html.Div([html.Div(str(len(num_cols)), className="nyc-metric-value"), html.Div("Numeric Cols", className="nyc-metric-label")], className="nyc-metric"), md=2, sm=4, xs=6, className="mb-3"),
            ] + metrics),
            dcc.Graph(figure=fig_null, config={"displayModeBar": False}),
        ])

    # ── Time Series ───────────────────────────────────────────────────────
    if active_tab == "time-series":
        if not date_cols:
            return dbc.Alert("No date/time columns detected.", color="warning")
        return html.Div([
            dbc.Row([
                dbc.Col(dcc.Dropdown(id="ts-date-col", options=[{"label": c, "value": c} for c in date_cols],
                                     value=date_cols[0], clearable=False,
                                     style={"background": "var(--bg-secondary)"}), md=4),
                dbc.Col(dcc.Dropdown(id="ts-val-col",
                                     options=[{"label": c, "value": c} for c in num_cols],
                                     value=num_cols[0] if num_cols else None,
                                     placeholder="Value column", style={"background": "var(--bg-secondary)"}), md=4),
                dbc.Col(dcc.Dropdown(id="ts-freq",
                                     options=[{"label": f, "value": f} for f in ["D","W","ME","QE","YE"]],
                                     value="ME", clearable=False, style={"background": "var(--bg-secondary)"}), md=4),
            ], className="mb-3"),
            dcc.Loading(dcc.Graph(id="ts-chart", style={"height": "420px"}), type="dot"),
            dcc.Store(id="ts-df-store", data={"records": df.to_dict("records"), "tmpl": tmpl}),
        ])

    # ── Distribution ──────────────────────────────────────────────────────
    if active_tab == "distribution":
        if not num_cols:
            return dbc.Alert("No numeric columns.", color="warning")
        figs = []
        for c in num_cols[:6]:
            fig = px.histogram(df, x=c, marginal="box", template=tmpl,
                               title=c, height=280, nbins=40)
            fig.update_layout(margin=dict(l=0, r=0, t=36, b=0),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              showlegend=False)
            figs.append(dbc.Col(dcc.Graph(figure=fig, config={"displayModeBar": False}), md=6, className="mb-3"))
        return dbc.Row(figs)

    # ── Correlation ───────────────────────────────────────────────────────
    if active_tab == "correlation":
        if len(num_cols) < 2:
            return dbc.Alert("Need ≥2 numeric columns for correlation.", color="warning")
        corr = df[num_cols].corr()
        fig  = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                         zmin=-1, zmax=1, title="Correlation Heatmap",
                         template=tmpl, aspect="auto", height=500)
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)")
        return dcc.Graph(figure=fig)

    # ── Text Analysis ─────────────────────────────────────────────────────
    if active_tab == "text-analysis":
        if not cat_cols:
            return dbc.Alert("No text columns.", color="warning")
        import re
        from collections import Counter
        col  = cat_cols[0]
        text = " ".join(df[col].dropna().astype(str).str.lower())
        freq = Counter(re.findall(r"\b[a-z]{4,}\b", text)).most_common(20)
        wdf  = pd.DataFrame(freq, columns=["word", "count"])
        fig  = px.bar(wdf, x="count", y="word", orientation="h",
                      title=f"Top words in '{col}'", template=tmpl, height=400)
        fig.update_layout(yaxis={"categoryorder": "total ascending"},
                          margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)")
        return dcc.Graph(figure=fig)

    # ── Anomalies ─────────────────────────────────────────────────────────
    if active_tab == "anomalies":
        if not num_cols:
            return dbc.Alert("No numeric columns for anomaly detection.", color="warning")
        # Z-score method via Dask for parallelism
        ddf       = dd.from_pandas(df[num_cols].fillna(0), npartitions=4)
        means     = ddf.mean().compute()
        stds      = ddf.std().compute()
        z_scores  = ((df[num_cols] - means) / stds.replace(0, 1)).abs()
        is_anom   = (z_scores > 3).any(axis=1)
        anom_df   = df[is_anom].head(200)

        count_fig = go.Figure(go.Indicator(
            mode="number+delta",
            value=int(is_anom.sum()),
            delta={"reference": 0},
            title={"text": "Anomalous Rows (Z > 3)"},
            number={"font": {"size": 52, "color": "var(--danger)"}},
        ))
        count_fig.update_layout(template=tmpl, paper_bgcolor="rgba(0,0,0,0)", height=180)

        return html.Div([
            dcc.Graph(figure=count_fig, config={"displayModeBar": False}),
            dag.AgGrid(
                rowData=anom_df.to_dict("records"),
                columnDefs=[{"field": c, "sortable": True, "filter": True, "resizable": True} for c in anom_df.columns],
                defaultColDef={"minWidth": 80},
                dashGridOptions={"pagination": True, "paginationPageSize": 20},
                className="ag-theme-alpine-dark", style={"height": "360px", "width": "100%"},
            ) if not anom_df.empty else dbc.Alert("No anomalies detected.", color="success"),
        ])

    return dbc.Alert("Select a tab.", color="secondary")


# ── Time-series chart callback ────────────────────────────────────────────────
@callback(
    Output("ts-chart", "figure"),
    Input("ts-date-col", "value"),
    Input("ts-val-col",  "value"),
    Input("ts-freq",     "value"),
    State("ts-df-store", "data"),
    prevent_initial_call=True,
)
def update_ts(date_col, val_col, freq, store):
    if not store or not date_col or not val_col:
        return go.Figure()
    tmpl = store.get("tmpl", "plotly_dark")
    df   = pd.DataFrame(store["records"])
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, val_col])
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    agg  = df.set_index(date_col)[val_col].resample(freq).mean().reset_index()
    fig  = px.line(agg, x=date_col, y=val_col, template=tmpl,
                   title=f"{val_col} over time (freq={freq})", height=420)
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig
