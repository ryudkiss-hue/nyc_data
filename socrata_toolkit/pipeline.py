from __future__ import annotations

import csv
import json
import logging
import tempfile
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from types import SimpleNamespace

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from .core import (
    SocrataClient, DuckDBExporter, DuckDBManager, 
    DEFAULT_DOMAIN, UTF8, COL_ID, COL_AT_ID, COL_LAT, COL_LON, COL_BORO,
    ENGINE_XL, XL_FREEZE
)

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

# ── 311 Ingestion ─────────────────────────────────────────────────────────────

def ingest_311_complaints(max_rows: int = 1000, borough: str | None = None) -> Any:
    """Fetch and triage 311 complaints, optionally filtered by borough."""
    from .core import SocrataClient
    client = SocrataClient()
    df = client.fetch_dataframe(DEFAULT_DOMAIN, "erm2-nwe9", max_rows=max_rows)
    if borough and COL_BORO in df.columns:
        df = df[df[COL_BORO].str.upper() == borough.upper()]
    return SimpleNamespace(total=len(df), critical_count=0, data=df, df=df)

# ── Data Engineering ──────────────────────────────────────────────────────────

def deduplicate_dataframe(df: pd.DataFrame, subset: List[str] | None = None) -> pd.DataFrame:
    """Remove duplicate rows."""
    return df.drop_duplicates(subset=subset)

def detect_changes(old_df: pd.DataFrame, new_df: pd.DataFrame, key: str | List[str]) -> Any:
    """Detect added, deleted, or modified rows between two dataframes."""
    merged = old_df.merge(new_df, on=key, how="outer", indicator="_merge", suffixes=("_old", "_new"))

    added = merged[merged["_merge"] == "right_only"].drop(columns=["_merge"])
    deleted = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    # For modified rows, compare paired _old/_new columns value-by-value
    both = merged[merged["_merge"] == "both"].drop(columns=["_merge"])
    old_cols = [c for c in both.columns if c.endswith("_old")]
    new_cols = [c.replace("_old", "_new") for c in old_cols if c.replace("_old", "_new") in both.columns]
    if old_cols and new_cols:
        # Compare element-wise; treat NaN == NaN as equal
        old_vals = both[old_cols].fillna("__NA__").values
        new_vals = both[new_cols].fillna("__NA__").values
        diff_mask = (old_vals != new_vals).any(axis=1)
        modified = both[diff_mask]
    else:
        modified = pd.DataFrame()

    return SimpleNamespace(
        added=added,
        deleted=deleted,
        modified=modified,
        added_count=len(added),
        removed_count=len(deleted),
        modified_count=len(modified)
    )

# Reporting logic moved to analysis.py

# ── Data Integration ──────────────────────────────────────────────────────────

def join_datasets(left_df: pd.DataFrame, right_df: pd.DataFrame, on: str | List[str], how: str = 'inner', suffixes: Tuple[str, str] = ('_left', '_right')) -> pd.DataFrame:
    """Join two datasets using pandas merge."""
    return pd.merge(left_df, right_df, on=on, how=how, suffixes=suffixes, validate=None)

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
            # Convert to string if it's a datetime object
            if hasattr(last_updated, "isoformat"):
                last_updated = last_updated.isoformat()
    except Exception as e:
        logger.info(f"Initializing table {table_name} for first-time sync.")

    # 2. Fetch rows (incremental if possible)
    where = f"{updated_col} > '{last_updated}'" if last_updated else None
    
    # Force chronological streaming so that mid-download crashes can perfectly resume
    order = f"{updated_col} ASC"
    
    # Pre-flight query to get total count for the progress bar percentage & ETA
    total_to_fetch = None
    if tqdm:
        try:
            import requests
            count_params = {"$select": "count(*)"}
            if where: count_params["$where"] = where
            url = f"https://{domain}/resource/{fourfour}.json"
            # Socrata returns count as [{"count": "1234"}]
            resp = requests.get(url, params=count_params, headers=client._headers(), timeout=10)
            if resp.status_code == 200:
                total_to_fetch = int(resp.json()[0]["count"])
        except Exception:
            pass

    pbar = None
    if tqdm and (total_to_fetch is None or total_to_fetch > 0):
        bar_fmt = "{desc} {percentage:3.0f}% │{bar}│ {n_fmt}/{total_fmt} rows [ETA: {remaining}, {rate_fmt}]" if total_to_fetch else "{desc}: {n_fmt} rows [{elapsed}, {rate_fmt}]"
        pbar = tqdm(total=total_to_fetch, desc=f"📡 Streaming {fourfour}", unit="rows", bar_format=bar_fmt)

    from .core import DuckDBRepository
    repo = DuckDBRepository(manager, table_name)
    pk = None
    table_initialized = False
    count = 0

    # Fetch using JSON stream for efficiency with potential where clause
    try:
        for batch in client.fetch_json(domain, fourfour, where=where, order=order):
            if not batch: continue
            df_batch = pd.DataFrame(batch)
            
            if not table_initialized:
                pk = COL_ID if COL_ID in df_batch.columns else (COL_AT_ID if COL_AT_ID in df_batch.columns else None)
                table_initialized = True
                
            # Safely commit to disk every batch. Closing the window won't lose data!
            if pk:
                repo.upsert_dataframe(df_batch, pk)
            else:
                existing_tables = manager.conn.execute("SHOW TABLES").fetchall()
                table_exists = any(t[0] == table_name for t in existing_tables)
                manager.conn.register("temp_df", df_batch)
                if table_exists:
                    manager.query(f'INSERT INTO "{table_name}" SELECT * FROM temp_df')
                else:
                    manager.conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM temp_df')
                    
            count += len(batch)
            
            if pbar:
                pbar.update(len(batch))
                # Alternating colors based on download speed (rows per second)
                rate = pbar.format_dict.get("rate")
                if rate:
                    if rate > 2000:
                        pbar.colour = "#10b981" # Fast: Emerald Green
                    elif rate > 500:
                        pbar.colour = "#f59e0b" # Medium: Amber
                    else:
                        pbar.colour = "#ef4444" # Slow: Red
                        
    except (Exception, KeyboardInterrupt) as e:
        logger.exception(f"Sync fetch failed: {e}")
        if pbar: pbar.close()
        manager.close()
        return count
        
    if pbar: pbar.close()

    manager.close()
    return count

def create_pivot_table(df: pd.DataFrame, index: str, columns: str, values: str, aggfunc: str = "mean") -> pd.DataFrame:
    """Create a pivot table using pandas."""
    return df.pivot_table(index=index, columns=columns, values=values, aggfunc=aggfunc)

def vlookup(df: pd.DataFrame, other_df: pd.DataFrame, left_on: str, right_on: str, col: str) -> pd.DataFrame:
    """Simulate Excel VLOOKUP by merging and extracting a single column."""
    merged = df.merge(other_df[[right_on, col]], left_on=left_on, right_on=right_on, how="left")
    return merged

def create_presentation(df: pd.DataFrame, title: str):
    """Simulate PowerPoint generation by saving an info file."""
    Path("outputs/reports").mkdir(parents=True, exist_ok=True)
    (Path("outputs/reports") / "presentation_info.txt").write_text(f"Presentation: {title}\nRows: {len(df)}")

class SQLQueryBuilder:
    """Builder for generating SQL queries from dataframes."""
    def __init__(self, df: pd.DataFrame, table_name: str):
        self.df = df
        self.table_name = table_name
    def build(self) -> str: return f"SELECT * FROM {self.table_name}"

def dataframe_to_create_table(df: pd.DataFrame, table_name: str) -> str:
    """Generate a SQL CREATE TABLE statement."""
    cols = [f"{c} TEXT" for c in df.columns]
    return f"CREATE TABLE {table_name} ({', '.join(cols)});"

def postgis_add_geom(manager: DuckDBManager, table_name: str, lat_col: str, lon_col: str):
    manager.conn.execute(f"UPDATE {table_name} SET geom = ST_Point({lon_col}, {lat_col}) WHERE geom IS NULL;")

def compute_hotspots(df: pd.DataFrame, lat_col: str = COL_LAT, lon_col: str = COL_LON, borough: str | None = None) -> pd.DataFrame:
    """Return a dataframe of density hotspots."""
    out = df.copy()
    if borough and COL_BORO in out.columns:
        out = out[out[COL_BORO].str.upper() == borough.upper()]
    return out

def export_as_sql_file(sql: str, path: str):
    """Save SQL string to a file."""
    Path(path).write_text(sql)

def export_graph(df: pd.DataFrame, path: str):
    """Simulate graph export (e.g. for Gephi or NetworkX)."""
    df.to_csv(path, index=False)

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
    show_progress: bool = True,
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
    
    pbar = None
    if show_progress and tqdm:
        pbar = tqdm(total=total, desc=f"Downloading {fourfour}", unit="rows", unit_scale=True)

    try:
        if targets.get("duckdb", {}).get("enabled"):
            duckdb_exporter = DuckDBExporter(targets["duckdb"].get("db_path"))

        if targets.get("xlsx", {}).get("enabled"):
            jsonl_path = Path(tempfile.gettempdir()) / f"{fourfour}_backup.jsonl"
            jsonl_f = open(jsonl_path, "w", encoding=UTF8)

        for batch in client.fetch_json(domain, fourfour, max_rows=max_rows):
            if not batch: continue
            fetched += len(batch)

            if governance_processor:
                for row in batch:
                    event = CDCEvent(
                        event_id=str(uuid.uuid4()),
                        source_dataset=fourfour,
                        operation="INSERT",
                        record_id=str(row.get(COL_ID, row.get(COL_AT_ID, uuid.uuid4()))),
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
            if pbar: pbar.update(len(batch))

        return {"rows_processed": fetched, "jsonl_backup": str(jsonl_path) if jsonl_path else None}

    finally:
        if duckdb_exporter: duckdb_exporter.manager.close()
        if jsonl_f: jsonl_f.close()
        if pbar: pbar.close()

# ── BI & Excel Integrations ───────────────────────────────────────────────────

class ExcelWorkbookBuilder:
    """Builds multi-sheet Excel workbooks with formatting and formulas."""
    def __init__(self):
        self.sheets: List[Tuple[str, pd.DataFrame, Dict[str, Any]]] = []

    def add_data_sheet(self, name: str, df: pd.DataFrame, freeze_panes: str = XL_FREEZE) -> ExcelWorkbookBuilder:
        self.sheets.append((name, df, {"freeze_panes": freeze_panes}))
        return self

    def add_pivot_sheet(self, name: str, df: pd.DataFrame, index: str | None = None, columns: str | None = None, values: str | None = None, rows: str | None = None) -> ExcelWorkbookBuilder:
        idx = index or rows
        pivot = df.pivot_table(index=idx, columns=columns, values=values)
        self.sheets.append((name, pivot.reset_index(), {}))
        return self

    def save(self, path: str):
        with pd.ExcelWriter(path, engine=ENGINE_XL) as writer:
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

# ── Workflow Engine (Reconciled) ──────────────────────────────────────────────

class WorkflowStep:
    """Represents a single step in a processing workflow."""
    def __init__(self, name: str, action: Callable[[pd.DataFrame], pd.DataFrame], 
                 trigger: Callable[[pd.DataFrame], bool] = None):
        self.name = name
        self.action = action
        self.trigger = trigger if trigger is not None else lambda df: True

    def execute(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.trigger(df):
            logger.info(f"Executing workflow step: {self.name}")
            return self.action(df)
        return df

class Workflow:
    """A collection of workflow steps to be executed in sequence."""
    def __init__(self, steps: List[WorkflowStep]):
        self.steps = steps

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        for step in self.steps:
            df = step.execute(df)
        return df

    def export_to_airflow(self) -> str:
        """Export the workflow definition to a Python Airflow DAG snippet."""
        lines = [
            "from airflow import DAG",
            "from airflow.operators.python import PythonOperator",
            "from datetime import datetime",
            "",
            "with DAG('nyc_data_workflow', start_date=datetime(2024, 1, 1), schedule_interval='@daily') as dag:"
        ]
        for step in self.steps:
            lines.append(f"    {step.name}_task = PythonOperator(task_id='{step.name}', python_callable={step.action.__name__})")
        return "\n".join(lines)
