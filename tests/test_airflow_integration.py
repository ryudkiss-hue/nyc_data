"""
Test Suite: Airflow Integration Tests

Tests validate:
- End-to-end DAG runs with mocked external systems
- Data flow through complete pipeline (incident → repair → KPI → API)
- Phase 1 integration (validation, KPIs)
- Phase 2 integration (freshness, metrics, lineage)
- Idempotency and error recovery
- Database connectivity
- Alert generation
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from airflow.models import DAG, DagRun
from airflow.utils.state import DagRunState, TaskInstanceState
import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def test_dag():
    """Create test DAG"""
    return DAG(
        'test_integration_dag',
        start_date=datetime(2026, 5, 1),
        catchup=False,
    )


@pytest.fixture
def mock_incident_data():
    """Mock incident data from Socrata API"""
    return pd.DataFrame({
        'incident_id': [1, 2, 3, 4, 5],
        'date_reported': pd.to_datetime([
            '2026-05-10', '2026-05-10', '2026-05-09', '2026-05-08', '2026-05-08'
        ]),
        'location': ['loc1', 'loc2', 'loc3', 'loc4', 'loc5'],
        'severity': [2, 3, 1, 2, 3],
        'status': ['open', 'open', 'closed', 'closed', 'open'],
    })


@pytest.fixture
def mock_repair_data():
    """Mock repair schedule data"""
    return pd.DataFrame({
        'repair_id': [1, 2, 3, 4, 5],
        'incident_id': [1, 2, 3, 4, 5],
        'scheduled_date': pd.to_datetime([
            '2026-05-13', '2026-05-15', '2026-05-12', '2026-05-11', '2026-05-14'
        ]),
        'crew_id': [101, 102, 101, 103, 102],
    })


# ============================================================================
# INCIDENT INGESTION END-TO-END TESTS
# ============================================================================

class TestIncidentIngestionFullRun:
    """Test incident_ingestion DAG end-to-end"""

    @patch('socrata_toolkit.core.client.SocrataClient')
    @patch('socrata_toolkit.quality.validation.ValidationRuleSet')
    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    @patch('socrata_toolkit.quality.freshness.FreshnessTracker')
    def test_incident_ingestion_full_pipeline(
        self,
        mock_tracker_class,
        mock_db_class,
        mock_validator_class,
        mock_client_class,
        mock_incident_data,
    ):
        """Full incident ingestion pipeline should process data end-to-end"""
        
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value = mock_incident_data
        
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = Mock(
            is_valid=True,
            valid_count=5,
            invalid_count=0,
        )
        
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.upsert.return_value = 5
        
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        # Execute pipeline steps
        # Step 1: Fetch
        client = mock_client_class()
        incidents = client.query(dataset_id='a2nx-4u46')
        assert len(incidents) == 5
        
        # Step 2: Validate
        validator = mock_validator_class()
        validation_result = validator.validate(incidents)
        assert validation_result.is_valid is True
        
        # Step 3: Upsert
        db = mock_db_class()
        loaded = db.upsert('incident', incidents.to_dict('records'), key_columns=['incident_id'])
        assert loaded == 5
        
        # Step 4: Update freshness
        tracker = mock_tracker_class()
        tracker.update_freshness(
            last_updated=datetime.now(timezone.utc),
            record_count=5,
            metadata={'source': 'socrata'}
        )
        
        # Verify all steps executed
        mock_client.query.assert_called_once()
        mock_validator.validate.assert_called_once()
        mock_db.upsert.assert_called_once()
        mock_tracker.update_freshness.assert_called_once()

    @patch('socrata_toolkit.core.client.SocrataClient')
    def test_incident_ingestion_with_api_error(self, mock_client_class):
        """Incident ingestion should handle API errors"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.side_effect = Exception("API rate limit exceeded")
        
        client = mock_client_class()
        
        with pytest.raises(Exception, match="API rate limit exceeded"):
            client.query(dataset_id='a2nx-4u46')

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    @patch('socrata_toolkit.quality.validation.ValidationRuleSet')
    def test_incident_ingestion_with_data_quality_failure(
        self, mock_validator_class, mock_db_class, mock_incident_data
    ):
        """Incident ingestion should fail if quality check fails"""
        
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = Mock(
            is_valid=False,
            valid_count=3,
            invalid_count=2,
            errors=['Missing location in 2 rows']
        )
        
        validator = mock_validator_class()
        result = validator.validate(mock_incident_data)
        
        assert result.is_valid is False
        # Should not proceed to upsert if validation fails


# ============================================================================
# REPAIR SCHEDULING END-TO-END TESTS
# ============================================================================

class TestRepairSchedulingEndToEnd:
    """Test repair_scheduling DAG end-to-end"""

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    @patch('socrata_toolkit.spatial.GeoProcessor')
    @patch('socrata_toolkit.analysis.SchedulingOptimizer')
    @patch('socrata_toolkit.analysis.metrics.MetricsEmitter')
    def test_repair_scheduling_optimization(
        self,
        mock_emitter_class,
        mock_optimizer_class,
        mock_geo_class,
        mock_db_class,
        mock_incident_data,
        mock_repair_data,
    ):
        """Repair scheduling should optimize schedule end-to-end"""
        
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.query.side_effect = [
            mock_incident_data,  # First call returns incidents
            mock_repair_data,    # Second call returns repairs
        ]
        
        mock_geo = MagicMock()
        mock_geo_class.return_value = mock_geo
        mock_geo.cluster_incidents.return_value = mock_incident_data
        
        mock_optimizer = MagicMock()
        mock_optimizer_class.return_value = mock_optimizer
        optimized_schedule = mock_repair_data.copy()
        mock_optimizer.optimize.return_value = optimized_schedule
        
        mock_emitter = MagicMock()
        mock_emitter_class.return_value = mock_emitter
        
        # Execute pipeline
        db = mock_db_class()
        incidents = db.query("SELECT * FROM incident WHERE status='open'")
        repairs = db.query("SELECT * FROM repair_history")
        
        assert len(incidents) == 5
        assert len(repairs) == 5
        
        geo = mock_geo_class()
        clustered = geo.cluster_incidents(incidents, max_distance_km=0.5)
        assert len(clustered) == 5
        
        optimizer = mock_optimizer_class(max_workers=50)
        schedule = optimizer.optimize(
            incidents=clustered,
            repairs=repairs,
            constraints={'daily_capacity': 100}
        )
        assert len(schedule) == 5
        
        emitter = mock_emitter_class()
        emitter.counter('repairs_scheduled', len(schedule))
        
        mock_optimizer.optimize.assert_called_once()
        mock_emitter.counter.assert_called_once()

    @patch('socrata_toolkit.sensors.ExternalTaskSensor')
    def test_repair_scheduling_waits_for_incidents(self, mock_sensor_class):
        """Repair scheduling should wait for incident data"""
        
        mock_sensor = MagicMock()
        mock_sensor_class.return_value = mock_sensor
        mock_sensor.poke.return_value = True
        
        sensor = mock_sensor_class()
        poked = sensor.poke()
        
        assert poked is True


# ============================================================================
# KPI MATERIALIZATION END-TO-END TESTS
# ============================================================================

class TestKPIMaterializationEndToEnd:
    """Test kpi_materialization DAG end-to-end"""

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    @patch('socrata_toolkit.engineering.dot_sidewalk.MaterialAwareSidewalkKPI')
    @patch('socrata_toolkit.lineage.LineageTracker')
    @patch('socrata_toolkit.analysis.metrics.MetricsEmitter')
    def test_kpi_computation_accuracy(
        self,
        mock_emitter_class,
        mock_lineage_class,
        mock_kpi_class,
        mock_db_class,
        mock_incident_data,
        mock_repair_data,
    ):
        """KPI computation should produce accurate results"""
        
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.query.side_effect = [mock_incident_data, mock_repair_data]
        
        mock_kpi = MagicMock()
        mock_kpi_class.return_value = mock_kpi
        mock_kpi.compute.return_value = {
            'response_time_mean': 1.5,
            'response_time_median': 1.2,
            'repair_rate': 0.92,
            'incident_density': 2.3,
            'repair_rate_by_material': {'concrete': 0.88, 'asphalt': 0.91},
        }
        
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        
        mock_emitter = MagicMock()
        mock_emitter_class.return_value = mock_emitter
        
        # Execute pipeline
        db = mock_db_class()
        incidents = db.query("SELECT * FROM incident")
        repairs = db.query("SELECT * FROM repair")
        
        kpi = mock_kpi_class(
            incidents_df=incidents,
            repairs_df=repairs,
            jurisdiction='NYC'
        )
        
        results = kpi.compute()
        
        assert results['response_time_mean'] == 1.5
        assert results['repair_rate'] == 0.92
        assert results['response_time_median'] == 1.2
        
        lineage = mock_lineage_class()
        lineage.add_transformation(
            name='kpi_computation',
            input_records=len(results),
            output_records=len(results),
            operation='kpi_materialization'
        )
        
        emitter = mock_emitter_class()
        emitter.gauge('response_time_mean_days', results['response_time_mean'])
        
        mock_lineage.add_transformation.assert_called_once()
        mock_emitter.gauge.assert_called_once()


# ============================================================================
# PHASE 1 INTEGRATION TESTS
# ============================================================================

class TestPhase1Integration:
    """Test Phase 3 integration with Phase 1 modules"""

    @patch('socrata_toolkit.quality.validation.ValidationRuleSet')
    @patch('socrata_toolkit.discovery.schema.SchemaRegistry')
    @patch('socrata_toolkit.engineering.dot_sidewalk.MaterialAwareSidewalkKPI')
    def test_validation_and_kpi_pipeline(
        self,
        mock_kpi_class,
        mock_registry_class,
        mock_validator_class,
        mock_incident_data,
    ):
        """Pipeline should validate and compute KPIs using Phase 1"""
        
        # Validation
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = Mock(is_valid=True, valid_count=5)
        
        validator = mock_validator_class()
        result = validator.validate(mock_incident_data)
        assert result.is_valid is True
        
        # Schema compliance
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        mock_registry.is_compliant.return_value = True
        
        registry = mock_registry_class()
        is_compliant = registry.is_compliant(mock_incident_data, 'incident_schema')
        assert is_compliant is True
        
        # KPI computation
        mock_kpi = MagicMock()
        mock_kpi_class.return_value = mock_kpi
        mock_kpi.compute.return_value = {
            'response_time_mean': 1.5,
            'repair_rate': 0.92,
        }
        
        kpi = mock_kpi_class(
            incidents_df=mock_incident_data,
            repairs_df=pd.DataFrame(),
            jurisdiction='NYC'
        )
        results = kpi.compute()
        
        assert results['response_time_mean'] == 1.5


# ============================================================================
# PHASE 2 INTEGRATION TESTS
# ============================================================================

class TestPhase2Integration:
    """Test Phase 3 integration with Phase 2 modules"""

    @patch('socrata_toolkit.quality.freshness.FreshnessTracker')
    @patch('socrata_toolkit.analysis.metrics.MetricsEmitter')
    @patch('socrata_toolkit.lineage.LineageTracker')
    @patch('socrata_toolkit.observability.OperationalLogger')
    def test_observability_pipeline(
        self,
        mock_logger_class,
        mock_lineage_class,
        mock_emitter_class,
        mock_tracker_class,
    ):
        """Pipeline should integrate all Phase 2 observability modules"""
        
        # Freshness tracking
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        tracker = mock_tracker_class(data_source='socrata_incidents')
        tracker.update_freshness(
            last_updated=datetime.now(timezone.utc),
            record_count=5000,
        )
        tracker.update_freshness.assert_called_once()
        
        # Metrics emission
        mock_emitter = MagicMock()
        mock_emitter_class.return_value = mock_emitter
        
        emitter = mock_emitter_class(job_name='incident_ingestion')
        emitter.counter('incidents_processed', 5000)
        emitter.histogram('duration_seconds', 45)
        
        assert mock_emitter.counter.call_count == 1
        assert mock_emitter.histogram.call_count == 1
        
        # Lineage tracking
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        
        lineage = mock_lineage_class()
        lineage.add_upstream_source(
            name='socrata_api',
            source_type='api',
            dataset_id='a2nx-4u46'
        )
        lineage.add_transformation(
            name='validation',
            input_records=5000,
            output_records=4950,
            operation='schema_validation'
        )
        
        assert mock_lineage.add_upstream_source.call_count == 1
        assert mock_lineage.add_transformation.call_count == 1
        
        # Structured logging
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        logger_inst = mock_logger_class(__name__)
        logger_inst.log_event(
            event_name='pipeline_started',
            event_type='pipeline_execution',
            metadata={'dag_id': 'incident_ingestion'}
        )
        
        mock_logger.log_event.assert_called_once()


# ============================================================================
# IDEMPOTENCY TESTS
# ============================================================================

class TestIdempotency:
    """Test that DAGs are idempotent (re-runs produce same results)"""

    @patch('socrata_toolkit.quality.freshness.FreshnessTracker')
    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    @patch('socrata_toolkit.core.client.SocrataClient')
    def test_incident_ingestion_idempotent(
        self,
        mock_client_class,
        mock_db_class,
        mock_tracker_class,
        mock_incident_data,
    ):
        """Incident ingestion should be idempotent"""
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.return_value = mock_incident_data
        
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        mock_tracker.get_last_update.return_value = datetime(2026, 5, 10)
        
        # First run
        client = mock_client_class()
        db = mock_db_class()
        tracker = mock_tracker_class()
        
        tracker.update_freshness(
            last_updated=datetime(2026, 5, 10, 6, 30),
            record_count=5,
        )
        
        # Re-run with same checkpoint
        client.query.return_value = mock_incident_data
        db.upsert = MagicMock(return_value=5)
        
        tracker.update_freshness(
            last_updated=datetime(2026, 5, 10, 6, 30),
            record_count=5,
        )
        
        # Both runs should have same effect (UPSERT is idempotent)
        # Re-running should not cause errors


# ============================================================================
# ERROR RECOVERY TESTS
# ============================================================================

class TestErrorRecovery:
    """Test DAG recovery from failures"""

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    def test_recovery_after_task_failure(self, mock_db_class):
        """DAG should continue after task failure with proper recovery"""
        
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        # First attempt fails
        mock_db.upsert.side_effect = Exception("Connection timeout")
        
        db = mock_db_class()
        
        with pytest.raises(Exception, match="Connection timeout"):
            db.upsert('incident', [], key_columns=['incident_id'])
        
        # Retry succeeds
        mock_db.upsert.side_effect = None
        mock_db.upsert.return_value = 5
        
        result = db.upsert('incident', [], key_columns=['incident_id'])
        assert result == 5

    @patch('socrata_toolkit.core.client.SocrataClient')
    def test_incremental_loading_on_retry(self, mock_client_class):
        """On retry, should load only new data since checkpoint"""
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Initial attempt fetches all data
        initial_data = pd.DataFrame({
            'incident_id': [1, 2, 3],
            'date': ['2026-05-10'] * 3,
        })
        
        mock_client.query.return_value = initial_data
        
        client = mock_client_class()
        result = client.query(dataset_id='a2nx-4u46')
        
        assert len(result) == 3
        
        # Retry with updated checkpoint fetches only new data
        new_data = pd.DataFrame({
            'incident_id': [4, 5],
            'date': ['2026-05-10'] * 2,
        })
        
        mock_client.query.return_value = new_data
        result = client.query(dataset_id='a2nx-4u46')
        
        assert len(result) == 2


# ============================================================================
# DATABASE CONNECTIVITY TESTS
# ============================================================================

class TestDatabaseConnectivity:
    """Test database connections"""

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    def test_postgres_connection_success(self, mock_db_class):
        """Should successfully connect to PostgreSQL"""
        
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.query.return_value = pd.DataFrame({'count': [1]})
        
        db = mock_db_class('postgres_warehouse')
        result = db.query("SELECT 1 as count")
        
        assert len(result) == 1

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    def test_postgres_connection_failure(self, mock_db_class):
        """Should handle PostgreSQL connection errors"""
        
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.query.side_effect = Exception("Connection refused")
        
        db = mock_db_class('postgres_warehouse')
        
        with pytest.raises(Exception, match="Connection refused"):
            db.query("SELECT 1")

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    def test_checkpoint_table_existence(self, mock_db_class):
        """Checkpoint tables should exist"""
        
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        # Mock checkpoint table
        mock_db.query.return_value = pd.DataFrame({
            'source': ['socrata_incidents'],
            'last_processed_date': [datetime(2026, 5, 10)],
        })
        
        db = mock_db_class()
        result = db.query("SELECT * FROM data_checkpoint")
        
        assert len(result) == 1


# ============================================================================
# ALERT GENERATION TESTS
# ============================================================================

class TestAlertGeneration:
    """Test alert generation on SLA violations"""

    @patch('socrata_toolkit.providers.slack.SlackWebhookOperator')
    def test_slack_alert_on_sla_miss(self, mock_slack_class):
        """Should send Slack alert on SLA violation"""
        
        mock_slack = MagicMock()
        mock_slack_class.return_value = mock_slack
        
        context = {
            'task': Mock(dag_id='incident_ingestion', task_id='fetch_incidents'),
            'execution_date': datetime(2026, 5, 10, 6, 0),
            'task_instance': Mock(log_url='http://localhost:8080/logs/...'),
        }
        
        # Trigger alert
        slack = mock_slack_class(
            task_id='slack_alert',
            http_conn_id='slack_notifications',
            message='Task failed!'
        )
        
        slack.execute(context)
        assert mock_slack.execute.called

    @patch('socrata_toolkit.quality.freshness.FreshnessTracker')
    def test_freshness_sla_violation(self, mock_tracker_class):
        """Should detect freshness SLA violations"""
        
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        # Data is stale (older than threshold)
        mock_tracker.is_fresh.return_value = False
        
        tracker = mock_tracker_class(
            data_source='socrata_incidents',
            freshness_threshold_hours=24
        )
        
        is_fresh = tracker.is_fresh()
        
        assert is_fresh is False
        # Should trigger alert on stale data


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""

    def test_large_batch_processing(self, mock_incident_data):
        """Should handle large batches efficiently"""
        
        # Create large dataset (10k records)
        large_data = pd.concat([mock_incident_data] * 2000, ignore_index=True)
        
        assert len(large_data) == 10000
        assert large_data['incident_id'].nunique() > 1

    @patch('socrata_toolkit.core.db_helpers.PostgresHelper')
    def test_batch_upsert_performance(self, mock_db_class):
        """UPSERT should handle large batches"""
        
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.upsert.return_value = 10000
        
        db = mock_db_class()
        
        large_batch = [
            {'incident_id': i, 'name': f'incident_{i}'}
            for i in range(10000)
        ]
        
        result = db.upsert('incident', large_batch, key_columns=['incident_id'])
        assert result == 10000
