# Airflow DAG Development & Migration Guide

## Table of Contents
- [Creating New DAGs](#creating-new-dags)
- [DAG Structure Template](#dag-structure-template)
- [Custom Operators](#custom-operators)
- [Phase 1 Integration](#phase-1-integration)
- [Phase 2 Integration](#phase-2-integration)
- [Testing DAGs Locally](#testing-dags-locally)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Creating New DAGs

### Quick Start: 5-Minute DAG

Create a simple DAG that fetches external data and processes it:

```python
# airflow/dags/my_new_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'data_engineering',
    'start_date': datetime(2026, 5, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'my_new_dag',
    default_args=default_args,
    description='My first data pipeline',
    schedule_interval='0 6 * * *',  # Daily at 6 AM
    catchup=False,
    tags=['data_processing'],
)

def extract_data(**context):
    """Extract data from source"""
    execution_date = context['execution_date']
    print(f"Extracting data for {execution_date}")
    return {"rows_extracted": 1000}

def transform_data(ti):
    """Transform extracted data"""
    extracted = ti.xcom_pull(task_ids='extract')
    rows = extracted['rows_extracted']
    print(f"Transforming {rows} rows")
    return {"rows_transformed": rows}

def load_data(ti):
    """Load transformed data"""
    transformed = ti.xcom_pull(task_ids='transform')
    rows = transformed['rows_transformed']
    print(f"Loading {rows} rows into database")

extract = PythonOperator(
    task_id='extract',
    python_callable=extract_data,
    dag=dag,
)

transform = PythonOperator(
    task_id='transform',
    python_callable=transform_data,
    dag=dag,
)

load = PythonOperator(
    task_id='load',
    python_callable=load_data,
    dag=dag,
)

extract >> transform >> load
```

Deploy immediately:
```bash
cd airflow/dags
# File is auto-discovered by Airflow
# Check UI: http://localhost:8080 (DAGs tab)
```

---

## DAG Structure Template

### Complete Production-Ready DAG

```python
# airflow/dags/example_production_dag.py
"""
Example production-ready DAG with all best practices.

Purpose: Demonstrates integration with Phase 1/2 modules,
         error handling, monitoring, and recovery.

Schedule: Daily at 6 AM UTC
Owner: data_engineering_team
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.exceptions import AirflowException
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

# Import Phase 1/2 modules
from socrata_toolkit.validation import ValidationRuleSet
from socrata_toolkit.freshness import FreshnessTracker
from socrata_toolkit.metrics import MetricsEmitter
from socrata_toolkit.observability import OperationalLogger

# Configure logging
logger = logging.getLogger(__name__)
op_logger = OperationalLogger(__name__)

# Default arguments applicable to all tasks in this DAG
default_args = {
    'owner': 'data_engineering',
    'email': ['alerts@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'start_date': datetime(2026, 5, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

# Define SLA: Tasks must complete within 30 minutes of scheduled start
dag_sla = timedelta(minutes=30)

dag = DAG(
    'example_production_dag',
    default_args=default_args,
    description='Production-ready DAG with validation, monitoring, and error handling',
    schedule_interval='0 6 * * *',  # Daily at 6 AM UTC
    catchup=False,  # Don't run missed schedules on deploy
    max_active_runs=2,  # Allow max 2 concurrent runs
    tags=['production', 'example'],
    sla=dag_sla,
)

# ============================================================================
# TASK IMPLEMENTATIONS
# ============================================================================

def check_prerequisites(**context) -> Dict[str, Any]:
    """
    Validate prerequisites before processing.
    
    Returns:
        Configuration dict for downstream tasks
    """
    execution_date = context['execution_date']
    
    logger.info(f"Checking prerequisites for {execution_date}")
    
    op_logger.log_event(
        event_name="dag_started",
        event_type="dag_task",
        dag_id=context['task'].dag_id,
        metadata={"execution_date": str(execution_date)}
    )
    
    # Validate configuration
    config = {
        'execution_date': execution_date,
        'batch_size': 1000,
        'max_retries': 3,
    }
    
    return config

def fetch_data(ti) -> Dict[str, Any]:
    """
    Fetch data from external source.
    
    Returns:
        Metadata about fetched data
    """
    config = ti.xcom_pull(task_ids='check_prerequisites')
    execution_date = config['execution_date']
    
    logger.info(f"Fetching data for {execution_date}")
    
    # Simulate data fetch
    data_metadata = {
        'record_count': 5000,
        'source': 'external_api',
        'fetch_timestamp': datetime.utcnow().isoformat(),
    }
    
    op_logger.log_event(
        event_name="data_fetch_completed",
        event_type="data_operation",
        metadata=data_metadata
    )
    
    return data_metadata

def validate_data(ti) -> Dict[str, Any]:
    """
    Validate fetched data against rules from Phase 1.
    
    Returns:
        Validation result dict
    """
    data_metadata = ti.xcom_pull(task_ids='fetch_data')
    record_count = data_metadata['record_count']
    
    logger.info(f"Validating {record_count} records")
    
    # Use Phase 1 validation rules
    validator = ValidationRuleSet(name='example_rules')
    
    # Define rules
    validator.add_rule('non_null', {'columns': ['id', 'name']})
    validator.add_rule('type_check', {'column': 'created_date', 'dtype': 'datetime'})
    
    # Simulate validation
    validation_result = {
        'total_records': record_count,
        'valid_records': int(record_count * 0.99),
        'invalid_records': int(record_count * 0.01),
        'validation_passed': True,
    }
    
    if not validation_result['validation_passed']:
        raise AirflowException("Data validation failed")
    
    op_logger.log_event(
        event_name="validation_completed",
        event_type="quality_gate",
        metadata=validation_result
    )
    
    return validation_result

def transform_data(ti) -> Dict[str, Any]:
    """
    Transform validated data.
    
    Returns:
        Transformation result dict
    """
    validation_result = ti.xcom_pull(task_ids='validate_data')
    valid_count = validation_result['valid_records']
    
    logger.info(f"Transforming {valid_count} valid records")
    
    # Simulate transformation
    transform_result = {
        'input_records': valid_count,
        'output_records': valid_count,
        'transformation_timestamp': datetime.utcnow().isoformat(),
    }
    
    op_logger.log_event(
        event_name="transformation_completed",
        event_type="data_operation",
        metadata=transform_result
    )
    
    return transform_result

def load_to_database(ti) -> Dict[str, Any]:
    """
    Load transformed data into PostgreSQL.
    
    Returns:
        Load result dict
    """
    transform_result = ti.xcom_pull(task_ids='transform_data')
    record_count = transform_result['output_records']
    
    logger.info(f"Loading {record_count} records to database")
    
    # Simulate database load
    load_result = {
        'loaded_records': record_count,
        'load_timestamp': datetime.utcnow().isoformat(),
    }
    
    op_logger.log_event(
        event_name="data_loaded",
        event_type="database_operation",
        metadata=load_result
    )
    
    return load_result

def update_freshness(ti) -> None:
    """
    Update data freshness metadata using Phase 2 module.
    """
    load_result = ti.xcom_pull(task_ids='load_to_database')
    
    logger.info("Updating data freshness tracking")
    
    # Use Phase 2 freshness tracker
    tracker = FreshnessTracker(
        data_source='example_source',
        freshness_threshold_hours=24
    )
    
    tracker.update_freshness(
        last_updated=datetime.utcnow(),
        record_count=load_result['loaded_records'],
        metadata={'dag_id': dag.dag_id}
    )
    
    op_logger.log_event(
        event_name="freshness_updated",
        event_type="metadata_operation",
        metadata={'source': 'example_source'}
    )

def emit_metrics(ti) -> None:
    """
    Emit metrics using Phase 2 module.
    """
    logger.info("Emitting metrics for monitoring")
    
    # Use Phase 2 metrics emitter
    emitter = MetricsEmitter(job_name=dag.dag_id)
    
    load_result = ti.xcom_pull(task_ids='load_to_database')
    
    emitter.counter('records_loaded', load_result['loaded_records'])
    emitter.histogram('load_duration_seconds', 120)
    
    op_logger.log_event(
        event_name="metrics_emitted",
        event_type="monitoring",
        metadata={'job_name': dag.dag_id}
    )

def failure_callback(context: Dict[str, Any]) -> None:
    """
    Handle task failures - send alert.
    """
    task = context['task']
    exception = context['exception']
    
    op_logger.log_event(
        event_name="task_failed",
        event_type="error",
        dag_id=task.dag_id,
        task_id=task.task_id,
        metadata={'exception': str(exception)}
    )

# ============================================================================
# TASK DEFINITIONS
# ============================================================================

task_check_prerequisites = PythonOperator(
    task_id='check_prerequisites',
    python_callable=check_prerequisites,
    provide_context=True,
    dag=dag,
)

task_fetch_data = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_data,
    on_failure_callback=failure_callback,
    retries=3,
    dag=dag,
)

task_validate_data = PythonOperator(
    task_id='validate_data',
    python_callable=validate_data,
    on_failure_callback=failure_callback,
    dag=dag,
)

task_transform_data = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    on_failure_callback=failure_callback,
    dag=dag,
)

task_load_to_database = PythonOperator(
    task_id='load_to_database',
    python_callable=load_to_database,
    on_failure_callback=failure_callback,
    dag=dag,
)

task_update_freshness = PythonOperator(
    task_id='update_freshness',
    python_callable=update_freshness,
    dag=dag,
)

task_emit_metrics = PythonOperator(
    task_id='emit_metrics',
    python_callable=emit_metrics,
    dag=dag,
)

# ============================================================================
# TASK DEPENDENCIES
# ============================================================================

task_check_prerequisites >> task_fetch_data
task_fetch_data >> task_validate_data
task_validate_data >> task_transform_data
task_transform_data >> task_load_to_database
task_load_to_database >> [task_update_freshness, task_emit_metrics]
```

---

## Custom Operators

### Extending BaseOperator

Create custom operators for reusable task logic:

```python
# airflow/plugins/custom_operators.py

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from typing import Callable, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DataQualityCheckOperator(BaseOperator):
    """
    Custom operator that validates data quality.
    
    Integrates with Phase 1 validation module.
    """
    
    @apply_defaults
    def __init__(
        self,
        validation_rules: Dict[str, Any],
        table_name: str,
        postgres_conn_id: str = 'postgres_warehouse',
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.validation_rules = validation_rules
        self.table_name = table_name
        self.postgres_conn_id = postgres_conn_id
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """Execute data quality checks"""
        from socrata_toolkit.validation import ValidationRuleSet
        from socrata_toolkit.db_helpers import PostgresHelper
        
        logger.info(f"Running quality checks on {self.table_name}")
        
        # Connect to database
        db = PostgresHelper(self.postgres_conn_id)
        
        # Create validator from Phase 1
        validator = ValidationRuleSet(name=f'{self.table_name}_rules')
        
        # Load data and validate
        data = db.query(f"SELECT * FROM {self.table_name}")
        
        is_valid = validator.validate(data, self.validation_rules)
        
        if not is_valid:
            raise ValueError(f"Quality checks failed for {self.table_name}")
        
        logger.info(f"Quality checks passed for {self.table_name}")
        return True

class MetricsPublisherOperator(BaseOperator):
    """
    Custom operator that publishes metrics.
    
    Integrates with Phase 2 metrics module.
    """
    
    @apply_defaults
    def __init__(
        self,
        metrics: Dict[str, float],
        job_name: str,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.metrics = metrics
        self.job_name = job_name
    
    def execute(self, context: Dict[str, Any]) -> None:
        """Publish metrics"""
        from socrata_toolkit.metrics import MetricsEmitter
        
        logger.info(f"Publishing metrics for {self.job_name}")
        
        emitter = MetricsEmitter(job_name=self.job_name)
        
        for metric_name, metric_value in self.metrics.items():
            emitter.gauge(metric_name, metric_value)
        
        logger.info(f"Metrics published: {list(self.metrics.keys())}")
```

Using custom operators in DAGs:

```python
from plugins.custom_operators import DataQualityCheckOperator

quality_check = DataQualityCheckOperator(
    task_id='quality_check',
    validation_rules={
        'non_null': ['id', 'name'],
        'type_check': {'created_date': 'datetime'},
    },
    table_name='incident_data',
    dag=dag,
)
```

---

## Phase 1 Integration

### Using Validation Rules

```python
from socrata_toolkit.validation import ValidationRuleSet
from socrata_toolkit.schema_registry import SchemaRegistry

def validate_incident_data(ti):
    """Validate incident data using Phase 1 validation rules"""
    
    # Load validation rules
    validator = ValidationRuleSet(name='incident_validation')
    
    validator.add_rule('non_null', {'columns': ['incident_id', 'date', 'location']})
    validator.add_rule('type_check', {
        'incident_id': 'string',
        'date': 'datetime',
        'severity': 'int'
    })
    validator.add_rule('range_check', {
        'severity': {'min': 1, 'max': 5}
    })
    
    # Get data and validate
    data = get_incident_data()  # Your fetch function
    
    result = validator.validate(data)
    
    if not result.is_valid:
        raise ValueError(f"Validation failed: {result.errors}")
    
    return {"valid_records": len(data)}

def check_schema_compliance(ti):
    """Check data schema against registry"""
    
    # Load schema registry
    registry = SchemaRegistry()
    
    schema = registry.get_schema('incident_data')
    
    data = get_incident_data()
    
    if not registry.is_compliant(data, schema):
        raise ValueError("Schema compliance check failed")
    
    return {"schema_version": schema.version}
```

### Computing Metrics

```python
from socrata_toolkit.dot_sidewalk import MaterialAwareSidewalkMetric

def compute_metrics(ti):
    """Compute sidewalk Metrics using Phase 1 module"""
    
    # Load incident and repair data
    incidents = get_incidents_from_db()
    repairs = get_repairs_from_db()
    
    # Create Metric computer from Phase 1
    metric = MaterialAwareSidewalkMetric(
        incidents_df=incidents,
        repairs_df=repairs,
        jurisdiction='NYC'
    )
    
    # Compute Metrics
    results = metric.compute()
    
    # Results include:
    # - response_time_mean, response_time_median
    # - repair_rate_by_material
    # - incident_density_by_borough
    # - seasonal_trends
    
    return results.to_dict()
```

---

## Phase 2 Integration

### Track Data Freshness

```python
from socrata_toolkit.freshness import FreshnessTracker

def update_incident_freshness(ti):
    """Update freshness tracking for incidents"""
    
    tracker = FreshnessTracker(
        data_source='socrata_incidents',
        freshness_threshold_hours=24
    )
    
    incident_count = get_latest_incident_count()
    
    tracker.update_freshness(
        last_updated=datetime.utcnow(),
        record_count=incident_count,
        metadata={
            'source': 'Socrata API',
            'dataset_id': 'a2nx-4u46',
        }
    )
    
    logger.info(f"Updated freshness for {incident_count} incidents")
```

### Emit Operational Metrics

```python
from socrata_toolkit.metrics import MetricsEmitter
from socrata_toolkit.observability import OperationalLogger

def report_pipeline_metrics(ti):
    """Emit metrics from pipeline execution"""
    
    emitter = MetricsEmitter(job_name='incident_ingestion')
    op_logger = OperationalLogger(__name__)
    
    # Emit counters
    emitter.counter('incidents_processed', 5000)
    emitter.counter('incidents_valid', 4950)
    emitter.counter('incidents_rejected', 50)
    
    # Emit histograms
    emitter.histogram('processing_time_seconds', 120)
    emitter.histogram('avg_record_size_bytes', 512)
    
    # Structured logging
    op_logger.log_event(
        event_name="incident_pipeline_completed",
        event_type="pipeline_execution",
        metadata={
            'processed': 5000,
            'valid': 4950,
            'rejected': 50,
            'duration_seconds': 120,
        }
    )
```

### Track Data Lineage

```python
from socrata_toolkit.lineage import LineageTracker

def track_data_lineage(ti):
    """Track data lineage from API to database"""
    
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
        name='incident_data_table',
        target_type='postgresql',
        table='incident'
    )
    
    logger.info("Data lineage recorded")
```

---

## Testing DAGs Locally

### Test DAG Syntax

```bash
cd /workspaces/nyc_data

# Test DAG parsing (no execution)
python -m py_compile airflow/dags/example_production_dag.py

# Load DAG and check for import errors
python -c "from airflow.models import DagBag; DagBag(dag_folder='airflow/dags')"

# Verify in Docker
docker-compose exec scheduler airflow dags list
```

### Unit Test Custom Operators

```python
# tests/test_custom_operators.py

import pytest
from datetime import datetime
from airflow import DAG
from airflow.utils.context import Context
from airflow.plugins.custom_operators import DataQualityCheckOperator
from unittest.mock import Mock, patch

@pytest.fixture
def dag():
    return DAG('test_dag', start_date=datetime(2026, 5, 1))

@pytest.fixture
def context():
    return {
        'task': Mock(),
        'execution_date': datetime(2026, 5, 1),
        'task_instance': Mock(),
    }

def test_quality_check_operator_success(dag, context):
    """Test quality check passes"""
    
    operator = DataQualityCheckOperator(
        task_id='test_quality',
        validation_rules={'non_null': ['id', 'name']},
        table_name='test_table',
        dag=dag,
    )
    
    with patch('plugins.custom_operators.ValidationRuleSet'):
        with patch('plugins.custom_operators.PostgresHelper'):
            result = operator.execute(context)
    
    assert result is True

def test_quality_check_operator_failure(dag, context):
    """Test quality check failure raises exception"""
    
    operator = DataQualityCheckOperator(
        task_id='test_quality',
        validation_rules={'non_null': ['id']},
        table_name='test_table',
        dag=dag,
    )
    
    with patch('plugins.custom_operators.ValidationRuleSet'):
        with patch('plugins.custom_operators.PostgresHelper'):
            with pytest.raises(ValueError):
                operator.execute(context)
```

### Integration Test DAG Runs

```python
# tests/test_dag_integration.py

from datetime import datetime
from airflow.models import DagBag
from airflow.utils.context import Context
import pytest

@pytest.fixture
def dagbag():
    return DagBag(dag_folder='airflow/dags')

def test_example_dag_structure(dagbag):
    """Test DAG is properly configured"""
    dag = dagbag.get_dag('example_production_dag')
    
    assert dag is not None
    assert dag.doc is not None
    assert dag.default_args['owner'] == 'data_engineering'
    assert len(dag.tasks) == 7  # check_prerequisites, fetch_data, validate_data, ...

def test_example_dag_dependencies(dagbag):
    """Test task dependencies are correct"""
    dag = dagbag.get_dag('example_production_dag')
    
    # Task: check_prerequisites -> fetch_data
    check_task = dag.get_task('check_prerequisites')
    assert 'fetch_data' in [t.task_id for t in check_task.get_direct_relatives()]
```

---

## Best Practices

### 1. DAG Naming Conventions

```python
# ✓ GOOD: Descriptive, snake_case, includes data source
'incident_ingestion_daily'
'repair_scheduling_optimization'
'metric_materialization_hourly'

# ✗ BAD: Unclear, camelCase, generic
'dag1'
'myDAG'
'data_pipeline'
```

### 2. Task Idempotency

Ensure tasks produce same result if re-run with same inputs:

```python
def load_data_idempotent(ti):
    """
    Idempotent load: Use UPSERT instead of INSERT to allow re-runs.
    """
    data = ti.xcom_pull(task_ids='transform')
    
    # Use UPSERT to allow re-execution
    query = """
    INSERT INTO incident_data (id, name, created_date)
    VALUES (%s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        created_date = EXCLUDED.created_date
    """
    
    db.execute_many(query, data)
```

### 3. Checkpointing for Incremental Processing

```python
def fetch_incidents_incremental(ti):
    """
    Only fetch incidents since last run.
    """
    from socrata_toolkit.freshness import FreshnessTracker
    
    tracker = FreshnessTracker(data_source='socrata_incidents')
    
    # Get last processed date
    last_processed = tracker.get_last_update()
    
    # Fetch only new data
    api = SocrataAPI()
    new_incidents = api.fetch(
        dataset_id='a2nx-4u46',
        where=f"created_date > {last_processed}"
    )
    
    # Update checkpoint
    tracker.update_freshness(
        last_updated=datetime.utcnow(),
        record_count=len(new_incidents)
    )
    
    return new_incidents
```

### 4. Error Handling & Retries

```python
from airflow.exceptions import AirflowException

@task(retries=3, retry_delay=timedelta(minutes=5))
def resilient_fetch_with_circuit_breaker():
    """
    Retry with exponential backoff and circuit breaker pattern.
    """
    try:
        return api.fetch_data()
    except ConnectionError as e:
        logger.error(f"Connection failed, retry count: {retry_count}")
        raise AirflowException(f"API connection failed: {e}") from e
```

### 5. Documentation

```python
# ✓ GOOD: Clear purpose, parameters, returns
def compute_metric_metrics(incident_df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute sidewalk incident Metric metrics.
    
    Args:
        incident_df: DataFrame with incident records containing:
            - incident_id: unique identifier
            - date: incident date
            - location: geospatial coordinates
            
    Returns:
        Dict with metrics:
        - response_time_mean: average response time (days)
        - response_rate: percentage of incidents with repairs
        - density: incidents per square mile
        
    Raises:
        ValueError: If required columns missing or data invalid
    """
```

---

## Troubleshooting

### DAG Not Appearing in UI

```bash
# Check file location and naming
ls -la airflow/dags/*.py

# Verify file is readable by Airflow user
docker-compose exec scheduler airflow dags list

# Check for import errors
docker-compose logs scheduler | grep -i "error\|import"

# Try explicit import
docker-compose exec scheduler python -c "
from airflow.models import DagBag
bag = DagBag('airflow/dags')
print([d.dag_id for d in bag.dags.values()])
"
```

### Xcom Between Tasks Not Working

```python
# ✗ WRONG: Xcom needs explicit push/pull
def task1():
    return {"key": "value"}  # This is NOT auto-pushed

# ✓ CORRECT: Explicit xcom operations
def task1(ti):
    result = {"key": "value"}
    ti.xcom_push(key='result', value=result)
    return result

def task2(ti):
    result = ti.xcom_pull(task_ids='task1', key='result')
```

### Task Timeouts

```python
# Set task timeout
my_task = PythonOperator(
    task_id='long_running_task',
    python_callable=my_function,
    execution_timeout=timedelta(hours=2),  # Max 2 hours
    dag=dag,
)
```

---

## Next Steps

- [Deployment Guide](./airflow_deployment.md): Deploy to production
- [Operations Guide](./airflow_operations.md): Daily operations
- [Phase 3 Integration Guide](./PHASE3_INTEGRATION_GUIDE.md): Full architecture
