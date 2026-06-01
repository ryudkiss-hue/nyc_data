# CLAUDE.md

Guidance for Claude Code when working with this repository.

## What this project is

NYC DOT Sidewalk Inspection & Management Toolkit — a Streamlit-based application for analyzing SIM unit data from NYC Open Data, with a Python CLI toolkit for analysts and a desktop/web interface.

**Key components:**
- `app/` — Streamlit Mission Control dashboard (app/app.py)
- `src/socrata_toolkit/` — Core Python library for analysis, data quality, lineage tracking, governance
- `data-analytics-skills/` — 31 portable AI-powered analytical skills (see below)
- `tests/` — Test suite (pytest)
- `scripts/` — Utility scripts

**Current visualizations:** 30 across the app:
- 3 Plotly charts (velocity, lag, forecast) in mission control
- 2 Streamlit maps (spatial workflows, studio view)
- 1 scatter chart (workflows view)
- 13 Advanced Analytics charts (CUSUM, Bayesian CI, KMeans, survival curves, etc.)
- 10 GIS Dashboard charts (DBSCAN, TSP, conflict buffers, animated bar, etc.)
- 1 quality scorecard chart

---

## v0.4.0 Features

New capabilities shipped in v0.4.0 (2026-06-01):

- **6 new CLI commands** — `conflict-detect`, `report`, `dataset health`, `cache refresh`, `export`, `nl-query`
- **13 new Advanced Analytics charts** — CUSUM control charts, Bayesian confidence intervals, KMeans clustering, survival curves, Moran's I spatial autocorrelation, and more
- **10 new GIS Dashboard charts** — DBSCAN spatial clustering, TSP route optimization, conflict buffer overlays, animated borough bar chart, and more
- **Bayesian SLA forecasting** — PyMC-based breach probability with credible intervals
- **NL query interface** — Claude API (claude-haiku-4-5) translates natural-language questions to SOQL
- **DuckDB L2 cache + delta fetch** — schema-drift detection, incremental Parquet updates
- **Quality scorecard module** — 0–100 composite score across completeness, uniqueness, validity, timeliness
- **WeasyPrint PDF + Excel + PPTX reports** — exportable analyst deliverables
- **Nightly scheduler** — APScheduler-based prefetch with configurable cron

---

## 📚 Data Analytics Skills Library

**31 portable skills** for structured analytical workflows, organized across 6 categories. These activate on-demand in Claude Code sessions.

### How to use skills in Claude Code

Describe your task naturally, and Claude will activate the appropriate skill:

```
You:    "Analyze this dataset for quality issues"
Claude: [activates programmatic-eda]
        [asks for dataset + context]
You:    [provides data]
Claude: [runs structured EDA with checks]
```

### Skill Quick Reference

#### 🔍 Data Quality & Validation
- **programmatic-eda** — Exploratory data analysis with automated checks
- **data-quality-audit** — Comprehensive quality assessment
- **query-validation** — SQL review for correctness & performance
- **schema-mapper** — Understand database relationships
- **metric-reconciliation** — Investigate metric discrepancies

#### 📝 Documentation & Knowledge
- **semantic-model-builder** — Create semantic layers for metrics
- **analysis-documentation** — Document findings reproducibly
- **data-catalog-entry** — Standardized metadata for assets
- **sql-to-business-logic** — Translate SQL to business language
- **analysis-assumptions-log** — Track assumptions & decisions

#### 📊 Data Analysis & Investigation
- **cohort-analysis** — Time-based cohort tracking & retention
- **segmentation-analysis** — Customer/user segmentation
- **funnel-analysis** — Conversion funnel with drop-off analysis
- **time-series-analysis** — Trends, seasonality, forecasting
- **root-cause-investigation** — Diagnose metric changes
- **ab-test-analysis** — Experiment analysis with significance testing
- **business-metrics-calculator** — Standard business metrics

#### 🎨 Data Storytelling & Visualization
- **insight-synthesis** — Extract key findings as business insights
- **visualization-builder** — Chart selection & design guidance
- **executive-summary-generator** — Concise exec summaries
- **dashboard-specification** — Full dashboard requirements
- **data-narrative-builder** — Tell compelling data stories

#### 🤝 Stakeholder Communication
- **technical-to-business-translator** — Reframe findings for business
- **stakeholder-requirements-gathering** — Clarify stakeholder needs
- **analysis-qa-checklist** — Pre-delivery quality gate
- **methodology-explainer** — Explain approach to any audience
- **impact-quantification** — Estimate business impact

#### ⚙️ Workflow Optimization
- **analysis-planning** — Structure approach before diving in
- **context-packager** — Package context efficiently for AI
- **peer-review-template** — Structured peer review checklist
- **analysis-retrospective** — Post-analysis learning

### Common Workflows

**Exploratory analysis on new data:**
```
programmatic-eda → data-quality-audit → [choose analysis skill]
```

**Document a metric:**
```
semantic-model-builder → analysis-documentation
```

**Present findings to leadership:**
```
insight-synthesis → technical-to-business-translator → executive-summary-generator
```

**Investigate a metric change:**
```
root-cause-investigation [+ root-cause-investigation for hypothesis testing]
```

**Any analysis quality check:**
```
[analysis skill] → analysis-qa-checklist → analysis-assumptions-log
```

### Where to find skills

Location: `data-analytics-skills/`

Each skill follows this structure:
```
NN-category/skill-name/
├── SKILL.md          ← Read this first (contains the skill definition)
├── scripts/          ← Standalone Python CLI utilities
├── references/       ← Frameworks, glossaries, patterns
└── assets/           ← Output templates (Markdown, YAML, HTML)
```

See `data-analytics-skills/QUICKSTART.md` for:
- 5-minute getting started guide
- Common scenarios and workflow patterns
- Learning path and pro tips

---

## 🔧 Running the App

### Streamlit (Mission Control)
```bash
streamlit run app/app.py
```

Requires: `pip install -e ".[mission]"` (includes streamlit, plotly, folium, geospatial, forecasting, etc.)

### CLI Toolkit
```bash
socrata --help                          # Analyst command-line interface
socrata-fair --help                     # FAIR data registry bridge
python -m socrata_toolkit.core.cli      # Readiness checks, data profiling
```

### Tests
```bash
python -m pytest tests/ -q --tb=short
```

Dev dependencies: `pip install -r requirements-dev.txt`

---

## 📁 Project Structure

**Key directories:**
- `src/socrata_toolkit/` — Core library
  - `core/` — CLI, config, persistence, logging, state management
  - `analyst/` — Analyst workflows (budget, publish, workflow, etc.)
  - `analysis/` — Data analysis (cohorts, segmentation, time-series, etc.)
  - `quality/` — Data quality profiling, validation, SLA tracking
  - `lineage/` — Data lineage and impact tracking
  - `spatial/` — Geospatial analytics and queries
  - `governance/` — Audit, compliance, versioning
  - `discovery/` — Data discovery and catalog
- `app/` — Streamlit UI
  - `main.py` — Entry point with mission control router
  - `views/` — Page views (home, publish, workflows, studio, settings)
  - `ui/` — Theme, empty states, i18n
  - `utils/` — Alerts, exports, i18n
  - `services/` — Agency service layer
- `tests/` — Test suite
- `data/` — Local data files (not tracked)
- `scripts/` — Utility scripts
- `docs/` — Documentation

---

## 🧪 Code Quality

**Linting:**
```bash
ruff check src/socrata_toolkit tests app
```

**Formatting (Black):**
```bash
black src/socrata_toolkit tests app
```

**Type hints:** Optional but encouraged (mypy can be run on specific modules)

**Test coverage:** Tracked for `app/`, `src/socrata_toolkit/analyst`, `src/socrata_toolkit/core` (target: >40%)

---

## 🚀 Development

**Create feature:**
1. Branch from `main`
2. Make changes in `app/`, `src/`, or `tests/`
3. Run `ruff check` and fix any issues
4. Run `pytest tests/ -q` to verify tests pass
5. Commit with clear message
6. Push and create PR (draft OK)

**Common tasks:**
- **Add a visualization:** Create chart function in `src/socrata_toolkit/viz/` or inline in `app/main.py`, then call `st.plotly_chart()` in the appropriate view
- **Add a quality rule:** Implement in `src/socrata_toolkit/quality/rules.py`
- **Add a new view:** Create file in `app/views/`, define `render_*_page()` function, register in `app/app.py` router
- **Customize a skill:** Add `references/` folder inside skill with company-specific context (schema.md, metric_definitions.md, etc.)

---

## 📖 Documentation

- `README.md` — Project overview
- `QUICKSTART.md` — Getting started
- `data-analytics-skills/README.md` — Skill library overview
- `data-analytics-skills/QUICKSTART.md` — Skill quick start
- Inline docstrings in `src/socrata_toolkit/` modules

---

## ✅ Pre-commit Checks

When pushing, the repo runs:
- **ruff** — Python linting (E, F, W, I, UP, B)
- **pytest** — Unit and integration tests
- **import smoke test** — Verify key modules import without errors
- **Docker build** — Build Mission Control image
- **CodeQL** — Security scanning

All must pass before merging to main.

