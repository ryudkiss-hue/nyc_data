"""Pipeline pillar: CDC, deduplication, complaints, streaming, SCD."""

from __future__ import annotations

from ..cdc.compliance import ComplianceCheckResult
from ..cdc.engine import CDCEvent, CDCProcessor
from ..cdc.export import ExportFormat, ExportResult
from .cdc import detect_changes, detect_status_changes
from .complaints import *
from .dedupe import *
from .scd import SCDRecord, SCDType2Manager
from .soft_delete import *
from .streaming import *
from .sync import sync_dataset
from ..core.pipeline import run_from_rows

__all__ = [
    "sync_dataset",
    "run_from_rows",
]
