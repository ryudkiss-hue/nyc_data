# Google Cloud Run Deployment Guide

Deploy NYC Sidewalk Toolkit to Google Cloud Run with full Dash + API capabilities.

---

## Architecture

```
User Browser/API Client
        ↓
    Cloud Run (1 container, 2 workers)
        ├─ Dash Mission Control (port 8080/)
        ├─ FastAPI Backend (port 8080/api/)
        └─ Data Layer
            ├─ MotherDuck (cloud, PRIMARY)
            └─ DuckDB (local cache, FALLBACK)
```

---

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Cloud Run API** enabled
3. **GitHub repository** (for CI/CD)
4. **Secrets configured** (see Setup step 2)

---

## Step 1: Setup GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$PROJECT_ID

# Create service account for Cloud Run
gcloud iam service-accounts create cloud-run-deployer \
  --display-name="Cloud Run Deployer" \
  --project=$PROJECT_ID

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cloud-run-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cloud-run-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

---

## Step 2: Configure GitHub Secrets

**In GitHub Settings → Secrets and variables → Actions:**

```
GCP_PROJECT_ID = your-gcp-project-id

WORKLOAD_IDENTITY_PROVIDER = projects/123456789/locations/global/workloadIdentityPools/github/providers/github

SERVICE_ACCOUNT = cloud-run-deployer@your-project-id.iam.gserviceaccount.com

SOCRATA_APP_TOKEN = your-socrata-token

ANTHROPIC_API_KEY = your-claude-api-key

MOTHERDUCK_TOKEN = your-motherduck-token
```

---

## Step 3: Deploy Manually (First Time)

```bash
# Build Docker image
docker build -t gcr.io/$PROJECT_ID/nyc-sidewalk-toolkit:latest -f Dockerfile.cloudbuild .

# Push to Container Registry
gcloud auth configure-docker
docker push gcr.io/$PROJECT_ID/nyc-sidewalk-toolkit:latest

# Deploy to Cloud Run
gcloud run deploy nyc-sidewalk-toolkit \
  --image gcr.io/$PROJECT_ID/nyc-sidewalk-toolkit:latest \
  --region northamerica-northeast2 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 600 \
  --set-env-vars SOCRATA_APP_TOKEN=$SOCRATA_APP_TOKEN,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,MOTHERDUCK_TOKEN=$MOTHERDUCK_TOKEN \
  --project $PROJECT_ID

# Get the URL
gcloud run services describe nyc-sidewalk-toolkit \
  --region northamerica-northeast2 \
  --format 'value(status.url)' \
  --project $PROJECT_ID
```

---

## Step 4: Enable Automatic Deployment

**Option A: GitHub Actions (Recommended)**

1. Fork/clone the repository
2. Set GitHub Secrets (see Step 2 above)
3. Push to `main` or `claude/elegant-ptolemy-kctbqo`
4. GitHub Actions automatically builds and deploys

**Option B: Google Cloud Build**

1. Connect GitHub repo to Cloud Build
2. Create trigger for `main` branch
3. Select `cloudbuild.yaml` as build config
4. Set substitutions and environment variables

---

## Step 5: Verify Deployment

```bash
# Get service URL
URL=$(gcloud run services describe nyc-sidewalk-toolkit \
  --region northamerica-northeast2 \
  --format 'value(status.url)' \
  --project $PROJECT_ID)

echo "Service URL: $URL"

# Test health check
curl $URL/api/health

# Check active platform
curl $URL/api/platform

# List datasets
curl $URL/api/datasets | jq .

# Visit Dash dashboard
open $URL/dash/
```

---

## Usage

### Via Web Browser

1. Visit: `https://your-cloud-run-url/dash/`
2. Explore Dash Mission Control dashboard
3. Real-time data, interactive charts

### Via REST API

```bash
# Get health status
curl https://your-url/api/health

# List all datasets
curl https://your-url/api/datasets

# Execute query
curl -X POST https://your-url/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) FROM inspection"}'

# Get dataset stats
curl https://your-url/api/dataset/violations/stats
```

### Via Python

```python
import requests

BASE_URL = "https://your-cloud-run-url"

# Get platform info
platform = requests.get(f"{BASE_URL}/api/platform").json()
print(f"Using: {platform['platform']}")

# Execute query
query_result = requests.post(
    f"{BASE_URL}/api/query",
    json={"query": "SELECT * FROM inspection LIMIT 100"}
).json()

df = pd.DataFrame(query_result['data'])
print(df)
```

---

## Cost Management

**Cloud Run Pricing:**
- Memory: $0.00001667 per GB-second
- Requests: $0.40 per million requests
- Free tier: 2M requests/month, 400K GB-seconds/month

**Monthly estimate (moderate usage):**
- 1000 requests/day: ~$0.01
- 2GB memory, 1hr/day running: ~$1.50
- Data egress: ~$0.10
- **Total: ~$1.60/month**

**Cost optimization:**
```bash
# Reduce memory if not needed
gcloud run deploy nyc-sidewalk-toolkit --memory 1Gi

# Set min/max instances
gcloud run deploy nyc-sidewalk-toolkit --min-instances 0 --max-instances 2

# Enable autoscaling
gcloud run deploy nyc-sidewalk-toolkit --concurrency 80
```

---

## Monitoring & Logging

```bash
# View logs
gcloud run logs read nyc-sidewalk-toolkit --region northamerica-northeast2

# Live logs
gcloud run logs read nyc-sidewalk-toolkit --region northamerica-northeast2 --follow

# Set up alerts
gcloud monitoring alert-policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="Cloud Run Errors"
```

---

## Troubleshooting

**"Health check failed"**
- Check logs: `gcloud run logs read nyc-sidewalk-toolkit`
- Verify tokens are set correctly in Cloud Run environment
- Test locally first: `python app/cloud_run.py`

**"MotherDuck connection timeout"**
- Verify MOTHERDUCK_TOKEN is set
- Cloud Run should automatically fallback to DuckDB
- Check platform: `curl https://your-url/api/platform`

**"Out of memory"**
- Increase memory allocation (default: 2GB)
- `gcloud run deploy ... --memory 4Gi`

**"Cold start too slow"**
- Enable min-instances: `gcloud run deploy ... --min-instances 1`
- Use max-instances to control costs: `gcloud run deploy ... --max-instances 5`

---

## CI/CD Pipeline

### Automatic deployment on push:

```
git push to main/claude/elegant-ptolemy-kctbqo
        ↓
GitHub Actions Workflow Triggered
        ↓
1. Build Docker image
2. Push to Container Registry
3. Deploy to Cloud Run
4. Verify health check
        ↓
Service available at Cloud Run URL
```

### View deployment status:

```bash
# Check GitHub Actions
gh run list -w deploy-cloud-run.yml

# Check Cloud Run revisions
gcloud run revisions list --service nyc-sidewalk-toolkit

# View active revision
gcloud run services describe nyc-sidewalk-toolkit
```

---

## Updating the Service

**Automatic (via git push):**
```bash
git commit -am "Update dashboard"
git push origin main
# GitHub Actions automatically deploys
```

**Manual:**
```bash
gcloud run deploy nyc-sidewalk-toolkit \
  --image gcr.io/$PROJECT_ID/nyc-sidewalk-toolkit:latest \
  --region northamerica-northeast2
```

---

## Disaster Recovery

**Rollback to previous revision:**
```bash
# List revisions
gcloud run revisions list --service nyc-sidewalk-toolkit

# Deploy specific revision
gcloud run deploy nyc-sidewalk-toolkit \
  --image gcr.io/$PROJECT_ID/nyc-sidewalk-toolkit:REVISION_ID \
  --region northamerica-northeast2
```

---

## Local Development

```bash
# Build and run locally
docker build -t nyc-toolkit -f Dockerfile.cloudbuild .
docker run -p 8080:8080 \
  -e MOTHERDUCK_TOKEN=$MOTHERDUCK_TOKEN \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  nyc-toolkit

# Visit:
# Dash: http://localhost:8080/dash/
# API: http://localhost:8080/api/
# Docs: http://localhost:8080/api/docs/
```

---

## Next Steps

1. ✅ Setup GCP project and enable APIs
2. ✅ Configure GitHub secrets
3. ✅ Deploy first version (manually or via CI/CD)
4. ✅ Visit Dash dashboard at Cloud Run URL
5. ✅ Share URL with team
6. ✅ Monitor logs and metrics
7. ✅ Enable auto-scaling as needed

---

**Your toolkit is now live on Google Cloud Run!**

Access it at: `https://your-cloud-run-url/dash/`
