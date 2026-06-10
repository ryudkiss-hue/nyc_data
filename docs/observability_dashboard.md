# Phase 2 Observability Dashboard Specifications

Comprehensive dashboard configuration for monitoring data pipelines, freshness, and data quality using Prometheus, Grafana, and Loki.

## Overview

This document provides deployment and configuration specifications for three integrated Grafana dashboards:

1. **Pipeline Health Dashboard** - Ingestion success/failure rates, duration trends, schema violations
2. **Data Freshness Dashboard** - Dataset staleness, SLA compliance %, time-to-update distribution
3. **Data Quality Dashboard** - Completeness, validity, uniqueness, referential integrity trends

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Pipeline                          │
│  (FreshnessTracker, PipelineMetrics, DataQualityMetrics)   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
    ┌───▼───┐      ┌──▼───┐      ┌──▼────┐     ┌──▼────┐
    │ Logs  │      │Metrics│      │Audit  │     │Lineage│
    │(JSON) │      │(Prom) │      │Trails │     │(JSON) │
    └───┬───┘      └──┬───┘      └──┬────┘     └──┬────┘
        │             │             │             │
    ┌───▼──────────────▼─────────────▼─────────────▼───┐
    │      PostgreSQL (Long-term storage)              │
    │  - data_freshness_log (date partitioned)         │
    │  - column_lineage_registry                       │
    │  - audit_log (immutable append-only)             │
    └───┬──────────────────────────────────────────────┘
        │
    ┌───▼──────────┬──────────────┬──────────────┐
    │   Prometheus │   Loki       │   PostgreSQL │
    │   (metrics)  │   (logs)     │   (queries)  │
    └───┬──────────┴──────────────┴──────────────┘
        │
    ┌───▼──────────────────────────────────────────┐
    │    Grafana Dashboard Suite                   │
    │  - Pipeline Health Dashboard                 │
    │  - Data Freshness Dashboard                  │
    │  - Data Quality Dashboard                    │
    └───────────────────────────────────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- PostgreSQL 13+ (or managed service)
- Prometheus 2.30+
- Grafana 8.0+
- Loki 2.0+

## Docker Compose Setup

### Step 1: Create `docker-compose.observability.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL for long-term storage
  postgres:
    image: postgres:15-alpine
    container_name: obs-postgres
    environment:
      POSTGRES_DB: observability
      POSTGRES_USER: obs_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init_observability.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U obs_user -d observability"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    container_name: obs-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./config/alerting_rules.yml:/etc/prometheus/alerting_rules.yml
      - prometheus_data:/prometheus
    depends_on:
      - postgres

  # Loki for logs
  loki:
    image: grafana/loki:latest
    container_name: obs-loki
    command: -config.file=/etc/loki/loki-config.yml
    ports:
      - "3100:3100"
    volumes:
      - ./config/loki-config.yml:/etc/loki/loki-config.yml
      - loki_data:/loki

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: obs-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    ports:
      - "3000:3000"
    volumes:
      - ./config/grafana/provisioning:/etc/grafana/provisioning
      - ./config/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
      - loki
      - postgres

volumes:
  postgres_data:
  prometheus_data:
  loki_data:
  grafana_data:
```

### Step 2: Prometheus Configuration

**File: `config/prometheus.yml`**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'nyc-data-pipeline'
    environment: 'production'

# Alerting configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Rules for alerting
rule_files:
  - 'alerting_rules.yml'

scrape_configs:
  # Metrics from Python application via HTTP endpoint
  - job_name: 'socrata_pipeline'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # PostgreSQL metrics (if using postgres_exporter)
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
    scrape_interval: 60s
```

### Step 3: Alerting Rules

**File: `config/alerting_rules.yml`**

```yaml
groups:
  - name: freshness_alerts
    interval: 30s
    rules:
      # Alert when dataset SLA is violated
      - alert: DatasetFreshnessSLAViolated
        expr: dataset_freshness_sla_violations_total > 0
        for: 5m
        labels:
          severity: critical
          component: freshness
        annotations:
          summary: "Dataset freshness SLA violated"
          description: "{{ $labels.dataset_id }} has violated freshness SLA"

      # Alert when SLA compliance drops below threshold
      - alert: FreshnessSLAComplianceLow
        expr: dataset_freshness_sla_compliance_pct < 95
        for: 15m
        labels:
          severity: warning
          component: freshness
        annotations:
          summary: "Freshness SLA compliance below 95%"
          description: "Current SLA compliance: {{ $value }}%"

  - name: pipeline_alerts
    interval: 30s
    rules:
      # Alert on high ingestion error rate
      - alert: HighIngestionErrorRate
        expr: >
          (rate(ingestion_errors_total[5m]) /
           (rate(ingestion_records_total[5m]) + rate(ingestion_errors_total[5m])))
          > 0.05
        for: 10m
        labels:
          severity: warning
          component: pipeline
        annotations:
          summary: "High ingestion error rate"
          description: "Error rate > 5% for {{ $labels.dataset_id }}"

      # Alert on schema violations
      - alert: SchemaViolationsDetected
        expr: increase(schema_violations_total[1h]) > 0
        for: 5m
        labels:
          severity: warning
          component: pipeline
        annotations:
          summary: "Schema violations detected"
          description: "{{ $labels.dataset_id }} has schema violations"

  - name: data_quality_alerts
    interval: 30s
    rules:
      # Alert when completeness drops
      - alert: LowDataCompleteness
        expr: data_completeness_pct < 90
        for: 15m
        labels:
          severity: warning
          component: quality
        annotations:
          summary: "Low data completeness"
          description: "{{ $labels.dataset_id }}.{{ $labels.column }} completeness: {{ $value }}%"

      # Alert on validity issues
      - alert: DataValidityIssues
        expr: data_validity_pct < 95
        for: 15m
        labels:
          severity: warning
          component: quality
        annotations:
          summary: "Data validity issues"
          description: "{{ $labels.dataset_id }}.{{ $labels.column }} validity: {{ $value }}%"
```

### Step 4: Loki Configuration

**File: `config/loki-config.yml`**

```yaml
auth_enabled: false

ingester:
  chunk_idle_period: 3m
  chunk_retain_period: 1m
  max_chunk_age: 1h
  chunk_encoding: snappy

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

server:
  http_listen_port: 3100
  log_level: info

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

## Grafana Dashboards

### Dashboard 1: Pipeline Health Dashboard

**Metrics Displayed:**
- Ingestion success rate (% successful vs. failed)
- Records ingested per dataset (time series)
- Average ingestion duration per dataset
- Schema violations (count over time)
- Validation failures (count over time)
- Dataset health status indicator

**Key Panels:**

```json
{
  "dashboard": {
    "title": "Pipeline Health Dashboard",
    "panels": [
      {
        "title": "Ingestion Success Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "(rate(ingestion_records_total[5m]) / (rate(ingestion_records_total[5m]) + rate(ingestion_errors_total[5m]))) * 100"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100
          }
        }
      },
      {
        "title": "Records Ingested by Dataset",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(ingestion_records_total[5m])",
            "legendFormat": "{{ dataset_id }}"
          }
        ]
      },
      {
        "title": "Ingestion Duration (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, ingestion_duration_seconds)"
          }
        ]
      },
      {
        "title": "Schema Violations",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(schema_violations_total[24h])"
          }
        ]
      },
      {
        "title": "Validation Failures",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(validation_failures_total[24h])"
          }
        ]
      }
    ]
  }
}
```

### Dashboard 2: Data Freshness Dashboard

**Metrics Displayed:**
- SLA compliance percentage (overall)
- Datasets by staleness level (fresh, warning, critical)
- Hours since last update (per dataset)
- Time to SLA violation (remaining hours)
- Freshness trend (7-day history)
- SLA violations (24-hour count)

**Key Panels:**

```json
{
  "dashboard": {
    "title": "Data Freshness Dashboard",
    "panels": [
      {
        "title": "Overall SLA Compliance",
        "type": "gauge",
        "targets": [
          {
            "expr": "dataset_freshness_sla_compliance_pct"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "mode": "percentage",
              "steps": [
                { "color": "red", "value": 0 },
                { "color": "yellow", "value": 90 },
                { "color": "green", "value": 95 }
              ]
            }
          }
        }
      },
      {
        "title": "Dataset Freshness Status",
        "type": "piechart",
        "targets": [
          {
            "expr": "count(dataset_hours_since_update < 24)"
          }
        ]
      },
      {
        "title": "Hours Since Last Update",
        "type": "graph",
        "targets": [
          {
            "expr": "dataset_hours_since_update",
            "legendFormat": "{{ dataset_id }}"
          }
        ]
      },
      {
        "title": "SLA Violations (24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(dataset_freshness_sla_violations_total[24h])"
          }
        ]
      },
      {
        "title": "Freshness Timeline (7 days)",
        "type": "graph",
        "targets": [
          {
            "expr": "dataset_freshness_sla_compliance_pct",
            "range": "7d"
          }
        ]
      }
    ]
  }
}
```

### Dashboard 3: Data Quality Dashboard

**Metrics Displayed:**
- Completeness scorecard (% non-null by column)
- Validity scorecard (% conforming values)
- Uniqueness scorecard (% unique values)
- Referential integrity scorecard
- Quality trends (7-day history)
- Critical quality alerts

**Key Panels:**

```json
{
  "dashboard": {
    "title": "Data Quality Dashboard",
    "panels": [
      {
        "title": "Data Completeness by Column",
        "type": "graph",
        "targets": [
          {
            "expr": "data_completeness_pct",
            "legendFormat": "{{ dataset_id }}.{{ column }}"
          }
        ]
      },
      {
        "title": "Data Validity by Column",
        "type": "graph",
        "targets": [
          {
            "expr": "data_validity_pct",
            "legendFormat": "{{ dataset_id }}.{{ column }}"
          }
        ]
      },
      {
        "title": "Data Uniqueness by Column",
        "type": "table",
        "targets": [
          {
            "expr": "data_uniqueness_pct"
          }
        ]
      },
      {
        "title": "Referential Integrity",
        "type": "table",
        "targets": [
          {
            "expr": "referential_integrity_pct",
            "legendFormat": "{{ dataset_id }}.{{ fk }}"
          }
        ]
      },
      {
        "title": "Quality Trend (7 days)",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(data_completeness_pct)",
            "range": "7d"
          }
        ]
      }
    ]
  }
}
```

## Log Aggregation with Loki

### Querying Logs

**LogQL Examples:**

```logql
# Find all ingestion errors in last hour
{component="pipeline"} | json | level="ERROR" | ingestion | 1h

# Find warnings for specific dataset
{dataset_id="nyc-311"} | json | level="WARNING"

# Count logs by level
{} | json | stats count() by level

# Find slow ingestion operations
{operation_type="ingestion"} | json | duration_seconds > 5

# Audit trail for specific dataset
{dataset_id="nyc-311"} | json | action_type != ""
```

## Deployment Instructions

### 1. Create Required Directories

```bash
mkdir -p config/grafana/{provisioning,dashboards}
mkdir -p sql
mkdir -p logs
```

### 2. Start Services

```bash
docker-compose -f docker-compose.observability.yml up -d
```

### 3. Initialize PostgreSQL

Create `sql/init_observability.sql`:

```sql
-- Freshness tracking table
CREATE TABLE IF NOT EXISTS data_freshness_log (
    id BIGSERIAL PRIMARY KEY,
    dataset_id VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(512),
    last_updated_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    expected_update_frequency_hours DOUBLE PRECISION,
    sla_threshold_hours DOUBLE PRECISION,
    ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sla_violated BOOLEAN,
    days_stale DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS data_freshness_log_dataset_id_idx
ON data_freshness_log (dataset_id);

-- Column lineage registry
CREATE TABLE IF NOT EXISTS column_lineage_registry (
    id BIGSERIAL PRIMARY KEY,
    edge_id UUID NOT NULL UNIQUE,
    source_dataset_id VARCHAR(255) NOT NULL,
    target_dataset_id VARCHAR(255) NOT NULL,
    source_columns TEXT[] NOT NULL,
    target_columns TEXT[] NOT NULL,
    transformation_type VARCHAR(50),
    transformation_sql TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit log (immutable append-only)
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    operation_id UUID NOT NULL,
    actor VARCHAR(255),
    action_type VARCHAR(50) NOT NULL,
    dataset_id VARCHAR(255),
    resource_id VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    details JSONB,
    status VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS audit_log_dataset_id_idx
ON audit_log (dataset_id);
```

### 4. Configure Grafana Data Sources

1. Open Grafana at `http://localhost:3000`
2. Login (default: admin/admin)
3. Add data sources:
   - **Prometheus**: `http://prometheus:9090`
   - **Loki**: `http://loki:3100`
   - **PostgreSQL**: `host=postgres user=obs_user password=... database=observability`

### 5. Import Dashboards

Place dashboard JSON files in `config/grafana/dashboards/` and Grafana will auto-provision them.

## Integration with Python Pipeline

### Emit Metrics from Python

```python
from socrata_toolkit.metrics import get_global_registry, PipelineMetrics
from socrata_toolkit.freshness import FreshnessTracker
from socrata_toolkit.observability import OperationalLogger, OperationalContext

# Initialize
registry = get_global_registry()
pipeline_metrics = PipelineMetrics(registry=registry)
freshness_tracker = FreshnessTracker(db_dsn='postgresql://...')
logger = OperationalLogger(__name__)

# Instrument pipeline
with OperationalContext(operation_type='ingestion', dataset_id='nyc-311', logger=logger) as ctx:
    try:
        records = ingest_dataset('nyc-311')
        pipeline_metrics.record_ingestion_success('nyc-311', len(records), elapsed_time)
        freshness_tracker.track_ingestion('nyc-311', datetime.utcnow(), 24)
        logger.info(f"Ingestion complete", dataset_id='nyc-311', record_count=len(records))
    except Exception as e:
        pipeline_metrics.record_ingestion_error('nyc-311', 'network')
        logger.error(f"Ingestion failed: {e}", dataset_id='nyc-311', error=str(e))
```

### Export Metrics Endpoint

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

## Maintenance

### Retention Policies

- **Prometheus**: 15 days (configurable in `prometheus.yml`)
- **Loki**: 30 days (configurable in `loki-config.yml`)
- **PostgreSQL**: 90 days for freshness log (implement via retention jobs)

### Backup

```bash
# Backup PostgreSQL
docker exec obs-postgres pg_dump -U obs_user observability > backup.sql

# Backup Grafana dashboards
docker exec obs-grafana grafana-cli admin export-dashboard > dashboards.json
```

## Troubleshooting

### Prometheus not scraping metrics

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check scrape errors
curl http://localhost:9090/api/v1/targets?state=any
```

### Loki log ingestion issues

```bash
# Check Loki status
curl http://localhost:3100/ready

# View Loki logs
docker logs obs-loki
```

### Grafana dashboard not showing data

1. Verify data source connectivity
2. Test PromQL query in Prometheus UI
3. Check panel time range matches data availability
4. Ensure metric labels match your configuration

## Next Steps

- Configure PagerDuty/Slack for alert notifications
- Implement custom dashboards for specific use cases
- Set up Prometheus AlertManager webhook integration
- Configure multi-environment dashboards (dev/staging/prod)
