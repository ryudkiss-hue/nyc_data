"""Plotly Interactive Charts for DOT Sidewalk Toolkit.

Interactive, browser-based visualizations using Plotly. All functions
return Plotly Figure objects that can be:
- Displayed in Streamlit (st.plotly_chart)
- Saved as standalone HTML files
- Embedded in Flask/Django templates
- Exported as PNG/SVG via plotly's kaleido engine

Example::

    from socrata_toolkit.plotly_charts import (
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
    """Interactive bar chart of a metric by borough."""
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
        title=title or f"{value_col.replace('_', ' ').title()} by Borough",
        xaxis_title="Borough", yaxis_title=value_col.replace("_", " ").title(),
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
        title=title or "Contract Schedule",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(template="plotly_white")
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
    ))
    fig.update_layout(
        title=title or f"{value_col.replace('_', ' ').title()} Heatmap",
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
            title=title or f"{value_col.replace('_', ' ').title()} Trend",
        )
    else:
        resampled = tmp.set_index(date_col).resample(resample)[value_col].agg(agg).reset_index()
        fig = px.line(resampled, x=date_col, y=value_col,
                      title=title or f"{value_col.replace('_', ' ').title()} Trend")

    fig.update_layout(template="plotly_white")
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
    ))
    fig.update_layout(title=title or "Status Distribution", template="plotly_white")
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
