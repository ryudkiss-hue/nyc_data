# NYC DOT SIM Analyst Toolkit

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![30+ Visualizations](https://img.shields.io/badge/Visualizations-30%2B-orange?style=flat-square)](app/)
[![75+ Features](https://img.shields.io/badge/Features-75%2B-purple?style=flat-square)](src/socrata_toolkit/)

A unified Streamlit Mission Control dashboard and Python CLI toolkit for NYC DOT analysts. It ingests live Socrata open data, runs Bayesian SLA forecasting, performs spatial conflict detection, and surfaces 30+ interactive visualizations — all backed by a DuckDB L2 cache and a natural-language query interface powered by the Claude API.

---

## Feature Matrix

| Feature | Status |
|---------|--------|
| Streamlit Mission Control | ✅ |
| GIS Dashboard (10 charts) | ✅ |
| Advanced Analytics (13 charts) | ✅ |
| Spatial Conflict Detection | ✅ |
| Contract Analytics & Gantt | ✅ |
| Bayesian SLA Forecasting | ✅ |
| DuckDB L2 Cache | ✅ |
| Nightly Prefetch Scheduler | ✅ |
| NL Query (Claude API) | ✅ |
| PDF/Excel/PPTX Reports | ✅ |
| CLI Analyst Commands | ✅ |
| Data Quality Scorecard | ✅ |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           NYC DOT SIM Analyst Toolkit        │
├──────────────┬──────────────┬────────────────┤
│  Streamlit   │  CLI Toolkit │  Python API    │
│  Mission     │  socrata     │  socrata_      │
│  Control     │  commands    │  toolkit       │
├──────────────┴──────────────┴────────────────┤
│              Data Layer                      │
│  ┌──────────────┐    ┌───────────────────┐   │
│  │ Socrata SODA │    │ L2 Parquet Cache  │   │
│  │ NYC Open Data│    │ DuckDB Store      │   │
│  └──────────────┘    └───────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## Quickstart

```bash
pip install -e ".[mission]"
streamlit run app/app.py

# CLI:
socrata --help
socrata dataset health
socrata nl-query "How many inspections per borough?" --dataset sidewalk_inspections
```

Open **http://localhost:8501** — demo mode loads automatically (no token needed).

**With live data:** add `SOCRATA_APP_TOKEN=your_token` to a `.env` file.

---

## Dataset Registry

All 26 datasets are defined in `config/datasets.yaml` and loaded at runtime.

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
| `ramp_complaints` | Ramp Complaints | jagj-gttd | accessibility |
| `ramp_progress` | Ramp Program Progress | e7gc-ub6z | accessibility |
| `street_permits` | Street Construction Permits | tqtj-sjs8 | coordination |
| `weekly_construction` | Weekly Construction Schedule | r528-jcks | coordination |
| `capital_blocks` | Capital Reconstruction Blocks | jvk9-k4re | coordination |
| `capital_intersections` | Capital Reconstruction Projects - Intersection | 97nd-ff3i | coordination |
| `street_construction_inspections` | Street Construction Inspections (HIQA) | ydkf-mpxb | coordination |
| `street_closures_block` | Street Closures by Block | i6b5-j7bu | coordination |
| `permit_stipulations` | Street Construction Permit Stipulations | gsgx-6efw | coordination |
| `street_resurfacing_schedule` | Street Resurfacing Schedule | xnfm-u3k5 | coordination |
| `street_resurfacing_inhouse` | DOT In-house Street Resurfacing Projects | ffaf-8mrv | coordination |
| `step_streets` | Step Streets Locations | u9au-h79y | overlays |
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
| `SOCRATA_APP_TOKEN` | Socrata API token | No |
| `ANTHROPIC_API_KEY` | Claude API key for NL queries | No |
| `SLACK_WEBHOOK_URL` | Slack alerts webhook | No |
| `SOCRATA_CACHE_DIR` | L2 cache directory | No |

---

## Docker

```bash
docker build -f Dockerfile.mission -t mission-control .
docker run -p 8501:8501 --env-file .env mission-control
```

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
