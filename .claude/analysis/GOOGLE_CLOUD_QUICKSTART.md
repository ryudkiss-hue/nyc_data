# Google Cloud Quick Start (5 Minutes)

Get all 26 NYC datasets in Google Cloud in under an hour.

---

## Prerequisites

- Google Cloud account (free trial gives $300 credit)
- 30 minutes of time
- All 26 datasets cached locally (check: `ls data/cache/ | wc -l`)

---

## Step 1: Install & Authenticate (5 min)

```bash
# Install Google Cloud SDK
pip install google-cloud-storage google-cloud-bigquery

# Authenticate
gcloud auth login
gcloud auth application-default login
```

---

## Step 2: Create GCP Project & Resources (5 min)

```bash
# Set your project ID (replace with yours)
export GCP_PROJECT="nyc-mission-control"

# Create bucket
gsutil mb -p $GCP_PROJECT gs://nyc-mission-control-data

# Create BigQuery dataset
bq mk --project_id=$GCP_PROJECT nyc_datasets
```

---

## Step 3: Upload to GCS (10-15 min)

```bash
python sync_to_gcs.py --bucket nyc-mission-control-data
```

Monitor progress: Shows file size, upload time, throughput.

---

## Step 4: Load to BigQuery (20-30 min)

```bash
python load_to_bigquery.py \
  --project $GCP_PROJECT \
  --dataset nyc_datasets \
  --bucket nyc-mission-control-data
```

Loads all 26 tables into BigQuery. Auto-detects schema from Parquet.

---

## Step 5: Query Your Data

### Via BigQuery CLI

```bash
bq query --use_legacy_sql=false "
  SELECT COUNT(*) FROM \`$GCP_PROJECT.nyc_datasets.complaints_311\`
"
```

### Via BigQuery Python

```python
from google.cloud import bigquery

client = bigquery.Client(project='your-project-id')
df = client.query("""
  SELECT borough, COUNT(*) as violations
  FROM \`your-project-id.nyc_datasets.violations\`
  WHERE created_date > CURRENT_DATE() - 30
  GROUP BY borough
""").to_dataframe()
print(df)
```

### Via Web Console

Visit: https://console.cloud.google.com/bigquery

Select your project → nyc_datasets → run SQL directly in browser.

---

## Total Cost (First Month)

- Data transfer: ~$0.20
- BigQuery storage: ~$10
- Queries (estimate): ~$5
- **Total: ~$15** (includes free tier)

---

## Common Commands

```bash
# Check buckets
gsutil ls

# Check BigQuery datasets
bq ls --project_id=$GCP_PROJECT

# Query via CLI
bq query "SELECT * FROM \`$GCP_PROJECT.nyc_datasets.inspection\` LIMIT 10"

# Download from GCS
gsutil cp gs://nyc-mission-control-data/nyc-datasets/inspection.parquet .

# Check file in GCS
gsutil stat gs://nyc-mission-control-data/nyc-datasets/inspection.parquet
```

---

## Next: Share with Team

```bash
# Give team member access to BigQuery dataset:
gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member=user:colleague@company.com \
  --role=roles/bigquery.dataEditor

# Now they can query the data directly!
```

---

## Troubleshooting

**"Bucket not found"**
```bash
gsutil ls gs://nyc-mission-control-data
# If not there, create it: gsutil mb gs://nyc-mission-control-data
```

**"Dataset not found"**
```bash
bq ls --project_id=$GCP_PROJECT
# If not there, create it: bq mk --project_id=$GCP_PROJECT nyc_datasets
```

**"Permission denied"**
```bash
gcloud auth login
gcloud auth application-default login
```

---

## What's Next?

1. **Share data:** Give team access to BigQuery dataset (see "Share with Team" above)
2. **Build dashboards:** Looker Studio or Data Studio connected to BigQuery
3. **Automate updates:** Schedule daily fetch + sync to GCS + BigQuery load
4. **Combine platforms:** Keep MotherDuck for fast personal analytics, BigQuery for team

---

Time to complete: ~45-60 minutes total  
Cost: ~$15/month  
Complexity: Low (scripts handle everything)

Get started:
```bash
python sync_to_gcs.py --bucket nyc-mission-control-data
```
