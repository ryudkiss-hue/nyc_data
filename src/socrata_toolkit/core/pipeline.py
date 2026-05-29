"""In-memory pipeline runner and preview utilities.

This module provides a lightweight API for previewing and running simple
pipelines that take an in-memory list of rows and dispatch them to multiple
targets (Postgres, Mongo, XLSX). The preview capability is used extensively in
the Streamlit Workbench to show example SQL, sample rows, and ensure safe
operations before executing writes.
"""

from __future__ import annotations

from typing import Any

from .exporters import MongoExporter, PostgresExporter, XLSXExporter


def _sql_type(value: Any) -> str:
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int) and not isinstance(value, bool):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE PRECISION"
    return "TEXT"


def _collect_columns_and_types(rows: list[dict[str, Any]], sample_n: int = 10) -> dict[str, str]:
    cols = {}
    if not rows:
        return cols
    # examine up to sample_n rows to infer types
    for r in rows[:sample_n]:
        for k, v in r.items():
            if k in cols:
                continue
            if v is None:
                continue
            cols[k] = _sql_type(v)
    # fallback for keys that had only None values
    all_keys = set().union(*(r.keys() for r in rows))
    for k in all_keys:
        if k not in cols:
            cols[k] = "TEXT"
    return cols


def generate_postgres_preview(rows: list[dict[str, Any]], table: str, conflict_col: str | None = None) -> dict:
    cols = _collect_columns_and_types(rows)
    if not cols:
        return {"create_table": "-- no rows to infer schema", "insert_example": "-- none"}
    cols_defs = ", ".join(f'"{c}" {t}' for c, t in cols.items())
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({cols_defs});'
    index_sql = ""
    if conflict_col and conflict_col in cols:
        index_sql = f'CREATE UNIQUE INDEX IF NOT EXISTS "{table}_{conflict_col}_idx" ON "{table}" ("{conflict_col}");'
    # sample insert
    sample = rows[0]
    cols_list = ", ".join(f'"{c}"' for c in sample.keys())
    placeholders = ", ".join(["%s"] * len(sample.keys()))
    updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in sample.keys() if c != conflict_col)
    if updates:
        insert_sql = f'INSERT INTO "{table}" ({cols_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict_col}") DO UPDATE SET {updates};'
    else:
        insert_sql = f'INSERT INTO "{table}" ({cols_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict_col}") DO NOTHING;'
    return {"create_table": create_sql, "index": index_sql, "insert_example": insert_sql, "sample_row": sample}


def run_from_rows(rows: list[dict[str, Any]], targets: dict, dry_run: bool = True) -> dict:
    """Run a pipeline from an in-memory list of rows.

    targets: dict with optional keys: 'postgres', 'mongo', 'xlsx'.
    Each target value is a dict with necessary connection params.
    """
    # Build a human-readable report that describes previews and actions taken.
    report: dict[str, Any] = {"rows": len(rows), "targets": {}}

    # Postgres
    pg = targets.get("postgres")
    if pg and pg.get("enabled"):
        preview = generate_postgres_preview(rows, pg.get("table", "socrata_data"), pg.get("conflict_column"))
        report["targets"]["postgres"] = {"preview": preview}
        if not dry_run:
            with PostgresExporter(pg["dsn"]) as pge:
                total = pge.upsert_batches([rows], table=pg.get("table", "socrata_data"), conflict_column=pg.get("conflict_column"))
            report["targets"]["postgres"]["rows_upserted"] = total

    # Mongo
    mg = targets.get("mongo")
    if mg and mg.get("enabled"):
        sample = rows[:5]
        report["targets"]["mongo"] = {"sample": sample, "count": len(rows)}
        if not dry_run:
            with MongoExporter(mg["uri"], mg["db"]) as mge:
                if mg.get("geojson") and mg.get("geojson_payload"):
                    total = mge.upsert_geojson(mg["geojson_payload"], collection=mg.get("collection"), conflict_field=mg.get("conflict_field"))
                else:
                    total = mge.upsert_batches([rows], collection=mg.get("collection"), conflict_field=mg.get("conflict_field"))
            report["targets"]["mongo"]["rows_upserted"] = total

    # XLSX
    xl = targets.get("xlsx")
    if xl and xl.get("enabled"):
        sample = rows[:5]
        report["targets"]["xlsx"] = {"filename": xl.get("path", "socrata_backup.xlsx"), "count": len(rows), "sample": sample}
        if not dry_run:
            XLSXExporter().write(rows, xl.get("path", "socrata_backup.xlsx"))
            report["targets"]["xlsx"]["written"] = True

    return report
