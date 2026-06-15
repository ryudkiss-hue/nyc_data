"""DuckDB connection helpers for local analytics."""

from __future__ import annotations

import logging
import os
import sys
import threading
import uuid
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
        or text.lower().startswith(("select", "with", "describe", "summarize", "pragma", "from"))
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
    """Manages DuckDB local file connection, MotherDuck integration, and extensions."""

    def __init__(
        self,
        db_path: str | None = None,
        read_only: bool | None = None,
        motherduck_token: str | None = None,
    ):
        self.db_path = db_path or os.getenv(
            "DUCKDB_PATH", "data/local_db/nyc_mission_control.duckdb"
        )
        self.read_only = read_only
        self.motherduck_token = motherduck_token or os.getenv("MOTHERDUCK_TOKEN")
        self._conn: duckdb.DuckDBPyConnection | None = None
        # [FIX 1] Add connection lock for thread-safe singleton access
        self._conn_lock = threading.RLock()

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Thread-safe singleton connection with double-check locking pattern.

        [FIX 1] Ensures all concurrent access to the shared connection is serialized
        via an RLock, preventing isolation violations and connection state conflicts.
        """
        if self._conn is None:
            with self._conn_lock:
                # Double-check pattern: another thread may have created connection
                if self._conn is None:
                    connection_path = self.db_path
                    # If token provided but path is not md:, we still connect to local
                    # and allow manual ATTACH 'md:' later.
                    # If path is 'md:', it connects to MotherDuck directly.

                    logger.info("Connecting to DuckDB at %s", connection_path)
                    # Use read_only if requested via environment or default to False
                    is_read_only = (
                        self.read_only
                        if self.read_only is not None
                        else (os.getenv("DUCKDB_READ_ONLY", "false").lower() == "true")
                    )

                    # DuckDB 0.10+ handles 'md:' natively if token is in env or config
                    if self.motherduck_token and not connection_path.startswith("md:"):
                        # We connect to local but will enable MD extension
                        self._conn = duckdb.connect(connection_path, read_only=is_read_only)
                        try:
                            self._conn.execute(f"SET motherduck_token='{self.motherduck_token}';")
                            self._conn.execute("INSTALL motherduck;")
                            self._conn.execute("LOAD motherduck;")
                        except Exception as exc:
                            logger.warning("Could not initialize MotherDuck extension: %s", exc)
                    else:
                        self._conn = duckdb.connect(connection_path, read_only=is_read_only)

                    # Item 6: Disable insertion order for performance
                    self._conn.execute("SET preserve_insertion_order = false;")

                    # Initialize Spatial Extension
                    try:
                        self._conn.execute("INSTALL spatial;")
                        self._conn.execute("LOAD spatial;")
                        logger.info("DuckDB spatial extension loaded successfully.")
                    except Exception as exc:
                        logger.warning("Could not load DuckDB spatial extension: %s", exc)
        return self._conn

    def execute_atomic(self, sql: str, *args: object):
        """Execute SQL under exclusive lock for ACID isolation.

        [FIX 1] Use for operations that must be atomic with respect to concurrent access:
        - Multi-step upserts
        - Transactions (BEGIN...COMMIT)
        - Schema modifications

        Single-threaded or write-heavy operations don't need this;
        they benefit from the lock implicitly via the shared connection.

        Args:
            sql: SQL statement to execute
            *args: Query parameters for parameterized queries

        Returns:
            DuckDB query result
        """
        with self._conn_lock:
            return self.conn.execute(sql, *args)

    def attach_motherduck(self, alias: str = "md"):
        """Attach MotherDuck cloud database to the current local session."""
        logger.info("Attaching MotherDuck as '%s'", alias)
        self.conn.execute(f"ATTACH 'md:' AS {alias}")

    def publish_to_motherduck(self, table_name: str, remote_name: str, database: str = "my_db"):
        """Item 7: Data Bridging - Push local table/view to MotherDuck.

        Example: publish_to_motherduck('local_cache', 'nyc_data_share')
        """
        logger.info("Publishing '%s' to MotherDuck as '%s'", table_name, remote_name)
        # Ensure MD is attached
        try:
            self.attach_motherduck("md_publish")
        except Exception:
            pass  # Already attached or error

        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS md_publish.{database}.{remote_name} AS SELECT * FROM {table_name}"
        )

    def query_ducklake(self, sql: str, *args: object):
        """Execute a 'DuckLake' query that joins local L2 Parquet caches with MD.

        This helper ensures MotherDuck is attached and runs the query.
        """
        try:
            self.attach_motherduck()
        except Exception:
            pass
        return self.query(sql, *args)

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
        """Item 5: Intermediate Query Caching.

        Uses CREATE TABLE AS SELECT (CTAS) to materialize query results.
        """
        logger.info(f"Caching query result to table: {table_name}")
        self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS {sql}")

    def summarize_table(self, table_name: str):
        """Generate a summary of the table's statistics using DuckDB's SUMMARIZE."""
        return self.query(f"SUMMARIZE {table_name}").df()

    def get_partitioned_parquet_files(
        self, key: str, cache_dir: str | Path | None = None
    ) -> list[Path]:
        """Item 2: Helper for Partitioned Parquet."""
        base = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
        if not base.exists():
            return []
        return sorted(list(base.glob(f"{key}_*.parquet")))


class DuckDBRepository:
    """Repository for DuckDB bulk upserts with Spatial awareness.

    Supports 'DuckLake' architecture by allowing targeting of different
    attached databases (e.g., 'main' for local, 'md' for MotherDuck).
    """

    def __init__(self, manager: DuckDBManager, table_name: str, database: str = "main"):
        self.manager = manager
        self.table_name = table_name.replace('"', "")
        self.database = database.replace('"', "")

    @property
    def qualified_name(self) -> str:
        return f'"{self.database}"."{self.table_name}"'

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
        lon_cand = next(
            (cols[c] for c in ("longitude", "lon", "lng", "long", "x", "xcoord") if c in cols),
            None,
        )

        if lat_cand and lon_cand:
            spatial_map["lat"] = lat_cand
            spatial_map["lon"] = lon_cand

        return spatial_map

    def upsert_dataframe(self, df: pd.DataFrame, conflict_column: str) -> int:
        if df.empty:
            return 0

        conflict_col = conflict_column.replace('"', "")
        temp_view = f"temp_view_{self.table_name}_{uuid.uuid4().hex[:8]}"
        self.manager.conn.register(temp_view, df)

        # Detect spatial columns to create native GEOMETRY
        spatial_info = self._detect_spatial_cols(df)
        geom_expr = "NULL"
        if "wkt" in spatial_info:
            geom_expr = f'ST_GeomFromText("{spatial_info["wkt"]}")'
        elif "lat" in spatial_info and "lon" in spatial_info:
            # Note: NYC uses EPSG:2263 or WGS84 (4326). We default to 4326 for ingestion.
            geom_expr = (
                f'ST_Point(CAST("{spatial_info["lon"]}" AS DOUBLE), '
                f'CAST("{spatial_info["lat"]}" AS DOUBLE))'
            )

        # Check if table exists — use direct query as the primary approach since
        # information_schema.table_catalog varies ('memory' for in-memory, database
        # name for file-based) and doesn't reliably match self.database ('main').
        try:
            self.manager.conn.execute(f"SELECT 1 FROM {self.qualified_name} WHERE 1=0")
            table_exists = True
        except Exception:
            table_exists = False

        if not table_exists:
            # Create table with an explicit GEOMETRY column
            # Use IF NOT EXISTS for double safety
            sql_create = f"""
                CREATE TABLE IF NOT EXISTS {self.qualified_name} AS
                SELECT *,
                ({geom_expr}) AS native_geom
                FROM "{temp_view}"
            """
            self.manager.conn.execute(sql_create)
            # Create index if not in MotherDuck (MD doesn't support local indexes in the same way)
            if self.database == "main":
                self.manager.conn.execute(
                    f'CREATE UNIQUE INDEX IF NOT EXISTS "idx_{self.table_name}_{conflict_col}" '
                    f'ON {self.qualified_name} ("{conflict_col}")'
                )
            return len(df)

        # Schema Evolution: get existing columns via information_schema,
        # filtering by table_schema='main' (works for both in-memory and file-based).
        existing_cols = [
            row[0]
            for row in self.manager.conn.execute(
                f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_schema = 'main' "
                f"AND table_name = '{self.table_name}'"
            ).fetchall()
        ]

        if not existing_cols:
            # Fallback to PRAGMA if info_schema failed
            prefix = f'"{self.database}".' if self.database != "main" else ""
            existing_cols = [
                c[1]
                for c in self.manager.conn.execute(
                    f"PRAGMA table_info('{prefix}{self.table_name}')"
                ).fetchall()
            ]

        if "native_geom" not in existing_cols:
            logger.info("Spatial Migration: Adding 'native_geom' column to %s", self.qualified_name)
            self.manager.conn.execute(
                f"ALTER TABLE {self.qualified_name} ADD COLUMN native_geom GEOMETRY;"
            )

        # Standard column evolution
        for col in df.columns:
            if col not in existing_cols and col != "native_geom":
                self.manager.conn.execute(
                    f'ALTER TABLE {self.qualified_name} ADD COLUMN "{col.replace(chr(34), "")}" VARCHAR;'
                )

        columns = df.columns.tolist()
        update_set_parts = [
            f'"{col.replace(chr(34), "")}" = EXCLUDED."{col.replace(chr(34), "")}"'
            for col in columns
            if col != conflict_column
        ]
        # Always update native_geom during upsert
        update_set_parts.append(f"native_geom = ({geom_expr})")
        update_set = ", ".join(update_set_parts)

        # MotherDuck might not support ON CONFLICT in all versions/modes yet
        # Fallback to DELETE + INSERT if needed, but for now use ON CONFLICT
        sql_upsert = f"""
            INSERT INTO {self.qualified_name} BY NAME
            SELECT *, ({geom_expr}) AS native_geom FROM "{temp_view}"
            ON CONFLICT ("{conflict_col}") DO UPDATE SET {update_set}
        """
        self.manager.conn.execute(sql_upsert)
        return len(df)

    def fetch_all(self, limit: int | None = None) -> pd.DataFrame:
        if limit is None or limit == -1:
            return self.manager.conn.execute(f"SELECT * FROM {self.qualified_name}").df()
        return self.manager.conn.execute(
            f"SELECT * FROM {self.qualified_name} LIMIT ?", [limit]
        ).df()

    def count(self) -> int:
        row = self.manager.conn.execute(f"SELECT COUNT(*) FROM {self.qualified_name}").fetchone()
        return int(row[0]) if row else 0
