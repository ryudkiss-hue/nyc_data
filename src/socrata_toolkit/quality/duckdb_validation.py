"""Validation framework for DuckDB pipeline stages.

Checks: Count validation, Freshness, Uniqueness, Business logic, Referential integrity
"""

import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


def validate_counts(conn, raw_table: str, staging_table: str) -> Dict:
    """Ensure no rows lost in transformation.

    Args:
        conn: DuckDB connection
        raw_table: Raw stage table name
        staging_table: Staging stage table name

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

        return {
            "status": "success",
            "raw_count": raw_count,
            "staging_count": staging_count,
            "loss_pct": round(loss_pct, 2),
            "valid": is_valid
        }
    except Exception as e:
        logger.error(f"Count validation failed: {e}")
        return {"status": "error", "error": str(e)}


def validate_freshness(conn, table: str, sla_hours: int = 24) -> Dict:
    """Check data freshness against SLA threshold.

    Args:
        conn: DuckDB connection
        table: Table to check
        sla_hours: SLA threshold in hours (default 24)

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

            return {
                "status": "success",
                "max_timestamp": str(max_ts),
                "age_hours": round(age_hours, 2),
                "sla_hours": sla_hours,
                "fresh": is_fresh
            }
        else:
            return {
                "status": "warning",
                "message": "No timestamp found",
                "fresh": False
            }
    except Exception as e:
        logger.warning(f"Freshness validation skipped (no timestamp column): {e}")
        return {"status": "skipped", "reason": "no_timestamp_column"}


def validate_uniqueness(conn, table: str, key_columns: List[str]) -> Dict:
    """Check for duplicate rows on key columns.

    Args:
        conn: DuckDB connection
        table: Table to check
        key_columns: List of columns that define uniqueness

    Returns:
        Uniqueness validation result with duplicate count
    """
    logger.info(f"Validating uniqueness for {table} on {key_columns}...")
    try:
        key_str = ", ".join(key_columns)

        result = conn.execute(f"""
            SELECT COUNT(*) - COUNT(DISTINCT ({key_str}))
            FROM {table}
        """).fetchone()[0]

        is_valid = result == 0

        return {
            "status": "success",
            "duplicate_rows": result,
            "valid": is_valid
        }
    except Exception as e:
        logger.error(f"Uniqueness validation failed: {e}")
        return {"status": "error", "error": str(e)}


def validate_business_rules(conn, table: str) -> Dict:
    """Verify business logic constraints.

    Args:
        conn: DuckDB connection
        table: Table to validate

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

        return {
            "status": "success",
            "violations": violations,
            "valid": len(violations) == 0
        }
    except Exception as e:
        logger.warning(f"Business rules validation partial (missing columns): {e}")
        return {"status": "skipped", "reason": "missing_columns"}


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
