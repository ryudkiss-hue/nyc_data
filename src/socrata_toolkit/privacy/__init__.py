"""
socrata_toolkit.privacy - multi-signal PII detection, masking, and
DAMA-DMBOK2 data-quality scoring.

This is a standalone package; it does not modify or depend on the legacy PII
helper in ``api/governance.py``.
"""

from __future__ import annotations

from .dmbok import DimensionScore, DmbokReport, score_dataframe
from .masking import (
    bucket_numeric,
    hash_token,
    partial_mask,
    recommend_strategy,
    redact,
    truncate_geo,
)
from .pii_scanner import PiiSignal, luhn_check, scan_dataframe

__all__ = [
    # scanner
    "PiiSignal",
    "scan_dataframe",
    "luhn_check",
    # masking
    "redact",
    "hash_token",
    "bucket_numeric",
    "truncate_geo",
    "partial_mask",
    "recommend_strategy",
    # dmbok
    "DimensionScore",
    "DmbokReport",
    "score_dataframe",
]
