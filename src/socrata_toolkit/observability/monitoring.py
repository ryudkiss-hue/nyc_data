"""Operational Monitoring System with Real-Time Alerts for Data Quality Issues.

Provides comprehensive monitoring of data freshness, validation failures, row count
anomalies, reconciliation discrepancies, and domain rule breaches. Generates alerts
with configurable thresholds and integrates with notification systems (logging, Slack, email).

Key components:
- Alert dataclass for alert definition with severity tracking
- Monitoring class for executing quality checks
- AlertManager for alert lifecycle management and persistence
- DuckDB persistence for alert history and analytics

Standards: Python 3.11+, full type hints, comprehensive docstrings
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlertStatus(str, Enum):
    """Alert status lifecycle."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Represents a single data quality alert.

    Attributes:
        alert_id: Unique identifier for this alert
        severity: Severity level (HIGH, MEDIUM, LOW)
        message: Human-readable alert message
        alert_type: Type of check that triggered (freshness, validation, row_count, etc)
        timestamp: When the alert was created (ISO 8601)
        status: Current status (new, acknowledged, resolved)
        payload: Detailed context (thresholds, actual values, affected items)
        dataset_name: Name of the dataset being monitored
        check_name: Name of the check that triggered the alert
    """
    alert_id: str
    severity: AlertSeverity
    message: str
    alert_type: str
    timestamp: str
    status: AlertStatus
    payload: Dict[str, Any]
    dataset_name: str
    check_name: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "message": self.message,
            "alert_type": self.alert_type,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "payload": self.payload,
            "dataset_name": self.dataset_name,
            "check_name": self.check_name,
        }

    @staticmethod
    def create(
        severity: AlertSeverity,
        message: str,
        alert_type: str,
        payload: Dict[str, Any],
        dataset_name: str,
        check_name: str,
    ) -> Alert:
        """Factory method to create a new alert with auto-generated ID and timestamp."""
        return Alert(
            alert_id=str(uuid4()),
            severity=severity,
            message=message,
            alert_type=alert_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=AlertStatus.NEW,
            payload=payload,
            dataset_name=dataset_name,
            check_name=check_name,
        )


@dataclass
class MonitoringResult:
    """Result of a single monitoring check.

    Attributes:
        check_name: Name of the check
        status: PASS, WARNING, or FAIL
        alerts: List of alerts generated (if any)
        details: Additional context about the check
    """
    check_name: str
    status: str
    alerts: List[Alert] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class Monitoring:
    """Executes data quality checks and generates alerts.

    Provides methods for checking data freshness, validation failures, row count
    anomalies, reconciliation discrepancies, and domain rule breaches.
    """

    def __init__(self):
        """Initialize the Monitoring system."""
        self.results: List[MonitoringResult] = []
        logger.info("Monitoring system initialized")

    def check_data_freshness(
        self,
        dataset_name: str,
        last_modified: datetime,
        freshness_threshold_hours: int = 24,
    ) -> MonitoringResult:
        """Check if dataset freshness exceeds threshold.

        Alert Type: data_freshness
        Severity: HIGH if >24 hours old

        Args:
            dataset_name: Name of the dataset
            last_modified: When the dataset was last updated
            freshness_threshold_hours: Maximum age before alert (default: 24h)

        Returns:
            MonitoringResult with any generated alerts
        """
        result = MonitoringResult(
            check_name="data_freshness",
            status="PASS",
            details={},
        )

        now = datetime.now(timezone.utc)
        if isinstance(last_modified, str):
            last_modified = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)

        age_hours = (now - last_modified).total_seconds() / 3600
        result.details = {
            "last_modified": last_modified.isoformat(),
            "age_hours": round(age_hours, 2),
            "threshold_hours": freshness_threshold_hours,
        }

        if age_hours > freshness_threshold_hours:
            result.status = "FAIL"
            alert = Alert.create(
                severity=AlertSeverity.HIGH,
                message=f"Dataset {dataset_name} is stale: {age_hours:.1f}h old (threshold: {freshness_threshold_hours}h)",
                alert_type="data_freshness",
                payload={
                    "dataset": dataset_name,
                    "age_hours": age_hours,
                    "threshold_hours": freshness_threshold_hours,
                    "last_modified": last_modified.isoformat(),
                },
                dataset_name=dataset_name,
                check_name="data_freshness",
            )
            result.alerts.append(alert)
            logger.warning(f"Freshness alert for {dataset_name}: {age_hours:.1f}h old")
        else:
            result.status = "PASS"
            logger.debug(f"Freshness OK for {dataset_name}: {age_hours:.1f}h old")

        self.results.append(result)
        return result

    def check_validation_failures(
        self,
        dataset_name: str,
        audit_entries: List[Dict[str, Any]],
        failure_threshold_pct: float = 5.0,
    ) -> MonitoringResult:
        """Check if validation failures exceed threshold.

        Alert Type: validation_failures
        Severity: MEDIUM if >5% fail

        Args:
            dataset_name: Name of the dataset
            audit_entries: List of audit log entries (from AuditLogger)
            failure_threshold_pct: Threshold percentage (default: 5%)

        Returns:
            MonitoringResult with any generated alerts
        """
        result = MonitoringResult(
            check_name="validation_failures",
            status="PASS",
            details={},
        )

        if not audit_entries:
            result.details = {"total_checks": 0, "failures": 0, "failure_pct": 0}
            logger.debug(f"No audit entries for {dataset_name}")
            return result

        total_checks = len(audit_entries)
        failure_count = sum(
            1 for entry in audit_entries
            if entry.get("status") == "failure" or entry.get("status") == "error"
        )
        failure_pct = (failure_count / total_checks * 100) if total_checks > 0 else 0

        result.details = {
            "total_checks": total_checks,
            "failures": failure_count,
            "failure_pct": round(failure_pct, 2),
            "threshold_pct": failure_threshold_pct,
        }

        if failure_pct > failure_threshold_pct:
            result.status = "FAIL"
            alert = Alert.create(
                severity=AlertSeverity.MEDIUM,
                message=f"Dataset {dataset_name}: {failure_pct:.1f}% validation failures (threshold: {failure_threshold_pct}%)",
                alert_type="validation_failures",
                payload={
                    "dataset": dataset_name,
                    "total_checks": total_checks,
                    "failures": failure_count,
                    "failure_pct": failure_pct,
                    "threshold_pct": failure_threshold_pct,
                },
                dataset_name=dataset_name,
                check_name="validation_failures",
            )
            result.alerts.append(alert)
            logger.warning(f"Validation failure alert for {dataset_name}: {failure_pct:.1f}% failed")
        else:
            result.status = "PASS"
            logger.debug(f"Validation OK for {dataset_name}: {failure_pct:.1f}% failed")

        self.results.append(result)
        return result

    def check_row_count_anomalies(
        self,
        dataset_name: str,
        current_count: int,
        baseline_count: int,
        anomaly_threshold_pct: float = 5.0,
    ) -> MonitoringResult:
        """Check if row count variance exceeds threshold.

        Alert Type: row_count_anomaly
        Severity: MEDIUM if >5% variance

        Args:
            dataset_name: Name of the dataset
            current_count: Current row count
            baseline_count: Expected/baseline row count
            anomaly_threshold_pct: Threshold percentage (default: 5%)

        Returns:
            MonitoringResult with any generated alerts
        """
        result = MonitoringResult(
            check_name="row_count_anomalies",
            status="PASS",
            details={},
        )

        if baseline_count == 0:
            variance_pct = 100.0 if current_count != 0 else 0.0
        else:
            variance_pct = abs((current_count - baseline_count) / baseline_count * 100)

        result.details = {
            "current_count": current_count,
            "baseline_count": baseline_count,
            "variance_pct": round(variance_pct, 2),
            "threshold_pct": anomaly_threshold_pct,
        }

        if variance_pct > anomaly_threshold_pct:
            result.status = "FAIL"
            alert = Alert.create(
                severity=AlertSeverity.MEDIUM,
                message=f"Dataset {dataset_name}: row count variance {variance_pct:.1f}% (current: {current_count}, baseline: {baseline_count})",
                alert_type="row_count_anomaly",
                payload={
                    "dataset": dataset_name,
                    "current_count": current_count,
                    "baseline_count": baseline_count,
                    "variance_pct": variance_pct,
                    "threshold_pct": anomaly_threshold_pct,
                },
                dataset_name=dataset_name,
                check_name="row_count_anomalies",
            )
            result.alerts.append(alert)
            logger.warning(f"Row count anomaly alert for {dataset_name}: {variance_pct:.1f}% variance")
        else:
            result.status = "PASS"
            logger.debug(f"Row count OK for {dataset_name}: {variance_pct:.1f}% variance")

        self.results.append(result)
        return result

    def check_reconciliation_discrepancies(
        self,
        dataset_name: str,
        reconciliation_results: List[Dict[str, Any]],
        discrepancy_threshold_pct: float = 5.0,
    ) -> MonitoringResult:
        """Check if reconciliation discrepancies exceed threshold.

        Alert Type: reconciliation_discrepancy
        Severity: MEDIUM if >5% difference

        Args:
            dataset_name: Name of the dataset
            reconciliation_results: List of reconciliation check results
            discrepancy_threshold_pct: Threshold percentage (default: 5%)

        Returns:
            MonitoringResult with any generated alerts
        """
        result = MonitoringResult(
            check_name="reconciliation_discrepancies",
            status="PASS",
            details={},
        )

        if not reconciliation_results:
            result.details = {"total_checks": 0, "failures": 0}
            logger.debug(f"No reconciliation results for {dataset_name}")
            return result

        # Count failures (status != "OK")
        total_checks = len(reconciliation_results)
        failed_checks = [
            r for r in reconciliation_results
            if r.get("status") != "OK"
        ]
        failure_count = len(failed_checks)
        failure_pct = (failure_count / total_checks * 100) if total_checks > 0 else 0

        # Get max variance for detail
        max_variance = max(
            (abs(r.get("variance_pct", 0)) for r in reconciliation_results),
            default=0.0,
        )

        result.details = {
            "total_checks": total_checks,
            "failed_checks": failure_count,
            "failure_pct": round(failure_pct, 2),
            "max_variance_pct": round(max_variance, 2),
            "threshold_pct": discrepancy_threshold_pct,
        }

        if failure_pct > discrepancy_threshold_pct:
            result.status = "FAIL"
            failed_tables = [r.get("table") for r in failed_checks]
            alert = Alert.create(
                severity=AlertSeverity.MEDIUM,
                message=f"Dataset {dataset_name}: {failure_pct:.1f}% reconciliation discrepancies (tables: {', '.join(failed_tables[:3])})",
                alert_type="reconciliation_discrepancy",
                payload={
                    "dataset": dataset_name,
                    "total_checks": total_checks,
                    "failed_checks": failure_count,
                    "failure_pct": failure_pct,
                    "max_variance_pct": max_variance,
                    "failed_tables": failed_tables,
                    "threshold_pct": discrepancy_threshold_pct,
                },
                dataset_name=dataset_name,
                check_name="reconciliation_discrepancies",
            )
            result.alerts.append(alert)
            logger.warning(f"Reconciliation alert for {dataset_name}: {failure_pct:.1f}% discrepancies")
        else:
            result.status = "PASS"
            logger.debug(f"Reconciliation OK for {dataset_name}: {failure_pct:.1f}% discrepancies")

        self.results.append(result)
        return result

    def check_domain_rule_breaches(
        self,
        dataset_name: str,
        domain_rule_results: List[Dict[str, Any]],
    ) -> MonitoringResult:
        """Check if domain rule violations exist.

        Alert Type: domain_rule_breach
        Severity: LOW-MEDIUM for any violations

        Args:
            dataset_name: Name of the dataset
            domain_rule_results: List of domain rule check results (from DomainRules)

        Returns:
            MonitoringResult with any generated alerts
        """
        result = MonitoringResult(
            check_name="domain_rule_breaches",
            status="PASS",
            details={},
        )

        if not domain_rule_results:
            result.details = {"total_rules": 0, "failures": 0}
            logger.debug(f"No domain rule results for {dataset_name}")
            return result

        # Count rule failures
        total_rules = len(domain_rule_results)
        failed_rules = [
            r for r in domain_rule_results
            if r.get("status") in ("FAIL", "WARNING")
        ]
        failure_count = len(failed_rules)

        result.details = {
            "total_rules": total_rules,
            "failures": failure_count,
            "rule_names": [r.get("rule_name") for r in domain_rule_results],
            "failed_rules": [r.get("rule_name") for r in failed_rules],
        }

        if failure_count > 0:
            result.status = "FAIL"
            # Determine severity based on number of failures
            severity = AlertSeverity.MEDIUM if failure_count > 1 else AlertSeverity.LOW
            failed_rule_names = [r.get("rule_name") for r in failed_rules]

            alert = Alert.create(
                severity=severity,
                message=f"Dataset {dataset_name}: {failure_count} domain rule violations (rules: {', '.join(failed_rule_names)})",
                alert_type="domain_rule_breach",
                payload={
                    "dataset": dataset_name,
                    "total_rules": total_rules,
                    "failures": failure_count,
                    "failed_rules": failed_rule_names,
                    "failed_rule_details": [asdict(r) if hasattr(r, '__dataclass_fields__') else r for r in failed_rules],
                },
                dataset_name=dataset_name,
                check_name="domain_rule_breaches",
            )
            result.alerts.append(alert)
            logger.warning(f"Domain rule breach alert for {dataset_name}: {failure_count} violations")
        else:
            result.status = "PASS"
            logger.debug(f"Domain rules OK for {dataset_name}")

        self.results.append(result)
        return result

    def get_all_alerts(self) -> List[Alert]:
        """Get all alerts from all monitoring results."""
        all_alerts: List[Alert] = []
        for result in self.results:
            all_alerts.extend(result.alerts)
        return all_alerts

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get all alerts of a specific severity."""
        return [a for a in self.get_all_alerts() if a.severity == severity]

    def reset(self) -> None:
        """Reset all monitoring results."""
        self.results = []
        logger.debug("Monitoring results reset")


class AlertManager:
    """Manages alert lifecycle, persistence, and notifications.

    Tracks alert state (new, acknowledged, resolved), stores alerts in DuckDB,
    and triggers notifications via configured channels (logging, Slack, email).
    """

    def __init__(self, duckdb_conn=None):
        """Initialize AlertManager.

        Args:
            duckdb_conn: Optional DuckDB connection for persistence
        """
        self.duckdb_conn = duckdb_conn
        self.alerts: Dict[str, Alert] = {}  # alert_id -> Alert
        self.alert_history: List[Dict[str, Any]] = []
        self.notification_handlers: List[Callable[[Alert], None]] = []
        logger.info("AlertManager initialized")

    def register_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Register a handler to be called when alerts are triggered.

        Args:
            handler: Callable that takes an Alert and sends notification
        """
        self.notification_handlers.append(handler)
        logger.info(f"Notification handler registered: {handler.__name__}")

    def ingest_alert(self, alert: Alert) -> None:
        """Ingest a new alert into the manager.

        Args:
            alert: Alert to ingest
        """
        self.alerts[alert.alert_id] = alert
        self.alert_history.append(alert.to_dict())

        # Trigger notifications
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")

        logger.info(f"Alert ingested: {alert.alert_id} ({alert.severity.value})")

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: ID of alert to acknowledge

        Returns:
            True if acknowledged, False if alert not found
        """
        if alert_id not in self.alerts:
            logger.warning(f"Alert not found: {alert_id}")
            return False

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        self.alert_history.append({
            **alert.to_dict(),
            "action": "acknowledged",
            "action_time": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Alert acknowledged: {alert_id}")
        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert.

        Args:
            alert_id: ID of alert to resolve

        Returns:
            True if resolved, False if alert not found
        """
        if alert_id not in self.alerts:
            logger.warning(f"Alert not found: {alert_id}")
            return False

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        self.alert_history.append({
            **alert.to_dict(),
            "action": "resolved",
            "action_time": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Alert resolved: {alert_id}")
        return True

    def get_alerts_by_status(self, status: AlertStatus) -> List[Alert]:
        """Get all alerts with specific status.

        Args:
            status: Status to filter by

        Returns:
            List of alerts with matching status
        """
        return [a for a in self.alerts.values() if a.status == status]

    def get_active_alerts(self) -> List[Alert]:
        """Get all non-resolved alerts.

        Returns:
            List of active (new or acknowledged) alerts
        """
        return [
            a for a in self.alerts.values()
            if a.status in (AlertStatus.NEW, AlertStatus.ACKNOWLEDGED)
        ]

    def get_alert_summary(self) -> Dict[str, int]:
        """Get count of alerts by severity.

        Returns:
            Dict with severity -> count
        """
        summary: Dict[str, int] = {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }
        for alert in self.alerts.values():
            if alert.status != AlertStatus.RESOLVED:
                summary[alert.severity.value] += 1
        return summary

    def save_to_duckdb(self, table_name: str = "alert_log") -> bool:
        """Persist alerts to DuckDB.

        Creates the alert table if it doesn't exist, then inserts all alerts.

        Args:
            table_name: Name of the table to create/use

        Returns:
            True if save was successful, False otherwise
        """
        if not self.duckdb_conn:
            logger.warning("DuckDB connection not configured")
            return False

        if not self.alerts:
            logger.warning("No alerts to save")
            return False

        try:
            # Create table if it doesn't exist
            self.duckdb_conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    alert_id VARCHAR PRIMARY KEY,
                    severity VARCHAR,
                    message VARCHAR,
                    alert_type VARCHAR,
                    timestamp VARCHAR,
                    status VARCHAR,
                    payload JSON,
                    dataset_name VARCHAR,
                    check_name VARCHAR
                )
            """)

            # Insert alerts
            for alert in self.alerts.values():
                payload_json = json.dumps(alert.payload)
                try:
                    self.duckdb_conn.execute(f"""
                        INSERT INTO {table_name}
                        (alert_id, severity, message, alert_type, timestamp, status, payload, dataset_name, check_name)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        alert.alert_id,
                        alert.severity.value,
                        alert.message,
                        alert.alert_type,
                        alert.timestamp,
                        alert.status.value,
                        payload_json,
                        alert.dataset_name,
                        alert.check_name,
                    ])
                except Exception as e:
                    logger.debug(f"Alert {alert.alert_id} may already exist: {e}")

            logger.info(f"Successfully saved {len(self.alerts)} alerts to {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to save alerts to DuckDB: {e}")
            return False

    def query_alerts_from_duckdb(
        self,
        table_name: str = "alert_log",
        hours_ago: int = 24,
    ) -> List[Dict[str, Any]]:
        """Query recent alerts from DuckDB.

        Args:
            table_name: Name of the alert table
            hours_ago: Only retrieve alerts from last N hours

        Returns:
            List of alert dictionaries
        """
        if not self.duckdb_conn:
            logger.warning("DuckDB connection not configured")
            return []

        try:
            cutoff_time = datetime.now(timezone.utc)
            cutoff_time = cutoff_time.replace(
                hour=cutoff_time.hour - hours_ago,
                minute=0,
                second=0,
                microsecond=0,
            )

            result = self.duckdb_conn.execute(f"""
                SELECT *
                FROM {table_name}
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, [cutoff_time.isoformat()]).fetchall()

            # Convert to list of dicts
            columns = [desc[0] for desc in self.duckdb_conn.description] if result else []
            return [dict(zip(columns, row)) for row in result]

        except Exception as e:
            logger.error(f"Failed to query alerts from DuckDB: {e}")
            return []
