# Phase 3 Integration Guide: Airflow Orchestration of Phase 1 & 2

## Overview

Phase 3 integrates Phase 1 (data validation, KPI computation) and Phase 2 (freshness tracking, metrics, observability) into a production-grade Airflow orchestration layer for the NYC Sidewalk Incident Management system.

This guide explains:
1. How Phase 3 components integrate with Phase 1/2
2. Data flow through the complete pipeline
3. How to use Phase 1/2 modules in Airflow operators
4. Architecture diagrams and integration points

---

## Phase Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PHASE 3: AIRFLOW ORCHESTRATION               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────┐  │
│  │ incident_ingestion  │  │  repair_scheduling  │  │ kpi_        │  │
│  │ (DAG)               │  │  (DAG)              │  │ materialization
│  │                     │  │                     │  │ (DAG)      │  │
│  │ 6-hour schedule     │  │ Daily schedule      │  │ Hourly     │  │
│  └─────────────────────┘  └─────────────────────┘  └────────────┘  │
│           ↓                      ↓                       ↓           │
├─────────────────────────────────────────────────────────────────────┤
│           PHASE 1: DATA VALIDATION & KPI COMPUTATION               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ socrata_toolkit.validation                                   │  │
│  │ - ValidationRuleSet: Define validation rules               │  │
│  │ - validate_data(): Apply rules to DataFrames              │  │
│  │ - Data quality gates                                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ socrata_toolkit.schema_registry                              │  │
│  │ - SchemaRegistry: Manage data schemas                       │  │
│  │ - is_compliant(): Check schema compliance                  │  │
│  │ - Version tracking and evolution                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ socrata_toolkit.dot_sidewalk (Phase 1)                       │  │
│  │ - MaterialAwareSidewalkKPI: Compute incident KPIs           │  │
│  │   * response_time (mean, median, percentiles)              │  │
│  │   * repair_rate_by_material                                │  │
│  │   * incident_density_by_location                           │  │
│  │   * seasonal_trends                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│         PHASE 2: FRESHNESS TRACKING & METRICS                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ socrata_toolkit.freshness                                    │  │
│  │ - FreshnessTracker: Track data freshness                    │  │
│  │ - Update freshness metadata after pipeline steps            │  │
│  │ - SLA violation detection                                   │  │
│  │ - Checkpoint tracking for incremental processing           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ socrata_toolkit.metrics                                      │  │
│  │ - MetricsEmitter: Export Prometheus metrics                 │  │
│  │ - Counter: incidents_processed, records_validated          │  │
│  │ - Histogram: pipeline_duration, data_size                  │  │
│  │ - Gauge: queue_size, active_tasks                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ socrata_toolkit.lineage                                      │  │
│  │ - LineageTracker: Track data lineage                        │  │
│  │ - Record upstream (API), transformations, downstream       │  │
│  │ - Audit trail for compliance                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ socrata_toolkit.observability                                │  │
│  │ - OperationalLogger: Structured logging                     │  │
│  │ - JSON log events with context                             │  │
│  │ - Integration with monitoring dashboards                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
         ↓                    ↓                      ↓
   ┌─────────────────────────────────────────────────────────────────┐
   │                    POSTGRESQL DATABASE                           │
   │  (incident, repair, checkpoint, kpi_materialization tables)     │
   └─────────────────────────────────────────────────────────────────┘
         ↓
   ┌─────────────────────────────────────────────────────────────────┐
   │                    PHASE 4: API LAYER                            │
   │  (Queries materialized KPIs from database)                      │
   └─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Incident → Repair → KPI → API

### Step 1: Incident Ingestion (incident_ingestion DAG)

```
Socrata API → Fetch → Validate → Transform → UPSERT → Update Freshness
    ↓           ↓         ↓         ↓        ↓              ↓
  6 hours    fetch_     validate_  transform  upsert_    update_
  schedule   incidents   data       data      incidents  freshness
```

**Operators & Phase 1/2 Integration:**

```python
# Task: fetch_incidents
from airflow.operators.python import PythonOperator
from socrata_toolkit.client import SocrataClient

def fetch_incidents(ti):
    """Fetch new incidents from Socrata API"""
    client = SocrataClient()
    incidents = client.query(
        dataset_id='a2nx-4u46',
        where="created_date > '2026-05-10'"
    )
    return incidents

# Task: validate_data
from socrata_toolkit.validation import ValidationRuleSet

def validate_incident_data(ti):
    """Validate incidents using Phase 1 rules"""
    incidents = ti.xcom_pull(task_ids='fetch_incidents')
    
    validator = ValidationRuleSet(name='incident_validation')
    validator.add_rule('non_null', {'columns': ['incident_id', 'date', 'location']})
    validator.add_rule('type_check', {
        'incident_id': 'string',
        'date': 'datetime',
        'severity': 'int'
    })
    
    result = validator.validate(incidents)
    if not result.is_valid:
        raise ValueError(f"Validation failed: {result.errors}")
    
    return incidents  # Return valid records

# Task: upsert_incidents
from socrata_toolkit.db_helpers import PostgresHelper

def upsert_incidents(ti):
    """Load incidents into database with checkpoint tracking"""
    incidents = ti.xcom_pull(task_ids='validate_data')
    
    db = PostgresHelper('postgres_warehouse')
    
    # UPSERT: Insert new, update existing (idempotent)
    db.upsert(
        table='incident',
        records=incidents,
        key_columns=['incident_id']
    )
    
    return {"loaded": len(incidents)}

# Task: update_freshness
from socrata_toolkit.freshness import FreshnessTracker

def update_incident_freshness(ti):
    """Update freshness metadata after ingestion"""
    load_result = ti.xcom_pull(task_ids='upsert_incidents')
    
    tracker = FreshnessTracker(data_source='socrata_incidents')
    tracker.update_freshness(
        last_updated=datetime.utcnow(),
        record_count=load_result['loaded'],
        metadata={'dataset_id': 'a2nx-4u46', 'dag_id': 'incident_ingestion'}
    )
```

### Step 2: Repair Scheduling (repair_scheduling DAG)

```
Wait for Incidents → Load → Optimize → Publish Schedule → Update Freshness
       ↓              ↓        ↓            ↓                  ↓
  ExternalTask    load_    optimize_    publish_           update_
  Sensor         incidents schedule     schedule          freshness
```

**Operators & Phase 1/2 Integration:**

```python
# Task: check_incidents_available
from airflow.sensors.external_task import ExternalTaskSensor

sensor = ExternalTaskSensor(
    task_id='check_incidents_available',
    external_dag_id='incident_ingestion',
    external_task_id='update_freshness',
    poke_interval=300,  # Check every 5 minutes
    timeout=3600,       # Wait max 1 hour
    dag=dag,
)

# Task: optimize_schedule
from socrata_toolkit.spatial import GeoProcessor
from socrata_toolkit.analysis import SchedulingOptimizer

def optimize_repair_schedule(ti):
    """Optimize repair scheduling using Phase 1 analysis"""
    
    # Load incident and repair data
    db = PostgresHelper('postgres_warehouse')
    incidents = db.query("SELECT * FROM incident WHERE status='open'")
    repairs = db.query("SELECT * FROM repair_history LIMIT 1000")
    
    # Apply spatial analysis (Phase 1)
    geo = GeoProcessor()
    clustered = geo.cluster_incidents(incidents, max_distance_km=0.5)
    
    # Optimize scheduling
    optimizer = SchedulingOptimizer(max_workers=50)
    schedule = optimizer.optimize(
        incidents=clustered,
        repairs=repairs,
        constraints={'daily_capacity': 100}
    )
    
    return schedule

# Task: publish_schedule
from socrata_toolkit.metrics import MetricsEmitter

def publish_schedule(ti):
    """Save optimized schedule and emit metrics"""
    schedule = ti.xcom_pull(task_ids='optimize_schedule')
    
    db = PostgresHelper('postgres_warehouse')
    db.insert('repair_schedule', schedule)
    
    # Emit metrics (Phase 2)
    emitter = MetricsEmitter(job_name='repair_scheduling')
    emitter.counter('repairs_scheduled', len(schedule))
    emitter.histogram('avg_distance_to_incident', 0.75)
```

### Step 3: KPI Materialization (kpi_materialization DAG)

```
Get Incidents → Get Repairs → Compute KPIs → Publish to DB → Emit Metrics
       ↓            ↓              ↓                ↓             ↓
   SQL Query    SQL Query    Phase 1 KPI       UPSERT       Counter,
                             Computation       materialization Histogram
```

**Operators & Phase 1/2 Integration:**

```python
# Task: compute_sidewalk_kpi
from socrata_toolkit.dot_sidewalk import MaterialAwareSidewalkKPI

def compute_sidewalk_kpi(ti):
    """Compute KPIs using Phase 1 module"""
    
    # Get data
    db = PostgresHelper('postgres_warehouse')
    incidents = db.query("SELECT * FROM incident")
    repairs = db.query("SELECT * FROM repair")
    
    # Compute KPIs (Phase 1)
    kpi = MaterialAwareSidewalkKPI(
        incidents_df=incidents,
        repairs_df=repairs,
        jurisdiction='NYC'
    )
    
    results = kpi.compute()  # Returns:
    # {
    #   'response_time_mean': 12.5,  # days
    #   'response_time_median': 10.2,
    #   'response_time_p95': 45.0,
    #   'repair_rate_by_material': {'concrete': 0.85, 'asphalt': 0.78},
    #   'incident_density_by_borough': {...},
    #   'seasonal_trends': {...}
    # }
    
    return results

# Task: publish_kpi
from socrata_toolkit.lineage import LineageTracker

def publish_kpi_materialization(ti):
    """Save KPIs to materialization table for API queries"""
    results = ti.xcom_pull(task_ids='compute_sidewalk_kpi')
    
    db = PostgresHelper('postgres_warehouse')
    
    # Upsert KPI results
    db.upsert(
        table='kpi_materialization',
        records=[{
            'computed_at': datetime.utcnow(),
            'metric_name': 'response_time_mean',
            'metric_value': results['response_time_mean'],
            'metadata': results
        }],
        key_columns=['computed_at', 'metric_name']
    )
    
    # Track lineage (Phase 2)
    tracker = LineageTracker()
    tracker.add_transformation(
        name='kpi_computation',
        input_records=len(results),
        output_records=len(results),
        operation='kpi_materialization'
    )
    
    # Emit metrics
    emitter = MetricsEmitter(job_name='kpi_materialization')
    emitter.gauge('response_time_mean_days', results['response_time_mean'])
    emitter.gauge('repair_rate', results.get('repair_rate', 0))
```

---

## Integration Points: Phase 1 Modules

### ValidationRuleSet (Validation)

**Used in**: incident_ingestion → validate_data task

```python
from socrata_toolkit.validation import ValidationRuleSet

validator = ValidationRuleSet(name='incident_validation')

# Define validation rules
validator.add_rule('non_null', {
    'columns': ['incident_id', 'date', 'location', 'status']
})

validator.add_rule('type_check', {
    'incident_id': 'int64',
    'date': 'datetime64[ns]',
    'location': 'object',  # GeoJSON
    'status': 'category'
})

validator.add_rule('range_check', {
    'severity': {'min': 1, 'max': 5}
})

# Apply validation
result = validator.validate(incidents_dataframe)
print(f"Valid: {result.valid_count}, Invalid: {result.invalid_count}")
```

### SchemaRegistry (Schema Management)

**Used in**: All DAGs to ensure data schema compliance

```python
from socrata_toolkit.schema_registry import SchemaRegistry

registry = SchemaRegistry()

# Get schema for incident data
schema = registry.get_schema('incident_data')

# Check compliance
if not registry.is_compliant(data, schema):
    raise ValueError("Data does not match expected schema")

# Track schema changes
schema_version = schema.version  # e.g., "1.2.3"
```

### MaterialAwareSidewalkKPI (KPI Computation)

**Used in**: kpi_materialization → compute_sidewalk_kpi task

```python
from socrata_toolkit.dot_sidewalk import MaterialAwareSidewalkKPI

kpi = MaterialAwareSidewalkKPI(
    incidents_df=incidents,
    repairs_df=repairs,
    jurisdiction='NYC'
)

results = kpi.compute()
# Results include:
# - response_time (mean, median, percentiles)
# - repair_rate_by_material (concrete, asphalt, etc)
# - incident_density_by_location (hot spots)
# - seasonal_trends (monthly patterns)
```

---

## Integration Points: Phase 2 Modules

### FreshnessTracker (Freshness Tracking)

**Used in**: All DAGs' final task to track data freshness

```python
from socrata_toolkit.freshness import FreshnessTracker

tracker = FreshnessTracker(
    data_source='socrata_incidents',
    freshness_threshold_hours=24
)

# Update freshness after data load
tracker.update_freshness(
    last_updated=datetime.utcnow(),
    record_count=5000,
    metadata={'source': 'Socrata API', 'dataset_id': 'a2nx-4u46'}
)

# Check if data is fresh
is_fresh = tracker.is_fresh()  # True if last update < 24 hours ago

# Get freshness status
status = tracker.get_freshness_status()
# {'source': 'socrata_incidents', 'last_updated': ..., 'is_fresh': True}
```

### MetricsEmitter (Prometheus Metrics)

**Used in**: All DAGs to emit metrics for monitoring

```python
from socrata_toolkit.metrics import MetricsEmitter

emitter = MetricsEmitter(job_name='incident_ingestion')

# Counters: increment for events
emitter.counter('incidents_fetched', 5000)
emitter.counter('incidents_valid', 4950)
emitter.counter('incidents_rejected', 50)

# Histograms: measure distributions
emitter.histogram('fetch_duration_seconds', 45)
emitter.histogram('validation_duration_seconds', 30)

# Gauges: current state
emitter.gauge('api_quota_remaining', 49500)
emitter.gauge('queue_depth', 10)
```

### LineageTracker (Data Lineage)

**Used in**: All DAGs to track data transformations

```python
from socrata_toolkit.lineage import LineageTracker

tracker = LineageTracker()

# Record upstream source
tracker.add_upstream_source(
    name='socrata_incidents',
    source_type='api',
    dataset_id='a2nx-4u46'
)

# Record transformation
tracker.add_transformation(
    name='validate_incidents',
    input_records=5000,
    output_records=4950,
    operation='schema_validation'
)

# Record downstream target
tracker.add_downstream_target(
    name='incident_table',
    target_type='postgresql',
    table='incident'
)
```

### OperationalLogger (Structured Logging)

**Used in**: All DAGs and custom operators for structured logging

```python
from socrata_toolkit.observability import OperationalLogger

logger = OperationalLogger(__name__)

# Log events with context
logger.log_event(
    event_name='incident_ingestion_started',
    event_type='pipeline_execution',
    dag_id='incident_ingestion',
    metadata={
        'dataset_id': 'a2nx-4u46',
        'expected_records': 5000,
        'execution_date': '2026-05-10T06:00:00Z'
    }
)

# Log errors with exception handling
try:
    fetch_incidents()
except Exception as e:
    logger.log_event(
        event_name='fetch_failed',
        event_type='error',
        metadata={'error': str(e), 'retry_count': 2}
    )
```

---

## End-to-End Trace: From API to Query

Tracing a single incident record through the complete pipeline:

```
┌─ 2026-05-10 06:00:00 UTC ─────────────────────────────────────────┐
│ INCIDENT_INGESTION DAG RUNS                                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 1. fetch_incidents                                                  │
│    └─> Socrata API returns: incident_id=12345, date=2026-05-10    │
│    └─> OperationalLogger: "Fetched 5000 incidents"                │
│    └─> XCom: {"incident_id": 12345, ...}                          │
│                                                                     │
│ 2. validate_data (uses Phase 1)                                     │
│    └─> ValidationRuleSet.validate() checks schema                 │
│    └─> Record passes: non_null, type_check, range_check          │
│    └─> MetricsEmitter: counter('incidents_valid', 1)              │
│    └─> OperationalLogger: "Validation passed"                     │
│                                                                     │
│ 3. upsert_incidents                                                │
│    └─> PostgreSQL: INSERT incident (id=12345) ON CONFLICT UPDATE  │
│    └─> LineageTracker: records transformation                     │
│    └─> OperationalLogger: "Loaded 5000 incidents"                │
│                                                                     │
│ 4. update_freshness (uses Phase 2)                                 │
│    └─> FreshnessTracker.update_freshness()                        │
│    └─> Sets last_updated=2026-05-10T06:30:00Z                    │
│    └─> MetricsEmitter: gauge('data_freshness_hours', 0.5)        │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                              ↓
              PostgreSQL: incident.id=12345 exists
                              ↓
┌─ 2026-05-11 02:00:00 UTC ─────────────────────────────────────────┐
│ REPAIR_SCHEDULING DAG RUNS                                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 1. check_incidents_available                                       │
│    └─> ExternalTaskSensor waits for incident_ingestion done       │
│    └─> Returns SUCCESS after 5-minute check                       │
│                                                                     │
│ 2. optimize_schedule (uses Phase 1)                                 │
│    └─> Loads incident #12345 from PostgreSQL                      │
│    └─> GeoProcessor clusters nearby incidents                      │
│    └─> SchedulingOptimizer computes optimal repair sequence       │
│    └─> Assigns priority, crew, time window                        │
│    └─> OperationalLogger: "Scheduled 50 repairs"                  │
│                                                                     │
│ 3. publish_schedule                                                │
│    └─> INSERT repair_schedule (incident_id=12345, crew=123)       │
│    └─> MetricsEmitter: counter('repairs_scheduled', 50)           │
│    └─> FreshnessTracker: schedule freshness updated               │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                              ↓
        PostgreSQL: repair_schedule.incident_id=12345 exists
                              ↓
┌─ 2026-05-11 03:00:00 UTC ──────────────────────────────────────────┐
│ KPI_MATERIALIZATION DAG RUNS (Every Hour)                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 1. compute_sidewalk_kpi (uses Phase 1)                              │
│    └─> Loads all incidents from PostgreSQL (includes #12345)      │
│    └─> Loads all repairs from PostgreSQL                          │
│    └─> MaterialAwareSidewalkKPI.compute()                         │
│       ├─> response_time_mean = 1.5 days (includes #12345)        │
│       ├─> repair_rate = 0.92                                      │
│       └─> incident_density = 2.3 per block                        │
│                                                                     │
│ 2. publish_kpi_materialization                                     │
│    └─> UPSERT kpi_materialization:                                │
│        - computed_at = 2026-05-11T03:00:00Z                       │
│        - response_time_mean = 1.5                                 │
│        - material_breakdown = {concrete: 0.88, asphalt: 0.91}     │
│    └─> LineageTracker.add_transformation()                        │
│    └─> MetricsEmitter: gauge('response_time_mean', 1.5)          │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                              ↓
        PostgreSQL: kpi_materialization with incident #12345 data
                              ↓
┌─ PHASE 4: API LAYER ───────────────────────────────────────────────┐
│ Query: GET /api/v1/incidents/{id}                                  │
│ Returns:                                                            │
│ {                                                                   │
│   "incident_id": 12345,                                            │
│   "created_date": "2026-05-10",                                    │
│   "status": "scheduled_for_repair",                                │
│   "kpi_response_time_mean_days": 1.5,  ← FROM KPI_MATERIALIZATION │
│   "kpi_repair_rate": 0.92,                                         │
│   "assigned_crew": 123,                                            │
│   "estimated_repair_date": "2026-05-13"                           │
│ }                                                                   │
└────────────────────────────────────────────────────────────────────┘

Timeline: API call → Incident load → KPI computation → API response
          (Days 1-3)    (Day 1)        (Every hour)     (Real-time)
```

---

## Monitoring & Observability Integration

### Prometheus Metrics Dashboard

Key metrics emitted by Phase 3 (Phase 2 integration):

```
# Incident Ingestion Metrics
incident_ingestion:incidents_fetched{status="success"} 5000
incident_ingestion:incidents_valid{status="success"} 4950
incident_ingestion:incidents_rejected{status="failed"} 50
incident_ingestion:fetch_duration_seconds 45
incident_ingestion:validation_duration_seconds 30
incident_ingestion:data_freshness_hours 0.5

# Repair Scheduling Metrics
repair_scheduling:repairs_scheduled{status="success"} 50
repair_scheduling:optimization_duration_seconds 120
repair_scheduling:avg_distance_to_incident_km 0.75

# KPI Materialization Metrics
kpi_materialization:response_time_mean_days 1.5
kpi_materialization:repair_rate 0.92
kpi_materialization:incident_density_per_block 2.3
kpi_materialization:computation_duration_seconds 60
```

### Structured Logging (OperationalLogger)

Sample logs from Phase 3 DAGs:

```json
{
  "timestamp": "2026-05-10T06:00:00Z",
  "event_name": "incident_ingestion_started",
  "event_type": "pipeline_execution",
  "dag_id": "incident_ingestion",
  "metadata": {
    "dataset_id": "a2nx-4u46",
    "expected_records": 5000,
    "schedule": "0 */6 * * *"
  }
}

{
  "timestamp": "2026-05-10T06:15:00Z",
  "event_name": "validation_completed",
  "event_type": "quality_gate",
  "metadata": {
    "total_records": 5000,
    "valid_records": 4950,
    "invalid_records": 50,
    "validation_rules": ["non_null", "type_check", "range_check"]
  }
}

{
  "timestamp": "2026-05-10T06:30:00Z",
  "event_name": "freshness_updated",
  "event_type": "metadata_operation",
  "metadata": {
    "source": "socrata_incidents",
    "last_updated": "2026-05-10T06:30:00Z",
    "record_count": 4950,
    "is_fresh": true
  }
}
```

---

## Architecture Decisions

### Why Separate DAGs?

1. **incident_ingestion** (Every 6 hours)
   - **Frequency**: High (pulls latest data frequently)
   - **Dependencies**: Socrata API availability
   - **SLA**: Strict (1 hour)

2. **repair_scheduling** (Daily)
   - **Frequency**: Lower (optimization is expensive)
   - **Dependencies**: Recent incident data (ExternalTaskSensor)
   - **SLA**: Moderate (2 hours)

3. **kpi_materialization** (Every hour)
   - **Frequency**: High (API queries need fresh KPIs)
   - **Dependencies**: Incident and repair data
   - **SLA**: Strict (30 minutes)

### Why XCom Between Tasks?

Data passed via XCom (instead of direct DB queries):
- **Idempotency**: Re-running task uses same input
- **Debugging**: XCom history shows data at each step
- **Testing**: Mocking XCom data simpler than DB mocking
- **Performance**: Avoids DB queries for intermediate data

### Why ExternalTaskSensor for repair_scheduling?

Could use `depends_on_past` but ExternalTaskSensor:
- **Decoupling**: repair_scheduling doesn't depend on specific incident_ingestion run
- **Visibility**: Airflow UI shows cross-DAG dependency
- **Flexibility**: Can specify which upstream task to wait for
- **Timeout**: Can fail fast if incident data unavailable

---

## Testing Integration

### Unit Test: Phase 1 Integration

```python
def test_incident_validation_integration():
    """Test validation rules applied correctly"""
    from socrata_toolkit.validation import ValidationRuleSet
    
    validator = ValidationRuleSet(name='test')
    validator.add_rule('non_null', {'columns': ['id', 'date']})
    
    test_data = pd.DataFrame({
        'id': [1, 2, None],
        'date': ['2026-05-10', '2026-05-11', '2026-05-12']
    })
    
    result = validator.validate(test_data)
    assert result.valid_count == 2
    assert result.invalid_count == 1
```

### Integration Test: Full DAG Run

```python
def test_incident_ingestion_full_run():
    """Test incident_ingestion DAG end-to-end"""
    from airflow.models import DagBag
    
    bag = DagBag('airflow/dags')
    dag = bag.get_dag('incident_ingestion')
    
    # Verify DAG structure
    assert len(dag.tasks) == 4
    assert dag.get_task('fetch_incidents')
    assert dag.get_task('validate_data')
    assert dag.get_task('upsert_incidents')
    assert dag.get_task('update_freshness')
    
    # Verify task dependencies
    fetch = dag.get_task('fetch_incidents')
    validate = dag.get_task('validate_data')
    assert validate in fetch.get_direct_relatives()
```

---

## Next Steps

1. **Deploy Phase 3**: Follow [Deployment Guide](./airflow_deployment.md)
2. **Run DAGs**: Use [Operations Guide](./airflow_operations.md)
3. **Add New DAGs**: Use [Migration Guide](./airflow_migration_guide.md) template
4. **Monitor**: Query Prometheus metrics and Structured Logs
5. **Phase 4**: Build API queries on top of KPI materialization tables
