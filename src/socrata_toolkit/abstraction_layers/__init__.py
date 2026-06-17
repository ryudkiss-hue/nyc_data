"""Abstraction layers for config-driven dataset integration.

These layers provide type-safe, testable interfaces for:
- ChartFactory: Universal Plotly chart creation
- CallbackFactory: Auto-generated Dash callbacks
- KPIEngine: KPI computation with validation
- DatasetLoader: Data fetching with schema validation
- SchemaRegistry: Central schema validation layer

Usage:
    from socrata_toolkit.abstraction_layers import (
        ChartFactory,
        KPIEngine,
        DatasetLoader,
        SchemaRegistry,
    )

    # Create a chart from a specification
    factory = ChartFactory()
    fig = factory.create(
        chart_type="vertical_bar",
        data=df,
        iv_column="borough",
        dv_column="violation_count",
    )

    # Compute a KPI with automatic validation
    engine = KPIEngine(registry)
    result = engine.compute("inspection", "inspections_scheduled_week")

    # Load data with schema validation
    loader = DatasetLoader(registry)
    df = loader.load("inspection", filters={"borough": "MANHATTAN"})
"""

from __future__ import annotations

from .chart_factory import ChartFactory, ChartSpec
from .callback_factory import CallbackFactory
from .kpi_engine import KPIEngine, KPIResult
from .dataset_loader import DatasetLoader, DatasetResult
from .schema_registry import SchemaRegistry, ValidationResult

__all__ = [
    "ChartFactory",
    "ChartSpec",
    "CallbackFactory",
    "KPIEngine",
    "KPIResult",
    "DatasetLoader",
    "DatasetResult",
    "SchemaRegistry",
    "ValidationResult",
]
