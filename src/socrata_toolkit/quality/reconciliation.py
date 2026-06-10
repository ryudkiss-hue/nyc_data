"""Data Reconciliation Module - Compare expected vs actual row counts.

Provides tools for reconciliation checks across datasets, detecting anomalies
and surfacing data quality issues to analysts.

Standards: Python 3.9+, type hints, comprehensive docstrings, operational logging
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """Result of a single reconciliation check.

    Attributes:
        table: Dataset or table name
        expected: Expected row count
        actual: Actual row count
        variance: Absolute difference (actual - expected)
        variance_pct: Percentage variance ((actual - expected) / expected * 100)
        status: "OK" if within tolerance, "WARNING" if within 2x tolerance, else "FAIL"
        timestamp: When the reconciliation was performed
    """

    table: str
    expected: int
    actual: int
    variance: int
    variance_pct: float
    status: str  # "OK", "WARNING", "FAIL"
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "table": self.table,
            "expected": self.expected,
            "actual": self.actual,
            "variance": self.variance,
            "variance_pct": self.variance_pct,
            "status": self.status,
            "timestamp": self.timestamp,
        }


class DataReconciliation:
    """Reconciliation system comparing expected vs actual row counts.

    Detects anomalies and surfaces data quality issues by comparing
    expected counts (baseline or SLA targets) against actual counts
    from live datasets.
    """

    def __init__(
        self,
        dataset_name: str,
        expected_counts: dict[str, int],
        actual_counts: dict[str, int],
    ):
        """Initialize reconciliation checker.

        Args:
            dataset_name: Name or identifier for this dataset group
            expected_counts: Dict of table -> expected row count
            actual_counts: Dict of table -> actual row count
        """
        self.dataset_name = dataset_name
        self.expected_counts = expected_counts
        self.actual_counts = actual_counts
        self.results: list[ReconciliationResult] = []

    def check_counts(self, tolerance_pct: float = 0.05) -> list[ReconciliationResult]:
        """Check row counts and detect discrepancies.

        Args:
            tolerance_pct: Tolerance as decimal (0.05 = 5% variance)

        Returns:
            List of ReconciliationResult objects, one per table
        """
        self.results = []
        timestamp = datetime.now(timezone.utc).isoformat()

        # Process all tables (both expected and actual)
        all_tables = set(self.expected_counts.keys()) | set(self.actual_counts.keys())

        for table in sorted(all_tables):
            expected = self.expected_counts.get(table, 0)
            actual = self.actual_counts.get(table, 0)

            # Calculate variance
            variance = actual - expected
            if expected != 0:
                variance_pct = (variance / expected) * 100
            else:
                # If expected is 0, any actual count is a significant variance
                variance_pct = 100.0 if actual != 0 else 0.0

            # Determine status based on tolerance
            abs_variance_pct = abs(variance_pct)
            tolerance_threshold = tolerance_pct * 100

            if abs_variance_pct <= tolerance_threshold:
                status = "OK"
            elif abs_variance_pct <= tolerance_threshold * 2:
                status = "WARNING"
            else:
                status = "FAIL"

            result = ReconciliationResult(
                table=table,
                expected=expected,
                actual=actual,
                variance=variance,
                variance_pct=variance_pct,
                status=status,
                timestamp=timestamp,
            )
            self.results.append(result)
            logger.debug(
                f"Reconciliation: {table} | expected={expected} actual={actual} "
                f"variance={variance_pct:.2f}% | status={status}"
            )

        return self.results

    def generate_reconciliation_report(self) -> str:
        """Generate a text report of reconciliation results.

        Returns:
            Formatted text report with summary and detailed table
        """
        if not self.results:
            self.check_counts()

        # Summary statistics
        total_checks = len(self.results)
        ok_count = sum(1 for r in self.results if r.status == "OK")
        warning_count = sum(1 for r in self.results if r.status == "WARNING")
        fail_count = sum(1 for r in self.results if r.status == "FAIL")

        timestamp = datetime.now(timezone.utc).isoformat()

        lines = []
        lines.append("=" * 80)
        lines.append("DATA RECONCILIATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Dataset: {self.dataset_name}")
        lines.append(f"Generated: {timestamp}")
        lines.append("")

        # Summary section
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total Tables Checked: {total_checks}")
        lines.append(f"OK:      {ok_count} ({ok_count/max(total_checks, 1)*100:.1f}%)")
        lines.append(f"WARNING: {warning_count} ({warning_count/max(total_checks, 1)*100:.1f}%)")
        lines.append(f"FAIL:    {fail_count} ({fail_count/max(total_checks, 1)*100:.1f}%)")
        lines.append("")

        # Detailed results
        lines.append("DETAILED RESULTS")
        lines.append("-" * 80)
        lines.append(
            f"{'Table':<30} {'Expected':>12} {'Actual':>12} {'Variance':>12} {'Status':<10}"
        )
        lines.append("-" * 80)

        for result in sorted(self.results, key=lambda r: r.status, reverse=True):
            status_display = f"[{result.status}]"
            variance_str = f"{result.variance_pct:+.2f}%"
            lines.append(
                f"{result.table:<30} {result.expected:>12,} "
                f"{result.actual:>12,} {variance_str:>12} {status_display:<10}"
            )

        lines.append("")

        # Discrepancies section (only include non-OK items)
        discrepancies = [r for r in self.results if r.status != "OK"]
        if discrepancies:
            lines.append("DISCREPANCIES REQUIRING ATTENTION")
            lines.append("-" * 80)
            for result in sorted(discrepancies, key=lambda r: abs(r.variance_pct), reverse=True):
                lines.append(
                    f"\n{result.table}")
                lines.append(f"  Status:    {result.status}")
                lines.append(f"  Expected:  {result.expected:,} rows")
                lines.append(f"  Actual:    {result.actual:,} rows")
                lines.append(f"  Variance:  {result.variance:+,} rows ({result.variance_pct:+.2f}%)")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def get_failed_tables(self) -> list[str]:
        """Get list of tables with FAIL status.

        Returns:
            List of table names with failed reconciliation
        """
        if not self.results:
            self.check_counts()
        return [r.table for r in self.results if r.status == "FAIL"]

    def get_warning_tables(self) -> list[str]:
        """Get list of tables with WARNING status.

        Returns:
            List of table names with warning status
        """
        if not self.results:
            self.check_counts()
        return [r.table for r in self.results if r.status == "WARNING"]

    def summary_stats(self) -> dict[str, Any]:
        """Get summary statistics of reconciliation.

        Returns:
            Dict with counts and percentages
        """
        if not self.results:
            self.check_counts()

        total = len(self.results)
        return {
            "total_checks": total,
            "ok_count": sum(1 for r in self.results if r.status == "OK"),
            "warning_count": sum(1 for r in self.results if r.status == "WARNING"),
            "fail_count": sum(1 for r in self.results if r.status == "FAIL"),
            "ok_pct": round(sum(1 for r in self.results if r.status == "OK") / max(total, 1) * 100, 1),
            "warning_pct": round(
                sum(1 for r in self.results if r.status == "WARNING") / max(total, 1) * 100, 1
            ),
            "fail_pct": round(sum(1 for r in self.results if r.status == "FAIL") / max(total, 1) * 100, 1),
            "max_variance_pct": max((abs(r.variance_pct) for r in self.results), default=0.0),
        }
