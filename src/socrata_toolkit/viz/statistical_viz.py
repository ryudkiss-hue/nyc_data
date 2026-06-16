"""Statistical visualization layer for NYC DOT SIM Division.

Exposes publication-quality charts for the statistical models that already
exist in ``socrata_toolkit.analysis`` but previously had no dedicated viz:

- CUSUM control chart  (wraps changepoint.detect_cusum_changepoint)
- Bayesian posterior / credible-interval strip plots  (wraps analysis.bayesian)
- Moran's I spatial autocorrelation plot  (global + LISA quadrant map)
- Ridge / joy plots  (distributional comparison across boroughs or materials)
- Violin + half-eye plots  (HDI-annotated distribution)
- Change-point annotation overlay  (multi-series with vertical markers)

All functions return Plotly Figure objects.

Example::

    from socrata_toolkit.viz.statistical_viz import (
        cusum_control_chart,
        bayesian_posterior_strip,
        moran_scatter_plot,
        ridge_plot,
        changepoint_overlay,
    )
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .units import get_unit_label


def _go():
    try:
        import plotly.graph_objects as go
        return go
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc


def _px():
    try:
        import plotly.express as px
        return px
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc


# ---------------------------------------------------------------------------
# CUSUM Control Chart
# ---------------------------------------------------------------------------

def cusum_control_chart(
    series: pd.Series,
    title: str | None = None,
    k: float | None = None,
    h: float | None = None,
    annotate_changepoint: bool = True,
) -> Any:
    """Two-sided CUSUM control chart with optional tabular CUSUM decision boundaries.

    Plots the raw series, the CUSUM accumulation, and—when ``annotate_changepoint``
    is True—a vertical marker at the detected shift point.

    Args:
        series: Time-ordered numeric series (index = observation order or dates).
        title: Chart title.
        k: Allowance parameter for tabular CUSUM (defaults to 0.5 × sigma).
        h: Decision threshold (defaults to 5 × sigma).
        annotate_changepoint: Draw a vertical red line at the detected shift.

    Returns:
        Plotly Figure with two stacked subplots: raw series (top) + CUSUM (bottom).
    """
    from plotly.subplots import make_subplots

    go = _go()

    from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

    mu = series.mean()
    sigma = series.std() or 1.0
    k = k if k is not None else 0.5 * sigma
    h = h if h is not None else 5.0 * sigma

    # Two-sided tabular CUSUM
    cusum_pos = np.zeros(len(series))
    cusum_neg = np.zeros(len(series))
    for i in range(1, len(series)):
        cusum_pos[i] = max(0, cusum_pos[i - 1] + (series.iloc[i] - mu) - k)
        cusum_neg[i] = max(0, cusum_neg[i - 1] - (series.iloc[i] - mu) - k)

    cp_idx = detect_cusum_changepoint(series)
    x_vals = list(range(len(series)))

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=["Observed Values", "CUSUM Accumulation"],
        row_heights=[0.45, 0.55],
        vertical_spacing=0.08,
    )

    # Row 1: raw series + mean line
    fig.add_trace(
        go.Scatter(x=x_vals, y=series.values, mode="lines", name="Observed",
                   line=dict(color="#003366", width=1.5)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=x_vals, y=[mu] * len(x_vals), mode="lines",
                   name="Target Mean", line=dict(color="#6c757d", dash="dot")),
        row=1, col=1,
    )

    # Row 2: CUSUM+ and CUSUM-
    fig.add_trace(
        go.Scatter(x=x_vals, y=cusum_pos, mode="lines", name="CUSUM+",
                   line=dict(color="#28a745", width=1.5)),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(x=x_vals, y=cusum_neg, mode="lines", name="CUSUM−",
                   line=dict(color="#dc3545", width=1.5)),
        row=2, col=1,
    )
    # Decision threshold bands
    fig.add_hline(y=h, line_dash="dash", line_color="#dc3545",
                  annotation_text=f"UCL h={h:.1f}", row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="#6c757d", row=2, col=1)

    # Changepoint vertical marker
    if annotate_changepoint and cp_idx is not None:
        for row in [1, 2]:
            fig.add_vline(
                x=cp_idx,
                line_dash="dash",
                line_color="#fd7e14",
                annotation_text=f"Shift @ {cp_idx}",
                row=row, col=1,
            )

    fig.update_layout(
        title=title or "CUSUM Control Chart — Process Shift Detection",
        template="plotly_white",
        height=600,
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Bayesian Posterior Strip / Credible-Interval Plot
# ---------------------------------------------------------------------------

def bayesian_posterior_strip(
    trace_df: pd.DataFrame,
    param_cols: list[str],
    hdi_prob: float = 0.89,
    title: str | None = None,
) -> Any:
    """Credible-interval strip plot for Bayesian posterior samples.

    Args:
        trace_df: DataFrame where each column is a sampled parameter
                  (posterior draws as rows — typically from arviz or PyMC).
        param_cols: Which columns to plot.
        hdi_prob: HDI probability mass (0.89 = 89 % credible interval).
        title: Chart title.

    Returns:
        Plotly Figure: dot (posterior mean) + thick bar (50 % HDI) + thin bar (``hdi_prob`` HDI).
    """
    go = _go()

    alpha = (1 - hdi_prob) / 2

    fig = go.Figure()
    for i, col in enumerate(param_cols):
        vals = trace_df[col].dropna().values
        mean = float(np.mean(vals))
        lo89 = float(np.quantile(vals, alpha))
        hi89 = float(np.quantile(vals, 1 - alpha))
        lo50 = float(np.quantile(vals, 0.25))
        hi50 = float(np.quantile(vals, 0.75))

        # 89 % HDI (thin)
        fig.add_trace(
            go.Scatter(
                x=[lo89, hi89], y=[i, i],
                mode="lines", line=dict(color="#0D6EFD", width=2),
                name=f"{int(hdi_prob * 100)}% HDI", showlegend=(i == 0),
            )
        )
        # 50 % HDI (thick)
        fig.add_trace(
            go.Scatter(
                x=[lo50, hi50], y=[i, i],
                mode="lines", line=dict(color="#0D6EFD", width=8),
                name="50% HDI", showlegend=(i == 0),
            )
        )
        # Posterior mean
        fig.add_trace(
            go.Scatter(
                x=[mean], y=[i],
                mode="markers",
                marker=dict(color="white", size=10, line=dict(color="#003366", width=2)),
                name="Mean", showlegend=(i == 0),
            )
        )

    fig.update_layout(
        title=title or f"Bayesian Posterior — {int(hdi_prob * 100)}% HDI",
        yaxis=dict(tickvals=list(range(len(param_cols))), ticktext=param_cols),
        xaxis_title="Parameter Value",
        template="plotly_white",
        height=max(300, 60 * len(param_cols)),
    )
    return fig


# ---------------------------------------------------------------------------
# Moran's I Scatter Plot (Global Spatial Autocorrelation)
# ---------------------------------------------------------------------------

def moran_scatter_plot(
    df: pd.DataFrame,
    value_col: str,
    spatial_lag_col: str | None = None,
    borough_col: str | None = "borough",
    title: str | None = None,
) -> Any:
    """Moran's I scatter plot (global spatial autocorrelation).

    Plots standardised values (z) on the x-axis vs the spatial lag (W×z)
    on the y-axis. The slope of the OLS line is the global Moran's I statistic.
    Quadrants map to LISA categories: HH (high-high), LL, HL, LH.

    If ``spatial_lag_col`` is absent, a synthetic lag is approximated by
    borough-mean (suitable for exploratory use; replace with proper spatial
    weights for publication).

    Args:
        df: Source DataFrame.
        value_col: The variable to test for spatial autocorrelation.
        spatial_lag_col: Pre-computed spatial lag column. If None, computed
            from borough-mean approximation.
        borough_col: Used to compute approximate spatial lag when
            ``spatial_lag_col`` is None.
        title: Chart title.

    Returns:
        Plotly Figure with four LISA quadrant annotations.
    """
    go = _go()

    tmp = df.copy()
    z = (tmp[value_col] - tmp[value_col].mean()) / (tmp[value_col].std() or 1)

    if spatial_lag_col and spatial_lag_col in tmp.columns:
        wz = (tmp[spatial_lag_col] - tmp[spatial_lag_col].mean()) / (tmp[spatial_lag_col].std() or 1)
    elif borough_col and borough_col in tmp.columns:
        borough_means = tmp.groupby(borough_col)[value_col].transform("mean")
        wz = (borough_means - borough_means.mean()) / (borough_means.std() or 1)
    else:
        wz = z.shift(1).fillna(0)

    # Global Moran's I ~ slope of z vs Wz
    moran_i = float(np.cov(z, wz)[0, 1] / (z.var() or 1))

    # Quadrant assignment
    quad = np.where(
        (z > 0) & (wz > 0), "HH",
        np.where((z < 0) & (wz < 0), "LL",
        np.where((z > 0) & (wz < 0), "HL", "LH")),
    )

    quad_colors = {"HH": "#dc3545", "LL": "#003366", "HL": "#fd7e14", "LH": "#0d6efd"}

    fig = go.Figure()
    for q, color in quad_colors.items():
        mask = quad == q
        if mask.any():
            fig.add_trace(
                go.Scatter(
                    x=z[mask],
                    y=wz[mask],
                    mode="markers",
                    name=q,
                    marker=dict(color=color, opacity=0.6, size=7),
                    text=tmp.get(borough_col, pd.Series(range(len(tmp))))[mask].astype(str),
                    hovertemplate="%{text}<br>z=%{x:.2f} Wz=%{y:.2f}<extra></extra>",
                )
            )

    # OLS regression line
    x_line = np.linspace(z.min(), z.max(), 100)
    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=moran_i * x_line,
            mode="lines",
            name=f"Moran's I = {moran_i:.3f}",
            line=dict(color="#333", width=2, dash="dot"),
        )
    )
    # Quadrant dividers
    for val in [0, 0]:
        fig.add_hline(y=0, line_dash="dash", line_color="#6c757d", line_width=1)
        fig.add_vline(x=0, line_dash="dash", line_color="#6c757d", line_width=1)

    fig.update_layout(
        title=title or f"Moran's I Scatter — {get_unit_label(value_col)} (I={moran_i:.3f})",
        xaxis_title=f"Standardised {get_unit_label(value_col)}",
        yaxis_title="Spatial Lag (Wz)",
        template="plotly_white",
        height=520,
    )
    return fig


# ---------------------------------------------------------------------------
# Ridge / Joy Plot
# ---------------------------------------------------------------------------

def ridge_plot(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    bandwidth: float = 0.5,
    title: str | None = None,
) -> Any:
    """Ridge (joy) plot — stacked KDE distributions per group.

    Ideal for comparing violation-count or condition-score distributions across
    boroughs or material types without the clutter of overlapping histograms.

    Args:
        df: Source DataFrame.
        value_col: Numeric column to plot distributions of.
        group_col: Grouping column (e.g. borough, material_type).
        bandwidth: KDE bandwidth multiplier (relative to scipy scott).
        title: Chart title.

    Returns:
        Plotly Figure (stacked violin traces in ridgeline style).
    """
    go = _go()

    groups = sorted(df[group_col].dropna().unique())
    COLORS = ["#003366", "#D63384", "#198754", "#FD7E14", "#6610F2", "#0D6EFD"]

    fig = go.Figure()
    for i, grp in enumerate(groups):
        subset = df[df[group_col] == grp][value_col].dropna()
        if len(subset) < 5:
            continue
        fig.add_trace(
            go.Violin(
                x=subset,
                name=str(grp),
                orientation="h",
                side="positive",
                fillcolor=COLORS[i % len(COLORS)],
                line_color=COLORS[i % len(COLORS)],
                opacity=0.7,
                bandwidth=bandwidth * subset.std(),
                points=False,
                meanline_visible=True,
            )
        )

    fig.update_traces(width=1.8)
    fig.update_layout(
        title=title or f"Ridge Plot — {get_unit_label(value_col)} by {group_col.replace('_', ' ').title()}",
        xaxis_title=get_unit_label(value_col),
        yaxis_title=group_col.replace("_", " ").title(),
        violingap=0,
        violingroupgap=0,
        template="plotly_white",
        height=max(350, 80 * len(groups)),
    )
    return fig


# ---------------------------------------------------------------------------
# Changepoint Overlay — multi-series with vertical shift markers
# ---------------------------------------------------------------------------

def changepoint_overlay(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_col: str | None = None,
    title: str | None = None,
) -> Any:
    """Time-series chart with CUSUM changepoint markers overlaid per group.

    Args:
        df: Source DataFrame sorted by ``date_col``.
        date_col: Date/timestamp column.
        value_col: Numeric metric.
        group_col: Optional grouping (one trace + changepoint per group).
        title: Chart title.

    Returns:
        Plotly Figure.
    """
    from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

    go = _go()
    COLORS = ["#003366", "#D63384", "#198754", "#FD7E14", "#6610F2"]

    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp = tmp.dropna(subset=[date_col]).sort_values(date_col)

    fig = go.Figure()

    groups = tmp[group_col].dropna().unique() if group_col and group_col in tmp.columns else [None]

    for i, grp in enumerate(groups):
        color = COLORS[i % len(COLORS)]
        subset = tmp[tmp[group_col] == grp] if grp is not None else tmp
        series = subset.set_index(date_col)[value_col].sort_index().dropna()
        if len(series) < 4:
            continue

        label = str(grp) if grp is not None else get_unit_label(value_col)
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines",
                name=label,
                line=dict(color=color, width=1.5),
            )
        )

        cp_idx = detect_cusum_changepoint(series.reset_index(drop=True))
        if cp_idx is not None and cp_idx < len(series):
            cp_date = series.index[cp_idx]
            fig.add_vline(
                x=cp_date,
                line_dash="dash",
                line_color=color,
                annotation_text="↑ Shift",
                annotation_position="top",
            )

    fig.update_layout(
        title=title or f"Changepoint Overlay — {get_unit_label(value_col)}",
        xaxis_title="Date",
        yaxis_title=get_unit_label(value_col),
        template="plotly_white",
        height=480,
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# HDI-Annotated Violin
# ---------------------------------------------------------------------------

def hdi_violin(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    hdi_prob: float = 0.89,
    title: str | None = None,
) -> Any:
    """Violin plot with HDI (highest density interval) annotation lines.

    Args:
        df: Source DataFrame.
        value_col: Numeric column.
        group_col: Grouping column.
        hdi_prob: HDI probability mass (default 0.89).
        title: Chart title.

    Returns:
        Plotly Figure.
    """
    go = _go()

    groups = sorted(df[group_col].dropna().unique())
    alpha = (1 - hdi_prob) / 2
    COLORS = ["#003366", "#D63384", "#198754", "#FD7E14", "#6610F2"]

    fig = go.Figure()
    for i, grp in enumerate(groups):
        vals = df[df[group_col] == grp][value_col].dropna()
        if len(vals) < 5:
            continue
        lo = float(np.quantile(vals, alpha))
        hi = float(np.quantile(vals, 1 - alpha))
        color = COLORS[i % len(COLORS)]

        fig.add_trace(
            go.Violin(
                y=vals,
                name=str(grp),
                box_visible=True,
                meanline_visible=True,
                fillcolor=color,
                line_color=color,
                opacity=0.65,
                points="outliers",
            )
        )
        # HDI annotation as a shape
        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=i - 0.3,
            x1=i + 0.3,
            y0=lo,
            y1=hi,
            fillcolor=color,
            opacity=0.15,
            line_width=0,
        )

    fig.update_layout(
        title=title or (
            f"HDI-Annotated Violin — {get_unit_label(value_col)} "
            f"({int(hdi_prob * 100)}% HDI shaded)"
        ),
        yaxis_title=get_unit_label(value_col),
        xaxis_title=group_col.replace("_", " ").title(),
        template="plotly_white",
        height=520,
    )
    return fig
