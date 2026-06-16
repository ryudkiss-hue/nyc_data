"""Pre-flight QA checklist — blocks reports if data quality gates fail."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd


@dataclass
class QACheckResult:
    check_name: str
    passed: bool
    message: str
    severity: str = "error"  # "error" | "warning" | "info"


@dataclass
class QAReport:
    dataset_key: str
    run_id: str
    checks: list[QACheckResult] = field(default_factory=list)
    blocked: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add(self, check: QACheckResult) -> None:
        self.checks.append(check)
        if not check.passed and check.severity == "error":
            self.blocked = True

    def summary(self) -> str:
        passed = sum(1 for c in self.checks if c.passed)
        return f"{passed}/{len(self.checks)} checks passed" + (
            " — BLOCKED" if self.blocked else " — OK"
        )


def run_preflight(
    df: pd.DataFrame,
    dataset_key: str,
    *,
    run_id: str = "",
    min_rows: int = 10,
    freshness_hours: float | None = None,
    fetch_timestamp: datetime | None = None,
    required_columns: list[str] | None = None,
    min_completeness: float = 0.5,
) -> QAReport:
    """
    Run all pre-flight checks before generating a report or export.

    Returns a QAReport. Check report.blocked before proceeding.
    """
    report = QAReport(dataset_key=dataset_key, run_id=run_id or str(uuid.uuid4()))

    report.add(
        QACheckResult(
            "min_rows",
            len(df) >= min_rows,
            f"n={len(df)} (minimum: {min_rows})",
            "error" if len(df) < min_rows else "info",
        )
    )

    if freshness_hours is not None and fetch_timestamp is not None:
        age = (datetime.now(timezone.utc) - fetch_timestamp).total_seconds() / 3600
        ok = age <= freshness_hours
        report.add(
            QACheckResult(
                "data_freshness",
                ok,
                f"Data age {age:.1f}h (limit: {freshness_hours}h)",
                "error" if not ok else "info",
            )
        )

    if required_columns:
        missing = [c for c in required_columns if c not in df.columns]
        report.add(
            QACheckResult(
                "required_columns",
                len(missing) == 0,
                f"Missing columns: {missing}" if missing else "All required columns present",
                "error" if missing else "info",
            )
        )

    if not df.empty:
        completeness = 1.0 - df.isnull().mean().mean()
        ok = completeness >= min_completeness
        report.add(
            QACheckResult(
                "completeness",
                ok,
                f"Completeness {completeness:.1%} (minimum: {min_completeness:.1%})",
                "warning" if not ok else "info",
            )
        )

    if not df.empty:
        all_null = [c for c in df.columns if df[c].isnull().all()]
        report.add(
            QACheckResult(
                "no_all_null_columns",
                len(all_null) == 0,
                f"All-null columns: {all_null}" if all_null else "No all-null columns",
                "warning" if all_null else "info",
            )
        )

    return report
