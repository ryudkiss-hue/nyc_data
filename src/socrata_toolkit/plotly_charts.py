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

# =============================================================================
# PHASE 1: AUTO-GENERATED VISUALIZATION FUNCTIONS (21 datasets)
# =============================================================================
# These functions were auto-generated from DATASET_REGISTRY.yaml
# Last generated: 2026-06-17
# Covers: Permits, Pedestrian Infrastructure, Safety, Budget, Geospatial


# ---------------------------------------------------------------------------
# Accessible Pedestrian Signals by Borough
# ---------------------------------------------------------------------------

def accessible_signals_by_borough(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "signal_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Accessible Pedestrian Signals by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Accessible Pedestrian Signals by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="signal_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Accessible Signals by Condition Status
# ---------------------------------------------------------------------------

def accessible_signals_condition(
    df: pd.DataFrame,
    category_col: str = "condition_status",
    value_col: str = "signal_count",
    title: str | None = None,
) -> Any:
    """Donut chart showing distribution: Accessible Signals by Condition Status."""
    go, px = _get_plotly()
    agg_df = df.groupby(category_col)[value_col].agg("count").reset_index()

    fig = px.pie(
        agg_df, names=category_col, values=value_col,
        hole=0.3, title=title or "Accessible Signals by Condition Status"
    )
    fig.update_layout(template="plotly_white")
    return fig


# ---------------------------------------------------------------------------
# Bicycle Parking Shelters by Borough
# ---------------------------------------------------------------------------

def bicycle_parking_coverage(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "shelter_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Bicycle Parking Shelters by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Bicycle Parking Shelters by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="shelter_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Bus Pad Construction Status Distribution
# ---------------------------------------------------------------------------

def bus_pad_construction_status(
    df: pd.DataFrame,
    category_col: str = "status",
    value_col: str = "pad_count",
    title: str | None = None,
) -> Any:
    """Donut chart showing distribution: Bus Pad Construction Status Distribution."""
    go, px = _get_plotly()
    agg_df = df.groupby(category_col)[value_col].agg("count").reset_index()

    fig = px.pie(
        agg_df, names=category_col, values=value_col,
        hole=0.3, title=title or "Bus Pad Construction Status Distribution"
    )
    fig.update_layout(template="plotly_white")
    return fig


# ---------------------------------------------------------------------------
# Capital Projects Pipeline Status
# ---------------------------------------------------------------------------

def capital_projects_pipeline(
    df: pd.DataFrame,
    borough_col: str = "status",
    value_col: str = "project_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Capital Projects Pipeline Status."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Capital Projects Pipeline Status",
        xaxis_title="status".replace("_", " ").title(),
        yaxis_title="project_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Street Centerline Network Coverage
# ---------------------------------------------------------------------------

def centerline_network_coverage(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    color_col: str | None = "borough",
    title: str | None = None,
) -> Any:
    """Scatter map showing locations: Street Centerline Network Coverage."""
    go, px = _get_plotly()

    fig = px.scatter_mapbox(
        df, lat=lat_col, lon=lon_col, color=color_col,
        zoom=9, title=title or "Street Centerline Network Coverage",
        mapbox_style="open-street-map",
    )
    fig.update_layout(
        height=600, margin={"r": 0, "t": 30, "l": 0, "b": 0},
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Leading Pedestrian Interval Signals by Borough
# ---------------------------------------------------------------------------

def lpi_signal_coverage(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "signal_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Leading Pedestrian Interval Signals by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Leading Pedestrian Interval Signals by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="signal_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Open Streets Program Locations
# ---------------------------------------------------------------------------

def open_streets_coverage_map(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    color_col: str | None = "borough",
    title: str | None = None,
) -> Any:
    """Scatter map showing locations: Open Streets Program Locations."""
    go, px = _get_plotly()

    fig = px.scatter_mapbox(
        df, lat=lat_col, lon=lon_col, color=color_col,
        zoom=9, title=title or "Open Streets Program Locations",
        mapbox_style="open-street-map",
    )
    fig.update_layout(
        height=600, margin={"r": 0, "t": 30, "l": 0, "b": 0},
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Parking Meters Obstruction Zones
# ---------------------------------------------------------------------------

def parking_meters_obstruction_zones(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    color_col: str | None = "borough",
    title: str | None = None,
) -> Any:
    """Scatter map showing locations: Parking Meters Obstruction Zones."""
    go, px = _get_plotly()

    fig = px.scatter_mapbox(
        df, lat=lat_col, lon=lon_col, color=color_col,
        zoom=9, title=title or "Parking Meters Obstruction Zones",
        mapbox_style="open-street-map",
    )
    fig.update_layout(
        height=600, margin={"r": 0, "t": 30, "l": 0, "b": 0},
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Parking Meter Density by Borough
# ---------------------------------------------------------------------------

def meter_density_by_borough(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "meter_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Parking Meter Density by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Parking Meter Density by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="meter_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Pedestrian Mobility Demand Heatmap
# ---------------------------------------------------------------------------

def pedestrian_demand_heatmap(
    df: pd.DataFrame,
    x_col: str = "neighborhood",
    y_col: str = "demand_level",
    value_col: str = "count",
    title: str | None = None,
) -> Any:
    """Heatmap showing: Pedestrian Mobility Demand Heatmap."""
    go, px = _get_plotly()
    pivot_df = df.pivot_table(index=y_col, columns=x_col, values=value_col, aggfunc="avg", fill_value=0)

    fig = px.imshow(
        pivot_df, title=title or "Pedestrian Mobility Demand Heatmap",
        labels={"color": "Count"}, aspect="auto"
    )
    fig.update_layout(
        xaxis_title="neighborhood".replace("_", " ").title(),
        yaxis_title="demand_level".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Pedestrian Plazas Engagement Map
# ---------------------------------------------------------------------------

def plaza_public_engagement(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    color_col: str | None = "borough",
    title: str | None = None,
) -> Any:
    """Scatter map showing locations: Pedestrian Plazas Engagement Map."""
    go, px = _get_plotly()

    fig = px.scatter_mapbox(
        df, lat=lat_col, lon=lon_col, color=color_col,
        zoom=9, title=title or "Pedestrian Plazas Engagement Map",
        mapbox_style="open-street-map",
    )
    fig.update_layout(
        height=600, margin={"r": 0, "t": 30, "l": 0, "b": 0},
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Pedestrian Plazas by Borough
# ---------------------------------------------------------------------------

def plaza_inspection_coverage(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "plaza_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Pedestrian Plazas by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Pedestrian Plazas by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="plaza_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Manhattan Pedestrian Ramp Audit Results
# ---------------------------------------------------------------------------

def manhattan_ramp_audit_results(
    df: pd.DataFrame,
    borough_col: str = "district",
    value_col: str = "ramp_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Manhattan Pedestrian Ramp Audit Results."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Manhattan Pedestrian Ramp Audit Results",
        xaxis_title="district".replace("_", " ").title(),
        yaxis_title="ramp_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Speed Reducers by Borough
# ---------------------------------------------------------------------------

def speed_reducer_coverage(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "reducer_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Speed Reducers by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Speed Reducers by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="reducer_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Street Closures due to Construction Timeline
# ---------------------------------------------------------------------------

def street_closures_timeline(
    df: pd.DataFrame,
    start_col: str = "start_date",
    end_col: str = "end_date",
    task_col: str = "location",
    color_col: str | None = "status",
    title: str | None = None,
) -> Any:
    """Timeline chart showing: Street Closures due to Construction Timeline."""
    go, px = _get_plotly()
    tmp = df.copy()
    tmp[start_col] = pd.to_datetime(tmp[start_col], errors="coerce")
    tmp[end_col] = pd.to_datetime(tmp[end_col], errors="coerce")
    tmp = tmp.dropna(subset=[start_col, end_col])

    fig = px.timeline(
        tmp, x_start=start_col, x_end=end_col, y=task_col,
        color=color_col, title=title or "Street Closures due to Construction Timeline",
    )
    fig.update_layout(template="plotly_white")
    return fig


# ---------------------------------------------------------------------------
# Crane Permits by Borough
# ---------------------------------------------------------------------------

def crane_permits_by_borough(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "crane_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Crane Permits by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Crane Permits by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="crane_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Street Construction Permit Fees by Borough
# ---------------------------------------------------------------------------

def street_permits_fee_by_borough(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "permit_count",
    agg: str = "sum",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Street Construction Permit Fees by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Street Construction Permit Fees by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="permit_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Historical Permit Trends (2013-2021)
# ---------------------------------------------------------------------------

def permit_trends_2013_2021(
    df: pd.DataFrame,
    time_col: str = "year",
    value_col: str = "permit_count",
    title: str | None = None,
) -> Any:
    """Line chart showing trends: Historical Permit Trends (2013-2021)."""
    go, px = _get_plotly()

    fig = px.line(
        df, x=time_col, y=value_col,
        title=title or "Historical Permit Trends (2013-2021)",
        markers=True,
        line_shape="linear",
    )
    fig.update_layout(
        xaxis_title="year".replace("_", " ").title(),
        yaxis_title="permit_count".replace("_", " ").title(),
        template="plotly_white",
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Related Agency Permits by Borough and Agency
# ---------------------------------------------------------------------------

def agency_permits_heatmap(
    df: pd.DataFrame,
    x_col: str = "borough",
    y_col: str = "agency_name",
    value_col: str = "count",
    title: str | None = None,
) -> Any:
    """Heatmap showing: Related Agency Permits by Borough and Agency."""
    go, px = _get_plotly()
    pivot_df = df.pivot_table(index=y_col, columns=x_col, values=value_col, aggfunc="count", fill_value=0)

    fig = px.imshow(
        pivot_df, title=title or "Related Agency Permits by Borough and Agency",
        labels={"color": "Count"}, aspect="auto"
    )
    fig.update_layout(
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="agency_name".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig


# ---------------------------------------------------------------------------
# Vision Zero Enhanced Crossings by Borough
# ---------------------------------------------------------------------------

def vision_zero_crossing_maintenance(
    df: pd.DataFrame,
    borough_col: str = "borough",
    value_col: str = "crossing_count",
    agg: str = "count",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: Vision Zero Enhanced Crossings by Borough."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "Vision Zero Enhanced Crossings by Borough",
        xaxis_title="borough".replace("_", " ").title(),
        yaxis_title="crossing_count".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig



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
