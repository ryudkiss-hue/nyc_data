"""Visualization pillar: charts, maps, dashboards."""

from __future__ import annotations

from .charts_extra import (
    data_completeness_chart,
    metric_status_pie_chart,
    plot_geospatial_compliance_map,
)
from .core import *
from .map import *
from .plotly import *

# Expose hidden analysis-module chart functions
try:
    from ..analysis import animated_scatter_chart, treemap_chart
except Exception:
    pass
