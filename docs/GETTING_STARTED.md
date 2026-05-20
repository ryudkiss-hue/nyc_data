# Getting Started — NYC DOT Sidewalk Toolkit

This guide gets a **Project Analyst (Sidewalk)** from zero to a working install in about 15 minutes. For full workflows, job-duty mappings, and reference material, see the [User Manual](USER_MANUAL.md).

## Who this is for

NYC DOT staff who manage sidewalk inspection data, construction lists, contract reporting, and program KPIs across the five boroughs.

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| Python 3.9–3.12 | See `pyproject.toml` |
| Git | To clone the repository |
| Docker Desktop (optional) | For PostgreSQL, Airflow, API, monitoring stack |
| Socrata app token (recommended) | Register at [NYC Open Data](https://data.cityofnewyork.us/profile/app_tokens) |

## 1. Clone and install

```bash
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data
pip install -e ".[all]"
```

On Windows, you can also use the launcher after install:

```powershell
python launcher.py setup all
```

## 2. Configure environment

Copy the template and set your token and database connection:

```bash
cp .env.example .env
# Edit .env — at minimum set SOCRATA_APP_TOKEN and PG_DSN if using Postgres
```

Many teams use `.env.socrata` for Docker and shared drives (see [User Manual — Configuration](USER_MANUAL.md#configuration)).

## 3. Verify installation

```bash
python launcher.py doctor
socrata search -q "sidewalk" --limit 5
```

Extended CLI (pipeline, conflicts, schema registry):

```bash
python -m socrata_toolkit.core.cli doctor --check-db
```

## 4. Pick your interface

| Goal | Command | URL / output |
|------|---------|----------------|
| **Dash analyst UI** | `python dash_app/app.py` | http://localhost:8050 (default Dash port) |
| **Mission Control (NiceGUI)** | `python app.py` | http://localhost:8501 |
| **CLI — daily sync** | `socrata sync -i erm2-nwe9 --table complaints_311` | `nyc_mission_control.duckdb` |
| **CLI — full pipeline** | See [Command Reference](COMMAND_REFERENCE.md) | `outputs/` |
| **Analyst weekly pack** | Python API — see [User Manual — Analyst Autopilot](USER_MANUAL.md#analyst-autopilot-weekly-pack) | `outputs/analyst_pack/` |
| **Docker stack** | `python launcher.py docker up` | Postgres :5432, Airflow :8080, API :8000 |

> **Note:** `python launcher.py web` starts Streamlit against `app.py`, but `app.py` is a NiceGUI app. Prefer `python app.py` or `python dash_app/app.py` directly until the launcher is aligned.

## 5. First analyst workflow (5 minutes)

1. **Fetch 311 complaints into DuckDB** (common nightly dataset):

```bash
socrata sync -i erm2-nwe9 --table complaints_311 --updated-col created_date
socrata status
```

2. **Open the Dash dashboard** and explore KPI and map pages:

```bash
python dash_app/app.py
```

3. **Optional — run Analyst Autopilot** with the example profile:

```bash
cp config/analyst_profile.example.yaml config/analyst_profile.yaml
# Edit paths in the YAML, then:
python -c "from socrata_toolkit.analyst import run_analyst_pack; r=run_analyst_pack('config/analyst_profile.yaml'); print(r.pack_dir)"
```

## Documentation map

| Document | Purpose |
|----------|---------|
| [USER_MANUAL.md](USER_MANUAL.md) | Complete guide for analysts |
| [FAQ.md](FAQ.md) | Quick answers |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Errors, logs, fixes |
| [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) | CLI cheat sheet |
| [QUICKSTART.md](../QUICKSTART.md) | Docker-first 5-minute setup |
| [cli.md](cli.md) | Legacy CLI index |
| [DOCKER_SETUP.md](DOCKER_SETUP.md) | Container stack details |

## Next steps

- Configure Postgres and run `python -m socrata_toolkit.core.cli migrate --dsn "%PG_DSN%"` for warehouse tables.
- Schedule `socrata sync` or Airflow DAGs for nightly ingestion.
- Read [FAQ.md](FAQ.md) if you hit token limits, Excel import issues, or conflict-detection questions.
