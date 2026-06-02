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

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("DUCKDB_PATH", "data/local_db/nyc_mission_control.duckdb")
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            logger.info("Connecting to DuckDB at %s", self.db_path)
            self._conn = duckdb.connect(self.db_path)
            try:
                self._conn.execute("INSTALL spatial;")
                self._conn.execute("LOAD spatial;")
            except Exception as exc:
                logger.warning("Could not load DuckDB spatial extension: %s", exc)
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def query(self, sql: str, *args: object):
        return self.conn.execute(sql, *args)


class DuckDBRepository:
    """Repository for DuckDB bulk upserts."""

    def __init__(self, manager: DuckDBManager, table_name: str):
        self.manager = manager
        self.table_name = table_name

    def upsert_dataframe(self, df: pd.DataFrame, conflict_column: str) -> int:
        if df.empty:
            return 0
        # Sanitize identifiers: strip embedded double-quotes before quoting
        table_name = self.table_name.replace('"', '')
        conflict_col = conflict_column.replace('"', '')
        temp_view = f"temp_view_{table_name}"
        self.manager.conn.register(temp_view, df)
        tables = self.manager.conn.execute("SHOW TABLES").fetchall()
        table_exists = any(t[0] == table_name for t in tables)
        if not table_exists:
            self.manager.conn.execute(
                f'CREATE TABLE "{table_name}" AS SELECT * FROM "{temp_view}"'
            )
            self.manager.conn.execute(
                f'CREATE UNIQUE INDEX IF NOT EXISTS "idx_{table_name}_{conflict_col}" '
                f'ON "{table_name}" ("{conflict_col}")'
            )
            return len(df)
        columns = df.columns.tolist()
        update_set = ", ".join(
            f'"{col.replace(chr(34), "")}" = EXCLUDED."{col.replace(chr(34), "")}"'
            for col in columns if col != conflict_column
        )
        sql = (
            f'INSERT INTO "{table_name}" SELECT * FROM "{temp_view}" '
            f'ON CONFLICT ("{conflict_col}") DO UPDATE SET {update_set}'
        )
        self.manager.conn.execute(sql)
        return len(df)

    def fetch_all(self, limit: int = 1000) -> pd.DataFrame:
        safe_table = self.table_name.replace('"', '')
        return self.manager.conn.execute(
            f'SELECT * FROM "{safe_table}" LIMIT ?', [limit]
        ).df()

    def count(self) -> int:
        safe_table = self.table_name.replace('"', '')
        row = self.manager.conn.execute(f'SELECT COUNT(*) FROM "{safe_table}"').fetchone()
        return int(row[0]) if row else 0
