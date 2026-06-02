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
pip install -e ".[mission,postgres,xlsx]"
python main.py
```

### Q3. Do I need Docker?

No for basic CLI and DuckDB sync. Docker is recommended when you need **Postgres/PostGIS**, **Airflow**, the **REST API**, or team-shared warehouse tables.

### Q4. What does `python launcher.py setup all` do?

It checks `.env.socrata`, lists SQL migration files under `sql/`, and verifies optional Postgres client libraries. It does not load production data by itself.

### Q5. Where is the interactive install wizard?

```bash
python -m socrata_toolkit.install_wizard
# or: socrata setup
# or: python launcher.py setup wizard
```

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

**Mission Control** (`python main.py`) is the primary 8-tab Streamlit app for all agency analytics, data quality, spatial analysis, governance, and AI Copilot workflows. The legacy Dash app is archived at `legacy_archive/dash_app/app.py`.

### Q36. How do I open Mission Control?

```bash
python main.py
# or: PYTHONPATH=src:. python -m streamlit run app/mission_control.py
```

Then open http://localhost:8501. For demo mode (no Socrata token needed): `MISSION_DEMO=1 python main.py`.

Legacy Dash (archived): `python legacy_archive/dash_app/app.py` → http://127.0.0.1:8050

### Q37. What port does Mission Control use?

**8501** (Streamlit default). Check the terminal output when the server starts. To use a different port: `python main.py --server.port 8502`.

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

---

## AI Copilot

### Q41. How do I enable the AI Copilot tab?

Set at least one backend API key before launching Mission Control:

```bash
# Gemini (recommended — free tier available)
export GEMINI_API_KEY=your_key

# OpenAI
export OPENAI_API_KEY=your_key

# Ollama (local, no API key needed)
# Install from https://ollama.com, then: ollama pull llama3
# OLLAMA_HOST defaults to http://localhost:11434
```

### Q42. Where do I get a Gemini API key?

Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create a key. Paste it as `GEMINI_API_KEY` in `.env` or set it in the Render dashboard.

### Q43. Can I use the AI Copilot offline?

Yes — use Ollama. Install from https://ollama.com, pull a model (`ollama pull llama3`), and start the server. Mission Control auto-detects it at `OLLAMA_HOST` (default `http://localhost:11434`). No internet required once the model is downloaded.

### Q44. What happens if no AI backend is configured?

The AI Copilot tab still loads but shows a "no backend configured" notice. All other 7 tabs work fully without any AI key.

---

## Render Deployment

### Q45. How do I deploy to Render in one click?

The repo contains `render.yaml` (a Render blueprint). Steps:
1. Fork/push the repo to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → connect your repo.
3. Render reads `render.yaml` and provisions the service automatically.
4. Set `SOCRATA_APP_TOKEN` in Render dashboard → Environment tab for live data.
5. The service uses `MISSION_DEMO=1` by default so it works without a token.

### Q46. Does the Render free tier support the Bayesian engine?

Yes. The Apex Engine uses ADVI (~50 MB RAM) rather than NUTS (~400 MB), so it fits within Render's free tier memory limit. If you switch to NUTS sampling you will need a paid tier.

### Q47. How do I set environment variables on Render?

In the Render dashboard: open your service → **Environment** tab → add key/value pairs. You do not need to redeploy after setting env vars; Render applies them on the next restart.

### Q48. Can I use a custom domain on Render?

Yes. In the Render dashboard go to your service → **Settings** → **Custom Domains** and follow the DNS instructions. TLS is provisioned automatically.

---

## Bayesian / ML

### Q49. What is ADVI and why is it used instead of NUTS?

ADVI (Automatic Differentiation Variational Inference) is a fast approximate inference method in PyMC. It uses ~50 MB RAM and completes in seconds. NUTS (No-U-Turn Sampler) is a full MCMC method that gives exact posterior samples but uses ~400 MB RAM and can take minutes. Mission Control defaults to ADVI so it works on Render's free tier.

### Q50. The Bayesian sampling step failed. What do I do?

1. Check that `pymc` and `arviz` are installed: `pip install -e ".[mission]"`.
2. Verify you have at least 512 MB free RAM.
3. Check the Streamlit logs for the specific PyMC error.
4. If the error is `ModuleNotFoundError: No module named 'pymc'`, the heavy ML deps were not installed. Run `pip install -e ".[mission]"` with the `mission` extra.
5. The Apex Engine degrades gracefully if PyMC is unavailable — the tab will display a warning and skip the Bayesian step.

### Q51. What happens if Prophet is not installed?

The 12-month forecast chart in the Apex Engine tab is skipped with a warning. All other tabs are unaffected. Install Prophet with `pip install -e ".[mission]"`.

### Q52. What is the Governance tab in the desktop/SPA app?

It assesses any dataset in your cart across three lenses, over a 500-row sample:
- **DAMA-DMBOK quality** — completeness, validity, uniqueness, consistency,
  timeliness, accuracy, with a weighted overall score.
- **FAIRness** — Findable / Accessible / Interoperable / Reusable sub-scores
  with a list of detected gaps.
- **PII inspector** — flags columns containing personal data (multi-signal:
  column name + value patterns + Luhn check) with severity chips.

Click **Assess**, then **Export report** for a JSON record. Scores are computed
client-side; when running the Electron desktop app with the Python sidecar
(`MMC_SIDECAR=1`), heavier server-side scoring is used instead.

### Q53. How do I run the optional analytics sidecar?

From the `desktop/` folder: `MMC_SIDECAR=1 MMC_PYTHON=python npm start`. This
spawns `app.sidecar_api:app` (FastAPI on 127.0.0.1:8000) exposing Bayesian
yield-rate (PyMC ADVI), Prophet forecasting, PII scan, DMBOK score, FAIRness
score, and anomaly detection. It is **off by default** — the app runs fully
without it, and every endpoint degrades gracefully if optional deps are absent.

### Q54. Does the desktop app work offline?

Yes. The Electron build vendors all front-end libraries (Tailwind, FontAwesome,
Leaflet, Mermaid, etc.) locally — `copy-spa.js` rewrites CDN URLs to bundled
`vendor/` paths at build time. Live Socrata data still requires a connection.

### Q55. What accessibility features are available?

WCAG 2.2 AAA-oriented: full keyboard tab navigation (arrow keys), command
palette (Ctrl/Cmd+P), modal focus trapping, skip-to-content, high-contrast and
reduced-motion support, screen-reader announcements, and high-contrast focus
rings. Charts include data-table fallbacks for non-visual access.

### Q56. How do I check performance / clear the cache?

In the app's DevTools console: `mmcPerfReport()` shows timing (TTFB, LCP, long
tasks); `mmcCacheStats()` shows cache size; `mmcCacheClear()` empties it. See
`docs/PERFORMANCE_BUDGET.md`.

---

## Still stuck?

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — structured error guide  
2. [USER_MANUAL.md](USER_MANUAL.md) — full workflows  
3. [sop_faq.md](sop_faq.md) — DOT operational SOPs (morning brief, permit lookahead)

---

## Visualization & Advanced Features

**How do I switch to GPU-accelerated deck.gl maps?**
Open the Map modal (map icon in top toolbar), then click the **⚡ GPU (deck.gl)** button in the top-right corner of the map panel. deck.gl uses WebGL for 60fps rendering with millions of points. Click **🗺 Leaflet** to switch back.

**What is Expert mode?**
Click the **Simple Mode / Expert Mode** button in the bottom-right corner of the screen. Simple mode hides advanced tabs (ERD, SOQL Builder, Trends, Bayesian ML, Code Generators) to reduce complexity for new users. Expert mode reveals them all. Your preference is saved in localStorage.

**How do I run queries offline with DuckDB?**
In the SOQL Builder tab, check the **DuckDB-WASM (local)** checkbox before clicking Run. This routes the query through DuckDB running entirely in the browser — no network call to Socrata for the SQL execution step (the data still needs to be fetched once). Requires a modern browser.

**How do I export governance metadata (DCAT 3, PROV-DM, ODRL, STAC)?**
Go to the Governance tab, run an assessment, then scroll to the **Standards Export** panel at the bottom. Click any of the download buttons. The sidecar API must be running (`python app/sidecar_api.py`).

**How do I view the Trends chart?**
Click the **Trends** tab in the main tab bar. Select a dataset from your cart, choose an X column (date/time) and a Y column (numeric), then click **Plot**. The chart uses Observable Plot with a confidence band line.

**How do I get a scatter plot?**
Go to the **Profiles** tab, select a dataset from your cart. A **Scatter Plot** panel appears below the column table. Choose two numeric columns from the X/Y dropdowns and click **Plot**.

**How do I export slides as PowerPoint?**
Add datasets to your cart, run any analyses to render charts, then click the **PPTX** button in the cart sidebar. The sidecar will collect all rendered canvas charts and build a `.pptx` file. Requires `pip install python-pptx` and the sidecar running.

**How do I use semantic (AI-powered) search?**
In the Discovery tab, look for the **✦ Semantic search** input below the regular search bar. Type a natural-language query (e.g. "sidewalk inspection quality scores by borough"). Results are ranked by meaning similarity using sentence-transformers via the sidecar. Requires the sidecar running with `sentence-transformers` installed.

**How do I see PII masking previews?**
Run a governance assessment on a dataset in the Governance tab. In the PII Inspector card, each flagged column has a **Preview masked** button — click it to see 5 sample values masked (emails, phones, SSNs automatically redacted).
