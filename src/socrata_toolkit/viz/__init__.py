"""Visualization pillar: charts, maps, dashboards."""

from __future__ import annotations

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

# Deferred imports to avoid circular dependency issues
def __getattr__(name: str):
    """Lazy-load functions from charts_extra and analysis modules."""
    if name in ("data_completeness_chart", "metric_status_pie_chart", "plot_geospatial_compliance_map"):
        from .charts_extra import (
            data_completeness_chart,
            metric_status_pie_chart,
            plot_geospatial_compliance_map,
        )
        return locals()[name]
    elif name in ("animated_scatter_chart", "treemap_chart"):
        try:
            from ..analysis import animated_scatter_chart, treemap_chart
            return locals()[name]
        except Exception:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
