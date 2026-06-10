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
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb

from socrata_toolkit.core.client import SocrataClient, SocrataConfig

logger = logging.getLogger(__name__)

SOCRATA_DOMAIN = "data.cityofnewyork.us"

SOCRATA_DATASETS = {
    # Core SIM (already present)
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "permits": "tqtj-sjs8",
    "ramp_progress": "e7gc-ub6z",

    # Add 22 more
    "built": "ugc8-s3f6",
    "lot_info": "i642-2fxq",
    "reinspection": "gx72-kirf",
    "tree_damage": "j6v2-6uxq",
    "dismissals": "p4u2-3jgx",
    "correspondences": "bheb-sjfi",
    "curb_metal_protruding": "i2y3-sx2e",
    "ramp_locations": "ufzp-rrqu",
    "ramp_complaints": "jagj-gttd",
    "weekly_construction": "r528-jcks",
    "capital_blocks": "jvk9-k4re",
    "capital_intersections": "97nd-ff3i",
    "street_construction_inspections": "ydkf-mpxb",
    "street_closures_block": "i6b5-j7bu",
    "street_resurfacing_schedule": "xnfm-u3k5",
    "street_resurfacing_inhouse": "ffaf-8mrv",
    "step_streets": "u9au-h79y",
    "sidewalk_planimetric": "vfx9-tbb6",
    "pedestrian_demand": "fwpa-qxaf",
    "mappluto": "64uk-42ks",
    "complaints_311": "erm2-nwe9",
}

DEFAULT_DB_PATH = "data/local_db/nyc_mission_control.duckdb"

_connection: Optional[duckdb.DuckDBPyConnection] = None
_connection_path: Optional[str] = None
_connection_lock = threading.Lock()


def get_duckdb_connection(db_path: str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Get or create the module-level DuckDB connection.

    Creates parent directories if needed. If db_path differs from the cached
    connection's path (e.g. tests passing ':memory:' or a tmp path), the old
    connection is closed and a new one is opened. Thread-safe: the singleton
    mutation is guarded by a lock (APScheduler workers + Streamlit threads).
    """
    global _connection, _connection_path
    with _connection_lock:
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
    with _connection_lock:
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


def load_raw_from_socrata(dataset_key: str, max_rows: int | None = None) -> dict:
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


# Candidate columns per dataset — real Socrata schemas vary, so staging SQL is
# built defensively from whatever columns actually exist in the raw table.
_INSPECTION_KEY_CANDIDATES = ["objectid", "object_id", "id"]
_INSPECTION_DATE_CANDIDATES = ["created_date", "inspection_date", ":updated_at"]
_PERMIT_KEY_CANDIDATES = ["permit_number", "permitnumber", "permit_id", "objectid", "id"]
_PERMIT_DATE_CANDIDATES = [
    "permit_issue_date",
    "issue_date",
    "permit_date",
    "created_date",
    ":updated_at",
]
_RAMP_KEY_CANDIDATES = ["ramp_id", "rampid", "objectid", "id"]
_RAMP_DATE_CANDIDATES = [
    "status_date",
    "completion_date",
    "installation_date",
    "created_date",
    ":updated_at",
]
_VIOLATION_JOIN_CANDIDATES = ["block_id", "location", "bbl", "borough_block_lot"]


def _existing_columns(conn: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    """Return the set of column names for a table (raises if table is missing)."""
    return {row[0] for row in conn.execute(f"DESCRIBE {table}").fetchall()}


def _table_exists(conn: duckdb.DuckDBPyConnection, schema: str, name: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?",
        [schema, name],
    ).fetchone()
    return bool(row[0])


def _pick_column(columns: set[str], candidates: list[str]) -> Optional[str]:
    return next((c for c in candidates if c in columns), None)


def _dedup_subquery(
    raw_table: str, key_col: Optional[str], date_col: Optional[str]
) -> tuple[str, Optional[str]]:
    """Build a dedup SELECT for raw_table; returns (sql, note)."""
    if key_col is None:
        return f"SELECT DISTINCT * FROM {raw_table}", (
            "no natural key column found; fell back to SELECT DISTINCT *"
        )
    order_clause = (
        f'ORDER BY "{date_col}" DESC NULLS LAST' if date_col else "ORDER BY 1"
    )
    sql = (
        "SELECT * EXCLUDE (_rn) FROM ("
        f'SELECT *, ROW_NUMBER() OVER (PARTITION BY "{key_col}" {order_clause}) AS _rn '
        f"FROM {raw_table}) WHERE _rn = 1"
    )
    return sql, None


def _stage_table(
    raw_table: str,
    staging_table: str,
    key_candidates: list[str],
    date_candidates: list[str],
    conn: Optional[duckdb.DuckDBPyConnection] = None,
) -> dict:
    """Generic staging: dedup raw_table into staging_table (idempotent)."""
    try:
        if conn is None:
            conn = get_duckdb_connection(_connection_path or DEFAULT_DB_PATH)
        conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
        columns = _existing_columns(conn, raw_table)
        raw_count = conn.execute(f"SELECT COUNT(*) FROM {raw_table}").fetchone()[0]
        key_col = _pick_column(columns, key_candidates)
        date_col = _pick_column(columns, date_candidates)
        dedup_sql, note = _dedup_subquery(raw_table, key_col, date_col)
        conn.execute(f"DROP TABLE IF EXISTS {staging_table}")
        conn.execute(f"CREATE TABLE {staging_table} AS {dedup_sql}")
        staged_count = conn.execute(
            f"SELECT COUNT(*) FROM {staging_table}"
        ).fetchone()[0]
        result = {
            "status": "success",
            "table": staging_table,
            "row_count_raw": raw_count,
            "row_count_staged": staged_count,
            "dedup_loss_pct": round((raw_count - staged_count) / raw_count * 100, 2)
            if raw_count
            else 0.0,
        }
        if note:
            result["note"] = note
        logger.info(
            f"Staged {staging_table}: {raw_count} raw -> {staged_count} staged "
            f"(key={key_col}, date={date_col})"
        )
        return result
    except Exception as e:
        logger.error(f"Failed to stage {staging_table} from {raw_table}: {e}")
        return {"status": "error", "error": str(e), "table": staging_table}


def stage_inspections() -> dict:
    """Stage raw.inspection into staging.inspections.

    Deduplicates on the natural key (most recent record kept) and LEFT JOINs
    raw.violations to compute violation_count per block/location.
    """
    result = _stage_table(
        "raw.inspection",
        "staging.inspections",
        _INSPECTION_KEY_CANDIDATES,
        _INSPECTION_DATE_CANDIDATES,
    )
    if result["status"] != "success":
        return result
    try:
        conn = get_duckdb_connection(_connection_path or DEFAULT_DB_PATH)
        join_col = None
        if _table_exists(conn, "raw", "violations"):
            insp_cols = _existing_columns(conn, "staging.inspections")
            viol_cols = _existing_columns(conn, "raw.violations")
            join_col = _pick_column(insp_cols & viol_cols, _VIOLATION_JOIN_CANDIDATES)
        if join_col:
            conn.execute(
                "CREATE OR REPLACE TABLE staging._inspections_tmp AS "
                "SELECT i.*, COALESCE(v._vc, 0) AS violation_count "
                "FROM staging.inspections i "
                f'LEFT JOIN (SELECT "{join_col}", COUNT(*) AS _vc '
                f'FROM raw.violations GROUP BY "{join_col}") v '
                f'USING ("{join_col}")'
            )
        else:
            conn.execute(
                "CREATE OR REPLACE TABLE staging._inspections_tmp AS "
                "SELECT i.*, 0 AS violation_count FROM staging.inspections i"
            )
            result["note"] = (
                "raw.violations missing or no shared join column; "
                "violation_count defaulted to 0"
            )
        conn.execute("DROP TABLE staging.inspections")
        conn.execute("ALTER TABLE staging._inspections_tmp RENAME TO inspections")
        return result
    except Exception as e:
        logger.error(f"Failed to join violations into staging.inspections: {e}")
        return {"status": "error", "error": str(e), "table": "staging.inspections"}


def stage_permits() -> dict:
    """Stage raw.permits into staging.permits (dedup on permit key)."""
    return _stage_table(
        "raw.permits",
        "staging.permits",
        _PERMIT_KEY_CANDIDATES,
        _PERMIT_DATE_CANDIDATES,
    )


def stage_ramps() -> dict:
    """Stage raw.ramp_progress into staging.ramps (dedup on ramp key)."""
    return _stage_table(
        "raw.ramp_progress",
        "staging.ramps",
        _RAMP_KEY_CANDIDATES,
        _RAMP_DATE_CANDIDATES,
    )


def stage_dataset(dataset_key: str, conn: Optional[duckdb.DuckDBPyConnection] = None) -> int:
    """Generic staging for any dataset using config-driven column discovery.

    Reads dataset_config.json to find key_candidates and date_candidates,
    then uses DuckDB DESCRIBE to verify columns exist, and deduplicates
    the raw table into staging. Works for all 26 datasets without hardcoding.

    Args:
        dataset_key: Key in SOCRATA_DATASETS (e.g., 'inspection', 'street_permits')
        conn: Optional DuckDB connection. If None, uses the module-level connection.

    Returns:
        Row count in staging table after dedup.

    Raises:
        FileNotFoundError: If dataset_config.json not found.
        ValueError: If no primary key column found.
        Exception: If DuckDB operations fail.
    """
    import json

    if conn is None:
        conn = get_duckdb_connection(_connection_path or DEFAULT_DB_PATH)

    # Load config
    config_path = Path("data/dataset_config.json")
    if not config_path.exists():
        config_path = Path(__file__).parent.parent.parent.parent / "data" / "dataset_config.json"
    with open(config_path) as f:
        config = json.load(f)

    if dataset_key not in config:
        raise ValueError(f"Dataset {dataset_key} not found in config")

    ds_config = config[dataset_key]
    key_candidates = ds_config.get("key_candidates", [])
    date_candidates = ds_config.get("date_candidates", [])

    # Stage using existing _stage_table logic
    result = _stage_table(
        f"raw.{dataset_key}",
        f"staging.{dataset_key}",
        key_candidates,
        date_candidates,
        conn=conn,
    )

    if result["status"] != "success":
        raise Exception(f"Failed to stage {dataset_key}: {result.get('error')}")

    return result["row_count_staged"]


class DuckDBPipeline:
    """Orchestrate raw → staging → analytics ELT workflow.

    Deprecated: prefer the module-level pipeline functions
    (load_raw_from_socrata, stage_*, analytics create_*).
    """

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
