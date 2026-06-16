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

## 2b. Multi-profile setup (recommended)

If multiple teams or workflows share one install, use **profiles**. The install wizard now supports this directly and writes files under:

- `config/profiles/<name>/analyst_profile.yaml`
- `config/profiles/<name>/publish_profile.yaml` (optional)
- `outputs/.state/profiles/<name>/...` (per-profile state + decisions store)

Run:

```bash
socrata setup
```

Then pick a profile name when prompted. The wizard writes `TOOLKIT_PROFILE=<name>` into `.env` so Dash, CLI, and scheduled tasks stay aligned.

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
| **Mission Control (Dash — PRIMARY)** | `python app/dash_app.py` | http://localhost:8011 |
| **Mission Control launcher** | `python main.py` | Auto-selects primary (Dash) |
| **Streamlit (SECONDARY option)** | `streamlit run app/app.py` | http://localhost:8501 |
| **CLI — daily sync** | `socrata sync -i erm2-nwe9 --table complaints_311` | `data/local_db/` |
| **CLI — full pipeline** | See [Command Reference](COMMAND_REFERENCE.md) | `outputs/` |
| **Analyst weekly pack** | `socrata analyst run --profile config/analyst_profile.yaml` | `outputs/analyst_pack/` |
| **Nightly (Task Scheduler)** | `scripts\nightly_analyst_sync.ps1` | Same pack output |
| **Docker (Mission Control)** | `docker compose up mission-control` | Port 8011 (Dash primary) |

> **Layout:** Python package lives in `src/socrata_toolkit/`; **Dash Mission Control (primary)** in `app/dash_app.py`; Streamlit (secondary) in `app/app.py`.

## 4b. Deploy to Render (alternative to local)

`render.yaml` at the repo root is a Render blueprint. To deploy without a local Python install:

1. Push the repo to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect your repo.
3. Render reads `render.yaml` and auto-provisions the Mission Control service.
4. Set `SOCRATA_APP_TOKEN` in Render dashboard → Environment tab for live data.
5. `MISSION_DEMO=1` is set by default — the app works without a token.

Free tier: the Bayesian engine uses ADVI (~50 MB RAM), which fits within Render's free memory limit.

## 5. First analyst workflow (5 minutes)

1. **Fetch 311 complaints into DuckDB** (common nightly dataset):

```bash
socrata sync -i erm2-nwe9 --table complaints_311 --updated-col created_date
socrata status
```

2. **Open Mission Control** (Dash — recommended) or Streamlit alternative:

```bash
python app/dash_app.py     # Dash Mission Control (primary)
# or: python main.py       # Launcher shim
# or: streamlit run app/app.py  # Streamlit (secondary option)
# Demo/offline (no token): MISSION_DEMO=1 python main.py
# Legacy Dash: python legacy_archive/dash_app/app.py
```

3. **Optional — run Analyst Autopilot** with the example profile:

```bash
cp config/analyst_profile.example.yaml config/analyst_profile.yaml
# Edit paths in the YAML, then:
python -c "from socrata_toolkit.analyst import run_analyst_pack; r=run_analyst_pack('config/analyst_profile.yaml'); print(r.pack_dir)"
```

## 6. Review decisions (conflicts + approvals)

After a pack run, you can record decisions locally and export them into the pack:

```bash
socrata review set --pack-date YYYY-MM-DD --kind conflict --key-type location_id --key L123 --status resolved --notes "Checked permit"
socrata review list --pack-date YYYY-MM-DD --kind conflict
socrata review export --pack outputs/analyst_pack/YYYY-MM-DD
```

Dash also includes a **Review** page to edit these decisions.

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
