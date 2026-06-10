# NYC Data Engineering - Observability Stack

Comprehensive observability for production data pipelines with structured logging, metrics collection, distributed tracing, and SLA tracking.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Getting Started](#getting-started)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Integration](#integration)
8. [Troubleshooting](#troubleshooting)

## Overview

The observability stack provides production-grade monitoring for the NYC Data Engineering system across:

- **Structured Logging**: JSON-formatted logs with correlation IDs for request tracing
- **Metrics Collection**: Prometheus-compatible metrics (counters, gauges, histograms, summaries)
- **Distributed Tracing**: OpenTelemetry-compatible span tracking across service boundaries
- **Health Checks**: Readiness and liveness probes for all major components
- **SLA Tracking**: Automatic violation detection and alerting on SLA breaches

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────┐
│      Application Code (no changes required)         │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│    ObservabilityManager (singleton coordinator)     │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Logging     │  │  Metrics     │  │ Tracing    │ │
│  │  (JSON)      │  │  (Prometheus)│  │ (OTel)     │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │  Health      │  │  SLA         │                 │
│  │  Checks      │  │  Tracking    │                 │
│  └──────────────┘  └──────────────┘                 │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│       PostgreSQL Storage & Persistence              │
├─────────────────────────────────────────────────────┤
│ • observability_logs (full-text searchable)         │
│ • observability_metrics_hourly (aggregated)         │
│ • observability_traces (span events)                │
│ • observability_sla_violations (history)            │
│ • observability_health_checks (historical)          │
└─────────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    ┌────────┐   ┌──────────┐   ┌─────────┐
    │Grafana │   │  Jaeger  │   │ Kibana  │
    │(metrics)│  │(tracing) │   │ (logs)  │
    └────────┘   └──────────┘   └─────────┘
```

### Component Responsibilities

| Component | Responsibility | Export Formats |
|-----------|-----------------|-----------------|
| **StructuredLogger** | JSON-formatted log output with correlation IDs | JSON, JSONL |
| **LogContext** | Thread-local context propagation | N/A |
| **MetricsCollector** | Counter, gauge, histogram, summary metrics | Prometheus, JSON, CSV |
| **TracingContext** | Span creation and distributed tracing | Jaeger JSON, OTLP |
| **HealthChecker** | Component health status and readiness probes | JSON |
| **SLATracker** | SLA definitions and violation detection | YAML, JSON |
| **ObservabilityManager** | Central coordination and initialization | N/A |

## Components

### 1. Structured Logging

Provides JSON-formatted log output with automatic correlation ID tracking.

**Module**: `socrata_toolkit.observability_logging`

**Key Classes**:
- `StructuredLogger`: Main logger interface
- `LogContext`: Thread-local context manager
- `LogAggregator`: In-memory and file storage
- `CircularLogBuffer`: Thread-safe circular buffer

**Features**:
- Automatic correlation ID injection
- JSON output format
- Full-text search capability
- Daily log rotation
- Circular buffer (default 10,000 logs)

### 2. Metrics Collection

Thread-safe metrics collection with Prometheus export.

**Module**: `socrata_toolkit.observability_metrics`

**Metric Types**:
- **Counter**: Monotonically increasing values (records processed)
- **Gauge**: Current values (active tasks, pool size)
- **Histogram**: Distribution with percentiles (latency)
- **Summary**: Percentile statistics (query times)

**Features**:
- Per-label metric tracking
- Percentile calculations (p50, p95, p99)
- Multiple export formats
- Thread-safe operations

### 3. Distributed Tracing

OpenTelemetry-compatible tracing with span management.

**Module**: `socrata_toolkit.observability_tracing`

**Key Classes**:
- `TracingContext`: Central trace management
- `Span`: Individual operation tracking
- `SpanEvent`: Milestone events within spans
- `ContextPropagator`: W3C and B3 header handling

**Features**:
- Span nesting and parent-child relationships
- W3C traceparent header support
- B3 propagation for message systems
- Jaeger JSON export

### 4. Health Checks

Readiness and liveness probes for all components.

**Module**: `socrata_toolkit.observability_health`

**Check Types**:
- Database connectivity (PostgreSQL)
- File system writability
- Disk space availability
- Memory usage
- CPU utilization
- Schema registry availability
- Lineage system health

**Statuses**:
- `HEALTHY`: All checks pass
- `DEGRADED`: Non-critical checks fail
- `UNHEALTHY`: Critical checks fail

### 5. SLA Tracking

Service Level Agreement monitoring with automatic violation detection.

**Module**: `socrata_toolkit.observability_sla`

**Key Classes**:
- `SLADefinition`: SLA specification
- `SLATracker`: SLA management and evaluation
- `SLAViolation`: Breach records

**Features**:
- Metric-based SLA targets
- Time window evaluation (5m, 1h, 1d)
- Severity levels (CRITICAL, HIGH, MEDIUM, LOW)
- Alert callbacks
- Compliance reporting

## Getting Started

### Installation

The observability stack is included in the main package. Install dependencies:

```bash
pip install -r requirements.txt
```

Key dependencies:
- `psycopg` (PostgreSQL)
- `pyyaml` (SLA configuration)
- `psutil` (System metrics)

### Quick Start

```python
from socrata_toolkit.observability_integration import get_observability_manager

# Initialize observability
obs = get_observability_manager()
obs.initialize()

# Get logger
logger = obs.get_logger(__name__)
logger.info('Application started')

# Get metrics
metrics = obs.get_metrics()
metrics.counter('startup_count', 1)

# Check health
health = obs.health_status()
print(health)
```

### Minimal Setup

```python
from socrata_toolkit.observability_logging import StructuredLogger
from socrata_toolkit.observability_metrics import MetricsCollector
from socrata_toolkit.observability_tracing import TracingContext

# Logging
logger = StructuredLogger(__name__)
logger.info('Hello world')

# Metrics
metrics = MetricsCollector()
metrics.counter('events', 1)

# Tracing
tracer = TracingContext()
span = tracer.start_span('operation')
tracer.end_span(span.span_id)
```

## Usage Examples

### Structured Logging with Correlation IDs

```python
from socrata_toolkit.observability_logging import StructuredLogger, LogContext

logger = StructuredLogger(__name__)

# Automatic correlation ID
with LogContext(dataset_id='nyc-311', borough='Manhattan'):
    logger.info('Processing dataset', extra={'record_count': 1500})
    # Logs will include: correlation_id, dataset_id, borough
```

### Recording Metrics

```python
metrics = obs.get_metrics()

# Counter
metrics.counter('records_ingested', 100)
metrics.counter('records_validated', 95)

# Gauge
metrics.gauge('active_pipelines', 3)
metrics.gauge_inc('queue_depth')

# Histogram
metrics.histogram('latency_ms', 234.5)
metrics.histogram('validation_time_ms', 45.2)

# Summary
metrics.summary('query_execution_ms', 156.3)

# Export
prometheus_text = metrics.export_prometheus()
json_data = metrics.export_json()
```

### Distributed Tracing

```python
from socrata_toolkit.observability_tracing import traced_operation

# Decorator approach
@traced_operation(name='process_records')
def process_records(dataset_id):
    # Automatic span creation and timing
    pass

# Manual approach
tracer = obs.get_tracing_context()
span = tracer.start_span('ingestion', attributes={'dataset': 'nyc-311'})
try:
    # Do work
    tracer.add_event(span.span_id, 'records_loaded', {'count': 1000})
    tracer.end_span(span.span_id, status='ok')
except Exception as e:
    tracer.end_span(span.span_id, status='error', error_message=str(e))
```

### Health Checks

```python
# Get health status
health = obs.health_status()
print(f"Overall status: {health['status']}")
for component in health['components']:
    print(f"  {component['name']}: {component['status']}")

# Readiness probe (for Kubernetes, etc.)
readiness = obs.readiness_status()
if readiness['ready']:
    # Accept traffic
    pass

# Liveness probe
liveness = obs.liveness_status()
# Always returns True if application is running
```

### SLA Tracking

```python
# Configure SLAs
obs.configure_sla('ingestion_latency_p99', target=5000, severity='CRITICAL')
obs.configure_sla('schema_compliance', target=0.95, severity='MEDIUM')

# Record metrics
sla = obs.get_sla_tracker()
sla.record_metric('ingestion_latency_p99', 4500)

# Evaluate
report = sla.evaluate()
print(f"Compliance: {report.compliance_percent}%")
for violation in report.violations:
    print(f"  Violation: {violation.sla_name}")

# Alert on violations
def alert_handler(violation):
    print(f"SLA BREACH: {violation.sla_name}")

sla.register_alert_callback(alert_handler)
```

## Configuration

### Environment Variables

```bash
# Logging
LOG_LEVEL=INFO                           # DEBUG, INFO, WARN, ERROR, CRITICAL
OBSERVABILITY_LOG_DIR=./logs             # Log directory

# Metrics
OBSERVABILITY_METRICS_ENABLED=true       # Enable/disable metrics
OBSERVABILITY_METRICS_BUFFER_SIZE=10000  # In-memory buffer size

# Tracing
OBSERVABILITY_TRACING_ENABLED=true       # Enable/disable tracing
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # Jaeger/Tempo endpoint

# Health Checks
OBSERVABILITY_HEALTH_ENABLED=true        # Enable/disable health checks
OBSERVABILITY_HEALTH_CHECK_INTERVAL=30   # Seconds between checks

# SLAs
SLA_DEFINITIONS_FILE=config/sla_definitions.yaml  # SLA config file
```

### SLA Configuration File

See `config/sla_definitions.yaml` for complete example.

```yaml
slas:
  - metric_name: ingestion_latency_p99
    target: 5000        # milliseconds
    window: 5m          # 5m, 1h, 1d
    severity: CRITICAL  # CRITICAL, HIGH, MEDIUM, LOW
    channels:           # Notification channels
      - pagerduty
      - slack
    description: "P99 latency must be < 5s"
```

## Integration

### With Existing Code

The observability stack is **non-breaking** and purely additive.

1. **No changes required** to existing code
2. Optional decorators for automatic instrumentation
3. Optional context managers for correlation tracking

### Integrating with Ingestion

```python
from socrata_toolkit.observability_integration import get_observability_manager

class DataIngestion:
    def __init__(self):
        self.obs = get_observability_manager()
        self.logger = self.obs.get_logger(__name__)
        self.metrics = self.obs.get_metrics()

    def ingest(self, dataset_id, records):
        with self.obs.create_log_context(dataset_id=dataset_id):
            self.logger.info('Ingestion started')
            
            # Record metrics
            self.metrics.counter('ingestion_started', 1)
            
            # Track latency
            start = time.time()
            try:
                # Process records
                processed = len(records)
                self.metrics.counter('records_processed', processed)
            finally:
                duration = (time.time() - start) * 1000
                self.metrics.histogram('ingestion_latency_ms', duration)
```

### With Schema Registry (Week 1)

```python
from socrata_toolkit.schema_registry import SchemaRegistry

registry = SchemaRegistry()
metrics = obs.get_metrics()

# Track schema validation
schema = registry.get_schema(dataset_id)
violations = registry.validate(data, schema)

metrics.counter('schema_validations', 1)
metrics.counter('schema_violations', len(violations))
compliance_rate = 1 - (len(violations) / len(data))
metrics.gauge('schema_compliance', compliance_rate)
```

### With Material Standards (Week 2)

```python
from socrata_toolkit.material_compliance import MaterialCompliance

compliance = MaterialCompliance()
metrics = obs.get_metrics()

# Track material compliance
issues = compliance.check_ada_compliance(sidewalk_data)

metrics.counter('ada_checks', 1)
metrics.counter('ada_violations', len(issues))
compliance_pct = 1 - (len(issues) / len(sidewalk_data))
metrics.gauge('ada_compliance_rate', compliance_pct)
```

### With Lineage Tracking (Week 3)

```python
from socrata_toolkit.lineage_tracking import LineageTracker

tracker = LineageTracker()
tracer = obs.get_tracing_context()

# Trace lineage operations
span = tracer.start_span('lineage_execution')
try:
    lineage = tracker.track_transformation(source, target)
    tracer.add_event(span.span_id, 'lineage_computed', {
        'nodes': len(lineage.nodes)
    })
finally:
    tracer.end_span(span.span_id)
```

## Troubleshooting

### Logs Not Appearing

1. Check `LOG_LEVEL` environment variable
2. Verify `OBSERVABILITY_LOG_DIR` is writable
3. Check circular buffer isn't full: `obs.get_log_aggregator().buffer.size()`

### Metrics Not Exported

1. Verify `OBSERVABILITY_METRICS_ENABLED=true`
2. Check metrics are being recorded: `metrics.summary_dict()`
3. Verify Prometheus scrape config points to correct endpoint

### SLA Violations Not Detected

1. Verify SLA is configured: `sla.summary_dict()`
2. Check metrics are being recorded: `sla._metrics[metric_name]`
3. Verify SLA window and target are correct

### Health Checks Failing

1. Check individual component statuses
2. Run manual health check: `obs.health_status()`
3. Review `observability_health_checks` table in PostgreSQL

## Advanced Topics

### Custom Health Checks

```python
from socrata_toolkit.observability_health import ComponentHealth

def check_custom_service() -> ComponentHealth:
    try:
        # Check service
        response = requests.get('http://service/health')
        return ComponentHealth(
            name='custom_service',
            status='HEALTHY' if response.status_code == 200 else 'UNHEALTHY',
            duration_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        return ComponentHealth(
            name='custom_service',
            status='UNHEALTHY',
            message=str(e),
        )

obs.get_health_checker().register_check('custom_service', check_custom_service)
```

### Custom Metrics Export

```python
# Export to CSV
metrics.export_csv(Path('metrics.csv'))

# Export to JSON
json_data = json.loads(metrics.export_json())

# Create custom aggregations
summary = metrics.summary_dict()
```

### Querying Logs

```python
# By level
errors = obs.query_logs(level='ERROR')

# By correlation_id
related_logs = obs.query_logs(correlation_id='req-123')

# By context fields
dataset_logs = obs.query_logs(dataset_id='nyc-311')

# By time range
recent = obs.query_logs(
    start_time='2025-01-01T00:00:00Z',
    end_time='2025-01-01T01:00:00Z'
)
```

## Performance Considerations

- **Logging overhead**: < 1ms per log message
- **Metrics overhead**: < 0.5ms per metric
- **Tracing overhead**: < 1ms per span
- **Total observability overhead**: < 5% with full stack enabled

All overhead is optimized with:
- Thread-local context variables
- Lock-free data structures where possible
- Circular buffers to prevent memory growth
- Async export to remote backends

## Next Steps

1. Load SLA configuration: `obs.load_sla_config(Path('config/sla_definitions.yaml'))`
2. Setup Prometheus scrape config: See `config/prometheus.yml`
3. Deploy PostgreSQL migrations: `sql/005_observability_tables.sql`
4. Configure alerting in AlertManager
5. Setup Grafana dashboards (templates in `socrata_toolkit/observability_dashboards.py`)
