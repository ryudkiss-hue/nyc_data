# Dataset Health Workflow - Quick Start Guide

## 5-Minute Setup

### 1. Check Installation

```python
# Verify imports work
from socrata_toolkit.analysis import (
    DatasetHealthClassifier,
    DatasetHealthWorkflow,
    run_dataset_health_workflow,
)
print("✓ Dataset Health modules imported successfully")
```

### 2. Run Quick Health Check

```python
# Simplest possible usage
from socrata_toolkit.analysis import run_dataset_health_workflow

report = run_dataset_health_workflow()

# Print summary
print(f"Total datasets: {report['total_datasets']}")
print(f"Healthy: {report['summary']['healthy']}")
print(f"Stale: {report['summary']['stale']}")
print(f"Critical alerts: {len(report['critical_alerts'])}")

# Show critical issues
for alert in report['critical_alerts'][:3]:
    print(f"  - {alert['key']}: {alert['status']}")
```

### 3. Check Single Dataset

```python
from socrata_toolkit.analysis import (
    DatasetHealthClassifier,
    DatasetHealthMetrics,
)
from datetime import datetime, timezone, timedelta

classifier = DatasetHealthClassifier()

# Example: violations dataset
metrics = DatasetHealthMetrics(
    key="violations",
    fourfour="6kbp-uz6m",
    row_count=312000,
    last_modified=datetime.now(timezone.utc) - timedelta(days=3),
    schema_snapshot={"id": "int64", "status": "object"},
    schema_baseline={"id": "int64", "status": "object"},
    is_accessible=True
)

report = classifier.classify(metrics)
print(f"Status: {report.status.value}")
print(f"Severity: {report.severity}/100 ({report.severity_level.value})")
print(f"Alerts: {report.alerts}")
print(f"Recommendations: {report.recommendations}")
```

## Common Tasks

### Task 1: Find All Stale Datasets

```python
from socrata_toolkit.analysis import run_dataset_health_workflow

report = run_dataset_health_workflow()

stale = [d for d in report['datasets'].values() if d['status'] == 'stale']
print(f"Found {len(stale)} stale datasets:")
for dataset in stale:
    days_old = dataset.get('freshness_days', 'unknown')
    print(f"  - {dataset['key']}: {days_old} days old")
```

### Task 2: Get Claude Recommendations for Critical Issues

```python
from socrata_toolkit.analysis import run_dataset_health_workflow

report = run_dataset_health_workflow()

if report.get('claude_recommendations'):
    recs = report['claude_recommendations']
    if recs.get('critical_action_required'):
        print("Claude's top issues:")
        for issue in recs['critical_action_required']:
            print(f"  {issue['key']}: {issue['root_cause']}")
            print(f"    Escalation: {issue['escalation']}")
```

### Task 3: Classify Multiple Datasets

```python
from socrata_toolkit.analysis import DatasetHealthClassifier, DatasetHealthMetrics
from datetime import datetime, timezone, timedelta

classifier = DatasetHealthClassifier()
now = datetime.now(timezone.utc)

datasets = [
    ("violations", "6kbp-uz6m", 312000, now - timedelta(days=2)),
    ("inspection", "dntt-gqwq", 398000, now - timedelta(days=1)),
    ("ramp_progress", "e7gc-ub6z", 187000, now - timedelta(days=7)),
]

metrics_list = [
    DatasetHealthMetrics(
        key=key,
        fourfour=fourfour,
        row_count=row_count,
        last_modified=last_modified,
        schema_snapshot={"id": "int64"},
        schema_baseline={"id": "int64"},
        is_accessible=True
    )
    for key, fourfour, row_count, last_modified in datasets
]

reports = classifier.classify_batch(metrics_list)
for report in reports:
    print(f"{report.key}: {report.status.value} (severity={report.severity})")
```

### Task 4: Export Results to JSON

```python
import json
from socrata_toolkit.analysis import run_dataset_health_workflow

report = run_dataset_health_workflow()

with open("health_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Report saved to health_report.json")
```

### Task 5: Get Batch Summary

```python
from socrata_toolkit.analysis import DatasetHealthClassifier

classifier = DatasetHealthClassifier()

# Classify multiple datasets (as shown in Task 3)
reports = classifier.classify_batch(metrics_list)

# Get summary
summary = classifier.summarize(reports)
print(f"Healthy: {summary['healthy']}")
print(f"Stale: {summary['stale']}")
print(f"Schema Drift: {summary['schema_drift']}")
print(f"Empty/Error: {summary['empty_or_error']}")
print(f"\nDatasets needing attention ({len(summary['needs_attention'])}):")
for dataset in summary['needs_attention']:
    print(f"  - {dataset['key']}: {dataset['primary_alert']}")
```

## API Reference

### DatasetHealthClassifier

```python
classifier = DatasetHealthClassifier(
    sla_thresholds={"HIGH": 14, "MEDIUM": 30, "LOW": 60},
    empty_threshold=100  # Rows below this = empty
)

# Single classification
report = classifier.classify(metrics)

# Batch classification
reports = classifier.classify_batch(metrics_list)

# Summary
summary = classifier.summarize(reports)
```

### DatasetHealthMetrics (Input)

```python
metrics = DatasetHealthMetrics(
    key: str,                                      # Dataset key (e.g. "violations")
    fourfour: str,                                 # Socrata ID (e.g. "6kbp-uz6m")
    row_count: int | None,                         # Row count (or None if unavailable)
    last_modified: datetime | None,                # Last update timestamp
    schema_snapshot: dict[str, str] | None,        # Current schema {col: dtype}
    schema_baseline: dict[str, str] | None,        # Baseline schema for drift detection
    is_accessible: bool,                           # True if API reachable
    error_message: str | None = None,              # Error details if not accessible
)
```

### DatasetHealthReport (Output)

```python
report = DatasetHealthReport(
    key: str,                                      # Dataset key
    fourfour: str,                                 # Socrata ID
    status: HealthStatus,                          # HEALTHY | STALE | SCHEMA_DRIFT | EMPTY_OR_ERROR
    severity: int,                                 # 0-100 score
    severity_level: Severity,                      # CRITICAL | HIGH | MEDIUM | LOW
    freshness_days: int | None,                    # Days since last update
    row_count: int | None,                         # Current row count
    schema_changes: dict,                          # Drift detection results
    alerts: list[str],                             # Issues found
    recommendations: list[str],                    # Suggested fixes
    metadata: dict[str, Any],                      # Extra context
)

# Convert to dict for JSON serialization
report_dict = report.to_dict()
```

## Status & Severity Reference

### Health Status

| Status | Meaning | Color | Action |
|--------|---------|-------|--------|
| HEALTHY | All systems nominal | Green | No action |
| STALE | Data is older than SLA | Yellow | Investigate ETL |
| SCHEMA_DRIFT | Schema changed unexpectedly | Yellow | Review changes |
| EMPTY_OR_ERROR | Dataset empty or inaccessible | Red | Critical escalation |

### Severity Levels

| Severity | Range | Color | Escalation |
|----------|-------|-------|-----------|
| CRITICAL | 0-20 | Red | Immediate action required |
| HIGH | 21-50 | Orange | Review within 24h |
| MEDIUM | 51-70 | Yellow | Monitor, plan fix |
| LOW | 71-100 | Green | No action needed |

## Troubleshooting

### "ModuleNotFoundError: No module named 'langgraph'"

The workflow gracefully falls back to sequential execution if LangGraph is unavailable:

```python
from socrata_toolkit.analysis import run_dataset_health_workflow
# Still works! Just slower (no parallelization)
report = run_dataset_health_workflow()
```

### "SOCRATA_APP_TOKEN not set"

The workflow will still run, but limited to 2000 rows per dataset. To fetch full datasets:

```bash
export SOCRATA_APP_TOKEN="your_token_here"
python -c "from socrata_toolkit.analysis import run_dataset_health_workflow; print(run_dataset_health_workflow())"
```

### "ANTHROPIC_API_KEY not set"

Claude recommendations will be skipped if the API key is unavailable:

```python
report = run_dataset_health_workflow()
# report['claude_recommendations'] will be {'error': '...'}
```

### Schema baseline always None

Currently, baselines must be loaded from persistence. This is a TODO:

```python
# Current behavior
metrics.schema_baseline = None  # No drift detection

# To enable drift detection, implement:
# baseline = load_schema_snapshot(f"baselines/{key}.json")
# metrics.schema_baseline = baseline
```

## Next Steps

1. **Run the workflow:** `python` → `run_dataset_health_workflow()`
2. **Integrate with CLI:** Copy snippet from `dataset_health_cli_snippet.py` to `core/cli.py`
3. **Set up alerts:** Route critical_alerts to Slack/email
4. **Schedule:** Run nightly via APScheduler
5. **Customize:** Update SLA thresholds in config

## Documentation

- **Full documentation:** See `docs/dataset_health_workflow.md`
- **Build summary:** See `DATASET_HEALTH_WORKFLOW_BUILD_SUMMARY.md`
- **Test coverage:** See `tests/test_dataset_health.py`
- **CLI snippet:** See `dataset_health_cli_snippet.py`

## Files

```
src/socrata_toolkit/analysis/
├── dataset_health.py           # Classifier (150 lines)
├── dataset_health_workflow.py  # Workflow (200 lines)
└── dataset_health_cli_snippet.py # CLI integration example

docs/
└── dataset_health_workflow.md  # Full documentation

tests/
└── test_dataset_health.py      # 11 test cases
```

## Performance

- **Full workflow (26 datasets + Claude):** ~45-60 seconds
- **Quick health check (no Claude):** ~30-45 seconds
- **Single dataset classification:** <1 second

## Support

Questions? Check:
1. This quickstart (you're reading it)
2. `docs/dataset_health_workflow.md` (comprehensive reference)
3. `DATASET_HEALTH_WORKFLOW_BUILD_SUMMARY.md` (architecture details)
4. `tests/test_dataset_health.py` (code examples)
