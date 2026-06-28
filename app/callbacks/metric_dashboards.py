"""Dash callbacks for Metric dashboard integration.

Connects Metric materialization pipeline to interactive Dash visualizations.
Enables real-time filtering, drill-down, and dimension selection.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Tuple

import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from socrata_toolkit.metric.registry import MetricRegistry

from socrata_toolkit.viz.chart_factory import ChartFactory

logger = logging.getLogger(__name__)


class MetricPDashboard:
    """Dashboard controller for Metric visualizations."""

    def __init__(self, registry: MetricRegistry, duckdb_manager):
        self.registry = registry
        self.db = duckdb_manager
        self.chart_factory = ChartFactory()

    def render_metric_overview(self) -> html.Div:
        """Render Metric overview page with key metrics."""

        return html.Div([
            html.H1('Metric Dashboard Overview', className='page-title'),

            # Metric Grid (4-column)
            html.Div(
                id='metric-grid',
                className='metric-grid',
                children=[]  # Populated by callback
            ),

            dcc.Store(id='selected-metric-store'),
        ])

    def render_metric_detail(self) -> html.Div:
        """Render detailed Metric view with forecast and anomalies."""

        return html.Div([
            html.H2(id='metric-title', className='page-title'),

            html.Div(
                className='metric-detail-grid',
                children=[
                    # Current status
                    html.Div(
                        id='metric-status',
                        className='metric-card',
                    ),
                    # Gauge chart
                    html.Div(
                        dcc.Graph(id='metric-gauge'),
                        className='chart-container'
                    ),
                ]
            ),

            html.Div(
                className='metric-detail-grid',
                children=[
                    # Time-series with forecast
                    html.Div(
                        dcc.Graph(id='metric-forecast-chart'),
                        className='chart-container-wide'
                    ),
                ]
            ),

            # Dimension breakdown
            html.Div(
                id='dimension-selector',
                className='control-panel'
            ),

            html.Div(
                dcc.Graph(id='metric-dimension-chart'),
                className='chart-container-wide'
            ),
        ])

    def get_metric_cards(self) -> List[html.Div]:
        """Generate Metric card components from registry."""

        cards = []
        for metric in self.registry.get_all_metrics()[:12]:  # First 12 Metrics
            card = html.Div(
                [
                    html.H3(metric.name),
                    html.Div(id=f'metric-value-{metric.metric_id}', className='metric-value'),
                    html.Div(id=f'metric-status-{metric.metric_id}', className='metric-status-badge'),
                ],
                className='metric-card',
                id=f'metric-card-{metric.metric_id}'
            )
            cards.append(card)

        return cards

    def register_callbacks(self, app):
        """Register Dash callbacks for interactivity."""

        @app.callback(
            Output('metric-grid', 'children'),
            Input('url', 'pathname')
        )
        def update_metric_grid(_):
            """Update Metric grid on page load."""
            return self.get_metric_cards()

        @app.callback(
            [Output('metric-gauge', 'figure'),
             Output('metric-forecast-chart', 'figure'),
             Output('metric-dimension-chart', 'figure')],
            Input('selected-metric-store', 'data')
        )
        def update_metric_charts(selected_metric_id):
            """Update all charts when Metric selection changes."""

            if not selected_metric_id:
                # Return empty figures
                return (go.Figure(), go.Figure(), go.Figure())

            try:
                # Fetch Metric data from analytics
                with self.db.get_connection() as conn:
                    # Gauge chart
                    result = conn.execute(f"""
                        SELECT current_value, target FROM analytics.metric_latest
                        WHERE metric_id = '{selected_metric_id}'
                    """).fetchall()

                    if not result:
                        return (go.Figure(), go.Figure(), go.Figure())

                    current_val, target = result[0]
                    metric = self.registry.get_metric(selected_metric_id)

                    # Create gauge
                    gauge_spec = self.chart_factory.create_gauge_chart(
                        selected_metric_id, current_val, target, metric.name
                    )

                    # Forecast chart
                    ts_data = conn.execute(f"""
                        SELECT period, current_value FROM analytics.metric_time_series
                        WHERE metric_id = '{selected_metric_id}' ORDER BY period
                    """).fetchall()

                    forecast_data = conn.execute(f"""
                        SELECT forecast_period, forecast_value, forecast_ci_lower, forecast_ci_upper
                        FROM analytics.metric_forecasts
                        WHERE metric_id = '{selected_metric_id}' ORDER BY forecast_period
                    """).fetchall()

                    periods = [str(p[0]) for p in ts_data] if ts_data else []
                    values = [p[1] for p in ts_data] if ts_data else []

                    forecast_periods = [str(p[0]) for p in forecast_data] if forecast_data else []
                    forecast_values = [p[1] for p in forecast_data] if forecast_data else []
                    ci_lower = [p[2] for p in forecast_data] if forecast_data else []
                    ci_upper = [p[3] for p in forecast_data] if forecast_data else []

                    forecast_spec = self.chart_factory.create_line_chart(
                        selected_metric_id, periods, values,
                        forecast_periods=forecast_periods,
                        forecast_values=forecast_values,
                        ci_lower=ci_lower,
                        ci_upper=ci_upper,
                        title=f'{metric.name} - Actual vs Forecast'
                    )

                    # Dimension breakdown chart (borough example)
                    dim_data = conn.execute(f"""
                        SELECT dimension_value, metric_value
                        FROM analytics.metric_dimensions
                        WHERE metric_id = '{selected_metric_id}' AND dimension_name = 'borough'
                        ORDER BY metric_value DESC
                    """).fetchall()

                    if dim_data:
                        dims = [str(d[0]) for d in dim_data]
                        dim_vals = [d[1] for d in dim_data]
                        dim_spec = self.chart_factory.create_bar_chart(
                            selected_metric_id, dims, dim_vals,
                            title=f'{metric.name} by Borough'
                        )
                    else:
                        dim_spec = ChartFactory.create_bar_chart(
                            selected_metric_id, [], [],
                            title='No dimension data'
                        )

                    return (gauge_spec.figure, forecast_spec.figure, dim_spec.figure)

            except Exception as e:
                logger.error(f"Chart update failed: {e}")
                return (go.Figure(), go.Figure(), go.Figure())


def create_metric_dashboard(registry: MetricRegistry, duckdb_manager) -> MetricPDashboard:
    """Factory for Metric dashboard."""
    return MetricPDashboard(registry, duckdb_manager)
