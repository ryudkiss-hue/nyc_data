"""Dash page registration helpers."""

from __future__ import annotations

import os


def _flag(name: str) -> bool:
    return os.getenv(name, "").lower() in ("1", "true", "yes")


def legacy_pages_enabled() -> bool:
    """Enterprise / debug pages (AI, governance, pipeline, etc.)."""
    return _flag("NYC_DOT_DEBUG") or _flag("NYC_DOT_ENTERPRISE")


def analyst_pages_only() -> bool:
    return not legacy_pages_enabled()
