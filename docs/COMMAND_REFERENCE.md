# Command Reference — NYC DOT Sidewalk Toolkit

Quick cheat sheet for CLI and launcher commands. For narrative examples and job-duty workflows, see [USER_MANUAL.md](USER_MANUAL.md).

## Entry points

| Invocation | CLI surface |
|------------|-------------|
| `socrata …` | **Toolkit CLI** (`socrata_toolkit.cli`) — search, fetch, analyze, sync, status, map-toolkit |
| `python -m socrata_toolkit.core.cli …` | **Extended CLI** — pipeline, conflict, schema, lineage, alerts, quality, etc. |
| `python launcher.py cli …` | Forwards to **Toolkit CLI** (same as `socrata`) |
| `python launcher.py web` | Dash dashboard at http://127.0.0.1:8050 |
| `python launcher.py docker up\|down\|logs\|status` | Docker Compose stack |
| `python launcher.py doctor` | Host health checks |
| `python launcher.py setup all` | Config / schema / DB setup hints |

## Toolkit CLI (`socrata`)

```bash
# Search NYC Open Data
socrata search -q "sidewalk repair" -d data.cityofnewyork.us -l 10

# Fetch dataset to file
socrata fetch -i erm2-nwe9 -d data.cityofnewyork.us -l 5000 -f csv -o complaints.csv

# Program KPI dashboard from local CSV
socrata analyze --file data/samples/sidewalk_inspections_full.csv

# Incremental DuckDB sync (nightly)
socrata sync -i erm2-nwe9 --table complaints_311 --updated-col created_date \
  --db-path nyc_mission_control.duckdb --optimize

# Optional Parquet backup after sync
socrata sync -i erm2-nwe9 --table complaints_311 --export-parquet backups/parquet

# DuckDB table row counts
socrata status --db-path nyc_mission_control.duckdb

# Capability map (HTML)
socrata map-toolkit --output toolkit_map.html
```

Environment: `SOCRATA_APP_TOKEN` (recommended). Logs: `nyc_toolkit.log` (rotating, 5 MB × 3).

## Extended CLI (`python -m socrata_toolkit.core.cli`)

### Data access

```bash
python -m socrata_toolkit.core.cli search "sidewalk" --limit 10
python -m socrata_toolkit.core.cli meta data.cityofnewyork.us h9gi-nx95
python -m socrata_toolkit.core.cli fetch data.cityofnewyork.us h9gi-nx95 --format xlsx --out out.xlsx --include-meta
python -m socrata_toolkit.core.cli upsert-pg data.cityofnewyork.us h9gi-nx95 --table inspections --conflict-col id
```

### Pipeline and analysis

```bash
python -m socrata_toolkit.core.cli pipeline data.cityofnewyork.us h9gi-nx95 \
  --json-out data.json --xlsx-out data.xlsx \
  --pg-dsn "$PG_DSN" --pg-table inspections --pg-conflict-col id

python -m socrata_toolkit.core.cli pipeline data.cityofnewyork.us h9gi-nx95 \
  --stream --pg-dsn "$PG_DSN" --pg-table inspections --pg-conflict-col id

python -m socrata_toolkit.core.cli analyze data.cityofnewyork.us h9gi-nx95 --key-column id
python -m socrata_toolkit.core.cli text-insights data.cityofnewyork.us h9gi-nx95 --text-column descriptor
python -m socrata_toolkit.core.cli outliers data.cityofnewyork.us h9gi-nx95 --method iqr
python -m socrata_toolkit.core.cli correlations data.cityofnewyork.us h9gi-nx95 --threshold 0.5
python -m socrata_toolkit.core.cli quality-score data.cityofnewyork.us h9gi-nx95 --key-column id --date-column updated_at
```

### Conflicts and spatial

```bash
python -m socrata_toolkit.core.cli conflict \
  --proposed-file proposed.json --ref-file permits.json \
  --buffer-meters 20 --out-xlsx construction_clean.xlsx

python -m socrata_toolkit.core.cli spatial-join \
  --left-json proposed.json --right-json permits.json \
  --left-geom-col geometry --right-geom-col geometry --out joined.json
```

### Operations

```bash
python -m socrata_toolkit.core.cli doctor --check-db
python -m socrata_toolkit.core.cli migrate --dsn "$PG_DSN"
python -m socrata_toolkit.core.cli alerts --pg-dsn "$PG_DSN" --preview
python -m socrata_toolkit.core.cli batch-search data.cityofnewyork.us DATASET --field id --file ids.txt --out hits.json
```

### Schema registry

```bash
python -m socrata_toolkit.core.cli schema list sidewalk-inspections
python -m socrata_toolkit.core.cli schema current sidewalk-inspections --json-out current.json
python -m socrata_toolkit.core.cli schema diff sidewalk-inspections 1 2
python -m socrata_toolkit.core.cli schema validate sidewalk-inspections data.jsonl
```

### Visualization

```bash
python -m socrata_toolkit.core.cli visualize data.cityofnewyork.us h9gi-nx95 \
  --chart histogram --column severity --out hist.png
```

Verbosity: `-v` / `-vv` or `--log-level DEBUG`.

## Launcher

```bash
python launcher.py docker up
python launcher.py docker down --remove-volumes
python launcher.py docker logs --service postgres
python launcher.py doctor
python launcher.py info
python launcher.py cli search -q "311 sidewalk"
```

## Analyst Autopilot (Python)

```bash
python -c "from socrata_toolkit.analyst import run_analyst_pack; print(run_analyst_pack('config/analyst_profile.yaml'))"
python -c "from socrata_toolkit.analyst import run_analyst_pack; print(run_analyst_pack('config/analyst_profile.yaml', dry_run=True))"
```

## Publishing Analyst Packs

```bash
# Publish (dry-run preview)
socrata analyst publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD --dry-run

# Publish (apply)
socrata analyst publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD

# Alias
socrata publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD
```

## Web applications

```bash
python dash_app/app.py          # Dash — NYC DOT Data Assistant
python app.py                   # NiceGUI — Mission Control
cd frontend && npm run dev      # React LLM UI (with API on :8000)
```

## Docker Compose (from repo root)

```bash
docker compose up -d postgres redis api scheduler webserver
docker compose ps
```

Services: Postgres/PostGIS (5432), Redis (6379), API (8000), Airflow UI (8080), Grafana (3000), Prometheus (9090), Jaeger (16686), frontend dev (5173).

## Scheduled jobs

| Script | Purpose |
|--------|---------|
| `run_nightly_sync.bat` | Windows batch calling packaged `sync` for 311 data |
| `scripts/nightly_job.py` | Postgres delta + conflict alerts example |
| Airflow DAGs under `airflow_app/dags/` | Orchestrated ingest (when stack is up) |
