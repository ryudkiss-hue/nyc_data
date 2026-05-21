"""dash_app/pages/geospatial.py — Interactive map views, clustering, density heatmap"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dcc, html

from dash_app.data import db

_DEBUG = os.getenv("NYC_DOT_DEBUG", "").lower() in ("1", "true", "yes")
if _DEBUG:
    dash.register_page(__name__, path="/geospatial", name="Geospatial", order=6)

_LAT_HINTS = ["lat", "latitude", "y_coord", "y_coordinate", "geo_lat"]
_LON_HINTS = ["lon", "lng", "long", "longitude", "x_coord", "x_coordinate", "geo_lon"]

MAPBOX_STYLES = {"dark": "carto-darkmatter", "light": "carto-positron", "sepia": "stamen-terrain"}

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("🗺️ Geospatial", className="nyc-page-title"),
                html.P(
                    "Interactive NYC maps, KMeans clustering, and density heatmaps — powered by Plotly Mapbox + DuckDB.",
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
                            id="geo-table-sel",
                            placeholder="Select DuckDB table…",
                            style={"background": "var(--bg-secondary)"},
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Latitude column",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Dropdown(id="geo-lat-sel", style={"background": "var(--bg-secondary)"}),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Longitude column",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Dropdown(id="geo-lon-sel", style={"background": "var(--bg-secondary)"}),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Label(
                            "Color by",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Dropdown(
                            id="geo-color-sel",
                            placeholder="(none)",
                            style={"background": "var(--bg-secondary)"},
                        ),
                    ],
                    md=3,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label(
                            "K clusters",
                            style={
                                "fontSize": "0.78rem",
                                "fontWeight": 600,
                                "color": "var(--text-muted)",
                            },
                        ),
                        dcc.Slider(
                            id="geo-k-slider",
                            min=2,
                            max=12,
                            step=1,
                            value=5,
                            marks={i: str(i) for i in range(2, 13, 2)},
                            tooltip={"placement": "bottom"},
                        ),
                    ],
                    md=4,
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
                        dbc.Input(
                            id="geo-max-rows",
                            type="number",
                            value=5000,
                            min=100,
                            max=50000,
                            size="sm",
                        ),
                    ],
                    md=2,
                ),
                dbc.Col(
                    [
                        html.Div(style={"height": "22px"}),
                        dbc.Button(
                            "🗺️ Render Map",
                            id="geo-render-btn",
                            color="primary",
                            size="sm",
                            className="me-2",
                        ),
                    ],
                    md=6,
                ),
            ],
            className="mb-3",
        ),
        dcc.Loading(html.Div(id="geo-status"), type="dot"),
        dbc.Tabs(
            [
                dbc.Tab(label="📍 Point Map", tab_id="points", className="nyc-tabs"),
                dbc.Tab(label="🔵 Clusters", tab_id="clusters", className="nyc-tabs"),
                dbc.Tab(label="🌡️ Density", tab_id="density", className="nyc-tabs"),
                dbc.Tab(label="📊 Borough Stats", tab_id="borough", className="nyc-tabs"),
            ],
            id="geo-tabs",
            active_tab="points",
            className="nyc-tabs mb-3",
        ),
        dcc.Loading(html.Div(id="geo-map-content"), type="circle", color="var(--accent)"),
        dcc.Store(id="geo-data-store"),
    ],
    fluid=True,
)


@callback(Output("geo-table-sel", "options"), Input("session-store", "data"))
def populate_tables(_):
    return [{"label": t, "value": t} for t in db.list_tables()]


@callback(
    Output("geo-lat-sel", "options"),
    Output("geo-lon-sel", "options"),
    Output("geo-color-sel", "options"),
    Output("geo-lat-sel", "value"),
    Output("geo-lon-sel", "value"),
    Input("geo-table-sel", "value"),
    prevent_initial_call=True,
)
def populate_cols(table):
    if not table:
        return [], [], [], None, None
    df = db.query_df(f'SELECT * FROM "{table}" LIMIT 1')
    cols = list(df.columns)
    opts = [{"label": c, "value": c} for c in cols]
    lat = next((c for c in cols if any(h in c.lower() for h in _LAT_HINTS)), None)
    lon = next((c for c in cols if any(h in c.lower() for h in _LON_HINTS)), None)
    return opts, opts, [{"label": "(none)", "value": ""}] + opts, lat, lon


@callback(
    Output("geo-data-store", "data"),
    Output("geo-status", "children"),
    Input("geo-render-btn", "n_clicks"),
    State("geo-table-sel", "value"),
    State("geo-lat-sel", "value"),
    State("geo-lon-sel", "value"),
    State("geo-color-sel", "value"),
    State("geo-max-rows", "value"),
    prevent_initial_call=True,
)
def load_geo(_, table, lat_col, lon_col, color_col, max_rows):
    if not all([table, lat_col, lon_col]):
        return dash.no_update, dbc.Alert("Select dataset, lat, and lon columns.", color="warning")
    try:
        df = db.query_df(f'SELECT * FROM "{table}" LIMIT {int(max_rows or 5000)}')
        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
        df = df.dropna(subset=[lat_col, lon_col])
        df = df[(df[lat_col].between(40.4, 41.0)) & (df[lon_col].between(-74.3, -73.6))]
        store = {
            "records": df.to_dict("records"),
            "lat": lat_col,
            "lon": lon_col,
            "color": color_col or "",
            "rows": len(df),
        }
        return store, dbc.Alert(
            f"✅ {len(df):,} points with valid coordinates",
            color="success",
            dismissable=True,
            duration=4000,
        )
    except Exception as e:
        return dash.no_update, dbc.Alert(f"❌ {e}", color="danger", dismissable=True)


@callback(
    Output("geo-map-content", "children"),
    Input("geo-tabs", "active_tab"),
    Input("geo-data-store", "data"),
    State("geo-k-slider", "value"),
    State("theme-store", "data"),
)
def render_map(tab, store, k, theme):
    if not store or not store.get("records"):
        return dbc.Alert("Configure and click 'Render Map' above.", color="secondary")

    import socrata_toolkit.analysis as st_analysis
    import socrata_toolkit.spatial as st_spatial

    df = pd.DataFrame(store["records"])
    lat_col = store["lat"]
    lon_col = store["lon"]
    color = store.get("color") or None

    # ── Point Map ───────────────────────────────────────────────────────
    if tab == "points":
        viz = st_spatial.SpatialVisualization(df)
        fig = viz.plot_scatter_map(lat_col, lon_col, color_col=color)
        return html.Div(
            [
                dcc.Graph(figure=fig, style={"height": "750px"}),
            ],
            className="nyc-animate-fade-up",
        )

    # ── Clusters ────────────────────────────────────────────────────────
    if tab == "clusters":
        try:
            from sklearn.cluster import KMeans

            coords = df[[lat_col, lon_col]].values
            km = KMeans(n_clusters=int(k), random_state=42, n_init=10).fit(coords)
            df = df.copy()
            df["cluster"] = km.labels_.astype(str)

            viz = st_spatial.SpatialVisualization(df)
            fig = viz.plot_scatter_map(
                lat_col, lon_col, color_col="cluster", title=f"K-Means Clusters (k={k})"
            )

            summary = df.groupby("cluster").size().reset_index(name="points")
            grid = dag.AgGrid(
                rowData=summary.to_dict("records"),
                columnDefs=[{"field": c} for c in summary.columns],
                dashGridOptions={"domLayout": "autoHeight"},
                className="ag-theme-alpine-dark",
                style={"marginTop": "12px"},
            )
            return html.Div(
                [dcc.Graph(figure=fig, style={"height": "650px"}), grid],
                className="nyc-animate-fade-up",
            )
        except ImportError:
            return dbc.Alert("Install scikit-learn for clustering.", color="warning")

    # ── Density ─────────────────────────────────────────────────────────
    if tab == "density":
        viz = st_spatial.SpatialVisualization(df)
        fig = viz.plot_heatmap(lat_col, lon_col)
        return html.Div(
            [
                dcc.Graph(figure=fig, style={"height": "750px"}),
            ],
            className="nyc-animate-fade-up",
        )

    # ── ADA Compliance Map ──────────────────────────────────────────────
    if tab == "borough":  # Re-purposing tab for ADA
        fig = st_analysis.plot_ada_compliance_map(df, lat_col, lon_col)
        return html.Div(
            [
                dbc.Alert(
                    "NYC SDM Accessibility Audit: Identifies compliant (green) and non-compliant (red) infrastructure segments.",
                    color="info",
                    className="mb-2",
                ),
                dcc.Graph(figure=fig, style={"height": "750px"}),
            ],
            className="nyc-animate-fade-up",
        )

    return html.Div()
