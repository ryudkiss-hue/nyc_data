"""Nightly job example: delta fetch, copy-upsert, permit lookahead, alert dispatch."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from socrata_toolkit.sql.conflict import PostGISConflictResolver

from socrata_toolkit.alerts import Alert, AlertManager, CLINotifier, EmailNotifier
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.core.exporters import PostgresExporter

def load_config(path: Path | None = None) -> dict[str, Any]:
    """Loads configuration from environment or JSON file."""
    if path is None:
        return {
            "pg_dsn": os.getenv("PG_DSN"),
            "domain": os.getenv("SOCRATA_DOMAIN"),
            "fourfour": os.getenv("SOCRATA_4X4"),
        }
    with open(path, encoding="utf-8") as f:
        config_data = json.load(f)
        return cast(dict[str, Any], config_data)

def run_nightly(config_path: str | None = None) -> None:
    """Runs the nightly ingest and conflict resolution sequence."""
    cfg = load_config(Path(config_path) if config_path else None)

    pg_dsn = str(cfg.get("pg_dsn") or "")
    domain = str(cfg.get("domain") or "")
    fourfour = str(cfg.get("fourfour") or "")

    mgr = AlertManager(batch_mode=False)
    mgr.register(CLINotifier())

    smtp_cfg = cfg.get("smtp")
    if isinstance(smtp_cfg, dict):
        mgr.register(EmailNotifier(cast(dict[str, Any], smtp_cfg)))

    if not domain or not fourfour:
        mgr.emit(Alert(severity="critical", message="Missing Socrata config"))
        return

    hwm_file = Path(".last_run_hwm")
    last_ts = hwm_file.read_text(encoding="utf-8").strip() if hwm_file.exists() else None

    client = SocrataClient(SocrataConfig())

    if last_ts:
        gen = client.fetch_since(domain, fourfour, updated_col="updated_at", since=last_ts)
    else:
        gen = client.fetch_json(domain, fourfour, max_rows=1000)

    rows: list[dict[str, Any]] = []
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
                buffer_m=20.0,
            )
            if summary.total_conflicts:
                mgr.emit(
                    Alert(
                        severity="warning",
                        message=f"Spatial conflicts detected: {summary.total_conflicts}",
                    )
                )
    except Exception as exc:
        mgr.emit(Alert(severity="warning", message=f"Conflict resolution skipped: {exc}"))

    hwm_file.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    mgr.emit(
        Alert(
            severity="info",
            message=f"Nightly ingest complete ({len(rows)} rows)",
        )
    )

if __name__ == "__main__":
    run_nightly()
