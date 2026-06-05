# NYC DOT SIM Analyst Toolkit — Developer Guide

**A unified Streamlit dashboard + Python CLI + REST API for analyzing NYC sidewalk inspection & management data.**

## Project At a Glance

| Property | Value |
|----------|-------|
| **Type** | Web + CLI + Python library |
| **Language** | Python 3.11+ |
| **UI Framework** | Streamlit 1.30+ |
| **Data Source** | NYC Socrata (26 open datasets) |
| **Cache Layer** | DuckDB (columnar SQL DB) |
| **AI Integration** | Claude API (Anthropic) |
| **Visualizations** | 30+ charts (Plotly, Folium, Pydeck) |

## Quick Start (3 ways)

### 1. Web Dashboard
```bash
pip install -e ".[mission]"
streamlit run app/app.py  # http://localhost:8501
```

### 2. CLI
```bash
socrata dataset health --all
socrata fetch data.cityofnewyork.us dntt-gqwq --limit 100
socrata nl-query "violations last 90 days"
```

### 3. Python
```python
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.analysis import quality_report

client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe("data.cityofnewyork.us", "dntt-gqwq")
score = quality_report(df, key_columns=["id"], date_column="created_date")
print(f"Quality: {score.overall:.1f}/100")  # 0–100 composite
```

## The 11 Dashboards

| Tab | Render Function | Charts | Purpose |
|-----|-----------------|--------|---------|
| Home | `render_home_page()` | 3 | Overview, quick stats |
| GIS | `render_gis_page()` | 10 | Spatial maps, conflicts |
| Construction | `render_construction_page()` | 4 | Scope, cost, prioritization |
| Contracts | `render_contracts_page()` | 5 | Gantt, timeline, dispatch |
| Forecasting | `render_forecasting_page()` | 4 | Time series, Bayesian SLA |
| Data Discovery | `render_data_discovery_page()` | — | Search, schema, lineage |
| **Advanced Analytics** | `render_analytics_advanced_page()` | **13** | **Hypothesis testing, drill-down** |
| Analytical Skills | `render_analytical_skills_page()` | — | 31 AI-powered frameworks |
| Catalog | `render_data_catalog_page()` | 3 | Dataset health, SLA |
| Publish | `render_publish_page()` | — | Export (Excel, PDF, PPTX) |
| Settings | `render_settings_page()` | — | Config, tokens, profiles |

**Plus 5 Workflows**: QA/QC, Spatial, Contract, Productivity, Quality

## Architecture

```
Socrata Data (26 datasets)
  ↓ SocrataClient (core/client.py)
  ↓ DuckDB Cache (data/local_db/)
  ↓ 7 Pillars
  ├─ Core: API, auth, DuckDB, CLI
  ├─ Analysis: Profiling, quality, insights
  ├─ Analyst: Workflows, publishing
  ├─ Quality: SLA, freshness
  ├─ Viz: 30+ charts
  ├─ Governance: Lineage, audit
  └─ Engineering: Domain logic
  ↓ CLI (60+ commands)
  ↓ Streamlit UI (11 tabs)
  ↓ Python API
```

## Key Metrics

- **26 Datasets**: Core SMD, accessibility, coordination, overlays
- **30+ Charts**: Plotly, Folium, Pydeck
- **60+ CLI Commands**: Fetch, quality, conflicts, reports, etc.
- **212 Python Modules**: 7 pillars, 75+ features
- **146 Test Files**: 76 unit + 70 coverage
- **45% Coverage Gate**: `src/socrata_toolkit/{analyst,core}`

## Data Quality Scoring

Composite 0–100 from 4 weighted components:
- **Completeness** (35%): null rate
- **Validity** (25%): type mismatch
- **Consistency** (25%): duplicates
- **Freshness** (15%): age vs SLA

Constants in `src/socrata_toolkit/governance/core.py`.

## SLA Thresholds

Single source: `data/sla_config.json`
- **HIGH** = 14 days (inspections, violations)
- **MEDIUM** = 30 days (permits, ramps)
- **LOW** = 60 days (reference data)

## Setup

### Install
```bash
pip install -e ".[mission,viz,geo,llm,postgres,reports]"
export SOCRATA_APP_TOKEN="your-token"  # Optional
```

### Code Quality
```bash
ruff check src/ app/ tests/
pytest tests/ -q
```

### Run
```bash
streamlit run app/app.py     # Web
socrata --help               # CLI
python -c "import socrata_toolkit; ..."  # Python
```

## Common Tasks

### Add a Chart
```python
# src/socrata_toolkit/viz/plotly.py
def my_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(...)
    return fig

# app/views/analytics_advanced.py
st.plotly_chart(my_chart(df), use_container_width=True)

# tests/test_plotly_charts.py
def test_my_chart(self):
    assert my_chart(pd.DataFrame(...)) is not None
```

### Add CLI Command
```python
# src/socrata_toolkit/core/cli.py
@cli.command()
@click.option("--dataset")
def my_command(dataset):
    """Description."""
    client = SocrataClient(SocrataConfig())
    df = client.fetch_dataframe("data.cityofnewyork.us", dataset)
    click.echo(f"Loaded {len(df)} rows")
```

### Run Tests
```bash
pytest tests/ -q                         # All
pytest tests/test_governance_weights.py  # Weights
pytest tests/test_sla_config.py          # SLA
pytest tests/ --cov                      # Coverage (45% target)
```

## Deployment

### Docker
```bash
docker build -f Dockerfile.mission -t nyc-sim .
docker run -e SOCRATA_APP_TOKEN="..." -p 8501:8501 nyc-sim
```

### CI/CD
- **ci.yml**: Tests + coverage
- **validate-docs-consistency.yml**: Docs sync
- **deploy.yml**: Build + push
- Requires: ruff ✅ + pytest ✅ + docker ✅ + CodeQL ✅

## Documentation

- **docs/README.md** (this): Quick start, tasks
- **docs/ARCHITECTURE.md**: System design, pillars
- **docs/DEVELOPMENT.md**: Conventions, patterns
- **docs/API.md**: Python API reference
- **docs/DEPLOYMENT.md**: Docker, CI/CD
- **CLAUDE.md** (24KB): Claude Code guidance
- **CONTRIBUTING.md**: PR workflow
- **SECURITY.md**: Security practices

## Status

✅ Production Ready | 📄 MIT License | 📅 Last Updated: 2026-06-05

---

**For setup details, see `QUICKSTART.md`. For architecture, see `docs/ARCHITECTURE.md`.**
