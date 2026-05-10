# Data Quality SLA Guide

## Overview

Service Level Agreements (SLAs) define measurable quality targets and track compliance. The SLA framework provides automated tracking, breach detection, and trend analysis.

## SLA Components

### Metric Type
- **Completeness:** % non-null values
- **Validity:** % matching domain rules
- **Uniqueness:** % unique values (for keys)
- **Consistency:** Cross-dataset integrity
- **Timeliness:** Data age < threshold
- **Accuracy:** % matching reference data

### Configuration Parameters

```python
SLADefinition(
    metric_name="sidewalk_completeness",      # Unique identifier
    metric_type=MetricType.COMPLETENESS,      # See Metric Type above
    target=0.98,                               # Target value (0-1)
    window="daily",                            # '5m', '1h', 'daily', 'weekly'
    dataset="sidewalk_inspections",            # Dataset this applies to
    severity=Severity.HIGH,                    # CRITICAL, HIGH, MEDIUM, LOW
    owner="data-engineering@example.com",      # Alert recipient
    materialization_mode=MaterializationMode.SOFT,  # HARD=block, SOFT=warn
    grace_period=5,                            # Minutes before alerting
)
```

## Pre-built SLAs

### Sidewalk Inspections
```
- sidewalk_inspections_completeness
  Target: 98% non-null
  Window: Daily
  Severity: HIGH

- sidewalk_inspections_validity
  Target: 95% passing domain rules
  Window: Daily
  Severity: HIGH

- sidewalk_inspections_timeliness
  Target: <24 hours old
  Window: Hourly
  Severity: MEDIUM
```

### 311 Complaints
```
- 311_complaints_completeness
  Target: 99% non-null
  Window: Daily
  Severity: HIGH
```

## Usage

### Register SLAs
```python
from socrata_toolkit.quality_sla import DataQualityTracker, create_standard_slas

tracker = DataQualityTracker()
for sla in create_standard_slas():
    tracker.register_sla(sla)
```

### Record Metrics
```python
tracker.record_metric(
    metric_name="sidewalk_inspections_completeness",
    value=0.99,
    dataset="sidewalk_inspections",
    metric_type=MetricType.COMPLETENESS,
    window="daily"
)
```

### Evaluate Compliance
```python
compliant, actual_value = tracker.evaluate_sla("sidewalk_inspections_completeness")

if not compliant:
    print(f"SLA violation: {actual_value} < target")
    # Alert owner, block materialization, etc.
```

### Analyze Trends
```python
trend = tracker.get_trend("sidewalk_inspections_completeness")

if trend.direction == TrendDirection.DEGRADING:
    print(f"Quality is declining: slope={trend.slope}")
```

### Generate Reports
```python
report = tracker.get_sla_compliance_report(lookback_minutes=1440)

print(f"Overall compliance: {report['overall_compliance']:.1%}")
for sla in report['sla_results']:
    if not sla['compliant']:
        print(f"  ❌ {sla['metric_name']}: {sla['actual']}/{sla['target']}")
```

## SLA Breach Management

### Active Breaches
```python
summary = tracker.get_breach_summary()
print(f"Active breaches: {summary['active_breaches']}")
print(f"Critical: {summary['critical_breaches']}")

# Investigate and resolve
# ...

# Mark as resolved
tracker.resolve_breach("metric_name")
```

### Breach Tracking
- Records timestamp, actual value, target
- Calculates breach duration
- Stores for audit and trend analysis

## Materialization Modes

### HARD Mode (Blocking)
```python
SLADefinition(
    ...
    materialization_mode=MaterializationMode.HARD,
)
# If SLA is breached, materialization is blocked
# Used for critical data requirements
```

### SOFT Mode (Warning)
```python
SLADefinition(
    ...
    materialization_mode=MaterializationMode.SOFT,
)
# If SLA is breached, warning is issued but materialization continues
# Used for non-critical metrics
```

## Time Windows

- **5m:** Real-time streaming data
- **1h:** Hourly aggregations (timeliness)
- **daily:** Batch daily loads
- **weekly:** Weekly summary data

## Grace Period

Prevents alert fatigue from momentary dips:

```python
SLADefinition(
    ...
    grace_period=5,  # Minutes to wait before alerting
)
# Metric must stay below target for 5+ minutes before breach
```

## Integration Points

### With Observability (W4)
- Emit metrics to Prometheus
- Create dashboards for monitoring
- Set up alerts in monitoring system

### With Audit Trail (W5-6)
- Log all SLA evaluations
- Record breaches with context
- Track remediation history

### With Lineage (W3)
- Include SLA status in transformation metadata
- Track quality degradation through pipelines
- Impact analysis on SLA breaches

## Best Practices

1. **Set realistic targets**
   - Base on historical data
   - Account for seasonal variations
   - Leave room for process improvements

2. **Define clear ownership**
   - Assign SLA owner
   - Define escalation path
   - Document remediation procedures

3. **Monitor trends**
   - Watch for degradation patterns
   - Investigate improving trends
   - Update targets based on capability

4. **Use appropriate windows**
   - Real-time data: 5m or 1h
   - Batch data: daily
   - Reports: weekly or monthly

5. **Review regularly**
   - Monthly SLA compliance review
   - Quarterly target reassessment
   - Annual framework evaluation

## Troubleshooting

### SLA Breaches
1. Check metric calculation
2. Verify data pipeline status
3. Review recent data changes
4. Investigate anomaly reports

### False Positives
1. Adjust target based on capability
2. Increase grace period
3. Review window size appropriateness

### No Data Recorded
1. Verify metric recording code runs
2. Check tracker initialization
3. Confirm dataset name matches

## Example SLA Configuration

```python
from socrata_toolkit.quality_sla import (
    DataQualityTracker,
    SLADefinition,
    MetricType,
    Severity,
    MaterializationMode,
)

tracker = DataQualityTracker()

# Critical SLA: Block on failure
tracker.register_sla(SLADefinition(
    metric_name="critical_completeness",
    metric_type=MetricType.COMPLETENESS,
    target=0.999,
    window="hourly",
    dataset="critical_dataset",
    severity=Severity.CRITICAL,
    owner="incident-commander@example.com",
    materialization_mode=MaterializationMode.HARD,
    grace_period=2,
))

# High priority: Alert on failure
tracker.register_sla(SLADefinition(
    metric_name="primary_validity",
    metric_type=MetricType.VALIDITY,
    target=0.95,
    window="daily",
    dataset="primary_dataset",
    severity=Severity.HIGH,
    owner="data-owner@example.com",
    materialization_mode=MaterializationMode.SOFT,
    grace_period=5,
))

# Record metrics throughout pipeline
for metric, value in metrics.items():
    tracker.record_metric(metric, value, dataset, metric_type)

# Check compliance
report = tracker.get_sla_compliance_report()
```
