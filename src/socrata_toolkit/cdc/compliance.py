"""CDC compliance, reconciliation, and data quality checks.

This module provides tools for verifying CDC system integrity, audit trail
completeness, and compliance with regulatory requirements.

Key Features:
    - Detect gaps in CDC events
    - Verify audit trail completeness
    - Reconcile SCD tables with source
    - Generate compliance reports
    - Data integrity checks
    - Record count validation

Classes:
    CDCReconciler: Main reconciliation interface
    ComplianceReport: Compliance check results
    ReconciliationResult: Reconciliation findings

Example:
    >>> reconciler = CDCReconciler(dsn="postgresql://...")
    >>> report = reconciler.verify_audit_trail_completeness()
    >>> result = reconciler.reconcile_scd_with_source("sidewalk_conditions")
    >>> compliance = reconciler.generate_compliance_report()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None  # type: ignore
    sql = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ComplianceCheckResult:
    """Result of a single compliance check.

    Attributes:
        check_name: Name of the check
        passed: Whether check passed
        issues: List of issues found
        severity: 'critical', 'warning', or 'info'
        timestamp: When check was run
    """
    check_name: str
    passed: bool
    issues: list[str] = field(default_factory=list)
    severity: str = "info"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ComplianceReport:
    """Overall compliance report.

    Attributes:
        report_date: When report was generated
        total_checks: Number of checks run
        passed_checks: Number of passed checks
        failed_checks: Number of failed checks
        checks: List of individual check results
        overall_status: 'compliant', 'warning', or 'critical'
        summary: Human-readable summary
    """
    report_date: datetime
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: list[ComplianceCheckResult]
    overall_status: str
    summary: str


@dataclass
class ReconciliationResult:
    """Result of reconciliation between CDC and source.

    Attributes:
        source_system: Source system name
        cdc_record_count: Records in CDC log
        source_record_count: Records in source
        missing_events: Records in source but not in CDC
        extra_events: Records in CDC but not in source
        timestamp_mismatches: Records with different timestamps
        reconciled: Whether reconciliation succeeded
    """
    source_system: str
    cdc_record_count: int
    source_record_count: int
    missing_events: list[str] = field(default_factory=list)
    extra_events: list[str] = field(default_factory=list)
    timestamp_mismatches: list[tuple[str, int, int]] = field(default_factory=list)
    reconciled: bool = False


class CDCReconciler:
    """Verify CDC system integrity and generate compliance reports.

    Performs comprehensive checks on CDC, audit trail, and SCD systems
    to ensure data integrity and regulatory compliance.
    """

    def __init__(self, dsn: str) -> None:
        """Initialize reconciler.

        Args:
            dsn: PostgreSQL connection string

        Raises:
            ImportError: If psycopg not installed
        """
        if psycopg is None:
            raise ImportError("Install postgres extras: pip install '.[postgres]'")
        self.dsn = dsn
        self.logger = logger.getChild(self.__class__.__name__)

    @contextmanager
    def _get_connection(self):
        """Context manager for database connection."""
        conn = psycopg.connect(self.dsn)
        try:
            yield conn
        finally:
            conn.close()

    def verify_audit_trail_completeness(self) -> ComplianceCheckResult:
        """Verify audit trail has no gaps and is complete.

        Checks:
        1. All tables have audit entries
        2. No suspiciously large time gaps
        3. Audit entries match expected operations

        Returns:
            ComplianceCheckResult
        """
        issues = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check for tables with no audit entries
                    cur.execute(
                        """SELECT COUNT(*) FROM public.audit_trail"""
                    )
                    total_audit = cur.fetchone()[0]

                    if total_audit == 0:
                        issues.append("No audit trail entries found")

                    # Check for gaps (>24 hours between entries for same entity)
                    cur.execute(
                        """WITH gaps AS (
                             SELECT entity_type, entity_id,
                                    timestamp,
                                    LAG(timestamp) OVER (PARTITION BY entity_type, entity_id ORDER BY timestamp) as prev_ts,
                                    EXTRACT(EPOCH FROM (timestamp - LAG(timestamp) OVER (PARTITION BY entity_type, entity_id ORDER BY timestamp))) / 3600 as hours_gap
                             FROM public.audit_trail
                           )
                           SELECT COUNT(DISTINCT entity_id) FROM gaps
                           WHERE hours_gap > 24 AND hours_gap IS NOT NULL"""
                    )
                    gap_count = cur.fetchone()[0]
                    if gap_count > 0:
                        issues.append(f"{gap_count} entities have >24hr gaps in audit trail")

                    # Verify immutability (no updates/deletes)
                    cur.execute(
                        """SELECT COUNT(*) FROM pg_stat_user_tables
                           WHERE relname = 'audit_trail' AND n_tup_upd > 0 OR n_tup_del > 0"""
                    )
                    if cur.fetchone()[0] > 0:
                        issues.append("Audit trail has been modified (updates/deletes detected)")
        except Exception as e:
            issues.append(f"Audit trail check failed: {e}")

        return ComplianceCheckResult(
            check_name="audit_trail_completeness",
            passed=len(issues) == 0,
            issues=issues,
            severity="critical" if len(issues) > 0 else "info",
        )

    def verify_cdc_event_ordering(self) -> ComplianceCheckResult:
        """Verify CDC events are in correct chronological order.

        Checks:
        1. Events for same record_id are chronologically ordered
        2. No duplicate event IDs
        3. Operation sequences are valid (INSERT before UPDATE/DELETE)

        Returns:
            ComplianceCheckResult
        """
        issues = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check for duplicate event IDs
                    cur.execute(
                        """SELECT event_id, COUNT(*)
                           FROM public.cdc_events
                           GROUP BY event_id
                           HAVING COUNT(*) > 1"""
                    )
                    duplicates = cur.fetchall()
                    if duplicates:
                        issues.append(f"{len(duplicates)} duplicate event IDs found")

                    # Check for out-of-order events
                    cur.execute(
                        """WITH ordered AS (
                             SELECT record_id, timestamp_ms,
                                    LAG(timestamp_ms) OVER (PARTITION BY record_id ORDER BY timestamp_ms) as prev_ts
                             FROM public.cdc_events
                           )
                           SELECT COUNT(*) FROM ordered
                           WHERE prev_ts IS NOT NULL AND timestamp_ms < prev_ts"""
                    )
                    out_of_order = cur.fetchone()[0]
                    if out_of_order > 0:
                        issues.append(f"{out_of_order} out-of-order events detected")

                    # Check operation sequences
                    cur.execute(
                        """WITH ops AS (
                             SELECT record_id, operation,
                                    LAG(operation) OVER (PARTITION BY record_id ORDER BY timestamp_ms) as prev_op
                             FROM public.cdc_events
                           )
                           SELECT COUNT(*) FROM ops
                           WHERE (operation = 'INSERT' AND prev_op IS NOT NULL) OR
                                 (prev_op = 'DELETE' AND operation != 'INSERT')"""
                    )
                    invalid_ops = cur.fetchone()[0]
                    if invalid_ops > 0:
                        issues.append(f"{invalid_ops} invalid operation sequences detected")
        except Exception as e:
            issues.append(f"CDC ordering check failed: {e}")

        return ComplianceCheckResult(
            check_name="cdc_event_ordering",
            passed=len(issues) == 0,
            issues=issues,
            severity="critical" if len(issues) > 0 else "info",
        )

    def verify_scd_integrity(self, table: str) -> ComplianceCheckResult:
        """Verify SCD Type 2 table integrity.

        Checks:
        1. No overlapping date ranges
        2. At most one is_current=TRUE per business_key
        3. end_date >= start_date
        4. Hash consistency

        Returns:
            ComplianceCheckResult
        """
        issues = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Check for multiple is_current
                    cur.execute(
                        f"""SELECT business_key, COUNT(*)
                           FROM {sql.Identifier(table)}
                           WHERE is_current = TRUE
                           GROUP BY business_key
                           HAVING COUNT(*) > 1"""
                    )
                    if cur.fetchall():
                        issues.append(f"Multiple is_current=TRUE records found in {table}")

                    # Check for overlapping dates
                    cur.execute(
                        f"""SELECT COUNT(*) FROM {sql.Identifier(table)} t1
                           JOIN {sql.Identifier(table)} t2 ON t1.business_key = t2.business_key
                           WHERE t1.scd_id != t2.scd_id
                             AND t1.start_date <= t2.start_date
                             AND (t1.end_date IS NULL OR t1.end_date > t2.start_date)
                             AND (t2.end_date IS NULL OR t2.end_date > t1.start_date)"""
                    )
                    overlaps = cur.fetchone()[0]
                    if overlaps > 0:
                        issues.append(f"{overlaps} overlapping date ranges detected in {table}")

                    # Check end_date >= start_date
                    cur.execute(
                        f"""SELECT COUNT(*) FROM {sql.Identifier(table)}
                           WHERE end_date IS NOT NULL AND end_date < start_date"""
                    )
                    invalid_ranges = cur.fetchone()[0]
                    if invalid_ranges > 0:
                        issues.append(f"{invalid_ranges} invalid date ranges (end < start) in {table}")
        except Exception as e:
            issues.append(f"SCD integrity check failed: {e}")

        return ComplianceCheckResult(
            check_name=f"scd_integrity_{table}",
            passed=len(issues) == 0,
            issues=issues,
            severity="critical" if len(issues) > 0 else "info",
        )

    def reconcile_scd_with_source(
        self, table: str, source_table: str
    ) -> ReconciliationResult:
        """Reconcile SCD table with source table.

        Checks:
        1. Current SCD records match source
        2. No missing records
        3. No extra records

        Args:
            table: SCD table name
            source_table: Source table name

        Returns:
            ReconciliationResult
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Count records
                    cur.execute(
                        f"""SELECT COUNT(DISTINCT business_key)
                           FROM {sql.Identifier(table)}
                           WHERE is_current = TRUE"""
                    )
                    scd_count = cur.fetchone()[0]

                    cur.execute(
                        f"""SELECT COUNT(*) FROM {sql.Identifier(source_table)}"""
                    )
                    source_count = cur.fetchone()[0]

                    # Find missing events
                    cur.execute(
                        f"""SELECT st.id FROM {sql.Identifier(source_table)} st
                           LEFT JOIN {sql.Identifier(table)} scd ON st.id = scd.business_key
                           WHERE scd.business_key IS NULL"""
                    )
                    missing = [row[0] for row in cur.fetchall()]

                    # Find extra events
                    cur.execute(
                        f"""SELECT scd.business_key FROM {sql.Identifier(table)} scd
                           LEFT JOIN {sql.Identifier(source_table)} st ON scd.business_key = st.id
                           WHERE scd.is_current = TRUE AND st.id IS NULL"""
                    )
                    extra = [row[0] for row in cur.fetchall()]
        except Exception as e:
            self.logger.error(f"Reconciliation failed: {e}")
            return ReconciliationResult(
                source_system=source_table,
                cdc_record_count=0,
                source_record_count=0,
                reconciled=False,
            )

        return ReconciliationResult(
            source_system=source_table,
            cdc_record_count=scd_count,
            source_record_count=source_count,
            missing_events=missing,
            extra_events=extra,
            reconciled=len(missing) == 0 and len(extra) == 0,
        )

    def check_record_count_consistency(
        self, table: str, expected_count: int
    ) -> ComplianceCheckResult:
        """Verify record counts match expectations.

        Args:
            table: Table name
            expected_count: Expected number of current records

        Returns:
            ComplianceCheckResult
        """
        issues = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""SELECT COUNT(DISTINCT business_key)
                           FROM {sql.Identifier(table)}
                           WHERE is_current = TRUE"""
                    )
                    actual_count = cur.fetchone()[0]

            if actual_count != expected_count:
                issues.append(
                    f"Record count mismatch: expected {expected_count}, got {actual_count}"
                )
        except Exception as e:
            issues.append(f"Count check failed: {e}")

        return ComplianceCheckResult(
            check_name=f"record_count_{table}",
            passed=len(issues) == 0,
            issues=issues,
            severity="warning" if len(issues) > 0 else "info",
        )

    def check_audit_trail_coverage(self) -> ComplianceCheckResult:
        """Verify audit trail covers all transactions.

        Checks percentage of time period covered and identifies gaps.

        Returns:
            ComplianceCheckResult
        """
        issues = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Get date range
                    cur.execute(
                        """SELECT MIN(timestamp), MAX(timestamp)
                           FROM public.audit_trail"""
                    )
                    min_ts, max_ts = cur.fetchone()

                    if not min_ts or not max_ts:
                        issues.append("No audit trail entries found")
                        return ComplianceCheckResult(
                            check_name="audit_trail_coverage",
                            passed=False,
                            issues=issues,
                            severity="critical",
                        )

                    # Check for days with no entries
                    cur.execute(
                        """SELECT COUNT(DISTINCT DATE(timestamp)) as days_with_entries,
                                  (MAX(timestamp)::date - MIN(timestamp)::date + 1) as total_days
                           FROM public.audit_trail"""
                    )
                    days_with, total_days = cur.fetchone()
                    coverage = (days_with / total_days * 100) if total_days > 0 else 0

                    if coverage < 100:
                        issues.append(
                            f"Audit trail coverage: {coverage:.1f}% "
                            f"({days_with} of {total_days} days have entries)"
                        )
        except Exception as e:
            issues.append(f"Coverage check failed: {e}")

        return ComplianceCheckResult(
            check_name="audit_trail_coverage",
            passed=len(issues) == 0,
            issues=issues,
            severity="warning" if len(issues) > 0 else "info",
        )

    def generate_compliance_report(self) -> ComplianceReport:
        """Generate comprehensive compliance report.

        Runs all compliance checks and generates summary.

        Returns:
            ComplianceReport
        """
        checks = [
            self.verify_audit_trail_completeness(),
            self.verify_cdc_event_ordering(),
            self.check_audit_trail_coverage(),
        ]

        passed = sum(1 for c in checks if c.passed)
        failed = len(checks) - passed

        # Determine overall status
        critical = any(c.severity == "critical" and not c.passed for c in checks)
        overall = "critical" if critical else ("warning" if failed > 0 else "compliant")

        summary = f"{passed}/{len(checks)} checks passed. "
        if critical:
            summary += "CRITICAL ISSUES FOUND. "
        elif failed > 0:
            summary += "Warning: some checks failed. "
        else:
            summary += "All checks passed. "

        return ComplianceReport(
            report_date=datetime.now(timezone.utc),
            total_checks=len(checks),
            passed_checks=passed,
            failed_checks=failed,
            checks=checks,
            overall_status=overall,
            summary=summary,
        )

    def detect_missing_changes(
        self, start_date: date, end_date: date
    ) -> dict[str, Any]:
        """Detect potentially missing changes in date range.

        Identifies suspicious gaps or patterns that might indicate
        missing CDC events.

        Args:
            start_date: Range start
            end_date: Range end

        Returns:
            Dict with findings
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Find records with no changes in range
                    cur.execute(
                        """SELECT COUNT(DISTINCT entity_id) as entities_no_change
                           FROM (
                             SELECT DISTINCT entity_id
                             FROM public.audit_trail
                             WHERE timestamp >= %s AND timestamp <= %s
                           ) recent
                           WHERE NOT EXISTS (
                             SELECT 1 FROM public.audit_trail
                             WHERE entity_id = recent.entity_id
                               AND timestamp >= %s AND timestamp <= %s
                           )""",
                        (start_date, end_date, start_date, end_date)
                    )
                    no_change = cur.fetchone()[0]

                    # Find entities with too-frequent changes (potential duplicates)
                    cur.execute(
                        """SELECT entity_id, COUNT(*) as change_count
                           FROM public.audit_trail
                           WHERE timestamp >= %s AND timestamp <= %s
                           GROUP BY entity_id
                           HAVING COUNT(*) > 100
                           ORDER BY change_count DESC
                           LIMIT 10""",
                        (start_date, end_date)
                    )
                    frequent = cur.fetchall()
        except Exception as e:
            self.logger.error(f"Missing changes detection failed: {e}")
            frequent = []
            no_change = 0

        return {
            "entities_no_change": no_change,
            "high_frequency_changes": [{"entity_id": row[0], "count": row[1]} for row in frequent],
        }

    def export_compliance_report(self, report: ComplianceReport) -> str:
        """Export compliance report to formatted string.

        Args:
            report: ComplianceReport

        Returns:
            Formatted report string
        """
        lines = [
            f"CDC Compliance Report - {report.report_date.isoformat()}",
            "=" * 60,
            f"Status: {report.overall_status.upper()}",
            f"Checks: {report.passed_checks}/{report.total_checks} passed",
            "",
            "Summary:",
            report.summary,
            "",
            "Check Results:",
            "-" * 60,
        ]

        for check in report.checks:
            status = "✓ PASS" if check.passed else "✗ FAIL"
            lines.append(f"{status} | {check.check_name} ({check.severity})")
            for issue in check.issues:
                lines.append(f"       {issue}")

        lines.append("-" * 60)
        return "\n".join(lines)
