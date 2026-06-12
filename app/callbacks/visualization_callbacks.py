"""
Visualization Callbacks: Phase B-F integration with MotherDuck data.

Wires 5 AnalyticsEngine methods to Dash callbacks:
- Phase B: Moran's I spatial autocorrelation
- Phase C: Distribution classification
- Phase D: Anomaly detection
- Phase E: Seasonal decomposition
- Phase F: Bootstrap CI / SLA forecast

Data flow:
    User filter change → store-global-filters updated
    → callback fetches from MotherDuck view
    → AnalyticsEngine method renders Figure + Narrative
    → callback returns (figure, narrative_html, statistics_html)

All callbacks target <500ms latency.
"""

import logging
import traceback
from typing import Any

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from app.callbacks.analytics import AnalyticsEngine
from app.callbacks.decorators import memoize_with_ttl, timer_callback
from app.services.motherduck_service import (
    fetch_phase_b_results,
    fetch_phase_c_results,
    fetch_phase_d_results,
    fetch_phase_e_decomposition,
    fetch_phase_f_bootstrap_ci,
)

logger = logging.getLogger(__name__)

def _render_statistics_panel(stats: dict[str, Any]) -> html.Div:
    """
    Render a statistics panel below each visualization.

    Args:
        stats: Dictionary of statistics to display

    Returns:
        html.Div: Styled statistics panel
    """
    if not stats:
        return html.Div()

    stat_items = []
    for key, value in stats.items():
        if isinstance(value, float):
            formatted = f"{value:.2f}"
        else:
            formatted = str(value)

        stat_items.append(
            dmc.Group(
                [
                    dmc.Text(key, size="sm", c="dimmed", fw=500, style={"minWidth": "100px"}),
                    dmc.Text(formatted, size="sm", fw=700),
                ],
                spacing="sm",
                style={"paddingBottom": "6px"},
            )
        )

    return dmc.Paper(
        withBorder=True,
        p="md",
        radius="lg",
        shadow="xs",
        style={"backgroundColor": "#f8f9fa", "marginTop": "12px"},
        children=dmc.Stack(stat_items, spacing="xs"),
    )

def _render_narrative_panel(narrative: str) -> html.Div:
    """
    Render narrative panel with S-DIKW insights.

    Args:
        narrative: Narrative text (HTML or plain)

    Returns:
        html.Div: Styled narrative panel
    """
    return dmc.Paper(
        withBorder=True,
        p="md",
        radius="lg",
        shadow="xs",
        style={"backgroundColor": "#f0f8ff", "borderColor": "#1e90ff", "borderWidth": "2px"},
        children=[
            dmc.Text("Key Insight", size="sm", fw=700, c="blue", mb="xs"),
            dmc.Text(narrative, size="sm", lineClamp=4),
        ],
    )

# =============================================================================
# PHASE B: MORAN'S I SPATIAL AUTOCORRELATION
# =============================================================================

@callback(
    Output("phase-b-figure", "children"),
    Output("phase-b-narrative", "children"),
    Output("phase-b-statistics", "children"),
    Input("store-global-filters", "data"),
    prevent_initial_call=False,
)
@timer_callback
@memoize_with_ttl(seconds=600)
def update_phase_b_morans_i(
    filters: dict[str, Any],
) -> tuple[html.Div, html.Div, html.Div]:
    """
    Update Phase B visualization: Moran's I spatial clustering.

    Args:
        filters: Global filter state (boroughs, date_range, metric_type)

    Returns:
        tuple[html.Div, html.Div, html.Div]: (figure, narrative, statistics)
    """
    try:
        # Fetch data from MotherDuck
        df = fetch_phase_b_results(filters)
        if df is None or df.empty:
            return (
                dmc.Stack([dmc.Text("No data available for Phase B", c="orange")]),
                _render_narrative_panel("Insufficient data for spatial analysis."),
                html.Div(),
            )

        # Build data bundle for AnalyticsEngine
        data_bundle = {"spatial": df}

        # Render chart + narrative
        fig, narrative = AnalyticsEngine.chart_morans_i(data_bundle)

        # Extract statistics from figure
        stats = {
            "Borough Count": len(df),
            "Avg Moran's I": df.get("morans_i", [0]).mean() if "morans_i" in df else 0,
        }

        return (
            dmc.Stack([dcc.Graph(figure=fig, config={"displayModeBar": False})]),
            _render_narrative_panel(narrative),
            _render_statistics_panel(stats),
        )

    except Exception as e:
        logger.error(f"Phase B error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            _render_narrative_panel(f"Error in Phase B analysis: {str(e)}"),
            html.Div(),
        )

# =============================================================================
# PHASE C: DISTRIBUTION CLASSIFICATION
# =============================================================================

@callback(
    Output("phase-c-figure", "children"),
    Output("phase-c-narrative", "children"),
    Output("phase-c-statistics", "children"),
    Input("store-global-filters", "data"),
    prevent_initial_call=False,
)
@timer_callback
@memoize_with_ttl(seconds=600)
def update_phase_c_distribution(
    filters: dict[str, Any],
) -> tuple[html.Div, html.Div, html.Div]:
    """
    Update Phase C visualization: Distribution classification.

    Args:
        filters: Global filter state

    Returns:
        tuple[html.Div, html.Div, html.Div]: (figure, narrative, statistics)
    """
    try:
        df = fetch_phase_c_results(filters)
        if df is None or df.empty:
            return (
                dmc.Stack([dmc.Text("No data available for Phase C", c="orange")]),
                _render_narrative_panel("Insufficient data for distribution analysis."),
                html.Div(),
            )

        data_bundle = {"data": df}
        fig, narrative = AnalyticsEngine.chart_distribution_classification(data_bundle)

        stats = {
            "Records": len(df),
            "Distribution Types": df.get("distribution_type", []).nunique() if "distribution_type" in df else 0,
        }

        return (
            dmc.Stack([dcc.Graph(figure=fig, config={"displayModeBar": False})]),
            _render_narrative_panel(narrative),
            _render_statistics_panel(stats),
        )

    except Exception as e:
        logger.error(f"Phase C error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            _render_narrative_panel(f"Error in Phase C analysis: {str(e)}"),
            html.Div(),
        )

# =============================================================================
# PHASE D: ANOMALY DETECTION
# =============================================================================

@callback(
    Output("phase-d-figure", "children"),
    Output("phase-d-narrative", "children"),
    Output("phase-d-statistics", "children"),
    Input("store-global-filters", "data"),
    prevent_initial_call=False,
)
@timer_callback
@memoize_with_ttl(seconds=600)
def update_phase_d_anomalies(
    filters: dict[str, Any],
) -> tuple[html.Div, html.Div, html.Div]:
    """
    Update Phase D visualization: Anomaly detection.

    Args:
        filters: Global filter state

    Returns:
        tuple[html.Div, html.Div, html.Div]: (figure, narrative, statistics)
    """
    try:
        df = fetch_phase_d_results(filters)
        if df is None or df.empty:
            return (
                dmc.Stack([dmc.Text("No data available for Phase D", c="orange")]),
                _render_narrative_panel("Insufficient data for anomaly analysis."),
                html.Div(),
            )

        data_bundle = {"geographic": df}
        fig, narrative = AnalyticsEngine.chart_anomaly_detection(data_bundle)

        stats = {
            "Anomalies": len(df),
            "High Severity": (df.get("severity") == "HIGH").sum() if "severity" in df else 0,
        }

        return (
            dmc.Stack([dcc.Graph(figure=fig, config={"displayModeBar": False})]),
            _render_narrative_panel(narrative),
            _render_statistics_panel(stats),
        )

    except Exception as e:
        logger.error(f"Phase D error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            _render_narrative_panel(f"Error in Phase D analysis: {str(e)}"),
            html.Div(),
        )

# =============================================================================
# PHASE E: SEASONAL DECOMPOSITION
# =============================================================================

@callback(
    Output("phase-e-figure", "children"),
    Output("phase-e-narrative", "children"),
    Output("phase-e-statistics", "children"),
    Input("store-global-filters", "data"),
    prevent_initial_call=False,
)
@timer_callback
@memoize_with_ttl(seconds=600)
def update_phase_e_decomposition(
    filters: dict[str, Any],
) -> tuple[html.Div, html.Div, html.Div]:
    """
    Update Phase E visualization: Seasonal decomposition.

    Args:
        filters: Global filter state

    Returns:
        tuple[html.Div, html.Div, html.Div]: (figure, narrative, statistics)
    """
    try:
        df = fetch_phase_e_decomposition(filters)
        if df is None or df.empty:
            return (
                dmc.Stack([dmc.Text("No data available for Phase E", c="orange")]),
                _render_narrative_panel("Insufficient data for time series analysis."),
                html.Div(),
            )

        data_bundle = {"timeseries": df}
        fig, narrative = AnalyticsEngine.chart_seasonal_decomposition(data_bundle)

        stats = {
            "Periods": len(df),
            "Avg Trend": df.get("trend", [0]).mean() if "trend" in df else 0,
        }

        return (
            dmc.Stack([dcc.Graph(figure=fig, config={"displayModeBar": False})]),
            _render_narrative_panel(narrative),
            _render_statistics_panel(stats),
        )

    except Exception as e:
        logger.error(f"Phase E error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            _render_narrative_panel(f"Error in Phase E analysis: {str(e)}"),
            html.Div(),
        )

# =============================================================================
# PHASE F: BOOTSTRAP CI / SLA FORECAST
# =============================================================================

@callback(
    Output("phase-f-figure", "children"),
    Output("phase-f-narrative", "children"),
    Output("phase-f-statistics", "children"),
    Input("store-global-filters", "data"),
    prevent_initial_call=False,
)
@timer_callback
@memoize_with_ttl(seconds=600)
def update_phase_f_bootstrap_ci(
    filters: dict[str, Any],
) -> tuple[html.Div, html.Div, html.Div]:
    """
    Update Phase F visualization: Bootstrap CI / SLA forecast.

    Args:
        filters: Global filter state

    Returns:
        tuple[html.Div, html.Div, html.Div]: (figure, narrative, statistics)
    """
    try:
        df = fetch_phase_f_bootstrap_ci(filters)
        if df is None or df.empty:
            return (
                dmc.Stack([dmc.Text("No data available for Phase F", c="orange")]),
                _render_narrative_panel("Insufficient data for bootstrap analysis."),
                html.Div(),
            )

        data_bundle = {"bootstrap": df}
        fig, narrative = AnalyticsEngine.chart_bootstrap_ci_forecast(data_bundle)

        stats = {
            "Boroughs": len(df),
            "Avg SLA Risk": df.get("prob_sla_breach", [0]).mean() if "prob_sla_breach" in df else 0,
        }

        return (
            dmc.Stack([dcc.Graph(figure=fig, config={"displayModeBar": False})]),
            _render_narrative_panel(narrative),
            _render_statistics_panel(stats),
        )

    except Exception as e:
        logger.error(f"Phase F error: {e}", exc_info=True)
        return (
            dmc.Stack([dmc.Text(f"Error: {str(e)}", c="red")]),
            _render_narrative_panel(f"Error in Phase F analysis: {str(e)}"),
            html.Div(),
        )

def register_visualization_callbacks() -> None:
    """Register all 5 visualization callbacks (called from dash_app.py)."""
    # Callbacks are registered via @callback decorators above
    logger.info("Visualization callbacks registered (Phase B-F)")

