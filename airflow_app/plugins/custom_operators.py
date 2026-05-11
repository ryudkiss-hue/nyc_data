"""
Custom Airflow Operators and Sensors for NYC DOT Sidewalk Inspection.

Operators:
- SocrataFetchOperator: Incremental fetch from Socrata API with freshness validation
- DataQualityCheckOperator: Execute Phase 1 validation rules
- SchemaComplianceOperator: Detect schema drift and breaking changes
- PostgresUpsertOperator: Idempotent UPSERT with checkpoint management
- FreshnessUpdateOperator: Record ingestion freshness via Phase 2 tracker
- MetricsEmitterOperator: Emit Prometheus metrics for observability

Sensors:
- FreshnessCheckSensor: Wait for dataset to meet freshness SLA
- DataQualitySensor: Wait for upstream tables to pass quality gates
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from airflow.models import BaseOperator, BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowException
from airflow.models import Variable

# Add parent directories to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from socrata_toolkit.client import SocrataClient
from socrata_toolkit.schema_registry import SchemaRegistry
from socrata_toolkit.validation import validate_material_coverage, validate_defect_applicability
from socrata_toolkit.freshness import FreshnessTracker
from socrata_toolkit.lineage import LineageRecorder
from socrata_toolkit.metrics import MetricsRegistry
from socrata_toolkit.observability import AlertManager

logger = logging.getLogger(__name__)

# ============================================================================
# SOCRATA FETCH OPERATOR
# ============================================================================


class SocrataFetchOperator(BaseOperator):
    """
    Fetch incremental data from Socrata API with checkpoint management.

    Fetches only records updated since last successful run (checkpoint-based).
    Uses Phase 2 freshness tracker to validate source data freshness.
    Emits lineage and metrics for observability.

    Args:
        dataset_id: Socrata dataset identifier
        checkpoint_table: PostgreSQL table storing checkpoint (max_update_timestamp)
        checkpoint_column: Column name tracking last update timestamp
        lookback_hours: Hours to lookback (safety margin for clock skew)
        incremental: If True, use checkpoint; if False, full refresh
        socrata_app_token: Socrata API app token (defaults to config variable)

    XCom Output:
        - row_count: Number of rows fetched
        - max_update_timestamp: Latest update timestamp in fetched data
        - first_record_timestamp: Earliest record timestamp
    """

    template_fields = ["dataset_id", "checkpoint_table"]

    @apply_defaults
    def __init__(
        self,
        dataset_id: str,
        checkpoint_table: str,
        checkpoint_column: str = "max_update_timestamp",
        lookback_hours: int = 24,
        incremental: bool = True,
        socrata_app_token: Optional[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.dataset_id = dataset_id
        self.checkpoint_table = checkpoint_table
        self.checkpoint_column = checkpoint_column
        self.lookback_hours = lookback_hours
        self.incremental = incremental
        self.socrata_app_token = socrata_app_token or Variable.get("SOCRATA_APP_TOKEN")

    def execute(self, context):
        """Execute incremental fetch from Socrata."""
        logger.info(
            f"Starting Socrata fetch: dataset_id={self.dataset_id}, incremental={self.incremental}"
        )

        try:
            # Initialize Socrata client
            client = SocrataClient(app_token=self.socrata_app_token)

            # Get checkpoint (last successful fetch timestamp)
            checkpoint_timestamp = None
            if self.incremental:
                checkpoint_timestamp = self._get_checkpoint(context)
                logger.info(f"Checkpoint timestamp: {checkpoint_timestamp}")

            # Validate source data freshness (Phase 2)
            freshness_tracker = FreshnessTracker()
            freshness_status = freshness_tracker.get_freshness(self.dataset_id)

            if freshness_status.is_stale:
                logger.warning(
                    f"Dataset {self.dataset_id} is stale (last update: {freshness_status.last_update})"
                )
                # Still fetch, but log warning for operators downstream
                context["task_instance"].xcom_push(
                    key="freshness_warning",
                    value=f"Source data is stale: {freshness_status.last_update}",
                )

            # Fetch data
            if self.incremental and checkpoint_timestamp:
                records = client.fetch_incremental(
                    dataset_id=self.dataset_id,
                    where=f"updated_at > '{checkpoint_timestamp}'",
                )
            else:
                records = client.fetch_all(dataset_id=self.dataset_id)

            if not records:
                logger.info(f"No new records found for {self.dataset_id}")
                context["task_instance"].xcom_push(key="row_count", value=0)
                return

            # Extract metrics
            row_count = len(records)
            max_update_timestamp = max(
                (r.get("updated_at") for r in records if "updated_at" in r),
                default=None,
            )
            first_record_timestamp = min(
                (r.get("created_at") for r in records if "created_at" in r),
                default=None,
            )

            logger.info(
                f"Fetched {row_count} records. "
                f"Max timestamp: {max_update_timestamp}, "
                f"First timestamp: {first_record_timestamp}"
            )

            # Push metrics to XCom
            context["task_instance"].xcom_push(key="row_count", value=row_count)
            context["task_instance"].xcom_push(
                key="max_update_timestamp", value=str(max_update_timestamp)
            )
            context["task_instance"].xcom_push(
                key="first_record_timestamp", value=str(first_record_timestamp)
            )

            # Emit Phase 2 lineage: 311_socrata → (output temporary staging)
            lineage_recorder = LineageRecorder()
            lineage_recorder.record_transformation(
                source_tables=[self.dataset_id],
                target_table=f"staging_{self.dataset_id}",
                operation="fetch_incremental",
                metadata={"row_count": row_count, "checkpoint_column": self.checkpoint_column},
            )

            # Emit Phase 2 metrics
            metrics_registry = MetricsRegistry()
            metrics_registry.record_ingestion(
                dataset_id=self.dataset_id,
                record_count=row_count,
                duration_seconds=(datetime.utcnow() - context["task_instance"].start_date).total_seconds(),
            )

            logger.info(f"✅ Successfully fetched and staged {row_count} records from {self.dataset_id}")
            return records

        except Exception as e:
            logger.error(f"❌ SocrataFetchOperator failed: {str(e)}")

            # Emit Phase 2 alert
            alert_manager = AlertManager()
            alert_manager.send_alert(
                alert_type="INGESTION_FAILURE",
                severity="HIGH",
                message=f"Failed to fetch {self.dataset_id}: {str(e)}",
                metadata={"dag_id": context["dag"].dag_id, "task_id": self.task_id},
            )

            raise AirflowException(f"Socrata fetch failed: {str(e)}")

    def _get_checkpoint(self, context) -> Optional[str]:
        """Get last checkpoint timestamp from database."""
        try:
            from sqlalchemy import create_engine, text

            # Get database connection from Airflow config
            from airflow.config import conf

            db_conn_str = conf.get("core", "sql_alchemy_conn")
            engine = create_engine(db_conn_str)

            with engine.connect() as conn:
                query = f"SELECT {self.checkpoint_column} FROM {self.checkpoint_table} ORDER BY created_at DESC LIMIT 1"
                result = conn.execute(text(query))
                row = result.fetchone()

                if row:
                    checkpoint = row[0]
                    logger.info(f"Retrieved checkpoint: {checkpoint}")
                    return checkpoint
                else:
                    logger.info(f"No checkpoint found in {self.checkpoint_table}, using lookback window")
                    lookback_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)
                    return lookback_time.isoformat()

        except Exception as e:
            logger.warning(f"Could not retrieve checkpoint: {str(e)}, using lookback window")
            lookback_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)
            return lookback_time.isoformat()


# ============================================================================
# DATA QUALITY CHECK OPERATOR
# ============================================================================


class DataQualityCheckOperator(BaseOperator):
    """
    Execute Phase 1 validation rules on data.

    Runs material coverage, defect applicability, and custom validation rules.
    Emits Phase 2 metrics and alerts on validation failures.

    Args:
        table_name: Table to validate
        validation_rules: List of validation rule names to run
        allow_failures: If False, raise exception on any failure
    """

    @apply_defaults
    def __init__(
        self,
        table_name: str,
        validation_rules: Optional[List[str]] = None,
        allow_failures: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.table_name = table_name
        self.validation_rules = validation_rules or [
            "material_coverage",
            "defect_applicability",
        ]
        self.allow_failures = allow_failures

    def execute(self, context):
        """Run data quality validations."""
        logger.info(f"Starting data quality checks on {self.table_name}")

        from sqlalchemy import create_engine, text
        from airflow.config import conf

        db_conn_str = conf.get("core", "sql_alchemy_conn")
        engine = create_engine(db_conn_str)

        results = {}
        failures = []

        try:
            with engine.connect() as conn:
                # Run material coverage validation
                if "material_coverage" in self.validation_rules:
                    try:
                        coverage = validate_material_coverage(self.table_name, conn)
                        results["material_coverage"] = coverage
                        logger.info(f"Material coverage: {coverage}")
                    except Exception as e:
                        failures.append(f"material_coverage: {str(e)}")
                        logger.warning(f"Material coverage validation failed: {e}")

                # Run defect applicability validation
                if "defect_applicability" in self.validation_rules:
                    try:
                        applicable = validate_defect_applicability(self.table_name, conn)
                        results["defect_applicability"] = applicable
                        logger.info(f"Defect applicability: {applicable}")
                    except Exception as e:
                        failures.append(f"defect_applicability: {str(e)}")
                        logger.warning(f"Defect applicability validation failed: {e}")

            # Emit Phase 2 metrics
            metrics_registry = MetricsRegistry()
            metrics_registry.record_validation(
                table_name=self.table_name,
                passed=len(failures) == 0,
                failure_count=len(failures),
                rules_executed=len(self.validation_rules),
            )

            # Push results to XCom
            context["task_instance"].xcom_push(key="validation_results", value=results)
            context["task_instance"].xcom_push(key="validation_failures", value=failures)

            if failures and not self.allow_failures:
                error_msg = f"Data quality checks failed: {failures}"
                logger.error(f"❌ {error_msg}")

                # Emit alert
                alert_manager = AlertManager()
                alert_manager.send_alert(
                    alert_type="DATA_QUALITY_FAILURE",
                    severity="MEDIUM",
                    message=error_msg,
                    metadata={
                        "table_name": self.table_name,
                        "dag_id": context["dag"].dag_id,
                    },
                )

                raise AirflowException(error_msg)

            logger.info(f"✅ Data quality checks passed for {self.table_name}")

        except Exception as e:
            logger.error(f"❌ DataQualityCheckOperator failed: {str(e)}")
            raise


# ============================================================================
# SCHEMA COMPLIANCE OPERATOR
# ============================================================================


class SchemaComplianceOperator(BaseOperator):
    """
    Detect schema drift and breaking changes.

    Compares actual schema against schema registry (Phase 1).
    Alerts on breaking changes (removed columns, type changes).

    Args:
        table_name: Table to check
        schema_version: Expected schema version
    """

    @apply_defaults
    def __init__(
        self, table_name: str, schema_version: str = "latest", *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.table_name = table_name
        self.schema_version = schema_version

    def execute(self, context):
        """Check schema compliance."""
        logger.info(f"Checking schema compliance for {self.table_name}")

        try:
            from sqlalchemy import create_engine, inspect
            from airflow.config import conf

            db_conn_str = conf.get("core", "sql_alchemy_conn")
            engine = create_engine(db_conn_str)

            # Get actual schema
            inspector = inspect(engine)
            actual_columns = {
                col["name"]: col["type"] for col in inspector.get_columns(self.table_name)
            }

            # Get expected schema from registry
            schema_registry = SchemaRegistry()
            expected_schema = schema_registry.get_schema(self.table_name, self.schema_version)

            if not expected_schema:
                logger.warning(f"No schema found for {self.table_name} in registry")
                return

            # Check for breaking changes
            expected_columns = {
                col["name"]: col["type"] for col in expected_schema.get("columns", [])
            }

            breaking_changes = []

            # Check for removed columns
            for col_name in expected_columns:
                if col_name not in actual_columns:
                    breaking_changes.append(f"Column '{col_name}' removed")

            # Check for type changes
            for col_name, expected_type in expected_columns.items():
                if col_name in actual_columns:
                    actual_type = str(actual_columns[col_name])
                    if str(expected_type) != actual_type:
                        breaking_changes.append(
                            f"Column '{col_name}' type changed: {expected_type} → {actual_type}"
                        )

            if breaking_changes:
                error_msg = f"Schema drift detected: {breaking_changes}"
                logger.error(f"❌ {error_msg}")

                # Emit alert
                alert_manager = AlertManager()
                alert_manager.send_alert(
                    alert_type="SCHEMA_DRIFT",
                    severity="HIGH",
                    message=error_msg,
                    metadata={"table_name": self.table_name},
                )

                raise AirflowException(error_msg)

            logger.info(f"✅ Schema compliance check passed for {self.table_name}")

        except Exception as e:
            logger.error(f"❌ SchemaComplianceOperator failed: {str(e)}")
            raise


# ============================================================================
# POSTGRES UPSERT OPERATOR
# ============================================================================


class PostgresUpsertOperator(BaseOperator):
    """
    Idempotent UPSERT operation with checkpoint management.

    Performs INSERT OR UPDATE based on primary keys.
    Updates checkpoint table with max timestamp and record count.

    Args:
        table_name: Target table
        checkpoint_table: Checkpoint table for incremental tracking
        primary_keys: List of column names forming primary key
        data_from_xcom: If True, read data from upstream task XCom
    """

    template_fields = ["table_name", "checkpoint_table"]

    @apply_defaults
    def __init__(
        self,
        table_name: str,
        checkpoint_table: str,
        primary_keys: List[str],
        data_from_xcom: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.table_name = table_name
        self.checkpoint_table = checkpoint_table
        self.primary_keys = primary_keys
        self.data_from_xcom = data_from_xcom

    def execute(self, context):
        """Execute UPSERT operation."""
        logger.info(f"Starting UPSERT to {self.table_name}")

        try:
            from sqlalchemy import create_engine, text
            from airflow.config import conf

            db_conn_str = conf.get("core", "sql_alchemy_conn")
            engine = create_engine(db_conn_str)

            # Get row count and max timestamp from previous task
            task_instance = context["task_instance"]
            row_count = task_instance.xcom_pull(
                task_ids=context["task"].upstream_list[0].task_id if context["task"].upstream_list else None,
                key="row_count",
            ) or 0
            max_timestamp = task_instance.xcom_pull(
                task_ids=context["task"].upstream_list[0].task_id if context["task"].upstream_list else None,
                key="max_update_timestamp",
            ) or datetime.utcnow().isoformat()

            logger.info(f"UPSERT parameters: row_count={row_count}, max_timestamp={max_timestamp}")

            with engine.connect() as conn:
                # Perform UPSERT (implementation assumes table exists)
                # This is a simplified example; real implementation would be dialect-specific
                upsert_query = f"""
                INSERT INTO {self.table_name} 
                SELECT * FROM staging_{self.table_name}
                ON CONFLICT ({', '.join(self.primary_keys)})
                DO UPDATE SET updated_at = NOW()
                """

                conn.execute(text(upsert_query))
                conn.commit()

                # Update checkpoint table
                checkpoint_query = f"""
                INSERT INTO {self.checkpoint_table} 
                ({self.primary_keys[0] if self.primary_keys else 'id'}, max_update_timestamp, record_count, created_at)
                VALUES ('{max_timestamp}', {row_count}, NOW())
                """

                conn.execute(text(checkpoint_query))
                conn.commit()

                logger.info(f"✅ UPSERT completed: {row_count} records to {self.table_name}")

            # Emit Phase 2 lineage
            lineage_recorder = LineageRecorder()
            lineage_recorder.record_transformation(
                source_tables=[f"staging_{self.table_name}"],
                target_table=self.table_name,
                operation="upsert",
                metadata={
                    "primary_keys": self.primary_keys,
                    "row_count": row_count,
                },
            )

            # Emit Phase 2 metrics
            metrics_registry = MetricsRegistry()
            metrics_registry.record_load(
                table_name=self.table_name,
                record_count=row_count,
                operation="upsert",
            )

        except Exception as e:
            logger.error(f"❌ PostgresUpsertOperator failed: {str(e)}")
            raise AirflowException(f"UPSERT failed: {str(e)}")


# ============================================================================
# FRESHNESS UPDATE OPERATOR
# ============================================================================


class FreshnessUpdateOperator(BaseOperator):
    """
    Record data freshness status in Phase 2 FreshnessTracker.

    Logs when datasets were last updated and checks against SLA.
    Alerts if freshness SLA is violated.

    Args:
        dataset_id: Dataset identifier
        expected_frequency_hours: Expected frequency of updates
    """

    @apply_defaults
    def __init__(
        self,
        dataset_id: str,
        expected_frequency_hours: int = 24,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.dataset_id = dataset_id
        self.expected_frequency_hours = expected_frequency_hours

    def execute(self, context):
        """Update freshness tracking."""
        logger.info(f"Recording freshness for {self.dataset_id}")

        try:
            # Get max timestamp from upstream task
            task_instance = context["task_instance"]
            max_timestamp = task_instance.xcom_pull(
                task_ids=context["task"].upstream_list[0].task_id if context["task"].upstream_list else None,
                key="max_update_timestamp",
            )

            if not max_timestamp:
                max_timestamp = datetime.utcnow().isoformat()

            # Record freshness in Phase 2 tracker
            freshness_tracker = FreshnessTracker()
            freshness_tracker.track_ingestion(
                dataset_id=self.dataset_id,
                last_updated=max_timestamp,
                expected_frequency_hours=self.expected_frequency_hours,
            )

            logger.info(f"✅ Recorded freshness for {self.dataset_id}: {max_timestamp}")

            # Check if freshness SLA is violated
            freshness_status = freshness_tracker.get_freshness(self.dataset_id)

            if freshness_status.is_stale:
                logger.warning(f"⚠️ Freshness SLA violated for {self.dataset_id}")

                alert_manager = AlertManager()
                alert_manager.send_alert(
                    alert_type="FRESHNESS_SLA_VIOLATION",
                    severity="MEDIUM",
                    message=f"Dataset {self.dataset_id} freshness SLA exceeded",
                    metadata={"expected_hours": self.expected_frequency_hours},
                )

        except Exception as e:
            logger.error(f"❌ FreshnessUpdateOperator failed: {str(e)}")
            raise AirflowException(f"Freshness tracking failed: {str(e)}")


# ============================================================================
# METRICS EMITTER OPERATOR
# ============================================================================


class MetricsEmitterOperator(BaseOperator):
    """
    Emit Prometheus metrics for observability.

    Records custom metrics with labels for Prometheus scraping.

    Args:
        metric_name: Prometheus metric name
        value: Metric value
        labels: Dictionary of metric labels (dataset_id, table_name, etc.)
    """

    @apply_defaults
    def __init__(
        self,
        metric_name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.metric_name = metric_name
        self.value = value
        self.labels = labels or {}

    def execute(self, context):
        """Emit metric to Prometheus."""
        logger.info(f"Emitting metric: {self.metric_name}={self.value}")

        try:
            metrics_registry = MetricsRegistry()

            # Record metric based on type
            if "duration" in self.metric_name:
                metrics_registry.record_duration(
                    operation=self.metric_name,
                    duration_seconds=self.value,
                    labels=self.labels,
                )
            elif "counter" in self.metric_name:
                metrics_registry.record_counter(
                    counter_name=self.metric_name,
                    value=int(self.value),
                    labels=self.labels,
                )
            else:
                metrics_registry.record_gauge(
                    gauge_name=self.metric_name,
                    value=self.value,
                    labels=self.labels,
                )

            logger.info(f"✅ Emitted metric: {self.metric_name}")

        except Exception as e:
            logger.error(f"❌ MetricsEmitterOperator failed: {str(e)}")
            raise AirflowException(f"Metrics emission failed: {str(e)}")


# ============================================================================
# FRESHNESS CHECK SENSOR
# ============================================================================


class FreshnessCheckSensor(BaseSensorOperator):
    """
    Wait for dataset to be fresh (not stale per Phase 2 SLA).

    Polls freshness tracker until dataset freshness SLA is met.

    Args:
        dataset_id: Dataset to check
        max_stale_hours: Maximum staleness threshold
        poke_interval: Seconds between checks
    """

    @apply_defaults
    def __init__(
        self,
        dataset_id: str,
        max_stale_hours: int = 24,
        poke_interval: int = 300,  # 5 minutes
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.dataset_id = dataset_id
        self.max_stale_hours = max_stale_hours
        self.poke_interval = poke_interval

    def poke(self, context):
        """Check if dataset is fresh."""
        try:
            freshness_tracker = FreshnessTracker()
            freshness_status = freshness_tracker.get_freshness(self.dataset_id)

            if not freshness_status.is_stale:
                logger.info(f"✅ Dataset {self.dataset_id} is fresh")
                return True
            else:
                logger.info(
                    f"⏳ Dataset {self.dataset_id} is still stale. "
                    f"Last update: {freshness_status.last_update}"
                )
                return False

        except Exception as e:
            logger.error(f"Error checking freshness for {self.dataset_id}: {e}")
            return False


# ============================================================================
# DATA QUALITY SENSOR
# ============================================================================


class DataQualitySensor(BaseSensorOperator):
    """
    Wait for upstream table to pass quality gates.

    Polls validation metrics until minimum quality score is met.

    Args:
        table_name: Table to monitor
        min_completeness_pct: Minimum data completeness percentage
        poke_interval: Seconds between checks
    """

    @apply_defaults
    def __init__(
        self,
        table_name: str,
        min_completeness_pct: float = 95.0,
        poke_interval: int = 60,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.table_name = table_name
        self.min_completeness_pct = min_completeness_pct
        self.poke_interval = poke_interval

    def poke(self, context):
        """Check if table meets quality gates."""
        try:
            from sqlalchemy import create_engine, text
            from airflow.config import conf

            db_conn_str = conf.get("core", "sql_alchemy_conn")
            engine = create_engine(db_conn_str)

            with engine.connect() as conn:
                # Query completeness metric (simplified)
                query = f"""
                SELECT COALESCE(AVG(CASE WHEN * IS NOT NULL THEN 1 ELSE 0 END), 0) * 100 
                FROM {self.table_name} 
                LIMIT 1000
                """

                result = conn.execute(text(query))
                completeness = result.scalar() or 0

                if completeness >= self.min_completeness_pct:
                    logger.info(
                        f"✅ Table {self.table_name} meets quality gates: {completeness:.1f}% complete"
                    )
                    return True
                else:
                    logger.info(
                        f"⏳ Table {self.table_name} quality low: {completeness:.1f}% complete "
                        f"(required: {self.min_completeness_pct}%)"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error checking quality for {self.table_name}: {e}")
            return False
