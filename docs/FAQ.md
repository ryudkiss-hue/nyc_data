# Frequently Asked Questions — NYC DOT Sidewalk Toolkit

Answers for Project Analysts (Sidewalk). For step-by-step workflows, see [USER_MANUAL.md](USER_MANUAL.md). For error codes and logs, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Installation and setup

### Q1. Which Python version do I need?

Python **3.9 through 3.12** (see `pyproject.toml`). Run `python --version` before installing. Python 3.13+ is not supported by current dependencies.

### Q2. What is the fastest way to install on a new laptop?

```bash
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data
pip install -e ".[all]"
python launcher.py doctor
```

### Q3. Do I need Docker?

No for basic CLI and DuckDB sync. Docker is recommended when you need **Postgres/PostGIS**, **Airflow**, the **REST API**, or team-shared warehouse tables.

### Q4. What does `python launcher.py setup all` do?

It checks `.env.socrata`, lists SQL migration files under `sql/`, and verifies optional Postgres client libraries. It does not load production data by itself.

### Q5. Where is the interactive install wizard?

The README references `python -m socrata_toolkit.install_wizard`. If that module is missing in your checkout, use `pip install -e ".[all]"` and `launcher.py setup` instead.

---

## Socrata tokens and API access

### Q6. Do I need a Socrata app token?

Not strictly required, but **strongly recommended**. Without a token you hit lower rate limits and may see throttling on large fetches.

### Q7. How do I register a token?

Create an application token at [NYC Open Data — App Tokens](https://data.cityofnewyork.us/profile/app_tokens). Set it in `.env` or `.env.socrata`:

```bash
SOCRATA_APP_TOKEN=your_token_here
```

### Q8. Why are my searches returning zero rows?

Check the query string, domain (`data.cityofnewyork.us`), and dataset ID (4x4). Use `socrata search -q "sidewalk" -l 20` to discover datasets.

### Q9. Which dataset ID is used for 311 sidewalk complaints?

The Mission Control and nightly sync examples use **`erm2-nwe9`** (NYC 311 Service Requests). Always confirm the dataset still matches your program’s definition of sidewalk-related complaints.

### Q10. Can I use the toolkit on DOT network only?

You need HTTPS access to `data.cityofnewyork.us` from the machine running fetch/sync. Internal Postgres can stay on DOT network; configure `PG_DSN` accordingly.

---

## CLI: two entry points

### Q11. Why does `socrata pipeline` say "No such command"?

`pip install` registers the **Toolkit CLI** (`socrata_toolkit.cli`) with commands like `search`, `fetch`, `sync`. The **extended** commands (`pipeline`, `conflict`, `schema`, …) live in `socrata_toolkit.core.cli`:

```bash
python -m socrata_toolkit.core.cli pipeline data.cityofnewyork.us DATASET_ID --json-out out.json
```

### Q12. What is the difference between `sync` and `pipeline`?

- **`socrata sync`** — incremental load into **local DuckDB** (analyst workstation pattern).
- **`core.cli pipeline`** — fetch plus optional export to JSON, XLSX, GeoJSON, Postgres, or Mongo in one job.

### Q13. Where are CLI logs written?

The Toolkit CLI writes to **`nyc_toolkit.log`** in the current working directory (5 MB rotation, three backups). Extended CLI uses structured logging via `get_logger()`; increase verbosity with `-vv` or `--log-level DEBUG`.

### Q14. How do I run a health check on databases?

```bash
socrata status
python -m socrata_toolkit.core.cli doctor --check-db
python launcher.py doctor
```

---

## Excel and file imports

### Q15. How do I import Excel construction lists?

Use **Analyst Autopilot** with `type: excel` in your YAML profile, or load in Python with pandas and pass to `prioritize_construction_list()`. Install Excel support: `pip install -e ".[xlsx]"`.

### Q16. Can Analyst Autopilot read CSV files directly?

The `excel` source type uses `pandas.read_excel`. For CSV, load into Postgres or DuckDB first, or use a `socrata` / `postgres` source in the profile.

### Q17. My Excel path glob finds no files

Use forward slashes or quoted paths in YAML. Confirm the service account running scheduled jobs can read the share (e.g. `Z:\ConstructionLists\*.xlsx`).

### Q18. Column names from DOT systems do not match the toolkit

Use `column_map` in the analyst profile source block, e.g. `boro: borough`. The workflow also maps common aliases (`boro` → `borough`).

---

## Conflicts and spatial analysis

### Q19. What buffer distance should I use for permit conflicts?

**20 meters** is the default in CLI and Analyst Autopilot (`buffer_m: 20`). Increase for conservative screening; decrease only with GIS team approval.

### Q20. Can I run conflicts without PostGIS?

Yes. Use local JSON/CSV files:

```bash
python -m socrata_toolkit.core.cli conflict \
  --proposed-file proposed.json --ref-file permits.json --buffer-meters 20
```

Or Python: `detect_construction_conflicts()` in `engineering/construction_list.py`.

### Q21. Why does PostGIS conflict detection fail?

Ensure geometries are valid, SRID is consistent (typically 4326 or NY State Plane per your warehouse), and `PG_DSN` points at the database with `permits` and proposed tables. Run `migrate` to apply SQL files.

### Q22. What is the difference between `conflict` and `spatial-join`?

`conflict` applies DOT construction-list logic and can emit GeoJSON/XLSX. `spatial-join` is a lower-level intersect join between two local files.

---

## PostgreSQL and DuckDB

### Q23. What connection string format does `PG_DSN` use?

Standard PostgreSQL URI:

```text
postgresql://user:password@host:5432/sidewalk_db
```

### Q24. Where is local DuckDB stored?

Default **`nyc_mission_control.duckdb`** in the working directory for `socrata sync`. The Dash app may use `nyc_dash.db` or MotherDuck depending on `DUCKDB_PATH` / `MOTHERDUCK_TOKEN`.

### Q25. How do I see table row counts in DuckDB?

```bash
socrata status --db-path nyc_mission_control.duckdb
```

### Q26. Docker Postgres credentials?

Defaults in Compose: user `dot_user`, password `dot_pass`, database `sidewalk_db` (override in `.env.socrata`).

---

## Analyst Autopilot

### Q27. Is Analyst Autopilot available?

Yes, in `socrata_toolkit/analyst/` (Python API). Copy `config/analyst_profile.example.yaml` and run `run_analyst_pack()`. A top-level `socrata analyst-pack` command may be added later.

### Q28. What does a dry run do?

It loads each configured source, reports row counts or errors, and does **not** write pack files.

### Q29. Where do outputs go?

`outputs/analyst_pack/<YYYY-MM-DD>/` by default, plus `manifest.json` listing artifacts.

### Q30. The pack is missing contract reports

Ensure `steps.contract_report: true`, the `contracts` source returns rows, and required columns exist (`contract_id` recommended).

---

## Docker, Airflow, and scheduling

### Q31. How do I start only Postgres?

```bash
python launcher.py docker up --service postgres
```

### Q32. What is the Airflow URL?

http://localhost:8080 (default credentials often `airflow` / `airflow`—confirm your deployment).

### Q33. Is there an analyst-runner container?

No. Schedule Analyst Autopilot with Task Scheduler, cron, or a custom Airflow PythonOperator calling `run_analyst_pack`.

### Q34. How do I set the token for Airflow?

```bash
docker exec airflow-scheduler airflow variables set SOCRATA_APP_TOKEN your_token_here
```

Or sync from `.env.socrata` per [QUICKSTART.md](../QUICKSTART.md).

---

## Web dashboards and UI

### Q35. Which web UI should analysts use daily?

**Dash** (`python dash_app/app.py`) is the primary multi-page Data Assistant. **NiceGUI** Mission Control (`python app.py`) focuses on 311 fetch, triage, and maps.

### Q36. Why does `launcher.py web` fail or look wrong?

The launcher starts **Streamlit** against `app.py`, but `app.py` is implemented with **NiceGUI**. Use `python app.py` or `python dash_app/app.py` directly.

### Q37. What port does Dash use?

Typically **8050** (Flask/Dash default). Check the terminal output when the server starts.

---

## Tests, quality, and support

### Q38. How do I run tests?

```bash
python -m pytest tests/ -v
```

### Q39. Tests fail on optional imports (spacy, shapely)

Install extras: `pip install -e ".[nlp,geo,all]"` or skip tests that require missing optional packages.

### Q40. Where do I report bugs?

GitHub Issues with: OS, Python version, exact command, redacted `PG_DSN`, and tail of `nyc_toolkit.log`. Do not post tokens or passwords.

---

## Still stuck?

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — structured error guide  
2. [USER_MANUAL.md](USER_MANUAL.md) — full workflows  
3. [sop_faq.md](sop_faq.md) — DOT operational SOPs (morning brief, permit lookahead)
