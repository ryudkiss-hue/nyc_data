"""Generalized materialization factory for analytics, validation, and monitoring marts.

Provides:
- MartBuilder: Base class for all mart builders
- BuilderRegistry: Plugin registry for builder discovery
- MaterializationFactory: Orchestrates mart materialization
- MartLineage: Tracks data flow (datasets → marts → dashboards)
- MartQuality: Monitors freshness, completeness, schema stability
"""

from .builder import MartBuilder
from .registry import BuilderRegistry
from .factory import MaterializationFactory
from .lineage import MartLineage
from .quality import MartQuality

__all__ = [
    "MartBuilder",
    "BuilderRegistry",
    "MaterializationFactory",
    "MartLineage",
    "MartQuality",
]
