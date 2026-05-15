from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import sys
from collections.abc import Callable, Generator, Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ── Logging & Exceptions ──────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


class SocrataToolkitError(Exception):
    """Base exception for the toolkit."""


def get_logger():
    """Get the standard toolkit logger."""
    return logger


# ── Constants ─────────────────────────────────────────────────────────────────

CATALOG_URL = "https://api.us.socrata.com/api/catalog/v1"
EXT_JSON = ".json"
EXT_GEOJSON = ".geojson"
UTF8 = "utf-8"
LANG_EN = "english"
HDR_TOKEN = "X-App-Token"
ENV_TOKEN = "SOCRATA_APP_TOKEN"
COMPRESSION_SNAPPY = "snappy"
ENGINE_XL = "openpyxl"
XL_FREEZE = "A2"
DEFAULT_DOMAIN = "data.cityofnewyork.us"

# Column names
COL_LAT = "latitude"
COL_LON = "longitude"
COL_BORO = "borough"
COL_ID = "id"
COL_AT_ID = "@id"
COL_COMPLAINT = "complaint_date"
COL_REPAIR = "repair_date"
COL_CREATED = "created_date"
COL_CLOSED = "closed_date"

# Types & Colors
DTYPE_NUM = "number"
COLOR_GREEN = "green"
COLOR_YELLOW = "yellow"
COLOR_RED = "red"

# Operational Status
STATUS_TODO = "todo"
STATUS_PROGRESS = "in_progress"
STATUS_DONE = "done"

# Priorities
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"
PRIORITY_INFO = "info"

# Labels
LBL_SYSTEM = "system"

# Models
MODEL_DEFAULT = "gpt-3.5-turbo"

# ── Models ───────────────────────────────────────────────────────────────────


@dataclass
class SearchResult:
    """Represents a dataset search result from the Socrata catalog."""

    name: str
    description: str
    domain: str
    fourfour: str
    page_views_last_month: int | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class DatasetMetadata:
    """Represents full metadata for a Socrata dataset."""

    domain: str
    fourfour: str
    name: str
    description: str
    row_count: int | None
    license: str | None
    columns: list[dict[str, Any]]

    @property
    def is_geo(self) -> bool:
        """Returns True if the dataset contains geospatial columns."""
        geo_types = {"point", "polygon", "line", "multipolygon", "location"}
        for c in self.columns:
            ctype = str(c.get("dataTypeName", "")).lower()
            if ctype in geo_types or "location" in ctype:
                return True
        return False

    def summary(self) -> dict[str, Any]:
        """Returns a summarized dictionary of metadata."""
        return {
            "domain": self.domain,
            "fourfour": self.fourfour,
            "name": self.name,
            "description": self.description,
            "row_count": self.row_count,
            "license": self.license,
            "is_geo": self.is_geo,
        }

    def column_dict(self) -> list[dict[str, Any]]:
        """Returns a list of column definitions."""
        return [
            {
                "name": c.get("name"),
                "fieldName": c.get("fieldName"),
                "dataTypeName": c.get("dataTypeName"),
                "description": c.get("description"),
                "position": c.get("position"),
            }
            for c in self.columns
        ]


# ── Configuration ─────────────────────────────────────────────────────────────


@dataclass
class SocrataConfig:
    """Configuration for the Socrata client."""

    app_token: str | None = None
    timeout: int = 30
    page_size: int = 1000


def load_local_config(path: str | None = None) -> dict[str, Any]:
    """Load configuration from local JSON files."""
    candidates = (
        [Path(path)]
        if path
        else [
            Path.cwd() / "socrata_toolkit.core.config.json",
            Path.home() / ".socrata_toolkit.core.config.json",
        ]
    )
    for c in candidates:
        if c and c.exists():
            return json.loads(c.read_text(encoding=UTF8))
    return {}


def get_default(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get a nested value from a configuration dictionary."""
    cur: Any = config
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def load_state(path: str) -> dict[str, Any]:
    """Load toolkit state from a JSON file."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding=UTF8))


def save_state(path: str, state: dict[str, Any]) -> None:
    """Save toolkit state to a JSON file, creating parent directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding=UTF8)


# ── Utilities ─────────────────────────────────────────────────────────────────


def with_retries(fn: Callable[[], requests.Response], retries: int = 3) -> requests.Response:
    """Executes a function with exponential backoff retries."""

    @retry(
        stop=stop_after_attempt(retries),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        reraise=True,
    )
    def _do_call():
        resp = fn()
        resp.raise_for_status()
        return resp

    try:
        return _do_call()
    except Exception as exc:
        raise SocrataToolkitError(f"Request failed after {retries} retries: {exc}")


def normalize_formats(values: list[str]) -> list[str]:
    """Clean and normalize a list of strings."""
    return [v.strip().lower() for v in values if v and v.strip()]


# ── Socrata Client ────────────────────────────────────────────────────────────


class SocrataClient:
    """Main client for interacting with Socrata SODA APIs."""

    def __init__(self, config: SocrataConfig | None = None) -> None:
        self.config = config or SocrataConfig(app_token=os.getenv(ENV_TOKEN))

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.config.app_token:
            h[HDR_TOKEN] = self.config.app_token
        return h

    def search(
        self,
        query: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        tags: str | None = None,
        order: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query
        if domain:
            params["domains"] = domain
        if category:
            params["categories"] = category
        if tags:
            params["tags"] = tags
        if order:
            params["order"] = order
        resp = with_retries(
            lambda: requests.get(
                "https://api.us.socrata.com/api/catalog/v1",
                params=params,
                headers=self._headers(),
                timeout=self.config.timeout,
            )
        )
        results = []
        for item in resp.json().get("results", []):
            resource = item.get("resource", {})
            results.append(
                SearchResult(
                    name=resource.get("name", ""),
                    description=resource.get("description", ""),
                    domain=item.get("metadata", {}).get("domain", ""),
                    fourfour=resource.get("id", ""),
                    page_views_last_month=resource.get("page_views", {}).get(
                        "page_views_last_month"
                    ),
                    category=resource.get("category"),
                    tags=resource.get("tags", []),
                )
            )
        return results

    def get_metadata(self, domain: str, fourfour: str) -> DatasetMetadata:
        url = f"https://{domain}/api/views/{fourfour}{EXT_JSON}"
        resp = with_retries(
            lambda u=url: requests.get(u, headers=self._headers(), timeout=self.config.timeout)
        )
        payload = resp.json()
        return DatasetMetadata(
            domain=domain,
            fourfour=fourfour,
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            row_count=payload.get("rowsCount") or payload.get("viewCount"),
            license=(
                (payload.get("license") or {}).get("name")
                if isinstance(payload.get("license"), dict)
                else None
            ),
            columns=payload.get("columns", []),
        )

    def fetch_json(
        self,
        domain: str,
        fourfour: str,
        where: str | None = None,
        select: str | None = None,
        order: str | None = None,
        q: str | None = None,
        max_rows: int | None = None,
    ) -> Generator[list[dict[str, Any]], None, None]:
        offset = 0
        remaining = max_rows
        while True:
            limit = (
                self.config.page_size
                if remaining is None
                else min(self.config.page_size, remaining)
            )
            params: dict[str, Any] = {"$limit": limit, "$offset": offset}
            if where:
                params["$where"] = where
            if select:
                params["$select"] = select
            if order:
                params["$order"] = order
            if q:
                params["$q"] = q

            url = f"https://{domain}/resource/{fourfour}{EXT_JSON}"
            resp = with_retries(
                lambda u=url, p=params: requests.get(
                    u, params=p, headers=self._headers(), timeout=self.config.timeout
                )
            )
            batch = resp.json()
            if not batch:
                break
            yield batch
            got = len(batch)
            offset += got
            if remaining is not None:
                remaining -= got
                if remaining <= 0:
                    break

    def fetch_dataframe(self, domain: str, fourfour: str, **kwargs: Any) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for batch in self.fetch_json(domain, fourfour, **kwargs):
            rows.extend(batch)
        return pd.DataFrame(rows)

    def parallel_fetch(
        self, domain: str, fourfour: str, limit: int, max_workers: int = 8
    ) -> pd.DataFrame:
        """Fetch data in parallel using multiple threads."""
        chunk_size = self.config.page_size

        def fetch_batch(offset: int):
            batch_limit = min(chunk_size, limit - offset)
            params = {"$limit": batch_limit, "$offset": offset}
            url = f"https://{domain}/resource/{fourfour}.json"
            resp = with_retries(
                lambda u=url, p=params: requests.get(
                    u, params=p, headers=self._headers(), timeout=self.config.timeout
                )
            )
            return resp.json()

        offsets = range(0, limit, chunk_size)
        all_rows = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_offset = {executor.submit(fetch_batch, offset): offset for offset in offsets}

            for future in concurrent.futures.as_completed(future_to_offset):
                try:
                    data = future.result()
                    if data and isinstance(data, list):
                        all_rows.extend(data)
                except Exception as exc:
                    logger.error(f"Batch fetch failed: {exc}")
        return pd.DataFrame(all_rows)

    def get_odata_url(self, domain: str, fourfour: str) -> str:
        """Generate the OData v4 endpoint for a dataset."""
        return f"https://{domain}/api/odata/v4/{fourfour}"

    def fetch_odata(self, domain: str, fourfour: str, top: int = 100) -> pd.DataFrame:
        """Fetch data using the OData v4 protocol."""
        url = f"{self.get_odata_url(domain, fourfour)}?$top={top}"
        headers = self._headers()
        resp = requests.get(url, headers=headers, timeout=self.config.timeout)
        resp.raise_for_status()
        data = resp.json().get("value", [])
        return pd.DataFrame(data)

    def fetch_geojson(
        self, domain: str, fourfour: str, where: str | None = None, max_rows: int | None = None
    ) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        offset = 0
        remaining = max_rows
        while True:
            limit = (
                self.config.page_size
                if remaining is None
                else min(self.config.page_size, remaining)
            )
            params: dict[str, Any] = {"$limit": limit, "$offset": offset}
            if where:
                params["$where"] = where
            url = f"https://{domain}/resource/{fourfour}{EXT_GEOJSON}"
            resp = with_retries(
                lambda u=url, p=params: requests.get(
                    u, params=p, headers=self._headers(), timeout=self.config.timeout
                )
            )
            fc = resp.json()
            batch = fc.get("features", [])
            if not batch:
                break
            features.extend(batch)
            got = len(batch)
            offset += got
            if remaining is not None:
                remaining -= got
                if remaining <= 0:
                    break
        return {"type": "FeatureCollection", "features": features}

    def fetch_since(self, domain: str, fourfour: str, updated_col: str, since: str, **kwargs: Any):
        """Fetch records updated after a given timestamp."""
        where = kwargs.pop("where", None)
        clause = f"{updated_col} > '{since}'"
        if where:
            where = f"({where}) AND ({clause})"
        else:
            where = clause
        return self.fetch_json(domain, fourfour, where=where, **kwargs)

    def search_datasets(self, query: str, limit: int = 10, offset: int = 0) -> pd.DataFrame:
        """Search the Socrata catalog using keyword search."""
        params = {"q": query, "limit": limit, "offset": offset}
        resp = with_retries(
            lambda: requests.get(
                "https://api.us.socrata.com/api/catalog/v1", params=params, headers=self._headers()
            )
        )
        results = [r.get("resource", {}) for r in resp.json().get("results", [])]
        return pd.DataFrame(results)

    def search_catalog(
        self,
        search_context: str | None = None,
        filters: str | None = None,
        order: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> pd.DataFrame:
        """Advanced catalog search using SoQL-like filters."""
        params: dict[str, Any] = {"limit": limit, "$offset": offset}
        if search_context:
            params["q"] = search_context
        if filters:
            params["$where"] = filters
        if order:
            params["$order"] = order
        resp = with_retries(
            lambda: requests.get(
                "https://api.us.socrata.com/api/catalog/v1", params=params, headers=self._headers()
            )
        )
        results = [r.get("resource", {}) for r in resp.json().get("results", [])]
        return pd.DataFrame(results)

    def catalog_query(self, soql: str) -> pd.DataFrame:
        """Execute a raw SoQL query against the catalog."""
        params = {"$query": soql}
        resp = with_retries(
            lambda: requests.get(
                "https://api.us.socrata.com/api/catalog/v1", params=params, headers=self._headers()
            )
        )
        results = [r.get("resource", {}) for r in resp.json().get("results", [])]
        return pd.DataFrame(results)


# ── SoQL Query Builder ────────────────────────────────────────────────────────


class SoQLBuilder:
    """Fluent interface for building Socrata Query Language (SoQL) strings."""

    def __init__(self) -> None:
        self._select: list[str] = []
        self._where: list[str] = []
        self._order: list[str] = []
        self._group: list[str] = []
        self._limit: int | None = None
        self._offset: int | None = None
        self._q: str | None = None
        self._having: list[str] = []
        self._variables: dict[str, Any] = {}

    def set_variable(self, name: str, value: Any) -> SoQLBuilder:
        """Set a variable for substitution."""
        self._variables[name] = value
        return self

    def select(self, *columns: str) -> SoQLBuilder:
        """Specify columns to return ($select)."""
        self._select.extend(columns)
        return self

    def where(self, *clauses: str) -> SoQLBuilder:
        """Add filtering conditions ($where)."""
        self._where.extend(clauses)
        return self

    def date_trunc(
        self, column: str, precision: str = "month", alias: str | None = None
    ) -> SoQLBuilder:
        """Add a date_trunc expression to the select clause."""
        expr = f"date_trunc_{precision}({column})"
        if alias:
            expr = f"{expr} AS {alias}"
        self._select.append(expr)
        return self

    def aggregate(self, func: str, column: str = "*", alias: str | None = None) -> SoQLBuilder:
        """Add an aggregation expression to the select clause."""
        expr = f"{func}({column})"
        if alias:
            expr = f"{expr} AS {alias}"
        self._select.append(expr)
        return self

    def order(self, column: str, desc: bool = False) -> SoQLBuilder:
        """Add ordering ($order)."""
        self._order.append(f"{column} {'DESC' if desc else 'ASC'}")
        return self

    def group(self, *columns: str) -> SoQLBuilder:
        """Add grouping ($group)."""
        self._group.extend(columns)
        return self

    def limit(self, value: int) -> SoQLBuilder:
        """Set row limit ($limit)."""
        self._limit = value
        return self

    def offset(self, value: int) -> SoQLBuilder:
        """Set row offset ($offset)."""
        self._offset = value
        return self

    def search(self, query: str) -> SoQLBuilder:
        """Full-text search ($q)."""
        self._q = query
        return self

    def having(self, *clauses: str) -> SoQLBuilder:
        """Add grouped filtering conditions ($having)."""
        self._having.extend(clauses)
        return self

    def _apply_variables(self, text: str) -> str:
        """Substitute {{var}} with values."""
        for k, v in self._variables.items():
            text = text.replace(f"{{{{{k}}}}}", str(v))
        return text

    def build(self) -> dict[str, str]:
        """Build the parameters dictionary for SocrataClient."""
        params: dict[str, str] = {}
        if self._select:
            params["select"] = self._apply_variables(", ".join(self._select))
        if self._where:
            params["where"] = self._apply_variables(" AND ".join(f"({c})" for c in self._where))
        if self._order:
            params["order"] = self._apply_variables(", ".join(self._order))
        if self._group:
            params["group"] = self._apply_variables(", ".join(self._group))
        if self._having:
            params["having"] = self._apply_variables(" AND ".join(f"({c})" for c in self._having))
        if self._limit:
            params["limit"] = str(self._limit)
        if self._offset is not None:
            params["offset"] = str(self._offset)
        if self._q:
            params["q"] = self._apply_variables(self._q)
        return params

    def build_query_string(self) -> str:
        """Build a raw SoQL query string ($query)."""
        parts = []
        if self._select:
            parts.append(f"SELECT {self._apply_variables(', '.join(self._select))}")
        if self._where:
            parts.append(
                f"WHERE {self._apply_variables(' AND '.join(f'({c})' for c in self._where))}"
            )
        if self._group:
            parts.append(f"GROUP BY {self._apply_variables(', '.join(self._group))}")
        if self._having:
            parts.append(
                f"HAVING {self._apply_variables(' AND '.join(f'({c})' for c in self._having))}"
            )
        if self._order:
            parts.append(f"ORDER BY {self._apply_variables(', '.join(self._order))}")
        if self._limit:
            parts.append(f"LIMIT {self._limit}")
        if self._offset:
            parts.append(f"OFFSET {self._offset}")
        return " ".join(parts)

    @staticmethod
    def between(column: str, start: str, end: str) -> str:
        """Helper for between(column, start, end)."""
        return f"{column} between '{start}' and '{end}'"

    @staticmethod
    def within_circle(column: str, lat: float, lon: float, radius_meters: float) -> str:
        """Helper for within_circle(column, lat, lon, radius)."""
        return f"within_circle({column}, {lat}, {lon}, {radius_meters})"

    @staticmethod
    def within_box(column: str, lat_nw: float, lon_nw: float, lat_se: float, lon_se: float) -> str:
        """Helper for within_box(column, lat_nw, lon_nw, lat_se, lon_se)."""
        return f"within_box({column}, {lat_nw}, {lon_nw}, {lat_se}, {lon_se})"


# ── Schema Registry ───────────────────────────────────────────────────────────


@dataclass
class ColumnSchema:
    name: str
    dtype: str
    nullable: bool = True
    position: int = 0
    sample_value: Any = None


@dataclass
class DatasetSchema:
    dataset_id: str
    version: int
    columns: dict[str, ColumnSchema]
    captured_at: datetime
    row_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class SchemaRegistry:
    def __init__(self, storage_dir: str = "schema_registry/"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def register_schema(self, schema: DatasetSchema):
        path = self.storage_dir / f"{schema.dataset_id}_v{schema.version}{EXT_JSON}"
        path.write_text(json.dumps(asdict(schema), default=str))


class SchemaValidator:
    """Validates dataframes against a defined schema."""

    def __init__(self, schema: dict[str, str]):
        self.schema = schema

    def validate(self, df: pd.DataFrame) -> list[str]:
        errors = []
        for col, _dtype in self.schema.items():
            if col not in df.columns:
                errors.append(f"Missing: {col}")
        return errors


def search_nyc_datasets(query: str, domain: str = DEFAULT_DOMAIN, limit: int = 10) -> pd.DataFrame:
    """Convenience function for searching NYC datasets."""
    client = SocrataClient()
    results = client.search(query=query, domain=domain, limit=limit)
    return pd.DataFrame([asdict(r) for r in results])


def generate_data_dictionary(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Generate a data dictionary from a DataFrame."""
    return [
        {"column": c, "dtype": str(df[c].dtype), "null_pct": f"{df[c].isna().mean() * 100:.1f}%"}
        for c in df.columns
    ]


# ── Database Helpers ──────────────────────────────────────────────────────────


def build_fts_index_sql(
    table: str, columns: Iterable[str], language: str = "english", index_name: str | None = None
) -> str:
    """Return SQL to create a GIN-backed FTS expression index on `table` for `columns`."""
    cols = list(columns)
    if not cols:
        raise ValueError("columns must be a non-empty iterable of column names")
    concat = " || ' ' || ".join(f"COALESCE({c}, '')" for c in cols)
    safe_table = table.replace('"', "")
    safe_cols = "_".join(c.replace('"', "").replace(".", "_") for c in cols)
    idx = index_name or f"{safe_table.replace('.', '_')}_{safe_cols}_fts_idx"
    sql = f"CREATE INDEX IF NOT EXISTS \"{idx}\" ON {table} USING GIN (to_tsvector('{language}', {concat}));"
    return sql


def ensure_fts_index(
    dsn: str, table: str, columns: Iterable[str], language: str = "english"
) -> None:
    """Connect to Postgres and create the FTS index for the given table/columns."""
    try:
        import psycopg
    except Exception as exc:
        raise ImportError("Install Postgres extras: pip install '.[postgres]'") from exc
    sql = build_fts_index_sql(table, columns, language=language)
    conn = psycopg.connect(dsn)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    conn.close()


# ── Storage Management ────────────────────────────────────────────────────────


def get_bundle_dir():
    """Detect if running as a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.getcwd()


class DuckDBManager:
    """Manages DuckDB local file connection and extensions."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("DUCKDB_PATH", "nyc_mission_control.db")
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            logger.info(f"Connecting to DuckDB at {self.db_path}")
            self._conn = duckdb.connect(self.db_path)
            try:
                self._conn.execute("INSTALL spatial;")
                self._conn.execute("LOAD spatial;")
                logger.info("DuckDB 'spatial' extension loaded.")
            except Exception as e:
                logger.warning(f"Could not load DuckDB spatial extension: {e}")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DuckDB connection closed.")

    def query(self, sql: str, *args):
        return self.conn.execute(sql, *args)


class DuckDBRepository:
    """Base repository for DuckDB operations with optimized bulk ingestion."""

    def __init__(self, manager: DuckDBManager, table_name: str):
        self.manager = manager
        self.table_name = table_name

    def upsert_dataframe(self, df: pd.DataFrame, conflict_column: str) -> int:
        if df.empty:
            return 0
        table_name = self.table_name
        temp_view = f"temp_view_{table_name}"
        self.manager.conn.register(temp_view, df)
        tables = self.manager.conn.execute("SHOW TABLES").fetchall()
        table_exists = any(t[0] == table_name for t in tables)
        if not table_exists:
            logger.info(f"Creating table {table_name} from dataframe.")
            self.manager.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {temp_view}")
            self.manager.conn.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_{conflict_column} ON {table_name} ({conflict_column})"
            )
            return len(df)
        else:
            columns = df.columns.tolist()
            update_set = ", ".join(
                [f"{col} = EXCLUDED.{col}" for col in columns if col != conflict_column]
            )
            sql = f"INSERT INTO {table_name} SELECT * FROM {temp_view} ON CONFLICT ({conflict_column}) DO UPDATE SET {update_set}"
            self.manager.conn.execute(sql)
            return len(df)

    def fetch_all(self, limit: int = 1000) -> pd.DataFrame:
        return self.manager.conn.execute(f"SELECT * FROM {self.table_name} LIMIT {limit}").df()

    def count(self) -> int:
        result = self.manager.conn.execute(f"SELECT count(*) FROM {self.table_name}").fetchone()
        return result[0] if result else 0


# ── Exporters ─────────────────────────────────────────────────────────────────


class XLSXExporter:
    """Simple Excel writer for data distribution."""

    def write(
        self,
        data: pd.DataFrame | list[dict[str, Any]],
        path: str,
        sheet: str = "Data",
        meta: Any = None,
        freeze_panes: bool = True,
        auto_filter: bool = True,
    ) -> None:
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        with pd.ExcelWriter(path, engine=ENGINE_XL) as writer:
            df.to_excel(writer, sheet_name=sheet, index=False)
            ws = writer.book[sheet]
            if freeze_panes:
                ws.freeze_panes = XL_FREEZE
            if auto_filter:
                ws.auto_filter.ref = ws.dimensions
            if meta is not None:
                pd.DataFrame([meta.summary()]).to_excel(writer, sheet_name="Summary", index=False)
                pd.DataFrame(meta.column_dict()).to_excel(
                    writer, sheet_name="Column Dictionary", index=False
                )


class ParquetExporter:
    """High-performance Parquet writer."""

    def write(
        self,
        data: pd.DataFrame | list[dict[str, Any]],
        path: str,
        compression: str = COMPRESSION_SNAPPY,
    ) -> None:
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        df.to_parquet(path, compression=compression, index=False)


class DuckDBExporter:
    """High-performance DuckDB exporter."""

    def __init__(self, db_path: str | None = None):
        self.manager = DuckDBManager(db_path)

    def __enter__(self) -> DuckDBExporter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.manager.close()

    def upsert_batches(
        self,
        batches: Iterable[list[dict[str, Any]] | pd.DataFrame],
        table: str,
        conflict_column: str,
    ) -> int:
        repo = DuckDBRepository(self.manager, table)
        total = 0
        for batch in batches:
            df = batch if isinstance(batch, pd.DataFrame) else pd.DataFrame(batch)
            total += repo.upsert_dataframe(df, conflict_column)
        return total


class APIKeyManager:
    def __init__(self, storage_path: str | None = None):
        self.storage_path = storage_path

    def create_key(self, name: str) -> str:
        return "sk_test_123"


class BackwardCompatibilityChecker:
    def check(self, old_schema: Any, new_schema: Any) -> list[str]:
        return []


class DataFreshnessMonitor:
    def check_freshness(self, dataset_id: str) -> dict[str, Any]:
        return {"status": "fresh"}


class EntityResolver:
    def resolve(self, df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        return df


def _quote_value(val: Any) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        safe_val = val.replace("'", "''")
        return f"'{safe_val}'"
    return str(val)


def and_join(clauses: list[str]) -> str:
    valid = [c for c in clauses if c]
    return " AND ".join(valid)


def or_join(clauses: list[str]) -> str:
    valid = [c for c in clauses if c]
    return " OR ".join(valid)


def in_clause(column: str, values: list[Any]) -> str:
    valid_values = [v for v in values if v is not None]
    if not valid_values:
        return "FALSE"
    quoted = [_quote_value(v) for v in valid_values]
    return f"{column} IN ({','.join(quoted)})"


def like_clause(column: str, pattern: str) -> str:
    return f"{column} LIKE {_quote_value(pattern)}"


def equals_clause(column: str, value: Any) -> str:
    return f"{column} = {_quote_value(value)}"



    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "columns": {k: v.__dict__ for k, v in self.columns.items()},
            "captured_at": self.captured_at.isoformat(),
            "row_count": self.row_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetSchema:
        cols = {k: ColumnSchema(**v) for k, v in data["columns"].items()}
        return cls(
            dataset_id=data["dataset_id"],
            version=data["version"],
            columns=cols,
            captured_at=datetime.fromisoformat(data["captured_at"]),
            row_count=data["row_count"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class SchemaChange:
    change_type: str
    field_name: str
    old_value: Any
    new_value: Any
    is_breaking: bool
    description: str


class ChangeType:
    BREAKING = "BREAKING"
    NON_BREAKING = "NON_BREAKING"
    COLUMN_ADDITION = "COLUMN_ADDITION"
    COLUMN_DELETION = "COLUMN_DELETION"
    TYPE_CHANGE = "TYPE_CHANGE"


class BreakingChangeAlert(Exception):
    def __init__(
        self,
        dataset_id: str = "",
        from_version: int = 0,
        to_version: int = 0,
        breaking_changes: list[SchemaChange] = None,
        timestamp: datetime = None,
        recommendation: str = "",
        message: str = "",
    ):
        self.dataset_id = dataset_id
        self.from_version = from_version
        self.to_version = to_version
        self.breaking_changes = breaking_changes or []
        self.timestamp = timestamp or datetime.now()
        self.recommendation = recommendation
        self.message = message or f"Breaking schema change in {dataset_id}"
        super().__init__(self.message)

    def __str__(self):
        return f"BREAKING SCHEMA CHANGE ALERT: {self.dataset_id} ({self.from_version} -> {self.to_version})"


class SQLQueryBuilder:
    def build(self, table: str, filters: dict[str, Any]) -> str:
        return f"SELECT * FROM {table}"
