"""Analytics Integration Callbacks: Phase B–F (real warehouse data).

Each callback reads a precomputed app_queries.v_phase_* view (built by
pipeline/analytics/build_phase_analytics.py) and renders it via app.callbacks.
phase_render. This is the single, real analytics path — the previous version
recomputed from a separate live-fetch adapter behind a filter gate that always
failed (it checked for a "borough" key the global store doesn't use).
"""
from __future__ import annotations

import logging
from typing import Any

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc

from app.callbacks.phase_render import (
    render_anomalies,
    render_bootstrap_ci,
    render_decomposition,
    render_distribution,
    render_morans_i,
)
from app.services.motherduck_service import (
    fetch_phase_b_results,
    fetch_phase_c_results,
    fetch_phase_d_results,
    fetch_phase_e_decomposition,
    fetch_phase_f_bootstrap_ci,
)

logger = logging.getLogger(__name__)


def _graph(fig: go.Figure) -> dcc.Graph:
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def _panel(title: str, fig: go.Figure) -> dmc.Stack:
    return dmc.Stack([
        dmc.Paper(withBorder=True, p="md", radius="lg", shadow="sm",
                  children=[dmc.Text(title, fw=700, size="lg"), _graph(fig)])
    ])


# ---- Phase C: Distribution ----------------------------------------------------
@callback(
    Output("distribution-chart-container", "children"),
    Output("distribution-narrative", "children"),
    Input("store-global-filters", "data"),
    Input("distribution-column-limit", "value"),
    prevent_initial_call=True,
)
def update_distribution_classification(filters: dict, limit: int = 8) -> tuple[Any, str]:
    try:
        df = fetch_phase_c_results(filters or {})
        fig, narrative = render_distribution(df)
        return _panel("Distribution Classification", fig), narrative
    except Exception as e:
        logger.error(f"Distribution classification error: {e}", exc_info=True)
        return dmc.Stack([dmc.Text(f"Error: {e}", c="red")]), f"Error: {e}"


# ---- Phase D: Anomalies -------------------------------------------------------
@callback(
    Output("anomaly-detection-chart", "children"),
    Output("anomaly-narrative", "children"),
    Output("anomaly-count-badge", "children"),
    Input("store-global-filters", "data"),
    Input("anomaly-detection-toggle", "checked"),
    prevent_initial_call=True,
)
def update_anomaly_detection(filters: dict, enabled: bool = True) -> tuple[Any, str, str]:
    try:
        df = fetch_phase_d_results(filters or {})
        fig, narrative = render_anomalies(df)
        count = "0" if df is None else str(len(df))
        return _panel("Time-Series Anomalies", fig), narrative, count
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}", exc_info=True)
        return dmc.Stack([dmc.Text(f"Error: {e}", c="red")]), f"Error: {e}", "—"


# ---- Phase E: Decomposition ---------------------------------------------------
@callback(
    Output("decomposition-chart-container", "children"),
    Output("decomposition-narrative", "children"),
    Input("store-global-filters", "data"),
    Input("decomposition-date-col", "value"),
    Input("decomposition-value-col", "value"),
    prevent_initial_call=True,
)
def update_seasonal_decomposition(filters: dict, date_col: str = None,
                                  value_col: str = None) -> tuple[Any, str]:
    try:
        df = fetch_phase_e_decomposition(filters or {})
        fig, narrative = render_decomposition(df)
        return _panel("Trend Decomposition", fig), narrative
    except Exception as e:
        logger.error(f"Decomposition error: {e}", exc_info=True)
        return dmc.Stack([dmc.Text(f"Error: {e}", c="red")]), f"Error: {e}"


# ---- Phase F: Bootstrap CI ----------------------------------------------------
@callback(
    Output("metric-bootstrap-figures", "children"),
    Output("metric-bootstrap-summary", "children"),
    Input("store-global-filters", "data"),
    Input("metric-refresh-interval", "n_intervals"),
    prevent_initial_call=True,
)
def update_bootstrap_ci_metrics(filters: dict, n_intervals: int = 0) -> tuple[Any, str]:
    try:
        df = fetch_phase_f_bootstrap_ci(filters or {})
        fig, narrative = render_bootstrap_ci(df)
        return _panel("Bootstrap Confidence Intervals", fig), narrative
    except Exception as e:
        logger.error(f"Bootstrap CI error: {e}", exc_info=True)
        return dmc.Stack([dmc.Text(f"Error: {e}", c="red")]), f"Error: {e}"


# ---- Phase B: Moran's I -------------------------------------------------------
@callback(
    Output("morans-i-gauge", "figure"),
    Output("morans-i-narrative", "children"),
    Input("store-global-filters", "data"),
    Input("morans-i-column-select", "value"),
    prevent_initial_call=True,
)
def update_morans_i(filters: dict, column: str = None) -> tuple[go.Figure, str]:
    try:
        df = fetch_phase_b_results(filters or {})
        fig, narrative = render_morans_i(df)
        return fig, narrative
    except Exception as e:
        logger.error(f"Moran's I error: {e}", exc_info=True)
        return go.Figure(), f"Error: {e}"


# ---- Universal refresh passthrough -------------------------------------------
@callback(
    Output("analytics-refresh-trigger", "data"),
    Input("store-global-filters", "data"),
    prevent_initial_call=True,
)
def trigger_all_updates(filters: dict) -> dict:
    return filters or {}
