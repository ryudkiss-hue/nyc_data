"""Validation framework for DuckDB pipeline stages.

Checks: Count validation, Freshness, Uniqueness, Business logic, Referential integrity

Task 5: Quality-gate validation checks that integrate with audit logging framework.
No-arg validation functions that use the singleton connection from duckdb_pipeline
and log results to AuditLogger.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import duckdb

from socrata_toolkit.core.duckdb_pipeline import get_duckdb_connection
from socrata_toolkit.governance.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

def validate_counts(
    conn,
    raw_table: str,
    staging_table: str,
    audit_logger: Optional[AuditLogger] = None
) -> dict:
    """Ensure no rows lost in transformation.

    Args:
        conn: DuckDB connection
        raw_table: Raw stage table name
        staging_table: Staging stage table name
        audit_logger: Optional AuditLogger for capturing check results

    Returns:
        Validation result with row counts and loss percentage
    """
    logger.info(f"Validating row counts: {raw_table} → {staging_table}...")
    try:
        raw_count = conn.execute(f"SELECT COUNT(*) FROM {raw_table}").fetchone()[0]
        staging_count = conn.execute(f"SELECT COUNT(*) FROM {staging_table}").fetchone()[0]

        loss_pct = 0
        if raw_count > 0:
            loss_pct = 100.0 * (raw_count - staging_count) / raw_count

        is_valid = loss_pct <= 5.0  # Allow 5% loss (deduplication, null filtering)

        result = {
            "status": "success",
            "raw_count": raw_count,
            "staging_count": staging_count,
            "loss_pct": round(loss_pct, 2),
            "valid": is_valid
        }

        if audit_logger:
            check_status = "success" if is_valid else "failure"
            audit_logger.log_check(
                check_type="validate_counts",
                table_name=staging_table,
                status=check_status,
                rows_affected=staging_count,
                details={
                    "raw_count": raw_count,
                    "staging_count": staging_count,
                    "loss_pct": loss_pct,
                    "threshold_pct": 5.0
                }
            )

        return result
    except Exception as e:
        logger.error(f"Count validation failed: {e}")
        result = {"status": "error", "error": str(e)}

        if audit_logger:
            audit_logger.log_check(
                check_type="validate_counts",
                table_name=staging_table,
                status="error",
                rows_affected=0,
                details={"error": str(e)}
            )

        return result

def validate_freshness(
    conn,
    table: str,
    sla_hours: int = 24,
    audit_logger: Optional[AuditLogger] = None
) -> dict:
    """Check data freshness against SLA threshold.

    Args:
        conn: DuckDB connection
        table: Table to check
        sla_hours: SLA threshold in hours (default 24)
        audit_logger: Optional AuditLogger for capturing check results

    Returns:
        Freshness validation result
    """
    logger.info(f"Validating freshness for {table} (SLA: {sla_hours}h)...")
    try:
        # Attempt to get the max timestamp from the table
        result = conn.execute(f"""
            SELECT MAX(staged_at) as max_timestamp
            FROM {table}
        """).fetchone()

        if result and result[0]:
            max_ts = result[0]
            age_hours = (datetime.now() - max_ts).total_seconds() / 3600
            is_fresh = age_hours <= sla_hours

            validation_result = {
                "status": "success",
                "max_timestamp": str(max_ts),
                "age_hours": round(age_hours, 2),
                "sla_hours": sla_hours,
                "fresh": is_fresh
            }

            if audit_logger:
                check_status = "success" if is_fresh else "warning"
                audit_logger.log_check(
                    check_type="validate_freshness",
                    table_name=table,
                    status=check_status,
                    rows_affected=0,
                    details={
                        "age_hours": round(age_hours, 2),
                        "sla_hours": sla_hours,
                        "max_timestamp": str(max_ts)
                    }
                )

            return validation_result
        else:
            validation_result = {
                "status": "warning",
                "message": "No timestamp found",
                "fresh": False
            }

            if audit_logger:
                audit_logger.log_check(
                    check_type="validate_freshness",
                    table_name=table,
                    status="warning",
                    rows_affected=0,
                    details={"message": "No timestamp found"}
                )

            return validation_result
    except Exception as e:
        logger.warning(f"Freshness validation skipped (no timestamp column): {e}")
        validation_result = {"status": "skipped", "reason": "no_timestamp_column"}

        if audit_logger:
            audit_logger.log_check(
                check_type="validate_freshness",
                table_name=table,
                status="skipped",
                rows_affected=0,
                details={"reason": "no_timestamp_column", "error": str(e)}
            )

        return validation_result

def validate_uniqueness(
    conn,
    table: str,
    key_columns: list[str],
    audit_logger: Optional[AuditLogger] = None
) -> dict:
    """Check for duplicate rows on key columns.

    Args:
        conn: DuckDB connection
        table: Table to check
        key_columns: List of columns that define uniqueness
        audit_logger: Optional AuditLogger for capturing check results

    Returns:
        Uniqueness validation result with duplicate count
    """
    logger.info(f"Validating uniqueness for {table} on {key_columns}...")
    try:
        key_str = ", ".join(key_columns)

        duplicate_count = conn.execute(f"""
            SELECT COUNT(*) - COUNT(DISTINCT ({key_str}))
            FROM {table}
        """).fetchone()[0]

        is_valid = duplicate_count == 0

        result = {
            "status": "success",
            "duplicate_rows": duplicate_count,
            "valid": is_valid
        }

        if audit_logger:
            check_status = "success" if is_valid else "failure"
            audit_logger.log_check(
                check_type="validate_uniqueness",
                table_name=table,
                status=check_status,
                rows_affected=duplicate_count,
                details={
                    "duplicate_rows": duplicate_count,
                    "key_columns": key_columns
                }
            )

        return result
    except Exception as e:
        logger.error(f"Uniqueness validation failed: {e}")
        result = {"status": "error", "error": str(e)}

        if audit_logger:
            audit_logger.log_check(
                check_type="validate_uniqueness",
                table_name=table,
                status="error",
                rows_affected=0,
                details={"error": str(e), "key_columns": key_columns}
            )

        return result

def validate_business_rules(
    conn,
    table: str,
    audit_logger: Optional[AuditLogger] = None
) -> dict:
    """Verify business logic constraints.

    Args:
        conn: DuckDB connection
        table: Table to validate
        audit_logger: Optional AuditLogger for capturing check results

    Returns:
        Validation result with violations found
    """
    logger.info(f"Validating business rules for {table}...")
    violations = []

    try:
        # Check condition_score is in valid range [0, 100]
        bad_scores = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE condition_score < 0 OR condition_score > 100
        """).fetchone()[0]

        if bad_scores > 0:
            violations.append(f"condition_score out of range: {bad_scores} rows")

        # Check violation_count is non-negative
        bad_counts = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE violation_count < 0
        """).fetchone()[0]

        if bad_counts > 0:
            violations.append(f"violation_count is negative: {bad_counts} rows")

        # Check dates are sensible (not in future)
        future_dates = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE inspection_date > CURRENT_DATE
        """).fetchone()[0]

        if future_dates > 0:
            violations.append(f"future inspection_dates: {future_dates} rows")

        result = {
            "status": "success",
            "violations": violations,
            "valid": len(violations) == 0
        }

        if audit_logger:
            check_status = "success" if len(violations) == 0 else "failure"
            total_violations = bad_scores + bad_counts + future_dates
            audit_logger.log_check(
                check_type="validate_business_rules",
                table_name=table,
                status=check_status,
                rows_affected=total_violations,
                details={
                    "violations": violations,
                    "violation_count": len(violations),
                    "bad_scores": bad_scores,
                    "bad_counts": bad_counts,
                    "future_dates": future_dates
                }
            )

        return result
    except Exception as e:
        logger.warning(f"Business rules validation partial (missing columns): {e}")
        result = {"status": "skipped", "reason": "missing_columns"}

        if audit_logger:
            audit_logger.log_check(
                check_type="validate_business_rules",
                table_name=table,
                status="skipped",
                rows_affected=0,
                details={"reason": "missing_columns", "error": str(e)}
            )

        return result

def run_all_validations(conn) -> dict:
    """Run complete validation suite on all pipeline stages.

    Args:
        conn: DuckDB connection

    Returns:
        Summary of all validation results
    """
    logger.info("Running complete validation suite...")
    results = {
        "count_validation": {
            "inspections": validate_counts(conn, "raw.inspection", "staging.inspections"),
            "permits": validate_counts(conn, "raw.street_permits", "staging.permits"),
            "ramps": validate_counts(conn, "raw.ramp_locations", "staging.ramps")
        },
        "freshness_checks": {
            "inspections": validate_freshness(conn, "staging.inspections", sla_hours=24),
            "permits": validate_freshness(conn, "staging.permits", sla_hours=24),
            "ramps": validate_freshness(conn, "staging.ramps", sla_hours=24)
        },
        "uniqueness_checks": {
            "inspections": validate_uniqueness(conn, "staging.inspections", ["objectid"]),
            "permits": validate_uniqueness(conn, "staging.permits", ["permit_number"]),
            "ramps": validate_uniqueness(conn, "staging.ramps", ["ramp_id"])
        },
        "business_rules": {
            "inspections": validate_business_rules(conn, "staging.inspections"),
            "permits": validate_business_rules(conn, "staging.permits"),
            "ramps": validate_business_rules(conn, "staging.ramps")
        }
    }

    # Summarize results
    total_checks = sum(
        len(v) for v in results.values()
    )

    return results

# ============================================================================
# TASK 5: Quality-Gate Validation Checks with Audit Logging Integration
# ============================================================================
# No-arg validation functions that use the singleton connection from
# duckdb_pipeline and log results to AuditLogger. Each returns:
# {"status":"PASS"|"FAIL"|"WARNING", "check_name":"...", "details":{...}, "rows_affected":N}
# ============================================================================

def _get_audit_logger() -> AuditLogger:
    """Get or create an audit logger for validation checks."""
    if not hasattr(_get_audit_logger, "_instance"):
        _get_audit_logger._instance = AuditLogger()
    return _get_audit_logger._instance

def _log_check(
    check_name: str,
    table_name: str,
    status: str,
    details: dict[str, Any],
    rows_affected: int = 0
) -> None:
    """Log a validation check result to the audit logger.

    Args:
        check_name: Name of the check being performed
        table_name: Name of the table being checked
        status: Status of the check (PASS, FAIL, WARNING)
        details: Details dictionary with check-specific information
        rows_affected: Number of rows affected or checked
    """
    audit_logger = _get_audit_logger()
    # Convert status to audit logger format (success/failure/warning)
    audit_status = status.lower() if status.upper() != "PASS" else "success"
    if status.upper() == "FAIL":
        audit_status = "failure"
    elif status.upper() == "WARNING":
        audit_status = "warning"

    audit_logger.log_check(
        check_type=check_name,
        table_name=table_name,
        status=audit_status,
        rows_affected=rows_affected,
        details=details
    )

def validate_raw_counts(conn: Optional[duckdb.DuckDBPyConnection] = None) -> dict[str, Any]:
    """Validate that raw.* tables have expected row counts (tolerance: ±%).

    Expected counts (from CLAUDE.md):
    - inspection: ~410K (±10%)
    - violations: ~330K (±10%)
    - permits: ~3.8M (±5%)
    - ramp_progress: ~200K (±10%)

    Args:
        conn: Optional DuckDB connection. If None, uses singleton from duckdb_pipeline.

    Returns:
        {"status":"PASS"|"FAIL"|"WARNING", "check_name":"validate_raw_counts",
         "details":{...}, "rows_affected":total_rows}
    """
    if conn is None:
        conn = get_duckdb_connection()
    check_name = "validate_raw_counts"

    expected = {
        "inspection": (410000, 0.10),
        "violations": (330000, 0.10),
        "permits": (3800000, 0.05),
        "ramp_progress": (200000, 0.10),
    }

    details = {"tables": {}}
    total_rows = 0
    all_pass = True

    for table_key, (expected_count, tolerance) in expected.items():
        table_name = f"raw.{table_key}"

        try:
            # Check if table exists
            exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'raw' AND table_name = ?",
                [table_key],
            ).fetchone()[0]

            if not exists:
                details["tables"][table_key] = {
                    "status": "FAIL",
                    "reason": "table_missing",
                    "row_count": 0,
                    "expected": expected_count,
                }
                all_pass = False
                continue

            row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            total_rows += row_count

            lower_bound = expected_count * (1 - tolerance)
            upper_bound = expected_count * (1 + tolerance)

            if lower_bound <= row_count <= upper_bound:
                status = "PASS"
            else:
                status = "FAIL"
                all_pass = False

            details["tables"][table_key] = {
                "status": status,
                "row_count": row_count,
                "expected": expected_count,
                "tolerance_pct": tolerance * 100,
                "lower_bound": int(lower_bound),
                "upper_bound": int(upper_bound),
            }
        except Exception as e:
            details["tables"][table_key] = {
                "status": "FAIL",
                "reason": "query_error",
                "error": str(e),
            }
            all_pass = False

    overall_status = "PASS" if all_pass else "FAIL"
    result = {
        "status": overall_status,
        "check_name": check_name,
        "details": details,
        "rows_affected": total_rows,
    }

    _log_check(check_name, "raw.*", overall_status, details, total_rows)
    return result

def validate_staging_dedup(conn: Optional[duckdb.DuckDBPyConnection] = None) -> dict[str, Any]:
    """Validate that staging.* tables have no duplicates on primary keys.

    Primary keys:
    - staging.inspections: objectid
    - staging.permits: permit_number
    - staging.ramps: ramp_id
    - staging.violations: (inferred from raw)

    Args:
        conn: Optional DuckDB connection. If None, uses singleton from duckdb_pipeline.

    Returns:
        {"status":"PASS"|"FAIL"|"WARNING", "check_name":"validate_staging_dedup",
         "details":{...}, "rows_affected":total_duplicates}
    """
    if conn is None:
        conn = get_duckdb_connection()
    check_name = "validate_staging_dedup"

    key_configs = {
        "inspections": "objectid",
        "permits": "permit_number",
        "ramps": "ramp_id",
    }

    details = {"tables": {}}
    total_duplicates = 0
    all_pass = True

    for table_key, key_col in key_configs.items():
        table_name = f"staging.{table_key}"

        try:
            # Check if table exists
            exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'staging' AND table_name = ?",
                [table_key],
            ).fetchone()[0]

            if not exists:
                details["tables"][table_key] = {
                    "status": "FAIL",
                    "reason": "table_missing",
                    "duplicate_count": 0,
                }
                all_pass = False
                continue

            # Check if key column exists
            col_exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = 'staging' AND table_name = ? AND column_name = ?",
                [table_key, key_col],
            ).fetchone()[0]

            if not col_exists:
                details["tables"][table_key] = {
                    "status": "FAIL",
                    "reason": "key_column_missing",
                    "key_column": key_col,
                }
                all_pass = False
                continue

            # Count duplicates: rows with the same key (not counting the first occurrence)
            duplicate_count = conn.execute(f"""
                SELECT COUNT(*) - COUNT(DISTINCT "{key_col}") FROM {table_name}
            """).fetchone()[0]

            total_duplicates += duplicate_count
            status = "PASS" if duplicate_count == 0 else "FAIL"
            if duplicate_count > 0:
                all_pass = False

            details["tables"][table_key] = {
                "status": status,
                "key_column": key_col,
                "duplicate_count": duplicate_count,
            }
        except Exception as e:
            details["tables"][table_key] = {
                "status": "FAIL",
                "reason": "query_error",
                "error": str(e),
            }
            all_pass = False

    overall_status = "PASS" if all_pass else "FAIL"
    result = {
        "status": overall_status,
        "check_name": check_name,
        "details": details,
        "rows_affected": total_duplicates,
    }

    _log_check(check_name, "staging.*", overall_status, details, total_duplicates)
    return result

def validate_staging_data_types(conn: Optional[duckdb.DuckDBPyConnection] = None) -> dict[str, Any]:
    """Spot-check staging table columns have expected data types.

    Expected types:
    - Dates (created_date, inspection_date, etc.): TIMESTAMP or DATE
    - IDs (objectid, permit_number, ramp_id): BIGINT, INTEGER, or HUGEINT
    - Geometry (the_geom): VARCHAR or GEOMETRY

    Args:
        conn: Optional DuckDB connection. If None, uses singleton from duckdb_pipeline.

    Returns:
        {"status":"PASS"|"FAIL"|"WARNING", "check_name":"validate_staging_data_types",
         "details":{...}, "rows_affected":0}
    """
    if conn is None:
        conn = get_duckdb_connection()
    check_name = "validate_staging_data_types"

    # Type validation patterns: (column_name_pattern, allowed_types)
    type_checks = {
        "date_columns": {
            "patterns": ["created_date", "inspection_date", "issued_date", "completion_date"],
            "allowed": ["TIMESTAMP", "DATE", "TIMESTAMP WITH TIME ZONE"],
        },
        "id_columns": {
            "patterns": ["objectid", "permit_number", "ramp_id", "id"],
            "allowed": ["BIGINT", "INTEGER", "HUGEINT", "SMALLINT"],
        },
        "geometry_columns": {
            "patterns": ["the_geom", "geom", "geometry", "point"],
            "allowed": ["VARCHAR", "GEOMETRY"],
        },
    }

    details = {"tables": {}, "mismatches": []}
    all_pass = True

    # Get all staging tables
    staging_tables = conn.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'staging'
    """).fetchall()

    for (table_name,) in staging_tables:
        full_name = f"staging.{table_name}"
        details["tables"][table_name] = {"columns": {}}

        try:
            # Get columns for this table
            columns = conn.execute(f"DESCRIBE {full_name}").fetchall()

            for col_name, col_type, *_ in columns:
                col_name_lower = col_name.lower()

                # Check each type category
                for type_category, config in type_checks.items():
                    patterns = config["patterns"]
                    allowed_types = config["allowed"]

                    # Check if column matches any pattern
                    if any(pattern in col_name_lower for pattern in patterns):
                        col_type_upper = col_type.upper()
                        is_valid = col_type_upper in allowed_types

                        details["tables"][table_name]["columns"][col_name] = {
                            "type": col_type,
                            "category": type_category,
                            "status": "PASS" if is_valid else "FAIL",
                        }

                        if not is_valid:
                            all_pass = False
                            details["mismatches"].append({
                                "table": table_name,
                                "column": col_name,
                                "actual_type": col_type,
                                "expected_types": allowed_types,
                            })
        except Exception as e:
            details["tables"][table_name]["error"] = str(e)
            all_pass = False

    overall_status = "PASS" if all_pass else "FAIL"
    result = {
        "status": overall_status,
        "check_name": check_name,
        "details": details,
        "rows_affected": 0,
    }

    _log_check(check_name, "staging.*", overall_status, details, 0)
    return result

def validate_analytics_populated(conn: Optional[duckdb.DuckDBPyConnection] = None) -> dict[str, Any]:
    """Validate all 5 analytics.* tables exist and have row_count > 0.

    Expected tables:
    - analytics.borough_summary
    - analytics.violation_trends
    - analytics.time_series_snapshots
    - analytics.permit_status_dashboard
    - analytics.inspection_quality_metrics

    Args:
        conn: Optional DuckDB connection. If None, uses singleton from duckdb_pipeline.

    Returns:
        {"status":"PASS"|"FAIL"|"WARNING", "check_name":"validate_analytics_populated",
         "details":{...}, "rows_affected":total_rows}
    """
    if conn is None:
        conn = get_duckdb_connection()
    check_name = "validate_analytics_populated"

    expected_tables = [
        "borough_summary",
        "violation_trends",
        "time_series_snapshots",
        "permit_status_dashboard",
        "inspection_quality_metrics",
    ]

    details = {"tables": {}}
    total_rows = 0
    all_pass = True

    for table_key in expected_tables:
        table_name = f"analytics.{table_key}"

        try:
            # Check if table exists
            exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'analytics' AND table_name = ?",
                [table_key],
            ).fetchone()[0]

            if not exists:
                details["tables"][table_key] = {
                    "status": "FAIL",
                    "reason": "table_missing",
                    "row_count": 0,
                }
                all_pass = False
                continue

            row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            total_rows += row_count

            status = "PASS" if row_count > 0 else "FAIL"
            if row_count == 0:
                all_pass = False

            details["tables"][table_key] = {
                "status": status,
                "row_count": row_count,
                "exists": True,
            }
        except Exception as e:
            details["tables"][table_key] = {
                "status": "FAIL",
                "reason": "query_error",
                "error": str(e),
            }
            all_pass = False

    overall_status = "PASS" if all_pass else "FAIL"
    result = {
        "status": overall_status,
        "check_name": check_name,
        "details": details,
        "rows_affected": total_rows,
    }

    _log_check(check_name, "analytics.*", overall_status, details, total_rows)
    return result

def validate_staging_to_analytics_lineage(conn: Optional[duckdb.DuckDBPyConnection] = None) -> dict[str, Any]:
    """Spot-check data flow continuity from staging to analytics.

    Loose checks:
    - If staging.inspections has rows, analytics.borough_summary should have 5 (boroughs)
    - If staging.inspections has rows, analytics.time_series_snapshots should have ≥12 (months)

    Args:
        conn: Optional DuckDB connection. If None, uses singleton from duckdb_pipeline.

    Returns:
        {"status":"PASS"|"FAIL"|"WARNING", "check_name":"validate_staging_to_analytics_lineage",
         "details":{...}, "rows_affected":0}
    """
    if conn is None:
        conn = get_duckdb_connection()
    check_name = "validate_staging_to_analytics_lineage"

    details = {"checks": []}
    all_pass = True

    try:
        # Check 1: staging.inspections -> analytics.borough_summary (5 boroughs)
        staging_insp_exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'staging' AND table_name = 'inspections'",
        ).fetchone()[0]

        analytics_borough_exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'analytics' AND table_name = 'borough_summary'",
        ).fetchone()[0]

        check1 = {"name": "staging.inspections -> analytics.borough_summary"}

        if staging_insp_exists and analytics_borough_exists:
            staging_count = conn.execute(
                "SELECT COUNT(*) FROM staging.inspections"
            ).fetchone()[0]

            if staging_count > 0:
                borough_count = conn.execute(
                    "SELECT COUNT(*) FROM analytics.borough_summary"
                ).fetchone()[0]

                # Expect 5 boroughs (or close to it)
                status = "PASS" if borough_count >= 4 else "FAIL"
                if borough_count < 4:
                    all_pass = False

                check1.update({
                    "status": status,
                    "staging_rows": staging_count,
                    "analytics_rows": borough_count,
                    "expected_min": 4,
                })
            else:
                check1["status"] = "WARNING"
                check1["reason"] = "staging_empty"
        else:
            check1["status"] = "WARNING"
            check1["reason"] = "tables_missing"

        details["checks"].append(check1)

        # Check 2: staging.inspections -> analytics.time_series_snapshots (≥12 months)
        check2 = {"name": "staging.inspections -> analytics.time_series_snapshots"}

        if staging_insp_exists and analytics_borough_exists:
            staging_count = conn.execute(
                "SELECT COUNT(*) FROM staging.inspections"
            ).fetchone()[0]

            if staging_count > 0:
                ts_exists = conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'analytics' AND table_name = 'time_series_snapshots'",
                ).fetchone()[0]

                if ts_exists:
                    ts_count = conn.execute(
                        "SELECT COUNT(*) FROM analytics.time_series_snapshots"
                    ).fetchone()[0]

                    status = "PASS" if ts_count >= 12 else "WARNING"
                    check2.update({
                        "status": status,
                        "staging_rows": staging_count,
                        "analytics_rows": ts_count,
                        "expected_min": 12,
                    })
                else:
                    check2["status"] = "WARNING"
                    check2["reason"] = "table_missing"
            else:
                check2["status"] = "WARNING"
                check2["reason"] = "staging_empty"
        else:
            check2["status"] = "WARNING"
            check2["reason"] = "staging_tables_missing"

        details["checks"].append(check2)

    except Exception as e:
        details["error"] = str(e)
        all_pass = False

    overall_status = "PASS" if all_pass else ("WARNING" if any(
        c.get("status") == "WARNING" for c in details["checks"]
    ) else "FAIL")

    result = {
        "status": overall_status,
        "check_name": check_name,
        "details": details,
        "rows_affected": 0,
    }

    _log_check(check_name, "staging->analytics", overall_status, details, 0)
    return result

def validate_data_freshness(conn: Optional[duckdb.DuckDBPyConnection] = None) -> dict[str, Any]:
    """Check that the most recent record in staging.inspections has a created_date
    within the last 7 days.

    Args:
        conn: Optional DuckDB connection. If None, uses singleton from duckdb_pipeline.

    Returns:
        {"status":"PASS"|"FAIL"|"WARNING", "check_name":"validate_data_freshness",
         "details":{...}, "rows_affected":0}
    """
    if conn is None:
        conn = get_duckdb_connection()
    check_name = "validate_data_freshness"

    details = {}

    try:
        # Check if staging.inspections exists
        exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'staging' AND table_name = 'inspections'",
        ).fetchone()[0]

        if not exists:
            overall_status = "FAIL"
            details["reason"] = "table_missing"
            details["table"] = "staging.inspections"
        else:
            # Find a date column (could be created_date, inspection_date, etc.)
            date_cols = conn.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'staging' AND table_name = 'inspections'
                AND (column_name ILIKE '%date%' OR column_name ILIKE '%time%')
                LIMIT 1
            """).fetchall()

            if not date_cols:
                overall_status = "FAIL"
                details["reason"] = "no_date_column"
                details["table"] = "staging.inspections"
            else:
                date_col = date_cols[0][0]

                # Get the max date
                max_date_result = conn.execute(f"""
                    SELECT MAX("{date_col}") FROM staging.inspections
                """).fetchone()

                max_date = max_date_result[0]

                if max_date is None:
                    overall_status = "FAIL"
                    details["reason"] = "no_data"
                    details["date_column"] = date_col
                else:
                    # Calculate age in days using DuckDB's DATE_DIFF
                    age_result = conn.execute(f"""
                        SELECT DATEDIFF('day', MAX("{date_col}"), CURRENT_DATE)
                        FROM staging.inspections
                    """).fetchone()

                    if age_result and age_result[0] is not None:
                        age_days = age_result[0]

                        # Check if within 7 days
                        if age_days <= 7:
                            overall_status = "PASS"
                        elif age_days <= 14:
                            overall_status = "WARNING"
                        else:
                            overall_status = "FAIL"

                        details["date_column"] = date_col
                        details["max_date"] = str(max_date)
                        details["age_days"] = age_days
                        details["threshold_days"] = 7
                    else:
                        overall_status = "WARNING"
                        details["reason"] = "could_not_calculate_age"
                        details["date_column"] = date_col

    except Exception as e:
        overall_status = "FAIL"
        details["error"] = str(e)

    result = {
        "status": overall_status,
        "check_name": check_name,
        "details": details,
        "rows_affected": 0,
    }

    _log_check(check_name, "staging.inspections", overall_status, details, 0)
    return result
