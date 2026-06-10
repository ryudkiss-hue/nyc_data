"""
GIS Dashboard callbacks for Dash.
Implements callback-based architecture for spatial filtering, clustering, and visualization.
Week 1-3 Phase 1 GIS Pilot implementation.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, no_update

from app.services.cache_service import CacheService
from app.services.gis_service import gis_service

logger = logging.getLogger(__name__)
cache = CacheService()

# =============================================================================
# FILTER SYNCHRONIZATION CALLBACKS
# =============================================================================


@callback(
    Output("gis-session-filters", "data"),
    Input("gis-borough-filter", "value"),
    Input("gis-severity-filter", "value"),
    Input("gis-date-range", "value"),
    prevent_initial_call=False,
)
def sync_gis_filters(boroughs, severity, date_range):
    """
    Synchronize filter selections and store in session.
    Merges borough, severity, and date range filters.

    Args:
        boroughs: List of selected boroughs (MultiSelect value)
        severity: Selected severity level (Select value)
        date_range: [start_date, end_date] from DatePickerRange

    Returns:
        dict: Filter state for use in other callbacks
    """
    filters = {
        "boroughs": boroughs or [],
        "severity": severity or "ALL",
        "date_range": date_range or [None, None],
    }

    # Cache filters in Redis for multi-session persistence
    try:
        cache.set(f"gis-filters:{id(filters)}", filters, ttl_seconds=3600)
    except Exception as e:
        logger.warning(f"Redis cache failed: {e}")

    return filters


# =============================================================================
# DROPDOWN/SELECT POPULATION CALLBACKS
# =============================================================================


@callback(
    Output("gis-borough-filter", "data"),
    Output("gis-severity-filter", "data"),
    Input("gis-data-loader", "children"),  # Triggered when data is ready
    prevent_initial_call=True,
)
def populate_filter_options(trigger_data):
    """
    Populate borough and severity filter options from loaded data.
    Called once after initial data fetch.

    Returns:
        Tuple of (borough_options, severity_options)
    """
    # Assume data loaded via app.data_manager or similar
    # For now, return static NYC boroughs
    borough_options = [
        {"value": "ALL", "label": "All Boroughs"},
        {"value": "MANHATTAN", "label": "Manhattan"},
        {"value": "BROOKLYN", "label": "Brooklyn"},
        {"value": "QUEENS", "label": "Queens"},
        {"value": "BRONX", "label": "Bronx"},
        {"value": "STATEN_ISLAND", "label": "Staten Island"},
    ]

    severity_options = [
        {"value": "ALL", "label": "All Severities"},
        {"value": "CRITICAL", "label": "Critical (0-30)"},
        {"value": "HIGH", "label": "High (31-60)"},
        {"value": "MEDIUM", "label": "Medium (61-80)"},
        {"value": "LOW", "label": "Low (81-100)"},
    ]

    return borough_options, severity_options


# =============================================================================
# VISUALIZATION CALLBACKS: CONDITION MAP
# =============================================================================


@callback(
    Output("viz-condition-map", "figure"),
    Input("gis-session-filters", "data"),
    State("gis-data-store", "data"),
    prevent_initial_call=False,
)
def update_condition_map(filters, data_store):
    """
    Update condition map visualization based on filters.
    Item 1: Condition map with Scatter Mapbox.

    Args:
        filters: Filter state from sync_gis_filters
        data_store: Cached inspection data (dcc.Store)

    Returns:
        Plotly Figure or empty figure if no data
    """
    if not filters or not data_store:
        return go.Figure().add_annotation(
            text="Loading data...",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )

    try:
        # Deserialize data from store
        df = pd.DataFrame(data_store)

        # Apply borough filter
        if filters.get("boroughs") and "ALL" not in filters["boroughs"]:
            df = df[df["borough"].isin(filters["boroughs"])]

        # Apply severity filter
        severity = filters.get("severity", "ALL")
        if severity != "ALL" and "condition_score" in df.columns:
            thresholds = {
                "CRITICAL": (0, 30),
                "HIGH": (31, 60),
                "MEDIUM": (61, 80),
                "LOW": (81, 100),
            }
            if severity in thresholds:
                min_score, max_score = thresholds[severity]
                df = df[df["condition_score"].between(min_score, max_score)]

        # Apply date range filter if present
        if filters.get("date_range") and "inspection_date" in df.columns:
            start_date, end_date = filters["date_range"]
            if start_date and end_date:
                df["inspection_date"] = pd.to_datetime(
                    df["inspection_date"], errors="coerce"
                )
                df = df[df["inspection_date"].between(start_date, end_date)]

        return gis_service.create_condition_map(df)

    except Exception as e:
        logger.error(f"Error updating condition map: {e}")
        return go.Figure().add_annotation(
            text=f"Error: {str(e)[:100]}",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )


# =============================================================================
# VISUALIZATION CALLBACKS: HOTSPOT ANALYSIS (KDE)
# =============================================================================


@callback(
    Output("viz-hotspot-kde", "figure"),
    Input("gis-session-filters", "data"),
    State("gis-data-store", "data"),
    prevent_initial_call=False,
)
def update_hotspot_analysis(filters, data_store):
    """
    Update hotspot KDE heatmap based on filters.
    Item 2: Hotspot analysis with KDE + density visualization.

    Args:
        filters: Filter state
        data_store: Inspection data

    Returns:
        Plotly Figure
    """
    if not filters or not data_store:
        return go.Figure().add_annotation(
            text="Loading data...",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )

    try:
        df = pd.DataFrame(data_store)

        # Filter to critical locations only for hotspot analysis
        if "condition_score" in df.columns:
            df = df[df["condition_score"] <= 35]  # Only critical

        # Apply borough filter
        if filters.get("boroughs") and "ALL" not in filters["boroughs"]:
            df = df[df["borough"].isin(filters["boroughs"])]

        return gis_service.create_kde_heatmap(df, title="Hotspot Analysis (Critical Locations)")

    except Exception as e:
        logger.error(f"Error updating hotspot analysis: {e}")
        return go.Figure().add_annotation(
            text=f"Error: {str(e)[:100]}",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )


# =============================================================================
# VISUALIZATION CALLBACKS: CONFLICT DETECTION
# =============================================================================


@callback(
    Output("viz-conflict-map", "figure"),
    Output("conflict-stats-text", "children"),
    Input("gis-session-filters", "data"),
    State("gis-data-store", "data"),
    State("gis-permits-store", "data"),
    prevent_initial_call=False,
)
def update_conflict_detection(filters, inspection_data, permit_data):
    """
    Detect and visualize spatial conflicts between inspections and permits.
    Item 3: Conflict detection with spatial buffer overlay.

    Args:
        filters: Filter state
        inspection_data: Inspection dataset
        permit_data: Permit dataset

    Returns:
        Tuple of (conflict_map_figure, stats_text)
    """
    if not inspection_data or not permit_data:
        empty_fig = go.Figure().add_annotation(
            text="Load both inspection and permit data",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
        return empty_fig, "No data loaded"

    try:
        df_insp = pd.DataFrame(inspection_data)
        df_perm = pd.DataFrame(permit_data)

        # Detect conflicts
        conflicts = gis_service.detect_conflicts(df_insp, df_perm)

        if conflicts.empty:
            empty_fig = go.Figure().add_annotation(
                text="No conflicts detected",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )
            stats_text = "No conflicts found"
            return empty_fig, stats_text

        # Generate map
        conflict_fig = gis_service.create_conflict_map(conflicts)

        # Generate stats
        high = (conflicts["severity"] == "HIGH").sum()
        med = (conflicts["severity"] == "MEDIUM").sum()
        low = (conflicts["severity"] == "LOW").sum()

        stats_text = (
            f"Total Conflicts: {len(conflicts)} | "
            f"High: {high} | Medium: {med} | Low: {low}"
        )

        return conflict_fig, stats_text

    except Exception as e:
        logger.error(f"Error in conflict detection: {e}")
        error_fig = go.Figure().add_annotation(
            text=f"Error: {str(e)[:100]}",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
        return error_fig, f"Error: {str(e)}"


# =============================================================================
# VISUALIZATION CALLBACKS: BOROUGH AGGREGATION
# =============================================================================


@callback(
    Output("viz-borough-bar", "figure"),
    Input("gis-session-filters", "data"),
    State("gis-data-store", "data"),
    prevent_initial_call=False,
)
def update_borough_aggregation(filters, data_store):
    """
    Aggregate inspection count by borough.

    Args:
        filters: Filter state
        data_store: Inspection data

    Returns:
        Plotly Figure
    """
    if not data_store:
        return go.Figure().add_annotation(
            text="Loading data...",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )

    try:
        df = pd.DataFrame(data_store)

        # Apply severity filter
        severity = filters.get("severity", "ALL") if filters else "ALL"
        if severity != "ALL" and "condition_score" in df.columns:
            thresholds = {
                "CRITICAL": (0, 30),
                "HIGH": (31, 60),
                "MEDIUM": (61, 80),
                "LOW": (81, 100),
            }
            if severity in thresholds:
                min_score, max_score = thresholds[severity]
                df = df[df["condition_score"].between(min_score, max_score)]

        return gis_service.aggregate_by_borough(
            df, value_col="condition_score", title="Inspection Count by Borough"
        )

    except Exception as e:
        logger.error(f"Error updating borough aggregation: {e}")
        return go.Figure().add_annotation(
            text=f"Error: {str(e)[:100]}",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )


# =============================================================================
# VISUALIZATION CALLBACKS: SPATIAL CLUSTERING (DBSCAN)
# =============================================================================


@callback(
    Output("viz-dbscan-clusters", "figure"),
    Output("cluster-stats-text", "children"),
    Input("gis-session-filters", "data"),
    State("gis-data-store", "data"),
    prevent_initial_call=False,
)
def update_dbscan_clustering(filters, data_store):
    """
    Compute and visualize DBSCAN spatial clusters.

    Args:
        filters: Filter state
        data_store: Inspection data

    Returns:
        Tuple of (cluster_map_figure, stats_text)
    """
    if not data_store:
        empty_fig = go.Figure().add_annotation(
            text="Loading data...",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
        return empty_fig, "No data"

    try:
        df = pd.DataFrame(data_store)

        if df.empty or "latitude" not in df.columns:
            empty_fig = go.Figure().add_annotation(
                text="No location data",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )
            return empty_fig, "No location data"

        # Apply borough filter
        if filters and filters.get("boroughs") and "ALL" not in filters["boroughs"]:
            df = df[df["borough"].isin(filters["boroughs"])]

        # Compute clusters
        clusters, n_clusters = gis_service.compute_dbscan_clusters(
            df, eps=0.01, min_samples=5
        )

        # Generate map
        cluster_fig = gis_service.create_cluster_map(
            df, clusters=clusters if len(clusters) > 0 else None
        )

        stats_text = f"Clusters found: {n_clusters} | Points: {len(df)}"

        return cluster_fig, stats_text

    except Exception as e:
        logger.error(f"Error in DBSCAN clustering: {e}")
        error_fig = go.Figure().add_annotation(
            text=f"Error: {str(e)[:100]}",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
        )
        return error_fig, f"Error: {str(e)}"


# =============================================================================
# EXPORT CALLBACKS
# =============================================================================


@callback(
    Output("gis-export-trigger", "data"),
    Input("btn-export-csv", "n_clicks"),
    State("gis-data-store", "data"),
    prevent_initial_call=True,
)
def export_gis_data_csv(n_clicks, data_store):
    """
    Prepare CSV export of filtered GIS data.

    Args:
        n_clicks: Button click count (trigger)
        data_store: Current filtered data

    Returns:
        dict: Data to trigger download (will be handled by dcc.Download)
    """
    if not data_store or n_clicks == 0:
        return no_update

    try:
        df = pd.DataFrame(data_store)
        csv_string = df.to_csv(index=False)

        return {"content": csv_string, "filename": "gis_export.csv"}

    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return no_update
