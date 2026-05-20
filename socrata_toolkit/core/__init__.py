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
from .config import get_default, load_local_config
from .db_helpers import build_fts_index_sql
from .duckdb_store import DuckDBManager, DuckDBRepository, get_bundle_dir
from .master_data import EntityMergeStrategy, MasterDataManager, MasterEntity
from .state import load_state, save_state
from .temporal import ChangePattern, ChangeSummary

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

# NYC datasets / dictionary helpers
try:
    from ..discovery.dictionary import generate_data_dictionary
    from ..discovery.nyc import DATASETS, list_available_datasets
except ImportError:
    generate_data_dictionary = None  # type: ignore
    DATASETS = {}
    list_available_datasets = lambda: []  # type: ignore

# SoQL builder (optional; used by query_builder tests)
from ..query_builder import (
    _quote_value,
    and_join,
    equals_clause,
    in_clause,
    like_clause,
    or_join,
)

try:
    from ..discovery.search import SoQLBuilder
except ImportError:
    SoQLBuilder = None  # type: ignore

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
    "get_default",
    "load_local_config",
    "build_fts_index_sql",
    "DuckDBManager",
    "DuckDBRepository",
    "get_bundle_dir",
    "MasterDataManager",
    "EntityMergeStrategy",
    "MasterEntity",
    "load_state",
    "save_state",
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
