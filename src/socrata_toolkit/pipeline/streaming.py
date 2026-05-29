"""Streaming pipeline utilities with integrated data governance.

Streaming pipeline with optional governance processor integration for:
- Schema validation and versioning
- Change data capture (CDC) and audit logging
- Data lineage tracking
- Design rule compliance checking
"""

from __future__ import annotations

import json
import logging
import tempfile
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.pipeline import generate_postgres_preview

logger = logging.getLogger(__name__)

try:
    from ..cdc.engine import CDCEvent
except ImportError:
    CDCEvent = None  # type: ignore


def stream_pipeline(
    client,
    domain: str,
    fourfour: str,
    targets: dict,
    dry_run: bool = True,
    chunk_size: int | None = None,
    max_rows: int | None = None,
    progress_callback: Callable[[int, int | None], None] | None = None,
    governance_processor: Any | None = None,
) -> dict[str, Any]:

    if chunk_size is not None:
        client.config.page_size = chunk_size

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
            report["targets"]["postgres"] = {
                "preview": generate_postgres_preview(sample_batch, pg.get("table", "socrata_data"), pg.get("conflict_column"))
            }
        if targets.get("mongo", {}).get("enabled"):
            report["targets"]["mongo"] = {"sample": sample_batch[:5]}
        if targets.get("xlsx", {}).get("enabled"):
            # Note: Streaming defaults to JSONL to prevent memory exhaustion
            report["targets"]["xlsx"] = {
                "sample": sample_batch[:5],
                "suggested_path": str(Path(tempfile.gettempdir()) / f"{fourfour}_backup.jsonl")
            }
        return report

    pg_writer = None
    mongo_client = None
    jsonl_path = None
    jsonl_f = None

    try:
        if targets.get("postgres", {}).get("enabled"):
            pg = targets["postgres"]
            try:
                import psycopg
            except Exception as exc:
                raise ImportError("Postgres support requires psycopg: pip install '.[postgres]'") from exc

            conn = psycopg.connect(pg["dsn"])
            cur = conn.cursor()
            pg_writer = {"conn": conn, "cur": cur, "table": pg.get("table", "socrata_data"), "conflict": pg.get("conflict_column"), "initialized": False}

        if targets.get("mongo", {}).get("enabled"):
            mg = targets["mongo"]
            try:
                from pymongo import MongoClient, UpdateOne
            except Exception as exc:
                raise ImportError("Mongo support requires pymongo: pip install '.[mongo]'") from exc
            # Ensure UpdateOne is attached so it can be used in the loop
            mongo_client = {
                "client": MongoClient(mg["uri"]),
                "db": mg["db"],
                "collection": mg["collection"],
                "conflict": mg["conflict_field"],
                "UpdateOne": UpdateOne  # Store reference for ease of use
            }

        if targets.get("xlsx", {}).get("enabled"):
            jsonl_path = Path(tempfile.gettempdir()) / f"{fourfour}_backup.jsonl"
            jsonl_f = open(jsonl_path, "w", encoding="utf-8")

        for batch in client.fetch_json(domain, fourfour, max_rows=max_rows):
            if not batch:
                continue
            fetched += len(batch)

            # Emit CDC events for governance processing (schema, lineage, compliance)
            if governance_processor and CDCEvent:
                for row in batch:
                    try:
                        # Create CDC event for governance validation
                        cdc_event = CDCEvent(
                            event_id=str(uuid.uuid4()),
                            source_dataset=fourfour,
                            operation="INSERT",  # Streaming pipeline is ingestion
                            record_id=str(row.get("id", row.get("@id", uuid.uuid4()))),
                            timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
                            after=row,
                            metadata={"source_domain": domain},
                        )
                        # Process through governance (validates schema, enriches lineage, checks compliance)
                        governance_processor.process_event(cdc_event)
                    except Exception as e:
                        logger.warning(f"Governance event processing skipped: {e}")

            # Postgres incremental upsert using simple executemany
            if pg_writer is not None:
                cur = pg_writer["cur"]
                # Sanitize identifiers by removing quotes to prevent SQL injection issues
                table = pg_writer["table"].replace('"', '')
                conflict = pg_writer["conflict"].replace('"', '') if pg_writer["conflict"] else None

                if not pg_writer["initialized"]:
                    cols = list(batch[0].keys())
                    defs = ", ".join(f'"{c.replace(chr(34), "")}" TEXT' for c in cols)
                    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({defs})')
                    if conflict and conflict in cols:
                        # FIX: Changed UNIQUE_INDEX to UNIQUE INDEX
                        cur.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "{table}_{conflict}_idx" ON "{table}" ("{conflict}")')
                    pg_writer["initialized"] = True

                cols = list(batch[0].keys())
                placeholders = ",".join(["%s"] * len(cols))
                col_list = ", ".join(f'"{c.replace(chr(34), "")}"' for c in cols)

                if conflict:
                    updates = ", ".join(f'"{c.replace(chr(34), "")}" = EXCLUDED."{c.replace(chr(34), "")}"' for c in cols if c != conflict)
                    if updates:
                        sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict}") DO UPDATE SET {updates}'
                    else:
                        sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) ON CONFLICT ("{conflict}") DO NOTHING'
                else:
                    # Fallback if no conflict key provided
                    sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

                values = [tuple(row.get(c) for c in cols) for row in batch]
                cur.executemany(sql, values)

            # Mongo bulk upsert
            if mongo_client is not None:
                col = mongo_client["client"][mongo_client["db"]][mongo_client["collection"]]
                UpdateOneClass = mongo_client["UpdateOne"]
                conflict_f = mongo_client["conflict"]

                # FIX: Use UpdateOne class directly, not as an attribute of MongoClient
                ops = [
                    UpdateOneClass({conflict_f: doc.get(conflict_f)}, {"$set": doc}, upsert=True)
                    for doc in batch if doc.get(conflict_f) is not None
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
        # safety: ensure all open resources are closed
        try:
            if pg_writer is not None and not pg_writer["conn"].closed:
                pg_writer["conn"].close()
        except Exception:
            pass
        try:
            if mongo_client is not None:
                mongo_client["client"].close()
        except Exception:
            pass
        try:
            if jsonl_f is not None and not jsonl_f.closed:
                jsonl_f.close()
        except Exception:
            pass
