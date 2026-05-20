"""DuckDB connection helpers for local analytics."""

from __future__ import annotations

import logging
import os
import sys

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


def get_bundle_dir() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.getcwd()


class DuckDBManager:
    """Manages DuckDB local file connection and extensions."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("DUCKDB_PATH", "nyc_mission_control.db")
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
        table_name = self.table_name
        temp_view = f"temp_view_{table_name}"
        self.manager.conn.register(temp_view, df)
        tables = self.manager.conn.execute("SHOW TABLES").fetchall()
        table_exists = any(t[0] == table_name for t in tables)
        if not table_exists:
            self.manager.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {temp_view}")
            self.manager.conn.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_{conflict_column} "
                f"ON {table_name} ({conflict_column})"
            )
            return len(df)
        columns = df.columns.tolist()
        update_set = ", ".join(
            f"{col} = EXCLUDED.{col}" for col in columns if col != conflict_column
        )
        sql = (
            f"INSERT INTO {table_name} SELECT * FROM {temp_view} "
            f"ON CONFLICT ({conflict_column}) DO UPDATE SET {update_set}"
        )
        self.manager.conn.execute(sql)
        return len(df)

    def fetch_all(self, limit: int = 1000) -> pd.DataFrame:
        return self.manager.conn.execute(f"SELECT * FROM {self.table_name} LIMIT {limit}").df()

    def count(self) -> int:
        row = self.manager.conn.execute(f"SELECT COUNT(*) FROM {self.table_name}").fetchone()
        return int(row[0]) if row else 0
