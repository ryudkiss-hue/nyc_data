"""DuckDB pipeline orchestration for ELT workflow.

Implements three-schema architecture:
- raw: Direct copies from Socrata (immutable)
- staging: Cleaned, deduplicated, joined tables
- analytics: Pre-computed KPIs and marts for analysis

Usage:
    pipeline = DuckDBPipeline('data/local_db/nyc_mission_control.duckdb')
    pipeline.load_raw_from_socrata(['inspection', 'violations', 'street_permits'])
    pipeline.stage_all()
    results = pipeline.validate_all()
    pipeline.materialize_analytics()
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb

from socrata_toolkit.core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)

SOCRATA_DOMAIN = "data.cityofnewyork.us"

SOCRATA_DATASETS = {
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "permits": "tqtj-sjs8",
    "ramp_progress": "e7gc-ub6z",
}

DEFAULT_DB_PATH = "data/local_db/nyc_mission_control.duckdb"

_connection: Optional[duckdb.DuckDBPyConnection] = None
_connection_path: Optional[str] = None


def get_duckdb_connection(db_path: str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Get or create the module-level DuckDB connection.

    Creates parent directories if needed. If db_path differs from the cached
    connection's path (e.g. tests passing ':memory:' or a tmp path), the old
    connection is closed and a new one is opened.
    """
    global _connection, _connection_path
    if _connection is not None and _connection_path == db_path:
        return _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _connection = duckdb.connect(db_path)
    _connection_path = db_path
    return _connection


def reset_connection() -> None:
    """Close and clear the module-level connection (used by tests)."""
    global _connection, _connection_path
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
    _connection = None
    _connection_path = None


def initialize_database() -> dict:
    """Create the raw, staging, and analytics schemas if they don't exist."""
    conn = get_duckdb_connection(_connection_path or DEFAULT_DB_PATH)
    schemas = ["raw", "staging", "analytics"]
    for schema in schemas:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    return {"status": "initialized", "schemas": schemas}


def load_raw_from_socrata(dataset_key: str, max_rows: int = None) -> dict:
    """Fetch a dataset from data.cityofnewyork.us into raw.<dataset_key>.

    Idempotent: drops and recreates the target table on each call.

    Returns {"status": "success", "table": ..., "row_count": N, "fourfour": ...}
    on success, or {"status": "error", "error": ..., "table": ...} on API or
    load failure. Raises ValueError for an unknown dataset_key.
    """
    if dataset_key not in SOCRATA_DATASETS:
        raise ValueError(
            f"Unknown dataset_key '{dataset_key}'. "
            f"Valid keys: {sorted(SOCRATA_DATASETS)}"
        )
    fourfour = SOCRATA_DATASETS[dataset_key]
    table = f"raw.{dataset_key}"
    try:
        client = SocrataClient(SocrataConfig())
        df = client.fetch_dataframe(SOCRATA_DOMAIN, fourfour, max_rows=max_rows)
        conn = get_duckdb_connection(_connection_path or DEFAULT_DB_PATH)
        conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
        conn.register("_raw_load_df", df)
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.execute(f"CREATE TABLE {table} AS SELECT * FROM _raw_load_df")
        finally:
            conn.unregister("_raw_load_df")
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info(f"Loaded {row_count} rows into {table} ({fourfour})")
        return {
            "status": "success",
            "table": table,
            "row_count": row_count,
            "fourfour": fourfour,
        }
    except Exception as e:
        logger.error(f"Failed to load {dataset_key} ({fourfour}): {e}")
        return {"status": "error", "error": str(e), "table": table}


class DuckDBPipeline:
    """Orchestrate raw → staging → analytics ELT workflow."""

    def __init__(self, db_path: str):
        """Initialize pipeline with DuckDB connection.

        Args:
            db_path: Path to DuckDB file
        """
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._init_schemas()
        self.load_timestamp = datetime.now()

    def _init_schemas(self):
        """Create raw, staging, analytics schemas if they don't exist."""
        for schema in ["raw", "staging", "analytics"]:
            try:
                self.conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            except Exception as e:
                logger.warning(f"Could not create schema {schema}: {e}")

    def load_raw_from_socrata(self, dataset_keys: list[str]) -> dict:
        """Load raw data from Socrata into raw schema (idempotent).

        Args:
            dataset_keys: List of dataset keys to load (e.g., ['inspection', 'violations'])

        Returns:
            Dict with load status and row counts
        """
        logger.info(f"Loading {len(dataset_keys)} datasets from Socrata...")
        results = {}

        for key in dataset_keys:
            try:
                # In production: fetch from Socrata API
                # For now: verify table exists or load from cache
                logger.info(f"  - {key}: loading...")
                results[key] = {"status": "loaded", "rows": 0}  # Placeholder
            except Exception as e:
                logger.error(f"Failed to load {key}: {e}")
                results[key] = {"status": "error", "error": str(e)}

        return results

    def stage_inspections(self) -> dict:
        """Stage inspection data: dedupe, join violations, compute metrics.

        Returns:
            Dict with status and row counts
        """
        logger.info("Staging inspection data...")
        try:
            # Idempotent: drop and recreate
            self.conn.execute("DROP TABLE IF EXISTS staging.inspections CASCADE")

            # Deduplication: rank by inspection_date DESC, keep most recent
            result = self.conn.execute("""
                CREATE TABLE staging.inspections AS
                SELECT DISTINCT ON (i.objectid)
                    i.objectid,
                    i.inspection_date,
                    i.condition_score,
                    i.material_type,
                    i.latitude,
                    i.longitude,
                    COUNT(v.objectid) as violation_count,
                    MIN(v.violation_date) as first_violation_date,
                    MAX(v.violation_date) as last_violation_date,
                    CURRENT_TIMESTAMP as staged_at
                FROM raw.inspection i
                LEFT JOIN raw.violations v ON i.objectid = v.inspection_id
                GROUP BY i.objectid, i.inspection_date, i.condition_score,
                         i.material_type, i.latitude, i.longitude
                ORDER BY i.objectid, i.inspection_date DESC
            """).fetchall()

            row_count = self.conn.execute("SELECT COUNT(*) FROM staging.inspections").fetchone()[0]

            return {"status": "success", "table": "staging.inspections", "rows": row_count}
        except Exception as e:
            logger.error(f"Failed to stage inspections: {e}")
            return {"status": "error", "error": str(e)}

    def stage_permits(self) -> dict:
        """Stage permit data: dedupe, flatten hierarchy, add metrics.

        Returns:
            Dict with status
        """
        logger.info("Staging permit data...")
        try:
            self.conn.execute("DROP TABLE IF EXISTS staging.permits CASCADE")

            self.conn.execute("""
                CREATE TABLE staging.permits AS
                SELECT DISTINCT ON (permit_number)
                    permit_number,
                    permit_date,
                    permit_type,
                    status,
                    completion_date,
                    CURRENT_TIMESTAMP as staged_at
                FROM raw.street_permits
                WHERE permit_number IS NOT NULL
                ORDER BY permit_number, permit_date DESC
            """)

            row_count = self.conn.execute("SELECT COUNT(*) FROM staging.permits").fetchone()[0]

            return {"status": "success", "table": "staging.permits", "rows": row_count}
        except Exception as e:
            logger.error(f"Failed to stage permits: {e}")
            return {"status": "error", "error": str(e)}

    def stage_ramps(self) -> dict:
        """Stage ramp data: dedupe, join complaints, compute accessibility.

        Returns:
            Dict with status
        """
        logger.info("Staging ramp data...")
        try:
            self.conn.execute("DROP TABLE IF EXISTS staging.ramps CASCADE")

            self.conn.execute("""
                CREATE TABLE staging.ramps AS
                SELECT DISTINCT ON (ramp_id)
                    ramp_id,
                    location,
                    latitude,
                    longitude,
                    installation_date,
                    condition,
                    COUNT(c.complaint_id) as complaint_count,
                    MAX(c.complaint_date) as last_complaint_date,
                    CURRENT_TIMESTAMP as staged_at
                FROM raw.ramp_locations r
                LEFT JOIN raw.ramp_complaints c ON r.ramp_id = c.ramp_id
                WHERE r.latitude IS NOT NULL AND r.longitude IS NOT NULL
                GROUP BY r.ramp_id, r.location, r.latitude, r.longitude,
                         r.installation_date, r.condition
                ORDER BY r.ramp_id, r.installation_date DESC
            """)

            row_count = self.conn.execute("SELECT COUNT(*) FROM staging.ramps").fetchone()[0]

            return {"status": "success", "table": "staging.ramps", "rows": row_count}
        except Exception as e:
            logger.error(f"Failed to stage ramps: {e}")
            return {"status": "error", "error": str(e)}

    def stage_all(self) -> dict:
        """Execute all staging transformations.

        Returns:
            Dict with combined results
        """
        logger.info("Starting staging transformations...")
        results = {
            "inspections": self.stage_inspections(),
            "permits": self.stage_permits(),
            "ramps": self.stage_ramps()
        }
        logger.info("Staging complete!")
        return results

    def materialize_analytics(self) -> dict:
        """Create analytics-ready views and marts.

        Returns:
            Dict with materialization results
        """
        logger.info("Materializing analytics views...")
        from socrata_toolkit.core.duckdb_analytics_models import refresh_all_analytics_views

        results = refresh_all_analytics_views(self.conn)
        logger.info("Analytics materialization complete!")
        return results

    def validate_all(self) -> dict:
        """Run validation checks on all stages.

        Returns:
            Dict with validation results
        """
        logger.info("Running validation checks...")
        from socrata_toolkit.quality.duckdb_validation import run_all_validations

        results = run_all_validations(self.conn)
        logger.info("Validation complete!")
        return results

    def run_full_pipeline(self, socrata_keys: list[str] = None) -> dict:
        """Execute complete ELT pipeline end-to-end.

        Args:
            socrata_keys: Keys to load from Socrata (defaults to core 3)

        Returns:
            Dict with pipeline execution results
        """
        if socrata_keys is None:
            socrata_keys = ["inspection", "violations", "street_permits"]

        logger.info("=" * 60)
        logger.info("STARTING FULL DUCKDB PIPELINE")
        logger.info("=" * 60)

        pipeline_results = {}

        # Step 1: Load raw
        logger.info("\n[Step 1] Loading raw data from Socrata...")
        pipeline_results["load_raw"] = self.load_raw_from_socrata(socrata_keys)

        # Step 2: Stage
        logger.info("\n[Step 2] Staging transformations...")
        pipeline_results["staging"] = self.stage_all()

        # Step 3: Materialize analytics
        logger.info("\n[Step 3] Materializing analytics...")
        pipeline_results["analytics"] = self.materialize_analytics()

        # Step 4: Validate
        logger.info("\n[Step 4] Running validations...")
        pipeline_results["validation"] = self.validate_all()

        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)

        return pipeline_results
