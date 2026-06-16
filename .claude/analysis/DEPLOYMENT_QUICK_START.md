# Cloud Run Deployment — Quick Start

Get your toolkit live in 10 minutes.

---

## 1. GitHub Secrets (2 min)

Add to GitHub Settings → Secrets → Actions:

```
GCP_PROJECT_ID = your-project-id
WORKLOAD_IDENTITY_PROVIDER = projects/123/locations/global/workloadIdentityPools/github/providers/github
SERVICE_ACCOUNT = cloud-run-deployer@your-project-id.iam.gserviceaccount.com
SOCRATA_APP_TOKEN = your-token
ANTHROPIC_API_KEY = your-key
MOTHERDUCK_TOKEN = your-motherduck-token
```

---

## 2. Setup GCP (5 min)

```bash
export PROJECT_ID="your-gcp-project-id"

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project=$PROJECT_ID

# Create service account
gcloud iam service-accounts create cloud-run-deployer --project=$PROJECT_ID

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cloud-run-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

---

## 3. Deploy (2 min)

```bash
# Just push to main
git push origin main

# GitHub Actions automatically:
# 1. Builds Docker image
# 2. Pushes to Container Registry
# 3. Deploys to Cloud Run
# 4. Runs health check

# Watch deployment at: GitHub → Actions
```

---

## 4. Access Your Toolkit

```bash
# Get the URL
gcloud run services describe nyc-sidewalk-toolkit \
  --region northamerica-northeast2 \
  --format 'value(status.url)' \
  --project $PROJECT_ID

# Visit:
# Dash Dashboard: https://your-url/dash/
# API Docs: https://your-url/api/docs/
# API Health: https://your-url/api/health/
```

---

## That's It!

Your toolkit is now live on Google Cloud Run.

**What you get:**
- ✅ Dash Mission Control dashboard
- ✅ FastAPI backend with 26 datasets
- ✅ MotherDuck cloud analytics (primary)
- ✅ DuckDB fallback (if MotherDuck unavailable)
- ✅ Auto-scaling based on traffic
- ✅ Automatic re-deployment on git push
- ✅ Health monitoring and logging

**Monthly cost:** ~$2-5 (very low)

**Scale up when needed:**
```bash
gcloud run deploy nyc-sidewalk-toolkit --memory 4Gi --max-instances 10
```

---

For full details: See `CLOUD_RUN_DEPLOYMENT.md`
