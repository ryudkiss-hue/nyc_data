"""
Analytics Integration Callbacks: Phase C-F
Integrates all 5 AnalyticsEngine chart methods into Dash views.
- Phase C: Distribution Classification → Analytics View
- Phase D: Anomaly Detection → Quality Dashboard
- Phase E: Seasonal Decomposition → Labor/Temporal View
- Phase F: Bootstrap CI → Executive Metric Dashboard

Pattern: Each callback fetches data → calls AnalyticsEngine method → renders Figure + Narrative
"""

import logging
from typing import Any

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc

from app.callbacks.analytics import AnalyticsEngine
from app.services.analytics_service import validate_filters
from app.services.dashboard_state import DashboardStateAdapter

logger = logging.getLogger(__name__)

# =============================================================================
# PHASE C: DISTRIBUTION CLASSIFICATION → ANALYTICS VIEW
# =============================================================================

@callback(
    Output("distribution-chart-container", "children"),
    Output("distribution-narrative", "children"),
    Input("store-global-filters", "data"),
    Input("distribution-column-limit", "value"),
    prevent_initial_call=False,
)
def update_distribution_classification(filters: dict, limit: int = 8) -> tuple[Any, str]:
    """
    Update Distribution Classification visualization.
    Analyzes numeric column distributions (normal, skewed, etc.).

    Args:
        filters: Global filter state (borough, date_range)
        limit: Max columns to analyze (default 8)

    Returns:
        tuple[dmc.Stack, str]: Chart container with multiple figures + S-DIKW narrative
    """
    try:
        if not validate_filters(filters):
            return (
                dmc.Stack([dmc.Text("No filters configured. Please select a dataset.", c="orange")]),
                "Distribution analysis requires valid filters."
            )

        # Build data_bundle for AnalyticsEngine
        state = DashboardStateAdapter(None, filters)
        df = state.get_analytics_dataset()
        if df.empty:
            return (
                dmc.Stack([dmc.Text("No data available for analysis.", c="orange")]),
                "Insufficient data for distribution analysis."
            )

        data_bundle = {'data': df}

        # Call AnalyticsEngine method
        fig, narrative = AnalyticsEngine.chart_distribution_classification(data_bundle)

        # Render with narrative panel
        chart_container = dmc.Stack([
            dmc.Paper(
                withBorder=True,
                p="md",
                radius="lg",
                shadow="sm",
                children=[
                    dmc.Text("Distribution Analysis", fw=700, size="lg"),
                    dcc.Graph(figure=fig, config={'displayModeBar': True}),
                    dmc.Text(
                        f"Analyzed {len(df):,} records across {len(df.select_dtypes(include=['number']).columns)} numeric columns.",
                        size="xs",
                        c="gray",
                        ta="right"
                    ),
                ]
            )
        ])

        logger.info(f"Distribution classification rendered ({len(df)} rows)")
        return chart_container, narrative

    except Exception as e:
        logger.error(f"Distribution classification error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            f"Error in distribution analysis: {str(e)}"
        )

# =============================================================================
# PHASE D: ANOMALY DETECTION → QUALITY DASHBOARD
# =============================================================================

@callback(
    Output("anomaly-detection-chart", "children"),
    Output("anomaly-narrative", "children"),
    Output("anomaly-count-badge", "children"),
    Input("store-global-filters", "data"),
    Input("anomaly-detection-toggle", "checked"),
    prevent_initial_call=False,
)
def update_anomaly_detection(filters: dict, enabled: bool = True) -> tuple[Any, str, str]:
    """
    Update Anomaly Detection visualization.
    Detects spatial outliers using IQR method.

    Args:
        filters: Global filter state
        enabled: Toggle to enable/disable analysis

    Returns:
        tuple[dmc.Stack, str, str]: Chart container + narrative + anomaly badge
    """
    try:
        if not enabled or not validate_filters(filters):
            return (
                dmc.Stack([dmc.Text("Anomaly detection disabled or no filters.", c="gray")]),
                "Anomaly detection is not enabled.",
                "0 anomalies"
            )

        # Fetch spatial data
        state = DashboardStateAdapter(None, filters)
        gdf = state.get_spatial_dataset()
        if gdf.empty:
            return (
                dmc.Stack([dmc.Text("No spatial data available.", c="orange")]),
                "Insufficient spatial data for anomaly detection.",
                "N/A"
            )

        data_bundle = {'spatial': gdf}

        # Call AnalyticsEngine method
        fig, narrative = AnalyticsEngine.chart_anomaly_detection(data_bundle)

        # Extract anomaly count from narrative (simple regex or count directly)
        numeric_cols = gdf.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            col = numeric_cols[0]
            data = gdf[col].dropna()
            Q1, Q3 = data.quantile([0.25, 0.75])
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            n_anomalies = ((gdf[col] < lower_bound) | (gdf[col] > upper_bound)).sum()
            badge_text = f"{n_anomalies:,} anomalies ({100*n_anomalies/len(gdf):.1f}%)"
        else:
            badge_text = "N/A"

        chart_container = dmc.Stack([
            dmc.Paper(
                withBorder=True,
                p="md",
                radius="lg",
                shadow="sm",
                children=[
                    dmc.Group([
                        dmc.Text("Spatial Anomaly Detection", fw=700, size="lg"),
                        dmc.Badge(badge_text, color="red" if n_anomalies > 0 else "green", size="lg"),
                    ], justify="space-between"),
                    dcc.Graph(figure=fig, config={'displayModeBar': True}),
                ]
            )
        ])

        logger.info(f"Anomaly detection rendered ({len(gdf)} spatial points, {n_anomalies} anomalies)")
        return chart_container, narrative, badge_text

    except Exception as e:
        logger.error(f"Anomaly detection error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            f"Error in anomaly detection: {str(e)}",
            "Error"
        )

# =============================================================================
# PHASE E: SEASONAL DECOMPOSITION → TEMPORAL PATTERNS VIEW
# =============================================================================

@callback(
    Output("decomposition-chart-container", "children"),
    Output("decomposition-narrative", "children"),
    Input("store-global-filters", "data"),
    Input("decomposition-date-col", "value"),
    Input("decomposition-value-col", "value"),
    prevent_initial_call=False,
)
def update_seasonal_decomposition(filters: dict, date_col: str = None, value_col: str = None) -> tuple[Any, str]:
    """
    Update Seasonal Decomposition visualization.
    Decomposes time series into trend, seasonal, and residual components.

    Args:
        filters: Global filter state
        date_col: Name of date column (e.g., 'created_date')
        value_col: Name of value column to decompose (e.g., 'violation_count')

    Returns:
        tuple[dmc.Stack, str]: 4-panel decomposition chart + S-DIKW narrative
    """
    try:
        if not validate_filters(filters) or not date_col or not value_col:
            return (
                dmc.Stack([dmc.Text("Decomposition requires date and value columns.", c="orange")]),
                "Seasonal decomposition requires configuration."
            )

        # Fetch time series data
        state = DashboardStateAdapter(None, filters)
        ts_df = state.get_timeseries_dataset()
        if ts_df.empty or len(ts_df) < 20:
            return (
                dmc.Stack([dmc.Text(f"Insufficient time series data ({len(ts_df)} points).", c="orange")]),
                "Time series decomposition requires 20+ data points."
            )

        data_bundle = {'timeseries': ts_df}

        # Call AnalyticsEngine method
        fig, narrative = AnalyticsEngine.chart_seasonal_decomposition(data_bundle)

        chart_container = dmc.Stack([
            dmc.Paper(
                withBorder=True,
                p="md",
                radius="lg",
                shadow="sm",
                children=[
                    dmc.Text("Time Series Decomposition", fw=700, size="lg"),
                    dcc.Graph(figure=fig, config={'displayModeBar': True, 'responsive': True}),
                    dmc.Text(
                        f"Analyzed {len(ts_df)} time points from {date_col}. Moving average window: 7 days.",
                        size="xs",
                        c="gray",
                        ta="right"
                    ),
                ]
            )
        ])

        logger.info(f"Decomposition rendered ({len(ts_df)} time series points)")
        return chart_container, narrative

    except Exception as e:
        logger.error(f"Seasonal decomposition error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            f"Error in decomposition: {str(e)}"
        )

# =============================================================================
# PHASE F: BOOTSTRAP CONFIDENCE INTERVALS → EXECUTIVE DASHBOARD
# =============================================================================

@callback(
    Output("metric-bootstrap-figures", "children"),
    Output("metric-bootstrap-summary", "children"),
    Input("store-global-filters", "data"),
    Input("metric-refresh-interval", "n_intervals"),
    prevent_initial_call=False,
)
def update_bootstrap_ci_metrics(filters: dict, n_intervals: int = 0) -> tuple[Any, str]:
    """
    Update Metric gauges with Bootstrap Confidence Intervals.
    Wraps existing Metric metrics with uncertainty quantification.

    Args:
        filters: Global filter state
        n_intervals: Refresh counter for polling

    Returns:
        tuple[dmc.SimpleGrid, str]: Grid of Metric gauges with CI bands + summary narrative
    """
    try:
        # Fetch Metric metrics (with CI already computed by get_metric_metrics)
        state = DashboardStateAdapter(None, filters)
        metrics = state.get_metrics_dataset()

        if not metrics or len(metrics) == 0:
            return (
                dmc.Stack([dmc.Text("No Metric metrics available.", c="orange")]),
                "Metric analysis requires valid data."
            )

        # Remove metadata flag
        metrics = {k: v for k, v in metrics.items() if not k.startswith('_')}

        # Create gauge figures for each metric
        gauge_figures = []
        narratives = []

        for metric_name, (point_est, ci_lower, ci_upper) in metrics.items():
            # Call AnalyticsEngine for each metric
            metric_bundle = {'metrics': {metric_name: (point_est, ci_lower, ci_upper)}}
            fig, narrative = AnalyticsEngine.chart_bootstrap_ci(metric_bundle)

            # Render gauge
            gauge_card = dmc.Paper(
                withBorder=True,
                p="md",
                radius="lg",
                shadow="sm",
                children=[
                    dmc.Text(metric_name.replace('_', ' ').title(), fw=700, size="md", mb="xs"),
                    dcc.Graph(figure=fig, config={'displayModeBar': False}),
                    dmc.Stack([
                        dmc.Text(f"Point Estimate: {point_est:.2f}", size="sm"),
                        dmc.Text(f"95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]", size="sm", c="dimmed"),
                    ], gap="xs"),
                ]
            )
            gauge_figures.append(gauge_card)
            narratives.append(narrative)

        # Assemble into responsive grid
        metric_grid = dmc.SimpleGrid(
            cols={"base": 1, "sm": 2, "md": 4},
            gap="md",
            children=gauge_figures
        )

        # Combined narrative
        summary = "Bootstrap confidence intervals provide uncertainty quantification for all Metric metrics. Narrow intervals indicate stable metrics; wide intervals suggest high variability."

        logger.info(f"Bootstrap CI Metrics rendered ({len(metrics)} metrics)")
        return metric_grid, summary

    except Exception as e:
        logger.error(f"Bootstrap CI error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            f"Error in Metric analysis: {str(e)}"
        )

# =============================================================================
# PHASE B (Existing): MORAN'S I SPATIAL AUTOCORRELATION
# (Integrated into GIS Dashboard via separate callback)
# =============================================================================

@callback(
    Output("morans-i-gauge", "figure"),
    Output("morans-i-narrative", "children"),
    Input("store-global-filters", "data"),
    Input("morans-i-column-select", "value"),
    prevent_initial_call=False,
)
def update_morans_i(filters: dict, column: str = None) -> tuple[go.Figure, str]:
    """
    Update Moran's I spatial autocorrelation gauge.
    Detects spatial clustering patterns.

    Args:
        filters: Global filter state
        column: Numeric column to analyze

    Returns:
        tuple[go.Figure, str]: Gauge figure + S-DIKW narrative
    """
    try:
        if not validate_filters(filters):
            empty_fig = go.Figure()
            return empty_fig, "No spatial data available for Moran's I analysis."

        # Fetch spatial data (Moran's I requires geographic boundaries)
        state = DashboardStateAdapter(None, filters)
        gdf = state.get_spatial_dataset()
        if gdf.empty or len(gdf) < 10:
            empty_fig = go.Figure()
            return empty_fig, "Insufficient spatial data (minimum 10 points required)."

        # Auto-select column if not provided
        if not column:
            numeric_cols = gdf.select_dtypes(include=['number']).columns
            if len(numeric_cols) == 0:
                empty_fig = go.Figure()
                return empty_fig, "No numeric columns available for spatial analysis."
            column = numeric_cols[0]

        data_bundle = {'spatial': gdf}

        # Call AnalyticsEngine method
        fig, narrative = AnalyticsEngine.chart_morans_i(data_bundle)

        logger.info(f"Moran's I rendered for column '{column}' ({len(gdf)} spatial points)")
        return fig, narrative

    except Exception as e:
        logger.error(f"Moran's I error: {e}", exc_info=True)
        empty_fig = go.Figure()
        return empty_fig, f"Error in Moran's I analysis: {str(e)}"

# =============================================================================
# UTILITY: FILTER CHANGE LISTENER
# (Ensures all charts update when filters change)
# =============================================================================

@callback(
    Output("analytics-refresh-trigger", "data"),
    Input("store-global-filters", "data"),
    prevent_initial_call=False,
)
def trigger_all_updates(filters: dict) -> dict:
    """
    Universal trigger for all analytics updates when filters change.
    Broadcasts filter change to all dependent callbacks.

    Args:
        filters: Updated global filters

    Returns:
        dict: Updated filters for downstream callbacks
    """
    logger.debug(f"Analytics refresh triggered: {filters}")
    return filters or {}

