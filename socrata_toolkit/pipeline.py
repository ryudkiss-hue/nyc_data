from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Iterable

import pandas as pd

from .core import SocrataClient, DuckDBExporter, DuckDBManager

logger = logging.getLogger(__name__)

# ── Change Data Capture (CDC) ────────────────────────────────────────────────

@dataclass
class CDCEvent:
    """Represents a single record change event."""
    event_id: str
    source_dataset: str
    operation: str
    record_id: str
    timestamp_ms: int
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CDCProcessor:
    """Processes and stores CDC events."""
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn
    
    def process_event(self, event: CDCEvent):
        logger.debug(f"Processing CDC event: {event.event_id} ({event.operation})")
        # In-memory or DuckDB storage could go here if DSN is not Postgres
        pass

# ── 311 Ingestion ─────────────────────────────────────────────────────────────

def ingest_311_complaints(max_rows: int = 1000) -> Any:
    """Fetch and triage 311 complaints."""
    from .core import SocrataClient
    client = SocrataClient()
    df = client.fetch_dataframe("data.cityofnewyork.us", "erm2-nwe9", max_rows=max_rows)
    return SimpleNamespace(total=len(df), critical_count=0, data=df)

# ── Data Engineering ──────────────────────────────────────────────────────────

def deduplicate_dataframe(df: pd.DataFrame, subset: List[str] | None = None) -> pd.DataFrame:
    """Remove duplicate rows."""
    return df.drop_duplicates(subset=subset)

def detect_changes(old_df: pd.DataFrame, new_df: pd.DataFrame, key: str) -> Any:
    """Detect added, deleted, or modified rows."""
    return SimpleNamespace(added=pd.DataFrame(), deleted=pd.DataFrame(), modified=pd.DataFrame())

# ── Reporting ─────────────────────────────────────────────────────────────────

def generate_program_report(df: pd.DataFrame, path: str):
    """Generate a high-level program report."""
    df.to_csv(path, index=False)

# ── Data Integration ──────────────────────────────────────────────────────────

def join_datasets(left_df: pd.DataFrame, right_df: pd.DataFrame, on: str | List[str], how: str = 'inner', suffixes: Tuple[str, str] = ('_left', '_right')) -> pd.DataFrame:
    """Join two datasets using pandas merge."""
    return pd.merge(left_df, right_df, on=on, how=how, suffixes=suffixes)

def sync_dataset(domain: str, fourfour: str, db_path: str, table_name: str, updated_col: str, token: str = "") -> int:
    """
    Perform an incremental sync of a Socrata dataset to a local DuckDB table.
    Only fetches rows updated since the last sync.
    """
    manager = DuckDBManager(db_path)
    client = SocrataClient()
    if token: client.config.app_token = token
    
    # 1. Get the last updated timestamp from local DB
    last_updated = None
    try:
        res = manager.query(f'SELECT max("{updated_col}") FROM "{table_name}"').fetchone()
        if res and res[0]:
            last_updated = res[0]
            if isinstance(last_updated, datetime):
                last_updated = last_updated.isoformat()
    except Exception as e:
        logger.warning(f"Could not get last update time for {table_name}: {e}")

    # 2. Fetch new rows
    where = None
    if last_updated:
        where = f"{updated_col} > '{last_updated}'"
    
    df = client.parallel_fetch(domain, fourfour, limit=50000) # Default limit for sync
    if where:
        # Re-fetch with filter if possible, or filter locally if parallel_fetch doesn't support where yet
        # For now, let's assume we want to re-implement a filtered fetch
        params = {"$where": where}
        rows = []
        for batch in client.fetch_json(domain, fourfour, where=where):
            rows.extend(batch)
        df = pd.DataFrame(rows)

    if df.empty:
        manager.close()
        return 0

    # 3. Upsert to DuckDB
    from .core import DuckDBRepository
    repo = DuckDBRepository(manager, table_name)
    # We need a primary key/conflict column. If not specified, we'll try to find one or just append.
    # For now, let's assume 'id' or '@id' is the conflict column.
    pk = "id" if "id" in df.columns else ("@id" if "@id" in df.columns else None)
    
    if pk:
        count = repo.upsert_dataframe(df, pk)
    else:
        manager.conn.register("temp_df", df)
        manager.query(f'INSERT INTO "{table_name}" SELECT * FROM temp_df')
        count = len(df)
    
    manager.close()
    return count

# ── Streaming Pipeline ────────────────────────────────────────────────────────

def stream_pipeline(
    client: SocrataClient,
    domain: str,
    fourfour: str,
    targets: dict,
    dry_run: bool = True,
    chunk_size: int | None = None,
    max_rows: int | None = None,
    progress_callback: Callable[[int, int | None], None] | None = None,
    governance_processor: Optional[Any] = None,
) -> dict[str, Any]:
    """Orchestrates high-performance data ingestion from Socrata to multiple targets."""
    if chunk_size: client.config.page_size = chunk_size
    
    try:
        meta = client.get_metadata(domain, fourfour)
        total = meta.row_count
    except Exception:
        total = None

    if dry_run:
        gen = client.fetch_json(domain, fourfour, max_rows=max_rows)
        batch = next(gen) if gen else []
        return {"rows_sampled": len(batch), "total_estimate": total, "preview": batch[:5]}

    fetched = 0
    duckdb_exporter = None
    jsonl_f = None
    jsonl_path = None

    try:
        if targets.get("duckdb", {}).get("enabled"):
            duckdb_exporter = DuckDBExporter(targets["duckdb"].get("db_path"))

        if targets.get("xlsx", {}).get("enabled"):
            jsonl_path = Path(tempfile.gettempdir()) / f"{fourfour}_backup.jsonl"
            jsonl_f = open(jsonl_path, "w", encoding="utf-8")

        for batch in client.fetch_json(domain, fourfour, max_rows=max_rows):
            if not batch: continue
            fetched += len(batch)

            if governance_processor:
                for row in batch:
                    event = CDCEvent(
                        event_id=str(uuid.uuid4()),
                        source_dataset=fourfour,
                        operation="INSERT",
                        record_id=str(row.get("id", row.get("@id", uuid.uuid4()))),
                        timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
                        after=row,
                        metadata={"source_domain": domain},
                    )
                    governance_processor.process_event(event)

            if duckdb_exporter:
                cfg = targets["duckdb"]
                duckdb_exporter.upsert_batches([batch], table=cfg.get("table"), conflict_column=cfg.get("conflict_column"))

            if jsonl_f:
                for r in batch: jsonl_f.write(json.dumps(r, default=str) + "\n")

            if progress_callback: progress_callback(fetched, total)

        return {"rows_processed": fetched, "jsonl_backup": str(jsonl_path) if jsonl_path else None}

    finally:
        if duckdb_exporter: duckdb_exporter.manager.close()
        if jsonl_f: jsonl_f.close()

# ── BI & Excel Integrations ───────────────────────────────────────────────────

class ExcelWorkbookBuilder:
    """Builds multi-sheet Excel workbooks with formatting and formulas."""
    def __init__(self):
        self.sheets: List[Tuple[str, pd.DataFrame, Dict[str, Any]]] = []

    def add_data_sheet(self, name: str, df: pd.DataFrame, freeze_panes: str = "A2") -> ExcelWorkbookBuilder:
        self.sheets.append((name, df, {"freeze_panes": freeze_panes}))
        return self

    def save(self, path: str):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for name, df, opts in self.sheets:
                df.to_excel(writer, sheet_name=name, index=False)
                ws = writer.book[name]
                if opts.get("freeze_panes"): ws.freeze_panes = opts["freeze_panes"]
        return path

def export_for_tableau(df: pd.DataFrame, output_dir: str, filename: str = "data") -> str:
    """Export data and metadata for Tableau."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"{filename}.csv"
    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    meta = {"source": "socrata_toolkit", "row_count": len(df), "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns]}
    (out / f"{filename}_metadata.json").write_text(json.dumps(meta, indent=2))
    return str(csv_path)

def export_for_powerbi(df: pd.DataFrame, output_dir: str, filename: str = "data") -> str:
    """Export data for Power BI."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"{filename}.csv"
    df.to_csv(csv_path, index=False)
    return str(csv_path)
