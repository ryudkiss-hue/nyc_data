"""Geographic Analysis Page Layout — Dash/Plotly + D3 components.

Charts rendered here:
1.  DBSCAN Spatial Clusters       — density-based spatial clustering of inspections
2.  Hex-Bin Density Map           — violation point density via D3 hex-binning
3.  Animated Choropleth           — month-over-month violation density animation
4.  Hot-Block Timeline            — animated horizontal bar of top-k community boards
5.  MoM Heatmap                   — month-over-month change (RdBu diverging)
6.  Conflict Buffer Overlay       — permit-to-inspection proximity scatter on map
7.  Borough Radar                 — multi-metric polygon per borough
8.  Sankey: Borough → Violation   — flow diagram of borough → violation type
9.  Bubble: Cost vs Density       — 4D encoding (x, y, size, color)
10. Treemap: Borough > CB > Status — nested violation hierarchy

All charts render demo data by default; replace _demo_*() with DuckDB queries.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
from dash import dcc, html

# ---------------------------------------------------------------------------
# Demo data factories
# ---------------------------------------------------------------------------

def _demo_geo_df(n: int = 600) -> pd.DataFrame:
    rng = np.random.default_rng(99)
    boroughs = ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]
    centers = {
        "MANHATTAN":     (40.7831, -73.9712),
        "BRONX":         (40.8448, -73.8648),
        "BROOKLYN":      (40.6782, -73.9442),
        "QUEENS":        (40.7282, -73.7949),
        "STATEN ISLAND": (40.5795, -74.1502),
    }
    rows = []
    for _ in range(n):
        b = rng.choice(boroughs)
        clat, clon = centers[b]
        rows.append({
            "borough": b,
            "latitude":  clat + rng.normal(0, 0.03),
            "longitude": clon + rng.normal(0, 0.03),
            "violation_count": int(rng.poisson(5)),
            "repair_cost": float(rng.exponential(3000)),
            "condition_score": float(rng.normal(60, 18).clip(0, 100)),
            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 540))),
            "status": rng.choice(["Open", "Pending Repair", "Complete", "Dismissed"]),
            "community_board": int(rng.integers(101, 520)),
            "violation_type": rng.choice(["Trip Hazard", "Cracked Slab", "ADA Non-Compliance", "Raised Lip", "Depression"]),
        })
    return pd.DataFrame(rows)


def _safe_fig(fn):
    try:
        return fn()
    except Exception as e:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(text=f"Chart unavailable: {e}", showarrow=False)
        return fig


def _dbscan_fig():
    import plotly.express as px
    from sklearn.cluster import DBSCAN
    df = _demo_geo_df(500)
    coords = df[["latitude", "longitude"]].values
    eps_deg = 0.015  # ~1.5 km
    labels = DBSCAN(eps=eps_deg, min_samples=5).fit_predict(coords)
    df["cluster"] = labels.astype(str)
    df.loc[df["cluster"] == "-1", "cluster"] = "Noise"
    fig = px.scatter_map(
        df, lat="latitude", lon="longitude",
        color="cluster", size="violation_count",
        hover_data=["borough", "violation_count"],
        map_style="carto-positron",
        zoom=9, center={"lat": 40.71, "lon": -74.0},
        title="DBSCAN Spatial Clusters — Inspection Hotspots",
        height=420,
    )
    return fig


def _animated_choropleth_fig():
    from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer
    df = _demo_geo_df(600)
    # Reformat to match expected columns
    df["violation_count"] = df["violation_count"].astype(int)
    viz = TemporalGeospatialVisualizer(df, period="month")
    return viz.plot_hot_blocks_timeline(top_k=8)


def _mom_heatmap_fig():
    from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer
    df = _demo_geo_df(600)
    df["violation_count"] = df["violation_count"].astype(int)
    viz = TemporalGeospatialVisualizer(df, period="month")
    return viz.plot_month_over_month_heatmap()


def _conflict_scatter_fig():
    import plotly.express as px
    df = _demo_geo_df(400)
    df["conflict_distance_m"] = np.random.exponential(120, len(df))
    fig = px.scatter_map(
        df, lat="latitude", lon="longitude",
        color="conflict_distance_m",
        color_continuous_scale="RdYlGn_r",
        size="violation_count",
        hover_data=["borough", "conflict_distance_m"],
        map_style="carto-darkmatter",
        zoom=9, center={"lat": 40.71, "lon": -74.0},
        title="Conflict Buffer Overlay — Permit-to-Inspection Distance (m)",
        height=420,
    )
    return fig


def _radar_fig():
    from socrata_toolkit.viz.advanced_multidim import radar_chart
    df = _demo_geo_df(500)
    return radar_chart(
        df,
        group_col="borough",
        metric_cols=["violation_count", "repair_cost", "condition_score"],
        title="Borough Radar — Multi-Metric Comparison (Normalised)",
    )


def _sankey_fig():
    from socrata_toolkit.viz.advanced_multidim import sankey_flow
    df = _demo_geo_df(500)
    return sankey_flow(
        df, source_col="borough", target_col="violation_type",
        title="Sankey: Borough → Violation Type Flow",
    )


def _bubble_fig():
    from socrata_toolkit.viz.advanced_multidim import bubble_chart
    df = _demo_geo_df(300)
    agg = df.groupby("community_board").agg(
        violation_count=("violation_count", "sum"),
        repair_cost=("repair_cost", "mean"),
        condition_score=("condition_score", "mean"),
        borough=("borough", "first"),
    ).reset_index()
    return bubble_chart(
        agg,
        x_col="condition_score",
        y_col="repair_cost",
        size_col="violation_count",
        color_col="borough",
        hover_name_col="community_board",
        title="Bubble: Condition Score vs Repair Cost (bubble = violation count)",
    )


def _treemap_fig():
    import plotly.express as px

    df = _demo_geo_df(500)
    fig = px.treemap(
        df,
        path=["borough", "violation_type", "status"],
        values="violation_count",
        color="condition_score",
        color_continuous_scale="RdYlGn",
        title="Treemap: Borough → Violation Type → Status",
    )
    fig.update_layout(template="plotly_white", height=420)
    return fig


# ---------------------------------------------------------------------------
# Hex-bin D3 embed helper
# ---------------------------------------------------------------------------

def _hex_html() -> str:
    from socrata_toolkit.viz.d3_components import hex_binmap
    df = _demo_geo_df(800)
    return hex_binmap(df, title="Hex-Bin Spatial Density — Violation Points")


# ---------------------------------------------------------------------------
# Layout card factory
# ---------------------------------------------------------------------------

def _chart_card(figure_fn, label: str, col_width: int = 6, height: int = 420) -> dbc.Col:
    fig = _safe_fig(figure_fn)
    return dbc.Col([
        dbc.Card([
            dbc.CardHeader(label, className="fw-semibold text-secondary small"),
            dbc.CardBody([
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": True, "scrollZoom": True},
                    style={"height": f"{height}px"},
                ),
            ], className="p-1"),
        ], className="shadow-sm mb-3"),
    ], width=col_width)


def _d3_card(html_content: str, label: str, col_width: int = 6, height: int = 460) -> dbc.Col:
    return dbc.Col([
        dbc.Card([
            dbc.CardHeader(label, className="fw-semibold text-secondary small"),
            dbc.CardBody([
                html.Iframe(
                    srcDoc=html_content,
                    style={"width": "100%", "height": f"{height}px", "border": "none"},
                ),
            ], className="p-1"),
        ], className="shadow-sm mb-3"),
    ], width=col_width)


# ---------------------------------------------------------------------------
# Page Layout
# ---------------------------------------------------------------------------

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Geographic Analysis", className="mb-1 fw-bold"),
            html.P(
                "Spatial depth: DBSCAN clustering, hex-bin density, temporal animation, "
                "conflict buffer overlays, Sankey borough flows, radar comparison, "
                "bubble-encoded community board metrics, and nested treemaps.",
                className="text-muted mb-3",
            ),
        ], width=12),
    ]),

    # Row 1 — Spatial clusters + conflict overlay
    dbc.Row([
        _chart_card(_dbscan_fig, "DBSCAN Spatial Clusters — Inspection Hotspots", col_width=6),
        _chart_card(_conflict_scatter_fig, "Conflict Buffer Overlay — Permit Proximity", col_width=6),
    ]),

    # Row 2 — Animated charts
    dbc.Row([
        _chart_card(_animated_choropleth_fig, "Animated Hot-Block Timeline (Top-8 Community Boards)", col_width=7),
        _chart_card(_mom_heatmap_fig, "Month-over-Month Change Heatmap", col_width=5),
    ]),

    # Row 3 — D3 hex-bin + Sankey
    dbc.Row([
        _d3_card(
            _safe_fig(_hex_html) if callable(_hex_html) else _hex_html(),
            "D3 Hex-Bin Density — Violation Point Concentration",
            col_width=6,
        ),
        _chart_card(_sankey_fig, "Sankey: Borough → Violation Type Flow", col_width=6),
    ]),

    # Row 4 — Radar + Bubble
    dbc.Row([
        _chart_card(_radar_fig, "Borough Radar — Multi-Metric Spider Chart", col_width=5),
        _chart_card(_bubble_fig, "Bubble: Condition vs Cost vs Volume", col_width=7),
    ]),

    # Row 5 — Treemap full width
    dbc.Row([
        _chart_card(_treemap_fig, "Nested Treemap: Borough → Violation Type → Status", col_width=12, height=480),
    ]),

], fluid=True, className="mt-4")
