# Cloud deployment (one-click)

Deploy **Mission Control** (Streamlit) without managing servers locally.

## Render (recommended)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)

1. Click the button (or connect the repo in Render dashboard).
2. Render reads `render.yaml` and builds with `pip install -e ".[mission,postgres,xlsx]"`.
3. Set `SOCRATA_APP_TOKEN` in the service environment (optional if `MISSION_DEMO=1`).
4. Open the generated URL (port mapped automatically).

## Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ryudkiss-hue/nyc_data)

Uses `app.json`, `Procfile`, and the Python buildpack. After deploy:

```bash
heroku config:set SOCRATA_APP_TOKEN=your-token
heroku config:set MISSION_DEMO=0
```

## Docker Compose (local / VM)

```bash
docker compose up -d mission-control
# UI: http://localhost:8501
```

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
