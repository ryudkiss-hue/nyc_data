# Manhattan Mission Control — Dash Dashboard

**NYC DOT SIM — Dash/Plotly Mission Control Dashboard**

A production-grade **Dash/FastAPI/Plotly** application for NYC DOT analysts. Ingests live Socrata datasets, runs Bayesian and Prophet forecasting models, visualizes spatial patterns with interactive Plotly charts, and provides responsive Mantine UI with real-time callbacks.

---

## Quick Start (3 commands)

```bash
# 1. Install
pip install -e ".[mission,postgres,xlsx]"

# 2. Launch (PRIMARY — Dash)
python app/dash_app.py
# → Opens at http://localhost:8011

# 3. Or use launcher shim
python main.py  # Auto-selects primary Dash
```

Alternative entry point (Streamlit — secondary):

```bash
streamlit run app/app.py
# → Opens at http://localhost:8501
```

---

## Architecture

**Primary Entry Point (Dash/FastAPI):**
```
app/dash_app.py          ← Main Dash application with FastAPI backend
├─ app/dash_layouts.py   ← Page layouts (dashboard, construction, gis, reports, etc.)
├─ app/callbacks/        ← Real-time callback handlers
│  ├─ analytics.py       ← Metric and metric callbacks
│  ├─ gis.py             ← Spatial analysis callbacks
│  ├─ export_callbacks.py← PDF/Excel export pipelines
│  └─ ...
├─ app/components/       ← Custom Dash components
│  ├─ filter_system.py   ← Interactive filter UI
│  ├─ metric_cards.py       ← Metric card components
│  └─ ...
└─ app/assets/           ← CSS, Mantine theming, custom styles
```

**Secondary Entry Point (Streamlit — fallback):**
```
app/app.py               ← Streamlit alternative for simplified data exploration
└─ app/views/            ← Streamlit page views (legacy support)
```

**Shared Data Layer:**
```
src/socrata_toolkit/     ← Core Python library
├─ core/                 ← CLI, config, persistence
├─ analysis/             ← Data analysis (cohorts, metrics, forecasting)
├─ viz/                  ← Visualization builders (Plotly, statistical charts)
├─ quality/              ← Data quality profiling and validation
└─ spatial/              ← Geospatial analytics
```

---

## Features (Dash)

### 1. Dashboard (Home)
- Metric cards with real-time metrics
- Dataset health status
- Audit trail of recent ingests
- Quick-action buttons for common workflows

### 2. Construction Lists
- Interactive borough-filtered table
- Construction project details (cost, timeline, status)
- Drill-down to individual permit records

### 3. GIS & Spatial
- Plotly Scattermapbox interactive map
- DBSCAN spatial clustering visualization
- Conflict buffer overlays (permits vs. inspections)
- TSP route optimization
- Animated borough bar charts

### 4. Contract Analytics
- Contractor performance metrics
- Spending patterns by borough
- Timeline and completion rates
- Gantt charts for project schedules

### 5. Advanced Analytics
- Bayesian SLA forecasting with credible intervals
- CUSUM control charts for process monitoring
- KMeans clustering visualizations
- Survival curves and time-to-event analysis
- Moran's I spatial autocorrelation

### 6. Governance & Compliance
- Data lineage DAG (dataset dependency graph)
- Dataset registry with schema tracking
- Ingest audit logs
- SLA compliance dashboard

### 7. Reports & Export
- PDF report generation (WeasyPrint)
- Excel export (openpyxl) with formatting
- PPTX slide deck generation
- Filtered exports by borough/date range

---

## Environment Variables

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `SOCRATA_APP_TOKEN` | NYC Open Data API token — raises rate limits | Optional |
| `ANTHROPIC_API_KEY` | Claude API for NL-to-SoQL translation | Optional |
| `MISSION_DEMO` | `1` = demo mode, no live API calls needed | Default on Render |
| `DASH_HOST` | Dash server host (default: `127.0.0.1`) | Optional |
| `DASH_PORT` | Dash server port (default: `8011`) | Optional |

Set variables in `.env` or export them in your shell before launching.

---

## Deployment Options

### Local (Python — PRIMARY)

```bash
# Install with mission extra (includes Dash, Plotly, Mantine, FastAPI, etc.)
pip install -e ".[mission,postgres,xlsx]"

# Launch Dash Mission Control (primary)
python app/dash_app.py
# → http://localhost:8011

# Or use launcher shim
python main.py
```

No Socrata token? Set `MISSION_DEMO=1` or leave it unset — demo mode loads automatically.

### Local (Streamlit — SECONDARY FALLBACK)

```bash
# Use streamlit as an alternative (less feature-rich than Dash)
streamlit run app/app.py
# → http://localhost:8501
```

### Docker

```bash
# Build the mission-control target (Dash)
docker build -t nyc-mission:dash --target mission .

# Run with port forwarding
docker run -p 8011:8011 \
  -e SOCRATA_APP_TOKEN=your_token \
  nyc-mission:dash

# Or use docker-compose (recommended)
docker compose up mission-control
```

Opens at http://localhost:8011 (Dash primary).

### Render.com (one-click cloud deployment)

`render.yaml` at the repo root is a Render blueprint. To deploy:

1. Fork / push the repo to GitHub.
2. Go to [render.com](https://render.com) → **New Blueprint** → connect the repo.
3. Render reads `render.yaml` and auto-deploys the Mission Control service.
4. Set `SOCRATA_APP_TOKEN` in the Render dashboard (Environment tab) for live data.
5. `MISSION_DEMO=1` is set by default so the app works without a token.

**Free tier notes:**
- Bayesian engine uses ADVI (~50 MB RAM) instead of NUTS (~400 MB), so it fits within Render's free memory limit.
- Render spins down free services after inactivity; first load may take ~30 seconds.
- Access at `https://<your-app>.onrender.com` (auto-HTTPS via Render)

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
| `socrata_toolkit.viz.plotly` | Borough bar, Metric gauge, Gantt, priority heatmap, trend, donut |
| `socrata_toolkit.viz.map` | Folium interactive map, cluster map |
| `socrata_toolkit.viz` | `treemap_chart()`, `animated_scatter_chart()` (via analysis module) |

### Export Formats

- **PPTX** — Cart sidebar → PPTX button (requires sidecar running with `python-pptx`)
- **PNG/SVG/PDF** — Python `viz` module chart functions
- **GeoJSON** — Map modal
- **Markdown report** — Cart sidebar → MD
- **Jupyter notebook** — Cart sidebar → .ipynb
- **Governance JSON** — Governance tab → Export report
