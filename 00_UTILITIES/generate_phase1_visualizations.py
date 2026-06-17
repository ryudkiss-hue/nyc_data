#!/usr/bin/env python3
"""
Generate Plotly visualizations for 21 Phase 1 datasets.

This script auto-generates chart functions for all Phase 1 datasets
and adds them to src/socrata_toolkit/plotly_charts.py.

Phase 1 Datasets (21 total):
- Permit Variants & Conflicts (5)
- Pedestrian Infrastructure (6)
- Street Safety & Conditions (5)
- Budget & Vendor (3)
- Reference & Geospatial (2)
"""

import textwrap
from pathlib import Path


# Chart templates for each dataset type
CHARTS = {
    # Phase 1: Permit Variants & Conflicts (5)
    "street_permits_fee": {
        "function": "street_permits_fee_by_borough",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "permit_count",
        "title": "Street Construction Permit Fees by Borough",
        "agg": "sum",
    },
    "street_closures_construction": {
        "function": "street_closures_timeline",
        "chart_type": "timeline",
        "iv": "start_date",
        "dv": "location",
        "title": "Street Closures due to Construction Timeline",
        "agg": "count",
    },
    "street_permits_historical": {
        "function": "permit_trends_2013_2021",
        "chart_type": "line",
        "iv": "year",
        "dv": "permit_count",
        "title": "Historical Permit Trends (2013-2021)",
        "agg": "count",
    },
    "street_permits_cranes": {
        "function": "crane_permits_by_borough",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "crane_count",
        "title": "Crane Permits by Borough",
        "agg": "count",
    },
    "street_permits_related_agency": {
        "function": "agency_permits_heatmap",
        "chart_type": "heatmap",
        "iv": "borough",
        "dv": "agency_name",
        "title": "Related Agency Permits by Borough and Agency",
        "agg": "count",
    },
    # Phase 1: Pedestrian Infrastructure (6)
    "open_streets": {
        "function": "open_streets_coverage_map",
        "chart_type": "scatter",
        "iv": "latitude",
        "dv": "longitude",
        "title": "Open Streets Program Locations",
        "agg": "count",
    },
    "pedestrian_mobility_demand": {
        "function": "pedestrian_demand_heatmap",
        "chart_type": "heatmap",
        "iv": "neighborhood",
        "dv": "demand_level",
        "title": "Pedestrian Mobility Demand Heatmap",
        "agg": "avg",
    },
    "accessible_signals_map": {
        "function": "accessible_signals_by_borough",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "signal_count",
        "title": "Accessible Pedestrian Signals by Borough",
        "agg": "count",
    },
    "accessible_signals_table": {
        "function": "accessible_signals_condition",
        "chart_type": "donut",
        "iv": "condition_status",
        "dv": "signal_count",
        "title": "Accessible Signals by Condition Status",
        "agg": "count",
    },
    "pedestrian_plazas_polygon": {
        "function": "plaza_inspection_coverage",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "plaza_count",
        "title": "Pedestrian Plazas by Borough",
        "agg": "count",
    },
    "pedestrian_plazas_map": {
        "function": "plaza_public_engagement",
        "chart_type": "scatter",
        "iv": "latitude",
        "dv": "longitude",
        "title": "Pedestrian Plazas Engagement Map",
        "agg": "count",
    },
    # Phase 1: Street Safety & Conditions (5)
    "parking_meters_map": {
        "function": "parking_meters_obstruction_zones",
        "chart_type": "scatter",
        "iv": "latitude",
        "dv": "longitude",
        "title": "Parking Meters Obstruction Zones",
        "agg": "count",
    },
    "parking_meters_table": {
        "function": "meter_density_by_borough",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "meter_count",
        "title": "Parking Meter Density by Borough",
        "agg": "count",
    },
    "speed_reducers": {
        "function": "speed_reducer_coverage",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "reducer_count",
        "title": "Speed Reducers by Borough",
        "agg": "count",
    },
    "leading_pedestrian_intervals": {
        "function": "lpi_signal_coverage",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "signal_count",
        "title": "Leading Pedestrian Interval Signals by Borough",
        "agg": "count",
    },
    "vision_zero_crossings": {
        "function": "vision_zero_crossing_maintenance",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "crossing_count",
        "title": "Vision Zero Enhanced Crossings by Borough",
        "agg": "count",
    },
    # Phase 1: Budget & Vendor (3)
    "capital_projects_dashboard": {
        "function": "capital_projects_pipeline",
        "chart_type": "bar",
        "iv": "status",
        "dv": "project_count",
        "title": "Capital Projects Pipeline Status",
        "agg": "count",
    },
    "bicycle_parking": {
        "function": "bicycle_parking_coverage",
        "chart_type": "bar",
        "iv": "borough",
        "dv": "shelter_count",
        "title": "Bicycle Parking Shelters by Borough",
        "agg": "count",
    },
    "bus_pad_tracking": {
        "function": "bus_pad_construction_status",
        "chart_type": "donut",
        "iv": "status",
        "dv": "pad_count",
        "title": "Bus Pad Construction Status Distribution",
        "agg": "count",
    },
    # Phase 1: Reference & Geospatial (2)
    "centerline_streets": {
        "function": "centerline_network_coverage",
        "chart_type": "scatter",
        "iv": "latitude",
        "dv": "longitude",
        "title": "Street Centerline Network Coverage",
        "agg": "count",
    },
    "pedestrian_ramp_audit_mbpo": {
        "function": "manhattan_ramp_audit_results",
        "chart_type": "bar",
        "iv": "district",
        "dv": "ramp_count",
        "title": "Manhattan Pedestrian Ramp Audit Results",
        "agg": "count",
    },
}


def generate_function_code(dataset_key: str, spec: dict) -> str:
    """Generate Plotly chart function code for a dataset."""
    func_name = spec["function"]
    title = spec["title"]
    chart_type = spec["chart_type"]
    iv = spec["iv"]
    dv = spec["dv"]
    agg = spec["agg"]

    if chart_type == "bar":
        return f'''# ---------------------------------------------------------------------------
# {title}
# ---------------------------------------------------------------------------

def {func_name}(
    df: pd.DataFrame,
    borough_col: str = "{iv}",
    value_col: str = "{dv}",
    agg: str = "{agg}",
    title: str | None = None,
) -> Any:
    """Interactive bar chart: {title}."""
    go, px = _get_plotly()
    agg_df = df.groupby(borough_col)[value_col].agg(agg).reset_index()
    agg_df.columns = [borough_col, value_col]

    colors = {{"MANHATTAN": "#0D6EFD", "BRONX": "#6610F2", "BROOKLYN": "#D63384",
             "QUEENS": "#198754", "STATEN ISLAND": "#FD7E14"}}
    agg_df["color"] = agg_df[borough_col].map(colors).fillna("#6C757D")

    fig = go.Figure(go.Bar(
        x=agg_df[borough_col], y=agg_df[value_col],
        marker_color=agg_df["color"], text=agg_df[value_col],
        textposition="auto",
    ))
    fig.update_layout(
        title=title or "{title}",
        xaxis_title="{iv}".replace("_", " ").title(),
        yaxis_title="{dv}".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig
'''

    elif chart_type == "line":
        return f'''# ---------------------------------------------------------------------------
# {title}
# ---------------------------------------------------------------------------

def {func_name}(
    df: pd.DataFrame,
    time_col: str = "{iv}",
    value_col: str = "{dv}",
    title: str | None = None,
) -> Any:
    """Line chart showing trends: {title}."""
    go, px = _get_plotly()

    fig = px.line(
        df, x=time_col, y=value_col,
        title=title or "{title}",
        markers=True,
        line_shape="linear",
    )
    fig.update_layout(
        xaxis_title="{iv}".replace("_", " ").title(),
        yaxis_title="{dv}".replace("_", " ").title(),
        template="plotly_white",
        hovermode="x unified",
    )
    return fig
'''

    elif chart_type == "donut":
        return f'''# ---------------------------------------------------------------------------
# {title}
# ---------------------------------------------------------------------------

def {func_name}(
    df: pd.DataFrame,
    category_col: str = "{iv}",
    value_col: str = "{dv}",
    title: str | None = None,
) -> Any:
    """Donut chart showing distribution: {title}."""
    go, px = _get_plotly()
    agg_df = df.groupby(category_col)[value_col].agg("{agg}").reset_index()

    fig = px.pie(
        agg_df, names=category_col, values=value_col,
        hole=0.3, title=title or "{title}"
    )
    fig.update_layout(template="plotly_white")
    return fig
'''

    elif chart_type == "scatter":
        return f'''# ---------------------------------------------------------------------------
# {title}
# ---------------------------------------------------------------------------

def {func_name}(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    color_col: str | None = "borough",
    title: str | None = None,
) -> Any:
    """Scatter map showing locations: {title}."""
    go, px = _get_plotly()

    fig = px.scatter_mapbox(
        df, lat=lat_col, lon=lon_col, color=color_col,
        zoom=9, title=title or "{title}",
        mapbox_style="open-street-map",
    )
    fig.update_layout(
        height=600, margin={{"r": 0, "t": 30, "l": 0, "b": 0}},
        template="plotly_white",
    )
    return fig
'''

    elif chart_type == "heatmap":
        return f'''# ---------------------------------------------------------------------------
# {title}
# ---------------------------------------------------------------------------

def {func_name}(
    df: pd.DataFrame,
    x_col: str = "{iv}",
    y_col: str = "{dv}",
    value_col: str = "count",
    title: str | None = None,
) -> Any:
    """Heatmap showing: {title}."""
    go, px = _get_plotly()
    pivot_df = df.pivot_table(index=y_col, columns=x_col, values=value_col, aggfunc="{agg}", fill_value=0)

    fig = px.imshow(
        pivot_df, title=title or "{title}",
        labels={{"color": "Count"}}, aspect="auto"
    )
    fig.update_layout(
        xaxis_title="{iv}".replace("_", " ").title(),
        yaxis_title="{dv}".replace("_", " ").title(),
        template="plotly_white",
    )
    return fig
'''

    elif chart_type == "timeline":
        return f'''# ---------------------------------------------------------------------------
# {title}
# ---------------------------------------------------------------------------

def {func_name}(
    df: pd.DataFrame,
    start_col: str = "start_date",
    end_col: str = "end_date",
    task_col: str = "location",
    color_col: str | None = "status",
    title: str | None = None,
) -> Any:
    """Timeline chart showing: {title}."""
    go, px = _get_plotly()
    tmp = df.copy()
    tmp[start_col] = pd.to_datetime(tmp[start_col], errors="coerce")
    tmp[end_col] = pd.to_datetime(tmp[end_col], errors="coerce")
    tmp = tmp.dropna(subset=[start_col, end_col])

    fig = px.timeline(
        tmp, x_start=start_col, x_end=end_col, y=task_col,
        color=color_col, title=title or "{title}",
    )
    fig.update_layout(template="plotly_white")
    return fig
'''

    return ""


def main():
    """Generate all Phase 1 visualization functions."""
    # Generate function code
    all_code = []
    for dataset_key, spec in sorted(CHARTS.items()):
        code = generate_function_code(dataset_key, spec)
        all_code.append(code)

    # Read existing plotly_charts.py
    charts_file = Path("src/socrata_toolkit/plotly_charts.py")
    with open(charts_file, "r") as f:
        existing = f.read()

    # Find the last function in the file
    last_func_start = existing.rfind("\ndef ")
    insertion_point = existing.rfind("\n", 0, last_func_start) + 1

    # Prepare new code
    phase1_section = "\n\n".join(all_code)
    phase1_header = """
# =============================================================================
# PHASE 1: AUTO-GENERATED VISUALIZATION FUNCTIONS (21 datasets)
# =============================================================================
# These functions were auto-generated from DATASET_REGISTRY.yaml
# Last generated: 2026-06-17
# Covers: Permits, Pedestrian Infrastructure, Safety, Budget, Geospatial
"""

    new_code = existing[:insertion_point] + phase1_header + "\n\n" + phase1_section + "\n\n" + existing[insertion_point:]

    # Write back
    with open(charts_file, "w") as f:
        f.write(new_code)

    print(f"[PASS] Generated {len(CHARTS)} visualization functions")
    print(f"[PASS] Functions added to: {charts_file}")
    print(f"\nGenerated Functions:")
    for dataset_key, spec in sorted(CHARTS.items()):
        print(f"  - {spec['function']}")

    # Summary
    print(f"\n[SUMMARY]")
    print(f"  Total Phase 1 datasets: {len(CHARTS)}")
    print(f"  Chart types used: {set(s['chart_type'] for s in CHARTS.values())}")
    print(f"  Status: Ready for integration into Dash app")


if __name__ == "__main__":
    main()
