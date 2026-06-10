# User-friendly enhancements

Five integrations for analysts and deployers (already in this repo).

## 1. Cross-platform native installers

| OS | Command |
|----|---------|
| Windows | `python scripts/build_exe.py` |
| macOS / Linux | `chmod +x scripts/build_unix.sh && ./scripts/build_unix.sh` |

Produces `dist/nyc-dot-toolkit` (CLI) and `dist/NYCDataToolkit/` (Mission Control bundle).

## 2. Docker Compose

Root `docker-compose.yml`:

```bash
docker compose up -d mission-control    # http://localhost:8501
docker compose --profile batch run analyst-runner
docker compose --profile observability up -d prometheus
```

Copy `.env.example` → `.env` and set `SOCRATA_APP_TOKEN` for live data.

## 3. Localization (EN / ES)

- Module: `app/utils/i18n.py`
- Selector: sidebar **Language / Idioma**
- Covers navigation, home, publish, and settings strings

## 4. Empty states & guided tour

- `app/ui/empty_states.py` — demo load button, CSV upload, tour expander
- Home shows empty state when no token; workflows show empty state if ingestion fails

## 5. One-click cloud deploy

| Platform | Files |
|----------|--------|
| Render | `render.yaml` + README deploy button |
| Heroku | `app.json` + `Procfile` |
| Guide | [DEPLOY_CLOUD.md](DEPLOY_CLOUD.md) |

Set `MISSION_DEMO=1` for public demos; use `SOCRATA_APP_TOKEN` for production.
