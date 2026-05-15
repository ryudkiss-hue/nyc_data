"""
Airflow DAG: Sidewalk Incident Ingestion.

Purpose:
    Daily ingestion of 311 sidewalk complaints and incidents from Socrata.
    Validates schema and data quality, loads to fact_incidents table with checkpoint tracking.

Schedule:
    Daily at 02:00 UTC (post-NYC business day)

SLA:
    Must complete within 1 hour

Dependencies:
    - Socrata API (data.cityofnewyork.us)
    - PostgreSQL warehouse
    - Phase 1: schema_registry, validation rules, domain model
    - Phase 2: freshness tracking, lineage tracking, metrics, alerts

Key Features:
    - Incremental load using checkpoint (max_update_timestamp)
    - Schema compliance checking for drift detection
    - Data quality validation (material coverage, defect applicability)
    - Full Phase 2 observability (metrics, lineage, alerts)
    - Slack notifications on failure
"""

import os

# Import custom operators
import sys
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.sensors.http import HttpSensor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from custom_operators import (
    DataQualityCheckOperator,
    FreshnessUpdateOperator,
    MetricsEmitterOperator,
    PostgresUpsertOperator,
    SchemaComplianceOperator,
    SocrataFetchOperator,
)

from config import SLA_CONFIG, get_dag_defaults

# ============================================================================
# DAG CONFIGURATION
# ============================================================================

DAG_ID = "sidewalk_incident_ingestion"
DAG_DESCRIPTION = "Daily ingestion of 311 sidewalk complaints from Socrata"

dag_defaults = get_dag_defaults(DAG_ID)
sla_config = SLA_CONFIG.get(DAG_ID, {})

# ============================================================================
# DAG DEFINITION
# ============================================================================

dag_defaults["sla"] = timedelta(seconds=sla_config.get("sla_seconds", 3600))

dag = DAG(
    dag_id=DAG_ID,
    description=DAG_DESCRIPTION,
    default_args=dag_defaults,
    schedule_interval="0 2 * * *",  # 02:00 UTC daily
    tags=["ingestion", "311", "sidewalk", "daily"],
    catchup=False,
    max_active_runs=2,
    doc_md=__doc__,
)

# ============================================================================
# TASK: Start DAG run
# ============================================================================

start_dag = PythonOperator(
    task_id="start_dag_run",
    python_callable=lambda: print("✅ Starting sidewalk incident ingestion DAG"),
    dag=dag,
)

# ============================================================================
# TASK: Check Socrata API health
# ============================================================================

# Pull Socrata App Token from Airflow Variables
try:
    socrata_token = Variable.get("SOCRATA_APP_TOKEN")
except:
    socrata_token = None

check_socrata_health = HttpSensor(
    task_id="check_socrata_api_health",
    http_conn_id="socrata_api",
    endpoint="/api/views/a2nx-4u46.json",  # 311 Service Requests dataset
    headers=(
        {"Accept": "application/json", "X-App-Token": socrata_token}
        if socrata_token
        else {"Accept": "application/json"}
    ),
    response_check=lambda response: response.status_code == 200,
    timeout=30,
    retries=2,
    retry_delay=timedelta(seconds=30),
    dag=dag,
)

# ============================================================================
# TASK: Fetch new incidents (incremental)
# ============================================================================

fetch_incidents = SocrataFetchOperator(
    task_id="fetch_new_incidents",
    dataset_id="a2nx-4u46",  # 311 Service Requests
    checkpoint_table="incident_ingestion_checkpoint",
    checkpoint_column="max_update_timestamp",
    lookback_hours=24,
    incremental=True,
    dag=dag,
)

# ============================================================================
# TASK: Validate schema compliance
# ============================================================================

validate_schema = SchemaComplianceOperator(
    task_id="validate_schema",
    table_name="staging_incident_311",
    schema_version="latest",
    dag=dag,
)

# ============================================================================
# TASK: Validate data quality
# ============================================================================

validate_quality = DataQualityCheckOperator(
    task_id="validate_data_quality",
    table_name="staging_incident_311",
    validation_rules=["material_coverage", "defect_applicability"],
    allow_failures=False,
    dag=dag,
)

# ============================================================================
# TASK: UPSERT to warehouse
# ============================================================================

upsert_to_warehouse = PostgresUpsertOperator(
    task_id="upsert_warehouse",
    table_name="fact_incidents",
    checkpoint_table="incident_ingestion_checkpoint",
    primary_keys=["complaint_id", "created_date"],
    data_from_xcom=True,
    dag=dag,
)

# ============================================================================
# TASK: Detect schema drift
# ============================================================================

detect_drift = SchemaComplianceOperator(
    task_id="detect_schema_drift",
    table_name="fact_incidents",
    schema_version="latest",
    dag=dag,
)

# ============================================================================
# TASK: Update freshness tracking
# ============================================================================

update_freshness = FreshnessUpdateOperator(
    task_id="emit_freshness_metric",
    dataset_id="311_socrata",
    expected_frequency_hours=24,
    dag=dag,
)

# ============================================================================
# TASK: Emit lineage tracking (Phase 2)
# ============================================================================


def emit_lineage_records(**context):
    """Record lineage for incident ingestion pipeline."""
    from custom_operators import LineageRecorder

    lineage = LineageRecorder()

    # Record source → fact table transformation
    lineage.record_transformation(
        source_tables=["311_socrata"],
        target_table="fact_incidents",
        operation="daily_incremental_ingestion",
        metadata={
            "checkpoint_column": "max_update_timestamp",
            "incident_types": [
                "Sidewalk Condition",
                "Street Sign - Missing",
                "Street Sign - Damaged",
            ],
        },
    )

    # Record fact table dependencies
    lineage.record_transformation(
        source_tables=["dim_defect_types", "dim_materials", "dim_locations"],
        target_table="fact_incidents",
        operation="dimension_join",
        metadata={"join_keys": ["defect_type_id", "material_id", "location_id"]},
    )

    print("✅ Lineage records emitted")


emit_lineage = PythonOperator(
    task_id="emit_lineage",
    python_callable=emit_lineage_records,
    dag=dag,
)

# ============================================================================
# TASK: Emit observability metrics (Phase 2)
# ============================================================================

emit_metrics_ingestion = MetricsEmitterOperator(
    task_id="emit_metrics",
    metric_name="incident_ingestion_duration_seconds",
    value=0,  # Will be overridden at runtime
    labels={
        "dataset_id": "311_socrata",
        "table_name": "fact_incidents",
        "dag_id": DAG_ID,
    },
    dag=dag,
)

# ============================================================================
# TASK: End DAG run
# ============================================================================

end_dag = PythonOperator(
    task_id="end_dag_run",
    python_callable=lambda: print("✅ Completed sidewalk incident ingestion"),
    dag=dag,
)

# ============================================================================
# DAG DEPENDENCIES
# ============================================================================

start_dag >> check_socrata_health >> fetch_incidents
fetch_incidents >> validate_schema >> validate_quality
validate_quality >> upsert_to_warehouse >> detect_drift
detect_drift >> update_freshness >> emit_lineage >> emit_metrics_ingestion >> end_dag

# ============================================================================
# DOCUMENTATION
# ============================================================================

"""
Task Execution Flow:

1. start_dag_run: Initialize DAG execution
2. check_socrata_api_health: Verify Socrata API is available (HTTP sensor, 30s timeout, 2 retries)
3. fetch_new_incidents: Fetch 311 data since last checkpoint using incremental query
4. validate_schema: Check for breaking schema changes against Phase 1 registry
5. validate_data_quality: Run Phase 1 validation rules (material coverage, defect applicability)
6. upsert_warehouse: Insert/update records in fact_incidents table, update checkpoint
7. detect_schema_drift: Alert if new columns or type changes detected
8. emit_freshness_metric: Update Phase 2 FreshnessTracker with last ingestion time
9. emit_lineage: Record Phase 2 lineage transformation metadata
10. emit_metrics: Emit Phase 2 Prometheus metrics for pipeline observability
11. end_dag_run: Mark completion

Error Handling:
- Operator failures trigger automatic retries with exponential backoff (3 attempts max)
- SLA violation after 1 hour triggers alerts via email and Slack
- Data quality failures halt pipeline and trigger manual approval task (future phase)
- Schema drift alerts sent to data engineering team via Slack

Idempotency:
- All operations use checkpoint-based incremental loads
- UPSERT ensures rerunning produces same results
- Lineage records are immutable (append-only audit log)
- Metrics are cumulative counters

Phase 1 Integration:
- Uses schema_registry.SchemaRegistry for schema validation
- Uses validation.validate_material_coverage() for material-aware quality checks
- Uses dot_sidewalk.DefectClassification for incident classification

Phase 2 Integration:
- Uses freshness.FreshnessTracker to track ingestion freshness
- Uses lineage.LineageRecorder to track data lineage
- Uses metrics.MetricsRegistry to emit Prometheus metrics
- Uses observability.AlertManager for failure alerts
"""
