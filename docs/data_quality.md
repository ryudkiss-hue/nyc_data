# Data Quality Framework - Comprehensive Guide

## Overview

The Data Quality Framework provides systematic validation, monitoring, and enforcement of data quality standards across the NYC DOT data ecosystem. Built on Great Expectations, it integrates seamlessly with existing pipelines, schema registry, material standards, observability, and audit systems.

## Key Components

### 1. Quality Expectations (`quality_expectations.py`)

Declarative specifications of data quality requirements using Great Expectations patterns.

**Features:**
- Column existence, data type, and nullability checks
- Value range and pattern validation
- Custom domain-specific rules
- Expectation suite management and versioning
- Pre-built suites for key datasets

**Example Usage:**
```python
from socrata_toolkit.quality_expectations import ExpectationSuite, create_sidewalk_inspections_suite

# Use pre-built suite
suite = create_sidewalk_inspections_suite()

# Or create custom suite
suite = ExpectationSuite("my_dataset")
suite.add_column_exists("id")
suite.add_column_not_null("name", mostly=0.99)
suite.add_column_values_in_set("status", {"ACTIVE", "INACTIVE"})
```

### 2. Data Quality Profiler (`quality_profiler.py`)

Statistical analysis and profiling of datasets to understand distributions, detect drift, and suggest expectations.

**Features:**
- Column-level and table-level statistics
- Null percentage, cardinality, outlier detection
- Drift detection between profile snapshots
- Schema change identification
- Automatic expectation suggestions

**Example Usage:**
```python
from socrata_toolkit.quality_profiler import ProfileGenerator

profiler = ProfileGenerator()
profile = profiler.profile_dataset(df, "sidewalk_inspections")

# Detect drift
drift = profiler.compare_profiles(profile_old, profile_new)
print(f"Changes detected: {len(drift.changes)}")

# Suggest expectations
suggestions = profiler.suggest_expectations(profile)
```

### 3. Quality SLA Framework (`quality_sla.py`)

Defines, tracks, and enforces Service Level Agreements for data quality metrics.

**Metrics:**
- Completeness: % non-null values
- Validity: % matching domain rules
- Uniqueness: % unique values
- Consistency: Cross-dataset integrity
- Timeliness: Data freshness (< 24 hours old)
- Accuracy: Spot checks and reference data comparison

**SLA Configuration:**
```python
from socrata_toolkit.quality_sla import SLADefinition, MetricType, Severity, DataQualityTracker

# Define SLA
sla = SLADefinition(
    metric_name="sidewalk_completeness",
    metric_type=MetricType.COMPLETENESS,
    target=0.98,  # 98% non-null
    window="daily",
    dataset="sidewalk_inspections",
    severity=Severity.HIGH,
    owner="data-team@example.com",
)

# Track metrics
tracker = DataQualityTracker()
tracker.register_sla(sla)
tracker.record_metric("sidewalk_completeness", 0.99, "sidewalk_inspections", MetricType.COMPLETENESS)

# Evaluate compliance
compliant, actual = tracker.evaluate_sla("sidewalk_completeness")
```

### 4. Validation Engine (`quality_validator.py`)

Validates data against expectations and aggregates results.

**Validation Stages:**
- Pre-ingestion: Validate Socrata data
- Post-ingestion: Before persistence
- Post-transformation: Before serving
- Pre-API: Before consumer access

**Streaming Support:**
```python
from socrata_toolkit.quality_validator import QualityValidator

validator = QualityValidator(fail_fast=True)

# Batch validation
result = validator.validate(df, suite, "dataset_name")
print(f"Pass rate: {result.pass_rate:.1%}")

# Streaming validation (per-record)
if validator.validate_record(record, suite):
    process_record(record)
```

### 5. Anomaly Detection (`quality_anomalies.py`)

Statistical detection of anomalies in quality metrics and data.

**Methods:**
- Z-score based outlier detection
- Moving average drift detection
- Seasonality violation detection
- Schema change detection
- Multi-metric correlation

**Example:**
```python
from socrata_toolkit.quality_anomalies import AnomalyDetector

detector = AnomalyDetector(z_score_threshold=3.0)

# Detect outliers
report = detector.detect_outliers("completeness_metric", history)

# Detect drift
drift_report = detector.detect_drift("validity_metric", history)

# Multi-metric analysis
report = detector.detect_multi_metric_anomaly({
    "completeness": history1,
    "validity": history2,
})
```

### 6. Business Rules Engine (`quality_rules.py`)

Domain-specific validation rules for NYC DOT data.

**Sidewalk Inspection Rules:**
- Valid material types (asphalt, concrete, permeable, etc.)
- Valid condition ratings (EXCELLENT, GOOD, FAIR, POOR, CRITICAL)
- Geographic bounds (NYC boroughs)
- Inspection recency (< 1 year old)
- No duplicate inspections same day/location

**Example:**
```python
from socrata_toolkit.quality_rules import create_sidewalk_rules

engine = create_sidewalk_rules()
violations = engine.apply_rules(df)

if not violations.can_proceed:
    print(f"Critical violations: {violations.critical_violations}")
    for v in violations.violations:
        print(f"  {v.rule_name}: {v.violation_count} violations")
```

### 7. Quality Reporting (`quality_reports.py`)

Comprehensive quality reporting in multiple formats.

**Report Types:**
- Daily quality report (all datasets, trends, compliance)
- Dataset-specific report (all metrics, tests, anomalies)
- SLA compliance report (by metric, by dataset, compliance %)
- Anomaly report (detected issues, severity, actions)

**Export Formats:**
- JSON (for programmatic access)
- HTML (for human review)
- CSV (for data analysis)

**Example:**
```python
from socrata_toolkit.quality_reports import QualityReportGenerator

gen = QualityReportGenerator(output_dir="./reports")

daily = gen.generate_daily_report(datasets, sla_results, anomalies)
gen.export_to_json(daily, "daily_report.json")
gen.export_to_html(daily, "daily_report.html")
```

### 8. Data Catalog Integration (`quality_catalog.py`)

Integrates quality metrics into data catalogs for discoverability.

**Quality Score Components:**
- Overall score (0-100)
- Completeness score
- Validity score
- Consistency score
- Timeliness score
- Accuracy score

**Usage:**
```python
from socrata_toolkit.quality_catalog import DataQualityCatalog, DatasetQualityScore

catalog = DataQualityCatalog()
catalog.register_dataset("sidewalk_inspections", "Sidewalk Inspections")

score = DatasetQualityScore(
    overall=92.5,
    completeness=98.0,
    validity=95.0,
    consistency=85.0,
    timeliness=100.0,
    accuracy=80.0,
)
catalog.update_quality_score("sidewalk_inspections", score)

# List by quality
high_quality = catalog.list_by_quality(min_score=90.0)
```

### 9. Pipeline Integration (`quality_integration.py`)

Hooks for integrating validation into data pipelines.

**Decorators:**
```python
from socrata_toolkit.quality_integration import validate_data, check_sla, apply_business_rules

@validate_data(suite=expectation_suite, fail_on_error=True)
def process_data(df):
    return df.transform()

@check_sla(metric_name='completeness', tracker=tracker)
def load_data():
    return pd.read_csv("data.csv")

@apply_business_rules(rules_engine=engine)
def transform_data(df):
    return df.filter()
```

## Quality SLA Definitions

### Completeness SLA
- **Metric:** Percentage of non-null values
- **Target:** ≥98%
- **Window:** Daily
- **Severity:** HIGH
- **Action:** Warn on breach, investigate data source

### Validity SLA
- **Metric:** Percentage matching domain rules
- **Target:** ≥95%
- **Window:** Daily
- **Severity:** HIGH
- **Action:** Block materialization on critical failure

### Timeliness SLA
- **Metric:** Data age (hours since update)
- **Target:** <24 hours
- **Window:** Hourly
- **Severity:** MEDIUM
- **Action:** Alert if stale

### Consistency SLA
- **Metric:** Cross-dataset referential integrity
- **Target:** 100%
- **Window:** Daily
- **Severity:** CRITICAL
- **Action:** Halt materialization

## Integration with Other Systems

### Schema Registry (W1)
- Auto-generate expectations from schema constraints
- Detect type mismatches
- Validate against schema versions

### Material Standards (W2)
- Domain-specific material validation
- ADA compliance rule checking
- Lifecycle consistency checks

### Lineage (W3)
- Quality as part of transformation metadata
- Track quality degradation through pipelines
- Impact analysis on quality changes

### Observability (W4)
- Emit quality metrics to monitoring systems
- Quality-based alerting
- SLA breach notifications

### Audit Trail (W5-6)
- Log all quality violations
- Track remediation history
- Compliance audit trails
- CDC integration for quality change tracking

## PostgreSQL Schema

**Tables:**
- `quality_expectations` - Expectation definitions
- `quality_profiles` - Statistical profiles (time-series)
- `quality_validations` - Validation results (history)
- `quality_sla_config` - SLA definitions
- `quality_metrics` - Time-series metrics (partitioned by month)
- `quality_anomalies` - Detected anomalies
- `quality_catalog` - Dataset quality profiles
- `quality_sla_breaches` - SLA breach history
- `quality_rules_violations` - Rule violation tracking
- `quality_audit_trail` - Audit log

## Best Practices

### 1. Expectation Design
- Start with column existence and type checks
- Add domain-specific rules
- Use materialization modes strategically
- Version expectation suites

### 2. SLA Definition
- Define realistic targets based on historical data
- Use appropriate windows (hourly for real-time, daily for batch)
- Assign clear owners for each SLA
- Set grace periods to avoid alert fatigue

### 3. Rule Development
- Keep rules focused and testable
- Document business logic
- Use HARD rules sparingly (only for critical issues)
- Provide clear remediation suggestions

### 4. Monitoring
- Establish baseline quality metrics
- Track trends, not just point values
- Investigate anomalies promptly
- Document and learn from quality issues

### 5. Performance
- Validation overhead should be <10% of pipeline latency
- Use sampling for very large datasets
- Archive old quality data regularly
- Index quality tables for fast queries

## Example: Complete Quality Pipeline

```python
from socrata_toolkit.quality_expectations import create_sidewalk_inspections_suite
from socrata_toolkit.quality_profiler import ProfileGenerator
from socrata_toolkit.quality_validator import QualityValidator
from socrata_toolkit.quality_rules import create_sidewalk_rules
from socrata_toolkit.quality_integration import QualityIntegration
from socrata_toolkit.quality_catalog import DataQualityCatalog, DatasetQualityScore

# Setup
suite = create_sidewalk_inspections_suite()
profiler = ProfileGenerator()
validator = QualityValidator()
rules = create_sidewalk_rules()
catalog = DataQualityCatalog()
integration = QualityIntegration(suite, tracker, anomaly_detector, rules)

# Load data
df = pd.read_csv("inspections.csv")

# Validate ingestion
validation = integration.validate_ingestion(df, "sidewalk_inspections")

# Check rules
violations = rules.apply_hard_rules(df)
if not violations.can_proceed:
    raise ValueError("Critical rule violations")

# Profile for trending
profile = profiler.profile_dataset(df, "sidewalk_inspections")

# Update catalog
score = DatasetQualityScore(
    overall=validation.pass_rate * 100,
    completeness=98.5,
    validity=96.0,
)
catalog.update_quality_score("sidewalk_inspections", score)

# Process data
processed = df.transform()

# Final validation
final = integration.validate_transformation(processed, "sidewalk_inspections")

print(f"Quality: {final.pass_rate:.1%}, Violations: {violations.total_violations}")
```

## Troubleshooting

### High Failure Rate
1. Check if expectations are too strict
2. Investigate data source for changes
3. Review rule definitions for false positives

### SLA Breaches
1. Verify metric calculation
2. Check for data pipeline delays
3. Investigate anomaly reports

### Performance Issues
1. Reduce sample size for profiling
2. Archive old quality metrics
3. Optimize expectation evaluation order

## Next Steps

1. Define SLAs for key datasets
2. Create custom expectations for business domains
3. Integrate with pipelines using decorators
4. Set up monitoring dashboards
5. Establish quality improvement processes
