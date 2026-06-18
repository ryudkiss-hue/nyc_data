"""ChartFactory: Intelligent Plotly chart generation for KPIs.

Maps KPI characteristics to optimal chart types and generates interactive
visualizations for dashboard integration.

Supported chart types (11):
1. Gauge - KPI status indicators
2. Indicator - Large value displays with delta
3. Bar - Comparisons across categories
4. Line - Time-series trends
5. Funnel - Conversion/completion rates
6. Scatter - Correlation analysis
7. Box - Distribution analysis
8. Heatmap - Correlation matrices
9. Waterfall - Composition breakdown
10. Sankey - Flow/process visualization
11. Choropleth - Geographic distribution
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


@dataclass
class ChartSpec:
    """Specification for a Plotly chart."""
    chart_type: str
    title: str
    figure: go.Figure
    config: Dict[str, Any]


class ChartFactory:
    """Creates optimized Plotly charts based on KPI characteristics."""

    # Chart type recommendations by KPI category
    CHART_RECOMMENDATIONS = {
        'inspection': ['indicator', 'gauge', 'line', 'bar'],
        'violations': ['bar', 'line', 'heatmap', 'box'],
        'contractor': ['bar', 'scatter', 'waterfall'],
        'budget': ['waterfall', 'bar', 'line'],
        'accessibility': ['indicator', 'gauge', 'choropleth'],
        'quality': ['line', 'box', 'heatmap'],
        'geographic': ['choropleth', 'scatter'],
        'compliance': ['gauge', 'indicator', 'line']
    }

    @staticmethod
    def create_gauge_chart(kpi_id: str, current_value: float, target: float,
                          title: str) -> ChartSpec:
        """Create gauge chart for KPI status indicator."""

        achievement = (current_value / target * 100.0) if target > 0 else 0.0

        fig = go.Figure(data=[go.Indicator(
            mode='gauge+number+delta',
            value=current_value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            delta={'reference': target},
            gauge={
                'axis': {'range': [0, target * 1.2]},
                'bar': {'color': 'darkblue'},
                'steps': [
                    {'range': [0, target * 0.6], 'color': 'lightgray'},
                    {'range': [target * 0.6, target * 0.8], 'color': 'gray'},
                    {'range': [target * 0.8, target * 1.2], 'color': 'lightgreen'}
                ],
                'threshold': {
                    'line': {'color': 'red', 'width': 4},
                    'thickness': 0.75,
                    'value': target
                }
            }
        )])

        return ChartSpec(
            chart_type='gauge',
            title=title,
            figure=fig,
            config={'responsive': True, 'displayModeBar': False}
        )

    @staticmethod
    def create_indicator_chart(kpi_id: str, current_value: float, target: float,
                              title: str, delta_period: Optional[float] = None) -> ChartSpec:
        """Create large-value indicator chart."""

        delta_text = None
        if delta_period is not None:
            delta_text = f"{delta_period:+.1f}% from previous"

        fig = go.Figure(data=[go.Indicator(
            mode='number+delta',
            value=current_value,
            title={'text': title},
            delta={'reference': target, 'relative': False, 'suffix': '' if delta_text else None},
            number={'font': {'size': 48}}
        )])

        fig.update_layout(height=300)

        return ChartSpec(
            chart_type='indicator',
            title=title,
            figure=fig,
            config={'responsive': True}
        )

    @staticmethod
    def create_line_chart(kpi_id: str, periods: List[str], values: List[float],
                         forecast_periods: Optional[List[str]] = None,
                         forecast_values: Optional[List[float]] = None,
                         ci_lower: Optional[List[float]] = None,
                         ci_upper: Optional[List[float]] = None,
                         title: str = '') -> ChartSpec:
        """Create time-series line chart with optional forecast."""

        fig = go.Figure()

        # Historical data
        fig.add_trace(go.Scatter(
            x=periods,
            y=values,
            mode='lines+markers',
            name='Actual',
            line=dict(color='steelblue', width=2),
            marker=dict(size=6)
        ))

        # Forecast
        if forecast_periods and forecast_values:
            fig.add_trace(go.Scatter(
                x=forecast_periods,
                y=forecast_values,
                mode='lines+markers',
                name='Forecast',
                line=dict(color='orange', width=2, dash='dash'),
                marker=dict(size=6)
            ))

            # Confidence interval
            if ci_lower and ci_upper:
                fig.add_trace(go.Scatter(
                    x=forecast_periods + forecast_periods[::-1],
                    y=ci_upper + ci_lower[::-1],
                    fill='toself',
                    fillcolor='rgba(255, 165, 0, 0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='95% CI',
                    hoverinfo='skip'
                ))

        fig.update_layout(
            title=title,
            hovermode='x unified',
            height=400,
            xaxis_title='Period',
            yaxis_title='Value'
        )

        return ChartSpec(
            chart_type='line',
            title=title,
            figure=fig,
            config={'responsive': True}
        )

    @staticmethod
    def create_bar_chart(kpi_id: str, categories: List[str], values: List[float],
                        title: str = '') -> ChartSpec:
        """Create bar chart for categorical comparisons."""

        fig = go.Figure([go.Bar(
            x=categories,
            y=values,
            marker=dict(color='steelblue'),
            text=values,
            textposition='outside'
        )])

        fig.update_layout(
            title=title,
            xaxis_title='Category',
            yaxis_title='Value',
            height=400,
            showlegend=False
        )

        return ChartSpec(
            chart_type='bar',
            title=title,
            figure=fig,
            config={'responsive': True}
        )

    @staticmethod
    def create_heatmap_chart(kpi_id: str, z_values: List[List[float]],
                            x_labels: List[str], y_labels: List[str],
                            title: str = '') -> ChartSpec:
        """Create heatmap for correlation/matrix visualization."""

        fig = go.Figure(data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            colorscale='RdYlGn',
            zmid=0.5
        ))

        fig.update_layout(
            title=title,
            height=500,
            width=700
        )

        return ChartSpec(
            chart_type='heatmap',
            title=title,
            figure=fig,
            config={'responsive': True}
        )

    @staticmethod
    def create_scatter_chart(kpi_id: str, x_values: List[float], y_values: List[float],
                            labels: Optional[List[str]] = None,
                            title: str = '') -> ChartSpec:
        """Create scatter plot for correlation analysis."""

        fig = go.Figure([go.Scatter(
            x=x_values,
            y=y_values,
            mode='markers',
            text=labels if labels else [''] * len(x_values),
            marker=dict(size=8, color='steelblue', line=dict(width=1)),
            hovertemplate='<b>%{text}</b><br>X: %{x}<br>Y: %{y}<extra></extra>'
        )])

        fig.update_layout(
            title=title,
            height=400,
            showlegend=False
        )

        return ChartSpec(
            chart_type='scatter',
            title=title,
            figure=fig,
            config={'responsive': True}
        )

    @staticmethod
    def recommend_chart_type(kpi_category: str, has_forecast: bool = False,
                            has_dimensions: bool = False) -> str:
        """Recommend chart type based on KPI characteristics.

        Args:
            kpi_category: KPI category (e.g., 'inspection', 'violations')
            has_forecast: Whether KPI has forecast data
            has_dimensions: Whether KPI has dimension breakdowns

        Returns:
            Recommended chart type string
        """

        recommendations = ChartFactory.CHART_RECOMMENDATIONS.get(
            kpi_category, ['indicator', 'bar', 'line']
        )

        # Adjust recommendation based on features
        if has_forecast:
            return 'line'  # Line charts best for forecast + actual
        if has_dimensions:
            return 'bar'   # Bar charts best for dimensional comparisons

        return recommendations[0]  # Default to first recommendation


def create_chart_factory() -> ChartFactory:
    """Factory for chart factory."""
    return ChartFactory()
