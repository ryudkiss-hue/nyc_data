# Troubleshooting — NYC DOT Sidewalk Toolkit

Structured guide for diagnosing failures. Cross-reference [FAQ.md](FAQ.md) for quick Q&A.

---

## Before you start

Collect:

1. **Command** you ran (full line)
2. **Python version** — `python --version`
3. **Install mode** — pip local, Docker, or packaged EXE
4. **Log files** (see [Log locations](#log-locations))
5. Whether **`SOCRATA_APP_TOKEN`** and **`PG_DSN`** are set (redact secrets when sharing)

Run baseline checks:

```bash
python launcher.py doctor
python -m socrata_toolkit.core.cli doctor --check-db
```

---

## Log locations

| Log | Path | When |
|-----|------|------|
| Toolkit CLI | `nyc_toolkit.log` (cwd) | `socrata` / `launcher.py cli` |
| Rotating backups | `nyc_toolkit.log.1`, `.2`, `.3` | After 5 MB rotation |
| Airflow | `airflow_app/logs/` | Docker scheduler/webserver |
| Docker service | `python launcher.py docker logs --service <name>` | Compose stack |
| API / Uvicorn | Docker logs for `api` service | REST errors |
| Dash | Terminal stdout | Callback tracebacks |

Enable debug on extended CLI:

```bash
python -m socrata_toolkit.core.cli -vv pipeline data.cityofnewyork.us DATASET --json-out out.json
```

---

## Error codes and messages

### Socrata / HTTP

| Symptom | Code / message | Cause | Fix |
|---------|----------------|-------|-----|
| Slow fetch, timeouts | HTTP 429 | Rate limit | Set `SOCRATA_APP_TOKEN`; reduce `max_rows`; use `sync` incremental |
| Forbidden | HTTP 403 | Invalid or revoked token | Regenerate token; restart shell so env reloads |
| Not found | HTTP 404 | Wrong domain or 4x4 | `socrata search -q "..."` to verify dataset ID |
| Empty DataFrame | (no error) | Over-restrictive `$where` | Test fetch without filter in browser or `fetch` with no `--where` |

### CLI

| Symptom | Message | Fix |
|---------|---------|-----|
| Unknown command `pipeline` | `No such command` | Use `python -m socrata_toolkit.core.cli pipeline ...` |
| ClickException on pipeline | `Required columns not found` | Pass correct `--required-col` or fix metadata |
| Sync shows 0 rows | Success with 0 count | Normal if no rows newer than `max(updated_col)`; check column name |
| ImportError openpyxl | Missing module | `pip install -e ".[xlsx]"` |
| ImportError psycopg | Missing module | `pip install psycopg[binary]` or `pip install -e ".[postgres]"` if defined |

### PostgreSQL

| Symptom | Message | Fix |
|---------|---------|-----|
| Connection refused | `could not connect` | Start Docker Postgres: `launcher.py docker up` |
| Auth failed | `password authentication failed` | Match `.env.socrata` with `PG_DSN` |
| Relation does not exist | `relation "..." does not exist` | Run migrations: `core.cli migrate --dsn "$PG_DSN"` |
| PostGIS errors | `function st_* does not exist` | Use `postgis/postgis` image; enable extension in DB |

### DuckDB

| Symptom | Message | Fix |
|---------|---------|-----|
| Database locked | `Conflicting lock` | Close Dash/other apps using same file |
| Table missing in status | Empty database | Run `socrata sync` first |
| VACUUM failed | Permission or corruption | Copy DB aside; recreate with fresh sync |

### Analyst Autopilot

| Symptom | Message | Fix |
|---------|---------|-----|
| Profile not found | `FileNotFoundError` | Copy `config/analyst_profile.example.yaml` |
| Source ERROR in dry run | Exception in warnings | Fix path, DSN, or token per source type |
| Empty construction list | No inspections source | Add `inspections` source with rows |
| Excel engine error | `openpyxl` | Install xlsx extra |
| geopandas ImportError | Geo source | `pip install geopandas` or use GeoJSON fallback |

### Docker

| Symptom | Fix |
|---------|-----|
| `docker-compose` not found | Install Docker Desktop; try `docker compose` (v2) |
| Env validation failed on `docker up` | Fix `.env` per `scripts/validate_env.py` output |
| Airflow unhealthy | Wait for Postgres; check `airflow_app/logs` |
| Port 5432 in use | Stop local Postgres or change host port in compose override |

### Web UI

| Symptom | Fix |
|---------|-----|
| Streamlit error on `launcher.py web` | Use `python app.py` (NiceGUI) or `python dash_app/app.py` (Dash) |
| Dash blank tables | Load/sync data into DuckDB; check `DUCKDB_PATH` |
| ModuleNotFoundError `dash` | `pip install dash dash-bootstrap-components duckdb` |

---

## Workflow-specific checks

### Nightly sync (`socrata sync`)

1. Confirm `updated_col` exists on dataset (often `created_date` or `updated_at`).
2. Delete or rename DuckDB file for a full re-load if schema changed drastically.
3. Test token: `socrata fetch -i DATASET -l 10 -o test.csv`.

### Conflict detection

1. Validate GeoJSON/geometry columns (`geometry`, `the_geom`, etc.).
2. Match `--proposed-geom` and `--ref-geom` to actual column names.
3. For Postgres: confirm both tables have GIST indexes on geom columns.

### Analyst Pack

```bash
python -c "
from socrata_toolkit.analyst import run_analyst_pack
print(run_analyst_pack('config/analyst_profile.yaml', dry_run=True).warnings)
"
```

Fix each `ERROR` line before a full run.

---

## Platform notes (Windows)

- Use **`py -3.11`** if multiple Python versions are installed.
- **`run_nightly_sync.bat`** expects `SHARED_ENV_PATH` to a network `.env` and optionally `dist\nyc_toolkit.exe`.
- Path length: keep repo under `C:\Users\...\` to avoid MAX_PATH issues with node_modules.

---

## Getting help

1. Search [FAQ.md](FAQ.md)  
2. Review [USER_MANUAL.md](USER_MANUAL.md) for your job duty  
3. Open a GitHub issue with logs and reproduction steps (no secrets)

---

## Related

- [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)  
- [DOCKER_SETUP.md](DOCKER_SETUP.md)  
- [observability.md](observability.md) — metrics and health endpoints
