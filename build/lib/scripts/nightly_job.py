"""Nightly job example: delta fetch, copy-upsert, permit lookahead, alert dispatch."""
from __future__ import annotations

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, cast # Added 'cast' for strict typing

from socrata_toolkit.client import SocrataClient, SocrataConfig
from socrata_toolkit.exporters import PostgresExporter
from socrata_toolkit.conflict import PostGISConflictResolver
from socrata_toolkit.alerts import AlertManager, CLINotifier, EmailNotifier, Alert

def load_config(path: Path | None = None) -> Dict[str, Any]:
    """Loads configuration from environment or JSON file."""
    if path is None:
        return {
            "pg_dsn": os.getenv("PG_DSN"),
            "domain": os.getenv("SOCRATA_DOMAIN"),
            "fourfour": os.getenv("SOCRATA_4X4"),
        }
    with open(path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        return cast(Dict[str, Any], config_data)

def run_nightly(config_path: str | None = None) -> None:
    """Runs the nightly ingest and conflict resolution sequence."""
    cfg = load_config(Path(config_path) if config_path else None)
    
    # Force types to string to satisfy Pylance reportArgumentType
    pg_dsn = str(cfg.get("pg_dsn") or "")
    domain = str(cfg.get("domain") or "")
    fourfour = str(cfg.get("fourfour") or "")

    mgr = AlertManager(batch_mode=False)
    mgr.register(CLINotifier())
    
    # Handle SMTP specifically to avoid "str | Any" mapping errors
    smtp_cfg = cfg.get("smtp")
    if isinstance(smtp_cfg, dict):
        mgr.register(EmailNotifier(cast(Dict[str, Any], smtp_cfg)))

    # Guard clause: stop if we don't have what we need
    if not domain or not fourfour:
        mgr.emit(Alert(severity="critical", message="Missing Socrata config"))
        return

    hwm_file = Path(".last_run_hwm")
    last_ts = hwm_file.read_text(encoding="utf-8").strip() if hwm_file.exists() else None

    client = SocrataClient(SocrataConfig())
    
    # Logic for fetch - Pylance now knows these are valid strings
    if last_ts:
        gen = client.fetch_since(domain, fourfour, updated_col="updated_at", since=last_ts)
    else:
        gen = client.fetch_json(domain, fourfour, max_rows=1000)

    rows: list[Dict[str, Any]] = []
    for batch in gen:
        rows.extend(batch)

    if pg_dsn and rows:
        with PostgresExporter(pg_dsn) as pg:
            pg.copy_upsert_batches([rows], table="socrata_ingest", conflict_column="id")

    try:
        if pg_dsn:
            resolver = PostGISConflictResolver(pg_dsn)
            _, summary = resolver.resolve_conflicts(
                proposed_table="socrata_ingest",
                reference_table="permits",
                proposed_id_col="id",
                proposed_geom_col="geom",
                reference_id_col="permit_id",
                reference_geom_col="geom",
                buffer_m=20.0
            )
            if summary.total_conflicts:
                mgr.emit(Alert(
                    severity="critical",
                    message=f"{summary.total_conflicts} permit conflicts detected",
                    payload=summary.__dict__
                ))
            resolver.close()
    except Exception as exc: # pylint: disable=broad-exception-caught
        mgr.emit(Alert(severity="warning", message="Conflict check failed", payload={"error": str(exc)}))

    now = datetime.utcnow().isoformat()
    hwm_file.write_text(now, encoding="utf-8")
    mgr.emit(Alert(severity="info", message="Job complete", payload={"rows": len(rows)}))

if __name__ == "__main__":
    run_nightly(None)


    rows = []
    for batch in gen:
        rows.extend(batch)

    if pg_dsn and rows:
        with PostgresExporter(pg_dsn) as pg:
            pg.copy_upsert_batches([rows], table="socrata_ingest", conflict_column="id")

    try:
        if pg_dsn:
            resolver = PostGISConflictResolver(pg_dsn)
            # Fix: Use 'summary' directly (df was unused) to clear W0612
            _, summary = resolver.resolve_conflicts(
                proposed_table="socrata_ingest",
                reference_table="permits",
                proposed_id_col="id",
                proposed_geom_col="geom",
                reference_id_col="permit_id",
                reference_geom_col="geom",
                buffer_m=20.0
            )
            if summary.total_conflicts:
                mgr.emit(Alert(
                    severity="critical",
                    message=f"{summary.total_conflicts} permit conflicts detected",
                    payload={"conflict_summary": summary.__dict__}
                ))
            resolver.close()
    except Exception as exc: # pylint: disable=broad-exception-caught
        mgr.emit(Alert(
            severity="warning",
            message="Permit lookahead failed",
            payload={"error": str(exc)}
        ))

    now = datetime.utcnow().isoformat()
    # Fix: Added encoding to clear W1514
    hwm_file.write_text(now, encoding="utf-8")
    mgr.emit(Alert(
        severity="info",
        message="Nightly job complete",
        payload={"rows": len(rows)}
    ))


if __name__ == "__main__":
    run_nightly(None)
