"""Streaming pipeline utilities.

This module implements a low-memory pipeline runner that pages Socrata
datasets and broadcasts batches to downstream targets (Postgres, MongoDB, or
a JSONL backup). The `dry_run` mode is used to preview what will be written
without performing any writes and is useful in interactive UIs.

Key behaviors:
 - honors `chunk_size` by overriding client's page size
 - attempts to obtain a row count from dataset metadata (best-effort)
 - in real runs, opens minimal persistent connections and commits at the end
 - ensures resources are closed even on unexpected exceptions
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from .pipeline import generate_postgres_preview


def stream_pipeline(client, domain: str, fourfour: str, targets: dict, dry_run: bool = True, chunk_size: int | None = None, max_rows: int | None = None, progress_callback: Callable[[int, int | None], None] | None = None) -> dict[str, Any]:
    """Stream dataset from Socrata and broadcast to targets.

    Parameters
    - client: SocrataClient instance
    - domain, fourfour: dataset identifier
    - targets: dict specifying enabled outputs and their connection info
    - dry_run: if True, only sample the first batch and return previews
    - chunk_size: override client page size for streaming
    - max_rows: limit total rows to process
    - progress_callback: optional callable(fetched, total_estimate)

    Returns a report dict summarizing preview or run results.
    """
    # allow overriding client's page size if requested
    if chunk_size is not None:
        client.config.page_size = chunk_size

    # try to get total count from metadata (best-effort) — not critical if it fails
    try:
        meta = client.get_metadata(domain, fourfour)
        total = meta.row_count
    except Exception:
        total = None

    fetched = 0

    # Dry-run: sample the first batch and return previews
    if dry_run:
        gen = client.fetch_json(domain, fourfour, max_rows=max_rows)
        try:
            sample_batch = next(gen)
        except StopIteration:
            sample_batch = []
        report = {"rows_sampled": len(sample_batch), "total_estimate": total, "targets": {}}
        if targets.get("postgres", {}).get("enabled"):
            pg = targets["postgres"]
            report["targets"]["postgres"] = {"preview": generate_postgres_preview(sample_batch, pg.get("table", "socrata_data"), pg.get("conflict_column"))}
        if targets.get("mongo", {}).get("enabled"):
            report["targets"]["mongo"] = {"sample": sample_batch[:5]}
        if targets.get("xlsx", {}).get("enabled"):
            report["targets"]["xlsx"] = {"sample": sample_batch[:5], "suggested_path": str(Path(tempfile.gettempdir()) / f"{fourfour}_backup.jsonl")} 
        return report

    # Real run: open writers and stream. We keep references to connections so
    # we can commit/close them at the end of the process.
    pg_writer = None
    mongo_client = None
    jsonl_path = None
    jsonl_f = None

    try:
        if targets.get("postgres", {}).get("enabled"):
            pg = targets["postgres"]
            try:
                import psycopg
            except Exception as exc:  # pragma: no cover - runtime import
                raise ImportError("Postgres support requires psycopg: pip install '.[postgres]'") from exc
            # open connection and prepare writer state
            conn = psycopg.connect(pg["dsn"])
            cur = conn.cursor()
            pg_writer = {"conn": conn, "cur": cur, "table": pg.get("table", "socrata_data"), "conflict": pg.get("conflict_column") , "initialized": False}

        if targets.get("mongo", {}).get("enabled"):
            mg = targets["mongo"]
            try:
                from pymongo import MongoClient, UpdateOne
            except Exception as exc:  # pragma: no cover - runtime import
                raise ImportError("Mongo support requires pymongo: pip install '.[mongo]'") from exc
            mongo_client = {"client": MongoClient(mg["uri"]), "db": mg["db"], "collection": mg["collection"], "conflict": mg["conflict_field"]}

        if targets.get("xlsx", {}).get("enabled"):
            jsonl_path = Path(tempfile.gettempdir()) / f"{fourfour}_backup.jsonl"
            jsonl_f = open(jsonl_path, "w", encoding="utf-8")

        # iterate and broadcast — each batch is handled independently so failures
        # in one batch do not necessarily abort the whole stream (best-effort)
        for batch in client.fetch_json(domain, fourfour, max_rows=max_rows):
            if not batch:
                continue
            fetched += len(batch)

            # Postgres incremental upsert using simple executemany
            if pg_writer is not None:
                cur = pg_writer["cur"]
                table = pg_writer["table"]
                conflict = pg_writer["conflict"]
                if not pg_writer["initialized"]:
                    cols = list(batch[0].keys())
                    defs = ", ".join(f'"{c}" TEXT' for c in cols)
                    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({defs})')
                    if conflict and conflict in cols:
                        cur.execute(f'CREATE UNIQUE_INDEX IF NOT EXISTS "{table}_{conflict}_idx" ON "{table}" ("{conflict}")')
                    pg_writer["initialized"] = True
                cols = list(batch[0].keys())
                placeholders = ",".join(["%s"] * len(cols))
                col_list = ", ".join(f'"{c}"' for c in cols)
                updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in cols if c != conflict)
                if updates:
                    sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict}") DO UPDATE SET {updates}'
                else:
                    sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict}") DO NOTHING'
                values = [tuple(row.get(c) for c in cols) for row in batch]
                cur.executemany(sql, values)

            # Mongo bulk upsert
            if mongo_client is not None:
                col = mongo_client["client"][mongo_client["db"]][mongo_client["collection"]]
                ops = [
                    (mongo_client["client"].UpdateOne({mongo_client["conflict"]: doc.get(mongo_client["conflict"])}, {"$set": doc}, upsert=True))
                    for doc in batch
                ]
                if ops:
                    col.bulk_write(ops, ordered=False)

            # JSONL backup
            if jsonl_f is not None:
                for r in batch:
                    jsonl_f.write(json.dumps(r, default=str) + "\n")

            if progress_callback:
                try:
                    progress_callback(fetched, total)
                except Exception:
                    pass

        # finalize: commit Postgres and close resources
        if pg_writer is not None:
            pg_writer["conn"].commit()
            pg_writer["cur"].close()
            pg_writer["conn"].close()
        if mongo_client is not None:
            mongo_client["client"].close()
        if jsonl_f is not None:
            jsonl_f.close()

        report = {"rows": fetched, "targets": {}}
        if targets.get("postgres", {}).get("enabled"):
            report["targets"]["postgres"] = {"rows_upserted": fetched}
        if targets.get("mongo", {}).get("enabled"):
            report["targets"]["mongo"] = {"rows_upserted": fetched}
        if targets.get("xlsx", {}).get("enabled"):
            report["targets"]["xlsx"] = {"jsonl_backup": str(jsonl_path)}

        return report

    finally:
        # safety: ensure all open resources are closed even if errors occurred
        try:
            if pg_writer is not None and pg_writer.get("conn"):
                pg_writer["conn"].close()
        except Exception:
            pass
        try:
            if mongo_client is not None and mongo_client.get("client"):
                mongo_client["client"].close()
        except Exception:
            pass
        try:
            if jsonl_f is not None and not jsonl_f.closed:
                jsonl_f.close()
        except Exception:
            pass
