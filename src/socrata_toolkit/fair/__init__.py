"""FAIR metadata catalog for Socrata datasets.

Implements the FAIR Guiding Principles (Wilkinson et al. 2016) for dataset
metadata: Findable, Accessible, Interoperable, Reusable. Provides a metadata
model, a transparent scoring rubric, a catalog with DCAT JSON-LD export, and
a bridge from the project's dataset registry.
"""

from __future__ import annotations

from .catalog import FairCatalog
from .model import FairDataset, FairnessScore, SchemaField
from .registry_bridge import from_registry_yaml
from .scoring import score_fairness

__all__ = [
    "FairDataset",
    "SchemaField",
    "FairnessScore",
    "FairCatalog",
    "score_fairness",
    "from_registry_yaml",
]
