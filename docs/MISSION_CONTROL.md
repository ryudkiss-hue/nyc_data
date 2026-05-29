# 🚧 Manhattan Mission Control

**NYC DOT SIM — Open Data Explorer + Agency Analytics Platform**

Live at: [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/)

---

## Two Modes

| Mode | File | How to access |
|------|------|--------------|
| **🌐 Browser App** | `app/static/mission_control_v2.html` | [GitHub Pages](https://ryudkiss-hue.github.io/nyc_data/) — no install |
| **🏢 Agency Dashboard** | `app/app.py` | `PYTHONPATH=. streamlit run app/app.py` |

---

## Browser App (V2) — Feature Summary

The standalone HTML app (`mission_control_v2.html`) runs entirely in the browser. No server, no install, no API key required.

### Search & Discovery
- Keyword search across NYC Open Data catalog (`api.us.socrata.com/api/catalog/v1`)
- Category, type, freshness filters
- Sort by relevance, name, views, updated date
- Tag pill filtering
- Sample search chips for quick starts
- Freshness indicators

### Dataset Cart
- Collect up to 50 datasets
- Undo/redo (Ctrl+Z / Ctrl+Y)
- Batch export
- Side-by-side comparison

### SOQL Query Studio
- Live SQL-like query editor
- Query history
- Template library
- Chart + map output
- CSV / JSON export

### Map Viewer
- Leaflet.js with heatmap + clustering
- Multiple tile layers
- Haversine distance tool
- Export map as PNG

### AI Assistant
- Explain datasets
- Suggest related data
- Generate queries
- PII column detection

### Code Generation
- Python, R, JavaScript
- GitHub Actions workflow
- Jupyter Notebook
- README.md template

### Workspace Management
- Save / restore named sessions
- Export / import as JSON
- Share via QR code or email

### Export & Sharing
- CSV, JSON, GeoJSON
- Markdown report
- Jupyter Notebook
- Citation (APA/Chicago/MLA)
- Embed code (iframe)
- QR code

### Accessibility (WCAG 2.1 AA)
- Keyboard navigation
- Screen reader / ARIA live regions
- High contrast mode
- Adjustable font size
- `prefers-reduced-motion` support

### Help Center
- 7-tab interactive tutorial (Quick Start, Features, FAQ, Shortcuts, Tips, Glossary, What's New)
- Inline contextual tooltips
- Guided tour

---

## Agency Dashboard (Streamlit)

### Layout

| Path | Role |
|------|------|
| `app/app.py` | Entry point, sidebar navigation, `@st.cache_data` wrappers |
| `app/analytics.py` | `run_all_workflows()` — all 5 workflow computations |
| `app/data_loader.py` | Socrata ingestion, parquet cache, dataset registry |
| `app/services/agency.py` | Health checks, completeness items, ingest log |
| `app/ui/theme.py` | CSS injection, header, readiness bar components |
| `app/ui/empty_states.py` | Onboarding UI for no-data state |
| `app/utils/i18n.py` | EN/ES translation (t() function) |
| `app/views/home.py` | Home / onboarding page |
| `app/views/workflows.py` | All 5 workflow view renderers |
| `app/views/publish.py` | Publish & Pack page |
| `app/views/settings.py` | Readiness, completeness, health, cache, logs |
| `config/datasets.yaml` | Socrata registry (single source of truth) |

### Workflow Views

| View key | Label | Datasets |
|----------|-------|---------|
| `qa` | 🔍 QA/QC & Inventory Ledger | Inspection results, defects |
| `spatial` | 🗺️ Spatial Conflict Detection | Permits, boundaries |
| `contract` | 📋 Contract & Dispatch Clearance | Contract status, crew |
| `productivity` | 🚶 Productivity & ADA Progress | Inspector metrics, ADA ramps |
| `quality` | 🩺 Data Quality Dashboard | All datasets (cross-profiling) |

### Run

```bash
# Recommended
PYTHONPATH=. streamlit run app/app.py

# With explicit token
PYTHONPATH=. SOCRATA_APP_TOKEN=your_token streamlit run app/app.py

# Demo mode (no API calls)
PYTHONPATH=. MISSION_DEMO=1 streamlit run app/app.py
```

Dataset registry: `config/datasets.yaml`  
Local parquet cache: `data/local_db/socrata_cache/` (24h TTL)  
Ingestion log: `outputs/logs/ingest.jsonl` (gitignored)

### CLI

```bash
pip install -e ".[xlsx,postgres]"
socrata analyst run --profile config/analyst_profile.yaml
socrata readiness
```

### Databases

DuckDB files: `data/local_db/` (see `config/analyst_profile.example.yaml`)

---

## Deployment

### GitHub Pages (HTML App)

Auto-deployed via `.github/workflows/pages.yml` on every push to `main`.

```yaml
# .github/workflows/pages.yml
- name: Prepare Pages content
  run: |
    mkdir -p _site
    cp app/static/mission_control_v2.html _site/index.html
```

### Render.com (Streamlit)

```yaml
# render.yaml
startCommand: >
  PYTHONPATH=. python -m streamlit run app/app.py
  --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
```

Critical: `PYTHONPATH=.` must be set (prevents `ModuleNotFoundError: No module named 'app'`).

---

## User-Friendly Extras

- i18n (EN/ES) — `app/utils/i18n.py`
- Empty states with demo mode CTA — `app/ui/empty_states.py`
- Docker Compose — `docker compose up`
- Unix build — `scripts/build_unix.sh`
- Render/Heroku one-click deploy — `render.yaml`, Heroku button

See [USER_FRIENDLY_FEATURES.md](USER_FRIENDLY_FEATURES.md) for details.

---

## Further Reading

| Doc | Content |
|-----|---------|
| [README.md](../README.md) | Main project overview |
| [DEPLOY_CLOUD.md](DEPLOY_CLOUD.md) | Full cloud deployment guide |
| [API_REFERENCE.md](API_REFERENCE.md) | SOQL + Socrata API |
| [AGENCY_RUNBOOK.md](AGENCY_RUNBOOK.md) | Agency operations |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common errors |
| [wiki/](../wiki/) | Full wiki documentation |
