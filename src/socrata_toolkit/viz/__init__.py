"""Visualization pillar: charts, maps, dashboards."""

from __future__ import annotations

from .charts_extra import (
    data_completeness_chart,
    metric_status_pie_chart,
    plot_geospatial_compliance_map,
)
from .core import *
from .map import *
from .plotly import (
    borough_bar_chart,
    contract_gantt,
    correlation_heatmap,
    hypothesis_test_results,
    inspector_performance_boxplot,
    kpi_gauge,
    priority_heatmap,
    save_chart,
    status_donut,
    trend_line,
    waterfall_chart,
)

# Expose hidden analysis-module chart functions
try:
    from ..analysis import animated_scatter_chart, treemap_chart
except Exception:
    pass
