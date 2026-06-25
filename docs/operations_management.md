# Operations Management & Automation Guide

This document outlines the architecture and operational playbook for turning raw 311 and GIS data into proactive, prioritized actions for NYC DOT.

## Key concepts
- Early Warning System: Detect conflicts, SLA breaches, and resource overload before they impact delivery.
- Batch vs Streaming: Use streaming mode for low-memory runs; use bulk COPY for nightly large loads.
- PostGIS-first: Spatial joins and heavy lifting belong in the database for scale.

## Components
- Ingest: SocrataClient streaming fetch (page-by-page), transform to canonical schema.
- Store: Postgres/PostGIS for authoritative storage; Mongo for denormalized operational state.
- Analyze: Use Python modules (`ops`, `conflict`, `relevance`) to compute Metrics and rankings.
- Notify: `alerts.AlertManager` routes to CLI, email, and DB.

## Nightly job outline
1. Fetch deltas using `client.fetch_since()` with a stored high-watermark.
2. Load into staging tables using `PostgresExporter.copy_upsert_batches()`.
3. Refresh materialized `construction_lists` view.
4. Run `PostGISConflictResolver` against `permits` and `active_projects`.
5. Produce Metrics and push alerts through the `AlertManager`.

## Recommended Postgres schema additions
- `alerts` table: persistent store of issued alerts (see `docs/sop_faq.md`).
- `construction_lists` materialized view: pre-computed lists for each contractor.
- `permits` and `active_projects` partitioned by borough for scale.

## Example: Grace Period automation
Implement a scheduled job that reads from `violations`:

```sql
UPDATE violations
SET status = 'City-Initiated'
WHERE date_part('day', now() - issued_date) > COALESCE(grace_pd, 75)
  AND status = 'Pending Repair';
```

This SQL can be converted into a Python method with `psycopg` and scheduled in your orchestration layer.

---

# Phase 2: Observability & Lineage Operations

## Overview

Phase 2 introduces comprehensive observability infrastructure for monitoring data freshness, pipeline health, and data quality. This section documents operational procedures for managing and troubleshooting the observability stack.

## Observability Components

### 1. Data Freshness Monitoring

**Purpose**: Track dataset update frequency, SLA compliance, and alert on staleness violations.

**Key Classes**:
- [`FreshnessTracker`](../socrata_toolkit/freshness.py): Core SLA monitoring
- [`DatasetFreshness`](../socrata_toolkit/freshness.py): Per-dataset metadata
- [`FreshnessAlert`](../socrata_toolkit/freshness.py): Alert generation

**Configuration**:

```python
from socrata_toolkit.freshness import FreshnessTracker
from datetime import datetime

# Initialize tracker (in-memory or PostgreSQL backend)
tracker = FreshnessTracker(db_dsn='postgresql://user:pass@localhost/freshness')

# Track ingestion with SLA
tracker.track_ingestion(
    dataset_id='nyc-311',
    last_updated_utc=datetime.utcnow(),
    expected_frequency_hours=24,
    sla_threshold_hours=48  # Alert if stale > 48 hours
)

# Get freshness status
status = tracker.get_freshness_status('nyc-311')
print(f"Fresh: {status['is_fresh']}, Days Stale: {status['days_stale']}")

# Compute SLA compliance
sla_report = tracker.compute_freshness_sla_pct(period_days=30)
print(f"SLA Compliance: {sla_report['compliance_pct']:.1f}%")

# Get stale datasets
alerts = tracker.get_stale_datasets()
for alert in alerts:
    print(f"ALERT: {alert.dataset_name} stale for {alert.stale_hours:.1f}h")
```

**Operational Thresholds**:
- Warning: SLA exceeded by < 24 hours
- Critical: SLA exceeded by ≥ 24 hours
- Default SLA: 2x expected update frequency

### 2. Data Lineage Tracking

**Purpose**: Track data flow from ingestion through transformations to serving.

**Key Classes**:
- [`LineageGraph`](../socrata_toolkit/lineage.py): DAG of data flows
- [`LineageEdge`](../socrata_toolkit/lineage.py): Individual source→target relationships
- [`ColumnLineage`](../socrata_toolkit/lineage.py): Column-level provenance
- [`LineageRegistry`](../socrata_toolkit/lineage.py): Persistent storage with PostgreSQL

**Configuration**:

```python
from socrata_toolkit.lineage import LineageRegistry, TransformationType

# Initialize registry (in-memory or with PostgreSQL)
registry = LineageRegistry(db_dsn='postgresql://user:pass@localhost/lineage')
graph = registry.get_graph()

# Add lineage edges
graph.add_edge(
    source_dataset_id='raw_311_data',
    target_dataset_id='311_staging',
    source_columns=['incident_id', 'location'],
    target_columns=['id', 'location'],
    transformation_type=TransformationType.INGESTION
)

graph.add_edge(
    source_dataset_id='311_staging',
    target_dataset_id='311_summary',
    source_columns=['incident_id'],
    target_columns=['ticket_id'],
    transformation_type=TransformationType.AGGREGATION,
    transformation_sql='SELECT COUNT(*) as count GROUP BY incident_type'
)

# Query lineage
upstream_tables = graph.get_upstream_tables('311_summary')
downstream_tables = graph.get_downstream_tables('raw_311_data')
column_lineage = graph.trace_column_lineage('311_summary', 'ticket_id')

# Export for visualization
openmetadata_format = graph.export_to_openmetadata_format()
```

**Lineage Validation**:
- Cycle detection prevents circular dependencies
- Column mapping validates transformation correctness
- SQL parsing extracts implicit lineage from queries

### 3. Prometheus Metrics Export

**Purpose**: Export operational metrics for Grafana dashboards and alerting.

**Key Classes**:
- [`MetricsRegistry`](../socrata_toolkit/metrics.py): Central metric collection
- [`PipelineMetrics`](../socrata_toolkit/metrics.py): Ingestion and validation metrics
- [`DataQualityMetrics`](../socrata_toolkit/metrics.py): Data quality scorecards

**Configuration**:

```python
from socrata_toolkit.metrics import (
    get_global_registry,
    PipelineMetrics,
    DataQualityMetrics
)

# Use global metrics registry
registry = get_global_registry()

# Create metric collectors
pipeline_metrics = PipelineMetrics(registry=registry)
dq_metrics = DataQualityMetrics(registry=registry)

# Record ingestion metrics
pipeline_metrics.record_ingestion_success('nyc-311', record_count=1500, duration_seconds=2.5)
pipeline_metrics.record_ingestion_error('nyc-parking', error_type='network')
pipeline_metrics.record_schema_violation('nyc-311', violation_type='column_added')
pipeline_metrics.record_validation_failure('nyc-311', rule_name='not_null_check')

# Record data quality metrics
dq_metrics.record_completeness('nyc-311', 'created_date', 99.5)
dq_metrics.record_validity('nyc-311', 'latitude', 98.7)
dq_metrics.record_uniqueness('nyc-311', 'ticket_id', 100.0)
dq_metrics.record_referential_integrity('nyc-311', 'location_id', 99.8)

# Export for Prometheus scrape
prometheus_text = registry.export_prometheus()
# Returns metrics in OpenMetrics text format
```

**Prometheus Scrape Endpoint**:

```python
from flask import Flask
app = Flask(__name__)

@app.route('/metrics')
def metrics():
    registry = get_global_registry()
    return registry.export_prometheus(), 200, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### 4. Unified Observability Logging

**Purpose**: Structured logging with operational context, request tracing, and audit trails.

**Key Classes**:
- [`OperationalLogger`](../socrata_toolkit/observability.py): Enhanced logging with structured fields
- [`OperationalContext`](../socrata_toolkit/observability.py): Request tracing with start/end/duration
- [`AuditLog`](../socrata_toolkit/observability.py): Immutable compliance audit trail

**Configuration**:

```python
from socrata_toolkit.observability import (
    OperationalLogger,
    OperationalContext,
    AuditLog,
    ActionType
)

# Initialize logger
logger = OperationalLogger(__name__)

# Log with structured fields
logger.info('Processing dataset', dataset_id='nyc-311', record_count=1500)
logger.warning('SLA violation detected', dataset_id='nyc-311', error='Stale > 24h')
logger.error('Ingestion failed', dataset_id='nyc-311', error='Connection timeout')

# Use context manager for request tracing
with OperationalContext(
    operation_type='ingestion',
    dataset_id='nyc-311',
    logger=logger
) as ctx:
    try:
        # Perform operation
        records = ingest_dataset('nyc-311')
        logger.info(f'Ingestion complete', record_count=len(records))
    except Exception as e:
        logger.error(f'Ingestion failed: {e}')
        # Context logs duration and failure automatically on exit

# Initialize audit trail
audit = AuditLog(db_dsn='postgresql://user:pass@localhost/audit')

# Record compliance events
audit.record_action(
    ActionType.INGESTION,
    dataset_id='nyc-311',
    details={'records_ingested': 1500, 'duration_seconds': 2.5}
)

audit.record_action(
    ActionType.SCHEMA_CHANGE,
    dataset_id='nyc-311',
    actor='data_engineer',
    details={'columns_added': ['new_field']}
)

audit.record_action(
    ActionType.DATA_QUALITY_GATE,
    dataset_id='nyc-311',
    details={'rule_name': 'not_null_check', 'status': 'failed'}
)

# Retrieve audit trail
trail = audit.get_audit_trail('nyc-311', limit=100)
for entry in trail:
    print(f"{entry['timestamp']}: {entry['action_type']} by {entry['actor']}")
```

**Log Output Formats**:
- JSON (for log aggregation: Loki, ELK, CloudWatch)
- Structured console output with contextual fields
- File rotation with 10MB per file, 5 file retention

## Monitoring & Alerting

### Grafana Dashboard Setup

Three pre-configured dashboards are provided:

1. **Pipeline Health Dashboard**
   - Ingestion success/error rates
   - Records processed per dataset
   - Schema violations and validation failures
   - Average ingestion duration

2. **Data Freshness Dashboard**
   - Overall SLA compliance %
   - Datasets by staleness level
   - Hours since last update per dataset
   - 24-hour SLA violation count

3. **Data Quality Dashboard**
   - Completeness, validity, uniqueness by column
   - Referential integrity metrics
   - 7-day quality trends

See [`docs/observability_dashboard.md`](observability_dashboard.md) for complete setup instructions.

### Alert Rules

**Prometheus AlertManager rules** trigger notifications:

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| `DatasetFreshnessSLAViolated` | SLA exceeded | CRITICAL | Page on-call; check ingestion pipeline |
| `FreshnessSLAComplianceLow` | Compliance < 95% | WARNING | Review SLA configuration; assess capacity |
| `HighIngestionErrorRate` | Error rate > 5% | WARNING | Check API availability; review logs |
| `SchemaViolationsDetected` | New violations | WARNING | Review schema changes; rerun validation |
| `LowDataCompleteness` | Completeness < 90% | WARNING | Identify missing columns; check source |
| `DataValidityIssues` | Validity < 95% | WARNING | Check data type conformance; validate rules |

### Slack Integration

Configure Slack webhooks for real-time alerts:

```python
from socrata_toolkit.freshness import FreshnessAlert

# Generate Slack message from alert
alert = FreshnessAlert.from_dataset_freshness(df)
slack_msg = alert.to_slack_json()

# Post to webhook
import requests
webhook_url = os.getenv('SLACK_WEBHOOK_URL')
requests.post(webhook_url, json=slack_msg)
```

## Troubleshooting

### Issue: Freshness SLA False Positives

**Symptoms**: Datasets marked stale despite recent updates

**Root Cause**: Last update timestamp is incorrect or timezone mismatch

**Resolution**:
1. Verify timestamps are ISO 8601 UTC: `datetime.utcnow()`
2. Check `expected_frequency_hours` matches actual update cadence
3. Review `sla_threshold_hours` (default 2x frequency)

**Query to diagnose**:
```sql
SELECT dataset_id, last_updated_utc, 
       NOW() - last_updated_utc AS age
FROM data_freshness_log
WHERE sla_violated = true
ORDER BY last_updated_utc DESC;
```

### Issue: Missing Metrics in Prometheus

**Symptoms**: Custom metrics not appearing in Prometheus UI

**Root Cause**: Metrics endpoint not registered or scrape config incorrect

**Resolution**:
1. Verify `/metrics` endpoint returns Prometheus format:
   ```bash
   curl http://localhost:8000/metrics
   ```
2. Check Prometheus scrape config: `http://localhost:9090/service-discovery`
3. Verify labels match expected values (e.g., `dataset_id="nyc-311"`)

### Issue: Lineage Cycle Detection

**Symptoms**: `ValueError: circular dependency` when adding edges

**Root Cause**: Transformation creates circular data flow

**Resolution**:
1. Review lineage architecture—ensure DAG structure (no cycles)
2. Break cycle by adding intermediate transformation node
3. Verify source→target mapping is unidirectional

**Example**:
```python
# ❌ Circular: B → A → B
graph.add_edge('B', 'A', [], [])
graph.add_edge('A', 'B', [], [])  # Raises ValueError

# ✅ Fixed: Add intermediate step C
graph.add_edge('B', 'C', [], [])  # B → C
graph.add_edge('C', 'A', [], [])  # C → A
```

### Issue: Audit Log Queries Slow

**Symptoms**: Audit trail retrieval takes >5 seconds

**Root Cause**: Missing indexes or large result sets

**Resolution**:
1. Verify indexes exist on `dataset_id`, `action_type`, `timestamp`
2. Limit results: `get_audit_trail(dataset_id, limit=100)`
3. Add date filter: query only recent events
4. Consider archiving old audit logs (> 90 days)

## Integration with Existing Pipelines

### Example: Instrument Ingestion Pipeline

```python
from datetime import datetime
from socrata_toolkit.client import SocrataClient
from socrata_toolkit.pipeline import run_from_rows
from socrata_toolkit.freshness import FreshnessTracker
from socrata_toolkit.metrics import PipelineMetrics, get_global_registry
from socrata_toolkit.observability import OperationalLogger, OperationalContext
from socrata_toolkit.lineage import LineageRegistry, TransformationType

logger = OperationalLogger('pipeline')
registry = get_global_registry()
pipeline_metrics = PipelineMetrics(registry=registry)
freshness_tracker = FreshnessTracker(db_dsn='postgresql://...')
lineage_registry = LineageRegistry(db_dsn='postgresql://...')

# Start operation context
with OperationalContext(operation_type='ingestion', dataset_id='nyc-311', logger=logger) as ctx:
    try:
        # Fetch data
        client = SocrataClient()
        rows = []
        start_time = datetime.utcnow()
        
        for batch in client.fetch_json('data.cityofnewyork.us', 'a2nx-4u46'):
            rows.extend(batch)
        
        duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        # Record metrics
        pipeline_metrics.record_ingestion_success('nyc-311', len(rows), duration_seconds)
        
        # Update freshness
        freshness_tracker.track_ingestion('nyc-311', datetime.utcnow(), 24)
        
        # Record lineage (source → destination)
        lineage_registry.add_edge(
            'socrata_api:nyc-311',
            'postgres:nyc_311_raw',
            source_columns=['*'],
            target_columns=['*'],
            transformation_type=TransformationType.INGESTION
        )
        
        # Log success
        logger.info(f'Ingestion complete: {len(rows)} records in {duration_seconds:.2f}s',
                   dataset_id='nyc-311',
                   operation_type='ingestion',
                   record_count=len(rows),
                   duration_seconds=duration_seconds)
        
        # Run pipeline to storage
        targets = {
            'postgres': {
                'enabled': True,
                'dsn': 'postgresql://...',
                'table': 'nyc_311_raw',
                'conflict_column': 'unique_id'
            }
        }
        result = run_from_rows(rows, targets, dry_run=False)
        logger.info('Pipeline completed', context={'upserted': result['targets']['postgres']['rows_upserted']})
        
    except Exception as e:
        pipeline_metrics.record_ingestion_error('nyc-311', 'network' if 'connection' in str(e).lower() else 'unknown')
        logger.error(f'Ingestion failed: {e}', dataset_id='nyc-311', error=str(e))
        raise
```

## Performance Considerations

- **Freshness Tracking**: In-memory storage O(1) lookup; PostgreSQL storage adds 1-2ms latency
- **Lineage Graph**: DFS upstream/downstream traversal O(V+E); caching optimizes repeated queries
- **Metrics Recording**: Negligible overhead; async export to Prometheus
- **Audit Logging**: Append-only operations; consider partitioning by date for very large tables

## Cost Estimation

| Component | Storage | Monthly Cost |
|-----------|---------|--------------|
| PostgreSQL (RDS, 50GB) | data_freshness_log, lineage, audit | ~$100 |
| Prometheus (retention 15 days) | ~50GB metrics | ~$50 |
| Loki (retention 30 days) | ~100GB logs | ~$80 |
| Grafana Cloud (3 dashboards) | Hosted | ~$25/dashboard |
| **Total** | **~250GB** | **~$330/month** |

For on-premises deployment, subtract cloud service costs; PostgreSQL and monitoring tools are open-source.

## Next Steps

1. Deploy observability stack using Docker Compose (see `docs/observability_dashboard.md`)
2. Integrate freshness tracking into nightly pipeline jobs
3. Configure alert notifications (Slack, PagerDuty, email)
4. Set SLA thresholds based on operational requirements
5. Establish audit log retention policy
6. Phase 3: Implement DAG orchestration with Airflow for scheduled monitoring jobs
