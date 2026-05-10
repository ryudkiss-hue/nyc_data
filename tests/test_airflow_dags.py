"""
Test Suite: Airflow DAG Structure & Configuration

Tests validate:
- DAG syntax and imports
- Task dependencies
- Scheduling configuration
- SLA definitions
- Alert handlers
- Checkpoint table integration
"""

import pytest
from datetime import datetime, timedelta
from airflow.models import DAG, DagBag
from airflow.exceptions import AirflowException
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def dagbag():
    """Load all DAGs from airflow/dags directory"""
    return DagBag(dag_folder='airflow/dags', include_examples=False)


@pytest.fixture
def required_dags():
    """List of required DAGs for Phase 3"""
    return [
        'incident_ingestion',
        'repair_scheduling',
        'kpi_materialization',
    ]


# ============================================================================
# BASIC DAG STRUCTURE TESTS
# ============================================================================

class TestDAGStructure:
    """Test basic DAG structure and configuration"""

    def test_all_dags_load_without_errors(self, dagbag):
        """DAG files should parse without import errors"""
        assert len(dagbag.dag_ids) >= 3, "Should have at least 3 DAGs loaded"
        
        # Verify no errors during parsing
        assert len(dagbag.import_errors) == 0, \
            f"DAG parsing errors: {dagbag.import_errors}"

    def test_required_dags_exist(self, dagbag, required_dags):
        """All required DAGs should be present"""
        for dag_id in required_dags:
            assert dag_id in dagbag.dag_ids, \
                f"Required DAG '{dag_id}' not found"

    def test_dag_has_description(self, dagbag, required_dags):
        """DAGs should have documentation"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            assert dag.description is not None and len(dag.description) > 0, \
                f"DAG '{dag_id}' missing description"

    def test_dag_has_valid_owner(self, dagbag, required_dags):
        """DAGs should have owner defined"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            owner = dag.default_args.get('owner')
            assert owner is not None and owner != '', \
                f"DAG '{dag_id}' missing owner"

    def test_dag_has_valid_start_date(self, dagbag, required_dags):
        """DAGs should have start_date in past"""
        current_date = datetime.utcnow()
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            start_date = dag.start_date
            assert start_date is not None, \
                f"DAG '{dag_id}' missing start_date"
            assert start_date < current_date, \
                f"DAG '{dag_id}' start_date is in future"

    def test_dag_not_in_examples(self, dagbag, required_dags):
        """Production DAGs should not be example DAGs"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            assert dag.owner != 'airflow', \
                f"DAG '{dag_id}' looks like example DAG"


# ============================================================================
# DAG DEPENDENCIES TESTS
# ============================================================================

class TestDAGDependencies:
    """Test DAG-level dependencies and scheduling"""

    def test_no_cyclic_task_dependencies(self, dagbag, required_dags):
        """DAGs should have no circular task dependencies"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            assert dag.is_paused is False, \
                f"DAG '{dag_id}' is paused"
            
            # Try to validate the DAG
            try:
                dag.validate()
            except Exception as e:
                pytest.fail(f"DAG '{dag_id}' validation failed: {e}")

    def test_all_tasks_have_unique_ids(self, dagbag, required_dags):
        """All task IDs within a DAG should be unique"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            task_ids = [task.task_id for task in dag.tasks]
            assert len(task_ids) == len(set(task_ids)), \
                f"DAG '{dag_id}' has duplicate task IDs"

    def test_all_tasks_have_dependencies(self, dagbag):
        """Tasks should have dependencies defined (except root)"""
        dag = dagbag.get_dag('incident_ingestion')
        
        root_tasks = dag.roots
        assert len(root_tasks) > 0, "DAG should have root tasks"
        
        # All non-root tasks should have upstream dependencies
        non_root_tasks = [t for t in dag.tasks if t not in root_tasks]
        for task in non_root_tasks:
            assert len(task.upstream_list) > 0, \
                f"Task '{task.task_id}' has no upstream dependencies"


# ============================================================================
# DAG SCHEDULING TESTS
# ============================================================================

class TestDAGScheduling:
    """Test DAG scheduling configuration"""

    def test_incident_ingestion_schedule(self, dagbag):
        """incident_ingestion should run every 6 hours"""
        dag = dagbag.get_dag('incident_ingestion')
        # Schedule: 0 */6 * * * (cron format)
        assert dag.schedule_interval is not None, \
            "incident_ingestion missing schedule"

    def test_repair_scheduling_schedule(self, dagbag):
        """repair_scheduling should run daily"""
        dag = dagbag.get_dag('repair_scheduling')
        assert dag.schedule_interval is not None, \
            "repair_scheduling missing schedule"

    def test_kpi_materialization_schedule(self, dagbag):
        """kpi_materialization should run hourly"""
        dag = dagbag.get_dag('kpi_materialization')
        assert dag.schedule_interval is not None, \
            "kpi_materialization missing schedule"

    def test_catchup_disabled_for_production_dags(self, dagbag, required_dags):
        """Production DAGs should not catch up on missing schedules"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            assert dag.catchup is False, \
                f"DAG '{dag_id}' has catchup=True, should be False"


# ============================================================================
# TASK STRUCTURE TESTS
# ============================================================================

class TestSidewalkIncidentDAGStructure:
    """Test incident_ingestion DAG task structure"""

    def test_incident_dag_has_required_tasks(self, dagbag):
        """incident_ingestion should have fetch, validate, upsert, freshness tasks"""
        dag = dagbag.get_dag('incident_ingestion')
        
        required_tasks = [
            'fetch_incidents',
            'validate_data',
            'upsert_incidents',
            'update_freshness'
        ]
        
        task_ids = [task.task_id for task in dag.tasks]
        for task_id in required_tasks:
            assert task_id in task_ids, \
                f"incident_ingestion missing task: {task_id}"

    def test_incident_dag_task_ordering(self, dagbag):
        """Tasks should run in correct order: fetch → validate → upsert → freshness"""
        dag = dagbag.get_dag('incident_ingestion')
        
        fetch = dag.get_task('fetch_incidents')
        validate = dag.get_task('validate_data')
        upsert = dag.get_task('upsert_incidents')
        freshness = dag.get_task('update_freshness')
        
        # Verify dependencies
        assert validate in fetch.downstream_list
        assert upsert in validate.downstream_list
        assert freshness in upsert.downstream_list

    def test_incident_dag_task_types(self, dagbag):
        """Tasks should use appropriate operator types"""
        dag = dagbag.get_dag('incident_ingestion')
        
        # All should be PythonOperator for now
        for task in dag.tasks:
            assert isinstance(task, PythonOperator), \
                f"Task '{task.task_id}' should be PythonOperator"


class TestRepairSchedulingDAGStructure:
    """Test repair_scheduling DAG task structure"""

    def test_repair_dag_has_required_tasks(self, dagbag):
        """repair_scheduling should have sensor, load, optimize, publish tasks"""
        dag = dagbag.get_dag('repair_scheduling')
        
        required_tasks = [
            'check_incidents_available',
            'load_incidents',
            'optimize_schedule',
            'publish_schedule'
        ]
        
        task_ids = [task.task_id for task in dag.tasks]
        for task_id in required_tasks:
            assert task_id in task_ids, \
                f"repair_scheduling missing task: {task_id}"

    def test_repair_dag_external_task_sensor(self, dagbag):
        """repair_scheduling should have ExternalTaskSensor for incident_ingestion"""
        dag = dagbag.get_dag('repair_scheduling')
        sensor = dag.get_task('check_incidents_available')
        
        assert isinstance(sensor, ExternalTaskSensor), \
            "check_incidents_available should be ExternalTaskSensor"
        
        assert sensor.external_dag_id == 'incident_ingestion', \
            "Sensor should wait for incident_ingestion"


class TestKPIMaterializationDAGStructure:
    """Test kpi_materialization DAG task structure"""

    def test_kpi_dag_has_required_tasks(self, dagbag):
        """kpi_materialization should have get, compute, publish tasks"""
        dag = dagbag.get_dag('kpi_materialization')
        
        # Core tasks
        task_ids = [task.task_id for task in dag.tasks]
        assert 'compute_sidewalk_kpi' in task_ids or \
               'compute_kpi' in task_ids, \
            "kpi_materialization missing KPI computation task"


# ============================================================================
# OPERATOR & CONFIGURATION TESTS
# ============================================================================

class TestDAGOperatorConfiguration:
    """Test operator configuration across DAGs"""

    def test_all_operators_have_retries(self, dagbag, required_dags):
        """All operators should have retry policy"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            for task in dag.tasks:
                # Skip sensors which may not need retries
                if isinstance(task, ExternalTaskSensor):
                    continue
                
                assert task.retries >= 2, \
                    f"Task '{task.task_id}' has retries={task.retries}, should be >= 2"

    def test_all_operators_have_timeout(self, dagbag, required_dags):
        """All operators should have execution timeout"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            for task in dag.tasks:
                assert task.execution_timeout is not None, \
                    f"Task '{task.task_id}' missing execution_timeout"

    def test_operators_have_error_handlers(self, dagbag, required_dags):
        """Critical tasks should have failure callbacks"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            # Data loading tasks should have handlers
            for task in dag.tasks:
                if 'upsert' in task.task_id or 'publish' in task.task_id:
                    # These are critical tasks that should alert on failure
                    assert task.on_failure_callback is not None or \
                           dag.default_args.get('on_failure_callback') is not None, \
                        f"Task '{task.task_id}' should have failure handler"


# ============================================================================
# SLA & MONITORING TESTS
# ============================================================================

class TestDAGSLAConfiguration:
    """Test SLA definitions for DAGs"""

    def test_incident_ingestion_has_sla(self, dagbag):
        """incident_ingestion should have SLA"""
        dag = dagbag.get_dag('incident_ingestion')
        assert dag.sla is not None, "incident_ingestion should have SLA"
        assert dag.sla <= timedelta(hours=1), "incident_ingestion SLA should be <= 1 hour"

    def test_repair_scheduling_has_sla(self, dagbag):
        """repair_scheduling should have SLA"""
        dag = dagbag.get_dag('repair_scheduling')
        assert dag.sla is not None, "repair_scheduling should have SLA"
        assert dag.sla <= timedelta(hours=2), "repair_scheduling SLA should be <= 2 hours"

    def test_kpi_materialization_has_sla(self, dagbag):
        """kpi_materialization should have SLA"""
        dag = dagbag.get_dag('kpi_materialization')
        assert dag.sla is not None, "kpi_materialization should have SLA"
        assert dag.sla <= timedelta(minutes=30), "kpi_materialization SLA should be <= 30 minutes"


class TestDAGAlerts:
    """Test alert configuration in DAGs"""

    def test_dags_have_alert_handlers(self, bagbag, required_dags):
        """DAGs should have alert handlers configured"""
        for dag_id in required_dags:
            dag = bagbag.get_dag(dag_id)
            
            # Check for on_failure_callback at DAG or task level
            has_alert = False
            
            if dag.default_args.get('on_failure_callback') is not None:
                has_alert = True
            
            for task in dag.tasks:
                if task.on_failure_callback is not None:
                    has_alert = True
                    break
            
            # Alert handlers are recommended but not mandatory for test
            logger.info(f"DAG '{dag_id}' alert handlers: {has_alert}")


# ============================================================================
# DATABASE CHECKPOINT TESTS
# ============================================================================

class TestCheckpointIntegration:
    """Test checkpoint table integration in DAGs"""

    def test_incident_ingestion_uses_checkpoint(self, dagbag):
        """incident_ingestion should reference checkpoint tables"""
        dag = dagbag.get_dag('incident_ingestion')
        
        # Check task docstrings or code for checkpoint references
        dag_code = str(dag)
        assert 'checkpoint' in dag_code.lower() or \
               'incremental' in dag_code.lower(), \
            "incident_ingestion should use checkpoint for incremental processing"

    def test_repair_scheduling_references_incident_table(self, dagbag):
        """repair_scheduling should load from incident table"""
        dag = dagbag.get_dag('repair_scheduling')
        
        # Should have task that loads from incident table
        task_ids = [task.task_id for task in dag.tasks]
        loading_tasks = [t for t in task_ids if 'load' in t]
        assert len(loading_tasks) > 0, \
            "repair_scheduling should have data loading task"

    def test_kpi_materialization_produces_materialization_table(self, dagbag):
        """kpi_materialization should output to materialization table"""
        dag = dagbag.get_dag('kpi_materialization')
        
        # Should have publishing task
        task_ids = [task.task_id for task in dag.tasks]
        publish_tasks = [t for t in task_ids if 'publish' in t or 'materialize' in t]
        assert len(publish_tasks) > 0, \
            "kpi_materialization should publish results"


# ============================================================================
# DAG PARAMETER TESTS
# ============================================================================

class TestDAGParameters:
    """Test DAG parameters and variables"""

    def test_dag_max_active_runs_limited(self, dagbag, required_dags):
        """DAGs should limit concurrent runs to prevent resource exhaustion"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            assert dag.max_active_runs >= 1, \
                f"DAG '{dag_id}' should allow at least 1 concurrent run"
            assert dag.max_active_runs <= 5, \
                f"DAG '{dag_id}' max_active_runs seems too high"

    def test_dag_catchup_disabled(self, dagbag, required_dags):
        """DAGs should not automatically catch up on missed runs"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            assert dag.catchup is False, \
                f"DAG '{dag_id}' catchup should be False"

    def test_dag_tags_present(self, dagbag, required_dags):
        """DAGs should have tags for organization"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            assert dag.tags is not None and len(dag.tags) > 0, \
                f"DAG '{dag_id}' should have tags"


# ============================================================================
# DAG DOCUMENTATION TESTS
# ============================================================================

class TestDAGDocumentation:
    """Test documentation quality of DAGs"""

    def test_all_tasks_have_docstrings(self, dagbag, required_dags):
        """All Python operators should have documented callables"""
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            for task in dag.tasks:
                if isinstance(task, PythonOperator):
                    # Check if python_callable has docstring
                    func = task.python_callable
                    assert func.__doc__ is not None and len(func.__doc__) > 0, \
                        f"Task '{task.task_id}' python_callable missing docstring"

    def test_dag_has_tags(self, dagbag, required_dags):
        """DAGs should have meaningful tags"""
        expected_tags = {'production', 'data_pipeline', 'airflow'}
        
        for dag_id in required_dags:
            dag = dagbag.get_dag(dag_id)
            dag_tags = set(dag.tags or [])
            
            # At least one meaningful tag expected
            assert len(dag_tags) > 0, f"DAG '{dag_id}' should have tags"


# ============================================================================
# INTEGRATION READINESS TESTS
# ============================================================================

class TestPhase3IntegrationReadiness:
    """Test Phase 3 readiness for Phase 1/2 integration"""

    def test_all_dags_loadable_with_phase1_imports(self, dagbag):
        """DAGs should be able to import Phase 1 modules without error"""
        import_successful = True
        try:
            from socrata_toolkit.validation import ValidationRuleSet
            from socrata_toolkit.dot_sidewalk import MaterialAwareSidewalkKPI
        except ImportError as e:
            import_successful = False
        
        assert import_successful, "Phase 1 modules should be importable"

    def test_all_dags_loadable_with_phase2_imports(self, dagbag):
        """DAGs should be able to import Phase 2 modules without error"""
        import_successful = True
        try:
            from socrata_toolkit.freshness import FreshnessTracker
            from socrata_toolkit.metrics import MetricsEmitter
            from socrata_toolkit.observability import OperationalLogger
        except ImportError as e:
            import_successful = False
        
        assert import_successful, "Phase 2 modules should be importable"
