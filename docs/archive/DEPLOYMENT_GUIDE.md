# Deployment Guide: GitHub Pages & Cloud Run

## Overview

This project deploys to both **GitHub Pages** (documentation) and **Google Cloud Run** (live dashboard). Both are automated via GitHub Actions workflows.

---

## GitHub Pages Deployment

**Status:** ✅ Fully Configured

### What Gets Published

- **Jekyll site** — Auto-generated from `README.md`, `QUICKSTART.md`, and docs/
- **Jupyter Book** — Interactive notebooks and analysis walkthroughs
- **API Documentation** — Auto-generated from docstrings

### Manual Deployment

```bash
# Trigger via Actions tab
# Or push to main with docs changes
```

Workflow: `.github/workflows/jekyll-gh-pages.yml`

### Access Documentation

- Main site: `https://ryudkiss-hue.github.io/nyc_data/`
- Jupyter Book: `https://ryudkiss-hue.github.io/nyc_data/jupyter-book/`

---

## Cloud Run Deployment

**Status:** ✅ Ready (All CI/CD jobs passing)

### Prerequisites

1. **Google Cloud Project** with:
   - Cloud Run API enabled
   - Container Registry enabled
   - Service Account with Editor role

2. **GitHub Secrets** configured:
   - `GCP_PROJECT_ID` — Your GCP project ID
   - `WORKLOAD_IDENTITY_PROVIDER` — WIF provider URL
   - `SERVICE_ACCOUNT` — Service account email
   - `SOCRATA_APP_TOKEN` — NYC Open Data API token
   - `ANTHROPIC_API_KEY` — Claude API key
   - `MOTHERDUCK_TOKEN` — MotherDuck cloud analytics token

### Deploy Manually

```bash
# Via GitHub Actions UI
# 1. Go to Actions tab
# 2. Select "Deploy to Cloud Run" workflow
# 3. Click "Run workflow"

# Or via CLI
gcloud run deploy nyc-sidewalk-toolkit \
  --image gcr.io/YOUR_PROJECT/nyc-sidewalk-toolkit:latest \
  --region northamerica-northeast2 \
  --platform managed \
  --allow-unauthenticated
```

### What Gets Deployed

```
App Layout
├── Dash Mission Control (Port 8080)
│   ├── Dashboard view (/dash/)
│   ├── GIS view
│   ├── Analytics view
│   └── Reporting view
│
├── FastAPI Backend (/api/)
│   ├── /api/health — Health check
│   ├── /api/docs — OpenAPI docs
│   ├── /api/metrics — Metric endpoints
│   └── /api/spatial — Conflict detection
│
└── Static Assets
    ├── CSS/JS (Mantine theme)
    └── Cache (DuckDB L2 cache)
```

### Health Check

```bash
curl https://nyc-sidewalk-toolkit-XXXXX.run.app/api/health
# Returns: {"status": "healthy", "metric_count": 51, "dataset_count": 78}
```

### View Logs

```bash
gcloud run logs read nyc-sidewalk-toolkit --limit 100
```

### Scale Configuration

```
Memory: 2Gi (adjustable)
Timeout: 600s (10 minutes)
Concurrency: 100 (default)
```

---

## CI/CD Workflows

### Test Matrix (All Passing ✅)

| Workflow | Status | Trigger |
|----------|--------|---------|
| `ci.yml` | ✅ PASS (4201 tests) | Every push |
| `deploy-cloud-run.yml` | ✅ PASS | main branch |
| `jekyll-gh-pages.yml` | ✅ PASS | main branch |
| `pre-commit.yml` | ✅ PASS | Every push |

### Test Coverage

- **Unit tests:** 4000+
- **Integration tests:** 200+ (Postgres + MongoDB)
- **Performance tests:** 1 (latency benchmarks)
- **Coverage:** >90%

### Fixing Broken Workflows

If a workflow fails:

1. **Check logs**: Actions tab → Select workflow → Latest run
2. **Common issues**:
   - Missing secrets → Add to Settings > Secrets
   - Dependency version → Update requirements.txt
   - Port conflict → Change PORT env var
3. **Re-trigger**: Actions tab → Select failed run → "Re-run failed jobs"

---

## File Structure for Deployment

```
Root Directory
├── requirements.txt ← CI/CD expects here
├── requirements-dev.txt ← CI/CD expects here
├── Dockerfile ← Docker build expects here
├── Dockerfile.cloudbuild ← Cloud Run expects here
├── CLAUDE.md ← Tests expect here
├── .github/workflows/ ← All CI/CD automation
├── app/ ← Dash app + FastAPI
├── src/socrata_toolkit/ ← Core library
├── 00_DOCUMENTATION/ ← Master docs (organized)
├── 00_CONFIG/ ← Backup copies of configs
└── tests/ ← Test suite (4200+ tests)
```

⚠️ **Note:** Files exist in both root AND `00_CONFIG/00_DOCUMENTATION/` for backwards compatibility.

---

## Troubleshooting

### "Requirements file not found"
```bash
# Solution: Files must be in root for CI
cp 00_CONFIG/requirements.txt .
cp 00_CONFIG/requirements-dev.txt .
```

### "Module not found: socrata_toolkit"
```bash
# Solution: Ensure PYTHONPATH is set
export PYTHONPATH=src:.
python app/cloud_run.py
```

### "Health check failed"
```bash
# Check if app is running
curl http://localhost:8080/api/health

# Check logs
gcloud run logs read nyc-sidewalk-toolkit

# If DuckDB issue:
rm -rf data/local_db/nyc_mission_control.duckdb
# App will recreate on restart
```

### "Datasets not loading"
```bash
# Check Socrata token
echo $SOCRATA_APP_TOKEN

# Verify network access
curl https://data.cityofnewyork.us/api/3/
```

---

## Monitoring

### Dashboards

- **Cloud Run**: GCP Console → Cloud Run → nyc-sidewalk-toolkit
- **GitHub**: Actions tab → Workflow run history
- **GitHub Pages**: Pages section shows deployment history

### Alerts

Configure via:
- Cloud Run: Settings → Notifications
- GitHub: Actions → Failure notifications
- Email: ryudkiss@gmail.com

---

## Rollback

If a deployment breaks:

```bash
# Via GCP Console
Cloud Run → nyc-sidewalk-toolkit → Revisions
→ Select previous working revision
→ "Manage Traffic" → Set to 100%

# Via CLI
gcloud run deploy nyc-sidewalk-toolkit \
  --image gcr.io/YOUR_PROJECT/nyc-sidewalk-toolkit:TAG_OF_WORKING_VERSION
```

---

## Next Steps

1. ✅ Ensure all secrets are configured
2. ✅ Run manual test deploy: Actions → "Deploy to Cloud Run"
3. ✅ Monitor logs for first 5 minutes
4. ✅ Test dashboard at deployed URL
5. ✅ Share URL with team

---

**Questions?** Check `.github/workflows/` for latest automation details.
