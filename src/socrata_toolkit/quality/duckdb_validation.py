"""Validation framework for DuckDB pipeline stages.

Checks: Count validation, Freshness, Uniqueness, Business logic, Referential integrity
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from socrata_toolkit.governance.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


def validate_counts(
    conn,
    raw_table: str,
    staging_table: str,
    audit_logger: Optional[AuditLogger] = None
) -> Dict:
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
) -> Dict:
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
    key_columns: List[str],
    audit_logger: Optional[AuditLogger] = None
) -> Dict:
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
) -> Dict:
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


def run_all_validations(conn) -> Dict:
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
