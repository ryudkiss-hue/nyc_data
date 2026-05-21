"""dash_app/pages/analytics.py — Analytics page with Plotly + DuckDB + Dask"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Any, Final

import dash
import dash_bootstrap_components as dbc
import dask.dataframe as dd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from dash_app.data import db

_DEBUG = os.getenv("NYC_DOT_DEBUG", "").lower() in ("1", "true", "yes")
if _DEBUG:
    dash.register_page(__name__, path="/analytics", name="Analytics", order=1)

TABS: Final[list[str]] = [
    "KPI Dashboard",
    "Time Series",
    "Distribution",
    "Correlation",
    "Text Analysis",
    "Anomalies",
]

TEXT_MUTED: Final[str] = "var(--text-muted)"
FONT_SIZE_SM: Final[str] = "0.78rem"

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("📊 Analytics", className="nyc-page-title"),
                html.P(
                    "Statistical analysis, time-series trends, and anomaly detection powered by DuckDB + Dask.",
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
                                "fontSize": FONT_SIZE_SM,
                                "fontWeight": 600,
                                "color": TEXT_MUTED,
                            },
                        ),
                        dcc.Dropdown(
                            id="analytics-table-sel",
                            placeholder="Select a DuckDB table…",
                            style={
                                "background": "var(--bg-secondary)",
                                "color": "var(--text-primary)",
                            },
                        ),
                    ],
                    md=5,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Or use session dataset",
                            style={
                                "fontSize": FONT_SIZE_SM,
                                "fontWeight": 600,
                                "color": TEXT_MUTED,
                            },
                        ),
                        dbc.Button(
                            "Use Active Dataset",
                            id="analytics-use-session",
                            color="primary",
                            outline=True,
                            size="sm",
                            className="mt-1",
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Max rows (Dask)",
                            style={
                                "fontSize": FONT_SIZE_SM,
                                "fontWeight": 600,
                                "color": TEXT_MUTED,
                            },
                        ),
                        dbc.Input(
                            id="analytics-max-rows",
                            type="number",
                            value=50000,
                            min=1000,
                            max=1000000,
                            size="sm",
                        ),
                    ],
                    md=3,
                ),
            ],
            className="mb-3",
        ),
        dcc.Loading(html.Div(id="analytics-load-status"), type="dot"),
        dbc.Tabs(
            [dbc.Tab(label=t, tab_id=t.lower().replace(" ", "-")) for t in TABS],
            id="analytics-tabs",
            active_tab="kpi-dashboard",
            className="nyc-tabs mb-3",
        ),
        html.Div(id="analytics-tab-content"),
        # Hidden stores
        dcc.Store(id="analytics-data-store"),
    ],
    fluid=True,
)


# ── Populate table dropdown ───────────────────────────────────────────────────
@callback(Output("analytics-table-sel", "options"), Input("session-store", "data"))
def populate_tables(_: Any) -> list[dict[str, str]]:
    return [{"label": t, "value": t} for t in db.list_tables()]


# ── Load dataset into analytics store ────────────────────────────────────────
@callback(
    Output("analytics-data-store", "data"),
    Output("analytics-load-status", "children"),
    Input("analytics-table-sel", "value"),
    Input("analytics-use-session", "n_clicks"),
    State("session-store", "data"),
    State("analytics-max-rows", "value"),
    prevent_initial_call=True,
)
def load_analytics_data(
    table: str | None, _: int | None, session: dict[str, Any] | None, max_rows: int | None
) -> tuple[Any, Any]:
    ctx = dash.callback_context
    tid = ctx.triggered_id

    if tid == "analytics-use-session" and session and session.get("records"):
        df = pd.DataFrame(session["records"])
        summary = db.df_summary(df)
        return {"records": df.to_dict("records"), "summary": summary}, dbc.Alert(
            f"Using session: {session['label']} ({len(df):,} rows)",
            color="info",
            dismissable=True,
            duration=4000,
        )

    if table:
        max_r = int(max_rows or 50000)
        try:
            # Use Dask for large tables
            df = db.query_df(f'SELECT * FROM "{table}" LIMIT {max_r}')
            if len(df) > 10000:
                ddf = dd.from_pandas(df, npartitions=4)
                df = ddf.compute()  # back to pandas after Dask processing
            summary = db.df_summary(df)
            return {"records": df.head(2000).to_dict("records"), "summary": summary}, dbc.Alert(
                f"Loaded `{table}` — {len(df):,} rows",
                color="success",
                dismissable=True,
                duration=4000,
            )
        except Exception as e:
            return dash.no_update, dbc.Alert(f"Error: {e}", color="danger")

    return dash.no_update, dash.no_update


# ── Render active tab ─────────────────────────────────────────────────────────
@callback(
    Output("analytics-tab-content", "children"),
    Input("analytics-tabs", "active_tab"),
    Input("analytics-data-store", "data"),
    State("theme-store", "data"),
)
def render_tab(active_tab: str, store: dict[str, Any] | None, theme: Any) -> Any:
    _ = theme  # Unused for now
    if not store or not store.get("records"):
        return dbc.Alert("Load a dataset above to begin.", color="secondary")

    from socrata_toolkit import analysis as st_analysis

    df = pd.DataFrame(store["records"])
    summary = store.get("summary", {})
    num_cols = summary.get("numeric", [])
    cat_cols = summary.get("text", [])
    date_cols = summary.get("date", [])

    # ── KPI Dashboard ─────────────────────────────────────────────────────
    if active_tab == "kpi-dashboard":
        metrics = []
        for c in num_cols[:4]:
            val = df[c].mean()
            metrics.append(
                dbc.Col(
                    dcc.Graph(
                        figure=st_analysis.gauge_chart(val, title=f"Avg {c.title()}"),
                        config={"displayModeBar": False},
                    ),
                    md=3,
                    className="mb-3",
                )
            )

        # Completeness gauge
        completeness = round((1 - df.isnull().mean().mean()) * 100, 1)
        metrics.append(
            dbc.Col(
                dcc.Graph(
                    figure=st_analysis.gauge_chart(
                        completeness, target=95.0, title="Data Completeness %"
                    ),
                    config={"displayModeBar": False},
                ),
                md=3,
                className="mb-3",
            )
        )

        return html.Div(
            [
                dbc.Row(metrics),
                html.Div(className="divider-nyc"),
                dbc.Row(
                    [
                        (
                            dbc.Col(
                                dcc.Graph(
                                    figure=st_analysis.bar_chart(
                                        df, cat_cols[0], title="Top Categories"
                                    )
                                ),
                                md=6,
                            )
                            if cat_cols
                            else None
                        ),
                        (
                            dbc.Col(
                                dcc.Graph(
                                    figure=st_analysis.histogram(
                                        df, num_cols[0], title="Value Distribution"
                                    )
                                ),
                                md=6,
                            )
                            if num_cols
                            else None
                        ),
                    ]
                ),
            ]
        )

    # ── Time Series ───────────────────────────────────────────────────────
    if active_tab == "time-series":
        if not date_cols:
            return dbc.Alert("No date/time columns detected.", color="warning")

        # Use high-performance Scattergl time series from toolkit
        val_col = num_cols[0] if num_cols else None
        if not val_col:
            return dbc.Alert("No numeric columns for Y-axis.", color="warning")

        fig = st_analysis.time_series_chart(df, date_cols[0], val_col)
        return html.Div(
            [
                dcc.Graph(figure=fig, style={"height": "600px"}),
            ]
        )

    # ── Distribution ──────────────────────────────────────────────────────
    if active_tab == "distribution":
        if not num_cols:
            return dbc.Alert("No numeric columns.", color="warning")
        figs = []
        for c in num_cols[:4]:
            fig = st_analysis.histogram(df, c)
            figs.append(
                dbc.Col(
                    dcc.Graph(figure=fig, config={"displayModeBar": False}), md=6, className="mb-3"
                )
            )
        return dbc.Row(figs)

    # ── Correlation ───────────────────────────────────────────────────────
    if active_tab == "correlation":
        return dcc.Graph(figure=st_analysis.correlation_heatmap(df))

    return dbc.Alert("Select a tab.", color="secondary")


# ── Time-series chart callback ────────────────────────────────────────────────
@callback(
    Output("ts-chart", "figure"),
    Input("ts-date-col", "value"),
    Input("ts-val-col", "value"),
    Input("ts-freq", "value"),
    State("ts-df-store", "data"),
    prevent_initial_call=True,
)
def update_ts(date_col, val_col, freq, store):
    if not store or not date_col or not val_col:
        return go.Figure()
    tmpl = store.get("tmpl", "plotly_dark")
    df = pd.DataFrame(store["records"])
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, val_col])
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    agg = df.set_index(date_col)[val_col].resample(freq).mean().reset_index()
    fig = px.line(
        agg,
        x=date_col,
        y=val_col,
        template=tmpl,
        title=f"{val_col} over time (freq={freq})",
        height=420,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
