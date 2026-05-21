# Manhattan Mission Control (Streamlit)

SIM Project Analyst workspace: 15 Socrata datasets, four workflow views, and Productivity ROI telemetry.

## Layout

| Path | Role |
|------|------|
| `app/` | Streamlit frontend (`app.py`, `data_loader.py`, `analytics.py`) |
| `src/socrata_toolkit/` | Python backend package (CLI, analyst, pipelines) |
| `legacy_archive/dash_app/` | Archived Dash Analyst Pack UI |

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
