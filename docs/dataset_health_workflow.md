# Dataset Health & Monitoring Workflow

## Overview

The Dataset Health & Monitoring workflow is a multi-stage LangGraph-based orchestration system that evaluates the health of all 26 registered NYC Open Data datasets and provides Claude-powered decision-making on high-severity issues.

**Key components:**
- `DatasetHealthClassifier` — Status detection (HEALTHY / STALE / SCHEMA_DRIFT / EMPTY_OR_ERROR)
- `DatasetHealthWorkflow` — LangGraph orchestration with 5 nodes
- `run_dataset_health_workflow()` — Convenience entry point
- CLI integration — `socrata dataset health --workflow`

## Architecture

### Health Classification (150 lines)

The classifier evaluates four dimensions for each dataset:

| Dimension | Metric | Healthy | Warning | Critical |
|-----------|--------|---------|---------|----------|
| **Freshness** | Days since last update | ≤ SLA | > SLA | N/A |
| **Completeness** | Row count | > 100 rows | — | ≤ 100 rows |
| **Schema Stability** | Changes from baseline | None | Added columns | Removed columns or type changes |
| **Accessibility** | API reachability | 200 OK | — | Error / Timeout |

**Severity Scoring (0-100):**
- 0-20: CRITICAL (Red) — Data is inaccessible or empty
- 21-50: HIGH (Orange) — Stale data or schema drift
- 51-70: MEDIUM (Yellow) — Approaching SLA threshold
- 71-100: LOW (Green) — All systems healthy

### Workflow Nodes (200 lines)

LangGraph structure:

```
START
  ↓
[fetch_metadata] — Parallelized API calls to Socrata
  ↓
[classify] — DatasetHealthClassifier processes metrics
  ↓
[route_severity] — Filter datasets with severity ≤70
  ↓
[conditional routing]
  ├─ Low severity (>70) → aggregate
  └─ High severity (≤70) → claude_decision
  ↓
[claude_decision] — Claude analyzes top 10 problematic datasets
  ↓
[aggregate] — Build final JSON report
  ↓
END
```

**Node Details:**

#### 1. `fetch_metadata` (Parallelized)
Fetches metadata for all 37 datasets using SocrataClient:
- Row counts via SODA v3 query
- Schema via /api/views/{fourfour}.json
- Last-modified timestamps
- Error handling: Graceful degradation on API failures

```python
# Input: registry dict
# Output: metadata_cache[key] = {row_count, columns, last_modified, is_accessible}
```

#### 2. `classify`
Applies DatasetHealthClassifier to each dataset:
- Compares freshness against SLA thresholds
- Detects schema drift vs baseline
- Calculates severity (0-100)
- Generates alerts and recommendations

```python
# Input: metadata_cache
# Output: classifications[key] = {status, severity, alerts, recommendations}
```

#### 3. `route_severity`
Filters datasets by severity for Claude escalation:
- severity ≤ 70: Routed to Claude
- severity > 70: Skipped (healthy)

```python
# Input: classifications
# Output: high_severity_datasets = [...]
```

#### 4. `claude_decision`
Calls Claude API (haiku-4-5) with ~300 token budget:
- Prompt: "Which 3-5 datasets need immediate action?"
- Returns: Root causes + escalation paths as JSON
- Graceful fallback if API unavailable

```python
# Input: high_severity_datasets (capped to 10)
# Output: claude_recommendations = {critical_action_required: [...]}
```

#### 5. `aggregate`
Builds final report with all results:
- Summary counts (healthy/stale/drift/error)
- Critical alerts list
- Claude recommendations
- Error log from each stage

```python
# Output: {
#   "timestamp": "2026-06-11T...",
#   "summary": {"healthy": N, "stale": N, ...},
#   "datasets": {...},
#   "critical_alerts": [...],
#   "claude_recommendations": {...}
# }
```

## Usage

### Python API

**Quick run (recommended):**
```python
from socrata_toolkit.analysis import run_dataset_health_workflow

report = run_dataset_health_workflow()
print(f"Critical issues: {len(report['critical_alerts'])}")
```

**Full workflow with custom settings:**
```python
from socrata_toolkit.analysis import DatasetHealthWorkflow

registry = {
    "violations": {"fourfour": "6kbp-uz6m"},
    "inspection": {"fourfour": "dntt-gqwq"},
    # ... 24 more datasets
}

workflow = DatasetHealthWorkflow(
    registry=registry,
    domain="data.cityofnewyork.us",
    sla_thresholds={"HIGH": 14, "MEDIUM": 30, "LOW": 60}
)
report = workflow.run()
```

**Low-level classifier (single dataset):**
```python
from socrata_toolkit.analysis import (
    DatasetHealthClassifier,
    DatasetHealthMetrics,
)
from datetime import datetime, timezone, timedelta

classifier = DatasetHealthClassifier()

metrics = DatasetHealthMetrics(
    key="violations",
    fourfour="6kbp-uz6m",
    row_count=312000,
    last_modified=datetime.now(timezone.utc) - timedelta(days=5),
    schema_snapshot={"id": "int64", "status": "object"},
    schema_baseline={"id": "int64", "status": "object"},
    is_accessible=True
)

report = classifier.classify(metrics)
print(f"Status: {report.status.value}")
print(f"Severity: {report.severity}/100")
print(f"Alerts: {report.alerts}")
```

### CLI

**Quick health check (existing):**
```bash
socrata dataset health --all
socrata dataset health --stale 7
```

**Full workflow (new):**
```bash
# Option 1: Extend existing command
socrata dataset health --workflow
socrata dataset health --workflow --output report.json

# Option 2: Dedicated command (if added)
socrata dataset health-workflow
socrata dataset health-workflow --format markdown
```

**Continuous monitoring:**
```bash
socrata dataset health --monitor  # Checks every 24h
```

### Output Format

```json
{
  "timestamp": "2026-06-11T14:30:00Z",
  "total_datasets": 26,
  "summary": {
    "healthy": 18,
    "stale": 4,
    "schema_drift": 1,
    "empty_or_error": 3
  },
  "datasets": {
    "violations": {
      "key": "violations",
      "fourfour": "6kbp-uz6m",
      "status": "healthy",
      "severity": 85,
      "severity_level": "low",
      "freshness_days": 2,
      "row_count": 312000,
      "alerts": [],
      "recommendations": []
    },
    "ramp_locations": {
      "key": "ramp_locations",
      "fourfour": "ufzp-rrqu",
      "status": "stale",
      "severity": 25,
      "severity_level": "high",
      "freshness_days": 2100,
      "row_count": 217000,
      "alerts": [
        "Data is stale: 2100 days old (SLA: 30 days)"
      ],
      "recommendations": [
        "Investigate why updates have paused (expected refresh every 30 days)",
        "Check data source and ETL pipeline health"
      ]
    }
  },
  "critical_alerts": [
    {
      "key": "ramp_locations",
      "fourfour": "ufzp-rrqu",
      "status": "stale",
      "alerts": ["Data is stale: 2100 days old (SLA: 30 days)"]
    }
  ],
  "claude_recommendations": {
    "critical_action_required": [
      {
        "key": "ramp_locations",
        "root_cause": "Data ingestion pipeline halted in 2021; no updates since.",
        "escalation": "Contact data owner (Accessibility team) + NYC Open Data support"
      }
    ],
    "next_steps": [
      "Re-enable ramp_locations ETL if data still exists in source system",
      "Switch analytics to ramp_progress (daily updates) as workaround"
    ]
  },
  "errors": [
    "permit_stipulations (gsgx-6efw): HTTP 403 Forbidden"
  ]
}
```

## Integration Points

### 1. SLA Configuration

Define thresholds in environment or code:

```python
SLA_THRESHOLDS = {
    "HIGH": 14,      # Mission-critical data (14 days)
    "MEDIUM": 30,    # Important (30 days)
    "LOW": 60        # Supporting (60 days)
}
```

Update in `CLAUDE.md` if changed.

### 2. Schema Baselines

To enable schema drift detection, load baselines from persistence:

```python
# TODO: Implement in _node_classify()
baseline = load_schema_snapshot(f"baselines/{key}.json")
metrics.schema_baseline = baseline
```

### 3. Alerts & Escalation

Route critical alerts to observability/alerting system:

```python
from socrata_toolkit.observability import AlertManager

alerts = AlertManager()
for alert in report["critical_alerts"]:
    alerts.emit(
        severity=alert["severity"],
        message=f"{alert['key']}: {alert['status']}",
        tags=["dataset-health", alert["status"]]
    )
```

### 4. Claude Customization

Adjust Claude prompt in `_node_claude_decision()`:

```python
prompt = f"""
Your custom prompt here.
Datasets: {datasets_text}
Context: ...
"""
```

## Testing

**Unit tests:**
```bash
pytest tests/test_dataset_health.py -v
```

**Integration test (requires SOCRATA_APP_TOKEN):**
```bash
pytest tests/test_dataset_health_workflow.py -v
```

**Manual test:**
```python
from socrata_toolkit.analysis import run_dataset_health_workflow
report = run_dataset_health_workflow()
assert "summary" in report
print("✓ Workflow executed successfully")
```

## Performance

- **Metadata fetch:** ~30-45s (parallelized, 37 datasets)
- **Classification:** ~1s
- **Claude decision:** ~5-10s (API latency)
- **Total end-to-end:** ~45-60s

**Optimization tips:**
- Cache metadata between runs (implement persistence layer)
- Parallelize Claude calls if >10 high-severity datasets
- Increase `page_size` in SocrataConfig for faster counting

## Known Limitations

1. **Schema baselines:** Currently `schema_baseline` is None; implement persistence layer to enable drift detection.
2. **Last-modified extraction:** May differ by dataset (rowsUpdatedAt vs updatedAt). See `_extract_last_modified()`.
3. **LangGraph optional:** Gracefully falls back to sequential execution if LangGraph not installed.
4. **Claude budget:** Capped to 10 datasets per decision call (~300 tokens).

## Future Enhancements

- [ ] Persistence layer for schema baselines and historical metrics
- [ ] Slack/email alerting for critical issues
- [ ] Scheduled execution (APScheduler integration)
- [ ] Custom SLA thresholds per dataset
- [ ] Data freshness trend analysis
- [ ] Automated remediation suggestions (beyond Claude)
- [ ] Multi-language Claude prompts (Spanish, Haitian Creole)

## References

- **CLAUDE.md** — Project context and dataset registry
- **governance/core.py** — QualityScore + schema detection patterns
- **quality/sla.py** — SLA framework and definitions
- **core/client.py** — SocrataClient API patterns

## Contact

For questions or enhancements:
- File an issue in the repo
- Contact the data team at ryudkiss@gmail.com

