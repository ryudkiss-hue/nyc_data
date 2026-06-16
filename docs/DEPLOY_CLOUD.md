# Cloud Deployment

📚 **See [docs/DEPLOYMENT.md](./DEPLOYMENT.md)** for the comprehensive deployment guide.

This document provides cloud deployment instructions for:
- **Local Development** (pip install + Streamlit)
- **Docker Compose** (local or VM)
- **AWS ECR** (push to registry)
- **Google Cloud Run** (recommended for Streamlit)
- **Azure Container Registry** (ACI/App Service)

---

## Quick Links

| Platform | Command | Time |
|----------|---------|------|
| **Local** | `streamlit run app/app.py` | < 2 min |
| **Docker** | `docker compose up mission-control` | < 5 min |
| **Cloud Run** | `gcloud run deploy ...` | < 10 min |
| **ECR** | `aws ecr push ...` | Custom |

---

## What Changed in v0.4.1

- ✅ Removed Render.com (no longer supported)
- ✅ Removed Heroku (free tier deprecated)
- ✅ Added DuckDB-native architecture (no external database)
- ✅ Added comprehensive cloud deployment guide
- ✅ Consolidated Docker images (multi-stage Dockerfile)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions for your platform.

Optional profiles:

```bash
docker compose --profile batch run analyst-runner
docker compose --profile observability up -d prometheus
```

## Native installers

| OS | Command |
|----|---------|
| Windows | `python scripts/build_exe.py` |
| macOS / Linux | `chmod +x scripts/build_unix.sh && ./scripts/build_unix.sh` |

## Security

- Never commit `.env` with real tokens.
- Use `MISSION_DEMO=1` for public demos only.
- Rotate `SOCRATA_APP_TOKEN` per agency policy.
