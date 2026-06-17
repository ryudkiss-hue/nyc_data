"""
KPI Registry Module — Unified definition & loading for all 51 KPIs.

Consolidates KPI definitions, metadata, and computation contracts into a single
source of truth. Supports time-series forecasting, multi-level thresholds,
dimension breakdowns, and visualization specifications.

Main Classes:
    - KPIDefinition: Complete KPI specification with all metadata
    - KPIRegistry: Singleton registry that loads all 51 KPIs from YAML
    - KPIResult: Dashboard contract with current value, trend, forecast, insights

Example:
    >>> from socrata_toolkit.kpi import KPIRegistry
    >>> registry = KPIRegistry.load()
    >>> kpi = registry.get_kpi("PRM-001")
    >>> print(kpi.name, kpi.target)
"""

from socrata_toolkit.kpi.models import (
    DimensionConfig,
    KPIDefinition,
    KPIResult,
    KPIValue,
    ThresholdLevel,
    TimeSeriesMetadata,
    Trend,
)
from socrata_toolkit.kpi.registry import KPIRegistry

__all__ = [
    "KPIRegistry",
    "KPIDefinition",
    "KPIResult",
    "KPIValue",
    "Trend",
    "ThresholdLevel",
    "TimeSeriesMetadata",
    "DimensionConfig",
]

__version__ = "0.1.0"
