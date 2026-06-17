"""Dataset Health Classifier — Status detection and severity scoring.

This module provides the DatasetHealthClassifier that evaluates dataset health
across four dimensions:

1. Freshness: How recent is the data relative to SLA thresholds?
2. Completeness: Are row counts healthy (not empty)?
3. Schema Stability: Has the schema changed unexpectedly?
4. Accessibility: Can the dataset be reached via API?

Each dataset is classified into one of four health statuses:
- HEALTHY: Green. All metrics within acceptable thresholds.
- STALE: Yellow. Data is older than SLA threshold.
- SCHEMA_DRIFT: Yellow. Schema has changed unexpectedly.
- EMPTY_OR_ERROR: Red. Dataset is empty or inaccessible.

Severity is a composite score (0-100):
- 0-20: Critical (Red)
- 21-50: High (Orange)
- 51-70: Medium (Yellow)
- 71-100: Low (Green)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status classification."""

    HEALTHY = "healthy"
    STALE = "stale"
    SCHEMA_DRIFT = "schema_drift"
    EMPTY_OR_ERROR = "empty_or_error"


class Severity(Enum):
    """Severity levels for escalation."""

    CRITICAL = "critical"  # 0-20
    HIGH = "high"  # 21-50
    MEDIUM = "medium"  # 51-70
    LOW = "low"  # 71-100


@dataclass
class DatasetHealthMetrics:
    """Raw health metrics for a single dataset."""

    key: str
    fourfour: str
    row_count: int | None
    last_modified: datetime | None
    schema_snapshot: dict[str, str] | None
    schema_baseline: dict[str, str] | None
    is_accessible: bool
    error_message: str | None = None
    fetch_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DatasetHealthReport:
    """Classified health status and remediation guidance."""

    key: str
    fourfour: str
    status: HealthStatus
    severity: int  # 0-100
    severity_level: Severity
    freshness_days: int | None
    row_count: int | None
    schema_changes: dict[str, Any]  # added, removed, type_changes
    alerts: list[str]
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "key": self.key,
            "fourfour": self.fourfour,
            "status": self.status.value,
            "severity": self.severity,
            "severity_level": self.severity_level.value,
            "freshness_days": self.freshness_days,
            "row_count": self.row_count,
            "schema_changes": self.schema_changes,
            "alerts": self.alerts,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class DatasetHealthClassifier:
    """Classify dataset health and generate remediation guidance.

    Usage:
        classifier = DatasetHealthClassifier(
            sla_thresholds={"HIGH": 14, "MEDIUM": 30, "LOW": 60}
        )
        metrics = DatasetHealthMetrics(
            key="violations",
            fourfour="6kbp-uz6m",
            row_count=312000,
            last_modified=datetime.now(timezone.utc) - timedelta(days=5),
            schema_snapshot={"id": "int64", "status": "object"},
            schema_baseline={"id": "int64", "status": "object"},
            is_accessible=True
        )
        report = classifier.classify(metrics)
        print(f"Status: {report.status.value}, Severity: {report.severity}")
    """

    def __init__(
        self,
        sla_thresholds: dict[str, int] | None = None,
        empty_threshold: int = 100,
    ):
        """Initialize classifier with SLA thresholds.

        Args:
            sla_thresholds: Mapping of SLA level -> days (HIGH: 14, MEDIUM: 30, LOW: 60).
            empty_threshold: Row count below this is considered "empty".
        """
        self.sla_thresholds = sla_thresholds or {
            "HIGH": 14,
            "MEDIUM": 30,
            "LOW": 60,
        }
        self.empty_threshold = empty_threshold

    def classify(self, metrics: DatasetHealthMetrics) -> DatasetHealthReport:
        """Classify dataset health from raw metrics.

        Returns a DatasetHealthReport with status, severity, and recommendations.
        """
        alerts: list[str] = []
        recommendations: list[str] = []
        schema_changes: dict[str, Any] = {}
        freshness_days: int | None = None
        severity = 100  # Start high (healthy)

        # 1. Accessibility check
        if not metrics.is_accessible:
            return DatasetHealthReport(
                key=metrics.key,
                fourfour=metrics.fourfour,
                status=HealthStatus.EMPTY_OR_ERROR,
                severity=10,
                severity_level=Severity.CRITICAL,
                freshness_days=None,
                row_count=metrics.row_count,
                schema_changes={},
                alerts=[f"Dataset is not accessible: {metrics.error_message or 'Unknown error'}"],
                recommendations=[
                    "Check Socrata API endpoint availability",
                    "Verify dataset permissions and access controls",
                    f"Contact NYC Open Data support for fourfour={metrics.fourfour}",
                ],
            )

        # 2. Freshness check (before empty-row check so stale datasets are classified as STALE)
        if metrics.last_modified:
            now = datetime.now(timezone.utc)
            freshness_days = (now - metrics.last_modified).days

            # Determine SLA level (assume MEDIUM if not specified)
            sla_threshold = self.sla_thresholds.get("MEDIUM", 30)
            if freshness_days > sla_threshold:
                status = HealthStatus.STALE
                alerts.append(
                    f"Data is stale: {freshness_days} days old (SLA: {sla_threshold} days)"
                )
                recommendations.append(
                    f"Investigate why updates have paused (expected refresh every {sla_threshold} days)"
                )
                recommendations.append("Check data source and ETL pipeline health")
                severity = 40
            else:
                severity = max(70, severity - (freshness_days * 2))  # Decay based on age
        else:
            alerts.append("No last-modified timestamp available")
            severity = 60

        # 3. Row count check (only if not already classified as stale)
        if "status" not in locals() and (
            metrics.row_count is None or metrics.row_count < self.empty_threshold
        ):
            alerts.append(f"Dataset is empty or nearly empty ({metrics.row_count} rows)")
            recommendations.append("Verify data ingestion pipeline is running")
            recommendations.append("Check source system for data availability")
            return DatasetHealthReport(
                key=metrics.key,
                fourfour=metrics.fourfour,
                status=HealthStatus.EMPTY_OR_ERROR,
                severity=20,
                severity_level=Severity.CRITICAL,
                freshness_days=freshness_days,
                row_count=metrics.row_count,
                schema_changes={},
                alerts=alerts,
                recommendations=recommendations,
            )

        # 4. Schema drift check
        if metrics.schema_baseline and metrics.schema_snapshot:
            schema_changes = self._detect_schema_changes(
                metrics.schema_baseline,
                metrics.schema_snapshot,
            )
            if (
                schema_changes.get("added_columns")
                or schema_changes.get("removed_columns")
                or schema_changes.get("type_changes")
            ):
                status = HealthStatus.SCHEMA_DRIFT
                alerts.append(
                    f"Schema has drifted: {len(schema_changes.get('type_changes', []))} type changes"
                )
                recommendations.append("Review schema changes against data dictionary")
                recommendations.append("Update downstream code to handle new/removed columns")
                severity = min(severity, 50)

        # Determine overall status if not already set
        if "status" not in locals():
            status = HealthStatus.HEALTHY

        # Convert severity to enum
        if severity <= 20:
            severity_level = Severity.CRITICAL
        elif severity <= 50:
            severity_level = Severity.HIGH
        elif severity <= 70:
            severity_level = Severity.MEDIUM
        else:
            severity_level = Severity.LOW

        return DatasetHealthReport(
            key=metrics.key,
            fourfour=metrics.fourfour,
            status=status,
            severity=severity,
            severity_level=severity_level,
            freshness_days=freshness_days,
            row_count=metrics.row_count,
            schema_changes=schema_changes,
            alerts=alerts,
            recommendations=recommendations,
            metadata={
                "sla_threshold_days": sla_threshold if metrics.last_modified else None,
                "last_modified": metrics.last_modified.isoformat()
                if metrics.last_modified
                else None,
            },
        )

    def _detect_schema_changes(
        self,
        baseline: dict[str, str],
        current: dict[str, str],
    ) -> dict[str, Any]:
        """Detect schema drift between baseline and current snapshots.

        Args:
            baseline: Previous schema as {column: dtype} dict.
            current: Current schema as {column: dtype} dict.

        Returns:
            {
                "added_columns": [...],
                "removed_columns": [...],
                "type_changes": [{"column": "x", "from": "int64", "to": "object"}],
                "is_compatible": bool
            }
        """
        baseline_cols = set(baseline.keys())
        current_cols = set(current.keys())

        added = sorted(current_cols - baseline_cols)
        removed = sorted(baseline_cols - current_cols)
        type_changes = []

        for col in baseline_cols & current_cols:
            if baseline[col] != current[col]:
                type_changes.append(
                    {
                        "column": col,
                        "from": baseline[col],
                        "to": current[col],
                    }
                )

        is_compatible = len(removed) == 0 and len(type_changes) == 0

        return {
            "added_columns": added,
            "removed_columns": removed,
            "type_changes": type_changes,
            "is_compatible": is_compatible,
        }

    def classify_batch(self, metrics_list: list[DatasetHealthMetrics]) -> list[DatasetHealthReport]:
        """Classify multiple datasets and return reports.

        Args:
            metrics_list: List of DatasetHealthMetrics objects.

        Returns:
            List of DatasetHealthReport objects, same order as input.
        """
        return [self.classify(m) for m in metrics_list]

    def summarize(self, reports: list[DatasetHealthReport]) -> dict[str, Any]:
        """Summarize health across a list of reports.

        Returns:
            {
                "total": int,
                "healthy": int,
                "stale": int,
                "schema_drift": int,
                "empty_or_error": int,
                "critical_alerts": [...],
                "needs_attention": [...]
            }
        """
        summary = {
            "total": len(reports),
            "healthy": 0,
            "stale": 0,
            "schema_drift": 0,
            "empty_or_error": 0,
            "critical_alerts": [],
            "needs_attention": [],
        }

        for report in reports:
            if report.status == HealthStatus.HEALTHY:
                summary["healthy"] += 1
            elif report.status == HealthStatus.STALE:
                summary["stale"] += 1
            elif report.status == HealthStatus.SCHEMA_DRIFT:
                summary["schema_drift"] += 1
            else:
                summary["empty_or_error"] += 1

            if report.severity <= 20:
                summary["critical_alerts"].append(
                    {
                        "key": report.key,
                        "fourfour": report.fourfour,
                        "status": report.status.value,
                        "alerts": report.alerts,
                    }
                )

            if report.severity <= 70:
                summary["needs_attention"].append(
                    {
                        "key": report.key,
                        "fourfour": report.fourfour,
                        "severity": report.severity,
                        "status": report.status.value,
                        "primary_alert": report.alerts[0] if report.alerts else "Unknown issue",
                    }
                )

        return summary
