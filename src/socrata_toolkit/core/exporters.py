"""Data exporters for Postgres, MongoDB and simple XLSX backup.

This module centralizes the logic that writes data to downstream systems.
Implementations are intentionally pragmatic: they create tables/indexes
automatically for convenience in early development, and provide faster
paths (COPY into a temp table) when possible.

Classes:
 - `XLSXExporter`: simple Excel writer (pandas/openpyxl)
 - `PostgresExporter`: psycopg-backed upsert utilities (`upsert_batches` and `copy_upsert_batches`)
 - `MongoExporter`: pymongo-backed upsert utilities using bulk_write
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

import pandas as pd


class XLSXExporter:
    def write(self, data: pd.DataFrame | list[dict[str, Any]], path: str, sheet: str = "Data", meta: Any = None, freeze_panes: bool = True, auto_filter: bool = True) -> None:
        """Write data to an Excel file, optionally appending Summary and Column Dictionary sheets from meta."""
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=sheet, index=False)
            ws = writer.book[sheet]
            if freeze_panes:
                ws.freeze_panes = "A2"
            if auto_filter:
                ws.auto_filter.ref = ws.dimensions
            if meta is not None:
                pd.DataFrame([meta.summary()]).to_excel(writer, sheet_name="Summary", index=False)
                pd.DataFrame(meta.column_dict()).to_excel(writer, sheet_name="Column Dictionary", index=False)


class DuckDBExporter:
    """Exporter for local DuckDB or MotherDuck cloud databases."""

    def __init__(
        self,
        db_path: str | None = None,
        motherduck_token: str | None = None,
        database: str = "main",
    ):
        from .duckdb_store import DuckDBManager

        self.manager = DuckDBManager(db_path=db_path, motherduck_token=motherduck_token)
        self.database = database

    def __enter__(self) -> DuckDBExporter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.manager.close()

    def upsert_batches(
        self, batches: Iterable[list[dict[str, Any]]], table: str, conflict_column: str
    ) -> int:
        """Upsert batches into DuckDB/MotherDuck."""
        from .duckdb_store import DuckDBRepository

        repo = DuckDBRepository(self.manager, table, database=self.database)
        total = 0
        for batch in batches:
            if not batch:
                continue
            df = pd.DataFrame(batch)
            total += repo.upsert_dataframe(df, conflict_column)
        return total


class PostgresExporter:
    def __init__(self, dsn: str):
        try:
            import psycopg
            from psycopg import sql as psycopg_sql
        except ImportError as exc:
            raise ImportError("Install postgres extras: pip install '.[postgres]'") from exc
        self.psycopg = psycopg
        self.psycopg_sql = psycopg_sql
        self.conn = psycopg.connect(dsn)

    def __enter__(self) -> PostgresExporter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.conn.close()

    def _sql_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, int):
            return "BIGINT"
        if isinstance(value, float):
            return "DOUBLE PRECISION"
        return "TEXT"

    def upsert_batches(self, batches: Iterable[list[dict[str, Any]]], table: str, conflict_column: str) -> int:
        """Insert or update record batches into a Postgres table using ON CONFLICT DO UPDATE."""
        total = 0
        cur = self.conn.cursor()
        initialized = False
        for batch in batches:
            if not batch:
                continue
            cols = list(batch[0].keys())
            if not initialized:
                defs = ", ".join(f'"{c}" {self._sql_type(batch[0].get(c))}' for c in cols)
                cur.execute(
                    self.psycopg_sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                        self.psycopg_sql.Identifier(table),
                        self.psycopg_sql.SQL(defs),
                    )
                )
                if conflict_column in cols:
                    cur.execute(
                        self.psycopg_sql.SQL(
                            "CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} ({})"
                        ).format(
                            self.psycopg_sql.Identifier(f"{table}_{conflict_column}_idx"),
                            self.psycopg_sql.Identifier(table),
                            self.psycopg_sql.Identifier(conflict_column),
                        )
                    )
                initialized = True
            placeholders = ", ".join(["%s"] * len(cols))
            col_list = ", ".join(f'"{c}"' for c in cols)
            updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in cols if c != conflict_column)
            if updates:
                sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict_column}") DO UPDATE SET {updates}'
            else:
                sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict_column}") DO NOTHING'
            values = [tuple(row.get(c) for c in cols) for row in batch]
            cur.executemany(sql, values)
            total += len(values)
        self.conn.commit()
        return total

    def copy_upsert_batches(self, batches: Iterable[list[dict[str, Any]]], table: str, conflict_column: str) -> int:
        """Bulk-load batches using COPY into a temp table and upsert into the target.

        This method attempts to use Postgres COPY for speed. If COPY is not
        available or an error occurs, it falls back to `upsert_batches` per-batch.
        """
        total = 0
        cur = self.conn.cursor()
        initialized = False
        for batch in batches:
            if not batch:
                continue
            cols = list(batch[0].keys())
            if not initialized:
                defs = ", ".join(f'"{c}" {self._sql_type(batch[0].get(c))}' for c in cols)
                cur.execute(
                    self.psycopg_sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                        self.psycopg_sql.Identifier(table),
                        self.psycopg_sql.SQL(defs),
                    )
                )
                if conflict_column in cols:
                    cur.execute(
                        self.psycopg_sql.SQL(
                            "CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} ({})"
                        ).format(
                            self.psycopg_sql.Identifier(f"{table}_{conflict_column}_idx"),
                            self.psycopg_sql.Identifier(table),
                            self.psycopg_sql.Identifier(conflict_column),
                        )
                    )
                initialized = True

            # Create a temp staging table with the same columns
            tmp = f"tmp_{uuid.uuid4().hex[:8]}"
            cur.execute(f'CREATE TEMP TABLE "{tmp}" ({defs}) ON COMMIT DROP')

            # Write CSV into the temp table using COPY
            try:
                # Build an in-memory CSV representation and feed it into COPY.
                # The psycopg cursor `copy` method may accept a file-like object.
                import csv
                import io

                s = io.StringIO()
                writer = csv.writer(s)
                for row in batch:
                    writer.writerow([row.get(c) for c in cols])
                s.seek(0)
                cols_quoted = ", ".join(f'"{c}"' for c in cols)
                copy_sql = f'COPY "{tmp}" ({cols_quoted}) FROM STDIN WITH CSV'
                # psycopg cursor copy may accept a file-like; if it doesn't this
                # block will raise and we fall back to the safe executemany path.
                cur.copy(copy_sql, s)

                # Use a single INSERT ... SELECT from the staging table into the
                # target table with ON CONFLICT to perform the upsert in SQL.
                col_list = ", ".join(f'"{c}"' for c in cols)
                updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in cols if c != conflict_column)
                if updates:
                    sql = f'INSERT INTO "{table}" ({col_list}) SELECT {col_list} FROM "{tmp}" ON CONFLICT ("{conflict_column}") DO UPDATE SET {updates}'
                else:
                    sql = f'INSERT INTO "{table}" ({col_list}) SELECT {col_list} FROM "{tmp}" ON CONFLICT ("{conflict_column}") DO NOTHING'
                cur.execute(sql)
                total += len(batch)
            except Exception:
                # Fallback to safe path
                self.conn.rollback()
                total += self.upsert_batches([batch], table, conflict_column)
        self.conn.commit()
        return total

    def upsert_metadata(self, meta: Any) -> None:
        """Upsert a metadata summary into the _socrata_metadata table keyed by fourfour."""
        cur = self.conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS _socrata_metadata (fourfour TEXT PRIMARY KEY, payload JSONB NOT NULL)')
        cur.execute(
            'INSERT INTO _socrata_metadata (fourfour, payload) VALUES (%s, %s) ON CONFLICT (fourfour) DO UPDATE SET payload = EXCLUDED.payload',
            (meta.fourfour, self.psycopg.types.json.Json(meta.summary())),
        )
        self.conn.commit()


class MongoExporter:
    def __init__(self, uri: str, db_name: str):
        try:
            from pymongo import MongoClient, UpdateOne
        except ImportError as exc:
            raise ImportError("Install mongo extras: pip install '.[mongo]'") from exc
        self.UpdateOne = UpdateOne
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def __enter__(self) -> MongoExporter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.client.close()

    def upsert_batches(self, batches: Iterable[list[dict[str, Any]]], collection: str, conflict_field: str) -> int:
        """Upsert record batches into a MongoDB collection using bulk_write."""
        col = self.db[collection]
        total = 0
        for batch in batches:
            ops = [self.UpdateOne({conflict_field: doc.get(conflict_field)}, {"$set": doc}, upsert=True) for doc in batch]
            if ops:
                col.bulk_write(ops, ordered=False)
                total += len(ops)
        return total

    def upsert_geojson(self, geojson: dict[str, Any], collection: str, conflict_field: str) -> int:
        """Upsert GeoJSON feature properties (plus geometry) into a MongoDB collection."""
        col = self.db[collection]
        ops = []
        for feat in geojson.get("features", []):
            props = feat.get("properties", {}).copy()
            props["geometry"] = feat.get("geometry")
            ops.append(self.UpdateOne({conflict_field: props.get(conflict_field)}, {"$set": props}, upsert=True))
        if ops:
            col.bulk_write(ops, ordered=False)
        return len(ops)
