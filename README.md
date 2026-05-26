# 🚧 Manhattan Mission Control

**NYC DOT Sidewalk Inspection & Management — Open Data Explorer + Agency Analytics Platform**

[![🚀 Live App](https://img.shields.io/badge/🌐_Live_App-GitHub_Pages-blue?style=for-the-badge)](https://ryudkiss-hue.github.io/nyc_data/)
[![Deploy to Render](https://img.shields.io/badge/Deploy-Render.com-46E3B7?style=for-the-badge&logo=render)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)
[![Deploy to Heroku](https://img.shields.io/badge/Deploy-Heroku-430098?style=for-the-badge&logo=heroku)](https://heroku.com/deploy?template=https://github.com/ryudkiss-hue/nyc_data)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-yellow?style=for-the-badge&logo=python)](https://python.org)

---

## ✨ What Is This?

**Manhattan Mission Control** is a dual-mode platform:

| Mode | What it is | Who needs it |
|------|-----------|--------------|
| 🌐 **Open Data Explorer** | Standalone HTML app — no install, runs in any browser | Anyone exploring NYC open data |
| 🏢 **Agency Dashboard** | Streamlit backend with live Socrata ingestion, analytics & publishing | NYC DOT analysts & managers |

### 🌐 Zero-Install Browser App — Try It Now

> **[https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/)**

No login. No install. Just open the link in your browser. Works on any device.

```
Search → Preview → Analyze → Export → Share
```

---

## 🗺️ Quick Feature Map

```
Manhattan Mission Control
├── 🌐 Open Data Explorer (mission_control_v2.html)
│   ├── 🔍 Smart Search  — keyword, tag, category filters
│   ├── 🛒 Dataset Cart  — collect, compare, export
│   ├── 📊 SOQL Query Studio — live SQL on any dataset
│   ├── 🗺️ Map Viewer    — Leaflet + heatmaps + clustering
│   ├── 🤖 AI Assistant  — explain datasets, generate code
│   ├── 💾 Workspaces    — save & restore sessions (localStorage)
│   └── 📤 Export        — CSV, JSON, GeoJSON, Markdown, Jupyter
│
└── 🏢 Agency Dashboard (Streamlit)
    ├── 🔍 QA/QC & Inventory Ledger
    ├── 🗺️ Spatial Conflict Detection
    ├── 📋 Contract & Dispatch Clearance
    ├── 🚶 Productivity & ADA Progress
    ├── 🩺 Data Quality Dashboard
    └── ⚙️ Settings (readiness, health, cache, logs)
```

---

## 🚀 Getting Started

### Option A — Browser App (Recommended, Zero Setup)

1. Open **[https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/)**
2. Type a search term (e.g., "sidewalk", "parking", "311 complaints")
3. Click a result to preview, or **Add to Cart** to collect datasets
4. Use the **SOQL Studio** to run custom queries
5. Export your findings as CSV, Markdown report, or Jupyter notebook

> 💡 **Tip:** Press `?` or click **Help** in the top-right corner for the full interactive tutorial.

### Option B — Run the Agency Dashboard Locally

```bash
# 1. Clone the repo
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data

# 2. Install dependencies
pip install -e ".[mission,postgres,xlsx]"

# 3. Configure (optional — skip for demo mode)
cp .env.example .env
# Edit .env: SOCRATA_APP_TOKEN=your_token_here

# 4. Launch
PYTHONPATH=. streamlit run app/app.py
```

Open **http://localhost:8501** in your browser.

> 📝 No Socrata token? The app runs in **demo mode** automatically — sample data is loaded from bundled fixtures.

### Option C — One-Click Cloud Deploy

| Platform | Button |
|----------|--------|
| **Render.com** (recommended) | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data) |
| **Heroku** | [![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ryudkiss-hue/nyc_data) |

See **[docs/DEPLOY_CLOUD.md](docs/DEPLOY_CLOUD.md)** for full cloud deployment instructions.

---

## 🌟 Feature Highlights

### 🔍 Smart Search Engine
- Full-text search across **thousands of NYC open datasets**
- Filter by **category** (Transportation, Housing, Health, Environment…)
- Filter by **data type** (maps, tables, calendars)
- **Freshness indicators** — see when each dataset was last updated
- **Category pills** — click to explore a topic instantly
- **Sample searches** — one-click starter queries for common use cases

### 🛒 Dataset Cart & Comparison
- Add up to **50 datasets** to your cart
- **Undo/redo** cart changes (Ctrl+Z / Ctrl+Y)
- Compare datasets side-by-side
- **Tag & organize** with custom labels
- **Batch export** all cart datasets at once

### 📊 SOQL Query Studio
- Write live **Socrata Query Language (SOQL)** queries
- Built-in **syntax highlighting** and auto-complete templates
- **Query history** — navigate back through previous queries
- **Visual chart output** — auto-render bar, line, scatter charts
- **Map visualization** — plot results on an interactive Leaflet map
- Export query results as **CSV or JSON**

### 🗺️ Interactive Map Viewer
- **Heatmaps**, **marker clustering**, and point-of-interest layers
- **Multiple tile layers** — Street, Satellite, Dark mode
- **Haversine distance tool** — measure distances on the map
- **Export map as PNG** — screenshot with one click
- **Borough boundaries** and neighborhood overlays

### 🤖 AI Assistant
- **Explain any dataset** in plain English
- **Generate Python code** to load and analyze a dataset
- **Generate SQL queries** from natural language descriptions
- Suggest **related datasets** for a given topic
- Built-in **prompt templates** for common analysis tasks

### 💻 Code Generation
Generate ready-to-run code snippets in:
- **Python** (pandas + sodapy)
- **R** (httr + jsonlite)
- **JavaScript** (fetch API)
- **SOQL** (direct API query)
- **GitHub Actions** (automated data pipeline)
- **Jupyter Notebook** (complete analysis template)

### 💾 Workspace Management
- **Save** named workspaces (cart + search state + query history)
- **Restore** any saved workspace with one click
- **Export/Import** workspaces as JSON files
- Share workspaces via **QR code** or **email link**
- **Auto-save** — your session persists across browser refreshes

### 📤 Export & Share
| Format | Content |
|--------|---------|
| **CSV** | Dataset rows |
| **JSON** | Raw API response |
| **GeoJSON** | Geographic features |
| **Markdown Report** | Formatted analysis summary |
| **Jupyter Notebook** | Executable analysis with code |
| **PDF** | Print-ready report |
| **Citation** | APA/Chicago/MLA format |
| **Embed Code** | iFrame for embedding in websites |
| **QR Code** | Shareable link |

### ♿ Accessibility
- **WCAG 2.1 AA** compliant
- Full **keyboard navigation** (Tab, Enter, Arrow keys)
- **Screen reader** support via ARIA live regions
- **High contrast mode** toggle
- **Adjustable font size** (3 sizes)
- Respects `prefers-reduced-motion` system setting

### 🎨 UI & Customization
- **Light / Dark mode** toggle
- **Compact / Comfortable / Spacious** density modes
- **Notification center** with dismissible alerts
- **Recent activity** sidebar
- **Favorites** — star datasets for quick access

---

## 🏢 Agency Dashboard (Streamlit Backend)

The Streamlit app provides agency-grade analytics for NYC DOT SIM analysts.

### Workflow Views

| View | Key Metrics |
|------|------------|
| **QA/QC & Inventory Ledger** | Defect rates, open/closed ratios, field vs. office reconciliation |
| **Spatial Conflict Detection** | Permit overlaps, buffer zones, GIS conflict mapping |
| **Contract & Dispatch Clearance** | Contract status, crew dispatch, clearance rates |
| **Productivity & ADA Progress** | Completion rates, ADA ramp counts, inspector productivity |
| **Data Quality Dashboard** | Schema completeness, null rates, freshness scores, PII flags |

### Settings & Health

- **Readiness score** — automated checks across 5 axes (data, code, infra, compliance, docs)
- **Completeness tracker** — 24-item agency sign-off checklist
- **System health monitor** — environment, dependencies, API connectivity
- **Cache manager** — parquet cache status, freshness, manual clear
- **Ingestion log** — filterable JSONL event stream

---

## 📖 SOQL Quick Reference

SOQL (Socrata Query Language) is SQL-like. Use it in the **SOQL Studio** tab.

```sql
-- Basic select
SELECT inspection_id, street_name, status
WHERE borough = 'MANHATTAN'
LIMIT 100

-- Aggregate
SELECT borough, COUNT(*) AS total
GROUP BY borough
ORDER BY total DESC

-- Filter by date
SELECT *
WHERE inspection_date >= '2024-01-01T00:00:00.000'

-- Text search
SELECT * WHERE upper(street_name) LIKE '%BROADWAY%'

-- Geospatial (within radius)
SELECT * WHERE within_circle(location, 40.7580, -73.9855, 500)
```

Full reference: **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)**

---

## 🔑 API Keys & Configuration

### Socrata App Token (Optional but Recommended)

Without a token, the Socrata API rate-limits to ~1 req/sec. A free token removes this limit.

1. Register at **[https://data.cityofnewyork.us/](https://data.cityofnewyork.us/)** → Sign In → Developer Settings → Create New App Token
2. Add to your environment:

```bash
# .env file (copy from .env.example)
SOCRATA_APP_TOKEN=your_token_here

# or export directly
export SOCRATA_APP_TOKEN=your_token_here
```

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | API tokens, secrets (gitignored) |
| `config/datasets.yaml` | Socrata dataset registry |
| `config/analyst_profile.yaml` | Analyst workflow settings |
| `config/publish_profile.yaml` | Publishing targets (email, Teams, S3) |

---

## 🗂️ Repository Structure

```
nyc_data/
├── app/                          # Streamlit agency dashboard
│   ├── app.py                    # Entry point
│   ├── analytics.py              # Workflow analytics engine
│   ├── data_loader.py            # Socrata ingestion + caching
│   ├── services/agency.py        # Health checks, completeness, logs
│   ├── ui/                       # Theme, components, empty states
│   ├── views/                    # Page renderers (home, workflows, etc.)
│   └── static/
│       └── mission_control_v2.html  # 🌟 Standalone browser app
│
├── src/socrata_toolkit/          # Core Python library
│   ├── core/                     # CLI, readiness, ingest, publish
│   └── analyst/                  # Analyst pack workflows
│
├── config/                       # YAML configuration files
├── docs/                         # All documentation (80+ files)
├── data/local_db/                # DuckDB + parquet cache (gitignored)
├── outputs/                      # Reports, exports, logs (gitignored)
├── tests/                        # pytest test suite
├── .github/workflows/            # CI + GitHub Pages deployment
├── render.yaml                   # Render.com blueprint
├── Procfile                      # Heroku/Railway process file
├── docker-compose.yml            # Docker local dev
└── pyproject.toml                # Python packaging
```

---

## 🛠️ Installation Options

### Minimal (core analyst)
```bash
pip install -e "."
```

### Mission Control (recommended)
```bash
pip install -e ".[mission,postgres,xlsx]"
```

### Full stack (everything)
```bash
pip install -e ".[all]"
```

### Optional extras
```bash
pip install -e ".[postgres]"   # PostgreSQL support
pip install -e ".[llm]"        # LLM/AI features (large download)
pip install -e ".[nlp]"        # spaCy text analysis
pip install -e ".[geo,viz]"    # Maps + charts
pip install -e ".[reports]"    # PDF + Plotly reports
pip install -e ".[exe]"        # PyInstaller Windows .exe build
```

---

## 🧪 Development

### Run Tests
```bash
python -m pytest tests/ -q
# With coverage
python -m pytest tests/ --cov=app --cov=src/socrata_toolkit -q
```

### Lint & Format
```bash
ruff check app/ src/
ruff format app/ src/
```

### Pre-commit Hooks
```bash
powershell -File scripts/setup_precommit.ps1   # Windows
# or
pip install pre-commit && pre-commit install    # any platform
```

---

## 📦 Deployment

### GitHub Pages (HTML App — auto-deployed)
Every push to `main` triggers the GitHub Actions workflow in `.github/workflows/pages.yml` which deploys `mission_control_v2.html` as the Pages site.

### Render.com (Streamlit Dashboard)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ryudkiss-hue/nyc_data)

Set `SOCRATA_APP_TOKEN` in the Render environment variables dashboard. The `render.yaml` blueprint handles the rest.

> **Troubleshooting:** If you see `ModuleNotFoundError: No module named 'app'`, ensure `PYTHONPATH=.` is set in your environment variables (it's already in `render.yaml`).

### Docker
```bash
docker compose up
# App available at http://localhost:8501
```

See **[docs/DOCKER_LOCAL.md](docs/DOCKER_LOCAL.md)** for full Docker documentation.

---

## 📚 Documentation Index

### Getting Started
| Doc | Description |
|-----|-------------|
| [docs/SIMPLE_START.md](docs/SIMPLE_START.md) | First day — plain language walkthrough |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Technical setup guide |
| [docs/MISSION_CONTROL.md](docs/MISSION_CONTROL.md) | Dashboard reference |
| [docs/FAQ.md](docs/FAQ.md) | Frequently asked questions |

### Reference
| Doc | Description |
|-----|-------------|
| [docs/USER_MANUAL.md](docs/USER_MANUAL.md) | Full feature reference |
| [docs/COMMAND_REFERENCE.md](docs/COMMAND_REFERENCE.md) | CLI commands cheat sheet |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | SOQL + Socrata API guide |
| [docs/METRICS_GLOSSARY.md](docs/METRICS_GLOSSARY.md) | KPI definitions |

### Operations
| Doc | Description |
|-----|-------------|
| [docs/AGENCY_RUNBOOK.md](docs/AGENCY_RUNBOOK.md) | Agency operations runbook |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common errors + fixes |
| [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) | Production checklist |
| [docs/DEPLOY_CLOUD.md](docs/DEPLOY_CLOUD.md) | Cloud deployment guide |

### Integrations
| Doc | Description |
|-----|-------------|
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | Email, Teams, S3, BI tools |
| [docs/MICROSOFT_365_INTEGRATION.md](docs/MICROSOFT_365_INTEGRATION.md) | M365 / Teams integration |
| [docs/DOCKER_LOCAL.md](docs/DOCKER_LOCAL.md) | Docker development |

---

## 📋 Changelog

### v2.0.0 — Manhattan Mission Control V2 (2025-05)
- 🌐 **New standalone HTML explorer** — zero-install, works in any browser
- 🤖 **AI Assistant** — dataset explainer + code generation
- 📊 **SOQL Query Studio** — live query editor with charts + maps
- 🛒 **Dataset Cart** — undo/redo, batch export, workspace save/restore
- 🗺️ **Enhanced map viewer** — heatmaps, clustering, PNG export
- 📤 **Multi-format export** — Markdown, Jupyter, GeoJSON, Citation, Embed, QR
- 🎨 **Theme system** — dark/light mode, font sizes, high contrast
- ♿ **Full accessibility** — WCAG 2.1 AA, keyboard nav, ARIA live regions
- 📚 **Interactive Help Center** — 7-tab tutorial, FAQ, glossary, shortcuts
- 💾 **Workspaces** — save/restore named sessions
- 🔔 **Notification center** — dismissible alerts with history
- ⭐ **Favorites** — bookmark datasets for quick access
- 🏷️ **SOQL history + templates** — query management
- 🔍 **Advanced filters** — category, type, freshness, tag pills
- 🌍 **i18n** — English/Spanish UI
- 🚀 **GitHub Pages** — automatic deployment on every push to main

### v1.x — Initial Release
- Python CLI + analyst pack
- Streamlit agency dashboard
- QA/QC, Spatial, Contract, Productivity workflows
- Socrata data ingestion + parquet caching
- Readiness scoring + completeness tracker
- Publish to email, Teams, S3, PDF

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Make changes + run `ruff check` + `pytest`
4. Commit with a clear message
5. Open a Pull Request

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

*Built for NYC DOT Sidewalk Inspection & Management · Powered by [NYC Open Data](https://opendata.cityofnewyork.us/) (Socrata API)*
