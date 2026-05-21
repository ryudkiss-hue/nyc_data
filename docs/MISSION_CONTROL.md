# Manhattan Mission Control (Streamlit)

SIM Project Analyst workspace: 15 Socrata datasets, four workflow views, and Productivity ROI telemetry.

## Layout

| Path | Role |
|------|------|
| `app/` | Streamlit app (`app.py`, `views/`, `ui/`, `services/`) |
| `app/views/` | Home, workflows, publish, settings pages |
| `config/datasets.yaml` | Socrata registry (single source of truth) |
| `src/socrata_toolkit/` | CLI, analyst pack, publish, readiness |
| `legacy_archive/dash_app/` | Archived Dash UI (optional) |

## Navigation (in-app)

| Page | Purpose |
|------|---------|
| **Home** | Onboarding, quick status |
| **Analyst Workflows** | QA, Spatial, Contract, Productivity |
| **Publish & Pack** | Run pack + publish (dry-run default) |
| **Settings & Quality** | Readiness, completeness, health, ingest log |

## Run

```powershell
pip install -e ".[mission]"
$env:SOCRATA_APP_TOKEN = "your-token"   # omit for demo/offline mode
python main.py
# or: mission
# or: .\run_app.ps1
```

Dataset registry: `config/datasets.yaml` (loaded by `app/data_loader.py`).  
Local parquet cache: `data/local_db/socrata_cache/` (24h TTL).  
Ingestion telemetry: `outputs/logs/ingest.jsonl` (local only, gitignored).

## CLI (unchanged entry point)

```powershell
pip install -e ".[xlsx,postgres]"
socrata analyst run --profile config/analyst_profile.yaml
socrata readiness
```

## Databases

Local DuckDB files live under `data/local_db/` (see `config/analyst_profile.example.yaml`).
