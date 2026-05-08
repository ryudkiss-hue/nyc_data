"""Nightly job example: delta fetch, copy-upsert, permit lookahead, alert dispatch.

This is an opinionated example designed as a starting point for your scheduler
(cron, Airflow, Kubernetes CronJob). It expects environment variables or a small
YAML config providing DSNs and endpoints.

The script is intentionally conservative: it runs best-effort sequences and
emits alerts via the AlertManager. Adapt to your production orchestration.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime

from socrata_toolkit.client import SocrataClient, SocrataConfig
from socrata_toolkit.exporters import PostgresExporter
from socrata_toolkit.ops import permit_lookahead_sql
from socrata_toolkit.conflict import PostGISConflictResolver
from socrata_toolkit.alerts import AlertManager, CLINotifier, EmailNotifier


def load_config(path: Path | None = None):
    # Simple JSON file config for demo. Keys: pg_dsn, domain, fourfour, smtp
    if path is None:
        return {
            "pg_dsn": os.getenv("PG_DSN"),
            "domain": os.getenv("SOCRATA_DOMAIN"),
            "fourfour": os.getenv("SOCRATA_4X4"),
        }
    return json.loads(path.read_text())


def run_nightly(config_path: str | None = None):
    cfg = load_config(Path(config_path) if config_path else None)
    pg_dsn = cfg.get("pg_dsn")
    domain = cfg.get("domain")
    fourfour = cfg.get("fourfour")

    # Setup alert manager (console + optional email)
    mgr = AlertManager(batch_mode=False)
    mgr.register(CLINotifier())
    smtp = cfg.get("smtp")
    if smtp:
        mgr.register(EmailNotifier(smtp))

    # Example: fetch new rows since last run using a simple high-watermark file
    hwm_file = Path(".last_run_hwm")
    last_ts = None
    if hwm_file.exists():
        last_ts = hwm_file.read_text().strip()

    client = SocrataClient(SocrataConfig())
    # If we have a last_ts, fetch deltas via fetch_since; otherwise fetch a small sample
    if last_ts:
        gen = client.fetch_since(domain, fourfour, updated_col="updated_at", since=last_ts)
    else:
        gen = client.fetch_json(domain, fourfour, max_rows=1000)

    rows = []
    for batch in gen:
        rows.extend(batch)

    # Upsert via Postgres COPY path for speed
    if pg_dsn and rows:
        with PostgresExporter(pg_dsn) as pg:
            pg.copy_upsert_batches([rows], table="socrata_ingest", conflict_column="id")

    # Run permit lookahead to identify imminent permit conflicts (90 days)
    try:
        resolver = PostGISConflictResolver(pg_dsn)
        df, summary = resolver.resolve_conflicts(proposed_table="socrata_ingest", reference_table="permits", proposed_id_col="id", proposed_geom_col="geom", reference_id_col="permit_id", reference_geom_col="geom", buffer_m=20.0)
        if summary.total_conflicts:
            # Emit a single summary alert for now
            mgr.emit(Alert(severity="critical", message=f"{summary.total_conflicts} permit conflicts detected", payload={"conflict_summary": summary.__dict__}))
        resolver.close()
    except Exception as exc:
        mgr.emit(Alert(severity="warning", message="Permit lookahead failed", payload={"error": str(exc)}))

    # Update high-watermark as now
    now = datetime.utcnow().isoformat()
    hwm_file.write_text(now)
    mgr.emit(Alert(severity="info", message="Nightly job complete", payload={"rows": len(rows)}))


if __name__ == "__main__":
    run_nightly(None)
