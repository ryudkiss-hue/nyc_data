"""Pipeline pillar: CDC, deduplication, complaints, streaming, SCD."""

from __future__ import annotations

from ..cdc.compliance import ComplianceCheckResult  # noqa: F401
from ..cdc.engine import CDCEvent, CDCProcessor  # noqa: F401
from ..cdc.export import ExportFormat, ExportResult  # noqa: F401
from ..core.pipeline import run_from_rows  # noqa: F401
from .cdc import detect_changes, detect_status_changes  # noqa: F401
from .complaints import *  # noqa: F401
from .dedupe import *  # noqa: F401
from .scd import SCDRecord, SCDType2Manager  # noqa: F401
from .soft_delete import *  # noqa: F401
from .streaming import *  # noqa: F401
from .sync import sync_dataset  # noqa: F401

__all__ = [
    "sync_dataset",
    "run_from_rows",
]
