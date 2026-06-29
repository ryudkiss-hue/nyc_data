"""Render Phase B–F figures from the REAL precomputed analytics views.

The warehouse now carries genuine statistics (pipeline/analytics/build_phase_analytics.py
→ app_queries.v_phase_*), so the dashboard renders those stored values directly
instead of trying to recompute from raw geometry that the views don't carry. Each
function takes the view DataFrame and returns (figure, S-DIKW narrative).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

_BORO_COLOR = {
    "Manhattan": "#3B82F6", "Brooklyn": "#10B981", "Bronx": "#F59E0B",
    "Queens": "#8B5CF6", "Staten Island": "#EF4444",
}


def _empty(msg: str) -> tuple[go.Figure, str]:
    return go.Figure(), msg


def render_morans_i(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Gauge of the citywide mean Moran's I with a per-borough breakdown."""
    if df is None or df.empty or "morans_i" not in df:
        return _empty("No spatial autocorrelation results available.")
    mean_i = float(df["morans_i"].mean())
    sig = df[df["significance"] < 0.05] if "significance" in df else df.iloc[0:0]
    color = "#EF4444" if mean_i < 0 else ("#EAB308" if mean_i < 0.2 else "#10B981")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(mean_i, 3),
        title={"text": "Moran's I — NTA Infrastructure Density"},
        gauge={"axis": {"range": [-1, 1]}, "bar": {"color": color},
               "steps": [{"range": [-1, -0.2], "color": "rgba(239,68,68,0.15)"},
                         {"range": [-0.2, 0.2], "color": "rgba(234,179,8,0.12)"},
                         {"range": [0.2, 1], "color": "rgba(16,185,129,0.15)"}]}))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=20))
    rows = ", ".join(f"{r.borough} {r.morans_i:+.3f}" for r in df.itertuples())
    klass = "clustering" if mean_i > 0.2 else ("dispersion" if mean_i < -0.2 else "near-random")
    insight = (
        f"**Data:** Moran's I across {len(df)} boroughs ({rows}).\n\n"
        f"**Information:** Citywide mean I = {mean_i:.3f} ({klass}); "
        f"{len(sig)} borough(s) significant at p<0.05.\n\n"
        f"**Knowledge:** Positive I = neighbouring NTAs have similar infrastructure "
        f"density (clustering); negative = a checkerboard pattern.\n\n"
        f"**Wisdom:** {'Target clustered boroughs for corridor-level programs.' if mean_i > 0.2 else 'Density is spatially even; allocate by need, not geography.'}"
    )
    return fig, insight


def render_distribution(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Per-borough skewness bar, coloured by classified distribution type."""
    if df is None or df.empty or "skewness" not in df:
        return _empty("No distribution results available.")
    fig = go.Figure(go.Bar(
        x=df["borough"], y=df["skewness"],
        marker_color=[_BORO_COLOR.get(b, "#64748B") for b in df["borough"]],
        text=df.get("distribution_type"), textposition="outside",
        hovertemplate="%{x}<br>skew=%{y:.2f}<extra></extra>"))
    fig.update_layout(title="Distribution Shape by Borough (skewness)",
                      yaxis_title="Skewness", height=380, template="plotly_white")
    types = ", ".join(f"{r.borough}: {r.distribution_type}" for r in df.itertuples())
    insight = (
        f"**Data:** Distribution of NTA infrastructure density across {len(df)} boroughs.\n\n"
        f"**Information:** {types}.\n\n"
        f"**Knowledge:** |skew|<0.5 ≈ symmetric; skew>1 = a long right tail "
        f"(a few very dense NTAs).\n\n"
        f"**Wisdom:** Right-skewed boroughs concentrate assets in a handful of NTAs — "
        f"check equity of coverage in the long tail."
    )
    return fig, insight


def render_anomalies(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Bar of detected time-series anomalies (z-score) by metric/year."""
    if df is None or df.empty or "zscore" not in df:
        return _empty("No anomalies detected in the tracked time series.")
    metric = df["metric_name"] if "metric_name" in df else df["borough"]
    label = metric.astype(str) + " " + df["year"].astype(str)
    colors = ["#EF4444" if s == "HIGH" else "#F59E0B" for s in df.get("severity", [])]
    fig = go.Figure(go.Bar(x=label, y=df["zscore"], marker_color=colors,
                           text=df.get("outlier_type"), textposition="outside"))
    fig.update_layout(title="Time-Series Anomalies (z-score)", yaxis_title="z-score",
                      height=380, template="plotly_white")
    hi = int((df.get("severity") == "HIGH").sum()) if "severity" in df else 0
    insight = (
        f"**Data:** {len(df)} anomalous metric-years flagged (|z| ≥ 2).\n\n"
        f"**Information:** {hi} HIGH-severity (|z| ≥ 3); the rest MEDIUM.\n\n"
        f"**Knowledge:** A z-score is how many standard deviations a year sits from "
        f"the metric's historical mean.\n\n"
        f"**Wisdom:** Confirm whether flagged drops are real (e.g. partial-year data) "
        f"before acting on them."
    )
    return fig, insight


def render_decomposition(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Trend + residual lines per metric over time (annual → no seasonal term)."""
    if df is None or df.empty or "trend" not in df:
        return _empty("No decomposition results available.")
    keycol = "metric_name" if "metric_name" in df else "borough"
    fig = go.Figure()
    for metric, g in df.groupby(keycol):
        g = g.sort_values("date_key")
        fig.add_trace(go.Scatter(x=g["date_key"], y=g["trend"], mode="lines+markers",
                                 name=f"{metric} trend"))
    fig.update_layout(title="Trend Decomposition by Metric (annual)",
                      xaxis_title="Year", yaxis_title="Trend component",
                      height=400, template="plotly_white")
    metrics = df[keycol].nunique()
    insight = (
        f"**Data:** Linear trend + residual for {metrics} annual metric series.\n\n"
        f"**Information:** Trend lines isolate the multi-year direction from "
        f"year-to-year noise (the residual).\n\n"
        f"**Knowledge:** Annual data has no within-year seasonality, so only "
        f"trend and residual are estimated (no fabricated seasonal wave).\n\n"
        f"**Wisdom:** Rising trends in violations/crashes warrant program review."
    )
    return fig, insight


def render_bootstrap_ci(df: pd.DataFrame) -> tuple[go.Figure, str]:
    """Per-borough point estimate with 95% bootstrap CI error bars."""
    if df is None or df.empty or "point_estimate" not in df:
        return _empty("No bootstrap confidence intervals available.")
    fig = go.Figure(go.Scatter(
        x=df["borough"], y=df["point_estimate"], mode="markers",
        marker=dict(size=12, color=[_BORO_COLOR.get(b, "#64748B") for b in df["borough"]]),
        error_y=dict(type="data", symmetric=False,
                     array=df["ci_upper"] - df["point_estimate"],
                     arrayminus=df["point_estimate"] - df["ci_lower"]),
        name="mean ± 95% CI"))
    fig.update_layout(title="Bootstrap 95% CI — NTA Infrastructure Density",
                      yaxis_title="Mean density (features/NTA)", height=380,
                      template="plotly_white")
    breach = df.get("prob_sla_breach")
    worst = df.loc[breach.idxmax()] if breach is not None and len(breach) else None
    insight = (
        f"**Data:** 2,000-sample bootstrap of mean density for {len(df)} boroughs.\n\n"
        f"**Information:** Every interval satisfies lower ≤ estimate ≤ upper "
        f"(validity-gated).\n\n"
        f"**Knowledge:** Wider intervals = more variable NTAs / smaller samples.\n\n"
        f"**Wisdom:** "
        + (f"{worst.borough} has the highest below-target probability "
           f"({worst.prob_sla_breach:.0%}) — prioritise it." if worst is not None
           else "Use the intervals, not point estimates, when comparing boroughs.")
    )
    return fig, insight
