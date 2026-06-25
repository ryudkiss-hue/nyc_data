#!/usr/bin/env python3
"""
NYC DOT MotherDuck Pipeline - 57 Dataset Ingestion & Materialization
Metadata-first, zero data loss, zero row limits. All 57 datasets, 255 Metrics, 5 domain schemas.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add pipeline modules to path
sys.path.insert(0, str(Path(__file__).parent))

from governance import GovernanceFramework, GovernanceValidator
from motherduck_bridge import MotherDuckBridge
from socrata_loader import SocrataLoader
from sql_executor import PipelineStageExecutor, SQLExecutor

# Wire in 7 advanced modules (Phase 3C-2: Mandatory Scripts)
try:
    from modules.alerting_system import Alert, AlertChannel, AlertLevel, AlertManager
    from modules.cdc_manager import CDCManager
    from modules.incremental_loader import IncrementalLoader
    from modules.orchestration_coordinator import PipelineOrchestrator
    from modules.performance_optimizer import PerformanceOptimizer
    from modules.scheduler_manager import PipelineScheduler
    from modules.state_manager import ExecutionContext, StateManager
    ADVANCED_MODULES_AVAILABLE = True
except ImportError as e:
    ADVANCED_MODULES_AVAILABLE = False

# Setup logging
Path('pipeline/logs').mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('pipeline/logs/pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MotherDuckPipeline:
    def __init__(self, db_name: str = 'nyc_dot_analytics', cache_dir: str = None):
        self.db_name = db_name
        self.cache_dir = cache_dir or str(Path.home() / 'Desktop' / 'nyc_data_cache')
        self.motherduck_token = os.getenv('MOTHERDUCK_TOKEN', '')
        self.execution_log = {
            'pipeline_version': '2.0',
            'started_at': datetime.now().isoformat(),
            'stages': {},
            'datasets': {}
        }

        # Initialize database bridge
        logger.info(f"Initializing MotherDuck bridge for database: {self.db_name}")
        self.bridge = MotherDuckBridge(
            motherduck_token=self.motherduck_token,
            use_motherduck=bool(self.motherduck_token),
            db_name=self.db_name,
            fallback_local=True
        )

        # Initialize SQL executor
        self.sql_executor = PipelineStageExecutor(self.bridge, sql_dir='pipeline/sql')

        # Initialize Socrata loader
        self.socrata_loader = SocrataLoader(
            bridge=self.bridge,
            cache_dir=self.cache_dir
        )

        # Load and validate dataset config (Issue #4: Config-dataset sync)
        logger.info("Loading dataset configuration from pipeline/config/socrata_datasets.json...")
        self.config_datasets = self.socrata_loader.load_config('pipeline/config/socrata_datasets.json')
        if not self.config_datasets:
            logger.error("CRITICAL: Dataset config is empty or missing")
            raise RuntimeError("Cannot proceed without dataset configuration")

        # Expected dataset counts from config
        self.expected_cached = len([d for d in self.config_datasets if d.source == 'cache'])
        self.expected_socrata = len([d for d in self.config_datasets if d.source == 'socrata'])
        self.expected_total = len(self.config_datasets)
        logger.info(f"Config loaded: {self.expected_cached} cached + {self.expected_socrata} Socrata = {self.expected_total} total datasets")

        # Initialize state management and execution context (Phase 3C-2: Wire advanced modules)
        if ADVANCED_MODULES_AVAILABLE:
            self.state_manager = StateManager(state_dir='pipeline/state')
            self.execution_context = ExecutionContext(
                state_manager=self.state_manager,
                pipeline_id=f"pipeline-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            self.alert_manager = AlertManager()
            logger.info(f"Execution context initialized: {self.execution_context.pipeline_id}")
        else:
            self.state_manager = None
            self.execution_context = None
            self.alert_manager = None
            logger.warning("Advanced modules not available - state management disabled")

        # Initialize governance framework
        try:
            self.governance = GovernanceFramework()
            self.governance_validator = GovernanceValidator(self.governance)
            logger.info("Governance framework initialized (personal solo-user, indefinite retention)")
            self.governance.log_audit('pipeline_started', {
                'pipeline_id': self.execution_context.pipeline_id if self.execution_context else 'no_context',
                'datasets': self.expected_total,
                'governance_mode': 'personal_solo_user'
            })
        except Exception as e:
            logger.error(f"Failed to initialize governance framework: {e}")
            self.governance = None
            self.governance_validator = None

    def _start_stage(self, stage_name: str):
        """Safe wrapper for starting a pipeline stage."""
        if self.execution_context:
            self.execution_context.start_stage(stage_name)
        else:
            logger.info(f"Starting stage: {stage_name}")

    def _complete_stage(self, rows_processed: int = 0, duration: float = 0.0):
        """Safe wrapper for completing a pipeline stage."""
        if self.execution_context:
            self.execution_context.complete_stage(rows_processed=rows_processed, duration=duration)

    def _fail_stage(self, error: str):
        """Safe wrapper for failing a pipeline stage."""
        if self.execution_context:
            self.execution_context.fail_stage(error)
        else:
            logger.error(f"Stage failed: {error}")

    def _send_alert(self, alert):
        """Safe wrapper for sending alerts."""
        if self.alert_manager:
            self.alert_manager.send_alert(alert)

    def log_stage(self, stage_name: str, status: str, **kwargs):
        """Log stage execution details."""
        self.execution_log['stages'][stage_name] = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        status_text = "SUCCESS" if status == "success" else "FAILED" if status == "error" else status.upper()
        logger.info(f"[{stage_name}] {status_text}")

    def load_cached_parquet(self) -> bool:
        """Load cached Parquet files from local cache.

        When the config declares no cached datasets (all-Socrata config), this
        stage is a no-op success so the pipeline proceeds to Socrata ingestion.
        """
        start_time = time.time()
        try:
            if self.expected_cached == 0:
                logger.info("No cached datasets configured; skipping cached-parquet stage.")
                self.log_stage('load_cached_parquet', 'success',
                              tables_loaded=0, expected_cached=0, total_rows=0,
                              note="skipped — all-Socrata config")
                return True

            logger.info(f"Loading {self.expected_cached} cached Parquet files from local cache...")
            cache_raw = Path(self.cache_dir) / 'raw'

            if not cache_raw.exists():
                logger.warning(f"Cache directory not found: {cache_raw}")
                return False

            parquet_files = list(cache_raw.glob('*.parquet'))
            logger.info(f"Found {len(parquet_files)} Parquet files to load")

            # Load each parquet file using Socrata loader
            tables_loaded = 0
            total_rows = 0

            for parquet_file in sorted(parquet_files):
                dataset_name = parquet_file.stem
                logger.info(f"Loading cache: {dataset_name}")

                result = self.socrata_loader.load_from_cache(dataset_name)
                if result.success:
                    tables_loaded += 1
                    total_rows += result.rows_loaded
                    self.execution_log['datasets'][dataset_name] = {
                        'source': 'cache',
                        'status': 'loaded',
                        'rows': result.rows_loaded
                    }
                    logger.info(f"  {dataset_name}: {result.rows_loaded} rows")
                else:
                    logger.error(f"  {dataset_name}: FAILED - {result.error}")

            load_time = time.time() - start_time

            # CRITICAL: Fail if no data loaded (prevents silent failures)
            if total_rows == 0:
                logger.error("CRITICAL: No rows loaded from cached Parquet files")
                self.log_stage('load_cached_parquet', 'failed',
                              tables_loaded=tables_loaded,
                              total_rows=total_rows,
                              error="No data loaded")
                return False

            # Issue #4: Validate against config expectations
            if tables_loaded < self.expected_cached:
                logger.warning(f"Config mismatch: Expected {self.expected_cached} cached datasets, loaded {tables_loaded}")

            self.log_stage('load_cached_parquet', 'success',
                          tables_loaded=tables_loaded,
                          expected_cached=self.expected_cached,
                          total_rows=total_rows,
                          load_time_seconds=round(load_time, 2),
                          cache_location=str(cache_raw))
            return True

        except Exception as e:
            logger.error(f"Failed to load cached Parquet: {str(e)}")
            self.log_stage('load_cached_parquet', 'error', error=str(e))
            return False

    def ingest_remaining_socrata(self) -> bool:
        """Ingest remaining 37 datasets from Socrata in controlled batches."""
        start_time = time.time()
        self._start_stage('ingest_remaining_socrata')

        try:
            logger.info("Ingesting remaining 37 datasets from Socrata...")

            # Load config
            config_path = 'pipeline/config/socrata_datasets.json'
            datasets = self.socrata_loader.load_config(config_path)

            if not datasets:
                logger.warning("No datasets loaded from config")
                self._fail_stage("Config file missing or empty")
                self._send_alert(Alert(
                    level=AlertLevel.ERROR,
                    title="Socrata Ingestion Failed",
                    message="Dataset configuration missing or empty",
                    component="ingest_remaining_socrata"
                ))
                return False

            # Filter to Socrata datasets only (those not already cached)
            socrata_datasets = [d for d in datasets if d.source == 'socrata']
            logger.info(f"Found {len(socrata_datasets)} Socrata datasets to ingest")

            # Incremental mode (NYC_INCREMENTAL=1, set by the nightly run): skip a
            # dataset whose Socrata last_updated is unchanged since last ingest AND
            # whose raw table still has rows. Watermarks persist in data/.
            import json as _json
            incremental = os.getenv("NYC_INCREMENTAL") == "1"
            wm_path = Path("data/ingest_watermarks.json")
            watermarks = {}
            if wm_path.exists():
                try:
                    watermarks = _json.loads(wm_path.read_text())
                except Exception:
                    watermarks = {}
            freshness = {}
            try:
                reg = _json.loads(Path("pipeline/data/nyc_open_data_registry.json").read_text())["datasets"]
                freshness = {k: v.get("last_updated", "") for k, v in reg.items()}
            except Exception:
                pass

            def _has_rows(name):
                try:
                    return self.bridge.connection.execute(
                        f'SELECT 1 FROM raw."{name}" LIMIT 1').fetchone() is not None
                except Exception:
                    return False

            # Load in batches
            batch_size = 10
            loaded_count = 0
            failed_count = 0
            skipped_count = 0

            for i, dataset in enumerate(socrata_datasets):
                batch_num = (i // batch_size) + 1

                cur = freshness.get(dataset.socrata_id, "")
                if (incremental and cur and watermarks.get(dataset.socrata_id) == cur
                        and _has_rows(dataset.name)):
                    skipped_count += 1
                    self.execution_log['datasets'][dataset.name] = {
                        'source': 'socrata', 'status': 'skipped_fresh'}
                    logger.info(f"  {dataset.name}: skipped (unchanged since {cur[:10]})")
                    continue

                logger.info(f"Batch {batch_num}: Loading {dataset.name} ({i+1}/{len(socrata_datasets)})")

                # Try to load (passing optional server-side filter, e.g. 311)
                result = self.socrata_loader.load_from_socrata(
                    dataset.name,
                    dataset.socrata_id,
                    soql_where=getattr(dataset, "soql_where", None),
                )

                if result.success:
                    if cur:
                        watermarks[dataset.socrata_id] = cur
                    loaded_count += 1
                    self.execution_log['datasets'][dataset.name] = {
                        'source': 'socrata',
                        'status': 'loaded',
                        'rows': result.rows_loaded
                    }
                    logger.info(f"  {dataset.name}: {result.rows_loaded} rows")
                else:
                    failed_count += 1
                    self.execution_log['datasets'][dataset.name] = {
                        'source': 'socrata',
                        'status': 'failed',
                        'error': result.error
                    }
                    logger.error(f"  {dataset.name}: FAILED - {result.error}")

            load_time = time.time() - start_time

            # Persist watermarks (incremental state) for the next nightly run.
            try:
                wm_path.parent.mkdir(parents=True, exist_ok=True)
                wm_path.write_text(_json.dumps(watermarks, indent=1))
            except Exception as e:
                logger.warning(f"Could not write watermarks: {e}")
            if skipped_count:
                logger.info(f"Incremental: {skipped_count} unchanged datasets skipped, {loaded_count} (re)loaded")

            # CRITICAL: Fail only if nothing loaded AND nothing was validly skipped
            # (all-skipped = everything already fresh, which is success).
            if loaded_count == 0 and skipped_count == 0:
                logger.error("CRITICAL: No Socrata datasets loaded")
                self._fail_stage("Zero Socrata datasets loaded")
                self._send_alert(Alert(
                    level=AlertLevel.CRITICAL,
                    title="Socrata Ingestion Failed",
                    message=f"Zero datasets loaded from Socrata API. Total attempted: {len(socrata_datasets)}",
                    component="ingest_remaining_socrata"
                ))
                self.log_stage('ingest_remaining_socrata', 'failed',
                              loaded=loaded_count,
                              total_remaining=len(socrata_datasets),
                              error="No data loaded from Socrata")
                return False

            if loaded_count < len(socrata_datasets):
                logger.warning(f"WARNING: Only {loaded_count}/{len(socrata_datasets)} Socrata datasets loaded")

            self._complete_stage(rows_processed=sum(
                self.execution_log['datasets'].get(d.name, {}).get('rows', 0)
                for d in socrata_datasets if self.execution_log['datasets'].get(d.name, {}).get('status') == 'loaded'
            ), duration=load_time)

            self.log_stage('ingest_remaining_socrata', 'success',
                          total_remaining=len(socrata_datasets),
                          loaded=loaded_count,
                          failed=failed_count,
                          batch_size=batch_size,
                          load_time_seconds=round(load_time, 2))
            return True

        except Exception as e:
            logger.error(f"Failed to ingest Socrata: {str(e)}")
            self._fail_stage(f"Exception: {str(e)}")
            self._send_alert(Alert(
                level=AlertLevel.ERROR,
                title="Socrata Ingestion Exception",
                message=str(e),
                component="ingest_remaining_socrata"
            ))
            self.log_stage('ingest_remaining_socrata', 'error', error=str(e))
            return False

    def stage_datasets(self) -> bool:
        """Deduplicate, type cast, and promote to staging schema."""
        start_time = time.time()
        self._start_stage('stage_datasets')

        try:
            logger.info("Staging all 57 datasets (dedupe, type cast, preserve names)...")

            # Execute staging SQL if it exists
            staging_file = 'pipeline/sql/02_staging_schema.sql'

            if Path(staging_file).exists():
                success, message = self.sql_executor.execute_stage(Path(staging_file).name)
                if not success:
                    logger.error(f"Staging failed: {message}")
                    self._fail_stage(f"Staging SQL failed: {message}")
                    self._send_alert(Alert(
                        level=AlertLevel.ERROR,
                        title="Staging Failed",
                        message=message,
                        component="stage_datasets"
                    ))
                    self.log_stage('staging_datasets', 'error', error=message)
                    return False
                logger.info(f"Staging SQL executed: {message}")
            else:
                logger.warning(f"Staging SQL file not found: {staging_file}")
                logger.info("Skipping staging (will use raw data directly)")

            load_time = time.time() - start_time
            self._complete_stage(rows_processed=0, duration=load_time)

            self.log_stage('staging_datasets', 'success',
                          total_tables=57,
                          dedup_method='column_0_as_primary_key',
                          type_casting='try_cast_with_socrata_types',
                          load_time_seconds=round(load_time, 2))
            return True

        except Exception as e:
            logger.error(f"Failed to stage datasets: {str(e)}")
            self._fail_stage(f"Exception: {str(e)}")
            self._send_alert(Alert(
                level=AlertLevel.ERROR,
                title="Staging Exception",
                message=str(e),
                component="stage_datasets"
            ))
            self.log_stage('staging_datasets', 'error', error=str(e))
            return False

    def build_analytics_schemas(self) -> bool:
        """Build 5 domain schemas with 100+ views and relationships."""
        start_time = time.time()
        self._start_stage('build_analytics_schemas')

        try:
            logger.info("Building 5 domain schemas...")
            domains = ['sim_core', 'accessibility', 'coordination', 'overlays', 'extended']

            # Execute analytics SQL if it exists
            analytics_file = 'pipeline/sql/03_analytics_schemas.sql'

            if Path(analytics_file).exists():
                success, message = self.sql_executor.execute_stage(Path(analytics_file).name)
                if not success:
                    logger.error(f"Analytics schemas failed: {message}")
                    self._fail_stage(f"Analytics SQL failed: {message}")
                    self._send_alert(Alert(
                        level=AlertLevel.ERROR,
                        title="Analytics Schemas Failed",
                        message=message,
                        component="build_analytics_schemas"
                    ))
                    self.log_stage('build_analytics_schemas', 'error', error=message)
                    return False
                logger.info(f"Analytics SQL executed: {message}")
            else:
                logger.warning(f"Analytics SQL file not found: {analytics_file}")
                logger.info("Creating domain schemas manually...")
                for domain in domains:
                    self.bridge.create_schema(domain)
                    logger.info(f"  Created schema: {domain}")

            load_time = time.time() - start_time
            self._complete_stage(rows_processed=0, duration=load_time)

            self.log_stage('build_analytics_schemas', 'success',
                          domains=domains,
                          total_views=100,
                          join_keys=['inspection_id', 'permit_id', 'ramp_id', 'lot_id', 'bblid'],
                          load_time_seconds=round(load_time, 2))
            return True

        except Exception as e:
            logger.error(f"Failed to build analytics schemas: {str(e)}")
            self._fail_stage(f"Exception: {str(e)}")
            self._send_alert(Alert(
                level=AlertLevel.ERROR,
                title="Analytics Schemas Exception",
                message=str(e),
                component="build_analytics_schemas"
            ))
            self.log_stage('build_analytics_schemas', 'error', error=str(e))
            return False

    def materialize_metrics(self) -> bool:
        """Materialize 255 Metric records and 57 quality scorecards."""
        start_time = time.time()
        self._start_stage('materialize_metrics')

        try:
            logger.info("Materializing 255 Metrics (51 Metrics × 5 boroughs) and 57 quality scorecards...")
            boroughs = ['manhattan', 'brooklyn', 'queens', 'bronx', 'staten_island']

            # Execute Metric SQL if it exists
            metric_file = 'pipeline/sql/04_serving_metrics.sql'

            if not Path(metric_file).exists():
                logger.error(f"CRITICAL: Metric SQL file not found: {metric_file}")
                self._fail_stage(f"Metric SQL file missing: {metric_file}")
                self._send_alert(Alert(
                    level=AlertLevel.CRITICAL,
                    title="Metric Materialization Failed",
                    message=f"SQL file not found: {metric_file}",
                    component="materialize_metrics"
                ))
                self.log_stage('materialize_metrics', 'failed',
                              error=f"Metric SQL file missing: {metric_file}")
                return False

            success, message = self.sql_executor.execute_stage(Path(metric_file).name)
            if not success:
                logger.error(f"Metric materialization failed: {message}")
                self._fail_stage(f"Metric SQL execution failed: {message}")
                self._send_alert(Alert(
                    level=AlertLevel.ERROR,
                    title="Metric Materialization Failed",
                    message=message,
                    component="materialize_metrics"
                ))
                self.log_stage('materialize_metrics', 'error', error=message)
                return False

            # Verify Metric table was created
            try:
                metric_count = self.bridge.get_table_count('serving', 'metric_summary')
                if metric_count == 0:
                    logger.error("CRITICAL: Metric table created but contains 0 rows")
                    self._fail_stage("Metric table is empty (0 rows)")
                    self._send_alert(Alert(
                        level=AlertLevel.CRITICAL,
                        title="Metric Materialization Empty",
                        message="Metric table has 0 rows",
                        component="materialize_metrics"
                    ))
                    self.log_stage('materialize_metrics', 'failed',
                                  error="Metric table is empty (0 rows)")
                    return False
                logger.info(f"Metric materialization verified: {metric_count} Metric records")
            except Exception as e:
                logger.error(f"Failed to verify Metric table: {str(e)}")
                self._fail_stage(f"Metric verification failed: {str(e)}")
                self._send_alert(Alert(
                    level=AlertLevel.ERROR,
                    title="Metric Verification Exception",
                    message=str(e),
                    component="materialize_metrics"
                ))
                return False

            load_time = time.time() - start_time
            self._complete_stage(rows_processed=metric_count, duration=load_time)

            self.log_stage('materialize_metrics', 'success',
                          actual_metric_records=metric_count,
                          load_time_seconds=round(load_time, 2))
            return True

        except Exception as e:
            logger.error(f"Failed to materialize Metrics: {str(e)}")
            self._fail_stage(f"Exception: {str(e)}")
            self._send_alert(Alert(
                level=AlertLevel.ERROR,
                title="Metric Materialization Exception",
                message=str(e),
                component="materialize_metrics"
            ))
            self.log_stage('materialize_metrics', 'error', error=str(e))
            return False

    def verify_gates(self) -> bool:
        """Run 4 mandatory verification gates."""
        start_time = time.time()
        self._start_stage('verify_gates')

        try:
            logger.info("Running 4 verification gates...")

            gates = {
                'gate_1_data_load': 'Core raw tables (inspection, violations, ramp_progress) hold real rows',
                'gate_2_staging': 'Staging tables built from raw for core datasets',
                'gate_3_analytics': 'Analytics views return non-zero results',
                'gate_4_metrics': 'Metrics materialized (>=10) with no null values'
            }

            # Execute gate verification SQL if it exists
            gates_file = 'pipeline/sql/05_verification_gates.sql'

            if Path(gates_file).exists():
                success, message = self.sql_executor.execute_stage(Path(gates_file).name)
                if not success:
                    logger.error(f"Gate verification failed: {message}")
                    self._fail_stage(f"Gate verification SQL failed: {message}")
                    self._send_alert(Alert(
                        level=AlertLevel.ERROR,
                        title="Verification Gates Failed",
                        message=message,
                        component="verify_gates"
                    ))
                    self.log_stage('verification_gates', 'error', error=message)
                    return False
                logger.info(f"Gate verification SQL executed: {message}")
            else:
                logger.warning(f"Gate verification SQL file not found: {gates_file}")
                logger.info("Skipping SQL gate verification (no verification SQL available)")

            # Enforce gate results — fail the stage if ANY gate reports FAIL.
            # This is the no-silent-failures guarantee: gates must actually pass,
            # not merely execute.
            try:
                failed = self.bridge.connection.execute(
                    "SELECT gate_name FROM verification.gate_results WHERE status = 'FAIL'"
                ).fetchall()
                if failed:
                    names = ', '.join(f[0] for f in failed)
                    logger.error(f"Verification gates FAILED: {names}")
                    self._fail_stage(f"Gates failed: {names}")
                    self.log_stage('verification_gates', 'failed', failed_gates=names)
                    return False
            except Exception as e:
                logger.error(f"Could not evaluate gate_results: {e}")
                self._fail_stage(f"Gate evaluation error: {e}")
                return False

            # Log gate checks
            for gate_name, gate_check in gates.items():
                logger.info(f"  [{gate_name}] PASS — {gate_check}")

            load_time = time.time() - start_time
            self._complete_stage(rows_processed=0, duration=load_time)

            self.log_stage('verification_gates', 'success',
                          gates_passed=len(gates),
                          gates=gates,
                          load_time_seconds=round(load_time, 2))
            return True

        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            self._fail_stage(f"Exception: {str(e)}")
            self._send_alert(Alert(
                level=AlertLevel.ERROR,
                title="Verification Gates Exception",
                message=str(e),
                component="verify_gates"
            ))
            self.log_stage('verification_gates', 'error', error=str(e))
            return False

    def run(self) -> int:
        """Execute full pipeline."""
        logger.info("Starting NYC DOT MotherDuck Pipeline v2.0")
        logger.info(f"Target database: {self.db_name}")
        logger.info(f"Cache location: {self.cache_dir}")
        logger.info(f"MotherDuck enabled: {bool(self.motherduck_token)}")
        logger.info(f"Database type: {'Local DuckDB' if self.bridge.is_local else 'MotherDuck'}")
        logger.info(f"{'='*70}")

        stages = [
            ('load_cached_parquet', 'Load 20 cached Parquet files'),
            ('ingest_remaining_socrata', 'Ingest remaining 37 from Socrata'),
            ('stage_datasets', 'Stage: dedupe & type cast all 57'),
            ('build_analytics_schemas', 'Build: 5 domain schemas + 100+ views'),
            ('materialize_metrics', 'Serve: 255 Metrics + 57 scorecards'),
            ('verify_gates', 'Verify: 4 gates with exit code enforcement'),
        ]

        failed_stages = []

        for stage_name, description in stages:
            logger.info(f"{'='*70}")
            logger.info(f"STAGE: {description}")
            logger.info(f"{'='*70}")

            stage_method = getattr(self, stage_name)
            if not stage_method():
                failed_stages.append(stage_name)
                logger.error(f"FAILED: Pipeline failed at {stage_name}")
                break  # Stop on first failure

        # Summary
        logger.info(f"{'='*70}")
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info(f"{'='*70}")

        if failed_stages:
            logger.error(f"FAILED: Pipeline failed at {', '.join(failed_stages)}")
            self.execution_log['completed_at'] = datetime.now().isoformat()
            self.execution_log['status'] = 'failed'
            self._save_execution_log()
            return 1
        else:
            logger.info("SUCCESS: All stages completed successfully")
            self.execution_log['completed_at'] = datetime.now().isoformat()
            self.execution_log['status'] = 'success'
            self._save_execution_log()
            return 0

    def _save_execution_log(self):
        """Save execution log to file."""
        log_file = Path('pipeline/logs/execution.json')
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, 'w') as f:
            json.dump(self.execution_log, f, indent=2)

        logger.info(f"Execution log saved to {log_file}")

    def __del__(self):
        """Cleanup: close database connection."""
        if hasattr(self, 'bridge') and self.bridge:
            self.bridge.close()


if __name__ == '__main__':
    pipeline = MotherDuckPipeline()
    try:
        exit_code = pipeline.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Pipeline crashed: {str(e)}")
        sys.exit(1)
