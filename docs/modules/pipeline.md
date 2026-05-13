# `socrata_toolkit.pipeline` — Ingestion, CDC & BI Export

**File:** `socrata_toolkit/pipeline.py` | **Pillar:** Pipeline  
**Dependencies:** `pandas`, `duckdb`, `openpyxl` (optional)

---

## Change Data Capture (CDC)

### `CDCEvent` (dataclass)
Represents a single record-level change.
```python
@dataclass
class CDCEvent:
    event_id: str; source_dataset: str; operation: str  # INSERT|UPDATE|DELETE
    record_id: str; timestamp_ms: int
    before: dict|None; after: dict|None; metadata: dict|None
    def to_dict(self) -> dict: ...
```

### `CDCProcessor`
Processes and logs CDC events.
```python
proc = CDCProcessor(dsn="postgresql://...")
proc.process_event(event)
```

---

## Data Ingestion

### `ingest_311_complaints(max_rows=1000, borough=None) → SimpleNamespace`
Fetches NYC 311 complaints (dataset `erm2-nwe9`) with optional borough filter.

```python
result = ingest_311_complaints(max_rows=5000, borough="BROOKLYN")
print(result.total)     # total rows fetched
df = result.df          # the DataFrame
```

Returns: `{total, critical_count, data, df}`

### `sync_dataset(domain, fourfour, db_path, table_name, updated_col, token) → int`
Incremental sync from Socrata to a local DuckDB table. Only fetches rows updated since the last sync watermark.

```python
rows_synced = sync_dataset(
    domain="data.cityofnewyork.us",
    fourfour="erm2-nwe9",
    db_path="nyc.db",
    table_name="complaints_311",
    updated_col=":updated_at",
    token="my_app_token"
)
print(f"Synced {rows_synced} new/updated rows")
```

**Sync logic:**
1. Queries local DuckDB for `MAX(updated_col)` watermark
2. Fetches only rows newer than watermark (full load on first run)
3. Upserts with `ON CONFLICT` handling on `id` or `@id`

---

## Streaming Pipeline

### `stream_pipeline(client, domain, fourfour, targets, *, dry_run, chunk_size, max_rows, progress_callback, governance_processor) → dict`

Orchestrates high-performance ingestion from Socrata to multiple output targets simultaneously.

```python
from socrata_toolkit import SocrataClient, stream_pipeline

client = SocrataClient()
result = stream_pipeline(
    client=client,
    domain="data.cityofnewyork.us",
    fourfour="erm2-nwe9",
    targets={
        "duckdb": {
            "enabled": True,
            "db_path": "nyc.db",
            "table": "complaints_311",
            "conflict_column": "unique_key"
        },
    },
    dry_run=False,
    max_rows=10000,
    progress_callback=lambda done, total: print(f"{done}/{total}")
)
print(result["rows_processed"])
```

**Supported targets:**
- `duckdb`: upsert to local DuckDB table
- `xlsx`: JSONL backup (first step toward workbook export)

**Dry run** mode fetches only the first page and returns a preview — useful for schema inspection.

**Governance integration:** Pass a `GovernanceProcessor` to auto-generate `CDCEvent`s for every ingested row.

---

## Data Engineering

### `deduplicate_dataframe(df, subset=None) → pd.DataFrame`
Remove duplicate rows, optionally on a subset of columns.

### `detect_changes(old_df, new_df, key) → SimpleNamespace`
Full diff between two DataFrames on a primary key.
```python
changes = detect_changes(old_df, new_df, key="unique_key")
print(changes.added_count, changes.removed_count, changes.modified_count)
changes.added    # DataFrame of new rows
changes.deleted  # DataFrame of removed rows
changes.modified # DataFrame of changed rows
```

### `join_datasets(left_df, right_df, on, how="inner", suffixes) → pd.DataFrame`
Wrapper around `pd.merge` with standard defaults.

### `create_pivot_table(df, index, columns, values, aggfunc="mean") → pd.DataFrame`
Create a pivot table.

### `vlookup(df, other_df, left_on, right_on, col) → pd.DataFrame`
Excel-style VLOOKUP via left merge.

### `compute_hotspots(df, lat_col, lon_col, borough=None) → pd.DataFrame`
Return filtered DataFrame for hotspot analysis (borough filter).

### `dataframe_to_create_table(df, table_name) → str`
Generate a `CREATE TABLE` SQL statement from DataFrame column names.

### `postgis_add_geom(manager, table_name, lat_col, lon_col)`
Add a geometry point column to a DuckDB table using the spatial extension.

---

## BI & Excel Export

### `ExcelWorkbookBuilder`
Fluent builder for multi-sheet Excel workbooks.

```python
from socrata_toolkit.pipeline import ExcelWorkbookBuilder

path = (
    ExcelWorkbookBuilder()
    .add_data_sheet("Raw Data", df)
    .add_pivot_sheet("By Borough", df, index="borough", values="violations")
    .save("output.xlsx")
)
```

| Method | Description |
|--------|-------------|
| `add_data_sheet(name, df, freeze_panes)` | Data sheet with frozen header |
| `add_pivot_sheet(name, df, index, columns, values)` | Auto-pivoted sheet |
| `save(path) → str` | Write and return path |

### `export_for_tableau(df, output_dir, filename="data") → str`
Exports CSV + `{filename}_metadata.json` with schema info for Tableau.

### `export_for_powerbi(df, output_dir, filename="data") → str`
Exports CSV for Power BI import.

### `export_as_sql_file(sql, path)`
Save a SQL string to disk.

### `export_graph(df, path)`
Export DataFrame as CSV for graph tools (Gephi, NetworkX).

### `create_presentation(df, title)`
Stub for PowerPoint export (saves info file to `outputs/reports/`).

---

## SQL Utilities

### `SQLQueryBuilder`
Simple query builder from a DataFrame schema.
```python
builder = SQLQueryBuilder(df, "sidewalks")
sql = builder.build()  # → "SELECT * FROM sidewalks"

---

## Workflow Engine (Reconciled)

### `WorkflowStep(name, action, trigger)`
A single step in a processing pipeline. `action` is a function `df -> df`.

### `Workflow(steps)`
A collection of steps executed in sequence.

```python
from socrata_toolkit import Workflow, WorkflowStep

steps = [
    WorkflowStep("clean", clean_df),
    WorkflowStep("analyze", analyze_df, trigger=lambda df: not df.empty)
]
flow = Workflow(steps)
result = flow.run(df)
dag = flow.export_to_airflow()
```

| Method | Description |
|--------|-------------|
| `run(df)` | Execute all steps in order |
| `export_to_airflow()` | Generate Airflow DAG code |
```
