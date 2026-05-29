# AGENTS.md

## Development instructions for AI coding agents (Cursor, Claude Code, etc.)

### Overview

**NYC DOT Sidewalk Toolkit** (`socrata_toolkit` v0.3.0) — Python toolkit for sidewalk inspection, open data analytics, and agency operations. The primary interface is **Manhattan Mission Control**, a unified 8-tab Streamlit dashboard (`app/mission_control.py`) served on port 8501.

### Running the Application

```bash
# Recommended — thin launcher shim, auto-finds entry point
MISSION_DEMO=1 python main.py

# Direct
PYTHONPATH=src:. python -m streamlit run app/mission_control.py --server.port 8501 --server.headless true
```

`MISSION_DEMO=1` loads synthetic data without a Socrata token. Set `SOCRATA_APP_TOKEN` in `.env` for live data.

### Key Development Commands

| Task | Command |
|------|---------|
| Install all deps | `pip install -e ".[mission,postgres,xlsx]" -r requirements-dev.txt` |
| Lint | `python -m ruff check src/socrata_toolkit/ tests/ app/` |
| Tests | `python -m pytest tests/ -q -m "not legacy"` |
| Run app (demo) | `MISSION_DEMO=1 python main.py` |
| Health check | `python -m socrata_toolkit.core.cli doctor` |

### Repository Layout

```
app/mission_control.py   ← entry point (8-tab Streamlit app)
app/views/apex.py        ← Bayesian hiring analytics tab
app/views/quality_dashboard.py
app/views/governance.py
app/views/spatial_analytics.py
app/data_loader.py       ← Socrata ingestion + DuckDB caching
src/socrata_toolkit/     ← core library (SocrataClient, DuckDBManager, etc.)
config/datasets.yaml     ← 16+ NYC DOT dataset definitions
```

### Non-obvious Caveats

1. **PYTHONPATH:** Must include both `src/` and `.` — `PYTHONPATH=src:.` or use `python main.py` which sets it automatically.

2. **Heavy ML deps** (`pymc`, `arviz`, `prophet`, `folium`) degrade gracefully — the app warns and skips those panels rather than crashing if they're missing.

3. **Demo mode:** `MISSION_DEMO=1` loads sample data. No Socrata token needed.

4. **Test exclusions:** Run with `-m "not legacy"` to skip Dash legacy page tests (require `dash` + `dash-ag-grid` + `dask`). Some tests also need `networkx`, `scikit-learn`, `fastapi`, `httpx`.

5. **Legacy Dash UI** is archived at `legacy_archive/dash_app/` — not the primary interface.

6. **psycopg:** Use `psycopg-binary` in cloud environments to avoid needing the `libpq` system library.
