"""DuckDB connection helpers for local analytics."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


def get_bundle_dir() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.getcwd()


# ---------------------------------------------------------------------------
# Parquet cache querying (Item 34)
# ---------------------------------------------------------------------------

def _escape_sql_literal(value: str) -> str:
    """Escape single quotes so *value* is safe inside a SQL string literal."""
    return value.replace("'", "''")


# INSTALL only hits the network/disk once per process; LOAD is cheap per-connection.
_SPATIAL_INSTALLED = False


def _default_cache_dir() -> Path:
    """Return the on-disk L2 cache directory used by Mission Control.

    Honours the ``SOCRATA_CACHE_DIR`` env var (same override the cache_manager
    uses); otherwise falls back to ``<repo_root>/data/cache``.
    """
    env_dir = os.getenv("SOCRATA_CACHE_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    # This file lives at src/socrata_toolkit/core/ — repo root is parents[3].
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "cache"


def _latest_parquet_for_key(key: str, cache_dir: str | Path | None) -> Path | None:
    """Return the newest cached Parquet file for *key*, or ``None`` if none exist.

    Matches the cache_manager naming (``<key>_<ts>.parquet.gz``) and the older
    ``<key>.parquet`` layout used by the legacy parquet cache.
    """
    base = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
    if not base.exists():
        return None
    candidates = sorted(
        (
            *base.glob(f"{key}_*.parquet.gz"),
            *base.glob(f"{key}_*.parquet"),
            *base.glob(f"{key}.parquet"),
        ),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def query_parquet_cache(
    sql_or_key: str,
    *,
    cache_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Run DuckDB SQL directly over cached Parquet file(s).

    DuckDB reads Parquet with projection and predicate pushdown, so only the
    requested columns/rows are materialized — no full pandas load of the cache.

    Two call styles are supported:

    1. **Full SQL** — a SQL string that already references a source such as
       ``read_parquet('<path>')``. It is executed verbatim::

           query_parquet_cache(
               "SELECT bbl FROM read_parquet('data/cache/violations_*.parquet.gz') "
               "WHERE status = 'OPEN'"
           )

    2. **Cache key** — a bare dataset key (no whitespace / SQL keywords). The
       newest cached Parquet file for that key under *cache_dir* is located and
       ``SELECT * FROM read_parquet('<path>')`` is run::

           query_parquet_cache("violations")

    *cache_dir* defaults to ``SOCRATA_CACHE_DIR`` if set, else
    ``<repo_root>/data/cache`` — matching the cache_manager layout.

    Returns a pandas ``DataFrame``. Raises ``ValueError`` for empty input,
    ``FileNotFoundError`` when a bare key has no cached file, and
    ``RuntimeError`` for DuckDB execution errors.
    """
    text = (sql_or_key or "").strip()
    if not text:
        raise ValueError("query_parquet_cache: sql_or_key must not be empty")

    # Heuristic: whitespace, parens, or a leading SQL keyword => treat as raw SQL.
    # Otherwise the argument is a bare dataset cache key.
    looks_like_sql = (
        any(ch.isspace() for ch in text)
        or "(" in text
        or text.lower().startswith(
            ("select", "with", "describe", "summarize", "pragma", "from")
        )
    )

    if looks_like_sql:
        sql = text
    else:
        path = _latest_parquet_for_key(text, cache_dir)
        if path is None:
            raise FileNotFoundError(
                f"query_parquet_cache: no cached Parquet file found for key '{text}'"
            )
        sql = f"SELECT * FROM read_parquet('{_escape_sql_literal(str(path))}')"

    try:
        return duckdb.query(sql).to_df()
    except duckdb.Error as exc:  # pragma: no cover - depends on caller SQL
        raise RuntimeError(f"query_parquet_cache: DuckDB query failed: {exc}") from exc


class DuckDBManager:
    """Manages DuckDB local file connection and extensions."""

    def __init__(self, db_path: str | None = None, read_only: bool | None = None):
        self.db_path = db_path or os.getenv("DUCKDB_PATH", "data/local_db/nyc_mission_control.duckdb")
        self.read_only = read_only
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            logger.info("Connecting to DuckDB at %s", self.db_path)
            # Use read_only if requested via environment or default to False
            is_read_only = self.read_only if self.read_only is not None else (os.getenv("DUCKDB_READ_ONLY", "false").lower() == "true")
            self._conn = duckdb.connect(self.db_path, read_only=is_read_only)

            # Item 6: Disable insertion order for performance
            self._conn.execute("SET preserve_insertion_order = false;")

            # Initialize Spatial Extension (INSTALL once per process, LOAD per connection)
            global _SPATIAL_INSTALLED
            try:
                if not _SPATIAL_INSTALLED:
                    self._conn.execute("INSTALL spatial;")
                    _SPATIAL_INSTALLED = True
                self._conn.execute("LOAD spatial;")
                logger.info("DuckDB spatial extension loaded successfully.")
            except Exception as exc:
                logger.warning("Could not load DuckDB spatial extension: %s", exc)
        return self._conn

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def query(self, sql: str, *args: object):
        """Execute a query and log performance."""
        logger.info(f"Executing Query: {sql[:100]}...")
        return self.conn.execute(sql, *args)

    def debug_query(self, sql: str, *args: object):
        """Item 4: Execution Auditing with EXPLAIN ANALYZE."""
        explain_sql = f"EXPLAIN ANALYZE {sql}"
        result = self.conn.execute(explain_sql, *args).fetchall()
        logger.info(f"Query Plan: {result}")
        return self.conn.execute(sql, *args)

    def create_table_as(self, table_name: str, sql: str):
        """Item 5: Intermediate Query Caching."""
        logger.info(f"Caching query result to table: {table_name}")
        self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS {sql}")

    def get_partitioned_parquet_files(self, key: str, cache_dir: str | Path | None = None) -> list[Path]:
        """Item 2: Helper for Partitioned Parquet."""
        base = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
        if not base.exists():
            return []
        return sorted(list(base.glob(f"{key}_*.parquet")))



class DuckDBRepository:
    """Repository for DuckDB bulk upserts with Spatial awareness."""

    def __init__(self, manager: DuckDBManager, table_name: str):
        self.manager = manager
        self.table_name = table_name

    def _detect_spatial_cols(self, df: pd.DataFrame) -> dict[str, str]:
        """Identify potential spatial columns and their types (lat/lon vs WKT)."""
        cols = {c.lower(): c for c in df.columns}
        spatial_map = {}

        # WKT Detection
        for wkt_cand in ("the_geom", "geometry", "location_wkt", "wkt"):
            if wkt_cand in cols:
                spatial_map["wkt"] = cols[wkt_cand]
                break

        # Lat/Lon Detection
        lat_cand = next((cols[c] for c in ("latitude", "lat", "y", "ycoord") if c in cols), None)
        lon_cand = next((cols[c] for c in ("longitude", "lon", "lng", "long", "x", "xcoord") if c in cols), None)

        if lat_cand and lon_cand:
            spatial_map["lat"] = lat_cand
            spatial_map["lon"] = lon_cand

        return spatial_map

    def upsert_dataframe(self, df: pd.DataFrame, conflict_column: str) -> int:
        if df.empty:
            return 0

        table_name = self.table_name.replace('"', '')
        conflict_col = conflict_column.replace('"', '')
        temp_view = f"temp_view_{table_name}"
        self.manager.conn.register(temp_view, df)

        # Detect spatial columns to create native GEOMETRY
        spatial_info = self._detect_spatial_cols(df)
        geom_expr = "NULL"
        if "wkt" in spatial_info:
            geom_expr = f"ST_GeomFromText(\"{spatial_info['wkt']}\")"
        elif "lat" in spatial_info and "lon" in spatial_info:
            # Note: NYC uses EPSG:2263 or WGS84 (4326). We default to 4326 for ingestion.
            geom_expr = f"ST_Point(CAST(\"{spatial_info['lon']}\" AS DOUBLE), CAST(\"{spatial_info['lat']}\" AS DOUBLE))"

        tables = self.manager.conn.execute("SHOW TABLES").fetchall()
        table_exists = any(t[0] == table_name for t in tables)

        if not table_exists:
            # Create table with an explicit GEOMETRY column derived from detected spatial sources
            sql_create = f"""
                CREATE TABLE "{table_name}" AS
                SELECT *,
                ({geom_expr}) AS native_geom
                FROM "{temp_view}"
            """
            self.manager.conn.execute(sql_create)
            self.manager.conn.execute(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "idx_{table_name}_{conflict_col}" '
                f'ON "{table_name}" ("{conflict_col}")'
            )
            return len(df)

        # Schema Evolution: Ensure native_geom exists
        existing_cols = [c[1] for c in self.manager.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()]
        if "native_geom" not in existing_cols:
            logger.info(f"Spatial Migration: Adding 'native_geom' column to '{table_name}'")
            self.manager.conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN native_geom GEOMETRY;')

        # Standard column evolution: late-arriving columns default to VARCHAR. This is
        # intentional for messy municipal data — a column that looks numeric today may
        # arrive as a string in a future batch, and VARCHAR absorbs both without
        # breaking ingestion (see test_type_safety_on_evolution).
        for col in df.columns:
            if col not in existing_cols and col != "native_geom":
                self.manager.conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.replace(chr(34), "")}" VARCHAR;')

        columns = df.columns.tolist()
        update_set_parts = [
            f'"{col.replace(chr(34), "")}" = EXCLUDED."{col.replace(chr(34), "")}"'
            for col in columns if col != conflict_column
        ]
        # Update native_geom only when this batch actually carries geometry source
        # columns; otherwise a projected/partial fetch would overwrite existing
        # geometry with NULL.
        if geom_expr != "NULL":
            update_set_parts.append(f'native_geom = ({geom_expr})')
        update_set = ", ".join(update_set_parts)

        sql_upsert = f"""
            INSERT INTO "{table_name}" BY NAME
            SELECT *, ({geom_expr}) AS native_geom FROM "{temp_view}"
            ON CONFLICT ("{conflict_col}") DO UPDATE SET {update_set}
        """
        self.manager.conn.execute(sql_upsert)
        return len(df)

    def fetch_all(self, limit: int | None = None) -> pd.DataFrame:
        safe_table = self.table_name.replace('"', '')
        if limit is None or limit == -1:
            return self.manager.conn.execute(
                f'SELECT * FROM "{safe_table}"'
            ).df()
        return self.manager.conn.execute(
            f'SELECT * FROM "{safe_table}" LIMIT ?', [limit]
        ).df()

    def count(self) -> int:
        safe_table = self.table_name.replace('"', '')
        row = self.manager.conn.execute(f'SELECT COUNT(*) FROM "{safe_table}"').fetchone()
        return int(row[0]) if row else 0
