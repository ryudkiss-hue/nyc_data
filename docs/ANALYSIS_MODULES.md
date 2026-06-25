# Data Analysis Components Reference

Complete catalog of the 65 analysis modules, 16 quality modules, and 17 visualization modules in the NYC DOT toolkit.

## Overview

The toolkit provides a comprehensive analytical foundation with three main component groups:

1. **Analysis Modules (65)** — Statistical inference, forecasting, domain-specific workflows
2. **Quality Modules (16)** — Data profiling, validation, SLA tracking, freshness monitoring
3. **Visualization Modules (17)** — Plotly charts, GIS mapping, statistical visualizations

---

## Analysis Modules (65 total)

Located in: `src/socrata_toolkit/analysis/`

### Core Analysis

| Module | Purpose | Key Functions |
|--------|---------|---|
| `core.py` | Foundation: data profiling, insights, quality reports | `profile_dataframe()`, `quality_report()`, `generate_text_insights()` |
| `advanced.py` | Advanced algorithms (clustering, dimensionality reduction) | `advanced_clustering()`, `pca_analysis()` |
| `ensemble.py` | Multi-model ensemble methods | `ensemble_predict()`, `combine_predictions()` |
| `inference.py` | Statistical hypothesis testing, significance | `t_test()`, `chi_square()`, `anova()` |
| `insights.py` | Insight extraction and reporting | `extract_insights()`, `anomaly_insights()` |
| `program.py` | Program-level analysis (aggregate metrics) | `program_dashboard()`, `program_metrics()` |
| `incremental.py` | Streaming/incremental data processing | `incremental_fit()`, `update_model()` |

### Domain-Specific: Complaint & Appeal Workflows

| Module | Purpose | Use Case |
|--------|---------|----------|
| `complaint_response_classifier.py` | Classify complaint resolution types | High/medium/low priority, escalation needed |
| `complaint_response_workflow.py` | End-to-end complaint processing | Track from intake → resolution |
| `complaint_response_example.py` | Example usage and patterns | Reference implementation |
| `appeal_classifier.py` | Classify appeal outcomes | Approved, denied, pending |
| `appeal_tracking_workflow.py` | Appeal lifecycle management | Track appeals through decision cycle |
| `appeal_tracking_example.py` | Appeal workflow examples | Concrete examples |

### Domain-Specific: Dismissal Analysis

| Module | Purpose | Use Case |
|--------|---------|----------|
| `dismissal_classifier.py` | Classify dismissal reasons | Administrative, legal, procedural |
| `dismissal_analysis_workflow.py` | Dismissal tracking and trends | Monitor dismissal patterns |
| `dismissal_analysis_example.py` | Dismissal workflow examples | Reference patterns |

### Domain-Specific: Legal Hold

| Module | Purpose | Use Case |
|--------|---------|----------|
| `legal_hold_classifier.py` | Flag records for legal holds | Litigation, audit, compliance |
| `legal_hold_workflow.py` | Legal hold lifecycle | Track holds through closure |
| `legal_hold_example.py` | Legal hold usage patterns | Real-world examples |

### Domain-Specific: Hotspot Analysis

| Module | Purpose | Use Case |
|--------|---------|----------|
| `hotspot_classifier.py` | Identify high-incident areas | Problem clusters, resource allocation |
| `hotspot_workflow.py` | Spatial hotspot tracking | Monitor problem zone evolution |

### Domain-Specific: Velocity & Performance

| Module | Purpose | Use Case |
|--------|---------|----------|
| `velocity_classifier.py` | Classify work completion speed | Fast, normal, slow tracks |
| `velocity_analysis_workflow.py` | Track repair velocity trends | Measure crew/contractor performance |
| `velocity_demo.py` | Velocity analysis examples | Concrete patterns |

### Domain-Specific: Correspondence & Communication

| Module | Purpose | Use Case |
|--------|---------|----------|
| `correspondence_classifier.py` | Classify communication type | Email, letter, phone, in-person |
| `correspondence_audit_workflow.py` | Track communication compliance | Ensure timely responses |

### Domain-Specific: Material & Condition

| Module | Purpose | Use Case |
|--------|---------|----------|
| `material_analysis.py` | Analyze repair materials used | Cost tracking, waste analysis |

### Domain-Specific: Sentiment & NLP

| Module | Purpose | Use Case |
|--------|---------|----------|
| `sentiment_classifier.py` | Classify complaint sentiment | Positive, neutral, negative |
| `sentiment_workflow.py` | Track sentiment trends | Monitor satisfaction |
| `nlp_analysis.py` | Text mining and extraction | Key phrase extraction, topic modeling |
| `nlp_classifier.py` | Text classification | Category assignment, intent detection |
| `nlp_examples.py` | NLP usage examples | Reference patterns |

### Statistical & Forecasting

| Module | Purpose | Key Functions |
|--------|---------|---|
| `bayesian.py` | Bayesian inference (PyMC) | `bayesian_ci()`, `credible_interval()`, `posterior_plot()` |
| `ab_testing.py` | A/B test analysis with significance | `ab_test_result()`, `sample_size_calc()` |
| `changepoint.py` | Change point detection (PELT algorithm) | `detect_changepoints()`, `segment_series()` |
| `clustering_diagnostics.py` | Validate clustering results | `silhouette_score()`, `davies_bouldin_index()` |
| `confidence_intervals.py` | Compute CIs (Wilson Score, Agresti-Coull) | `wilson_ci()`, `agresti_coull_ci()` |
| `forecast_classifier.py` | Classify forecast types | Trend, seasonal, cyclical |
| `forecast_validation.py` | Validate forecast accuracy | MAPE, RMSE, tracking signal |
| `forecasting_workflow.py` | Prophet-based time-series forecasting | `forecast_inspections()`, `sla_breach_forecast()` |
| `semantic_search.py` | Semantic similarity search (embeddings) | `similarity_search()`, `find_similar_records()` |
| `text.py` | Text processing utilities | Tokenize, clean, vectorize |
| `metrics.py` | Standard metric calculations | `pass_rate()`, `completion_rate()`, `sla_metric()` |
| `profiling.py` | Advanced data profiling | Distribution analysis, cardinality |

### Specialized Dataset Workflows

| Module | Purpose | Use Case |
|--------|---------|----------|
| `dataset_health.py` | Comprehensive health assessment | Readiness scores, completeness, freshness |
| `dataset_health_workflow.py` | Automated health tracking | Daily/weekly health reports |
| `dataset_health_cli_snippet.py` | CLI integration | `socrata dataset health` command |
| `sla_compliance_workflow.py` | SLA compliance tracking | Monitor freshness vs. thresholds |
| `sla_status.py` | SLA status calculation | Breach detection, alerting |
| `ramp_progress_test.py` | ADA ramp completion testing | Validate data quality |
| `ramp_progress_workflow.py` | Ramp completion tracking | Borough-level progress monitoring |
| `ramp_status.py` | Current ramp status calculations | Completion rates, CI bounds |

### Advanced Workflows

| Module | Purpose | Use Case |
|--------|---------|----------|
| `allocation_classifier.py` | Classify resource allocation | Fair/unfair, equitable distribution |
| `resource_allocation_workflow.py` | Track allocation patterns | Equity audits, distribution monitoring |
| `triage_cli.py` | CLI for case triage | Route cases to correct teams |
| `triage_example_complete.py` | Full triage workflow | Reference implementation |
| `langgraph_triage.py` | LLM-based triage (LangGraph) | Claude-powered case routing |
| `sim_pipeline_validation.py` | Validate SIM data pipeline | Data quality gates |
| `sim_workflows_complete.py` | Complete SIM analysis workflows | End-to-end SIM analysis |

### Infrastructure & Utilities

| Module | Purpose | Key Functions |
|--------|---------|---|
| `assumptions_logger.py` | Track analytical assumptions | `log_assumption()`, `review_assumptions()` |
| `qa_checklist.py` | Pre-delivery QA framework | `quality_gate()`, `validation_checklist()` |
| `reporting.py` | Report generation (PDF, Excel) | `generate_report()`, `export_findings()` |
| `reproducibility.py` | Reproducibility utilities | `log_random_seed()`, `record_versions()` |
| `verify_real_data.py` | Data verification utilities | `validate_schema()`, `check_completeness()` |
| `viz.py` | Visualization helper functions | Integration with viz modules |
| `_monolith.py` | Legacy monolith (DO NOT USE) | Kept for backward compatibility only |

---

## Quality Modules (16 total)

Located in: `src/socrata_toolkit/quality/`

### Core Quality Framework

| Module | Purpose | Key Classes |
|--------|---------|---|
| `profiler.py` | Data profiling engine | `DataProfiler`, `ColumnProfile`, `TableProfile`, `DriftReport` |
| `rules.py` | Data quality rules engine | `Rule`, `RuleSet`, `execute_rules()` |
| `validation.py` | Validation framework | `Validator`, `ValidationResult`, `validate()` |
| `validator.py` | Generic data validator | `DataValidator`, `schema_validator()` |

### Quality Dimensions

| Module | Purpose | Metrics |
|--------|---------|---------|
| `freshness.py` | Data freshness tracking | Days since last update, SLA status |
| `sla.py` | SLA compliance engine | Threshold comparison, breach detection |
| `sla_tracking.py` | SLA history tracking | Trend analysis, compliance reports |
| `anomalies.py` | Anomaly detection | Z-score, IQR, Isolation Forest |
| `expectations.py` | Great Expectations integration | Data quality expectations, checkpoints |

### Domain-Specific Quality

| Module | Purpose | Use Case |
|--------|---------|----------|
| `domain_rules.py` | Domain-specific validation rules | Business logic validation |
| `reconciliation.py` | Data reconciliation | Compare sources, detect discrepancies |
| `duckdb_validation.py` | DuckDB-native validation | Fast SQL-based quality checks |

### Quality Outputs

| Module | Purpose | Output |
|--------|---------|--------|
| `catalog.py` | Data catalog management | Dataset registry, metadata tracking |
| `integration.py` | Quality integration testing | End-to-end quality validation |
| `reports.py` | Quality report generation | Scorecard reports, dashboards |

---

## Visualization Modules (17 total)

Located in: `src/socrata_toolkit/viz/`

### Core Visualization

| Module | Purpose | Key Classes/Functions |
|--------|---------|---|
| `core.py` | Base chart generation | `ChartResult`, `histogram()`, `bar_chart()`, `correlation_heatmap()`, `time_series_chart()` |
| `plotly.py` | Plotly-specific charts | Interactive Plotly figures, customization |

### Statistical Visualizations

| Module | Purpose | Charts |
|--------|---------|--------|
| `statistical_viz.py` | Advanced statistical charts | CUSUM control charts, Bayesian credible intervals, KMeans clusters, survival curves |
| `clustering_viz.py` | Clustering visualization | Scatter plots, dendrograms, cluster profiles |

### Geographic Visualizations

| Module | Purpose | Maps |
|--------|---------|------|
| `map.py` | Geographic mapping | Scattermapbox, choropleths, spatial overlays |
| `temporal_maps.py` | Time-based map visualization | Animated maps, time-series spatial data |

### Interactive Dashboards

| Module | Purpose | Components |
|--------|---------|---|
| `dashboard.py` | Dashboard building | Layout templates, reactive components |
| `d3_components.py` | D3.js integration | Force networks, Sankey diagrams, tree maps |

### Specialized Visualizations

| Module | Purpose | Use Case |
|--------|---------|----------|
| `advanced_multidim.py` | Multi-dimensional visualization | Bubble charts, parallel coordinates, radar charts, scatter plot matrices |
| `chart_finder.py` | Auto chart recommendation | Suggest chart type based on data |
| `charts_extra.py` | Additional chart types | Specialized charts |
| `sankey_research_questions.py` | Sankey diagrams | Flow visualization |
| `material_viz.py` | Material Design visualizations | Material design theming |
| `accessibility.py` | Accessibility features | Color blindness support, alt text |
| `branding.py` | Theming & branding | NYC DOT branding, color schemes |
| `units.py` | Unit conversion & display | Format numbers with units |

---

## Test Coverage

### Analysis Tests

| Test File | Focus | Tests |
|-----------|-------|-------|
| `test_analysis.py` | Core analysis functionality | Core module coverage |
| `test_analysis_advanced.py` | Advanced algorithms | Clustering, ensemble, inference |
| `test_analysis_charts.py` | Analysis chart generation | Plotly integration |
| `test_analysis_visualization.py` | Visualization building | Figure generation |

### Quality Tests

| Test File | Focus | Tests |
|-----------|-------|-------|
| `test_quality.py` | Quality framework | Rules, validation, profiling |
| `test_quality_profiler_coverage.py` | Data profiling | ColumnProfile, TableProfile, DriftReport |
| `test_quality_rules_coverage.py` | Quality rules | Rule execution, scoring |
| `test_quality_validation_coverage.py` | Validation framework | Schema, domain rules |
| `test_quality_catalog_coverage.py` | Data catalog | Metadata tracking |
| `test_quality_freshness_coverage.py` | Data freshness | SLA tracking, timeliness |
| `test_quality_integration_coverage.py` | Integration testing | End-to-end workflows |
| `test_quality_reports_coverage.py` | Report generation | Quality scorecards |

**Total Test Count:** 4100+ tests  
**Coverage Target:** >40% for analyst + core modules

---

## Module Dependency Map

```
analysis/
├── core (core algorithms, profiling)
├── advanced (builds on core)
├── inference (statistics, uses core)
├── bayesian (PyMC-based, statistical)
├── ensemble (combines models)
├── forecasting (time-series, uses inference)
├── [domain modules] (complaint, dismissal, ramp, etc.)
└── [utility modules] (QA, assumptions, reproducibility)

quality/
├── profiler (core data profiling)
├── rules (quality rules engine)
├── validation (validator base class)
├── sla (uses freshness module)
├── freshness (time-based quality)
├── anomalies (outlier detection)
└── [domain modules] (business logic rules)

viz/
├── core (base Plotly charts)
├── plotly (Plotly customization)
├── statistical_viz (statistical charts)
├── map (geographic mapping)
├── dashboard (composition)
└── [specialty modules] (d3, advanced, accessibility)
```

---

## Usage Patterns

### Import Analysis Modules

```python
from socrata_toolkit.analysis import bayesian, metrics, forecasting
from socrata_toolkit.analysis.complaint_response_workflow import ComplaintWorkflow

# Bayesian analysis
ci = bayesian.bayesian_ci(data, prior="default")

# Metrics calculation
rate = metrics.pass_rate(data, key_column="id")

# Forecasting
forecast = forecasting.forecast_inspections(historical_data)

# Workflow
workflow = ComplaintWorkflow(config)
result = workflow.process(complaints_df)
```

### Import Quality Modules

```python
from socrata_toolkit.quality import profiler, sla, anomalies

# Profile data
prof = profiler.DataProfiler()
profile = prof.profile_dataframe(df)

# Check SLA
sla_status = sla.check_sla(df, dataset_key="inspection", freshness_threshold=30)

# Detect anomalies
outliers = anomalies.detect_outliers(df, method="isolation_forest")
```

### Import Visualization Modules

```python
from socrata_toolkit.viz import core, statistical_viz, map as gis_map

# Create chart
fig = core.bar_chart(df, x="borough", y="count", title="Inspections by Borough")

# Statistical visualization
fig = statistical_viz.cusum_control_chart(df, target=50, threshold=3)

# Map visualization
fig = gis_map.scattermapbox(df, lat="latitude", lon="longitude", size="priority")
```

---

## Related Documentation

- [`CLI_REFERENCE.md`](CLI_REFERENCE.md) — Command-line interface for analysis
- [`MISSION_CONTROL.md`](MISSION_CONTROL.md) — Dash dashboard (visual interface)
- [`CI.md`](CI.md) — Tests and CI/CD for analysis modules
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — Production deployment

---

## Performance Notes

**Profiling**: O(n) for n-row tables; typical ~100ms for 100K rows  
**Bayesian**: O(n*m) where m=MCMC iterations; ~5-10s for 10K rows  
**Forecasting**: O(n log n); ~2-3s for 5-year time series  
**Anomaly Detection**: O(n log n) for Isolation Forest; <1s for 100K rows  
**Quality Scoring**: O(n); typical <500ms

---

## Versioning

**Current version:** 0.5.0  
**Python compatibility:** 3.9–3.12  
**Key dependencies:**
- pandas 2.0+
- pymc 5.0+ (Bayesian)
- prophet 1.1+ (forecasting)
- plotly 5.0+ (visualization)
- duckdb 0.9.0+ (local caching)

See `pyproject.toml` for complete dependency list.
