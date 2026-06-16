# Google Cloud Integration Strategy

Store and query all 26 NYC datasets in Google Cloud (GCS + BigQuery).

---

## Overview

**Why Google Cloud?**
- **GCS:** Cheap cloud backup ($0.02/GB/month), shareable file access
- **BigQuery:** SQL warehouse for team analytics ($0.025/GB queries, first 1TB/month free)
- **Integration:** DuckDB/Parquet native support, seamless with current pipeline

**Time to full Google sync: ~60 minutes (first time)**

| Component | Time | Cost |
|-----------|------|------|
| GCS upload | 10-15 min | ~$0.20 (data transfer) |
| BigQuery load | 20-30 min | ~$0.10 (query cost) |
| Monthly | — | ~$15-25/month |
| First year | — | ~$200 |

---

## Setup (One-Time)

### 1. Install Google Cloud SDK

```bash
# macOS:
brew install --cask google-cloud-sdk

# Linux/WSL:
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Then authenticate:
gcloud auth login
gcloud auth application-default login
```

### 2. Create GCP Project

```bash
# Set your GCP project ID
export GCP_PROJECT="your-project-id"

# Create project (if needed):
gcloud projects create $GCP_PROJECT

# Set as default:
gcloud config set project $GCP_PROJECT
```

### 3. Enable APIs

```bash
# Enable required APIs:
gcloud services enable storage-api.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable bigquerydatatransfer.googleapis.com
```

### 4. Create GCS Bucket

```bash
# Create bucket (globally unique name):
gsutil mb -p $GCP_PROJECT gs://nyc-mission-control-data

# Verify:
gsutil ls gs://nyc-mission-control-data
```

### 5. Create BigQuery Dataset

```bash
# Create dataset:
bq mk --project_id=$GCP_PROJECT nyc_datasets

# Verify:
bq ls --project_id=$GCP_PROJECT
```

### 6. Install Python Dependencies

```bash
pip install google-cloud-storage google-cloud-bigquery
```

---

## Usage

### Option A: Upload to GCS Only (Simplest)

```bash
python sync_to_gcs.py --bucket nyc-mission-control-data
```

**What it does:**
- Uploads all 26 Parquet files to GCS
- Creates `gs://nyc-mission-control-data/nyc-datasets/` folder
- Shows progress and throughput

**Cost:** ~$0.20/transfer + $0.20/month storage  
**Time:** ~10-15 minutes (4 parallel workers)

**Query from anywhere:**
```bash
# List files:
gsutil ls gs://nyc-mission-control-data/nyc-datasets/

# Download one file:
gsutil cp gs://nyc-mission-control-data/nyc-datasets/inspection.parquet .

# Query via Python/DuckDB:
import duckdb
df = duckdb.query("SELECT * FROM read_parquet('gs://nyc-mission-control-data/nyc-datasets/inspection.parquet')").df()
```

---

### Option B: Load to BigQuery (Recommended for Team)

```bash
# Step 1: Upload to GCS (required for BigQuery load)
python sync_to_gcs.py --bucket nyc-mission-control-data

# Step 2: Load from GCS to BigQuery
python load_to_bigquery.py \
  --project your-gcp-project \
  --dataset nyc_datasets \
  --bucket nyc-mission-control-data
```

**What it does:**
1. Creates BigQuery dataset `nyc_datasets`
2. Loads all 26 Parquet files from GCS
3. Auto-detects schema from Parquet
4. Creates 26 tables in BigQuery

**Cost:** 
- Transfer: ~$0.10
- Queries: Free first 1TB/month (usually ~$0.025/GB after)
- Storage: ~$10/month for 26 tables

**Time:** ~30-40 minutes total (GCS upload + BigQuery load)

**Query from team:**

```bash
# BigQuery CLI:
bq query --use_legacy_sql=false "
  SELECT COUNT(*) as total_violations
  FROM \`your-gcp-project.nyc_datasets.violations\`
  WHERE created_date > CURRENT_DATE() - 7
"

# BigQuery Python API:
from google.cloud import bigquery

client = bigquery.Client(project='your-gcp-project')
df = client.query("""
  SELECT borough, COUNT(*) as ramps
  FROM \`your-gcp-project.nyc_datasets.ramp_progress\`
  WHERE status = 'COMPLETED'
  GROUP BY borough
""").to_dataframe()
print(df)

# BigQuery SQL Notebooks/Studio (web UI):
# Visit: console.cloud.google.com/bigquery
# Run SQL directly in browser
```

---

### Option C: Sync All Platforms at Once (Complete)

```bash
python sync_all_platforms.py \
  --platforms local motherduck gcs bigquery \
  --motherduck-token your_token \
  --gcs-bucket nyc-mission-control-data \
  --gcp-project your-gcp-project \
  --bq-dataset nyc_datasets
```

**What it does:**
- Shows which steps to run
- Provides exact commands for each platform
- Can auto-execute with `--auto-run` (if implemented)

**Total time:** ~60 minutes (all platforms in sequence)

---

## Advanced Options

### Load Specific Datasets

```bash
# GCS:
python sync_to_gcs.py \
  --bucket nyc-mission-control-data \
  --datasets inspection violations complaints_311

# BigQuery:
python load_to_bigquery.py \
  --project your-gcp-project \
  --dataset nyc_datasets \
  --bucket nyc-mission-control-data \
  --datasets inspection violations complaints_311
```

### Parallel Workers

```bash
# Use more workers for faster upload (be careful with API limits):
python sync_to_gcs.py --bucket nyc-mission-control-data --workers 8

# Use fewer workers for lighter load:
python sync_to_gcs.py --bucket nyc-mission-control-data --workers 2
```

### Dry Run (See What Would Happen)

```bash
python sync_to_gcs.py --bucket nyc-mission-control-data --dry-run
python load_to_bigquery.py --project your-gcp-project --dataset nyc_datasets --dry-run
```

### Load from Local Cache (No GCS)

```bash
# Directly to BigQuery from local Parquet:
python load_to_bigquery.py \
  --project your-gcp-project \
  --dataset nyc_datasets \
  --source local
```

---

## BigQuery Best Practices

### Query Performance

**Good (filtered, efficient):**
```sql
-- Filter by date and borough
SELECT * 
FROM `project.nyc_datasets.inspection`
WHERE created_date > CURRENT_DATE() - 30
  AND borough = 'MANHATTAN'
LIMIT 1000
```

**Bad (full table scan):**
```sql
SELECT * FROM `project.nyc_datasets.complaints_311`  -- 21.3M rows, slow!
```

### Partitioning Large Tables

For tables with 1M+ rows, partition by date:

```sql
-- Create partitioned table (after initial load):
CREATE OR REPLACE TABLE `project.nyc_datasets.complaints_311_partitioned`
PARTITION BY DATE(created_date) AS
SELECT * FROM `project.nyc_datasets.complaints_311`;
```

### Cost Optimization

```sql
-- Check table sizes:
SELECT 
  table_name,
  ROUND(size_bytes / (1024**3), 2) as size_gb,
  row_count
FROM `project.nyc_datasets.__TABLES__`
ORDER BY size_bytes DESC;

-- Estimate query cost before running:
-- BigQuery shows "bytes processed" before you run
-- Cost = bytes_processed / (1024**4) * $0.025
```

### Common Queries for NYC Data

```sql
-- Violations by borough (last 30 days):
SELECT borough, COUNT(*) as violation_count
FROM `project.nyc_datasets.violations`
WHERE created_date > CURRENT_DATE() - 30
GROUP BY borough
ORDER BY violation_count DESC;

-- Ramp completion rate by borough:
SELECT 
  borough,
  COUNT(*) as total_ramps,
  SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed,
  ROUND(100.0 * SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_complete
FROM `project.nyc_datasets.ramp_progress`
GROUP BY borough
ORDER BY pct_complete DESC;

-- 311 complaints trends:
SELECT 
  DATE_TRUNC(created_date, MONTH) as month,
  complaint_type,
  COUNT(*) as complaint_count
FROM `project.nyc_datasets.complaints_311`
WHERE YEAR(created_date) = 2026
GROUP BY month, complaint_type
ORDER BY month DESC, complaint_count DESC;

-- Conflicts between permits and inspections (spatial join):
SELECT 
  p.permit_id,
  COUNT(DISTINCT i.objectid) as nearby_inspections,
  ST_DISTANCE(p.location, i.location) as min_distance_meters
FROM `project.nyc_datasets.street_permits` p
JOIN `project.nyc_datasets.inspection` i
  ON ST_DWithin(p.location, i.location, 100)  -- 100 meter radius
WHERE p.start_date <= DATE(i.created_date) 
  AND DATE(i.created_date) <= p.end_date
GROUP BY p.permit_id
HAVING nearby_inspections > 0
ORDER BY nearby_inspections DESC;
```

---

## Connecting from Other Tools

### Looker Studio (Free Dashboards)

```
1. Visit: looker.studio
2. New Report → BigQuery
3. Select project.nyc_datasets.{table}
4. Build visualizations (no code needed)
```

### Google Sheets

```
1. In Sheet, Insert → Function → QUERY
2. Query BigQuery:
=QUERY("SELECT * FROM `project.nyc_datasets.inspection` LIMIT 10")
```

### Python Notebook (Colab)

```python
from google.colab import bigquery
import pandas as pd

# Query BigQuery directly in Colab
df = bigquery.magics.context.client.query("""
  SELECT * FROM `project.nyc_datasets.violations`
  WHERE created_date > CURRENT_DATE() - 30
""").to_dataframe()
df.head()
```

### DuckDB (Local + Cloud)

```python
import duckdb

# Query BigQuery from DuckDB:
df = duckdb.query("""
  SELECT * FROM 
  read_parquet('gs://nyc-mission-control-data/nyc-datasets/*.parquet')
  WHERE borough = 'MANHATTAN'
""").df()
```

---

## Troubleshooting

### "Bucket not found" or "403 Forbidden"

```bash
# Check bucket exists:
gsutil ls gs://nyc-mission-control-data

# Check permissions:
gcloud projects get-iam-policy $GCP_PROJECT

# Re-authenticate:
gcloud auth login
gcloud auth application-default login
```

### "BigQuery dataset not found"

```bash
# Create dataset:
bq mk --project_id=$GCP_PROJECT nyc_datasets

# Verify:
bq ls --project_id=$GCP_PROJECT
```

### "GCS upload slow"

```bash
# Use parallel uploads with gsutil:
gsutil -m cp -r data/cache/*.parquet gs://nyc-mission-control-data/nyc-datasets/

# Or reduce workers in Python script:
python sync_to_gcs.py --bucket nyc-mission-control-data --workers 2
```

### "BigQuery query expensive"

Check query cost before running:
```bash
bq query --dry_run --use_legacy_sql=false \
  "SELECT * FROM \`project.nyc_datasets.complaints_311\`"

# Output shows: "This query will process X bytes"
# Cost = X / (1024^4) * $0.025
```

If >1GB: Add WHERE filters or use partitioned tables.

### "Python module not found"

```bash
pip install google-cloud-storage google-cloud-bigquery
```

---

## Cost Analysis

### Storage

| Platform | Size | Cost/Month |
|----------|------|-----------|
| Local SSD | 500 MB | Free |
| GCS | 500 MB | $0.01 (at $0.02/GB/month) |
| BigQuery | 500 MB | $10 (at $0.025/GB month, actual: variable) |

### Query Costs

| Use Case | Monthly Cost |
|----------|-------------|
| 100 queries/month (1GB each) | ~$2.50 |
| 1000 queries/month (100MB avg) | ~$2.50 |
| Dashboard refresh (hourly) | ~$15 |

**Bottom line:** $10-30/month for single-user development, $50-100/month for team with dashboards.

---

## When to Use Each Platform

| Scenario | Platform |
|----------|----------|
| Just backing up data | GCS |
| Personal analysis (SQL) | BigQuery |
| Team dashboards | BigQuery + Looker |
| Real-time analytics | MotherDuck (faster) |
| Machine Learning | BigQuery ML |
| Compliance/retention | GCS (cheaper long-term) |
| All the above | Hybrid (local + MotherDuck + GCS + BQ) |

---

## Next Steps

1. **Setup GCP** (15 min): Follow Step 1-6 above
2. **Upload to GCS** (15 min): `python sync_to_gcs.py --bucket nyc-mission-control-data`
3. **Load to BigQuery** (30 min): `python load_to_bigquery.py --project your-project --dataset nyc_datasets`
4. **Query from team**: Share BigQuery dataset link with analysts
5. **Build dashboards** (optional): Looker Studio connected to BigQuery

---

## Files Included

```
.claude/analysis/
├── sync_to_gcs.py                      ← Upload to GCS
├── load_to_bigquery.py                 ← Load to BigQuery
├── sync_all_platforms.py               ← Orchestrate all platforms
├── GOOGLE_CLOUD_STRATEGY.md            ← This file
└── GOOGLE_CLOUD_SETUP.md               ← Detailed setup guide (coming)
```

---

**Questions?** See troubleshooting section above, or check:
- GCS docs: https://cloud.google.com/storage/docs
- BigQuery docs: https://cloud.google.com/bigquery/docs
- GCP auth: https://cloud.google.com/docs/authentication

---

Last updated: 2026-06-16  
Ready to use after GCP setup complete
