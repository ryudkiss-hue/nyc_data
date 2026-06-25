# NYC DOT SIM Toolkit

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Dash App](https://img.shields.io/badge/UI-Dash/Mantine-cyan?style=flat-square)](app/dash_app.py)
[![100+ Charts](https://img.shields.io/badge/Visualizations-100%2B-orange?style=flat-square)](app/callbacks/)

**NYC DOT SIM Toolkit** is a Python-based analysis platform for NYC's Sidewalk Inspection & Management program. It ingests live Socrata open data, detects spatial conflicts between construction permits and inspections, performs data quality analysis, and surfaces interactive visualizations via **Dash/Plotly** with a **Mantine UI** — all backed by DuckDB for high-performance local analytics and FastAPI for production-grade infrastructure.

### Key Features

| Feature | Status |
|---------|--------|
| **Dash Mission Control** (FastAPI + Plotly + Mantine) | ✅ |
| **30+ Interactive Plotly Charts** | ✅ |
| **Real-time Callbacks & Filters** | ✅ |
| **Spatial Conflict Detection** | ✅ |
| **Bayesian SLA Forecasting** | ✅ |
| **Data Quality Scoring** (0–100) | ✅ |
| **DuckDB L2 Cache** (Parquet) | ✅ |
| **CLI Toolkit** (socrata commands) | ✅ |
| **PDF/Excel/PPTX Reports** | ✅ |
| **Natural Language Queries** (Claude API) | ✅ |
| **Schema Drift Detection** | ✅ |
| **Streamlit UI** (Secondary option) | ✅ |

---

## Quick Start

### 1. Install
```bash
git clone <repo>
cd nyc_data
pip install -e ".[mission,xlsx]"
```

### 2. Run the Dashboard
```bash
# Start Dash Mission Control (PRIMARY)
python app/dash_app.py
# → Open http://localhost:8011

# Or use the launcher shim
python main.py

# Or use Streamlit (SECONDARY option)
streamlit run app/app.py
# → Open http://localhost:8501
```

### 3. Configure (Optional)
For live data access (>2,000 rows), set your Socrata API token:
```bash
export SOCRATA_APP_TOKEN=your-token-here
export ANTHROPIC_API_KEY=your-api-key-here
```

See **[QUICKSTART.md](QUICKSTART.md)** for detailed setup and **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for cloud deployment.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│              NYC DOT SIM Toolkit (v0.4.1)                  │
├────────────────┬──────────────────────────┬────────────────┤
│  Streamlit UI  │  MotherDuck Dives (New!) │  CLI Toolkit   │
│  (Mission      │  (Interactive Analytics) │  (socrata      │
│   Control)     │  Replaces Jupyter NB     │   commands)    │
├────────────────┴──────────────────────────┴────────────────┤
│                      Data Layer                            │
│  ┌───────────────────┐ ┌────────────────┐ ┌─────────────┐  │
│  │ Live Socrata API  │ │ DuckDB L2      │ │ MotherDuck  │  │
│  │ (57 datasets)     │ │ Parquet Cache  │ │ Cloud       │  │
│  └───────────────────┘ └────────────────┘ └─────────────┘  │
└────────────────────────────────────────────────────────────┘
```

> **Note on Legacy Dashboards:** All previous Jupyter Notebook dashboards (`01_inspection_dashboard.ipynb` through `05_advanced_analytics.ipynb`) have been moved to `jupyter_book/legacy_dashboards/` and are officially **SUPERSEDED**.
> Moving forward, all visual and statistical reporting for NYC DOT is managed as *Dives-as-Code* in the `dives/` directory. Use the synchronization utilities in `scripts/motherduck_dives_sync/` to push/pull dynamic Recharts+Mantine components back to the MotherDuck cloud workspace.

---

## Dataset Registry

**CURRENT SOURCE OF TRUTH:** See `SOCRATA_DATASETS_CONSOLIDATED.md` for complete registry with all 57 datasets, Metric mappings, and visualization cross-references.

All 57 datasets are defined in `config/datasets.yaml` and loaded at runtime.

| Key | Description | Fourfour | Category |
|-----|-------------|----------|----------|
| `inspection` | SMD Inspection | dntt-gqwq | core_smd |
| `violations` | SMD Violations | 6kbp-uz6m | core_smd |
| `built` | SMD Built | ugc8-s3f6 | core_smd |
| `lot_info` | SMD Lot Info | i642-2fxq | core_smd |
| `reinspection` | SMD ReInspection | gx72-kirf | core_smd |
| `tree_damage` | All Tree Damage | j6v2-6uxq | core_smd |
| `dismissals` | Sidewalk Dismissal Inspection Tracking | p4u2-3jgx | core_smd |
| `correspondences` | Sidewalk Correspondences | bheb-sjfi | core_smd |
| `curb_metal_protruding` | Curb Metal Protruding Data | i2y3-sx2e | core_smd |
| `ramp_locations` | Pedestrian Ramp Locations | ufzp-rrqu | accessibility |
| `ramp_complaints" | Ramp Complaints | jagj-gttd | accessibility |
| `ramp_progress` | Ramp Program Progress | e7gc-ub6z | accessibility |
| `street_permits` | Street Construction Permits | tqtj-sjs8 | coordination |
| `weekly_construction` | Weekly Construction Schedule | r528-jcks | coordination |
| `capital_blocks` | Capital Reconstruction Blocks | jvk9-k4re | coordination |
| `capital_intersections` | Capital Reconstruction Projects - Intersection | 97nd-ff3i | coordination |
| `street_construction_inspections` | Street Construction Inspections (HIQA) | ydkf-mpxb | coordination |
| `street_closures_block` | Street Closures by Block | i6b5-j7bu | coordination |
| `permit_stipulations" | Street Construction Permit Stipulations | gsgx-6efw | coordination |
| `street_resurfacing_schedule` | Street Resurfacing Schedule | xnfm-u3k5 | coordination |
| `street_resurfacing_inhouse` | DOT In-house Street Resurfacing Projects | ffaf-8mrv | coordination |
| `step_streets" | Step Streets Locations | u9au-h79y | overlays |
| `sidewalk_planimetric` | Planimetric Sidewalks | vfx9-tbb6 | overlays |
| `pedestrian_demand` | Pedestrian Demand | fwpa-qxaf | overlays |
| `mappluto` | MapPLUTO | 6fi9-q3ta | overlays |
| `complaints_311` | 311 Sidewalk/Curb | erm2-nwe9 | overlays |

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `socrata conflict-detect --borough MN` | Detect spatial conflicts |
| `socrata report contract` | Generate contract report |
| `socrata dataset health --all --stale 7 --sort-by staleness` | Check dataset status (row count, staleness, emptiness) |
| `socrata dataset ramp-analysis --full-corpus --borough MN` | Analyze pedestrian ramp completion rates by borough |
| `socrata cache refresh <key>` | Refresh L2 cache |
| `socrata export <key> --format csv` | Export dataset |
| `socrata nl-query "<question>"` | Natural language query |

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|---------|
| `SOCRATA_ALLOWED_KEY_HASHES` | Comma-separated SHA-256 hashes for API key validation | Yes (for API) |
| `SOCRATA_APP_TOKEN` | Socrata API token | No |
| `ANTHROPIC_API_KEY` | Claude API key for NL queries | No |
| `SLACK_WEBHOOK_URL` | Slack alerts webhook | No |
| `SOCRATA_CACHE_DIR` | L2 cache directory | No |

---

## Docker & Cloud Deployment

**Local Docker:**
```bash
docker compose up mission-control
# UI: http://localhost:8501
```

**Cloud Deployment** (AWS ECR, Google Cloud Run, Azure ACR):
See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for detailed instructions.

---

## Development

```bash
# Run tests
python -m pytest tests/ -q --tb=short

# Lint
ruff check src/socrata_toolkit tests app

# Format
black src/socrata_toolkit tests app
```

### Local Pre-Push Testing

Before pushing to main, run the CI simulation on your local Python version to catch failures early:

```bash
# Simulates GitHub Actions matrix (ruff + pytest) on current Python version
make ci-check
```

This runs the same quality checks that GitHub Actions will run on Python 3.10, 3.11, and 3.12:
- **Ruff linting** — Validates code style and correctness (E, F, W, I, UP, B rules)
- **Pytest** — Runs unit and integration test suite (excluding heavy tests)

The workflow matrix is defined in `.github/workflows/python-package.yml` and tests against Python 3.10, 3.11, and 3.12. The `make ci-check` target acts as a local pre-flight check on your current Python version to save CI time.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide.

---

## Documentation

| Doc | Description |
|-----|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and PR guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [CLAUDE.md](CLAUDE.md) | AI assistant guidance for this repo |
| [data-analytics-skills/QUICKSTART.md](data-analytics-skills/QUICKSTART.md) | 31-skill analytics library |

---

*Built for NYC DOT Sidewalk Inspection & Management · Powered by [NYC Open Data](https://opendata.cityofnewyork.us/)*

