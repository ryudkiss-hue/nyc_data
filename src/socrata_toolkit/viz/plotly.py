"""Plotly Interactive Charts for DOT Sidewalk Toolkit.

Interactive, browser-based visualizations using Plotly. All functions
return Plotly Figure objects that can be:
- Displayed in Streamlit (st.plotly_chart)
- Saved as standalone HTML files
- Embedded in Flask/Django templates
- Exported as PNG/SVG via plotly's kaleido engine

Example::

    from socrata_toolkit.viz.plotly import (
        borough_bar_chart,
        kpi_gauge,
        contract_gantt,
        priority_heatmap,
        trend_line,
    )

    fig = borough_bar_chart(df, value_col="violations")
    fig.write_html("borough_violations.html")
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from socrata_toolkit.viz.units import get_unit_label


def _get_plotly():
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        return go, px
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc

# ---------------------------------------------------------------------------
# Borough Bar Chart
# ---------------------------------------------------------------------------

def borough_bar_chart(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "violations",
    agg: str = "sum",
    title: str | None = None,
    color_map: dict[str, str] | None = None,
) -> Any:
    """Interactive bar chart of a metric by borough with proper units."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = color_map or {
        "MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
        "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14",
    }
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or f"{get_unit_label(value_col)} by Borough",
        xaxis_title="Borough Name",
        yaxis_title=get_unit_label(value_col),
        template="plotly_white",
    )
    return fig

# ---------------------------------------------------------------------------
# KPI Gauge
# ---------------------------------------------------------------------------

def kpi_gauge(
    value: float,
    title: str,
    target: float,
    min_val: float = 0,
    max_val: float | None = None,
    thresholds: dict[str, float] | None = None,
) -> Any:
    """Interactive gauge chart for a single KPI."""
    go, _ = _get_plotly()
    if max_val is None:
        max_val = max(value, target) * 1.5

    th = thresholds or {"green": target, "yellow": target * 1.5, "red": max_val}
    steps = [
        {"range": [min_val, th.get("green", target)], "color": "#d4edda"},
        {"range": [th.get("green", target), th.get("yellow", target * 1.5)], "color": "#fff3cd"},
        {"range": [th.get("yellow", target * 1.5), max_val], "color": "#f8d7da"},
    ]

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta={"reference": target, "increasing": {"color": "#DC3545"}, "decreasing": {"color": "#28A745"}},
        title={"text": title},
        gauge={
            "axis": {"range": [min_val, max_val]},
            "bar": {"color": "#003366"},
            "steps": steps,
            "threshold": {"line": {"color": "#000", "width": 3}, "thickness": 0.8, "value": target},
        },
    ))
    fig.update_layout(height=300)
    return fig

# ---------------------------------------------------------------------------
# Contract Gantt Chart
# ---------------------------------------------------------------------------

def contract_gantt(
    df: pd.DataFrame,
    task_col: str = "contract_id",
    start_col: str = "start_date",
    end_col: str = "end_date",
    color_col: str | None = "status",
    title: str | None = None,
) -> Any:
    """Interactive Gantt chart for contract schedules."""
    go, px = _get_plotly()
    tmp = df.copy()
    tmp[start_col] = pd.to_datetime(tmp[start_col], errors="coerce")
    tmp[end_col] = pd.to_datetime(tmp[end_col], errors="coerce")
    tmp = tmp.dropna(subset=[start_col, end_col])

    color_map = {
        "complete": "#28A745", "in_progress": "#FFC107",
        "delayed": "#DC3545", "not_started": "#6C757D",
        "Active": "#0D6EFD", "Complete": "#28A745",
    }

    fig = px.timeline(
        tmp, x_start=start_col, x_end=end_col, y=task_col,
        color=color_col, color_discrete_map=color_map,
        title=title or "Contract Schedule (Timeline)",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Date (YYYY-MM-DD)",
        yaxis_title="Task/Contract",
    )
    return fig

# ---------------------------------------------------------------------------
# Priority Heatmap
# ---------------------------------------------------------------------------

def priority_heatmap(
    df: pd.DataFrame,
    row_col: str = "borough",
    col_col: str = "status",
    value_col: str = "violations",
    agg: str = "sum",
    title: str | None = None,
) -> Any:
    """Interactive heatmap showing values across two categorical dimensions."""
    go, _ = _get_plotly()
    pivot = pd.pivot_table(df, index=row_col, columns=col_col, values=value_col, aggfunc=agg, fill_value=0)

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale="RdYlGn_r", text=pivot.values, texttemplate="%{text:.0f}",
        colorbar=dict(title=get_unit_label(value_col)),
    ))
    fig.update_layout(
        title=title or f"{get_unit_label(value_col)} by {row_col.replace('_', ' ').title()} and {col_col.replace('_', ' ').title()}",
        xaxis_title=col_col.replace('_', ' ').title(),
        yaxis_title=row_col.replace('_', ' ').title(),
        template="plotly_white",
    )
    return fig

# ---------------------------------------------------------------------------
# Trend Line
# ---------------------------------------------------------------------------

def trend_line(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_col: str | None = None,
    resample: str = "ME",
    agg: str = "sum",
    title: str | None = None,
) -> Any:
    """Interactive time series trend line with optional grouping."""
    go, px = _get_plotly()
    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp = tmp.dropna(subset=[date_col])

    if group_col and group_col in tmp.columns:
        fig = px.line(
            tmp.groupby([pd.Grouper(key=date_col, freq=resample), group_col])[value_col]
            .agg(agg).reset_index(),
            x=date_col, y=value_col, color=group_col,
            title=title or f"{get_unit_label(value_col)} Trend Over Time",
        )
    else:
        resampled = tmp.set_index(date_col).resample(resample)[value_col].agg(agg).reset_index()
        fig = px.line(resampled, x=date_col, y=value_col,
                      title=title or f"{get_unit_label(value_col)} Trend Over Time")

    fig.update_layout(
        template="plotly_white",
        xaxis_title=get_unit_label(date_col),
        yaxis_title=get_unit_label(value_col),
    )
    return fig

# ---------------------------------------------------------------------------
# Donut Chart (status distribution)
# ---------------------------------------------------------------------------

def status_donut(
    df: pd.DataFrame,
    status_col: str = "status",
    title: str | None = None,
    color_map: dict[str, str] | None = None,
) -> Any:
    """Interactive donut chart for status distribution."""
    go, _ = _get_plotly()
    counts = df[status_col].value_counts()
    colors = color_map or {
        "Pending Repair": "#FFC107", "Complete": "#28A745",
        "City-Initiated": "#0D6EFD", "In Progress": "#17A2B8",
        "Cancelled": "#DC3545",
    }
    marker_colors = [colors.get(s, "#6C757D") for s in counts.index]

    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values,
        hole=0.45, marker_colors=marker_colors,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        title=title or f"{status_col.replace('_', ' ').title()} Distribution (count)",
        template="plotly_white",
    )
    return fig

# ---------------------------------------------------------------------------
# Hypothesis Testing Results Visualization
# ---------------------------------------------------------------------------

def hypothesis_test_results(
    group_names: list[str],
    p_values: list[float],
    effect_sizes: list[float],
    title: str = "Hypothesis Test Results",
) -> Any:
    """Visualization of p-values and effect sizes across multiple tests."""
    go, _ = _get_plotly()
    significance_threshold = 0.05

    colors = [
        "#dc3545" if p < significance_threshold else "#6c757d" for p in p_values
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=group_names,
            y=p_values,
            marker_color=colors,
            text=[f"{p:.4f}" for p in p_values],
            textposition="auto",
            name="P-value",
        )
    )
    fig.add_hline(
        y=significance_threshold,
        line_dash="dash",
        line_color="red",
        annotation_text="α = 0.05",
    )

    fig.add_trace(
        go.Scatter(
            x=group_names,
            y=effect_sizes,
            mode="lines+markers",
            name="Effect Size",
            line=dict(color="#0d6efd", width=2),
            marker=dict(size=8),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title=title or "Hypothesis Test Results (P-value & Effect Size)",
        xaxis_title="Group Comparison",
        yaxis=dict(title=get_unit_label('p_value')),
        yaxis2=dict(title=get_unit_label('effect_size'), overlaying="y", side="right"),
        hovermode="x unified",
        template="plotly_white",
        height=400,
    )
    return fig

# ---------------------------------------------------------------------------
# Waterfall Chart (change decomposition)
# ---------------------------------------------------------------------------

def waterfall_chart(
    categories: list[str],
    values: list[float],
    title: str = "Change Waterfall",
    measure: list[str] | None = None,
) -> Any:
    """Waterfall chart showing cumulative effect of components."""
    go, _ = _get_plotly()

    if measure is None:
        measure = ["relative"] * len(categories)
        measure[0] = "absolute"
        measure[-1] = "total"

    fig = go.Figure(
        go.Waterfall(
            name="Value",
            orientation="v",
            x=categories,
            textposition="auto",
            text=[f"{v:+.0f}" for v in values],
            y=values,
            measure=measure,
            connector={"line": {"color": "rgba(0,0,0,0.4)"}},
        )
    )

    fig.update_layout(
        title=title,
        showlegend=False,
        template="plotly_white",
        height=400,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig

# ---------------------------------------------------------------------------
# Correlation Heatmap
# ---------------------------------------------------------------------------

def correlation_heatmap(
    df: pd.DataFrame,
    numeric_cols: list[str] | None = None,
    title: str = "Metric Correlation Matrix",
) -> Any:
    """Heatmap showing correlations between numeric columns."""
    go, _ = _get_plotly()

    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if not numeric_cols:
        fig = go.Figure()
        fig.add_annotation(text="No numeric columns to correlate", showarrow=False)
        return fig

    df_numeric = df[numeric_cols].astype(float, errors="ignore")
    corr_matrix = df_numeric.corr()

    fig = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr_matrix.values.round(2),
            texttemplate="%{text}",
            textfont={"size": 10},
            colorbar=dict(title=get_unit_label('correlation')),
        )
    )

    fig.update_layout(
        title=title or "Metric Correlation Matrix (−1 to 1)",
        xaxis_title="Metric",
        yaxis_title="Metric",
        height=500,
        width=600,
        template="plotly_white",
    )
    return fig

# ---------------------------------------------------------------------------
# Inspector Performance Distribution (Box Plot)
# ---------------------------------------------------------------------------

def inspector_performance_boxplot(
    df: pd.DataFrame,
    inspector_col: str = "inspector",
    metric_col: str = "score",
    title: str = "Inspector Performance Distribution",
) -> Any:
    """Box plot showing performance distribution by inspector."""
    go, px = _get_plotly()

    if inspector_col not in df.columns or metric_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Required columns not found", showarrow=False)
        return fig

    df_plot = df[[inspector_col, metric_col]].copy()
    df_plot[metric_col] = pd.to_numeric(df_plot[metric_col], errors="coerce")
    df_plot = df_plot.dropna()

    if df_plot.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid data to display", showarrow=False)
        return fig

    fig = px.box(
        df_plot.sort_values(inspector_col),
        x=inspector_col,
        y=metric_col,
        title=title or f"{get_unit_label(metric_col)} by Inspector",
        labels={inspector_col: "Inspector Name", metric_col: get_unit_label(metric_col)},
    )

    fig.update_layout(
        height=400,
        template="plotly_white",
        margin=dict(b=100),
        xaxis_tickangle=-45,
        yaxis_title=get_unit_label(metric_col),
    )
    return fig

# ---------------------------------------------------------------------------
# Save / Export
# ---------------------------------------------------------------------------

def save_chart(fig: Any, path: str) -> str:
    """Save a Plotly figure to file (HTML, PNG, SVG, PDF).

    HTML is always supported. Image formats require kaleido:
    ``pip install kaleido``
    """
    from pathlib import Path as P
    p = P(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ext = p.suffix.lower()

    if ext == ".html":
        fig.write_html(str(p))
    else:
        fig.write_image(str(p))
    return str(p)
