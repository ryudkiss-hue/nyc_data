# Deployment Guide

NYC DOT SIM Toolkit supports two deployment modes: **Local Development** and **Cloud Container**.

## Local Development

### Prerequisites
- Python 3.11+
- `pip` and `poetry` (optional, for dependency management)

### Quick Start
```bash
# Clone and install
git clone <repo>
cd nyc_data
pip install -e ".[mission,xlsx,postgres]"

# Run Streamlit app
streamlit run app/app.py
```

The app will be available at `http://localhost:8501`.

### Environment Configuration
Create a `.env` file in the project root:
```bash
SOCRATA_APP_TOKEN=<your-socrata-token>
ANTHROPIC_API_KEY=<your-api-key>
SOCRATA_DOMAIN=data.cityofnewyork.us
SOCRATA_CACHE_DIR=data/cache
DUCKDB_PATH=data/local_db/nyc_mission_control.duckdb
MISSION_DEMO=0
```

### Local Docker Development
Run the Streamlit app in Docker (useful for testing cloud behavior locally):
```bash
# Build the image
docker build -t nyc-dot-sim-toolkit:local --target mission .

# Run Mission Control
docker run -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/data/cache:/app/data/cache \
  -v $(pwd)/data/local_db:/app/data/local_db \
  nyc-dot-sim-toolkit:local
```

Or use Docker Compose:
```bash
# Mission Control only
docker compose up mission-control

# Analyst CLI runner (batch profile)
docker compose --profile batch up analyst-runner
```

---

## Cloud Deployment

### Architecture
- **Container**: Multi-stage Dockerfile (one canonical image, multiple targets: mission, analyst, turbo)
- **Storage**: DuckDB local database (no external database required; Parquet cache on S3 optional)
- **Configuration**: Environment variables for API keys, cache location, database path

### Build & Push to Cloud Registry

#### AWS ECR
```bash
# Authenticate
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push Mission Control
docker build -t <account-id>.dkr.ecr.us-east-1.amazonaws.com/nyc-dot-sim-toolkit:latest --target mission .
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/nyc-dot-sim-toolkit:latest

# Push Analyst target
docker build -t <account-id>.dkr.ecr.us-east-1.amazonaws.com/nyc-dot-sim-analyst:latest --target analyst .
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/nyc-dot-sim-analyst:latest
```

#### Google Cloud Run (Recommended for Streamlit)
```bash
# Configure gcloud
gcloud auth configure-docker

# Build and push
docker build -t gcr.io/<project-id>/nyc-dot-sim-toolkit:latest --target mission .
docker push gcr.io/<project-id>/nyc-dot-sim-toolkit:latest

# Deploy to Cloud Run
gcloud run deploy nyc-dot-sim-toolkit \
  --image gcr.io/<project-id>/nyc-dot-sim-toolkit:latest \
  --platform managed \
  --region us-east4 \
  --port 8501 \
  --memory 4Gi \
  --timeout 3600 \
  --set-env-vars "SOCRATA_APP_TOKEN=<token>,MISSION_DEMO=0,DUCKDB_PATH=/tmp/nyc_mission_control.duckdb"
```

#### Azure Container Registry
```bash
# Login
az acr login --name <registry-name>

# Build and push
docker build -t <registry-name>.azurecr.io/nyc-dot-sim-toolkit:latest --target mission .
docker push <registry-name>.azurecr.io/nyc-dot-sim-toolkit:latest

# Deploy to Azure Container Instances or App Service
az container create \
  --resource-group <group> \
  --name nyc-dot-sim-toolkit \
  --image <registry-name>.azurecr.io/nyc-dot-sim-toolkit:latest \
  --port 8501 \
  --environment-variables MISSION_DEMO=0 DUCKDB_PATH=/app/data/local_db/nyc_mission_control.duckdb
```

### Environment Variables
Cloud deployments should configure:
- `SOCRATA_APP_TOKEN` — API token for Socrata access
- `ANTHROPIC_API_KEY` — Claude API key (for NL query features)
- `SOCRATA_CACHE_DIR` — Path to Parquet cache (e.g., `/tmp/socrata_cache` in Cloud Run)
- `DUCKDB_PATH` — Path to DuckDB database file (e.g., `/tmp/nyc_mission_control.duckdb`)
- `MISSION_DEMO` — Set to `1` for demo mode (no API calls)

### Storage Considerations
- **Ephemeral Deployments** (Cloud Run, Fargate): Store cache/database in cloud storage
  ```bash
  # Example: Mount S3 bucket via s3fs in Cloud Run (requires sidecar)
  # Or: Use gs:// paths for Google Cloud Storage
  SOCRATA_CACHE_DIR=gs://project-socrata-cache
  ```
- **Persistent Deployments** (Compute Engine, ECS on EC2): Use local or attached volumes

### Health Checks
The container reports health via Streamlit's built-in endpoint:
```bash
curl http://localhost:8501/_stcore/health
```

---

## CI/CD Pipeline

### GitHub Actions
The repository includes `.github/workflows/nyc-toolkit-ci.yml` which:
1. Runs Python tests (pytest)
2. Lints with ruff
3. Smoke tests key imports
4. Builds Docker image (mission target) and verifies it starts

To enable cloud registry push:
```yaml
# In CI workflow, after docker-build step:
- name: Push to ECR (optional)
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  uses: docker/build-push-action@v6
  with:
    context: .
    file: ./Dockerfile
    target: mission
    push: true
    tags: <account-id>.dkr.ecr.us-east-1.amazonaws.com/nyc-dot-sim-toolkit:${{ github.sha }}
```

---

## Troubleshooting

### Streamlit Connection Issues
If Streamlit doesn't respond on `http://localhost:8501`:
- Check `SOCRATA_APP_TOKEN` is set (required unless `MISSION_DEMO=1`)
- Verify DuckDB path exists: `ls -la data/local_db/`
- Check logs: `docker logs <container-id>`

### DuckDB Errors
```bash
# Verify DuckDB database
duckdb data/local_db/nyc_mission_control.duckdb "SELECT COUNT(*) FROM information_schema.tables;"
```

### Missing Cache
If Parquet cache is missing, restart the app to trigger re-fetch (if `SOCRATA_APP_TOKEN` is set).

---

## References
- **Dockerfile Multi-Stage Builds**: https://docs.docker.com/build/building/multi-stage/
- **Docker Compose**: https://docs.docker.com/compose/
- **Cloud Run Deployment**: https://cloud.google.com/run/docs
- **ECR Push/Pull**: https://docs.aws.amazon.com/AmazonECR/latest/userguide/
