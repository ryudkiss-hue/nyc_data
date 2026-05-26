# 📋 Changelog

All notable changes to Manhattan Mission Control, organized by version.

---

## v2.0.0 — Manhattan Mission Control V2 (May 2025)

This is a major release introducing the standalone browser-based Open Data Explorer and dozens of new features.

### 🌐 New: Standalone HTML Explorer

A completely new single-file HTML/JS application (`app/static/mission_control_v2.html`) that:
- Runs entirely in the browser — **no server, no install**
- Deployed automatically to **GitHub Pages** on every push to `main`
- Live at [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/)

### 🆕 New Features

#### Search & Discovery
- Smart keyword search across NYC Open Data catalog
- Category, type, and freshness filters
- Sort by relevance, name, views, updated date
- Sample search chips for quick exploration
- Tag-based filtering with pill UI
- Freshness indicators on all results

#### Dataset Cart
- Collect up to 50 datasets
- **Undo/Redo** cart changes (Ctrl+Z / Ctrl+Y)
- Batch export all cart datasets
- Side-by-side dataset comparison
- Dataset tagging and labeling

#### SOQL Query Studio
- Live SQL-like query editor
- Syntax highlighting
- Query history with navigation
- Pre-built query templates
- Auto-visualization (charts + maps)
- CSV and JSON export of results

#### Interactive Maps
- Leaflet.js-powered map viewer
- Heatmap overlay
- Marker clustering
- Multiple tile layers (Street, Satellite, Dark)
- Haversine distance measurement tool
- Export map as PNG

#### AI Assistant
- Explain any dataset in plain English
- Suggest related datasets
- Generate SOQL queries from natural language
- Column type analysis (including PII detection)
- Prompt templates for common tasks

#### Code Generation
- **Python** (pandas + sodapy)
- **R** (httr + jsonlite)
- **JavaScript** (fetch API)
- **SOQL** query URL
- **GitHub Actions** automated pipeline
- **Jupyter Notebook** complete analysis
- **README.md** project template

#### Workspace Management
- Save named sessions (cart + search + query history)
- Restore any saved workspace
- Export/import workspaces as JSON
- Share via QR code or email link

#### Export & Sharing
- Markdown analysis report
- Jupyter Notebook export
- GeoJSON export for geographic data
- Citation generator (APA, Chicago, MLA)
- Embed code (iframe)
- QR code generator

#### Accessibility (WCAG 2.1 AA)
- Full keyboard navigation
- Screen reader support (ARIA live regions)
- High contrast mode
- Adjustable font size (3 levels)
- `prefers-reduced-motion` support
- Skip to main content link

#### UI & Customization
- Light/Dark theme toggle
- Compact/Comfortable/Spacious density
- Notification center with history
- Favorites (starred datasets)
- Recent activity sidebar
- Adjustable row limits

#### Interactive Help Center
- 7-tab help modal: Quick Start, Features, FAQ, Shortcuts, Tips, Glossary, What's New
- Guided interactive tour
- Inline contextual tooltips
- Dataset-type visual explanations

### 🔧 Fixes & Improvements

- **Fixed:** `ModuleNotFoundError: No module named 'app'` on Render.com
  - Added `PYTHONPATH=.` to `render.yaml` and `Procfile`
  - Added `sys.path.insert(0, _REPO_ROOT)` to `app/app.py`
  - Added `app/` to `packages` in `pyproject.toml`
- **Fixed:** GitHub Pages deploying README instead of app
  - Switched Pages source to "GitHub Actions"
  - Updated `.github/workflows/pages.yml` to properly deploy HTML
- **Fixed:** 16 Ruff lint errors (F401, E402, UP035, I001, B007, F841)
- **Fixed:** Unused imports across `analytics.py`, `publish.py`, `workflows.py`
- **Fixed:** `typing.Callable` → `collections.abc.Callable` (Python 3.9 compat)

### 🏢 Agency Dashboard Updates

- Added **Data Quality Dashboard** workflow view
- Added cross-dataset profiling in quality view
- i18n (English/Spanish) on publish and settings pages
- Improved empty states with demo mode CTA
- Settings → Cache tab with freshness report
- Settings → Logs tab with event type filtering
- `docker compose` local development support

---

## v1.3.0 — User-Friendly Extras (2024)

- **i18n:** English/Spanish UI via `app/utils/i18n.py`
- **Empty states:** Helpful onboarding when no data is loaded
- **Docker Compose:** `docker compose up` for local dev
- **Unix build:** `scripts/build_unix.sh` for macOS/Linux
- **Render/Heroku deploy:** One-click deploy buttons + `render.yaml`
- **CSV upload:** Upload custom CSV files to any workflow

---

## v1.2.0 — Agency Workflows (2024)

- **QA/QC & Inventory Ledger** workflow
- **Spatial Conflict Detection** workflow with Leaflet maps
- **Contract & Dispatch Clearance** workflow
- **Productivity & ADA Progress** workflow
- ROI calculation engine (`ProductivityROI`)
- Parquet caching with 24h TTL
- Ingestion telemetry (JSONL log)

---

## v1.1.0 — Streamlit Dashboard (2024)

- Migrated from Dash to Streamlit
- Settings → Readiness score (5 axes, 0–100)
- Settings → Completeness tracker (24-item checklist)
- Settings → System health checks
- Publish page: email, Teams, S3, PDF export
- Dataset registry (`config/datasets.yaml`)

---

## v1.0.0 — Initial Release (2024)

- Python CLI: `socrata analyst run`
- Analyst pack: 15 Socrata dataset workflows
- DuckDB local storage
- Socrata API integration with rate limiting
- Windows installer (`.exe`)
- Basic Dash web UI (now archived in `legacy_archive/`)

---

*[[Home]] · [[Feature-Reference]] · [[Deployment-Guide]] · [[Troubleshooting]]*
