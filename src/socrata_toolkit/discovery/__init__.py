"""Discovery sub-package — schema registry, data dictionary, dataset search, and entity registry."""

from .registry import (
    REGISTRY,
    ColumnDef,
    EntityDef,
    KeyMeta,
    KeyRole,
    build_er_diagram,
)

__all__ = [
    "REGISTRY",
    "ColumnDef",
    "EntityDef",
    "KeyMeta",
    "KeyRole",
    "build_er_diagram",
]
