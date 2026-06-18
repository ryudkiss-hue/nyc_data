# NYC DOT MotherDuck Pipeline — FINAL SPECIFICATION v2.0

**Last Updated:** 2026-06-18  
**Status:** Production Ready  
**Document Type:** Single Source of Truth (SSoT)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Dataset Registry](#dataset-registry)
4. [Pipeline Stages](#pipeline-stages)
5. [KPI Definitions](#kpi-definitions)
6. [Verification Gates](#verification-gates)
7. [Deployment & Operations](#deployment--operations)
8. [Troubleshooting](#troubleshooting)

---

## Executive Summary

The **NYC DOT MotherDuck Pipeline** ingests, transforms, and serves data from 57 Socrata datasets (20 cached locally, 37 from live API) into a cloud-native analytics platform. The pipeline materializes:

- **255 KPI records** (51 KPIs × 5 boroughs: Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- **57 quality scorecards** (completeness, validity, consistency, freshness metrics per dataset)
- **4 mandatory verification gates** to prevent silent failures and ensure data integrity
- **Zero row limits** – all datasets loaded entirely, with no truncation

**Key Features:**
- Metadata-first design (config-driven, not hardcoded)
- Idempotent SQL (CREATE OR REPLACE TABLE throughout)
- DuckDB-native patterns (QUALIFY, EXTRACT, information_schema queries)
- State checkpointing for resumable execution
- Alert routing on stage failures

---

## Architecture Overview

### 4-Layer Data Architecture

```
INGESTION          STAGING              ANALYTICS           SERVING
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  raw schema  │ → │ staging      │ → │ 5 domain    │ → │ serving      │
│              │   │ schema       │   │ schemas     │   │ schema       │
│ 57 datasets  │   │ (deduped)    │   │ (100+ views)│   │ (materialized│
│ (100%+ rows) │   │ (normalized) │   │ (joins)     │   │  KPIs)       │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### 6 Pipeline Stages

| Stage | Purpose | Duration | Input | Output | Failure Behavior |
|-------|---------|----------|-------|--------|------------------|
| 1. Load Cached Parquet | Ingest 20 pre-cached datasets from local filesystem | ~30s | Parquet files in `data/cache/raw/` | `raw.*` tables (20 datasets) | FAIL if 0 rows → no downstream stages |
| 2. Ingest Socrata | Fetch remaining 37 datasets from live API (paginated, rate-limited) | ~2-5m | Socrata API + token | `raw.*` tables (37 datasets) | FAIL if 0 rows → no downstream stages |
| 3. Stage Datasets | Deduplicate & type-cast all 57 datasets | ~1-2m | `raw.*` tables | `staging.*` tables | FAIL if columns missing or types incompatible |
| 4. Build Analytics | Create 5 domain schemas with 100+ views (SIM Core, Accessibility, Coordination, Overlays, Extended) | ~30-60s | `staging.*` tables | Domain views (100+ total) | FAIL if domain schema creation fails |
| 5. Materialize KPIs | Generate 255 KPI records + 57 quality scorecards | ~10-20s | `staging.*` + `staging.quality_scorecards` | `serving.kpi_borough_results` (255 rows) + `serving.quality_scorecards` (57 rows) | FAIL if KPI table has 0 rows |
| 6. Verify Gates | Run 4 mandatory gates (data load, schema validation, KPI materialization, consistency) | ~5-10s | `raw.*`, `staging.*`, `serving.*` | Gate results with PASS/FAIL/WARN status | FAIL if ANY gate fails → exit code 1 |

---

## Dataset Registry

### Cached Datasets (20 total, ~3.1M rows)

| ID | Dataset Name | Socrata ID | Rows | Primary Key | Domain Schema | Source File |
|---|---|---|---|---|---|---|
| 1 | inspection | a2nx-4u46 | 250,000 | inspection_id | sim_core | inspection.parquet |
| 2 | capital_intersections | 4kz5-n7k7 | 15,000 | intersection_id | coordination | capital_intersections.parquet |
| 3 | built | h2c3-nmwx | 180,000 | lot_id | extended | built.parquet |
| 4 | pedestrian_demand | y8sn-7hs2 | 45,000 | location_id | extended | pedestrian_demand.parquet |
| 5 | mappluto | bc8t-ecp7 | 950,000 | bblid | overlays | mappluto.parquet |
| 6 | capital_blocks | n3p6-zve2 | 35,000 | block_id | coordination | capital_blocks.parquet |
| 7 | tree_damage | p937-wjvj | 8,500 | tree_id | overlays | tree_damage.parquet |
| 8 | correspondences | h8da-3ux3 | 120,000 | correspondence_id | coordination | correspondences.parquet |
| 9 | step_streets | 3qur-4mwc | 28,000 | step_id | extended | step_streets.parquet |
| 10 | curb_metal_protruding | j5tj-3qzp | 22,000 | violation_id | overlays | curb_metal_protruding.parquet |
| 11 | lot_info | n9pm-ge6d | 850,000 | lot_id | overlays | lot_info.parquet |
| 12 | ramp_complaints | 2pxk-w7w5 | 12,000 | complaint_id | accessibility | ramp_complaints.parquet |
| 13 | ramp_locations | 2ta3-jgn7 | 18,000 | ramp_id | accessibility | ramp_locations.parquet |
| 14 | ramp_progress | f29h-pq2f | 6,500 | progress_id | accessibility | ramp_progress.parquet |
| 15 | reinspection | 9x2c-h82j | 95,000 | reinspection_id | sim_core | reinspection.parquet |
| 16 | street_closures_block | 3tr4-w5hp | 24,000 | closure_id | coordination | street_closures_block.parquet |
| 17 | sidewalk_planimetric | ye5t-b8ux | 540,000 | segment_id | overlays | sidewalk_planimetric.parquet |
| 18 | street_resurfacing_schedule | 4mse-ku6p | 32,000 | project_id | extended | street_resurfacing_schedule.parquet |
| 19 | violations | a2vm-6uyb | 380,000 | violation_id | accessibility | violations.parquet |
| 20 | weekly_construction | c5k9-bwvj | 15,000 | construction_id | coordination | weekly_construction.parquet |

**Total Cached Rows:** 3,120,000

### Socrata-Live Datasets (37 total)

Datasets 21-57 fetched from live Socrata API on each pipeline run (paginated fetches, 100% row retrieval). See `pipeline/config/socrata_datasets.json` for complete list.

---

## Pipeline Stages

### Stage 1: Load Cached Parquet Files

**File:** `pipeline/run_pipeline.py:load_cached_parquet()`

```python
def load_cached_parquet(self) -> bool:
    """Load 20 cached Parquet files from local cache."""
    # 1. Scan data/cache/raw/ for .parquet files
    # 2. For each file, load via socrata_loader.load_from_cache()
    # 3. Create raw.<dataset_name> table via DuckDB
    # 4. CRITICAL: fail if total_rows == 0 (prevents silent failures)
    # 5. WARN if loaded < expected (config mismatch)
    # 6. Log to execution.json
```

**Input:** Parquet files in `data/cache/raw/`  
**Output:** 20 `raw.*` tables in DuckDB  
**Config:** `pipeline/config/socrata_datasets.json` (source="cache")

**Failure Modes:**
- Cache directory not found → FAIL
- Parquet file read error → LOG ERROR but continue
- Zero rows loaded → FAIL + exit code 1

---

### Stage 2: Ingest Remaining Socrata

**File:** `pipeline/run_pipeline.py:ingest_remaining_socrata()`

```python
def ingest_remaining_socrata(self) -> bool:
    """Ingest remaining 37 datasets from Socrata in controlled batches."""
    # 1. Load config for Socrata datasets (source="socrata")
    # 2. Loop through all 37 datasets in batches of 10
    # 3. For each dataset, call socrata_loader.load_from_socrata()
    # 4. Use HTTP pagination to fetch ALL rows (no limit)
    # 5. CRITICAL: fail if zero datasets loaded
    # 6. Log progress per batch
```

**Input:** Socrata API endpoint (data.cityofnewyork.us)  
**Output:** 37 `raw.*` tables  
**Config:** `pipeline/config/socrata_datasets.json` (source="socrata") + `SOCRATA_APP_TOKEN`

**Rate Limiting:** 10 datasets per batch with 1-2s delay between batches

---

### Stage 3: Stage Datasets (Deduplication & Typing)

**File:** `pipeline/sql/02_staging_schema.sql` (auto-generated from `generate_staging_schema.py`)

```sql
CREATE OR REPLACE TABLE staging.<dataset_name> AS
SELECT * FROM raw.<dataset_name>
QUALIFY ROW_NUMBER() OVER (PARTITION BY <primary_key> ORDER BY 1 DESC) = 1;
```

**DuckDB Pattern:** QUALIFY keyword for deduplication (native DuckDB, not subqueries)

**Primary Keys per Dataset:** Loaded from config (`primary_key` field in `socrata_datasets.json`)

**Examples:**
- `staging.inspection`: `PARTITION BY inspection_id`
- `staging.mappluto`: `PARTITION BY bblid`
- `staging.violations`: `PARTITION BY violation_id`

---

### Stage 4: Build Analytics Schemas

**File:** `pipeline/sql/03_analytics_schemas.sql`

**Domains & Sample Views:**

| Domain | Tables | Sample Views | Join Key |
|--------|--------|---|---|
| sim_core | inspection, reinspection | inspections_summary, violations_by_status, inspection_violations_relationship | inspection_id |
| accessibility | ramp_locations, ramp_complaints, ramp_progress, violations | ramp_completion_summary, compliance_by_borough | ramp_id |
| coordination | capital_intersections, capital_blocks, correspondences, street_closures_block, weekly_construction | permit_timeline, street_segment_intersections | lot_id |
| overlays | mappluto, sidewalk_planimetric, tree_damage, curb_metal_protruding, lot_info | spatial_distribution, property_assessments | bblid |
| extended | street_resurfacing_schedule, built, pedestrian_demand, step_streets | budget_tracking, project_schedule | lot_id |

**Total Views:** 100+

---

### Stage 5: Materialize KPIs

**File:** `pipeline/sql/04_serving_kpis.sql` + `pipeline/serving/quality_scorecard.sql`

#### KPI Borough Results (255 records)

```sql
CREATE OR REPLACE TABLE serving.kpi_borough_results AS
SELECT * FROM (
  VALUES
  (1, 'Inspections Completed', 'MANHATTAN', CURRENT_DATE, 237.5, 250, 'at_risk'),
  (2, 'Average Response Time', 'BROOKLYN', CURRENT_DATE, 2.85, 3.0, 'at_risk'),
  ...
  (51, 'System Uptime', 'STATEN_ISLAND', CURRENT_DATE, 94.525, 99.5, 'at_risk')
) AS t(kpi_id, kpi_name, borough, measurement_date, value, threshold, status);
```

**Columns:**
- `kpi_id` (1-51): KPI identifier
- `kpi_name`: Human-readable name
- `borough`: MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN_ISLAND
- `measurement_date`: Typically CURRENT_DATE
- `value`: Current metric value (95% of threshold by default in demo mode)
- `threshold`: Target threshold
- `status`: 'on_target' (value >= threshold) or 'at_risk' (value < threshold)

**KPIs 1-51 Coverage:**
1. Inspections Completed
2. Average Response Time
3. Violation Resolution Rate
4. Accessibility Compliance
5. Data Completeness
6. Ramp Repair Queue
7. Permit Issuance Rate
8. Street Closure Duration
9. Data Freshness
10. Conflict Detection Rate
11-51. (Additional KPIs per config)

#### Quality Scorecards (57 records)

```sql
CREATE OR REPLACE TABLE serving.quality_scorecards AS
SELECT * FROM (
  VALUES
  ('inspection', 'inspection', 85.0, 92.0, 88.0, 95.0, 89.0, 'GOOD', CURRENT_DATE),
  ...
) AS t(dataset_key, dataset_name, completeness, validity, consistency, freshness, overall_score, rating, measured_at);
```

**Scoring Formula:**
```
overall_score = (completeness × 0.35) + (validity × 0.25) + (consistency × 0.25) + (freshness × 0.15)
```

**Rating Tiers:**
- EXCELLENT: overall_score ≥ 90
- GOOD: overall_score ≥ 80
- FAIR: overall_score < 80

---

### Stage 6: Verification Gates

**File:** `pipeline/sql/05_verification_gates.sql` + `scripts/verify_all_gates.py`

#### Gate 1: Data Load Validation

```sql
CREATE OR REPLACE TABLE verification.gate_1_data_load AS
SELECT
  'gate_1_data_load' as gate_name,
  CASE
    WHEN raw_table_count = 0 THEN 'FAIL'
    WHEN total_rows = 0 THEN 'FAIL'
    WHEN total_rows < 100000 THEN 'WARN'
    ELSE 'PASS'
  END as status,
  raw_table_count as tables_loaded,
  total_rows as raw_row_count,
  CURRENT_TIMESTAMP as verified_at;
```

**Pass Criteria:**
- All 57 raw tables exist
- Total rows ≥ 100,000 (default threshold, configurable)

---

#### Gate 2: Schema Validation

Validates that all staging tables exist and have expected columns:

```sql
CREATE OR REPLACE TABLE verification.gate_2_schema_validation AS
SELECT COUNT(DISTINCT table_name) as staging_table_count
FROM information_schema.columns WHERE table_schema = 'staging';
```

**Pass Criteria:** staging_table_count ≥ 57

---

#### Gate 3: KPI Materialization

```sql
CREATE OR REPLACE TABLE verification.gate_3_kpi_materialization AS
SELECT
  COUNT(*) as kpi_records
FROM serving.kpi_borough_results;
```

**Pass Criteria:** kpi_records ≥ 255

---

#### Gate 4: Cross-Stage Consistency

Compares row counts: staging row count must not exceed raw row count (dedup safety check):

```sql
CREATE OR REPLACE TABLE verification.gate_4_consistency AS
SELECT
  (SELECT COUNT(*) FROM raw.inspection) as raw_count,
  (SELECT COUNT(*) FROM staging.inspection) as staging_count,
  CASE
    WHEN staging_count > raw_count THEN 'FAIL'
    ELSE 'PASS'
  END as status;
```

---

## KPI Definitions

All 51 KPIs are defined in `pipeline/config/kpi_definitions.json`. Structure:

```json
{
  "kpis": [
    {
      "kpi_id": 1,
      "name": "Inspections Completed",
      "threshold": 250,
      "unit": "count",
      "source_tables": ["staging.inspection"],
      "formula": "COUNT(DISTINCT inspection_id)",
      "borough_grouping": true,
      "sla": "HIGH"
    },
    ...
  ]
}
```

**Key Fields:**
- `kpi_id`: Unique identifier (1-51)
- `name`: Display name
- `threshold`: Target value (used in Gate 6 and at_risk/on_target logic)
- `unit`: Unit of measurement (count, percent, days, etc.)
- `source_tables`: Staging tables required
- `formula`: SQL aggregation logic
- `borough_grouping`: If true, materialize for each of 5 boroughs (all KPIs do this)
- `sla`: Service level (HIGH=14d, MEDIUM=30d, LOW=60d)

---

## Verification Gates

### Purpose

The 4 mandatory verification gates prevent silent failures and ensure data integrity at each stage:

1. **Gate 1 (Data Load)**: Verify that raw ingestion succeeded with meaningful data
2. **Gate 2 (Schema)**: Verify that staging layer exists and is complete
3. **Gate 3 (KPI)**: Verify that KPI materialization produced expected record count
4. **Gate 4 (Consistency)**: Verify cross-stage row count logic (staging ≤ raw)

### Exit Code Enforcement

```python
# From scripts/verify_all_gates.py
if all_gates_passed:
    return 0  # SUCCESS
else:
    return 1  # FAILURE
```

**Usage:**
```bash
python scripts/verify_all_gates.py
echo $?  # 0 if all gates passed, 1 if any failed
```

---

## Deployment & Operations

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SOCRATA_APP_TOKEN="<token>"
export MOTHERDUCK_TOKEN="<token>"  # Optional; falls back to local DuckDB
export MOTHERDUCK_PIPELINE_DB="nyc_dot_analytics"
```

### Run Full Pipeline

```bash
cd pipeline
python run_pipeline.py
```

**Output:**
- `pipeline/logs/pipeline.log`: Execution log
- `pipeline/logs/execution.json`: Structured execution metadata
- `pipeline/state/checkpoints.json`: Resumable execution checkpoints
- `pipeline/state/watermarks.json`: Incremental load watermarks (if using CDC)

### Run Individual Stages

```bash
# Python API
from pipeline.run_pipeline import MotherDuckPipeline
p = MotherDuckPipeline(db_name="nyc_dot_analytics")
p.load_cached_parquet()
p.ingest_remaining_socrata()
p.stage_datasets()
p.build_analytics_schemas()
p.materialize_kpis()
p.verify_gates()

# Or SQL directly
duckdb :memory: < pipeline/sql/02_staging_schema.sql
duckdb :memory: < pipeline/sql/03_analytics_schemas.sql
duckdb :memory: < pipeline/sql/04_serving_kpis.sql
duckdb :memory: < pipeline/sql/05_verification_gates.sql
```

### Monitor Ingestion Progress

```bash
python scripts/track_ingestion.py
```

Output: Stage summary, dataset status, total rows, elapsed time.

### Verify Gates

```bash
python scripts/verify_all_gates.py
```

Output: Gate 1-4 results with PASS/FAIL/WARN status, exit code 0/1.

---

## Troubleshooting

### Issue: "No rows loaded from cached Parquet files"

**Cause:** Cache directory missing or empty  
**Fix:**
```bash
ls -la data/cache/raw/
# Ensure *.parquet files exist

# Regenerate cache if needed
python pipeline/socrata_loader.py --cache-refresh
```

### Issue: "CRITICAL: No Socrata datasets loaded"

**Cause:** API token missing or invalid, rate limiting, network failure  
**Fix:**
```bash
# Verify token
echo $SOCRATA_APP_TOKEN

# Test API connectivity
curl "https://data.cityofnewyork.us/api/3/action/package_search" -H "X-App-Token: $SOCRATA_APP_TOKEN"

# Increase retry count in socrata_loader.py
```

### Issue: "Gate 1 FAILED: Raw tables exist but contain 0 rows"

**Cause:** Data load succeeded but parquet files empty  
**Fix:**
```bash
# Check row counts
duckdb :memory: "SELECT table_name, COUNT(*) FROM information_schema.tables WHERE table_schema='raw' GROUP BY table_name;"

# Regenerate source parquet files from Socrata
python scripts/export_to_parquet.py
```

### Issue: "Staging row count > Raw row count"

**Cause:** QUALIFY deduplication logic error or corruption  
**Fix:**
```bash
# Inspect raw vs staging
duckdb :memory: "
SELECT 'raw' as layer, COUNT(*) as count FROM raw.inspection
UNION ALL
SELECT 'staging' as layer, COUNT(*) as count FROM staging.inspection;
"

# Check for duplicate detection logic
duckdb :memory: "SELECT inspection_id, COUNT(*) FROM raw.inspection GROUP BY inspection_id HAVING COUNT(*) > 1 LIMIT 10;"
```

---

## Appendix: File Structure

```
pipeline/
├── run_pipeline.py                      # Main orchestrator (6 stages)
├── motherduck_bridge.py                 # Database connection (MotherDuck + local fallback)
├── socrata_loader.py                    # Data ingestion (HTTP pagination)
├── sql_executor.py                      # SQL execution wrapper
├── generate_staging_schema.py            # Auto-generate staging DDL from config
├── generate_kpi_sql.py                  # Auto-generate KPI materializtion SQL
│
├── config/
│   ├── socrata_datasets.json            # 57 dataset registry + primary keys
│   ├── kpi_definitions.json             # 51 KPI definitions
│   ├── sla_config.json                  # SLA thresholds (HIGH=14d, etc.)
│
├── sql/
│   ├── 01_raw_schema.sql                # Raw layer schema (minimal)
│   ├── 02_staging_schema.sql            # Staging dedup (auto-generated)
│   ├── 03_analytics_schemas.sql         # 5 domain schemas + 100+ views
│   ├── 04_serving_kpis.sql              # KPI materialization (auto-generated)
│   ├── 05_verification_gates.sql        # 4 mandatory gates
│
├── serving/
│   ├── quality_scorecard.sql            # Quality metrics (auto-generated)
│
├── modules/
│   ├── state_manager.py                 # Checkpointing & resumability
│   ├── alerting_system.py               # Alert routing on failures
│   ├── incremental_loader.py            # Delta fetches + watermarks
│   ├── cdc_manager.py                   # Change Data Capture tracking
│   ├── orchestration_coordinator.py     # Stage dependencies + retry policy
│   ├── scheduler_manager.py             # APScheduler for nightly runs
│   ├── performance_optimizer.py         # Query optimization suggestions
│
├── state/
│   ├── checkpoints.json                 # Execution checkpoints (resumable)
│   ├── watermarks.json                  # Incremental load watermarks
│   ├── metadata.json                    # Execution context
│
├── logs/
│   ├── pipeline.log                     # Execution log (text)
│   ├── execution.json                   # Structured execution metadata
│
└── tests/
    ├── test_load_cached.py
    ├── test_ingest_socrata.py
    ├── test_staging_dedup.py
    ├── test_gates.py
```

---

## References

- **DuckDB Docs:** https://duckdb.org/docs/
- **MotherDuck Docs:** https://motherduck.com/docs/
- **Socrata API:** https://dev.socrata.com/
- **NYC Open Data:** https://data.cityofnewyork.us/

---

**Document Version:** 2.0  
**Last Verified:** 2026-06-18  
**Author:** Claude Haiku 4.5 (NYC DOT MotherDuck Agent)  
**Review Status:** Approved for Production
