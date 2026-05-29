# 🗽 Manhattan Mission Control

**NYC DOT Open Data Explorer & Agency Analytics Platform**

[![Deploy to Render](https://img.shields.io/badge/Deploy-Render.com-46E3B7?style=for-the-badge&logo=render)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Python 3.9–3.12](https://img.shields.io/badge/Python-3.9–3.12-yellow?style=for-the-badge&logo=python)](https://python.org)
[![CI](https://github.com/ryudkiss-hue/nyc_data/actions/workflows/nyc-toolkit-ci.yml/badge.svg)](https://github.com/ryudkiss-hue/nyc_data/actions/workflows/nyc-toolkit-ci.yml)

---

## What Is This?

Manhattan Mission Control is a **unified 8-tab Streamlit app** for NYC DOT analysts. It combines Socrata open data ingestion, Bayesian hiring analytics, geospatial visualization, data quality monitoring, and an AI copilot — all in one dashboard.

> **One-click deploy:** connect this repo at [render.com](https://render.com) → New Blueprint. No local setup required.

---

## 🚀 Quick Start

```bash
# 1. Install
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data
pip install -e ".[mission,postgres,xlsx]"

# 2. Launch
python main.py
```

Open **http://localhost:8501** — demo mode loads automatically (no token needed).

**With live data:** add `SOCRATA_APP_TOKEN=your_token` to a `.env` file.

---

## 🗂️ The 11 Tabs

| # | Tab | What it does |
|---|-----|-------------|
| 1 | **Home** | Load 16+ NYC DOT datasets, view audit trail, dataset status cards |
| 2 | **Apex Engine** | Hiring analytics — scrape JIDs, Bayesian ADVI yield rate, Prophet 12-month forecast with confidence bands, OMB lag correlation |
| 3 | **Agency Workflows** | QA/QC ledger, spatial conflict detection, contract clearance, productivity & ADA progress |
| 4 | **Data Quality** | Per-dataset health scores w/ chart, null/duplicate profiling, SLA freshness, anomaly detection, CSV export |
| 5 | **Spatial Analytics** | Borough distribution charts, Plotly point density map, Folium bubble map, permit conflict detection |
| 6 | **Governance** | Plotly lineage DAG, dataset registry, ingest audit log, SLA compliance table |
| 7 | **AI Copilot** | Multi-backend chat (Gemini / OpenAI / Ollama) context-hydrated with live pipeline results |
| 8 | **Dictionary** | Searchable field-level metadata browser — types, null rates, cardinality across all datasets |
| 9 | **Export** | Export center — single/bulk CSV, JSON, multi-sheet Excel, ZIP bundle with manifest |
| 10 | **Settings & Quality** | Readiness score, completeness checklist, system health, credential diagnostics, cache manager |
| 11 | **Studio** | Socrata data architecture studio — schema viewer, relationship inference, code generators |

### Design system

The UI is built on a modular toolkit in `app/ui/`:
- **`palettes.py`** — color-blind-safe palettes (Okabe-Ito categorical, viridis sequential)
- **`charts.py`** — themed Plotly factory with range selectors, small multiples, chart→table a11y fallbacks
- **`components.py`** — responsive KPI cards w/ sparklines, skeleton loaders, status pills
- **`theme.py`** — fluid `clamp()` typography, auto-fit grids, 44px touch targets, WCAG 2.2 focus rings, reduced-motion/high-contrast

---

## ⚙️ Configuration

Copy `.env.example` → `.env` and set what you need:

```bash
# NYC Open Data token — optional, removes rate limits
SOCRATA_APP_TOKEN=your_token

# AI Copilot — set whichever backend you use (all optional)
GEMINI_API_KEY=...
OPENAI_API_KEY=...
OLLAMA_HOST=http://localhost:11434   # self-hosted Ollama

# Demo mode — loads sample data without a Socrata token
MISSION_DEMO=1
```

Dataset registry: **`config/datasets.yaml`** — 16+ NYC DOT Open Data endpoints.

---

## ☁️ Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)

1. Click the button above (or connect the repo manually at render.com → New Blueprint)
2. `render.yaml` handles build + start commands automatically
3. Set `SOCRATA_APP_TOKEN` in the Render dashboard for live data  
4. `MISSION_DEMO=1` is the default — the app works without any token

**Free tier compatible:** the Bayesian engine uses ADVI variational inference (~50 MB RAM) instead of NUTS sampling (~400 MB), so it runs comfortably within Render's 512 MB free plan.

---

## 🐳 Docker

```bash
docker build -f Dockerfile.mission -t mission-control .
docker run -p 8501:8501 --env-file .env mission-control
```

Or with Compose:

```bash
docker compose up
```

---

## 🧪 Development

```bash
# Run tests
python -m pytest tests/ -q -m "not legacy"

# Lint
ruff check app/ src/

# Direct launch
PYTHONPATH=src:. python -m streamlit run app/mission_control.py
```

---

## 🗂️ Repository Layout

```
nyc_data/
├── app/
│   ├── mission_control.py      # ← entry point (8-tab Streamlit app)
│   ├── data_loader.py          # Socrata ingestion + DuckDB caching
│   ├── analytics.py            # Workflow analytics engine
│   ├── views/
│   │   ├── apex.py             # Bayesian hiring analytics tab
│   │   ├── quality_dashboard.py
│   │   ├── governance.py
│   │   ├── spatial_analytics.py
│   │   ├── workflows.py
│   │   ├── home.py
│   │   ├── settings.py
│   │   └── publish.py
│   └── ui/theme.py             # Dark agency CSS + components
│
├── src/socrata_toolkit/        # Core Python library
│   ├── core/                   # SocrataClient, DuckDBManager, CLI
│   ├── quality/                # Profiler, rules, SLA tracking
│   ├── lineage/                # DAG, impact analysis
│   └── analyst/                # Analyst pack workflows
│
├── config/
│   └── datasets.yaml           # 16+ NYC DOT dataset definitions
│
├── docs/                       # 80+ documentation files
├── tests/                      # pytest suite (670+ passing)
├── render.yaml                 # Render.com one-click blueprint
├── Dockerfile.mission          # Production container
├── Procfile                    # Heroku/Railway
└── pyproject.toml
```

---

## 📦 Install Extras

```bash
pip install -e ".[mission,postgres,xlsx]"   # recommended — includes all ML + geo deps
pip install -e ".[all]"                      # everything
pip install -e ".[llm]"                      # LangChain NL→SQL (heavy)
```

---

## 📚 Documentation

| Doc | Description |
|-----|-------------|
| [docs/SIMPLE_START.md](docs/SIMPLE_START.md) | 5-minute walkthrough |
| [docs/MISSION_CONTROL.md](docs/MISSION_CONTROL.md) | Full tab-by-tab reference |
| [docs/FAQ.md](docs/FAQ.md) | Common questions incl. AI Copilot & Render |
| [docs/AGENCY_RUNBOOK.md](docs/AGENCY_RUNBOOK.md) | Daily operations guide |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Technical setup |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | All deployment options |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Error fixes |

---

## 📋 Changelog

### v3.0 — Unified Mission Control (2026-05)
- **8-tab Streamlit app** — all workflows in one unified entry point (`app/mission_control.py`)
- **Apex Engine** — Bayesian ADVI hiring analytics with Prophet forecasting + OMB lag correlation
- **AI Copilot** — Gemini / OpenAI / Ollama multi-backend, context-hydrated with live pipeline data
- **Data Quality tab** — automated health scores, SLA freshness, anomaly detection
- **Governance tab** — Plotly lineage DAG, ingest audit log, SLA compliance
- **Spatial Analytics tab** — density maps, Folium bubble map, conflict detection
- **Render free-tier deploy** — ADVI replaces NUTS (10× less RAM), graceful degradation for all heavy deps
- 670+ passing tests, ruff-clean codebase

### v2.0 — Agency Dashboard (2025)
- Streamlit agency dashboard with QA/QC, Spatial, Contract, Productivity workflows
- Socrata ingestion + DuckDB parquet caching
- Readiness scoring + completeness tracker

### v1.0 — CLI Toolkit
- Python CLI + analyst pack
- Socrata API client, SOQL builder, data profiler

---

*Built for NYC DOT Sidewalk Inspection & Management · Powered by [NYC Open Data](https://opendata.cityofnewyork.us/)*
