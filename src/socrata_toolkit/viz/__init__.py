"""Visualization pillar: charts, maps, dashboards."""

from __future__ import annotations

# Multi-dimensional + crossfilter charts
from .advanced_multidim import (
    bubble_chart,
    clustermap,
    crossfilter_layout,
    inspection_funnel,
    parallel_coordinates,
    radar_chart,
    sankey_flow,
    scatter_plot_matrix,
)

# Chart Finder — intelligent recommendation engine
from .chart_finder import ChartFinder, ChartRecommendation
from .core import *

# D3.js / d3blocks components (return HTML strings)
from .d3_components import (
    chord_diagram,
    df_to_hierarchy,
    force_network,
    hex_binmap,
    stream_graph,
    treemap_d3,
)
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

# Statistical visualization layer
from .statistical_viz import (
    bayesian_posterior_strip,
    changepoint_overlay,
    cusum_control_chart,
    hdi_violin,
    moran_scatter_plot,
    ridge_plot,
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
