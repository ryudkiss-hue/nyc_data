"""Monitoring module for the observability subsystem.

Provides:
- MonitoringResult — the outcome of a single monitoring check
- Monitoring — runs the five standard data-quality checks
- Alert, AlertManager, AlertSeverity, AlertStatus — re-exported from alerts.manager
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..alerts.manager import Alert, AlertManager, AlertSeverity, AlertStatus


@dataclass
class MonitoringResult:
    """The result of a single monitoring check."""

    check_name: str
    dataset_name: str
    status: str  # "PASS" or "FAIL"
    alerts: list[Alert] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check result."""

    service: str
    status: str
    timestamp: datetime
    latency_ms: float | None = None


class HealthMonitor:
    """Monitor system health metrics."""

    def __init__(self):
        self.checks: list[HealthCheck] = []

    def record_check(self, service: str, status: str, latency_ms: float | None = None):
        """Record a health check result."""
        check = HealthCheck(service, status, datetime.utcnow(), latency_ms)
        self.checks.append(check)

    def get_status(self, service: str) -> str | None:
        """Get the latest status for a service."""
        matching = [c for c in self.checks if c.service == service]
        return matching[-1].status if matching else None


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


class Monitoring:
    """Operational monitoring — runs the five standard data-quality checks.

    Each check method returns a MonitoringResult and accumulates alerts in
    ``self.results`` so that ``get_all_alerts()`` can aggregate them.
    """

    def __init__(self):
        self.results: list[MonitoringResult] = []
        # Legacy component (kept for backward compatibility)
        self.health_monitor = HealthMonitor()

    # ------------------------------------------------------------------
    # 1. Data freshness
    # ------------------------------------------------------------------

    def check_data_freshness(
        self,
        dataset_name: str,
        last_modified: datetime | str,
        freshness_threshold_hours: float = 24.0,
    ) -> MonitoringResult:
        """Check whether a dataset has been updated within the threshold.

        Parameters
        ----------
        dataset_name:
            Human-readable name of the dataset being checked.
        last_modified:
            When the dataset was last updated. Accepts a ``datetime`` (aware or
            naive) or an ISO-8601 string.
        freshness_threshold_hours:
            Maximum acceptable age in hours before raising a HIGH alert.
        """
        # Normalise to an aware datetime
        if isinstance(last_modified, str):
            # fromisoformat handles "+00:00" suffixes; handle trailing "Z" too
            ts = last_modified.replace("Z", "+00:00")
            last_modified = datetime.fromisoformat(ts)

        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_seconds = (now - last_modified).total_seconds()
        age_hours = age_seconds / 3600.0

        alerts: list[Alert] = []
        if age_hours > freshness_threshold_hours:
            alerts.append(
                Alert.create(
                    severity=AlertSeverity.HIGH,
                    message=(
                        f"Dataset '{dataset_name}' is stale: "
                        f"{age_hours:.1f}h old (threshold {freshness_threshold_hours}h)"
                    ),
                    alert_type="data_freshness",
                    payload={
                        "dataset_name": dataset_name,
                        "age_hours": age_hours,
                        "threshold_hours": freshness_threshold_hours,
                    },
                    dataset_name=dataset_name,
                    check_name="data_freshness",
                )
            )

        result = MonitoringResult(
            check_name="data_freshness",
            dataset_name=dataset_name,
            status="FAIL" if alerts else "PASS",
            alerts=alerts,
            details={
                "age_hours": age_hours,
                "threshold_hours": freshness_threshold_hours,
                "last_modified": last_modified.isoformat(),
            },
        )
        self.results.append(result)
        return result

    # ------------------------------------------------------------------
    # 2. Validation failures
    # ------------------------------------------------------------------

    def check_validation_failures(
        self,
        dataset_name: str,
        audit_entries: list[dict[str, Any]],
        failure_threshold_pct: float = 5.0,
    ) -> MonitoringResult:
        """Check whether the validation failure rate exceeds the threshold.

        Parameters
        ----------
        dataset_name:
            Name of the dataset being checked.
        audit_entries:
            List of audit-log dicts, each with a ``"status"`` key whose value
            is either ``"failure"`` or anything else (treated as success).
        failure_threshold_pct:
            Maximum acceptable failure percentage before raising a MEDIUM alert.
        """
        total = len(audit_entries)
        alerts: list[Alert] = []
        failure_pct = 0.0

        if total == 0:
            result = MonitoringResult(
                check_name="validation_failures",
                dataset_name=dataset_name,
                status="PASS",
                alerts=[],
                details={"total_checks": 0, "failure_count": 0, "failure_pct": 0.0},
            )
            self.results.append(result)
            return result

        failure_count = sum(1 for e in audit_entries if e.get("status") == "failure")
        failure_pct = (failure_count / total) * 100.0

        if failure_pct > failure_threshold_pct:
            alerts.append(
                Alert.create(
                    severity=AlertSeverity.MEDIUM,
                    message=(
                        f"Dataset '{dataset_name}' validation failure rate "
                        f"{failure_pct:.1f}% exceeds threshold {failure_threshold_pct}%"
                    ),
                    alert_type="validation_failures",
                    payload={
                        "dataset_name": dataset_name,
                        "total_checks": total,
                        "failure_count": failure_count,
                        "failure_pct": failure_pct,
                        "threshold_pct": failure_threshold_pct,
                    },
                    dataset_name=dataset_name,
                    check_name="validation_failures",
                )
            )

        result = MonitoringResult(
            check_name="validation_failures",
            dataset_name=dataset_name,
            status="FAIL" if alerts else "PASS",
            alerts=alerts,
            details={
                "total_checks": total,
                "failure_count": failure_count,
                "failure_pct": failure_pct,
                "threshold_pct": failure_threshold_pct,
            },
        )
        self.results.append(result)
        return result

    # ------------------------------------------------------------------
    # 3. Row count anomalies
    # ------------------------------------------------------------------

    def check_row_count_anomalies(
        self,
        dataset_name: str,
        current_count: int,
        baseline_count: int,
        anomaly_threshold_pct: float = 10.0,
    ) -> MonitoringResult:
        """Check whether row count has changed beyond the threshold.

        Parameters
        ----------
        dataset_name:
            Name of the dataset being checked.
        current_count:
            Current number of rows.
        baseline_count:
            Expected (baseline) number of rows.
        anomaly_threshold_pct:
            Maximum acceptable percentage change from baseline before raising
            a MEDIUM alert.
        """
        if baseline_count == 0:
            # Any non-zero count is a 100% change from an empty baseline
            variance_pct = 100.0 if current_count != 0 else 0.0
        else:
            variance_pct = abs(current_count - baseline_count) / baseline_count * 100.0

        alerts: list[Alert] = []
        if variance_pct > anomaly_threshold_pct:
            direction = "+" if current_count >= baseline_count else "-"
            pct_display = f"{direction}{variance_pct:.0f}%"
            alerts.append(
                Alert.create(
                    severity=AlertSeverity.MEDIUM,
                    message=(
                        f"Dataset '{dataset_name}' row count anomaly: "
                        f"{current_count} rows ({pct_display} vs baseline {baseline_count})"
                    ),
                    alert_type="row_count_anomaly",
                    payload={
                        "dataset_name": dataset_name,
                        "current_count": current_count,
                        "baseline_count": baseline_count,
                        "variance_pct": variance_pct,
                        "threshold_pct": anomaly_threshold_pct,
                    },
                    dataset_name=dataset_name,
                    check_name="row_count_anomaly",
                )
            )

        result = MonitoringResult(
            check_name="row_count_anomaly",
            dataset_name=dataset_name,
            status="FAIL" if alerts else "PASS",
            alerts=alerts,
            details={
                "current_count": current_count,
                "baseline_count": baseline_count,
                "variance_pct": variance_pct,
                "threshold_pct": anomaly_threshold_pct,
            },
        )
        self.results.append(result)
        return result

    # ------------------------------------------------------------------
    # 4. Reconciliation discrepancies
    # ------------------------------------------------------------------

    def check_reconciliation_discrepancies(
        self,
        dataset_name: str,
        reconciliation_results: list[dict[str, Any]],
        discrepancy_threshold_pct: float = 5.0,
    ) -> MonitoringResult:
        """Check whether reconciliation results exceed the failure threshold.

        Parameters
        ----------
        dataset_name:
            Name of the dataset being checked.
        reconciliation_results:
            List of dicts, each with a ``"status"`` key (``"OK"`` or ``"FAIL"``).
        discrepancy_threshold_pct:
            Maximum acceptable percentage of failed reconciliation checks before
            raising a MEDIUM alert.
        """
        total = len(reconciliation_results)
        alerts: list[Alert] = []

        if total == 0:
            result = MonitoringResult(
                check_name="reconciliation_discrepancies",
                dataset_name=dataset_name,
                status="PASS",
                alerts=[],
                details={"total_checks": 0, "failed_checks": 0, "failure_pct": 0.0},
            )
            self.results.append(result)
            return result

        failed = sum(1 for r in reconciliation_results if r.get("status") != "OK")
        failure_pct = (failed / total) * 100.0

        if failure_pct > discrepancy_threshold_pct:
            alerts.append(
                Alert.create(
                    severity=AlertSeverity.MEDIUM,
                    message=(
                        f"Dataset '{dataset_name}' reconciliation discrepancy: "
                        f"{failed}/{total} checks failed ({failure_pct:.1f}%)"
                    ),
                    alert_type="reconciliation_discrepancy",
                    payload={
                        "dataset_name": dataset_name,
                        "total_checks": total,
                        "failed_checks": failed,
                        "failure_pct": failure_pct,
                        "threshold_pct": discrepancy_threshold_pct,
                    },
                    dataset_name=dataset_name,
                    check_name="reconciliation_discrepancies",
                )
            )

        result = MonitoringResult(
            check_name="reconciliation_discrepancies",
            dataset_name=dataset_name,
            status="FAIL" if alerts else "PASS",
            alerts=alerts,
            details={
                "total_checks": total,
                "failed_checks": failed,
                "failure_pct": failure_pct,
                "threshold_pct": discrepancy_threshold_pct,
            },
        )
        self.results.append(result)
        return result

    # ------------------------------------------------------------------
    # 5. Domain rule breaches
    # ------------------------------------------------------------------

    def check_domain_rule_breaches(
        self,
        dataset_name: str,
        domain_rule_results: list[dict[str, Any]],
    ) -> MonitoringResult:
        """Check whether any domain rules have been breached.

        Severity is determined by the number of breached rules:
        - 1 breach  → LOW alert
        - 2+ breaches → MEDIUM alert

        Any status other than ``"PASS"`` (e.g. ``"FAIL"`` or ``"WARNING"``)
        counts as a breach.

        Parameters
        ----------
        dataset_name:
            Name of the dataset being checked.
        domain_rule_results:
            List of dicts, each with ``"rule_name"`` and ``"status"`` keys.
        """
        breaches = [r for r in domain_rule_results if r.get("status") not in ("PASS",)]
        breach_count = len(breaches)

        alerts: list[Alert] = []
        if breach_count > 0:
            severity = AlertSeverity.LOW if breach_count == 1 else AlertSeverity.MEDIUM
            breach_names = [r.get("rule_name", "unknown") for r in breaches]
            alerts.append(
                Alert.create(
                    severity=severity,
                    message=(
                        f"Dataset '{dataset_name}' domain rule breach(es): "
                        f"{', '.join(breach_names)}"
                    ),
                    alert_type="domain_rule_breach",
                    payload={
                        "dataset_name": dataset_name,
                        "breach_count": breach_count,
                        "breached_rules": breach_names,
                    },
                    dataset_name=dataset_name,
                    check_name="domain_rule_breaches",
                )
            )

        result = MonitoringResult(
            check_name="domain_rule_breaches",
            dataset_name=dataset_name,
            status="FAIL" if alerts else "PASS",
            alerts=alerts,
            details={
                "total_rules": len(domain_rule_results),
                "breach_count": breach_count,
                "breached_rules": [r.get("rule_name") for r in breaches],
            },
        )
        self.results.append(result)
        return result

    # ------------------------------------------------------------------
    # Alert aggregation
    # ------------------------------------------------------------------

    def get_all_alerts(self) -> list[Alert]:
        """Return all alerts generated by all checks run so far."""
        all_alerts: list[Alert] = []
        for r in self.results:
            all_alerts.extend(r.alerts)
        return all_alerts

    def get_alerts_by_severity(self, severity: AlertSeverity) -> list[Alert]:
        """Return all alerts with the given severity."""
        return [a for a in self.get_all_alerts() if a.severity == severity]

    def reset(self) -> None:
        """Clear all accumulated monitoring results."""
        self.results = []

    # ------------------------------------------------------------------
    # Legacy compatibility
    # ------------------------------------------------------------------

    def check_service(self, service: str) -> str | None:
        return self.health_monitor.get_status(service)


__all__ = [
    "Alert",
    "AlertManager",
    "AlertSeverity",
    "AlertStatus",
    "HealthCheck",
    "HealthMonitor",
    "Monitoring",
    "MonitoringResult",
]
