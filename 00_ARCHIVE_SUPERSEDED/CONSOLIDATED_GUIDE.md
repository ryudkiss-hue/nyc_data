# NYC DOT Sidewalk Toolkit — Consolidated Guide

**Master documentation for all 57 NYC Open Data datasets + multi-platform analytics**

**NOTE:** For current complete registry, see: [`SOCRATA_DATASETS_CONSOLIDATED.md`](docs/SOCRATA_DATASETS_CONSOLIDATED.md) (57 datasets with KPI mappings and visualizations)

Last updated: 2026-06-16  
Status: Production-ready

---

## Quick Start (5 Minutes)

### 1. Setup Environment
```bash
cp .env.example .env
# Edit .env with your credentials:
# - SOCRATA_APP_TOKEN (required)
# - ANTHROPIC_API_KEY (required)
# - MOTHERDUCK_TOKEN (optional, for cloud analytics)
```

### 2. Fetch Data (First Time: ~45-60 minutes)
```bash
python .claude/analysis/dataset_cache_monitor.py --watch 5
# Data fetches automatically, watch progress live
```

### 3. Populate Analytics Platforms (Choose One or All)

**PRIMARY: MotherDuck (Cloud Analytics)**
```bash
python .claude/analysis/optimized_motherduck_population.py
# 20-25 minutes, 4 parallel workers
# Query at: https://console.motherduck.com/
```

**FALLBACK: Local DuckDB**
```bash
duckdb ./data/local_db/nyc_mission_control.duckdb
# 2-3 minutes, creates indices
# Query via Python: import duckdb; conn = duckdb.connect('./data/local_db/nyc_mission_control.duckdb')
```

**OPTIONAL: Google Cloud**
```bash
python .claude/analysis/sync_to_gcs.py --bucket your-bucket
python .claude/analysis/load_to_bigquery.py --project your-project --dataset nyc_datasets
```

### 4. Start Using Data

**MotherDuck (Recommended):**
```python
import duckdb
import os

token = os.getenv('MOTHERDUCK_TOKEN')
conn = duckdb.connect(f'md:?motherduck_token={token}')

# Query any of 37 tables
df = conn.execute("SELECT * FROM inspection LIMIT 100").df()
```

**Local DuckDB (Fallback):**
```python
import duckdb

conn = duckdb.connect('./data/local_db/nyc_mission_control.duckdb')
df = conn.execute("SELECT COUNT(*) FROM violations").df()
```

**Dash Mission Control (UI):**
```bash
python app/dash_app.py
# Visit: http://localhost:8011
```

---

## Architecture

```
NYC Open Data (Socrata API)
        ↓
Local Parquet Cache (500 MB)
        ↓
┌───────┴────────────────────────┐
│                                │
↓ (PRIMARY)                      ↓ (FALLBACK)
MotherDuck Cloud                Local DuckDB
(20-25 min)                      (2-3 min)
│                                │
├─ Fast queries                  ├─ Always available
├─ Team accessible               ├─ No API needed
├─ Shared analytics              └─ Offline capable
└─ https://console.motherduck.com/
        ↓
┌───────┴────────────────────────┐
│ (OPTIONAL)                     │
↓                                ↓
Google Cloud                   Dash/Streamlit UI
- GCS Backup                   - Interactive dashboards
- BigQuery SQL Warehouse       - 30+ Plotly charts
- Looker Studio Dashboards     - Real-time updates
```

---

## Platform Details

### MotherDuck (PRIMARY - Recommended)

**Best for:** Team analytics, fast queries, cloud-native workflows

**Setup:**
```bash
# 1. Create account: https://console.motherduck.com/
# 2. Generate token in settings
# 3. Set env var: export MOTHERDUCK_TOKEN="md_..."
# 4. Populate: python .claude/analysis/optimized_motherduck_population.py
```

**Query from anywhere:**
```python
# Python
import duckdb
conn = duckdb.connect('md:?motherduck_token=your_token')
df = conn.execute("SELECT * FROM inspection").df()

# SQL Notebook: https://console.motherduck.com/
# Just run SQL directly in browser

# DuckDB CLI
duckdb "SELECT COUNT(*) FROM read_parquet('md:inspection')"
```

**Cost:** $0-20/month (free tier available, 10GB/month quota)

**Features:**
- Real-time collaboration (share queries with team)
- Automatic backups (cloud redundancy)
- Direct integration with Google Sheets, Looker
- No local infrastructure needed

---

### Local DuckDB (FALLBACK - Always Available)

**Best for:** Development, offline work, no API needed

**Setup:**
```bash
duckdb ./data/local_db/nyc_mission_control.duckdb
# Creates indices, optimizes for analytical queries
```

**Query:**
```python
import duckdb
conn = duckdb.connect('./data/local_db/nyc_mission_control.duckdb')

# Simple queries
df = conn.execute("SELECT * FROM inspection LIMIT 10").df()

# Complex analysis
df = conn.execute("""
  SELECT borough, COUNT(*) as violations
  FROM violations
  WHERE created_date > CURRENT_DATE - 30
  GROUP BY borough
""").df()
```

**Cost:** Free (uses local disk)

**Advantages:**
- Zero cloud costs
- Works offline
- No API quota limits
- Fast local queries (SSD-backed)

---

### Google Cloud (OPTIONAL - Warehouse)

**Best for:** Large-scale analysis, team data warehouse, compliance

**Setup:**
```bash
# 1. gcloud auth login
# 2. gsutil mb gs://your-bucket
# 3. python .claude/analysis/sync_to_gcs.py --bucket your-bucket
# 4. python .claude/analysis/load_to_bigquery.py --project your-project
```

**Query:**
```bash
# CLI
bq query "SELECT COUNT(*) FROM `project.dataset.inspection`"

# Python
from google.cloud import bigquery
client = bigquery.Client(project='your-project')
df = client.query("SELECT * FROM `project.dataset.inspection`").to_dataframe()
```

**Cost:** $10-25/month (GCS storage + BigQuery queries)

**When to use:**
- Team of 5+ analysts
- 100+ queries/day
- Compliance requirements (audit trails)
- Long-term data archival

---

## 57 datasets Overview (See SOCRATA_DATASETS_CONSOLIDATED.md for complete registry)

### Core SIM Data (Inspections & Violations)
- `inspection` (399K rows) — Sidewalk inspection records
- `violations` (312K rows) — Violation details
- `dismissals` (85K rows) — Dismissed complaints
- `built` (105K rows) — Construction projects
- `lot_info` (1.2M rows) — Property information
- `reinspection` (36K rows) — Follow-up inspections
- `correspondences` (30K rows) — Agency correspondence
- `tree_damage` (17K rows) — Tree damage assessments
- `curb_metal_protruding` (23K rows) — Curb hazards

### Accessibility (Ramps)
- `ramp_progress` (187K rows) — Ramp installation tracking ⭐
- `ramp_complaints` (6K rows) — ADA complaints
- `ramp_locations` (217K rows) — Historical ramp data

### Permits & Construction
- `street_permits` (3.6M rows) — All street work permits
- `street_construction_inspections` (11.5M rows) — Construction inspection records
- `capital_intersections` (7.8K rows) — Capital project locations
- `street_closures_block` (4.3K rows) — Temporary closure permits
- `street_resurfacing_schedule` (309K rows) — Planned paving projects
- `street_resurfacing_inhouse` (602K rows) — Completed paving work
- `weekly_construction` (75 rows) — ⚠️ Archived 2017
- `capital_blocks` (0 rows) — ⚠️ Empty
- `permit_stipulations` — ⚠️ API error

### Context Layers
- `complaints_311` (21.3M rows) — All 311 complaints
- `pedestrian_demand` (127K rows) — Pedestrian activity hotspots
- `mappluto` (858K rows) — NYC property parcels
- `sidewalk_planimetric` (50K rows) — Sidewalk network geometry
- `step_streets` (110 rows) — Historic step street locations

See: `jupyter_book/reference/dataset_registry.md` for full registry

---

## Common Tasks

### Query Ramp Completion Rate by Borough
```python
import duckdb
import os

# Use MotherDuck (primary)
token = os.getenv('MOTHERDUCK_TOKEN')
conn = duckdb.connect(f'md:?motherduck_token={token}')

df = conn.execute("""
  SELECT 
    UPPER(borough) as borough,
    COUNT(*) as total_ramps,
    SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed,
    ROUND(100.0 * SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_complete
  FROM ramp_progress
  GROUP BY borough
  ORDER BY pct_complete DESC
""").df()

print(df)
```

### Detect Conflicts Between Permits and Inspections
```python
df = conn.execute("""
  SELECT 
    p.permit_id,
    COUNT(DISTINCT i.objectid) as nearby_inspections
  FROM street_permits p
  JOIN inspection i 
    ON ST_DWithin(p.location::geometry, i.the_geom::geometry, 100)
    AND p.start_date <= DATE(i.created_date) AND DATE(i.created_date) <= p.end_date
  GROUP BY p.permit_id
  HAVING COUNT(DISTINCT i.objectid) > 0
  ORDER BY nearby_inspections DESC
  LIMIT 100
""").df()
```

### Export to CSV/Excel/PDF
```bash
# Via Python
df.to_csv('output.csv', index=False)
df.to_excel('output.xlsx', index=False)

# Via CLI
socrata export violations.csv --where "created_date > '2026-05-01'"
```

---

## Fallback Strategy

**If MotherDuck unavailable:**
```python
import duckdb
import os

# Try MotherDuck first
token = os.getenv('MOTHERDUCK_TOKEN')
if token:
    try:
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        conn.execute("SELECT 1")  # Test connection
        print("✓ Using MotherDuck")
    except:
        conn = None

# Fallback to local DuckDB
if not conn:
    print("⚠️ Falling back to local DuckDB")
    conn = duckdb.connect('./data/local_db/nyc_mission_control.duckdb')

# Query works the same either way
df = conn.execute("SELECT * FROM inspection LIMIT 100").df()
```

---

## Environment Configuration

See `.env.example` for all variables:

**Required:**
- `SOCRATA_APP_TOKEN` — NYC Open Data API token
- `ANTHROPIC_API_KEY` — Claude API key

**Optional (if using):**
- `MOTHERDUCK_TOKEN` — Cloud analytics
- `GCP_PROJECT`, `GCS_BUCKET` — Google Cloud
- `PG_DSN` — PostgreSQL data warehouse

See: `.claude/analysis/ENV_CONSOLIDATION.md` for full details

---

## Documentation Files

| File | Purpose |
|------|---------|
| **CONSOLIDATED_GUIDE.md** | This file — master documentation |
| **CLAUDE.md** | Project overview & architecture |
| **README.md** | GitHub project summary |
| **QUICKSTART.md** | Getting started guide |
| **docs/SOCRATA_DATASETS_CONSOLIDATED.md** | All 57 datasets with KPI mappings |
| **.claude/analysis/MOTHERDUCK_STRATEGY.md** | Cloud analytics guide |
| **.claude/analysis/GOOGLE_CLOUD_STRATEGY.md** | GCS + BigQuery guide |
| **.claude/analysis/ENV_CONSOLIDATION.md** | Environment variables |

---

## Support & Troubleshooting

**MotherDuck won't connect?**
```bash
# Check token
echo $MOTHERDUCK_TOKEN

# Regenerate at: https://console.motherduck.com/
# Test: duckdb "SELECT 1"
```

**Local DuckDB not found?**
```bash
duckdb ./data/local_db/nyc_mission_control.duckdb
# Creates database and indices
```

**Data fetch stuck?**
```bash
python .claude/analysis/dataset_cache_monitor.py --watch 5
# Shows which datasets are cached
```

**Query too slow?**
```python
# Use WHERE filters to reduce data
df = conn.execute("""
  SELECT * FROM complaints_311 
  WHERE created_date > CURRENT_DATE - 30
  AND borough = 'MANHATTAN'
  LIMIT 1000
""").df()
```

---

## Next Steps

1. **Setup:** `cp .env.example .env` + add your tokens
2. **Fetch:** `python .claude/analysis/dataset_cache_monitor.py --watch 5`
3. **Populate:** `python .claude/analysis/optimized_motherduck_population.py` (MotherDuck)
4. **Analyze:** Start querying your 57 datasets
5. **Share:** Invite team members to MotherDuck workspace

---

## Resources

- **MotherDuck Docs:** https://motherduck.com/docs/
- **DuckDB Docs:** https://duckdb.org/docs/
- **NYC Open Data:** https://data.cityofnewyork.us/
- **Socrata API:** https://dev.socrata.com/

---

**Questions?** See `.claude/analysis/` for detailed guides on each platform.

**All 57 datasets ready. You are here. Go analyze.**

---

**IMPORTANT:** This document is part of the legacy documentation suite. For current authoritative sources, see:
- **SOCRATA_DATASETS_CONSOLIDATED.md** — Complete 57-dataset registry with KPI mappings
- **VISUALIZATION_REGISTRY_57_DATASETS.md** — 100+ charts and dashboard specifications
- **KPI_MAPPINGS_37_DATASETS.md** — All 51 KPIs with calculations and ownership
- **ERD_37_DATASETS_VERIFIED.md** — Entity relationships and primary/foreign keys
- **DUCKDB_INGESTION_CONFIG.md** — Automated pipeline configuration

