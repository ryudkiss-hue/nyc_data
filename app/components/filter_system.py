"""
Filter System: Comprehensive warehouse-aware filter bar for the dashboard.

Dynamically loads all raw tables from the DuckDB warehouse and organises them
into two tiers so analysts can filter on any dataset — not just a hardcoded
four. Also exposes Borough, Date-Range, Date-Field, Status, Community-District,
Metric-Type, and Data-Limit controls.
"""

import logging
import os
from pathlib import Path
from typing import Any

import dash_mantine_components as dmc
from dash import Input, Output, State, callback, html, no_update

logger = logging.getLogger(__name__)

# ── Borough options ─────────────────────────────────────────────────────────
BOROUGHS = [
    {"label": "Manhattan",     "value": "MN"},
    {"label": "Brooklyn",      "value": "BK"},
    {"label": "Bronx",         "value": "BX"},
    {"label": "Queens",        "value": "QN"},
    {"label": "Staten Island", "value": "SI"},
]

# ── Metric type options ──────────────────────────────────────────────────────
METRIC_TYPES = [
    {"label": "All Metrics",   "value": "all"},
    {"label": "Critical Only", "value": "critical"},
    {"label": "Active Cases",  "value": "active"},
    {"label": "Completed",     "value": "completed"},
]

# ── Record-status options ────────────────────────────────────────────────────
STATUS_OPTIONS = [
    {"label": "All Statuses",   "value": "all"},
    {"label": "Open",           "value": "open"},
    {"label": "Closed/Resolved","value": "closed"},
    {"label": "Dismissed",      "value": "dismissed"},
    {"label": "In Progress",    "value": "in_progress"},
]

# ── Date-field options (which column to apply the date range to) ─────────────
DATE_FIELD_OPTIONS = [
    {"label": "Inspection Date",  "value": "inspectiondate"},
    {"label": "Entry Date",       "value": "entrydate"},
    {"label": "Issue Date",       "value": "vissuedate"},
    {"label": "Created Date",     "value": "created_date"},
    {"label": "Certification Date","value": "certi_date"},
    {"label": "Post Date",        "value": "post_date"},
]

# ── Tier-1 (core SIM operations) ────────────────────────────────────────────
# Keeps consistent friendly label + value=warehouse table name.
_TIER1 = [
    ("Sidewalk Inspections",          "inspection"),
    ("Violations",                    "violations"),
    ("Built / Construction Projects", "built"),
    ("Re-Inspections",                "reinspection"),
    ("Dismissals",                    "dismissals"),
    ("Correspondences",               "correspondences"),
    ("Tree Damage Assessments",       "tree_damage"),
    ("Curb Metal Protruding",         "curb_metal_protruding"),
    ("Ramp Complaints",               "ramp_complaints"),
    ("Ramp Progress",                 "ramp_progress"),
    ("311 Complaints",                "complaints_311"),
    ("Capital Projects Dashboard",    "capital_projects_dashboard"),
    ("Capital Budget",                "capital_budget"),
    ("Lot Info / MapPLUTO",           "lot_info"),
]

# ── Tier-2 (supporting / context) ───────────────────────────────────────────
_TIER2 = [
    # Capital & budget
    ("Capital Commitment Plan",          "capital_commitment_plan"),
    ("Capital Commitment Actuals",       "capital_commitment_actuals"),
    ("Capital Project Detail – Dollars", "capital_project_detail_dollars"),
    ("Capital Project Detail – Milestones","capital_project_detail_milestones"),
    ("Capital Budget – Schedule History","capital_dashboard_schedule_history"),
    ("Capital Budget – Spend History",   "capital_dashboard_spend_history"),
    ("Capital Budget – FY Spend",        "capital_dashboard_budget_spend_fy"),
    ("State of Good Repair Needs",       "state_of_good_repair_needs"),
    ("CPDB Commitments",                 "cpdb_commitments"),
    ("CPDB Projects",                    "cpdb_projects"),
    ("10-Year Capital Strategy",         "ten_year_capital_strategy"),
    # Street construction
    ("Street Resurfacing – In-House",    "dot_in_house_street_resurfacing_projects"),
    ("Street Closures – Block",          "street_closures_due_to_construction_activities_b"),
    ("Interagency Construction Permits", "interagency_coordination_construction_permits"),
    ("Street Construction Permits",      "street_construction_permits"),
    ("Street Construction Permits – Cranes","street_construction_permits_cranes"),
    ("Street Closures – Block (2)",      "street_closures_due_to_construction_activities_b_2"),
    ("Street Closures – Block (3)",      "street_closures_due_to_construction_activities_b_3"),
    ("Water & Sewer Permits",            "water_sewer_permits"),
    ("Weekly Construction (Archived)",   "weekly_construction"),
    ("Holiday Construction Embargo – Block","holiday_construction_embargo_block"),
    ("Holiday Construction Embargo – Intersection","holiday_construction_embargo_intersection"),
    ("Protected Streets – Block",        "protected_streets_block_dataset"),
    ("Protected Streets – Intersection", "protected_streets_intersection_dataset"),
    ("Street Network Changes",           "street_network_changes"),
    # Vision Zero
    ("Vision Zero – Base Report",        "vision_zero_base_report"),
    ("Vision Zero – Speed Humps",        "vzv_speed_humps"),
    ("Vision Zero – Priority Corridors", "vzv_priority_corridors"),
    ("Vision Zero – Priority Intersections","vzv_priority_intersections"),
    ("Vision Zero – Priority Zones",     "vzv_priority_zones_areas"),
    ("Vision Zero – Enhanced Crossings", "vzv_enhanced_crossings"),
    ("Vision Zero – Senior Centers",     "vzv_senior_centers"),
    ("Vision Zero – Safe Streets Seniors","vzv_safe_streets_for_seniors"),
    ("Vision Zero – Pedestrian Interval Signals","vzv_leading_pedestrian_interval_signals"),
    ("Vision Zero – Arterial Slow Zones","vzv_arterial_slow_zones"),
    ("Vision Zero – Neighborhood Slow Zones","vzv_neighborhood_slow_zones"),
    ("Vision Zero – Bike Priority Areas","vzv_bike_priority_areas"),
    ("Vision Zero – SIP Corridors",      "vzv_street_improvement_projects_sip_corridor"),
    ("Vision Zero – SIP Intersections",  "vzv_street_improvement_projects_sip_intersection"),
    ("Vision Zero – Signal Timing 25 mph","vzv_signal_timing_25mph"),
    ("Vision Zero – Turn Traffic Calming","vzv_turn_traffic_calming"),
    ("Vision Zero – Speed Limits",       "vzv_speed_limits"),
    ("Vision Zero – Street Team Flyers", "vzv_street_team_flyers"),
    ("Vision Zero – Workshops Locations","vzv_workshops_locations"),
    # Planimetric / GIS
    ("Sidewalk Planimetric",             "sidewalk_planimetric"),
    ("Curbs Planimetric",                "curbs_planimetric"),
    ("Boardwalk Planimetric",            "boardwalk_planimetric"),
    ("Median Planimetric",               "median_planimetric"),
    ("Open Space / Parks",               "open_space_parks_planimetric"),
    ("Elevation Points",                 "elevation_points_planimetric"),
    ("Pedestrian Plazas (Polygon)",      "nyc_dot_pedestrian_plazas_polygon"),
    ("Pedestrian Plazas (Point)",        "nyc_dot_pedestrian_plazas_point_feature"),
    ("Public Plazas",                    "public_plazas_planimetric"),
    # Transportation / counts
    ("Bicycle & Pedestrian Counts – Daily","bicycle_pedestrian_counts_daily"),
    ("Bi-Annual Pedestrian Counts",      "bi_annual_pedestrian_counts"),
    ("Bicycle & Pedestrian Count Sensors","bicycle_and_pedestrian_count_sensors"),
    ("Bicycle Parking",                  "bicycle_parking"),
    ("Bicycle Parking Shelters",         "bicycle_parking_shelters"),
    ("Bicycle Routes",                   "new_york_city_bike_routes"),
    ("Bus Lanes – Local Streets",        "bus_lanes_local_streets"),
    ("Bus Stop Shelters",                "bus_stop_shelters"),
    ("Accessible Pedestrian Signals",    "accessible_pedestrian_signal_locations"),
    ("Exclusive Pedestrian Signals (Barnes Dance)","exclusive_pedestrian_signal_barnes_dance_locatio"),
    ("Pedestrian Space Added",           "pedestrian_space_added"),
    ("Pedestrian Demand",                "pedestrian_demand"),
    # Street management
    ("Open Streets",                     "open_streets_locations"),
    ("Seating Locations",                "seating_locations"),
    ("Sidewalk Cafes",                   "sidewalk_cafes"),
    ("Street Seats 2021–2024",           "street_seats_2021_2024"),
    ("Step Streets",                     "step_streets"),
    ("Raised Crosswalk Locations",       "raised_crosswalk_locations"),
    ("Newsrack Inspections",             "newsrack_inspections"),
    # Capital reconstruction & street condition
    ("Capital Reconstruction Projects",  "street_and_highway_capital_reconstruction_projec"),
    ("Capital Reconstruction Projects 2","street_and_highway_capital_reconstruction_projec_2"),
    ("MBPO Pedestrian Ramp Report",      "mbpo_pedestrian_ramp_report"),
    ("Street Pavement Ratings",          "street_pavement_ratings"),
    ("Street Pothole Work Orders (Closed)","street_pothole_work_orders_closed_dataset"),
    ("Street Resurfacing Schedule",      "street_resurfacing_schedule"),
    ("Street Centerline",                "street_centerline"),
    ("Roadbed Planimetric",              "roadbed_planimetric"),
    ("Speed Reducer Tracking (SRTS)",    "speed_reducer_tracking_srts"),
    # Motor vehicle collisions (Vision Zero source data)
    ("Motor Vehicle Collisions – Crashes","motor_vehicle_collisions_crashes"),
    ("Motor Vehicle Collisions – Persons","motor_vehicle_collisions_person"),
    # Capital project geospatial (CPDB)
    ("CPDB Projects – Points",           "cpdb_projects_points"),
    ("CPDB Projects – Polygons",         "cpdb_projects_polygons"),
    # Ramp locations (stale since 2021 — use ramp_progress for current data)
    ("Ramp Locations (Stale 2021)",      "ramp_locations"),
    # Demographics / equity
    ("Census Demographics – NTA",        "census_demographics_nta"),
    ("Heat Vulnerability Index",         "heat_vulnerability_index"),
    ("Street Tree Census 2015",          "street_tree_census_2015"),
    ("NTA 2020 Boundaries",              "nta_2020"),
    ("Walk to Park Service Area",        "walk_to_a_park_service_area"),
    # Parking / misc
    ("Parking Meters / ParkNYC",         "parking_meters_parknyc_block_faces"),
    ("Parking Permits – Disability (PPPD)","parking_permit_for_people_with_disabilities_pppd"),
    ("Parking Permits – Disability (PPPD 2)","parking_permit_for_people_with_disabilities_pppd_2"),
    ("Temporary Disability Parking Permits","temporary_parking_permit_for_people_with_disabil"),
    ("Carshare – Curbside",              "carshare_locations_curbside"),
    ("Shared E-Scooter Corrals",         "shared_e_scooter_parking_corrals"),
    ("Privately Owned Public Spaces",    "privately_owned_public_spaces_pops"),
    ("DOB Stalled Construction Sites",   "dob_stalled_construction_sites"),
    ("Encroachments & Defacements",      "encroachments_and_defacements"),
    ("Forestry Inspections",             "forestry_inspections"),
    ("Intercity Bus Stop Permits",       "intercity_bus_stop_permits"),
    ("Bikes in Buildings Requests",      "bikes_in_buildings_requests"),
    ("Street Direction Change Requests", "street_direction_change_requests_2019_present"),
]

# Default tier-1 datasets selected on load
_DEFAULT_DATASETS = [v for _, v in _TIER1]


def _build_dataset_options() -> list[dict]:
    """Build grouped dataset options for the MultiSelect from tier lists."""
    options: list[dict] = []
    # Tier 1 group
    options.append({"value": "__t1_header__", "label": "── TIER 1: Core SIM Operations ──", "disabled": True})
    for label, value in _TIER1:
        options.append({"label": label, "value": value})
    # Tier 2 group
    options.append({"value": "__t2_header__", "label": "── TIER 2: Supporting & Context ──", "disabled": True})
    for label, value in _TIER2:
        options.append({"label": label, "value": value})
    return options


# Build once at import
_DATASET_OPTIONS = _build_dataset_options()


def render_filter_bar() -> html.Div:
    """Render the comprehensive multi-field filter bar."""
    return html.Div(
        [
            # ── Row 1: Dataset selector (full width) ──────────────────────
            dmc.MultiSelect(
                id="filter-dataset-select",
                label="Datasets (Tier 1 + Tier 2 combined)",
                searchable=True,
                clearable=True,
                data=_DATASET_OPTIONS,
                value=_DEFAULT_DATASETS,
                maxValues=None,
                style={"marginBottom": "12px"},
            ),
            # ── Row 2: Geography filters ─────────────────────────────────
            dmc.Group(
                [
                    dmc.MultiSelect(
                        id="filter-borough-select",
                        label="Borough",
                        searchable=True,
                        clearable=True,
                        data=BOROUGHS,
                        value=["MN", "BK", "BX", "QN", "SI"],
                        style={"flex": 1, "minWidth": "160px"},
                    ),
                    dmc.MultiSelect(
                        id="filter-community-district",
                        label="Community District",
                        searchable=True,
                        clearable=True,
                        data=[
                            {"label": f"MN {n:02d}", "value": f"1{n:02d}"}
                            for n in range(1, 13)
                        ] + [
                            {"label": f"BX {n:02d}", "value": f"2{n:02d}"}
                            for n in range(1, 13)
                        ] + [
                            {"label": f"BK {n:02d}", "value": f"3{n:02d}"}
                            for n in range(1, 19)
                        ] + [
                            {"label": f"QN {n:02d}", "value": f"4{n:02d}"}
                            for n in range(1, 15)
                        ] + [
                            {"label": f"SI {n:02d}", "value": f"5{n:02d}"}
                            for n in range(1, 4)
                        ],
                        value=[],
                        placeholder="All districts",
                        style={"flex": 1, "minWidth": "160px"},
                    ),
                ],
                grow=True,
                gap="md",
                mb="xs",
            ),
            # ── Row 3: Date controls ─────────────────────────────────────
            dmc.Group(
                [
                    dmc.Select(
                        id="filter-date-field",
                        label="Date Field",
                        data=DATE_FIELD_OPTIONS,
                        value="inspectiondate",
                        clearable=False,
                        style={"flex": 1, "minWidth": "160px"},
                    ),
                    dmc.DateInput(
                        id="filter-date-start",
                        label="From",
                        placeholder="Start date",
                        valueFormat="YYYY-MM-DD",
                        style={"flex": 1, "minWidth": "130px"},
                    ),
                    dmc.DateInput(
                        id="filter-date-end",
                        label="To",
                        placeholder="End date",
                        valueFormat="YYYY-MM-DD",
                        style={"flex": 1, "minWidth": "130px"},
                    ),
                ],
                grow=True,
                gap="md",
                mb="xs",
            ),
            # ── Row 4: Record attributes ─────────────────────────────────
            dmc.Group(
                [
                    dmc.Select(
                        id="filter-status",
                        label="Record Status",
                        data=STATUS_OPTIONS,
                        value="all",
                        clearable=False,
                        style={"flex": 1, "minWidth": "160px"},
                    ),
                    dmc.Select(
                        id="filter-metric-type",
                        label="Metric Type",
                        data=METRIC_TYPES,
                        value="all",
                        searchable=True,
                        clearable=False,
                        style={"flex": 1, "minWidth": "160px"},
                    ),
                    dmc.Select(
                        id="filter-data-limit",
                        label="Rows per Dataset",
                        data=[
                            {"label": "No limit",        "value": "none"},
                            {"label": "1,000 records",   "value": "1000"},
                            {"label": "10,000 records",  "value": "10000"},
                            {"label": "100,000 records", "value": "100000"},
                        ],
                        value="none",
                        style={"flex": 1, "minWidth": "160px"},
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Apply Filters",
                                id="filter-apply-btn",
                                size="sm",
                                variant="filled",
                                color="blue",
                            ),
                            dmc.Button(
                                "Reset",
                                id="filter-reset-btn",
                                size="sm",
                                variant="outline",
                                color="gray",
                                style={"color": "#545b62"},
                            ),
                        ],
                        grow=False,
                        gap="sm",
                        align="flex-end",
                    ),
                ],
                grow=True,
                gap="md",
            ),
            dmc.LoadingOverlay(
                id="filter-loading-overlay",
                visible=False,
                loaderProps={"type": "bars", "color": "blue"},
            ),
        ],
        style={
            "padding": "20px",
            "backgroundColor": "#f8f9fa",
            "borderRadius": "8px",
            "marginBottom": "20px",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
        },
    )


def register_filter_callbacks() -> None:
    """Register Apply/Reset callbacks that broadcast the global filter store."""

    @callback(
        Output("store-global-filters", "data"),
        Input("filter-apply-btn",  "n_clicks"),
        Input("filter-reset-btn",  "n_clicks"),
        State("filter-borough-select",     "value"),
        State("filter-community-district", "value"),
        State("filter-date-field",         "value"),
        State("filter-date-start",         "value"),
        State("filter-date-end",           "value"),
        State("filter-status",             "value"),
        State("filter-metric-type",        "value"),
        State("filter-dataset-select",     "value"),
        State("filter-data-limit",         "value"),
        prevent_initial_call=True,
    )
    def update_global_filters(
        apply_clicks: int,
        reset_clicks: int,
        boroughs: list[str],
        community_districts: list[str],
        date_field: str,
        date_start: str,
        date_end: str,
        status: str,
        metric_type: str,
        datasets: list[str],
        data_limit: str,
    ) -> dict[str, Any]:
        if not any([apply_clicks, reset_clicks]):
            return no_update

        from dash import ctx
        ctx_id = getattr(ctx, "triggered_id", None)

        _all_boroughs = ["MN", "BK", "BX", "QN", "SI"]
        _all_datasets = _DEFAULT_DATASETS  # tier-1 defaults on reset

        if ctx_id == "filter-reset-btn":
            logger.info("Filters reset to defaults")
            return {
                "boroughs":           _all_boroughs,
                "community_districts": [],
                "date_field":         "inspectiondate",
                "date_start":         None,
                "date_end":           None,
                "status":             "all",
                "metric_type":        "all",
                "datasets":           _all_datasets,
                "data_limit":         "none",
            }

        # Apply button
        filters_dict = {
            "boroughs":           boroughs or _all_boroughs,
            "community_districts": community_districts or [],
            "date_field":         date_field or "inspectiondate",
            "date_start":         date_start,
            "date_end":           date_end,
            "status":             status or "all",
            "metric_type":        metric_type or "all",
            "datasets":           [d for d in (datasets or _all_datasets) if not d.startswith("__")],
            "data_limit":         data_limit or "none",
        }
        logger.info(f"Filters applied: {len(filters_dict['datasets'])} datasets, boroughs={filters_dict['boroughs']}")
        return filters_dict
