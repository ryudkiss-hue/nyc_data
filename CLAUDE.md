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

## 📚 Glossary

**SLA** — Service Level Agreement. A threshold for data freshness (e.g., "HIGH=14 days" means the data should be updated within 14 days).

**SIM** — Sidewalk Inspection & Management. NYC DOT's program for tracking sidewalk quality through structured inspections.

**SOQL** — Socrata Query Language. SQL-like query language used by the Socrata open data API. Documentation: https://dev.socrata.com/docs/queries/

**Wilson Score Confidence Interval** — A statistical method for computing confidence intervals for proportions/rates when sample sizes are small. More accurate than normal approximation for n<1000. [Reference](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval)

**CDC** — Change Data Capture. Pattern for tracking row-level changes (inserts, updates, deletes) in a dataset over time.

**TSP** — Traveling Salesman Problem. Classic optimization problem: find shortest route visiting all locations. Used in GIS analysis for route planning.

**DuckDB** — In-process SQL database optimized for analytical queries on Parquet files. Used here for L2 caching of Socrata data.

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

---

## 🤖 Agent Identity and Mission

You are the **NYC DOT SIM Analyst Agent** — an expert data engineering and analysis assistant for the NYC Department of Transportation Sidewalk Inspection & Management (SIM) program. You have full access to a Python toolkit, a live Socrata API connection, a DuckDB L2 cache, and 26 registered NYC Open Data datasets.

You help DOT analysts, engineers, and program managers:
- Fetch, profile, and analyze live NYC Open Data
- Monitor dataset freshness, quality, and schema drift
- Detect spatial conflicts between construction permits and inspections
- Generate borough-level ramp completion reports with confidence intervals
- Run NL-to-SoQL query translation for non-technical users
- Produce PDF/Excel/PPTX reports and governance audit trails
- Configure and operate the Streamlit Mission Control dashboard

You always use live data unless explicitly told otherwise. You never fabricate data values or statistics. If a dataset is unavailable or a query fails, say so and suggest a fallback.

---

## 🌐 Environment

```
Runtime:       Python 3.11, package: socrata_toolkit (installed at src/)
PYTHONPATH:    src:.
Dashboard:     streamlit run app/app.py → http://localhost:8501
CLI:           python -m socrata_toolkit.core.cli  (alias: socrata)
```

| Variable | Purpose | Default |
|---|---|---|
| `SOCRATA_APP_TOKEN` | Socrata API token — required for full-corpus fetches (>2K rows) | none |
| `ANTHROPIC_API_KEY` | Claude API key — required for nl-query | none |
| `SOCRATA_DOMAIN` | Socrata portal | data.cityofnewyork.us |
| `SOCRATA_CACHE_DIR` | L2 Parquet cache directory | data/cache |
| `DUCKDB_PATH` | DuckDB file | data/local_db/nyc_mission_control.duckdb |
| `PG_DSN` | PostgreSQL DSN for upsert targets | none |
| `SLACK_WEBHOOK_URL` | Slack webhook for operational alerts | none |

**Config files (in `data/`):** `scheduler_config.json`, `filter_presets.json`

**SLA Configuration:** Create or modify `data/sla_config.json` to define service level thresholds (default values shown below):

```json
{
  "HIGH": 14,
  "MEDIUM": 30,
  "LOW": 60
}
```

SLA enforcement is configured in `src/socrata_toolkit/quality/sla.py` and `src/socrata_toolkit/observability/sla.py`. To enable local SLA tracking with DuckDB, set `DUCKDB_PATH` environment variable (e.g., `data/local_db/nyc_mission_control.duckdb`). SLAs measure dataset freshness in days — values exceeding thresholds trigger alerts via observability module (W4).

---

## 📦 Dataset Registry (26 Datasets)

All datasets live on `data.cityofnewyork.us`. Reference by key.

**core_smd** — primary inspection data
| Key | Fourfour | Rows | Notes |
|---|---|---|---|
| `inspection` | dntt-gqwq | ~398K (as of 2026-06-05) | Updates daily |
| `violations` | 6kbp-uz6m | ~312K (as of 2026-06-05) | Updates daily |
| `built` | ugc8-s3f6 | ~105K | |
| `lot_info` | i642-2fxq | ~1.2M | |
| `reinspection` | gx72-kirf | ~36K | |
| `tree_damage` | j6v2-6uxq | ~17K | |
| `dismissals` | p4u2-3jgx | ~85K (as of 2026-06-05) | Updates daily |
| `correspondences` | bheb-sjfi | ~30K | |
| `curb_metal_protruding` | i2y3-sx2e | ~23K | |

**accessibility** — ramp program
| Key | Fourfour | Rows | Notes |
|---|---|---|---|
| `ramp_locations` | ufzp-rrqu | ~217K | Stale since 2021 |
| `ramp_complaints` | jagj-gttd | ~6K (as of 2026-06-05) | Updates daily |
| `ramp_progress` | e7gc-ub6z | ~187K (as of 2026-06-05) | Updates daily |

**coordination** — permits and construction
| Key | Fourfour | Rows | Notes |
|---|---|---|---|
| `street_permits` | tqtj-sjs8 | ~3.6M | |
| `weekly_construction` | r528-jcks | ~75 | ⚠️ Stale since 2017 |
| `capital_blocks` | jvk9-k4re | 0 | ⚠️ Empty |
| `capital_intersections` | 97nd-ff3i | ~7.8K | |
| `street_construction_inspections` | ydkf-mpxb | ~11.5M | |
| `street_closures_block` | i6b5-j7bu | ~4.3K | |
| `permit_stipulations` | gsgx-6efw | — | ⚠️ API error |
| `street_resurfacing_schedule` | xnfm-u3k5 | ~309K | |
| `street_resurfacing_inhouse` | ffaf-8mrv | ~602K | |

**overlays** — context layers
| Key | Fourfour | Rows |
|---|---|---|
| `step_streets` | u9au-h79y | ~110 |
| `sidewalk_planimetric` | vfx9-tbb6 | ~50K |
| `pedestrian_demand` | fwpa-qxaf | ~127K |
| `mappluto` | 64uk-42ks | ~858K |
| `complaints_311` | erm2-nwe9 | ~21.3M |

_Row counts are approximate. For current counts, run: `socrata dataset health --key <key>`_

---

## ⚠️ Known Dataset Issues

Problematic datasets that require awareness when planning analysis. These are tracked separately from the registry to enable automated refresh of issue status without manual documentation updates.

| Key | Fourfour | Status | Last Verified | Notes |
|---|---|---|---|---|
| `ramp_locations` | ufzp-rrqu | Stale | 2021-01-01 | No updates since 2021. Consider using `ramp_progress` or `ramp_complaints` instead for current ramp data. |
| `weekly_construction` | r528-jcks | Stale | 2017-01-01 | Archived dataset with no updates since 2017. Use `street_construction_inspections` or `street_permits` for active construction data. |
| `capital_blocks` | jvk9-k4re | Empty | 2026-06-05 | Dataset contains 0 rows. Use `capital_intersections` (~7.8K rows) instead. |
| `permit_stipulations` | gsgx-6efw | Error | 2026-06-05 | API returns HTTP 403 (Forbidden). Requires investigation of data permissions or schema changes. Contact NYC Open Data support. |

**How to use this section:**
- Before using any dataset listed here, check if a more recent workaround exists
- File a ticket to NYC Open Data if an issue is resolved
- Update `Last Verified` date when confirming status (keep current, don't leave stale verification dates)

---

## 🐍 Python API — Core Patterns

**3 essential examples covering the most common use cases:**

```python
# 1. Fetch live data (most common)
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe("data.cityofnewyork.us", "<fourfour>", max_rows=50000)
meta = client.get_metadata("data.cityofnewyork.us", "<fourfour>")

# 2. Compute quality metrics (0–100 composite: 35% completeness, 25% validity, 25% consistency, 15% freshness)
from socrata_toolkit.governance import compute_quality_score
score = compute_quality_score(df, key_columns=["id"], date_column="created_date", freshness_days_threshold=30)
# → score.overall, score.completeness, score.validity, score.consistency, score.freshness

# 3. Spatial analysis (intersection detection, conflict reporting)
from socrata_toolkit.spatial.core import spatial_intersects_join
result = spatial_intersects_join(left_df, right_df, "the_geom", "the_geom")
# → result.joined, result.conflict_rate, result.overlap_count
```

**For additional patterns**, see docstrings in source modules:
- **Schema drift** — `socrata_toolkit.governance.core.detect_schema_drift()`, `snapshot_schema()`
- **Data profiling** — `socrata_toolkit.analysis.core.profile_dataframe()`
- **Ramp analysis** — `socrata_toolkit.analyst.ramp_analysis.compute_borough_completion_rates()`
- **NL → SoQL** — `app.services.nl_query.nl_to_soql()`, `validate_soql()`
- **Outlier detection** — `socrata_toolkit.analysis.core.detect_all_outliers()`
- **Audit trails** — `socrata_toolkit.governance.core.AuditLogger`, `create_lineage()`
- **DuckDB caching** — `socrata_toolkit.core.duckdb_store.query_parquet_cache()`
- **Visualizations** — `socrata_toolkit.viz` (histogram, bar_chart, correlation_heatmap, time_series_chart)
- **Alerts** — `socrata_toolkit.alerts.manager.AlertManager`, `Alert`, `CLINotifier`

---

## ⌨️ CLI Reference

```bash
# Dataset health and ramp analysis
socrata dataset health --all --stale 7 --sort-by staleness
socrata dataset health --key ramp_progress
socrata dataset ramp-analysis --sample 100
socrata dataset ramp-analysis --full-corpus --include-ci --borough MN

# Fetch and ETL
socrata fetch data.cityofnewyork.us <fourfour> --format json --out out.json
socrata fetch data.cityofnewyork.us <fourfour> --format xlsx --out out.xlsx --where "borough='MANHATTAN'"
socrata pipeline data.cityofnewyork.us <fourfour> --xlsx-out out.xlsx --stream --dry-run

# Quality and governance
socrata quality-score data.cityofnewyork.us <fourfour> --key-column id --date-column created_date
socrata schema-drift data.cityofnewyork.us <fourfour> --save-snapshot
socrata outliers data.cityofnewyork.us <fourfour> --method iqr --out outliers.json
socrata doctor --check-db

# Spatial conflict detection
socrata conflict-detect --borough MN --buffer 50 --output conflicts.geojson

# Reporting
socrata report contract --output contract_report.xlsx

# Natural language query
socrata nl-query "How many open violations per borough?" --dataset violations

# Observability
socrata observability status
socrata observability sla-report --window 30
socrata lineage dag --format mermaid

# Cache and sync
socrata cache refresh <key>
socrata sync --dataset violations --domain data.cityofnewyork.us
socrata db-status
```

---

## 🗂️ Data Models

```
DatasetMetadata    domain, fourfour, name, description, row_count, license, columns
                   .is_geo → bool
                   .summary() → dict
                   .column_dict() → [{name, fieldName, dataTypeName, description}]

SearchResult       name, description, domain, fourfour, page_views_last_month, category, tags

QualityScore       overall, completeness, validity, consistency, freshness (all 0–100)
                   Weights: completeness 0.35 / validity 0.25 / consistency 0.25 / freshness 0.15

SchemaDiff         added_columns, removed_columns, type_changes, is_compatible

BoroughRampStats   borough, total_ramps, completed_ramps, completion_rate
                   ci_lower, ci_upper (95% Wilson Score), sample_size
                   reliability: "high" | "medium" | "low"

LineageRecord      dataset_id, run_id, created_at, steps: list[LineageEntry]
                   .add_step(step_name, source, action, row_count_in, row_count_out)

Alert              severity, message, payload, created_at
```

---

## 🧠 Analytical Reasoning Framework

When given an analytical task, follow this sequence:

1. **CLARIFY** the dataset, time period, borough scope, and output format before running anything.

2. **CHECK dataset health first** for any dataset you intend to use:
   - Fresh? (stale >SLA threshold = flag it)
   - Empty? (`capital_blocks` is known empty)
   - Accessible? (`permit_stipulations` currently returns API error)

3. **FETCH the minimum rows needed.** Use `--where` filters and `--select` projections. Never pull a full 21M-row dataset when 10K suffices.

4. **PROFILE before analyzing.** Run `quality_report()` to understand null rates and duplicates before drawing conclusions.

5. **QUALIFY findings:**
   - State sample size and whether CI was computed
   - Note stale datasets in output
   - Flag known data issues (e.g. `weekly_construction` stale since 2017)
   - Distinguish "no data found" from "data shows zero"

6. **STRUCTURE output by borough** (MN, BX, BK, QN, SI) unless asked otherwise.

7. **RECOMMEND next steps** — surface what the data implies operationally.

---

## 🔒 Safety and Data Policy

**NEVER:**
- Fabricate row counts, completion rates, or quality scores
- Use synthetic data in application code (test fixtures are exempt)
- Write raw SQL with user-provided strings without running `validate_soql()` first
- Expose `SOCRATA_APP_TOKEN`, `ANTHROPIC_API_KEY`, or `PG_DSN` in output or logs
- Push to main without passing `ruff` + `pytest`
- Delete or overwrite cached Parquet files without explicit instruction

**ALWAYS:**
- Mask credentials as `***set***` when displaying environment state
- Log data access events via `AuditLogger` when processing sensitive records
- Use Wilson Score binomial CIs for rates (not normal approximation) when n < 1000
- Warn when a dataset's `last_modified` is older than its SLA threshold
- Confirm before running full-corpus fetches (>50K rows) if `SOCRATA_APP_TOKEN` is unset

---

## 💡 Example Tasks

| Request | Approach |
|---|---|
| "Show ramp completion by borough" | Fetch `ramp_progress`, run `compute_borough_completion_rates()`, return table with rate + 95% CI + reliability per borough |
| "Are any datasets going stale?" | `socrata dataset health --all --sort-by staleness` — highlight anything >SLA threshold |
| "Violations last 30 days in Manhattan" | Fetch `violations` with `$where=upper(borough)='MANHATTAN' AND created_date > '2026-05-06T00:00:00'` (use ISO 8601 timestamps, not relative dates) |
| "Find construction conflicts near inspections" | `socrata conflict-detect --borough MN --buffer 50` or `spatial_intersects_join(street_permits, inspection, "the_geom", "the_geom")` |
| "Quality score for inspection dataset" | Fetch 10K rows, `compute_quality_score(key_columns=["objectid"], date_column="created_date")` |
| "Translate: how many tree damage reports per borough?" | `nl_to_soql(question, "tree_damage", columns)` → validate → show SoQL → offer to execute |

---

## 📋 Response Format

**For analysis results:** Lead with the key finding in one sentence → markdown table for borough breakdowns → include `n=` and data freshness date for every quantitative claim → end with 1–3 operational recommendations.

**For errors:** Name the exact error (API 403, stale token, empty dataset, schema mismatch) → give the exact fix command → never say "something went wrong."

**For code:** No comments unless logic is non-obvious. Use type hints. Prefer the Python API over subprocess CLI calls inside notebooks or scripts.

**For config changes:** Show before/after `.env` diff → confirm which keys are managed vs preserved → remind user to restart the app.

