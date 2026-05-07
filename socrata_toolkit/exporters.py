from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


class XLSXExporter:
    def write(self, data: pd.DataFrame | list[dict[str, Any]], path: str, sheet: str = "Data", meta: Any = None, freeze_panes: bool = True, auto_filter: bool = True) -> None:
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


class PostgresExporter:
    def __init__(self, dsn: str):
        try:
            import psycopg
        except ImportError as exc:
            raise ImportError("Install postgres extras: pip install '.[postgres]'") from exc
        self.psycopg = psycopg
        self.conn = psycopg.connect(dsn)

    def __enter__(self) -> "PostgresExporter":
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
        total = 0
        cur = self.conn.cursor()
        initialized = False
        for batch in batches:
            if not batch:
                continue
            cols = list(batch[0].keys())
            if not initialized:
                defs = ", ".join(f'"{c}" {self._sql_type(batch[0].get(c))}' for c in cols)
                cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({defs})')
                if conflict_column in cols:
                    cur.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "{table}_{conflict_column}_idx" ON "{table}" ("{conflict_column}")')
                initialized = True
            placeholders = ", ".join(["%s"] * len(cols))
            col_list = ", ".join(f'"{c}"' for c in cols)
            updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in cols if c != conflict_column)
            sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict_column}") DO UPDATE SET {updates}'
            values = [tuple(row.get(c) for c in cols) for row in batch]
            cur.executemany(sql, values)
            total += len(values)
        self.conn.commit()
        return total

    def upsert_metadata(self, meta: Any) -> None:
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

    def __enter__(self) -> "MongoExporter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.client.close()

    def upsert_batches(self, batches: Iterable[list[dict[str, Any]]], collection: str, conflict_field: str) -> int:
        col = self.db[collection]
        total = 0
        for batch in batches:
            ops = [self.UpdateOne({conflict_field: doc.get(conflict_field)}, {"$set": doc}, upsert=True) for doc in batch]
            if ops:
                col.bulk_write(ops, ordered=False)
                total += len(ops)
        return total

    def upsert_geojson(self, geojson: dict[str, Any], collection: str, conflict_field: str) -> int:
        col = self.db[collection]
        ops = []
        for feat in geojson.get("features", []):
            props = feat.get("properties", {}).copy()
            props["geometry"] = feat.get("geometry")
            ops.append(self.UpdateOne({conflict_field: props.get(conflict_field)}, {"$set": props}, upsert=True))
        if ops:
            col.bulk_write(ops, ordered=False)
        return len(ops)
