"""Dash callbacks for KPI dashboard integration.

Connects KPI materialization pipeline to interactive Dash visualizations.
Enables real-time filtering, drill-down, and dimension selection.
"""

from typing import Dict, List, Any, Tuple
import logging
from datetime import date
from dash import Input, Output, State, dcc, html, callback
import plotly.graph_objects as go

from socrata_toolkit.kpi.registry import KPIRegistry
from socrata_toolkit.viz.chart_factory import ChartFactory

logger = logging.getLogger(__name__)


class KPIPDashboard:
    """Dashboard controller for KPI visualizations."""

    def __init__(self, registry: KPIRegistry, duckdb_manager):
        self.registry = registry
        self.db = duckdb_manager
        self.chart_factory = ChartFactory()

    def render_kpi_overview(self) -> html.Div:
        """Render KPI overview page with key metrics."""

        return html.Div([
            html.H1('KPI Dashboard Overview', className='page-title'),

            # KPI Grid (4-column)
            html.Div(
                id='kpi-grid',
                className='kpi-grid',
                children=[]  # Populated by callback
            ),

            dcc.Store(id='selected-kpi-store'),
        ])

    def render_kpi_detail(self) -> html.Div:
        """Render detailed KPI view with forecast and anomalies."""

        return html.Div([
            html.H2(id='kpi-title', className='page-title'),

            html.Div(
                className='kpi-detail-grid',
                children=[
                    # Current status
                    html.Div(
                        id='kpi-status',
                        className='kpi-card',
                    ),
                    # Gauge chart
                    html.Div(
                        dcc.Graph(id='kpi-gauge'),
                        className='chart-container'
                    ),
                ]
            ),

            html.Div(
                className='kpi-detail-grid',
                children=[
                    # Time-series with forecast
                    html.Div(
                        dcc.Graph(id='kpi-forecast-chart'),
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
                dcc.Graph(id='kpi-dimension-chart'),
                className='chart-container-wide'
            ),
        ])

    def get_kpi_cards(self) -> List[html.Div]:
        """Generate KPI card components from registry."""

        cards = []
        for kpi in self.registry.get_all_kpis()[:12]:  # First 12 KPIs
            card = html.Div(
                [
                    html.H3(kpi.name),
                    html.Div(id=f'kpi-value-{kpi.kpi_id}', className='kpi-value'),
                    html.Div(id=f'kpi-status-{kpi.kpi_id}', className='kpi-status-badge'),
                ],
                className='kpi-card',
                id=f'kpi-card-{kpi.kpi_id}'
            )
            cards.append(card)

        return cards

    def register_callbacks(self, app):
        """Register Dash callbacks for interactivity."""

        @app.callback(
            Output('kpi-grid', 'children'),
            Input('url', 'pathname')
        )
        def update_kpi_grid(_):
            """Update KPI grid on page load."""
            return self.get_kpi_cards()

        @app.callback(
            [Output('kpi-gauge', 'figure'),
             Output('kpi-forecast-chart', 'figure'),
             Output('kpi-dimension-chart', 'figure')],
            Input('selected-kpi-store', 'data')
        )
        def update_kpi_charts(selected_kpi_id):
            """Update all charts when KPI selection changes."""

            if not selected_kpi_id:
                # Return empty figures
                return (go.Figure(), go.Figure(), go.Figure())

            try:
                # Fetch KPI data from analytics
                with self.db.get_connection() as conn:
                    # Gauge chart
                    result = conn.execute(f"""
                        SELECT current_value, target FROM analytics.kpi_latest
                        WHERE kpi_id = '{selected_kpi_id}'
                    """).fetchall()

                    if not result:
                        return (go.Figure(), go.Figure(), go.Figure())

                    current_val, target = result[0]
                    kpi = self.registry.get_kpi(selected_kpi_id)

                    # Create gauge
                    gauge_spec = self.chart_factory.create_gauge_chart(
                        selected_kpi_id, current_val, target, kpi.name
                    )

                    # Forecast chart
                    ts_data = conn.execute(f"""
                        SELECT period, current_value FROM analytics.kpi_time_series
                        WHERE kpi_id = '{selected_kpi_id}' ORDER BY period
                    """).fetchall()

                    forecast_data = conn.execute(f"""
                        SELECT forecast_period, forecast_value, forecast_ci_lower, forecast_ci_upper
                        FROM analytics.kpi_forecasts
                        WHERE kpi_id = '{selected_kpi_id}' ORDER BY forecast_period
                    """).fetchall()

                    periods = [str(p[0]) for p in ts_data] if ts_data else []
                    values = [p[1] for p in ts_data] if ts_data else []

                    forecast_periods = [str(p[0]) for p in forecast_data] if forecast_data else []
                    forecast_values = [p[1] for p in forecast_data] if forecast_data else []
                    ci_lower = [p[2] for p in forecast_data] if forecast_data else []
                    ci_upper = [p[3] for p in forecast_data] if forecast_data else []

                    forecast_spec = self.chart_factory.create_line_chart(
                        selected_kpi_id, periods, values,
                        forecast_periods=forecast_periods,
                        forecast_values=forecast_values,
                        ci_lower=ci_lower,
                        ci_upper=ci_upper,
                        title=f'{kpi.name} - Actual vs Forecast'
                    )

                    # Dimension breakdown chart (borough example)
                    dim_data = conn.execute(f"""
                        SELECT dimension_value, metric_value
                        FROM analytics.kpi_dimensions
                        WHERE kpi_id = '{selected_kpi_id}' AND dimension_name = 'borough'
                        ORDER BY metric_value DESC
                    """).fetchall()

                    if dim_data:
                        dims = [str(d[0]) for d in dim_data]
                        dim_vals = [d[1] for d in dim_data]
                        dim_spec = self.chart_factory.create_bar_chart(
                            selected_kpi_id, dims, dim_vals,
                            title=f'{kpi.name} by Borough'
                        )
                    else:
                        dim_spec = ChartFactory.create_bar_chart(
                            selected_kpi_id, [], [],
                            title='No dimension data'
                        )

                    return (gauge_spec.figure, forecast_spec.figure, dim_spec.figure)

            except Exception as e:
                logger.error(f"Chart update failed: {e}")
                return (go.Figure(), go.Figure(), go.Figure())


def create_kpi_dashboard(registry: KPIRegistry, duckdb_manager) -> KPIPDashboard:
    """Factory for KPI dashboard."""
    return KPIPDashboard(registry, duckdb_manager)
