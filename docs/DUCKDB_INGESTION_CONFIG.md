---
title: DuckDB/MotherDuck Ingestion Pipeline — 37-Dataset Configuration
version: 1.0
status: SOURCE_OF_TRUTH
created: 2026-06-17
last_updated: 2026-06-17
author: Claude Code
purpose: Define automated daily ingestion of all 37 Socrata datasets into DuckDB/MotherDuck
total_datasets: 37 (ALL MANDATORY)
refresh_strategy: Automated daily pull; all datasets required for full data integrity
---

# DuckDB Ingestion Configuration: 37-Dataset Pipeline

**MANDATORY:** All 37 datasets required for full data integrity. No optional datasets.

**Architecture:** Socrata (source) → DuckDB (staging/cache) → MotherDuck (cloud) → Dives (visualizations)

---

## Ingestion Schedule

| Frequency | Datasets | Start Time | SLA |
|-----------|----------|-----------|-----|
| **DAILY** | 15 datasets (Core, Quality, 311 Detailed) | 6:00 AM | Refresh within 6 hours |
| **WEEKLY** | 13 datasets (Construction, Contractor, Budget) | Sunday 5:00 PM | Refresh by Monday 6 AM |
| **MONTHLY** | 3 datasets (Equity base snapshot) | 1st of month, 12:00 AM | Refresh by 6 AM |
| **QUARTERLY** | 4 datasets (Reference/vendor updates) | Q start, 12:00 AM | Refresh within 24 hours |
| **ANNUAL** | 2 datasets (Census, EquityNYC) | Jan 1, 12:00 AM | Refresh within 48 hours |
| **STATIC** | 5 datasets (Geographic reference) | On-demand | On source update (quarterly check) |

---

## Ingestion Specifications by Dataset

### DAILY REFRESH (15 datasets) — 6:00 AM

#### Core Daily Operations (7)

```yaml
inspection:
  fourfour_id: dntt-gqwq
  source: https://data.cityofnewyork.us/api/views/dntt-gqwq/rows.json?$limit=100000
  frequency: DAILY
  refresh_time: 06:00 UTC
  sla_hours: 6
  duckdb_table: socrata.inspection
  partition_by: created_date
  incremental: TRUE (pull last 24 hours only)
  key_columns: [inspection_id, created_date]
  expected_rows: ~50K/day

violations:
  fourfour_id: 6kbp-uz6m
  source: https://data.cityofnewyork.us/api/views/6kbp-uz6m/rows.json?$limit=100000
  frequency: DAILY
  refresh_time: 06:00 UTC
  sla_hours: 6
  duckdb_table: socrata.violations
  partition_by: created_date
  incremental: TRUE
  key_columns: [violation_id, created_date]
  expected_rows: ~40K/day

reinspection:
  fourfour_id: gx72-kirf
  source: https://data.cityofnewyork.us/api/views/gx72-kirf/rows.json?$limit=50000
  frequency: DAILY
  refresh_time: 06:15 UTC
  sla_hours: 6
  duckdb_table: socrata.reinspection
  partition_by: inspection_date
  incremental: TRUE
  key_columns: [reinspection_id, inspection_date]
  expected_rows: ~5K/day

ramp_progress:
  fourfour_id: e7gc-ub6z
  source: https://data.cityofnewyork.us/api/views/e7gc-ub6z/rows.json?$limit=50000
  frequency: DAILY
  refresh_time: 06:30 UTC
  sla_hours: 6
  duckdb_table: socrata.ramp_progress
  partition_by: updated_date
  incremental: FALSE (full snapshot; small dataset)
  key_columns: [ramp_id]
  expected_rows: ~25K

ramp_complaints:
  fourfour_id: jagj-gttd
  source: https://data.cityofnewyork.us/api/views/jagj-gttd/rows.json?$limit=20000
  frequency: DAILY
  refresh_time: 06:45 UTC
  sla_hours: 6
  duckdb_table: socrata.ramp_complaints
  partition_by: created_date
  incremental: TRUE
  key_columns: [complaint_id, created_date]
  expected_rows: ~1K/day

complaints_311:
  fourfour_id: erm2-nwe9
  source: https://data.cityofnewyork.us/api/views/erm2-nwe9/rows.json?$limit=500000&$offset=0
  frequency: DAILY
  refresh_time: 07:00 UTC
  sla_hours: 8 (large dataset, staggered pull)
  duckdb_table: socrata.complaints_311
  partition_by: created_date
  incremental: TRUE (last 7 days rolling window)
  key_columns: [complaint_id, created_date]
  expected_rows: ~100K/day
  notes: Large dataset (21M+ rows); use pagination with $offset

built:
  fourfour_id: ugc8-s3f6
  source: https://data.cityofnewyork.us/api/views/ugc8-s3f6/rows.json?$limit=50000
  frequency: DAILY
  refresh_time: 07:30 UTC
  sla_hours: 6
  duckdb_table: socrata.built
  partition_by: completion_date
  incremental: FALSE (small dataset; full refresh OK)
  key_columns: [work_order_id]
  expected_rows: ~2K
```

#### Quality Assurance (3)

```yaml
dismissals:
  fourfour_id: p4u2-3jgx
  frequency: DAILY
  refresh_time: 08:00 UTC
  sla_hours: 6
  duckdb_table: socrata.dismissals
  incremental: TRUE (last 24 hours)
  expected_rows: ~10K/day

tree_damage:
  fourfour_id: j6v2-6uxq
  frequency: DAILY
  refresh_time: 08:15 UTC
  sla_hours: 6
  duckdb_table: socrata.tree_damage
  incremental: TRUE
  expected_rows: ~2K/day

correspondences:
  fourfour_id: bheb-sjfi
  frequency: DAILY
  refresh_time: 08:30 UTC
  sla_hours: 6
  duckdb_table: socrata.correspondences
  incremental: TRUE
  expected_rows: ~5K/day
```

#### 311 Detailed Complaints (3)

```yaml
Curb_Sidewalk_Complaints:
  fourfour_id: huz9-8jhi
  frequency: DAILY
  refresh_time: 09:00 UTC
  sla_hours: 6
  duckdb_table: socrata.curb_sidewalk_complaints
  incremental: TRUE (last 7 days)
  expected_rows: ~10K/day

DOT_311_Complaints_Street_Sidewalk:
  fourfour_id: th23-npnd
  frequency: DAILY
  refresh_time: 09:15 UTC
  sla_hours: 6
  duckdb_table: socrata.dot_311_complaints
  incremental: TRUE
  expected_rows: ~20K/day

311_Complaint_Type_Descriptor:
  fourfour_id: dtbq-f5rx
  frequency: DAILY
  refresh_time: 09:30 UTC
  sla_hours: 6
  duckdb_table: socrata.complaint_type_descriptor
  incremental: FALSE (lookup table; full refresh)
  expected_rows: ~500
```

---

### WEEKLY REFRESH (13 datasets) — Sunday 5:00 PM

#### Construction & Conflicts (6)

```yaml
street_permits:
  fourfour_id: tqtj-sjs8
  frequency: WEEKLY
  refresh_time: Sun 17:00 UTC
  sla_hours: 12
  duckdb_table: socrata.street_permits
  incremental: TRUE (last 7 days)
  partition_by: created_date
  expected_rows: ~500K/week
  notes: Largest dataset; consider parallel pagination if >1hr fetch time

capital_intersections:
  fourfour_id: 97nd-ff3i
  frequency: WEEKLY
  refresh_time: Sun 18:00 UTC
  sla_hours: 12
  duckdb_table: socrata.capital_intersections
  incremental: FALSE (small dataset)
  expected_rows: ~100

street_construction_inspections:
  fourfour_id: ydkf-mpxb
  frequency: WEEKLY
  refresh_time: Sun 18:30 UTC
  sla_hours: 12
  duckdb_table: socrata.street_construction_inspections
  incremental: TRUE
  expected_rows: ~200K/week

street_closures_block:
  fourfour_id: i6b5-j7bu
  frequency: WEEKLY
  refresh_time: Sun 19:00 UTC
  sla_hours: 12
  duckdb_table: socrata.street_closures_block
  incremental: FALSE
  expected_rows: ~50

street_resurfacing_inhouse:
  fourfour_id: ffaf-8mrv
  frequency: WEEKLY
  refresh_time: Sun 19:30 UTC
  sla_hours: 12
  duckdb_table: socrata.street_resurfacing_inhouse
  incremental: TRUE
  expected_rows: ~10K/week

street_resurfacing_schedule:
  fourfour_id: xnfm-u3k5
  frequency: WEEKLY
  refresh_time: Sun 20:00 UTC
  sla_hours: 12
  duckdb_table: socrata.street_resurfacing_schedule
  incremental: FALSE
  expected_rows: ~5K
```

#### Contractor & Vendor (3)

```yaml
NYCDOT_Awarded_Contracts:
  fourfour_id: 9u5s-8sd8
  frequency: WEEKLY
  refresh_time: Sun 20:30 UTC
  sla_hours: 12
  duckdb_table: socrata.nycdot_awarded_contracts
  incremental: FALSE (contract dataset; changes tracked by award_date)
  expected_rows: ~1K

Prequalified_Firms:
  fourfour_id: szkz-syh6
  frequency: WEEKLY
  refresh_time: Sun 21:00 UTC
  sla_hours: 24 (vendor list; slower updates OK)
  duckdb_table: socrata.prequalified_firms
  incremental: FALSE
  expected_rows: ~2K

Recent_Contract_Awards:
  fourfour_id: qyyg-4tf5
  frequency: WEEKLY
  refresh_time: Sun 21:30 UTC
  sla_hours: 12
  duckdb_table: socrata.recent_contract_awards
  incremental: TRUE (last 30 days)
  expected_rows: ~500/week
```

#### Budget (1)

```yaml
street_resurfacing_schedule:
  # (listed above; overlaps with construction category)
```

---

### MONTHLY REFRESH (3 datasets) — 1st of Month, 12:00 AM

#### Equity & Demographic Base Snapshots (3)

```yaml
EquityNYC_Data:
  fourfour_id: 8ek7-jxw6
  frequency: MONTHLY
  refresh_time: 1st month, 00:00 UTC
  sla_hours: 24
  duckdb_table: socrata.equity_nyc_data
  incremental: FALSE (annual refresh, but snapshot monthly for trend)
  expected_rows: ~100–500 (aggregated metrics)

Demographics_by_Borough:
  fourfour_id: 6khm-nrue
  frequency: MONTHLY
  refresh_time: 1st month, 01:00 UTC
  sla_hours: 24
  duckdb_table: socrata.demographics_by_borough
  incremental: FALSE
  expected_rows: ~50

Demographic_Housing_Profiles:
  fourfour_id: cu9u-3r5e
  frequency: MONTHLY
  refresh_time: 1st month, 02:00 UTC
  sla_hours: 24
  duckdb_table: socrata.demographic_housing_profiles
  incremental: FALSE
  expected_rows: ~50
```

---

### QUARTERLY REFRESH (4 datasets) — Q Start, 12:00 AM

#### Reference & Geographic (4)

```yaml
lot_info:
  fourfour_id: i642-2fxq
  frequency: QUARTERLY
  refresh_time: Q1/Q2/Q3/Q4 1st, 00:00 UTC
  duckdb_table: socrata.lot_info
  incremental: FALSE (static reference)
  expected_rows: ~1.2M

mappluto:
  fourfour_id: 64uk-42ks
  frequency: QUARTERLY
  refresh_time: Q start + 1 hour
  duckdb_table: socrata.mappluto
  incremental: FALSE
  expected_rows: ~858K

sidewalk_planimetric:
  fourfour_id: vfx9-tbb6
  frequency: QUARTERLY
  refresh_time: Q start + 2 hours
  duckdb_table: socrata.sidewalk_planimetric
  incremental: FALSE
  expected_rows: ~50K

curb_metal_protruding:
  fourfour_id: i2y3-sx2e
  frequency: QUARTERLY
  refresh_time: Q start + 3 hours
  duckdb_table: socrata.curb_metal_protruding
  incremental: FALSE
  expected_rows: ~23K
```

---

### ANNUAL REFRESH (2 datasets) — Jan 1, 12:00 AM

#### Census & Population (2)

```yaml
Census_Tracts_2020:
  fourfour_id: 63ge-mke6
  frequency: ANNUAL
  refresh_time: Jan 1, 00:00 UTC
  sla_hours: 48
  duckdb_table: socrata.census_tracts_2020
  note: Updates only on decennial census (2030 next)
  expected_rows: ~2K tracts

Census_Blocks_2020:
  fourfour_id: wmsu-5muw
  frequency: ANNUAL
  refresh_time: Jan 1, 01:00 UTC
  sla_hours: 48
  note: Updates only on decennial census (2030 next)
  expected_rows: ~300K blocks
```

---

### STATIC/ON-DEMAND (5 datasets) — Check Quarterly

#### Reference (5)

```yaml
step_streets:
  fourfour_id: u9au-h79y
  frequency: STATIC
  refresh_trigger: Quarterly check (Jan/Apr/Jul/Oct)
  duckdb_table: socrata.step_streets
  expected_rows: ~110

pedestrian_demand:
  fourfour_id: fwpa-qxaf
  frequency: STATIC
  refresh_trigger: Quarterly check
  duckdb_table: socrata.pedestrian_demand
  expected_rows: ~127K

accessible_pedestrian_signals:
  fourfour_id: de3m-c5p4
  frequency: STATIC
  refresh_trigger: Quarterly check
  duckdb_table: socrata.accessible_pedestrian_signals
  expected_rows: ~TBD

Population_Community_Districts:
  fourfour_id: xi7c-iiu2
  frequency: STATIC (annual updates)
  refresh_trigger: Check Jan 1; pull if changed
  duckdb_table: socrata.population_community_districts
  expected_rows: ~71

Recent_Contract_Awards:
  # Treat as weekly (listed above)
```

---

## DuckDB Schema & Storage

### Database Structure

```sql
-- Create schema
CREATE SCHEMA IF NOT EXISTS socrata;

-- Example: inspection table
CREATE TABLE IF NOT EXISTS socrata.inspection (
  inspection_id VARCHAR PRIMARY KEY,
  created_date TIMESTAMP,
  scheduled_date TIMESTAMP,
  borough VARCHAR,
  status VARCHAR,
  inspector_id VARCHAR,
  _loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  _source_fourfour VARCHAR DEFAULT 'dntt-gqwq'
) USING PARQUET PARTITION BY (created_date);

-- Delta Lake table (MotherDuck live table)
CREATE TABLE IF NOT EXISTS socrata_inspection_delta AS 
SELECT * FROM socrata.inspection 
WHERE _loaded_at > (SELECT MAX(_loaded_at) FROM socrata_inspection_delta);
```

### Storage Strategy

- **Local DuckDB:** Parquet files in `./data/socrata/` for development
- **MotherDuck:** All tables auto-synced as Delta Live Tables
- **Partitioning:** By date (created_date, updated_date) for performance
- **Retention:** 
  - Daily datasets: 2 years rolling window
  - Weekly datasets: 5 years rolling window
  - Reference datasets: All history (static)

---

## Ingestion Pipeline Code (Pseudocode)

```python
# socrata_ingestion.py
import duckdb
import motherduck
import requests
from datetime import datetime, timedelta

def ingest_dataset(fourfour_id, dataset_name, refresh_freq='DAILY'):
    """Ingest Socrata dataset into DuckDB"""
    
    # 1. Fetch from Socrata API
    url = f"https://data.cityofnewyork.us/api/views/{fourfour_id}/rows.json?$limit=100000"
    
    # 2. For incremental refresh, filter by date
    if refresh_freq == 'DAILY':
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        url += f"&$where=created_date>'{yesterday}'"
    
    response = requests.get(url, headers={'User-Agent': 'NYC-DOT-Ingestion/1.0'})
    data = response.json()
    
    # 3. Write to DuckDB
    conn = duckdb.connect(':memory:')
    df = pd.DataFrame(data)
    
    # Add metadata columns
    df['_loaded_at'] = datetime.now()
    df['_source_fourfour'] = fourfour_id
    
    # Write to local DuckDB
    conn.execute(f"INSERT INTO socrata.{dataset_name} SELECT * FROM df")
    
    # 4. Sync to MotherDuck
    md_conn = motherduck.connect()
    md_conn.execute(f"CREATE OR REPLACE TABLE nyc_dot.{dataset_name} AS SELECT * FROM local.socrata.{dataset_name}")
    
    return f"✅ {dataset_name}: {len(df)} rows loaded"

# Schedule all ingestions
schedule.every().day.at("06:00").do(lambda: ingest_dataset('dntt-gqwq', 'inspection', 'DAILY'))
schedule.every().day.at("06:15").do(lambda: ingest_dataset('6kbp-uz6m', 'violations', 'DAILY'))
# ... (all 15 daily datasets)

schedule.every().sunday.at("17:00").do(lambda: ingest_dataset('tqtj-sjs8', 'street_permits', 'WEEKLY'))
# ... (all weekly datasets)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Monitoring & Alerting

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| **Ingestion Lateness** | > SLA hours | Notify ops team; check API status |
| **Row Count Variance** | > 20% change | Flag potential data quality issue |
| **API Response Time** | > 60 seconds | Retry with backoff; log for troubleshooting |
| **Failed Fetch** | Any failure | Retry 3x; escalate after 3 failures |
| **Storage Size** | > 500 GB | Archive old partitions; alert ops |
| **Duplicate Rows** | > 0.5% | Investigate and deduplicate |

---

## Failure Recovery

**If ingestion fails:**
1. **Retry:** Auto-retry 3x with exponential backoff (5s, 10s, 20s)
2. **Alert:** After 3 failures, email ops + Slack #data-incidents
3. **Fallback:** Use previous day's snapshot (≤24hr stale data acceptable)
4. **Manual:** On-call engineer can manually re-trigger via CLI

**If source dataset corrupts:**
1. Pause ingestion for that dataset
2. Alert NYC Open Data support (via support.socrata.com)
3. Revert to last clean snapshot
4. Resume once source is fixed

---

## Maintenance & Optimization

- **Weekly:** Check ingestion logs for slow datasets; optimize if >1hr
- **Monthly:** Audit storage usage; archive old partitions if >90% full
- **Quarterly:** Review SLA compliance; update dataset list if new datasets added
- **Annually:** Review retention policy; archive datasets >5 years old if not needed

---

**STATUS: SOURCE OF TRUTH FOR ALL 37-DATASET INGESTION PIPELINE**

**Version:** 1.0 | **Date:** 2026-06-17 | **Mandatory Status:** ALL 37 REQUIRED

