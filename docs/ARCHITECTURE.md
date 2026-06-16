# System Architecture — NYC DOT Sidewalk Toolkit

Complete architectural reference showing the Dash/FastAPI/Plotly stack, data flows, and component integration.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                   NYC DOT SIM Toolkit v0.5.0                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐    PRIMARY: Dash/FastAPI/Plotly       │
│  │   User Interface    │    ├─ HTTP: http://localhost:8011     │
│  │                     │    ├─ UI: Mantine components          │
│  │  Dash 4.2           │    ├─ Charts: 30+ Plotly interactive  │
│  │  + FastAPI          │    └─ Callbacks: Real-time updates    │
│  │  + Mantine          │                                        │
│  │  + Plotly           │    SECONDARY: Streamlit (fallback)    │
│  └─────────────────────┘    ├─ HTTP: http://localhost:8501    │
│            │                └─ Use: Data exploration            │
│            │                                                    │
│            ▼                                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │         FastAPI Backend (Python 3.11)                   │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ Callback Handlers (app/callbacks/)                      │  │
│  │  ├─ analytics.py      → KPI metrics, time-series       │  │
│  │  ├─ gis.py            → Spatial analysis, mapping      │  │
│  │  ├─ export_callbacks.py → PDF/Excel/PPTX generation    │  │
│  │  ├─ visualization_callbacks.py → Plotly figures        │  │
│  │  └─ navigation.py     → Page routing                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│            │                                                   │
│            ▼                                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │    Analysis & Data Processing (socrata_toolkit)         │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ • 65 Analysis modules      • 16 Quality modules         │  │
│  │ • 17 Visualization modules • Data profiling, SLA check  │  │
│  └─────────────────────────────────────────────────────────┘  │
│            │                                                   │
│            ▼                                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │         Data Access Layer                               │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │  DuckDB L2 Cache (LOCAL, FAST)                          │  │
│  │  ├─ Parquet files (columnar, compressed)               │  │
│  │  ├─ 2–5 GB typical, queries <500ms                     │  │
│  │  └─ 26 datasets: inspections, violations, permits, etc.│  │
│  │                                                         │  │
│  │  Live Socrata API (when needed)                         │  │
│  │  PostgreSQL (optional)                                  │  │
│  │  Redis Cache (optional)                                 │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Deployment Options

**Local:** `python app/dash_app.py` → http://localhost:8011

**Docker:**
```bash
docker build -t nyc-mission:dash --target mission .
docker run -p 8011:8011 nyc-mission:dash
```

**Cloud:** AWS ECS, Google Cloud Run, Render, Heroku (see DEPLOYMENT_GUIDE.md)

---

## Component Stack

### Frontend (Dash + Mantine + Plotly)

- **Entry Point:** `app/dash_app.py` (6600 LOC)
- **Layouts:** `app/dash_layouts.py`, `app/dash_layouts_gis.py`, `app/dash_layouts_analytics_integration.py`
- **Components:** `app/components/` (filter system, KPI cards, spatial maps)
- **Styling:** `app/assets/custom.css` (Mantine + Plotly theming)

### Backend (FastAPI + Analysis Toolkit)

- **Callbacks:** `app/callbacks/` (5 handler modules)
  - `analytics.py` — KPI updates, metrics
  - `gis.py` — Spatial analysis, maps
  - `export_callbacks.py` — PDF/Excel/PPTX
  - `visualization_callbacks.py` — Plotly figures
  - `navigation.py` — Page routing

- **Analysis:** `src/socrata_toolkit/analysis/` (65 modules)
  - Core: bayesian, clustering, ensemble, forecasting, inference
  - Domain: complaint, dismissal, ramp, hotspot, velocity, sentiment, NLP
  - Output: metrics, insights, reporting

- **Quality:** `src/socrata_toolkit/quality/` (16 modules)
  - Profiler, rules engine, validation framework
  - SLA tracking, anomaly detection, freshness checks
  - Quality scoring (0–100)

- **Visualization:** `src/socrata_toolkit/viz/` (17 modules)
  - Plotly charts, statistical visualizations
  - GIS mapping (Scattermapbox, DBSCAN, TSP)
  - Dashboard building, chart recommendation
  - Accessibility, theming

### Data Layer

- **DuckDB:** `data/local_db/nyc_mission_control.duckdb` (Parquet cache)
- **Socrata API:** 26 live datasets (when cache stale or full-corpus needed)
- **PostgreSQL:** Optional permanent warehouse (if PG_DSN set)

### CLI Layer

- **Entry:** `src/socrata_toolkit/core/cli.py`
- **Commands:** `socrata [COMMAND]` (15 command categories)
- **Examples:** dataset health, fetch, sync, analyze, quality-score, nl-query, etc.

---

## Data Flow Example

User selects borough filter in Dash → Callback triggered → Analysis module computes metrics → Quality module validates data → Visualization module generates Plotly figure → Browser renders real-time update (<500ms)

---

## Technology Versions

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Core language |
| Dash | 4.2+ | Interactive dashboard |
| FastAPI | 0.100+ | Web backend (async) |
| Mantine | 8.0+ | UI components |
| Plotly | 5.0+ | Charts |
| DuckDB | 0.9.0+ | Local OLAP DB |
| PyMC | 5.0+ | Bayesian inference |
| Prophet | 1.1+ | Forecasting |
| Pytest | 9.0+ | Testing (4100+ tests) |

---

## Performance

**Page Load:** 200–500ms  
**Callback Update:** 300–800ms  
**Spatial Analysis:** 2–5s  
**Bayesian Inference:** 5–10s  
**Memory Usage:** 500 MB–2 GB (depends on dataset size)

---

## Related Docs

- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — How to deploy
- [`MISSION_CONTROL.md`](MISSION_CONTROL.md) — Dashboard features
- [`ANALYSIS_MODULES.md`](ANALYSIS_MODULES.md) — Component catalog
- [`CLI_REFERENCE.md`](CLI_REFERENCE.md) — Command-line interface
