from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .analysis import DashboardSummary, DataProfile
from .core import (
    COL_LAT,
    COL_LON,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    DTYPE_NUM,
)
from .engineering import SIDEWALK_MATERIALS

logger = logging.getLogger(__name__)


# ── Visualizations (Plotly) ───────────────────────────────────────────────────

_PLOTLY_THEME = "plotly_dark"
_FONT_FAMILY = "Inter, sans-serif"


def _apply_modern_layout(fig: Any, title: str | None = None) -> Any:
    """Standardize the look and feel of all Plotly charts with reference-grade defaults."""
    if not hasattr(fig, "update_layout"):
        return fig
    fig.update_layout(
        title=(
            {
                "text": title,
                "font": {"size": 22, "family": _FONT_FAMILY, "weight": "bold"},
                "x": 0.02,
                "xanchor": "left",
            }
            if title
            else None
        ),
        font_family=_FONT_FAMILY,
        template=_PLOTLY_THEME,
        # Accessibility: Use a colorblind-safe color sequence by default
        colorway=px.colors.qualitative.Safe,
        hoverlabel=dict(
            bgcolor="rgba(0,0,0,0.8)",
            font_size=13,
            font_family=_FONT_FAMILY,
            namelength=-1,  # Ensure full names are shown
        ),
        margin=dict(t=80 if title else 40, l=40, r=40, b=60),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"
        ),
        # Interaction & Selection (Plotly Reference: layout.clickmode, layout.dragmode)
        clickmode="event+select",
        dragmode="lasso",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        # Number Formatting (Plotly Reference: layout.separators)
        separators=",.",
    )

    # Trace specific defaults (Plotly Reference: trace.unselected.marker.opacity)
    fig.update_traces(unselected=dict(marker=dict(opacity=0.3)), selector=dict(type="scatter"))

    # Add NYC DOT watermark/branding
    fig.add_annotation(
        text="NYC DOT Data Assistant",
        xref="paper",
        yref="paper",
        x=1,
        y=-0.12,
        showarrow=False,
        font=dict(size=10, color="gray"),
    )
    return fig


def export_plotly_figure(fig: Any, base_filepath: str, formats: list[str] = ["html"]) -> list[str]:
    """Export a Plotly figure to multiple formats for portability and presentations.
    Formats supported: 'html' (interactive), 'json' (live-update state), 'png', 'pdf' (requires kaleido).
    """
    saved_paths = []
    base_path = Path(base_filepath)
    base_path.parent.mkdir(parents=True, exist_ok=True)

    if "html" in formats:
        out_path = f"{base_path.with_suffix('')}.html"
        # cdn allows the HTML to be fully self-contained and interactive offline if cached, or small size online
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        saved_paths.append(out_path)

    if "json" in formats:
        out_path = f"{base_path.with_suffix('')}.json"
        fig.write_json(out_path)
        saved_paths.append(out_path)

    if any(ext in formats for ext in ["png", "pdf", "svg"]):
        try:
            for ext in [f for f in formats if f in ["png", "pdf", "svg"]]:
                out_path = f"{base_path.with_suffix('')}.{ext}"
                fig.write_image(out_path)
                saved_paths.append(out_path)
        except ValueError:
            logger.warning(
                "Static image export requires the 'kaleido' package (pip install -U kaleido)."
            )

    return saved_paths


def histogram(df: pd.DataFrame, column: str, title: str | None = None) -> Any:
    """Return a refined interactive Plotly histogram."""
    fig = px.histogram(
        df,
        x=column,
        marginal="box",
        color_discrete_sequence=["#3b82f6"],
        opacity=0.75,
        labels={column: column.replace("_", " ").title()},
    )
    # Rich tooltips (Plotly Reference: trace.hovertemplate)
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>")
    return _apply_modern_layout(fig, title or f"Distribution Analysis: {column.title()}")


def bar_chart(
    df: pd.DataFrame,
    column: str,
    title: str | None = None,
    top_n: int = 15,
    animation_frame: str | None = None,
) -> Any:
    """Return a refined interactive Plotly bar chart with sorted counts and optional animation."""
    if animation_frame:
        # For animation, we need the full series per frame
        counts = df.groupby([animation_frame, column]).size().reset_index(name="Count")
        # Ensure we only keep top_n per frame or overall
        top_cats = df[column].value_counts().head(top_n).index
        counts = counts[counts[column].isin(top_cats)]
        # Sort by animation frame to ensure correct playback order
        counts = counts.sort_values(animation_frame)
    else:
        counts = df[column].value_counts().head(top_n).reset_index()
        counts.columns = [column, "Count"]

    fig = px.bar(
        counts,
        x=column,
        y="Count",
        color="Count",
        color_continuous_scale="Blues",
        text_auto=".2s",
        animation_frame=animation_frame,
    )

    # Highlight the top record with an annotation (only for non-animated or first frame)
    if not animation_frame:
        top_val = counts.iloc[0][column]
        fig.add_annotation(
            x=top_val,
            y=counts.iloc[0]["Count"],
            text="Highest Frequency",
            showarrow=True,
            arrowhead=1,
            yshift=10,
        )

    fig.update_traces(
        textposition="outside", hovertemplate="<b>%{x}</b><br>Volume: %{y:,.0f}<extra></extra>"
    )
    return _apply_modern_layout(fig, title or f"Top {top_n} Categories: {column.title()}")


def correlation_heatmap(df: pd.DataFrame, title: str | None = None) -> Any:
    """Return a high-resolution interactive Plotly correlation heatmap."""
    corr = df.select_dtypes(include=DTYPE_NUM).corr()
    if corr.empty:
        return go.Figure()

    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        aspect="auto",
        labels=dict(color="Correlation"),
    )

    fig.update_xaxes(side="top")
    return _apply_modern_layout(fig, title or "Inter-Variable Correlation Matrix")


def time_series_chart(
    df: pd.DataFrame, date_col: str, value_col: str, group_col: str | None = None
) -> Any:
    """Create a high-performance time series chart using Scattergl (WebGL)."""
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    # Optimization: Use Scattergl for performance with large datasets
    # Note: px.line uses scatter traces; we'll convert them to scattergl
    fig = px.line(
        df,
        x=date_col,
        y=value_col,
        color=group_col,
    )

    # Plotly Reference Optimization: webgl is much faster for thousands of points
    fig.update_traces(mode="lines+markers", marker=dict(size=4))
    for i in range(len(fig.data)):
        fig.data[i].type = "scattergl"

    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(step="all"),
                ]
            )
        ),
    )

    fig.update_traces(hovertemplate="<b>%{x|%b %d, %Y}</b><br>Value: %{y:,.2f}<extra></extra>")

    return _apply_modern_layout(fig, f"Temporal Trend: {value_col.title()} Over Time")


def sunburst_chart(df: pd.DataFrame, path: list[str], values: str, title: str | None = None) -> Any:
    """Create a hierarchical Sunburst chart (Plotly Reference: Sunburst)."""
    fig = px.sunburst(
        df,
        path=path,
        values=values,
        color=values,
        color_continuous_scale="Viridis",
        branchvalues="total",  # Preserves area proportional to totals
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Value: %{value:,.0f}<br>Parent: %{parent}<extra></extra>"
    )
    return _apply_modern_layout(fig, title or "Hierarchical Data Breakdown")


def treemap_chart(df: pd.DataFrame, path: list[str], values: str, title: str | None = None) -> Any:
    """Create a hierarchical Treemap (Plotly Reference: Treemap)."""
    fig = px.treemap(
        df,
        path=path,
        values=values,
        color=values,
        color_continuous_scale="Blues",
    )
    fig.update_traces(
        textinfo="label+value+percent parent",
        hovertemplate="<b>%{label}</b><br>Value: %{value:,.0f}<extra></extra>",
    )
    return _apply_modern_layout(fig, title or "Proportional Data Density")


def gauge_chart(value: float, target: float | None = None, title: str | None = None) -> Any:
    """Create a high-impact KPI Gauge (Plotly Reference: Indicator)."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta" if target is not None else "gauge+number",
            value=value,
            delta={"reference": target} if target is not None else None,
            title={"text": title, "font": {"size": 18}},
            gauge={
                "axis": {"range": [0, max(value * 1.5, 100)]},
                "bar": {"color": "#3b82f6"},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 50], "color": "rgba(255, 0, 0, 0.1)"},
                    {"range": [50, 100], "color": "rgba(0, 255, 0, 0.1)"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": target if target is not None else value,
                },
            },
        )
    )
    return _apply_modern_layout(fig)


def animated_scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    animation_frame: str,
    size: str | None = None,
    color: str | None = None,
    title: str | None = None,
) -> Any:
    """Create a fully animated scatter plot for exploring multi-dimensional trends over time."""
    # Ensure correct data types for animation
    df = df.dropna(subset=[x, y, animation_frame]).sort_values(animation_frame)

    fig = px.scatter(
        df,
        x=x,
        y=y,
        animation_frame=animation_frame,
        animation_group=color if color else x,
        size=size,
        color=color,
        hover_name=color if color else x,
        size_max=60,
        log_x=True if df[x].min() > 0 else False,
    )

    # Optimization for animation performance
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 800
    fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 400

    return _apply_modern_layout(fig, title or f"Animated Trends: {y.title()} vs {x.title()}")


def hotspot_density_mapbox(
    df: pd.DataFrame,
    lat_col: str = COL_LAT,
    lon_col: str = COL_LON,
    z_col: str | None = None,
    title: str | None = None,
) -> Any:
    """Create a high-performance density mapbox (Heatmap) for operational hotspots (e.g. 311 complaints, defect clusters)."""
    # Drop missing coords for mapping
    plot_df = df.dropna(subset=[lat_col, lon_col])

    fig = px.density_mapbox(
        plot_df,
        lat=lat_col,
        lon=lon_col,
        z=z_col,
        radius=12,
        center=dict(lat=40.7128, lon=-74.0060),
        zoom=10,
        mapbox_style="carto-darkmatter",
        color_continuous_scale="Inferno",
    )

    fig.update_layout(margin=dict(t=80 if title else 0, b=0, l=0, r=0))
    return _apply_modern_layout(fig, title or "Operational Density Hotspots")


def material_breakdown_pie_chart(
    df: pd.DataFrame, material_col: str, title: str | None = None
) -> Any:
    """Create an interactive Donut chart mapping SDM materials to their exact hex colors."""

    counts = df[material_col].value_counts().reset_index()
    counts.columns = [material_col, "Count"]

    fig = px.pie(
        counts,
        names=material_col,
        values="Count",
        hole=0.45,  # Creates the Donut effect
        color=material_col,
        color_discrete_map=SIDEWALK_MATERIALS,  # Maps to your official engineering standards!
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
    )

    return _apply_modern_layout(fig, title or "Material Composition Breakdown")


def material_borough_subplots(
    df: pd.DataFrame, material_col: str, borough_col: str = "borough", title: str | None = None
) -> Any:
    """Create a 1xN matrix of Donut chart subplots breaking down materials by Borough."""

    # Get top boroughs (up to 5) to avoid squishing the charts
    boroughs = df[borough_col].dropna().value_counts().head(5).index.tolist()
    if not boroughs:
        return material_breakdown_pie_chart(df, material_col, title)

    fig = make_subplots(
        rows=1,
        cols=len(boroughs),
        specs=[[{"type": "domain"}] * len(boroughs)],
        subplot_titles=boroughs,
    )

    for i, boro in enumerate(boroughs):
        boro_df = df[df[borough_col] == boro]
        counts = boro_df[material_col].value_counts().reset_index()
        counts.columns = [material_col, "Count"]

        colors = [SIDEWALK_MATERIALS.get(mat, "#9ca3af") for mat in counts[material_col]]

        fig.add_trace(
            go.Pie(
                labels=counts[material_col],
                values=counts["Count"],
                hole=0.45,
                marker=dict(colors=colors),
                name=str(boro),
                textinfo="percent",
                textposition="inside",
                hovertemplate="<b>%{label}</b><br>Count: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
            ),
            1,
            i + 1,
        )

    return _apply_modern_layout(fig, title or f"Material Breakdown by {borough_col.title()}")


def operations_gantt_chart(
    df: pd.DataFrame,
    task_col: str,
    start_col: str,
    end_col: str,
    color_col: str | None = None,
    title: str | None = None,
) -> Any:
    """Create a timeline/Gantt chart for tracking contract lifecycles, SLA durations, or permit windows."""
    plot_df = df.dropna(subset=[task_col, start_col, end_col]).copy()
    plot_df[start_col] = pd.to_datetime(plot_df[start_col])
    plot_df[end_col] = pd.to_datetime(plot_df[end_col])

    fig = px.timeline(
        plot_df, x_start=start_col, x_end=end_col, y=task_col, color=color_col, hover_name=task_col
    )

    # Tasks top-to-bottom
    fig.update_yaxes(autorange="reversed")
    return _apply_modern_layout(fig, title or "Operations Schedule & Timelines")


def triage_funnel_chart(df: pd.DataFrame, stage_col: str, title: str | None = None) -> Any:
    """Create a funnel chart to visualize operational throughput (e.g., Reported -> Inspected -> Assigned -> Completed)."""
    # Calculate counts per stage
    counts = df[stage_col].value_counts().reset_index()
    counts.columns = ["Stage", "Count"]

    # Optional: if you have a predefined order for stages, you can enforce it here
    # counts['Stage'] = pd.Categorical(counts['Stage'], categories=["Reported", "Inspected", "Assigned", "Completed"], ordered=True)
    # counts = counts.sort_values('Stage')

    fig = px.funnel(counts, x="Count", y="Stage", color="Stage")
    return _apply_modern_layout(fig, title or "Pipeline Conversion & Triage Funnel")


def plot_sidewalk_anatomy(geojson_data: dict[str, Any], title: str | None = None) -> Any:
    """Render a vectorized 2D sandbox schematic of sidewalk infrastructure."""
    fig = go.Figure()

    for feature in geojson_data.get("features", []):
        geom_type = feature.get("geometry", {}).get("type")
        coords = feature.get("geometry", {}).get("coordinates", [])
        props = feature.get("properties", {})

        if geom_type == "Polygon" and coords:
            # Extract x and y from the exterior polygon ring
            x = [pt[0] for pt in coords[0]]
            y = [pt[1] for pt in coords[0]]

            hover_text = (
                f"<b>Zone:</b> {props.get('zone_name', 'N/A')}<br>"
                f"<b>Material:</b> {props.get('material', 'N/A')}<br>"
                f"<b>Width:</b> {props.get('width_ft', 'N/A')} ft<br>"
                f"<b>Cross-Slope:</b> {props.get('cross_slope_pct', 'N/A')}%"
            )

            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    fill="toself",
                    fillcolor=props.get("fill_color", "#cccccc"),
                    line=dict(color="rgba(255, 255, 255, 0.4)", width=1.5),
                    mode="lines",
                    name=props.get("zone_name", "Zone"),
                    text=hover_text,
                    hoverinfo="text",
                )
            )

    # Create proportional CAD/Blueprint axes
    fig.update_layout(
        xaxis=dict(scaleanchor="y", scaleratio=1, showgrid=True, title="Length (ft)"),
        yaxis=dict(showgrid=True, title="Width (ft)"),
    )
    return _apply_modern_layout(fig, title or "Vectorized Sidewalk Anatomy Sandbox")


def violin_plot(df: pd.DataFrame, x_col: str, y_col: str, title: str | None = None) -> Any:
    """Create a Violin plot to visualize distributions and probability density (e.g. Repair Cost by Borough)."""
    fig = px.violin(
        df,
        x=x_col,
        y=y_col,
        box=True,
        points="all",
        color=x_col,
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Value: %{y}<extra></extra>")
    return _apply_modern_layout(fig, title or f"Distribution: {y_col.title()} by {x_col.title()}")


def quality_radar_chart(score_dict: dict[str, float], title: str | None = None) -> Any:
    """Create a Radar chart visualizing the multiple dimensions of data quality."""
    categories = ["Completeness", "Validity", "Consistency", "Freshness"]
    values = [score_dict.get(c.lower(), 100.0) for c in categories]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            line_color="#3b82f6",
        )
    )
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
    return _apply_modern_layout(fig, title or "Data Quality Radar")


def metric_status_pie_chart(summary: DashboardSummary, title: str | None = None) -> Any:
    """Create an interactive pie chart showing the distribution of metric statuses."""
    labels = ["Green (On Target)", "Yellow (Warning)", "Red (Alert)"]
    values = [summary.green_count, summary.yellow_count, summary.red_count]
    colors = [COLOR_GREEN, COLOR_YELLOW, COLOR_RED]

    # Filter out zero-value slices for a cleaner look
    non_zero_labels = [l for l, v in zip(labels, values) if v > 0]
    non_zero_values = [v for v in values if v > 0]
    non_zero_colors = [c for c, v in zip(colors, values) if v > 0]

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
                pull=[0.05 if "Red" in l else 0 for l in non_zero_labels],  # Explode red slice
            )
        ]
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
    )

    return _apply_modern_layout(fig, title or "Overall Program Health Status")


def data_completeness_chart(profile: DataProfile, title: str | None = None) -> Any:
    """Create a horizontal bar chart showing the data completeness for each column."""
    if not profile.columns:
        return go.Figure()

    completeness_data = [
        {"column": c["name"], "completeness_pct": 100.0 - c["null_pct"]} for c in profile.columns
    ]
    df_completeness = pd.DataFrame(completeness_data).sort_values(
        "completeness_pct", ascending=True
    )

    fig = px.bar(
        df_completeness,
        y="column",
        x="completeness_pct",
        orientation="h",
        text_auto=".1f",
        color="completeness_pct",
        color_continuous_scale="Cividis_r",
        range_color=[df_completeness["completeness_pct"].min() - 5, 100],
        labels={"column": "Column Name", "completeness_pct": "Completeness (%)"},
    )

    fig.update_traces(
        texttemplate="%{x:.1f}%",
        hovertemplate="<b>%{y}</b><br>Completeness: %{x:.1f}%<extra></extra>",
    )
    fig.update_layout(xaxis_range=[0, 100])

    return _apply_modern_layout(fig, title or "Data Completeness by Column")


def plot_geospatial_compliance_map(
    df: pd.DataFrame,
    lat_col: str = COL_LAT,
    lon_col: str = COL_LON,
    title: str | None = None,
) -> Any:
    """
    Creates a Mapbox scatter plot showing which points are within or outside
    the valid NYC geospatial boundaries.
    """
    if lat_col not in df.columns or lon_col not in df.columns:
        return go.Figure()

    plot_df = df[[lat_col, lon_col]].dropna().copy()
    if plot_df.empty:
        return go.Figure()

    # Define NYC bounds
    bounds = {"min_lat": 40.4774, "max_lat": 40.9176, "min_lon": -74.2591, "max_lon": -73.7004}

    # Vectorized check for points outside bounds
    is_out_of_bounds = (plot_df[lat_col] < bounds["min_lat"]) | (plot_df[lat_col] > bounds["max_lat"]) | (plot_df[lon_col] < bounds["min_lon"]) | (plot_df[lon_col] > bounds["max_lon"])
    plot_df["status"] = "In Bounds"
    plot_df.loc[is_out_of_bounds, "status"] = "Out of Bounds"

    fig = px.scatter_mapbox(plot_df, lat=lat_col, lon=lon_col, color="status", color_discrete_map={"In Bounds": "#3b82f6", "Out of Bounds": "#ef4444"}, size_max=15, zoom=9, center=dict(lat=40.7128, lon=-74.0060), mapbox_style="carto-darkmatter", opacity=0.7)
    fig.update_layout(margin=dict(t=80 if title else 0, b=0, l=0, r=0))
    return _apply_modern_layout(fig, title or "Geospatial Compliance Check")


def generate_semantic_network_map() -> Any:
    """
    Generate an interactive semantic network map of the toolkit's capabilities.
    Placeholder function.
    """
    logger.warning("generate_semantic_network_map is a placeholder and does not produce a real map.")
    fig = go.Figure()
    fig.add_annotation(text="Semantic Network Map (Not Implemented)", showarrow=False)
    return _apply_modern_layout(fig, title="Toolkit Semantic Network Map")


def plot_ada_compliance_map(
    df: pd.DataFrame, lat_col: str, lon_col: str, status_col: str
) -> Any:
    """
    Creates a Mapbox scatter plot showing ADA compliance status.
    Placeholder function.
    """
    logger.warning("plot_ada_compliance_map is a placeholder and does not produce a real map.")
    fig = go.Figure()
    fig.add_annotation(text="ADA Compliance Map (Not Implemented)", showarrow=False)
    return _apply_modern_layout(fig, title="ADA Compliance Map")