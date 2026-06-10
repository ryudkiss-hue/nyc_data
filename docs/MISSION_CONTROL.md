# Manhattan Mission Control

**NYC DOT SIM — Open Data Explorer + Agency Analytics Platform**

A unified 7-tab Streamlit application for NYC DOT analysts. Ingests NYC Open Data datasets via Socrata, runs Bayesian and Prophet forecasting models, visualizes spatial patterns, and provides an AI Copilot backed by Gemini, OpenAI, or Ollama.

---

## Quick Start (3 commands)

```bash
# 1. Install
pip install -e ".[mission,postgres,xlsx]"

# 2. Launch
python main.py

# 3. Open in browser
# http://localhost:8501
```

Or with the full PYTHONPATH form:

```bash
PYTHONPATH=src:. python -m streamlit run app/mission_control.py
```

---

## Entry Point

**`app/mission_control.py`** — the single entry point for the production app.

| File | Role |
|------|------|
| `app/mission_control.py` | Streamlit entry point, 7-tab layout |
| `app/data_loader.py` | Centralized Socrata / DuckDB loader used by all tabs |
| `config/datasets.yaml` | Socrata dataset registry (16+ NYC DOT datasets) |
| `src/socrata_toolkit/core/client.py` | `SocrataClient` — paginated, auth |
| `src/socrata_toolkit/core/duckdb_store.py` | `DuckDBManager` — local DuckDB cache |
| `outputs/logs/ingest.jsonl` | Ingest audit log |
| `outputs/analyst_pack/` | Weekly analyst exports |

---

## 7-Tab Feature Reference

### 1. Home
Dataset status cards showing load state for each configured dataset. **Load All Datasets** button triggers bulk ingestion. Audit trail of recent ingest events pulled from `outputs/logs/ingest.jsonl`.

### 2. Agency Workflows
Multi-view workflow panel for agency operations:
- QA/QC & Inventory Ledger
- Spatial Conflict Detection
- Contract & Dispatch Clearance
- Productivity & ADA Progress

### 3. Data Quality
Per-dataset health scoring dashboard:
- Null and duplicate profiling
- SLA freshness indicator: green (<7 days), amber (<30 days), red (>30 days)
- Anomaly detection flags
- CSV export of quality report

### 4. Spatial Analytics
- Borough bar charts
- Plotly Scattermapbox point-density map
- Folium bubble map
- Conflict detection between permit and inspection geometries

### 5. Governance
- Plotly lineage DAG (dataset dependency graph)
- Dataset registry table (from `config/datasets.yaml`)
- Ingest audit log viewer
- SLA compliance summary

### 6. AI Copilot
Multi-backend conversational assistant:
- Backends: **Gemini** (`GEMINI_API_KEY`), **OpenAI** (`OPENAI_API_KEY`), **Ollama** (`OLLAMA_HOST`)
- Context-hydrated with live pipeline results from the current session
- Quick-action chips for common analyst queries
- Falls back gracefully if no backend is configured

### 7. Settings & Quality
- Readiness score (0–100)
- Completeness checklist
- System health panel (dependency versions, cache sizes, token status)

---

## Environment Variables

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `SOCRATA_APP_TOKEN` | NYC Open Data API token — raises rate limits | Optional |
| `GEMINI_API_KEY` | AI Copilot → Gemini backend | Optional |
| `OPENAI_API_KEY` | AI Copilot → OpenAI backend | Optional |
| `OLLAMA_HOST` | AI Copilot → Ollama (default: `http://localhost:11434`) | Optional |
| `MISSION_DEMO` | `1` = demo mode, no live API calls needed | Default on Render |

Set variables in `.env` or export them in your shell before launching.

---

## Deployment Options

### Local (Python)

```bash
pip install -e ".[mission,postgres,xlsx]"
PYTHONPATH=src:. python -m streamlit run app/mission_control.py
# Shortcut:
python main.py
```

No Socrata token? Set `MISSION_DEMO=1` or leave it unset — demo mode loads automatically.

### Docker

```bash
docker build -f Dockerfile.mission -t nyc-mission .
docker run -p 8501:8501 \
  -e SOCRATA_APP_TOKEN=your_token \
  nyc-mission
```

Open http://localhost:8501.

### Render.com (one-click)

`render.yaml` at the repo root is a Render blueprint. To deploy:

1. Fork / push the repo to GitHub.
2. Go to [render.com](https://render.com) → **New Blueprint** → connect the repo.
3. Render reads `render.yaml` and auto-deploys.
4. Set `SOCRATA_APP_TOKEN` in the Render dashboard (Environment tab) for live data.
5. `MISSION_DEMO=1` is set by default so the app works without a token.

**Free tier notes:**
- Bayesian engine uses ADVI (~50 MB RAM) instead of NUTS (~400 MB), so it fits on Render's free tier.
- Render spins down free services after inactivity; first load may take ~30 seconds.

### Legacy Dash (archived)

The old Dash app is archived at `legacy_archive/dash_app/app.py`:

```bash
python legacy_archive/dash_app/app.py
# Opens at http://127.0.0.1:8050
```

---

## AI Copilot Setup

The AI Copilot tab supports three backends. Set at least one API key/host to enable it.

### Gemini (Google)

1. Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Set `GEMINI_API_KEY=your_key` in `.env` or the Render dashboard.

### OpenAI

1. Get an API key from [platform.openai.com](https://platform.openai.com/api-keys).
2. Set `OPENAI_API_KEY=your_key` in `.env` or the Render dashboard.

### Ollama (local / offline)

1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull llama3`
3. Set `OLLAMA_HOST=http://localhost:11434` (this is the default; you can omit it).
4. The Copilot will auto-detect a running Ollama instance.

### Offline mode

If no backend is configured, the AI Copilot tab still loads but shows a "no backend" notice. All other tabs work fully without any AI key.

---

## Configuration

### Dataset Registry — `config/datasets.yaml`

Single source of truth for the 16+ NYC DOT Socrata datasets. Each entry includes:
- `id` — Socrata 4x4 dataset identifier
- `name` — human-readable label
- `sla_days` — freshness SLA (used in Data Quality tab)
- `columns` — expected column list for schema validation

Edit this file to add, remove, or reconfigure datasets.

### Streamlit Config — `.streamlit/config.toml`

Controls theme, port, and upload limits. Example:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[server]
port = 8501
headless = true
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Run with `PYTHONPATH=src:.` or use `python main.py` (the shim sets this automatically).

### Bayesian sampling fails / out of memory

The Bayesian forecasting engine uses ADVI by default (low memory). If you see OOM errors, check that PyMC and ArviZ are installed (`pip install -e ".[mission]"`) and that you have at least 512 MB free RAM.

### Socrata rate limit / 429 errors

Set `SOCRATA_APP_TOKEN` in your environment. Without a token, requests are throttled at the anonymous rate limit (~1 req/s).

### Folium map not rendering

Folium renders to an HTML iframe. If the map tab is blank, check that `folium` and `geopandas` are installed and that your browser allows iframe content.

### AI Copilot returns "no backend"

Set at least one of `GEMINI_API_KEY`, `OPENAI_API_KEY`, or ensure Ollama is running at `OLLAMA_HOST`.

### Port 8501 already in use

```bash
PYTHONPATH=src:. python -m streamlit run app/mission_control.py --server.port 8502
```

---

## Further Reading

| Doc | Content |
|-----|---------|
| [README.md](../README.md) | Main project overview |
| [AGENCY_RUNBOOK.md](AGENCY_RUNBOOK.md) | Agency operations |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Full platform setup |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Deployment options |
| [FAQ.md](FAQ.md) | Common questions |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Error codes and logs |

---

## Visualization Features

### Browser Charts (no install required)

| Chart | How to access |
|---|---|
| **Trends (time series)** | Click the **Trends** tab — select dataset, X (date) and Y (numeric) columns, click Plot |
| **Scatter plot** | Open **Profiles** tab → select a dataset → Scatter Plot panel at bottom; choose two numeric columns |
| **Bayesian histogram** | Bayesian tab → Run ADVI Model → posterior distribution with HDI band |
| **Prophet forecast** | Bayesian tab → Forecast section → confidence band chart |
| **SOQL bar chart** | SOQL Builder → run any query → auto-rendered bar chart |
| **Sparklines** | Profile tab column list → numeric columns show inline mini-chart |
| **Mermaid ERD/Flowchart/Mindmap** | ERD tab → choose diagram type → auto-generated from cart |
| **SVG Sparklines** | Dataset result cards show inline mini-charts |

### Map Visualizations

| Feature | How to access |
|---|---|
| **Leaflet interactive map** | Map button (top toolbar) → 4 tile layer options |
| **Marker clustering** | Automatic when datasets have lat/lng columns |
| **deck.gl GPU map** | Map modal → click **⚡ GPU (deck.gl)** toggle |
| **Borough choropleth** | Map modal → Layers panel → **Borough Choropleth** button |
| **Bounding box filter** | Map modal → Draw Filter |
| **GeoJSON export** | Map modal → GeoJSON button |

### Governance Visualizations

| Feature | How to access |
|---|---|
| **DMBOK quality bars** | Governance tab → run assessment → DAMA-DMBOK Quality card |
| **FAIR radar chart** | Governance tab → run assessment → FAIRness card |
| **PII inspector + masking preview** | Governance tab → PII Inspector card → "Preview masked" per column |
| **DCAT 3 / PROV-DM / ODRL / STAC export** | Governance tab → Standards Export panel |
| **OGC Collections browser** | Governance tab → Standards Export → OGC Collections |

### Python Backend Charts (for reports)

| Module | Charts available |
|---|---|
| `socrata_toolkit.viz.core` | Histogram, bar, heatmap, time series, box plot, quality dashboard |
| `socrata_toolkit.viz.plotly` | Borough bar, KPI gauge, Gantt, priority heatmap, trend, donut |
| `socrata_toolkit.viz.map` | Folium interactive map, cluster map |
| `socrata_toolkit.viz` | `treemap_chart()`, `animated_scatter_chart()` (via analysis module) |

### Export Formats

- **PPTX** — Cart sidebar → PPTX button (requires sidecar running with `python-pptx`)
- **PNG/SVG/PDF** — Python `viz` module chart functions
- **GeoJSON** — Map modal
- **Markdown report** — Cart sidebar → MD
- **Jupyter notebook** — Cart sidebar → .ipynb
- **Governance JSON** — Governance tab → Export report
