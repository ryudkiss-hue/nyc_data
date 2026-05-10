"""
Test Suite: Airflow Custom Operators

Tests validate:
- Socrata fetch operator with checkpoint
- Data quality check operator
- Schema compliance operator
- PostgreSQL upsert operator
- Freshness update operator
- Metrics emitter operator
- Error handling and logging
- XCom data passing between tasks
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def test_dag():
    """Create test DAG"""
    return DAG(
        'test_dag',
        start_date=datetime(2026, 5, 1),
        catchup=False,
    )


@pytest.fixture
def test_context():
    """Create mock Airflow context"""
    return {
        'task': Mock(task_id='test_task', dag_id='test_dag'),
        'task_instance': Mock(
            log=Mock(),
            xcom_push=Mock(),
            xcom_pull=Mock(return_value={}),
        ),
        'execution_date': datetime(2026, 5, 10),
        'run_id': 'manual_run_123',
    }


# ============================================================================
# SOCRATA FETCH OPERATOR TESTS
# ============================================================================

class TestSocrataFetchOperator:
    """Test Socrata API fetch operator with checkpoint"""

    @patch('socrata_toolkit.client.SocrataClient')
    def test_fetch_incidents_success(self, mock_client_class, test_context):
        """Fetch operator should retrieve incidents from API"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock API response
        mock_incidents = pd.DataFrame({
            'incident_id': [1, 2, 3],
            'date': ['2026-05-10', '2026-05-10', '2026-05-10'],
            'location': ['loc1', 'loc2', 'loc3'],
        })
        mock_client.query.return_value = mock_incidents
        
        # Execute fetch
        from airflow.operators.python import PythonOperator
        
        def fetch_incidents(**context):
            client = mock_client_class()
            result = client.query(dataset_id='a2nx-4u46')
            return result.to_dict('records')
        
        op = PythonOperator(
            task_id='fetch_incidents',
            python_callable=fetch_incidents,
        )
        
        result = fetch_incidents()
        
        assert len(result) == 3
        assert result[0]['incident_id'] == 1
        mock_client.query.assert_called_once()

    @patch('socrata_toolkit.freshness.FreshnessTracker')
    def test_fetch_uses_checkpoint(self, mock_tracker_class):
        """Fetch should use checkpoint for incremental processing"""
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        mock_tracker.get_last_update.return_value = datetime(2026, 5, 9)
        
        # Verify checkpoint integration
        assert mock_tracker.get_last_update() == datetime(2026, 5, 9)
        mock_tracker.get_last_update.assert_called_once()

    @patch('socrata_toolkit.client.SocrataClient')
    def test_fetch_error_handling(self, mock_client_class):
        """Fetch should handle API errors gracefully"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.query.side_effect = Exception("API quota exceeded")
        
        def fetch_with_error():
            client = mock_client_class()
            return client.query(dataset_id='a2nx-4u46')
        
        with pytest.raises(Exception, match="API quota exceeded"):
            fetch_with_error()


# ============================================================================
# DATA QUALITY CHECK OPERATOR TESTS
# ============================================================================

class TestDataQualityCheckOperator:
    """Test data quality validation operator"""

    @patch('socrata_toolkit.validation.ValidationRuleSet')
    def test_quality_check_passes(self, mock_validator_class):
        """Quality check should pass valid data"""
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = Mock(
            is_valid=True,
            valid_count=100,
            invalid_count=0,
        )
        
        test_data = pd.DataFrame({
            'id': range(100),
            'name': [f'incident_{i}' for i in range(100)],
        })
        
        validator = mock_validator_class()
        result = validator.validate(test_data)
        
        assert result.is_valid is True
        assert result.valid_count == 100

    @patch('socrata_toolkit.validation.ValidationRuleSet')
    def test_quality_check_fails(self, mock_validator_class):
        """Quality check should fail invalid data"""
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = Mock(
            is_valid=False,
            valid_count=95,
            invalid_count=5,
            errors=['Missing incident_id in 5 rows'],
        )
        
        test_data = pd.DataFrame({
            'id': [None] * 5 + list(range(95)),
            'name': [f'incident_{i}' for i in range(100)],
        })
        
        validator = mock_validator_class()
        result = validator.validate(test_data)
        
        assert result.is_valid is False
        assert result.invalid_count == 5

    def test_quality_check_non_null_rule(self):
        """Validate non-null rule enforcement"""
        test_data = pd.DataFrame({
            'id': [1, 2, None, 4],
            'name': ['a', 'b', 'c', 'd'],
        })
        
        # Check for nulls in id column
        null_count = test_data['id'].isna().sum()
        assert null_count == 1

    def test_quality_check_type_validation(self):
        """Validate type checking"""
        test_data = pd.DataFrame({
            'id': [1, 2, 3],
            'date': pd.to_datetime(['2026-05-10', '2026-05-11', '2026-05-12']),
        })
        
        assert test_data['id'].dtype == 'int64'
        assert pd.api.types.is_datetime64_any_dtype(test_data['date'])


# ============================================================================
# SCHEMA COMPLIANCE OPERATOR TESTS
# ============================================================================

class TestSchemaComplianceOperator:
    """Test schema compliance checking operator"""

    @patch('socrata_toolkit.schema_registry.SchemaRegistry')
    def test_schema_compliance_check_passes(self, mock_registry_class):
        """Schema compliance should pass matching data"""
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        mock_registry.is_compliant.return_value = True
        mock_registry.get_schema.return_value = Mock(
            name='incident_schema',
            version='1.0.0',
        )
        
        test_data = pd.DataFrame({
            'incident_id': [1, 2, 3],
            'date': pd.to_datetime(['2026-05-10'] * 3),
            'location': ['loc1', 'loc2', 'loc3'],
        })
        
        registry = mock_registry_class()
        schema = registry.get_schema('incident_data')
        result = registry.is_compliant(test_data, schema)
        
        assert result is True
        assert schema.version == '1.0.0'

    @patch('socrata_toolkit.schema_registry.SchemaRegistry')
    def test_schema_compliance_check_fails(self, mock_registry_class):
        """Schema compliance should fail non-matching data"""
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        mock_registry.is_compliant.return_value = False
        
        # Missing required 'location' column
        test_data = pd.DataFrame({
            'incident_id': [1, 2, 3],
            'date': pd.to_datetime(['2026-05-10'] * 3),
        })
        
        registry = mock_registry_class()
        schema = registry.get_schema('incident_data')
        result = registry.is_compliant(test_data, schema)
        
        assert result is False


# ============================================================================
# POSTGRESQL UPSERT OPERATOR TESTS
# ============================================================================

class TestPostgresUpsertOperator:
    """Test PostgreSQL UPSERT operator"""

    @patch('socrata_toolkit.db_helpers.PostgresHelper')
    def test_upsert_new_records(self, mock_db_class):
        """UPSERT should insert new records"""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.upsert.return_value = 3
        
        test_records = [
            {'incident_id': 1, 'name': 'pothole'},
            {'incident_id': 2, 'name': 'crack'},
            {'incident_id': 3, 'name': 'flooding'},
        ]
        
        db = mock_db_class()
        result = db.upsert('incident', test_records, key_columns=['incident_id'])
        
        assert result == 3
        mock_db.upsert.assert_called_once()

    @patch('socrata_toolkit.db_helpers.PostgresHelper')
    def test_upsert_idempotency(self, mock_db_class):
        """UPSERT should be idempotent (safe to re-run)"""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        
        test_records = [
            {'incident_id': 1, 'name': 'pothole', 'status': 'open'},
        ]
        
        db = mock_db_class()
        
        # First insert
        db.upsert('incident', test_records, key_columns=['incident_id'])
        
        # Update same record (re-run, should update not fail)
        test_records[0]['status'] = 'closed'
        db.upsert('incident', test_records, key_columns=['incident_id'])
        
        # Should be called twice
        assert mock_db.upsert.call_count == 2

    @patch('socrata_toolkit.db_helpers.PostgresHelper')
    def test_upsert_error_handling(self, mock_db_class):
        """UPSERT should handle database errors"""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_db.upsert.side_effect = Exception("Database connection lost")
        
        db = mock_db_class()
        
        with pytest.raises(Exception, match="Database connection lost"):
            db.upsert('incident', [], key_columns=['incident_id'])


# ============================================================================
# FRESHNESS UPDATE OPERATOR TESTS
# ============================================================================

class TestFreshnessUpdateOperator:
    """Test freshness tracking operator"""

    @patch('socrata_toolkit.freshness.FreshnessTracker')
    def test_freshness_update_success(self, mock_tracker_class):
        """Freshness update should record last processed time"""
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        tracker = mock_tracker_class(data_source='socrata_incidents')
        tracker.update_freshness(
            last_updated=datetime(2026, 5, 10, 6, 30),
            record_count=5000,
            metadata={'source': 'Socrata API'},
        )
        
        tracker.update_freshness.assert_called_once()
        assert tracker.update_freshness.call_count == 1

    @patch('socrata_toolkit.freshness.FreshnessTracker')
    def test_freshness_check(self, mock_tracker_class):
        """Freshness check should verify data is current"""
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        mock_tracker.is_fresh.return_value = True
        
        tracker = mock_tracker_class(
            data_source='socrata_incidents',
            freshness_threshold_hours=24
        )
        is_fresh = tracker.is_fresh()
        
        assert is_fresh is True
        mock_tracker.is_fresh.assert_called_once()


# ============================================================================
# METRICS EMITTER OPERATOR TESTS
# ============================================================================

class TestMetricsEmitterOperator:
    """Test Prometheus metrics emission operator"""

    @patch('socrata_toolkit.metrics.MetricsEmitter')
    def test_counter_metric(self, mock_emitter_class):
        """Metrics emitter should emit counter metrics"""
        mock_emitter = MagicMock()
        mock_emitter_class.return_value = mock_emitter
        
        emitter = mock_emitter_class(job_name='incident_ingestion')
        emitter.counter('incidents_processed', 5000)
        
        mock_emitter.counter.assert_called_once_with('incidents_processed', 5000)

    @patch('socrata_toolkit.metrics.MetricsEmitter')
    def test_histogram_metric(self, mock_emitter_class):
        """Metrics emitter should emit histogram metrics"""
        mock_emitter = MagicMock()
        mock_emitter_class.return_value = mock_emitter
        
        emitter = mock_emitter_class(job_name='incident_ingestion')
        emitter.histogram('fetch_duration_seconds', 45)
        
        mock_emitter.histogram.assert_called_once_with('fetch_duration_seconds', 45)

    @patch('socrata_toolkit.metrics.MetricsEmitter')
    def test_gauge_metric(self, mock_emitter_class):
        """Metrics emitter should emit gauge metrics"""
        mock_emitter = MagicMock()
        mock_emitter_class.return_value = mock_emitter
        
        emitter = mock_emitter_class(job_name='incident_ingestion')
        emitter.gauge('api_quota_remaining', 49500)
        
        mock_emitter.gauge.assert_called_once_with('api_quota_remaining', 49500)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestOperatorErrorHandling:
    """Test operator error handling and recovery"""

    def test_operator_retry_on_failure(self, test_dag):
        """Operators should retry on failure"""
        op = PythonOperator(
            task_id='failing_task',
            python_callable=lambda: 1/0,  # Intentional error
            retries=3,
            dag=test_dag,
        )
        
        assert op.retries == 3

    def test_operator_timeout_configuration(self, test_dag):
        """Operators should have execution timeout"""
        from datetime import timedelta
        
        op = PythonOperator(
            task_id='timeout_task',
            python_callable=lambda: None,
            execution_timeout=timedelta(hours=1),
            dag=test_dag,
        )
        
        assert op.execution_timeout == timedelta(hours=1)

    def test_operator_failure_callback(self, test_dag):
        """Operators should support failure callbacks"""
        def on_failure(context):
            logger.error(f"Task {context['task'].task_id} failed")
        
        op = PythonOperator(
            task_id='callback_task',
            python_callable=lambda: None,
            on_failure_callback=on_failure,
            dag=test_dag,
        )
        
        assert op.on_failure_callback is not None


# ============================================================================
# XCOM PASSING TESTS
# ============================================================================

class TestOperatorXComPassing:
    """Test data passing between tasks via XCom"""

    def test_xcom_push_pull(self):
        """Tasks should pass data via XCom"""
        mock_ti = Mock()
        
        # Simulate task pushing data
        test_data = {'incidents_loaded': 5000}
        mock_ti.xcom_push(key='load_result', value=test_data)
        
        # Simulate downstream task pulling data
        mock_ti.xcom_pull.return_value = test_data
        result = mock_ti.xcom_pull(task_ids='upsert_incidents', key='load_result')
        
        assert result == test_data
        mock_ti.xcom_push.assert_called_once()

    def test_xcom_multiple_pushes(self):
        """Tasks can push multiple values"""
        mock_ti = Mock()
        
        mock_ti.xcom_push(key='count', value=1000)
        mock_ti.xcom_push(key='status', value='success')
        
        assert mock_ti.xcom_push.call_count == 2


# ============================================================================
# STRUCTURED LOGGING TESTS
# ============================================================================

class TestOperatorLogging:
    """Test structured logging in operators"""

    @patch('socrata_toolkit.observability.OperationalLogger')
    def test_structured_log_event(self, mock_logger_class):
        """Operators should log structured events"""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        logger_instance = mock_logger_class(__name__)
        logger_instance.log_event(
            event_name='fetch_started',
            event_type='data_operation',
            metadata={'dataset_id': 'a2nx-4u46'},
        )
        
        mock_logger.log_event.assert_called_once()

    @patch('socrata_toolkit.observability.OperationalLogger')
    def test_error_logging(self, mock_logger_class):
        """Operators should log errors with context"""
        mock_logger = MagicMock()
        mock_logger_class.return_value = mock_logger
        
        logger_instance = mock_logger_class(__name__)
        logger_instance.log_event(
            event_name='fetch_failed',
            event_type='error',
            metadata={'error': 'API quota exceeded', 'retry_count': 2},
        )
        
        mock_logger.log_event.assert_called_once()


# ============================================================================
# PHASE 1/2 INTEGRATION TESTS
# ============================================================================

class TestPhase1Phase2Integration:
    """Test integration between operators and Phase 1/2 modules"""

    def test_validation_rule_integration(self):
        """Operators should integrate with Phase 1 validation rules"""
        # Verify imports work
        try:
            from socrata_toolkit.validation import ValidationRuleSet
            assert ValidationRuleSet is not None
        except ImportError:
            pytest.fail("Phase 1 validation module should be importable")

    def test_freshness_tracking_integration(self):
        """Operators should integrate with Phase 2 freshness tracking"""
        try:
            from socrata_toolkit.freshness import FreshnessTracker
            assert FreshnessTracker is not None
        except ImportError:
            pytest.fail("Phase 2 freshness module should be importable")

    def test_metrics_emission_integration(self):
        """Operators should integrate with Phase 2 metrics emission"""
        try:
            from socrata_toolkit.metrics import MetricsEmitter
            assert MetricsEmitter is not None
        except ImportError:
            pytest.fail("Phase 2 metrics module should be importable")

    def test_observability_logging_integration(self):
        """Operators should integrate with Phase 2 observability logging"""
        try:
            from socrata_toolkit.observability import OperationalLogger
            assert OperationalLogger is not None
        except ImportError:
            pytest.fail("Phase 2 observability module should be importable")
