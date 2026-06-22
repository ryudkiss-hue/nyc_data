"""Core pillar: API client, config, master data, schema registry, and shared constants."""

from __future__ import annotations

# Shared column names and UI constants (used across analysis/engineering)
COL_LAT = "latitude"
COL_LON = "longitude"
COL_BORO = "borough"
COL_ID = "id"
COL_AT_ID = "@id"
COL_COMPLAINT = "complaint_date"
COL_REPAIR = "repair_date"
COL_CREATED = "created_date"
COL_CLOSED = "closed_date"
DTYPE_NUM = "number"
COLOR_GREEN = "green"
COLOR_YELLOW = "yellow"
COLOR_RED = "red"
STATUS_TODO = "todo"
STATUS_PROGRESS = "in_progress"
STATUS_DONE = "done"
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"
PRIORITY_INFO = "info"
LBL_SYSTEM = "system"
MODEL_DEFAULT = "gpt-3.5-turbo"

from .api import create_app
from .client import SocrataClient, SocrataConfig

# Config imports handled separately per module
from .db_helpers import build_fts_index_sql, ensure_fts_index
from .duckdb_store import DuckDBManager, DuckDBRepository, get_bundle_dir
from .memory_profiler import MemoryProfiler, get_global_profiler, profile_module_import
from .models import DatasetMetadata, SearchResult
from .profiles import (
    ProfilePaths,
    active_profile_name,
    ensure_profile_exists,
    list_profiles,
    profile_paths,
)


class DuckDBExporter:
    """High-performance DuckDB exporter."""

    def __init__(self, db_path: str | None = None):
        self.manager = DuckDBManager(db_path)

    def __enter__(self) -> DuckDBExporter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.manager.close()

def search_nyc_datasets(query: str, domain: str = "data.cityofnewyork.us", limit: int = 10):
    """Search NYC Open Data catalog and return results as a DataFrame."""
    from dataclasses import asdict

    import pandas as pd

    client = SocrataClient()
    results = client.search(query=query, domain=domain, limit=limit)
    return pd.DataFrame([asdict(r) for r in results])
# Schema registry lives under discovery but tests import from core
from ..discovery.schema import (
    BackwardCompatibilityChecker,
    BreakingChangeAlert,
    ChangeType,
    ColumnSchema,
    DatasetSchema,
    SchemaChange,
    SchemaRegistry,
    SchemaValidator,
)
from .master_data import EntityMergeStrategy, MasterDataManager, MasterEntity
from .state import load_state, save_state
from .temporal import ChangePattern, ChangeSummary

# NYC datasets / dictionary helpers
try:
    from ..discovery.dictionary import generate_data_dictionary
    from ..discovery.nyc import DATASETS, list_available_datasets
except ImportError:
    generate_data_dictionary = None  # type: ignore
    DATASETS = {}
    def list_available_datasets():
        return []  # type: ignore

# SoQL builder (optional; used by query_builder tests)
from ..query_builder import (
    _quote_value,
    and_join,
    equals_clause,
    in_clause,
    like_clause,
    or_join,
)
from .soql_builder import SoQLBuilder

__all__ = [
    "COL_LAT",
    "COL_LON",
    "COL_BORO",
    "COL_ID",
    "COL_COMPLAINT",
    "COL_REPAIR",
    "COL_CREATED",
    "COL_CLOSED",
    "COLOR_GREEN",
    "COLOR_YELLOW",
    "COLOR_RED",
    "SocrataClient",
    "SocrataConfig",
    "create_app",
    "build_fts_index_sql",
    "DuckDBManager",
    "DuckDBRepository",
    "get_bundle_dir",
    "MasterDataManager",
    "EntityMergeStrategy",
    "MasterEntity",
    "load_state",
    "save_state",
    "ProfilePaths",
    "active_profile_name",
    "profile_paths",
    "ensure_profile_exists",
    "list_profiles",
    "ChangePattern",
    "ChangeSummary",
    "SchemaRegistry",
    "SchemaValidator",
    "BackwardCompatibilityChecker",
    "BreakingChangeAlert",
    "ChangeType",
    "ColumnSchema",
    "DatasetSchema",
    "SchemaChange",
    "generate_data_dictionary",
    "DATASETS",
    "list_available_datasets",
    "SoQLBuilder",
    "_quote_value",
    "and_join",
    "equals_clause",
    "in_clause",
    "like_clause",
    "or_join",
]
