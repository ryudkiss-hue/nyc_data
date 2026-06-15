"""Advanced Analytics Page Layout — Dash/Plotly implementation.

Charts rendered here:
1. CUSUM Control Chart          — process-shift detection on violation counts
2. Bayesian Posterior Strip     — HDI credible intervals for modelled parameters
3. Moran's I Scatter Plot       — spatial autocorrelation of violation density
4. Parallel Coordinates         — multi-variate inspection profiling
5. Scatter Plot Matrix (SPLOM)  — pairwise metric relationships
6. Clustermap                   — Ward-clustered borough×metric heatmap
7. Ridge Plot                   — KDE distributions per borough
8. Changepoint Overlay          — multi-borough time-series with shift markers
9. HDI-Annotated Violin         — posterior-annotated distributional comparison
10. Inspection Pipeline Funnel  — inspection → violation → dismissal stages

All charts operate on synthetic demo data when no live dataset is loaded.
Wire real data by updating the `_demo_df()` and `_demo_*()` helpers or
connecting them to a DuckDB query in the callbacks bridge.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
from dash import dcc, html

# ---------------------------------------------------------------------------
# Demo data factories (replaced by live data in production callbacks)
# ---------------------------------------------------------------------------

def _demo_df(n: int = 500) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    boroughs = ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]
    materials = ["Concrete", "Brick", "Asphalt", "Granite", "Stone"]
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "borough": rng.choice(boroughs, n),
        "material_type": rng.choice(materials, n),
        "violation_count": rng.poisson(4, n),
        "repair_cost": rng.exponential(2500, n),
        "condition_score": rng.normal(65, 15, n).clip(0, 100),
        "age_years": rng.uniform(5, 40, n),
        "community_board": rng.integers(101, 520, n),
    })


def _cusum_fig():
    from socrata_toolkit.viz.statistical_viz import cusum_control_chart
    df = _demo_df(200)
    series = df.groupby("date")["violation_count"].sum().sort_index()
    return cusum_control_chart(series, title="CUSUM Control Chart — Daily Violation Counts")


def _parallel_coords_fig():
    from socrata_toolkit.viz.advanced_multidim import parallel_coordinates
    df = _demo_df(400)
    return parallel_coordinates(
        df,
        dimensions=["violation_count", "repair_cost", "condition_score", "age_years"],
        color_col="borough",
        title="Parallel Coordinates — Multi-Variate Inspection Profile",
    )


def _splom_fig():
    from socrata_toolkit.viz.advanced_multidim import scatter_plot_matrix
    df = _demo_df(600)
    return scatter_plot_matrix(
        df,
        dimensions=["violation_count", "repair_cost", "condition_score", "age_years"],
        color_col="borough",
        title="Scatter Plot Matrix — Pairwise Inspection Metrics",
    )


def _clustermap_fig():
    from socrata_toolkit.viz.advanced_multidim import clustermap
    df = _demo_df(500)
    return clustermap(
        df,
        row_key="borough",
        value_cols=["violation_count", "repair_cost", "condition_score", "age_years"],
        title="Clustermap — Borough × Metric Similarity",
    )


def _ridge_fig():
    from socrata_toolkit.viz.statistical_viz import ridge_plot
    df = _demo_df(500)
    return ridge_plot(df, value_col="violation_count", group_col="borough",
                      title="Ridge Plot — Violation Count Distribution by Borough")


def _changepoint_fig():
    from socrata_toolkit.viz.statistical_viz import changepoint_overlay
    df = _demo_df(300)
    return changepoint_overlay(df, date_col="date", value_col="violation_count",
                               group_col="borough",
                               title="Changepoint Overlay — Violation Counts by Borough")


def _violin_fig():
    from socrata_toolkit.viz.statistical_viz import hdi_violin
    df = _demo_df(500)
    return hdi_violin(df, value_col="condition_score", group_col="borough",
                      title="HDI-Annotated Violin — Condition Score by Borough")


def _funnel_fig():
    from socrata_toolkit.viz.advanced_multidim import inspection_funnel
    return inspection_funnel(
        stage_labels=["Inspections Filed", "Violations Issued", "Reinspected", "Dismissed", "Resolved"],
        stage_counts=[398000, 312000, 36000, 85000, 210000],
        title="SIM Inspection Pipeline Funnel (2026 YTD)",
    )


def _moran_fig():
    from socrata_toolkit.viz.statistical_viz import moran_scatter_plot
    df = _demo_df(300)
    return moran_scatter_plot(df, value_col="violation_count", borough_col="borough",
                              title="Moran's I — Spatial Autocorrelation of Violation Counts")


def _posterior_fig():
    from socrata_toolkit.viz.statistical_viz import bayesian_posterior_strip
    rng = np.random.default_rng(7)
    trace_df = pd.DataFrame({
        "Intercept": rng.normal(1.2, 0.3, 2000),
        "Borough Effect": rng.normal(0.4, 0.2, 2000),
        "Age Effect": rng.normal(0.07, 0.04, 2000),
        "Material Effect": rng.normal(-0.15, 0.08, 2000),
    })
    return bayesian_posterior_strip(
        trace_df,
        param_cols=list(trace_df.columns),
        title="Bayesian Posterior — 89% HDI Credible Intervals",
    )


# ---------------------------------------------------------------------------
# Pre-render all charts (static render at import; swap for callbacks in prod)
# ---------------------------------------------------------------------------

def _safe_fig(fn):
    try:
        return fn()
    except Exception as e:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_annotation(text=f"Chart unavailable: {e}", showarrow=False)
        return fig


_FIGS = {
    "cusum":      lambda: _safe_fig(_cusum_fig),
    "parallel":   lambda: _safe_fig(_parallel_coords_fig),
    "splom":      lambda: _safe_fig(_splom_fig),
    "clustermap": lambda: _safe_fig(_clustermap_fig),
    "ridge":      lambda: _safe_fig(_ridge_fig),
    "changepoint":lambda: _safe_fig(_changepoint_fig),
    "violin":     lambda: _safe_fig(_violin_fig),
    "funnel":     lambda: _safe_fig(_funnel_fig),
    "moran":      lambda: _safe_fig(_moran_fig),
    "posterior":  lambda: _safe_fig(_posterior_fig),
}


def _chart_card(fig_key: str, label: str, col_width: int = 6) -> dbc.Col:
    return dbc.Col([
        dbc.Card([
            dbc.CardHeader(label, className="fw-semibold text-secondary small"),
            dbc.CardBody([
                dcc.Graph(
                    figure=_FIGS[fig_key](),
                    config={"displayModeBar": True, "scrollZoom": True},
                    style={"height": "420px"},
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
            html.H2("Advanced Analytics", className="mb-1 fw-bold"),
            html.P(
                "Statistical depth: CUSUM control charts, Bayesian posterior inference, "
                "Moran's I spatial autocorrelation, multi-variate crossfilter exploration, "
                "ridge plots, and changepoint detection.",
                className="text-muted mb-3",
            ),
        ], width=12),
    ]),

    # Row 1 — Process quality
    dbc.Row([
        _chart_card("cusum", "CUSUM Control Chart — Violation Count Process Shifts", col_width=7),
        _chart_card("posterior", "Bayesian Posterior — Parameter HDI Credible Intervals", col_width=5),
    ]),

    # Row 2 — Multi-variate exploration
    dbc.Row([
        _chart_card("parallel", "Parallel Coordinates — Multi-Variate Profiling", col_width=7),
        _chart_card("moran", "Moran's I — Spatial Autocorrelation", col_width=5),
    ]),

    # Row 3 — Pairwise + cluster
    dbc.Row([
        _chart_card("splom", "Scatter Plot Matrix (SPLOM)", col_width=6),
        _chart_card("clustermap", "Clustermap — Ward Hierarchical Similarity", col_width=6),
    ]),

    # Row 4 — Distributions
    dbc.Row([
        _chart_card("ridge", "Ridge Plot — KDE Distribution by Borough", col_width=6),
        _chart_card("violin", "HDI-Annotated Violin — Condition Score", col_width=6),
    ]),

    # Row 5 — Temporal + pipeline
    dbc.Row([
        _chart_card("changepoint", "Changepoint Overlay — Temporal Shifts", col_width=8),
        _chart_card("funnel", "Inspection Pipeline Funnel", col_width=4),
    ]),

], fluid=True, className="mt-4")
