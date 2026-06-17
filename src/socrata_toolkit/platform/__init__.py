"""
Multi-platform analytics layer.

Unified interface for querying NYC datasets via:
- PRIMARY: MotherDuck (cloud DuckDB) — recommended for team analytics
- FALLBACK: Local DuckDB — always available, no API needed
"""

from .connection import (
    ConnectionManager,
    close_connection,
    get_connection,
    get_platform_name,
    is_motherduck,
    query,
)

__all__ = [
    "get_connection",
    "query",
    "get_platform_name",
    "is_motherduck",
    "close_connection",
    "ConnectionManager",
]
