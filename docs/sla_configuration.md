# SLA Configuration Guide

Service Level Agreement (SLA) configuration and monitoring for the NYC Data Engineering pipeline.

## Overview

SLAs define target performance levels for critical metrics. When actual values diverge from targets, the system:
1. Records the violation in the database
2. Triggers alert callbacks
3. Generates compliance reports

## SLA Lifecycle

```
Define SLA → Record Metrics → Evaluate → Detect Violations → Alert → Report → Track Trends
```

## Defining SLAs

### YAML Configuration

Create `config/sla_definitions.yaml`:

```yaml
slas:
  - metric_name: ingestion_latency_p99
    target: 5000              # milliseconds
    window: 5m                # 5m, 1h, 1d
    severity: CRITICAL        # CRITICAL, HIGH, MEDIUM, LOW
    channels:
      - pagerduty
      - slack
    description: "Ingestion P99 latency < 5 seconds"
```

### Programmatic Configuration

```python
from socrata_toolkit.observability_integration import get_observability_manager

obs = get_observability_manager()

# Add individual SLA
obs.configure_sla(
    metric_name='ingestion_latency_p99',
    target=5000,
    window='5m',
    severity='CRITICAL',
    channels=['pagerduty', 'slack']
)

# Load from file
obs.load_sla_config(Path('config/sla_definitions.yaml'))

# Save to file
obs.save_sla_config(Path('my_slas.yaml'))
```

## Common SLA Patterns

### Latency SLAs (Lower is Better)

For metrics like latency, duration, response time:

```yaml
- metric_name: api_response_time_p95
  target: 500           # milliseconds
  window: 5m            # Check every 5 minutes
  severity: MEDIUM
  description: "API must respond within 500ms for 95% of requests"
```

**Violation Logic**: If actual p95 > target (500ms)

### Success Rate SLAs (Higher is Better)

For metrics like success rate, availability, compliance:

```yaml
- metric_name: schema_compliance_rate
  target: 0.95          # 95%
  window: 1h
  severity: MEDIUM
  description: "95% of records must pass schema validation"
```

**Violation Logic**: If actual rate < target (0.95)

### Throughput SLAs (Lower Bound)

For metrics like records per second:

```yaml
- metric_name: ingestion_throughput
  target: 100           # records per second minimum
  window: 5m
  severity: MEDIUM
  description: "Process at least 100 records per second"
```

**Violation Logic**: If actual throughput < target (100)

## Window Types

| Window | Use Case | Example |
|--------|----------|---------|
| `5m` | Real-time alerting | Ingestion latency |
| `1h` | Hourly reporting | Success rates, compliance |
| `1d` | Daily reporting | Data freshness, uptime |

## Severity Levels

| Severity | Escalation | Typical Response |
|----------|------------|------------------|
| `CRITICAL` | Immediate | Page on-call engineer |
| `HIGH` | Urgent | Alert team lead |
| `MEDIUM` | Standard | Send to team channel |
| `LOW` | Background | Log and report |

## Notification Channels

```yaml
channels:
  - pagerduty      # Escalated critical alerts
  - slack          # Team notifications
  - email          # Historical records
  - webhook        # Custom integrations
```

## Recording Metrics

Metrics must be recorded before SLAs can be evaluated:

```python
from socrata_toolkit.observability_integration import get_observability_manager

obs = get_observability_manager()
sla = obs.get_sla_tracker()

# Record ingestion latency
ingestion_time = measure_ingestion()
sla.record_metric('ingestion_latency_p99', ingestion_time)

# Record success rate (0-1)
success_count = 950
total_count = 1000
success_rate = success_count / total_count
sla.record_metric('schema_compliance_rate', success_rate)

# Record throughput
records_per_second = 150
sla.record_metric('ingestion_throughput', records_per_second)
```

## Evaluating SLAs

### Automatic Evaluation

```python
# Evaluate all SLAs
report = sla.evaluate()

print(f"Compliance: {report.compliance_percent}%")
print(f"Violations: {len(report.violations)}")
for violation in report.violations:
    print(f"  {violation.sla_name}: {violation.actual} vs {violation.target}")
```

### Periodic Evaluation

Schedule evaluation at regular intervals:

```python
import schedule
import time

def evaluate_slas():
    sla = obs.get_sla_tracker()
    report = sla.evaluate()
    if not report.is_compliant:
        logger.warning(f"SLA violations: {report.compliance_percent}%")

# Evaluate every 5 minutes
schedule.every(5).minutes.do(evaluate_slas)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Alert Handling

### Custom Alert Callbacks

```python
from socrata_toolkit.observability_sla import SLAViolation

def handle_sla_violation(violation: SLAViolation):
    """Custom violation handler."""
    message = f"""
    SLA Violation Detected!
    SLA: {violation.sla_name}
    Severity: {violation.severity}
    Target: {violation.target}
    Actual: {violation.actual}
    Window: {violation.window}
    """
    
    if violation.severity == 'CRITICAL':
        send_pagerduty_alert(message)
    elif violation.severity == 'HIGH':
        send_slack_alert(message)

sla = obs.get_sla_tracker()
sla.register_alert_callback(handle_sla_violation)
```

### Integration with alerts.py

```python
from socrata_toolkit.alerts import AlertManager, Alert

alert_manager = AlertManager()

def handle_sla_with_alerts(violation: SLAViolation):
    alert = Alert(
        severity=violation.severity.lower(),
        message=f"SLA Violation: {violation.sla_name}",
        payload={
            'sla_name': violation.sla_name,
            'target': violation.target,
            'actual': violation.actual,
        }
    )
    alert_manager.emit(alert)

sla.register_alert_callback(handle_sla_with_alerts)
```

## Compliance Reporting

### Get SLA Report

```python
report = sla.evaluate()

print(f"Report Time: {report.report_time}")
print(f"Total SLAs: {report.total_slas}")
print(f"Passing: {report.passing_slas}")
print(f"Failing: {report.failing_slas}")
print(f"Compliance: {report.compliance_percent}%")
print(f"Trend: {report.trend}")

for violation in report.violations:
    print(f"  ✗ {violation.sla_name}: {violation.actual} vs {violation.target}")
```

### Export Report

```python
import json
from pathlib import Path

report_dict = report.to_dict()

# Save as JSON
with open('sla_report.json', 'w') as f:
    json.dump(report_dict, f, indent=2)

# Query from database
# SELECT * FROM observability_sla_violations 
# WHERE DATE(violation_time) = CURRENT_DATE;
```

## Trend Analysis

The system tracks compliance trends:

```python
report = sla.evaluate()

if report.trend == 'improving':
    print("✓ SLA compliance improving")
elif report.trend == 'degrading':
    print("✗ SLA compliance degrading")
else:
    print("→ SLA compliance stable")
```

## Best Practices

### 1. Start Conservative, Tighten Over Time

```yaml
# Week 1: Conservative targets
- metric_name: latency
  target: 10000  # 10 seconds

# Week 4: Tighter after optimization
- metric_name: latency
  target: 5000   # 5 seconds
```

### 2. Use Percentiles for Latency

```yaml
# Good - measures tail latency
- metric_name: ingestion_latency_p99
  target: 5000

# Less useful - averages hide outliers
- metric_name: ingestion_latency_avg
  target: 2000
```

### 3. Combine Related SLAs

```yaml
# Together they tell complete story
- metric_name: success_rate
  target: 0.99   # 99% success

- metric_name: latency_p99
  target: 5000   # But must be fast
```

### 4. Align Windows with Monitoring

```yaml
# Monitor
window: 5m     # Every 5 minutes

# Report on
window: 1h     # Hourly summaries
           OR: 1d  # Daily reports
```

### 5. Progressive Severity

```yaml
# Use severity strategically
- metric_name: critical_metric
  severity: CRITICAL  # Immediate action needed

- metric_name: nice_to_have
  severity: LOW       # Background tracking
```

## Troubleshooting SLAs

### SLA Violations Not Detected

1. **Check SLA Configuration**
   ```python
   print(sla.summary_dict())
   ```

2. **Verify Metrics are Being Recorded**
   ```python
   print(sla._metrics['metric_name'])
   ```

3. **Check Evaluation Window**
   ```python
   # Only evaluates recent data
   # Make sure metrics are fresh
   ```

### False Positives

If getting too many violations:

1. **Increase Target**
   ```yaml
   target: 5000  # Was too strict
   ```

2. **Increase Window**
   ```yaml
   window: 1h    # More time to achieve
   ```

3. **Lower Severity**
   ```yaml
   severity: MEDIUM  # Less urgent
   ```

### Missing Violations

If violations are not detected:

1. **Check Metric Name Matches**
   ```python
   sla.add_sla('ingestion_latency_p99')  # Must match exactly
   sla.record_metric('ingestion_latency_p99', value)
   ```

2. **Verify Metric Type Detection**
   - Latency metrics: Must contain 'latency', 'duration', or 'time'
   - Success metrics: Must contain 'success', 'rate', or 'compliance'

3. **Check Time Window**
   ```python
   # 5m window requires 5+ minutes of data
   ```

## Advanced Configuration

### Dynamic SLA Updates

```python
# Remove outdated SLA
sla.remove_sla('old_metric')

# Add new SLA
sla.add_sla('new_metric', target=100, window='5m')

# Save updated config
obs.save_sla_config(Path('config/sla_definitions.yaml'))
```

### Multi-Level SLAs

```yaml
# Tier 1: Very strict (used when critical)
- metric_name: latency_p99
  target: 2000
  severity: CRITICAL
  window: 5m

# Tier 2: Standard (used normally)
- metric_name: latency_p99
  target: 5000
  severity: HIGH
  window: 5m

# Tier 3: Relaxed (used during incidents)
- metric_name: latency_p99
  target: 10000
  severity: MEDIUM
  window: 5m
```

### Metric-Specific Handling

```python
def custom_violation_handler(violation: SLAViolation):
    if violation.sla_name == 'ingestion_latency_p99':
        # Trigger ingestion optimization
        trigger_optimization()
    elif violation.sla_name == 'schema_compliance':
        # Review recent schema changes
        review_schema_changes()

sla.register_alert_callback(custom_violation_handler)
```

## Example: Complete SLA Setup

```python
from pathlib import Path
from socrata_toolkit.observability_integration import get_observability_manager
from socrata_toolkit.observability_sla import SLAViolation

# Initialize
obs = get_observability_manager()
obs.initialize()

# Load SLA configuration
obs.load_sla_config(Path('config/sla_definitions.yaml'))

# Setup alerting
def alert_handler(violation: SLAViolation):
    print(f"ALERT: {violation.sla_name} violated!")

obs.get_sla_tracker().register_alert_callback(alert_handler)

# Simulate pipeline
for i in range(100):
    # Record metrics
    obs.get_sla_tracker().record_metric('ingestion_latency_p99', 4500 + i*10)
    obs.get_sla_tracker().record_metric('schema_compliance_rate', 0.97)
    
    # Evaluate every 10 iterations
    if i % 10 == 0:
        report = obs.sla_report()
        print(f"Compliance: {report['compliance_percent']}%")
```

## See Also

- [`docs/observability.md`](observability.md) - Main observability documentation
- [`config/sla_definitions.yaml`](../config/sla_definitions.yaml) - Example SLA configuration
- [`socrata_toolkit/observability_sla.py`](../socrata_toolkit/observability_sla.py) - SLA implementation
