"""
socrata_toolkit/viz/charts.py - Proxy for visualization functions.
Exports functions from analysis.py to maintain the Pillar Architecture and block imports.
"""

from ..analysis import (
    animated_scatter_chart,
    bar_chart,
    correlation_heatmap,
    export_plotly_figure,
    gauge_chart,
    generate_semantic_network_map,
    histogram,
    hotspot_density_mapbox,
    material_borough_subplots,
    material_breakdown_pie_chart,
    operations_gantt_chart,
    plot_ada_compliance_map,
    plot_sidewalk_anatomy,
    quality_radar_chart,
    sunburst_chart,
    time_series_chart,
    treemap_chart,
    triage_funnel_chart,
    violin_plot,
)

__all__ = [
    "animated_scatter_chart",
    "bar_chart",
    "correlation_heatmap",
    "export_plotly_figure",
    "gauge_chart",
    "generate_semantic_network_map",
    "histogram",
    "hotspot_density_mapbox",
    "material_borough_subplots",
    "material_breakdown_pie_chart",
    "operations_gantt_chart",
    "plot_ada_compliance_map",
    "plot_sidewalk_anatomy",
    "quality_radar_chart",
    "sunburst_chart",
    "time_series_chart",
    "treemap_chart",
    "triage_funnel_chart",
    "violin_plot",
]
