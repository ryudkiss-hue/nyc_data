# Total Recall: Full-Scale Socrata Ingestion Guide

This document captures the technical lessons and architectural decisions made during the implementation of the "Total Recall" high-capacity ingestion engine for the NYC DOT Socrata Toolkit.

## 1. Overview
"Total Recall" is a deep-sync operation designed to pull 100% of available records from all 26 registered municipal datasets into a local DuckDB store. Unlike the standard "Mission Control" preview, this mode bypasses all row limits and utilizes the SODA3 Query API for high-throughput pagination.

## 2. Technical Lessons Learned

### A. SODA3 Query Rigor (400 Bad Request)
The SODA3 `query.json` endpoint is significantly more strict than the legacy SODA2 `resource.json` endpoint.
- **Field Name Sensitivity**: If a field name in the `WHERE` or `ORDER BY` clause does not match the dataset schema *exactly* (case-sensitive and symbol-accurate), SODA3 will return an immediate `400 Bad Request`.
- **Robustness Probe**: The toolkit now implements a "pre-flight" probe using a simple `$select=<col>&$limit=1` GET request to verify column existence before committing to a heavy POST-based SODA3 query.

### B. DuckDB Schema Evolution (Binder Error)
Municipal data is frequently "sparse"—meaning columns might be completely missing from the JSON output of certain batches if they contain only null values for those specific records.
- **The Issue**: Standard SQL `INSERT INTO` expects a fixed column count. If batch #1 has 30 columns and batch #2 has 28, DuckDB throws a `Binder Error`.
- **The Fix**: 
    1. **Schema Evolution**: The ingestion engine now performs a `PRAGMA table_info` check before every batch and issues `ALTER TABLE ... ADD COLUMN ... VARCHAR` for any new keys detected.
    2. **BY NAME Insertion**: All bulk inserts now use the `INSERT INTO ... BY NAME SELECT * FROM temp_df` syntax. This allows DuckDB to map columns by their names rather than their positions, gracefully handling missing or reordered fields in Socrata JSON batches.

### C. Large-Scale Memory Management
- **Streaming Generators**: We utilize Python generators to yield batches immediately to DuckDB rather than materializing millions of rows in RAM.
- **Tqdm Robustness**: When the Socrata record count is unknown or cannot be probed, `tqdm` must be checked against `None` explicitly to prevent `TypeError: bool() undefined` errors.

## 3. Usage
To perform a full workspace sync:
```bash
python scripts/total_recall.py
```
This script is optimized for background execution. Progress is logged to `outputs/total_recall.log`.

## 4. Maintenance
## 5. Post-Sync Analytical Gates (v0.5.0+)

The `total_recall` pipeline now automatically triggers a **DataQualityAudit** for every successfully synced dataset.

### Analysis History
All analytical findings are persisted to the `analysis_history` table in DuckDB. This table includes:
- **skill_name**: The analytical tool used (e.g., `DataQualityAudit`).
- **success**: Boolean indicating if the analysis completed.
- **table_name**: The municipal dataset ID.
- **data**: JSON payload of findings (Four Moments, Outliers, Null Counts).
- **metadata**: Execution context.

### Telemetry & Overhead
The integration adds a minimal (approx. 5-10%) overhead to the sync process but ensures that data moving to the Dash platform is validated against municipal engineering standards.

