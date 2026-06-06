# System Architecture

## High-Level Design

```
DATA LAYER
  NYC Socrata (26 open datasets)
    ↓ sodapy, requests
  SocrataClient (core/client.py)
    ↓ JSON/GeoJSON/XLSX
  DuckDB L2 Cache (Parquet in data/local_db/)
    ↓ delta refresh, schema drift detection

PROCESSING LAYER (Elite Analyst Framework)
  ┌──────────────────────────────────────────┐
  │ 1. Core                                  │
  │    API client, DuckDB, Hardened Auth     │
  │                                          │
  │ 2. Analysis (Mandate Aligned)            │
  │    Four Moments, Bayesian MCMC, Inference│
  │                                          │
  │ 3. Analyst                               │
  │    Workflows, Docusaurus-Ready Reports   │
  │                                          │
  │ 4. Quality                               │
  │    Normality Audits, Evidence Tracking   │
  │                                          │
  │ 5. Visualization                         │
  │    Accessible Plotly/Folium (WCAG 2.1)   │
  │                                          │
  │ 6. Governance                            │
  │    Equity Weighting, Pipeline Reconcile  │
  │                                          │
  │ 7. Engineering (CMU & NYSDOT Standard)   │
  │    Markov Chains, LCCA, Vision Zero Audit│
  └──────────────────────────────────────────┘

INTERFACE LAYER
  ↓ CLI (socrata, 60+ commands)
  ↓ Streamlit UI (Manhattan Mission Control)
  ↓ Python API (import socrata_toolkit.*)
  ↓ REST API (FastAPI)

USER
  Analysts, Managers, Civil Engineers
```

## Pillar Details

### 1. Core (API, Auth, Persistence)
**Files**: `src/socrata_toolkit/core/`

- **SocrataClient** (`client.py`): Wrapper around Socrata SODA API
  - `fetch_dataframe()`: Download JSON/GeoJSON/XLSX
  - Hardened SQL injection protection using `psycopg.sql`.

### 2. Analysis (Elite Scientific Mandate)
**Files**: `src/socrata_toolkit/analysis/`

- **Scientific Profiling** (`profiling.py`): Characterization of the **Four Moments** (Expected Value, Variance, Skewness, Kurtosis).
- **Inference Engine** (`inference.py`): Formal hypothesis testing (t-tests, Chi-square) and normality audits.
- **Bayesian MCMC** (`bayesian.py`): Stochastic inference using NUTS sampling and Gelman-Rubin convergence diagnostics ($\hat{R}$ < 1.05).
- **Insights Engine** (`insights.py`): Automated synthesis of anomalies, drift, and engineering triggers.

### 7. Engineering (Infrastructure & Street Design)
**Files**: `src/socrata_toolkit/engineering/`

- **Infrastructure Management** (`infrastructure.py`): 
  - **Markov Chains**: Stochastic deterioration forecasting.
  - **LCCA/NPV**: Life-Cycle Cost Analysis with Monte Carlo risk simulation.
- **Pavement Engineering** (`pavement.py`): NYSDOT ESAL models, Surface Rating triggers, and FHWA IRI user-cost penalties.
- **Street Design Audit** (`standards_v4.py`): Automated Vision Zero geometric compliance for NYC SDM 4th Edition (2024).

### 6. Governance (Ethics & Integrity)
**Files**: `src/socrata_toolkit/governance/`

- **Equity Scorer** (`equity.py`): 2.0x socio-economic multiplier for historically underinvested neighborhoods.
- **Pipeline Reconciliation** (`pipeline/streaming.py`): 100% data integrity validation against remote metadata.

### 3. Analyst (Workflows, Publishing)
**Files**: `src/socrata_toolkit/analyst/`

- **AnalystWorkflow** (`workflow.py`): Orchestrator
  - DAG-based workflow execution
  - Steps: fetch, transform, validate, export
  - Telemetry logging

- **Publish** (`publish.py`): Report generation
  - Excel with formatting (openpyxl)
  - PowerPoint (python-pptx)
  - PDF (weasyprint)

- **RampAnalysis** (`ramp_analysis.py`): ADA ramp analytics
  - Completion rates by borough
  - Wilson Score confidence intervals

- **RoleProfiles** (`roles.py`): Role-based access
  - Analyst, Manager, Engineer roles
  - Custom dashboards per role

### 4. Quality (SLA, Freshness, Validation)
**Files**: `src/socrata_toolkit/quality/`

- **SLA Tracking** (`sla.py`, `sla_tracking.py`)
  - Thresholds: HIGH=14d, MEDIUM=30d, LOW=60d
  - Alerts when datasets exceed threshold
  - Severity levels

- **Data Validation** (`validation.py`, `rules.py`)
  - Pre-defined rules (no_nulls, unique_ids, etc.)
  - Custom rule framework
  - Batch validation

### 5. Visualization (30+ Charts)
**Files**: `src/socrata_toolkit/viz/`

- **Plotly**: Interactive charting
  - Borough bar charts, KPI gauges, Gantt charts
  - Hypothesis testing, waterfall, heatmap
  - Inspector performance box plots

- **Folium**: Map rendering
  - Geospatial points, polygons, heatmaps

- **Pydeck**: GPU-accelerated visualization
  - Large-scale point clouds
  - Cluster analysis

### 6. Governance (Lineage, Audit, Compliance)
**Files**: `src/socrata_toolkit/governance/`

- **Lineage Tracking** (`core.py`)
  - Record each step: fetch, transform, export
  - Row counts in/out per step
  - Metadata storage

- **Audit Logging** (`audit.py`)
  - Who accessed what, when
  - Data governance

- **Schema Drift Detection**
  - Compare current vs baseline schema
  - Alert on column additions/removals/type changes

### 7. Engineering (Domain Logic)
**Files**: `src/socrata_toolkit/engineering/`

- **Contract Analytics** (`contract_analytics.py`)
  - Contractor performance
  - Delivery timelines

- **Budget Forecast** (`budget_forecast.py`)
  - Cost estimation
  - Variance analysis

- **Construction List** (`construction_list.py`)
  - Scope-of-work prioritization

## Data Flow

### Fetch Flow
```
User: socrata fetch <fourfour> --limit 100
  ↓
SocrataClient.fetch_dataframe()
  ↓ If data in DuckDB cache && fresh:
  DuckDB L2 Cache → Return Parquet
  ↓ Else:
  Socrata SODA API → Paginate (50K chunks)
  ↓
DuckDB Store.upsert() → Save to Parquet
  ↓
Return DataFrame
```

### Quality Score Flow
```
DataFrame
  ↓
profile_dataframe() → null_pct, type_infer, cardinality
  ↓
compute_quality_score() [CONSTANT WEIGHTS]
  ↓ Completeness: 1 - null_pct
  ↓ Validity: constraint violations
  ↓ Consistency: (1 - dup_rate)
  ↓ Freshness: (1 - age/SLA_threshold) * 100
  ↓
overall = C*0.35 + V*0.25 + Co*0.25 + F*0.15
  ↓
QualityScore(overall=85.3, completeness=90, validity=80, ...)
```

### Analyst Workflow Flow
```
User: Execute AnalystWorkflow
  ↓
Step 1: fetch(dataset="inspection")
  → SocrataClient.fetch_dataframe() → DataFrame
  ↓
Step 2: profile()
  → profile_dataframe() → DataProfile
  ↓
Step 3: validate()
  → Run quality rules → ValidationReport
  ↓
Step 4: export(format="xlsx")
  → openpyxl → output.xlsx
  ↓
Telemetry: Log row counts, timing, errors
```

## Configuration Files

**config/datasets.yaml**
```yaml
dataset_registry:
  inspection:
    fourfour: dntt-gqwq
    domain: data.cityofnewyork.us
    rows: ~398K
    freshness_sla: 14  # HIGH
    
workflow_datasets:
  qa: [lot_info, mappluto, ...]
  spatial: [permits, capital_blocks, ...]
  contract: [violations, tree_damage, ...]
```

**data/sla_config.json** (Single Source of Truth)
```json
{
  "sla_thresholds": {
    "HIGH": {"days": 14},
    "MEDIUM": {"days": 30},
    "LOW": {"days": 60}
  }
}
```

Values verified by `tests/test_sla_config.py`.

**src/socrata_toolkit/governance/core.py** (Weight Constants)
```python
QUALITY_WEIGHT_COMPLETENESS = 0.35
QUALITY_WEIGHT_VALIDITY = 0.25
QUALITY_WEIGHT_CONSISTENCY = 0.25
QUALITY_WEIGHT_FRESHNESS = 0.15

assert sum == 1.0  # Module-level assertion
```

Values verified by `tests/test_governance_weights.py`.

## Key Decisions

### DuckDB for Caching
- Faster than refetching Socrata API
- Column-oriented (analytics-friendly)
- Schema drift detection built-in
- Parquet format (portable, efficient)

### 7 Pillars
- Semi-independent: can import selectively
- Avoid tight coupling
- Allows testing in isolation
- Easy to extend

### Weight Constants
- Prevents hardcoded magic numbers
- Single source of truth in code
- Tests verify weights don't drift from docs
- CI blocks inconsistent PRs

### Role-Based Dashboards
- Different views for Analysts/Managers/Engineers
- Reduces cognitive load
- Focuses on relevant metrics per role

## Deployment Architecture

```
GitHub (main branch)
  ↓ on push
GitHub Actions CI
  ├─ Lint (ruff)
  ├─ Test (pytest, 45% gate)
  ├─ Build Docker image
  ├─ Security scan (CodeQL)
  └─ Push to registry (ECR, Docker Hub)
    ↓
Docker Registry
  ↓ on deploy
Kubernetes / ECS / Heroku
  ├─ Mission Control (Streamlit)
  ├─ Scheduler (APScheduler)
  └─ API (optional FastAPI)
    ↓
Monitoring
  ├─ SLA alerts (when datasets >threshold)
  ├─ Error alerts (Slack webhook)
  └─ Metrics (Prometheus)
```

## Extension Points

### Add a New Visualization
1. Implement in `src/socrata_toolkit/viz/plotly.py`
2. Test in `tests/test_plotly_charts.py`
3. Import in `app/views/analytics_advanced.py`
4. Call `st.plotly_chart(func(df))`

### Add a New Workflow
1. Extend `AnalystWorkflow` in `src/socrata_toolkit/analyst/workflow.py`
2. Define steps and transformations
3. Add telemetry logging
4. Register in CLI

### Add a New Quality Rule
1. Implement in `src/socrata_toolkit/quality/rules.py`
2. Test in `tests/test_quality.py`
3. Register in `DataValidation` framework
4. Use in `quality_report()`

### Add a New CLI Command
1. Implement in `src/socrata_toolkit/core/cli.py` with @click.command()
2. Test in `tests/test_cli_coverage.py`
3. Document in CONTRIBUTING.md
4. Re-run `socrata --help` to verify

---

**See `docs/DEVELOPMENT.md` for coding conventions and patterns.**
