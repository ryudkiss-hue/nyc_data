"""Dashboard chart helpers used by tests (Plotly)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..analysis import DashboardSummary, DataProfile
from ..core import COLOR_GREEN, COLOR_RED, COLOR_YELLOW

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    go = None  # type: ignore
    px = None  # type: ignore

def _apply_modern_layout(fig: Any, title: str | None = None) -> Any:
    if fig is None:
        return fig
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title or "", x=0.5, xanchor="center"),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig

def metric_status_pie_chart(summary: DashboardSummary, title: str | None = None) -> Any:
    """Pie chart showing the distribution of metric statuses (green / yellow / red)."""
    if go is None:
        raise ImportError("Install plotly: pip install plotly")
    labels = ["Green (On Target)", "Yellow (Warning)", "Red (Alert)"]
    values = [summary.green_count, summary.yellow_count, summary.red_count]
    colors = [COLOR_GREEN, COLOR_YELLOW, COLOR_RED]
    non_zero_labels = [label for label, val in zip(labels, values) if val > 0]
    non_zero_values = [val for val in values if val > 0]
    non_zero_colors = [color for color, val in zip(colors, values) if val > 0]
    if not non_zero_values:
        fig = go.Figure()
        fig.add_annotation(text="No metric data to display", showarrow=False)
        return _apply_modern_layout(fig, title or "Overall Program Health Status")
    fig = go.Figure(
        data=[
            go.Pie(
                labels=non_zero_labels,
                values=non_zero_values,
                hole=0.4,
                marker=dict(colors=non_zero_colors, line=dict(color="#ffffff", width=2)),
                pull=[0.05 if "Red" in label else 0 for label in non_zero_labels],
            )
        ]
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _apply_modern_layout(fig, title or "Overall Program Health Status")

def data_completeness_chart(profile: DataProfile, title: str | None = None) -> Any:
    if px is None or go is None:
        raise ImportError("Install plotly: pip install plotly")
    columns = getattr(profile, "columns", None) or []
    if not columns:
        return go.Figure()
    completeness_data = [
        {"column": c["name"], "completeness_pct": 100.0 - c.get("null_pct", 0)} for c in columns
    ]
    df_completeness = pd.DataFrame(completeness_data).sort_values("completeness_pct", ascending=True)
    fig = px.bar(
        df_completeness,
        y="column",
        x="completeness_pct",
        orientation="h",
        text_auto=".1f",
        color="completeness_pct",
        color_continuous_scale="Cividis_r",
        labels={"column": "Column Name", "completeness_pct": "Completeness (%)"},
    )
    fig.update_layout(xaxis_range=[0, 100])
    return _apply_modern_layout(fig, title or "Data Completeness by Column")

def plot_geospatial_compliance_map(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    title: str | None = None,
) -> Any:
    if px is None or go is None:
        raise ImportError("Install plotly: pip install plotly")
    if lat_col not in df.columns or lon_col not in df.columns:
        return go.Figure()
    plot_df = df[[lat_col, lon_col]].dropna().copy()
    if plot_df.empty:
        return go.Figure()
  # Core NYC bbox used by compliance tests (tighter than full city limits)
    bounds = {"min_lat": 40.55, "max_lat": 40.88, "min_lon": -74.02, "max_lon": -73.75}
    is_out_of_bounds = (
        (plot_df[lat_col] < bounds["min_lat"])
        | (plot_df[lat_col] > bounds["max_lat"])
        | (plot_df[lon_col] < bounds["min_lon"])
        | (plot_df[lon_col] > bounds["max_lon"])
    )
    in_bounds_df = plot_df[~is_out_of_bounds]
    out_bounds_df = plot_df[is_out_of_bounds]
    fig = go.Figure()
    if not in_bounds_df.empty:
        fig.add_trace(
            go.Scattermap(
                lat=in_bounds_df[lat_col],
                lon=in_bounds_df[lon_col],
                mode="markers",
                name="In Bounds",
                marker=dict(size=9, color="#3b82f6"),
            )
        )
    if not out_bounds_df.empty:
        fig.add_trace(
            go.Scattermap(
                lat=out_bounds_df[lat_col],
                lon=out_bounds_df[lon_col],
                mode="markers",
                name="Out of Bounds",
                marker=dict(size=9, color="#ef4444"),
            )
        )
    fig.update_layout(
        map=dict(
            style="carto-darkmatter",
            zoom=9,
            center=dict(lat=40.7128, lon=-74.0060),
        ),
    )
    return _apply_modern_layout(fig, title or "Geospatial Compliance Check")
