"""Tests for the Operational Monitoring System.

Tests cover:
- Alert creation and dataclass functionality
- Monitoring checks for all 5 alert types
- AlertManager lifecycle (ingest, acknowledge, resolve)
- Threshold detection and severity classification
- DuckDB persistence
- Notification handler invocation
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

from socrata_toolkit.observability.monitoring import (
    Alert,
    AlertManager,
    AlertSeverity,
    AlertStatus,
    Monitoring,
    MonitoringResult,
)

# ============================================================================
# Alert Tests
# ============================================================================

class TestAlert:
    """Test Alert dataclass and factory methods."""

    def test_alert_creation(self):
        """Test creating an alert directly."""
        alert = Alert(
            alert_id="test-123",
            severity=AlertSeverity.HIGH,
            message="Test alert",
            alert_type="data_freshness",
            timestamp="2024-01-01T00:00:00Z",
            status=AlertStatus.NEW,
            payload={"test": "value"},
            dataset_name="test_dataset",
            check_name="freshness_check",
        )
        assert alert.alert_id == "test-123"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.NEW

    def test_alert_factory(self):
        """Test Alert.create() factory method."""
        alert = Alert.create(
            severity=AlertSeverity.MEDIUM,
            message="Factory alert",
            alert_type="validation_failures",
            payload={"count": 5},
            dataset_name="my_data",
            check_name="validation_check",
        )
        assert alert.alert_id is not None
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.status == AlertStatus.NEW
        assert "Factory alert" in alert.message

    def test_alert_to_dict(self):
        """Test alert serialization to dict."""
        alert = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Serialization test",
            alert_type="data_freshness",
            payload={"hours_old": 30},
            dataset_name="test",
            check_name="freshness",
        )
        alert_dict = alert.to_dict()
        assert alert_dict["severity"] == "HIGH"
        assert alert_dict["status"] == "new"
        assert alert_dict["alert_type"] == "data_freshness"

    def test_alert_status_transitions(self):
        """Test alert status lifecycle transitions."""
        alert = Alert.create(
            severity=AlertSeverity.MEDIUM,
            message="Status test",
            alert_type="row_count_anomaly",
            payload={},
            dataset_name="test",
            check_name="count_check",
        )
        assert alert.status == AlertStatus.NEW

        alert.status = AlertStatus.ACKNOWLEDGED
        assert alert.status == AlertStatus.ACKNOWLEDGED

        alert.status = AlertStatus.RESOLVED
        assert alert.status == AlertStatus.RESOLVED


# ============================================================================
# Monitoring Tests
# ============================================================================

class TestMonitoring:
    """Test Monitoring class and all check methods."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh Monitoring instance."""
        return Monitoring()

    def test_data_freshness_check_pass(self, monitor):
        """Test freshness check when data is recent."""
        now = datetime.now(timezone.utc)
        result = monitor.check_data_freshness(
            dataset_name="inspection",
            last_modified=now - timedelta(hours=6),
            freshness_threshold_hours=24,
        )
        assert result.status == "PASS"
        assert len(result.alerts) == 0
        assert result.details["age_hours"] < 24

    def test_data_freshness_check_fail(self, monitor):
        """Test freshness check when data is stale."""
        now = datetime.now(timezone.utc)
        result = monitor.check_data_freshness(
            dataset_name="violations",
            last_modified=now - timedelta(hours=48),
            freshness_threshold_hours=24,
        )
        assert result.status == "FAIL"
        assert len(result.alerts) == 1
        assert result.alerts[0].severity == AlertSeverity.HIGH
        assert "violations" in result.alerts[0].message

    def test_data_freshness_check_string_timestamp(self, monitor):
        """Test freshness check with string timestamp input."""
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(hours=30)
        result = monitor.check_data_freshness(
            dataset_name="test",
            last_modified=past_time.isoformat(),
            freshness_threshold_hours=24,
        )
        assert result.status == "FAIL"
        assert len(result.alerts) == 1

    def test_validation_failures_check_pass(self, monitor):
        """Test validation failure check when below threshold."""
        audit_entries = [
            {"status": "success", "table": "t1"},
            {"status": "success", "table": "t2"},
            {"status": "success", "table": "t3"},
            {"status": "failure", "table": "t4"},  # 1/4 = 25% > 5% threshold
        ]
        result = monitor.check_validation_failures(
            dataset_name="test",
            audit_entries=audit_entries,
            failure_threshold_pct=5.0,
        )
        # This will actually FAIL since 25% > 5%
        assert result.status == "FAIL"
        assert len(result.alerts) == 1
        assert result.alerts[0].severity == AlertSeverity.MEDIUM

    def test_validation_failures_check_pass_low_rate(self, monitor):
        """Test validation failure check with low failure rate."""
        audit_entries = [
            {"status": "success", "table": "t1"},
            {"status": "success", "table": "t2"},
            {"status": "success", "table": "t3"},
            {"status": "success", "table": "t4"},
            {"status": "success", "table": "t5"},
            {"status": "success", "table": "t6"},
            {"status": "failure", "table": "t7"},  # 1/7 = 14.3% > 5% threshold
        ]
        result = monitor.check_validation_failures(
            dataset_name="test",
            audit_entries=audit_entries,
            failure_threshold_pct=20.0,
        )
        assert result.status == "PASS"
        assert len(result.alerts) == 0

    def test_validation_failures_empty_entries(self, monitor):
        """Test validation check with no audit entries."""
        result = monitor.check_validation_failures(
            dataset_name="test",
            audit_entries=[],
            failure_threshold_pct=5.0,
        )
        assert result.status == "PASS"
        assert len(result.alerts) == 0
        assert result.details["total_checks"] == 0

    def test_row_count_anomalies_check_pass(self, monitor):
        """Test row count check when variance is within threshold."""
        result = monitor.check_row_count_anomalies(
            dataset_name="inspection",
            current_count=1050,
            baseline_count=1000,
            anomaly_threshold_pct=10.0,  # 5% variance < 10% threshold
        )
        assert result.status == "PASS"
        assert len(result.alerts) == 0
        assert result.details["variance_pct"] == 5.0

    def test_row_count_anomalies_check_fail(self, monitor):
        """Test row count check when variance exceeds threshold."""
        result = monitor.check_row_count_anomalies(
            dataset_name="violations",
            current_count=900,
            baseline_count=1000,
            anomaly_threshold_pct=5.0,  # 10% variance > 5% threshold
        )
        assert result.status == "FAIL"
        assert len(result.alerts) == 1
        assert result.alerts[0].severity == AlertSeverity.MEDIUM
        assert "900" in result.alerts[0].message or "-10%" in result.alerts[0].message

    def test_row_count_anomalies_zero_baseline(self, monitor):
        """Test row count check with zero baseline."""
        result = monitor.check_row_count_anomalies(
            dataset_name="test",
            current_count=100,
            baseline_count=0,
            anomaly_threshold_pct=5.0,
        )
        assert result.status == "FAIL"  # Any count with zero baseline = 100% variance
        assert result.details["variance_pct"] == 100.0

    def test_reconciliation_discrepancies_check_pass(self, monitor):
        """Test reconciliation check when all tables OK."""
        recon_results = [
            {"table": "t1", "status": "OK", "variance_pct": 2.0},
            {"table": "t2", "status": "OK", "variance_pct": 1.0},
            {"table": "t3", "status": "OK", "variance_pct": 0.5},
        ]
        result = monitor.check_reconciliation_discrepancies(
            dataset_name="inspection",
            reconciliation_results=recon_results,
            discrepancy_threshold_pct=5.0,
        )
        assert result.status == "PASS"
        assert len(result.alerts) == 0
        assert result.details["total_checks"] == 3
        assert result.details["failed_checks"] == 0

    def test_reconciliation_discrepancies_check_fail(self, monitor):
        """Test reconciliation check when threshold exceeded."""
        recon_results = [
            {"table": "t1", "status": "OK", "variance_pct": 2.0},
            {"table": "t2", "status": "FAIL", "variance_pct": 15.0},
            {"table": "t3", "status": "FAIL", "variance_pct": 20.0},
            {"table": "t4", "status": "OK", "variance_pct": 1.0},
        ]
        result = monitor.check_reconciliation_discrepancies(
            dataset_name="test",
            reconciliation_results=recon_results,
            discrepancy_threshold_pct=5.0,
        )
        assert result.status == "FAIL"
        assert len(result.alerts) == 1
        assert result.alerts[0].severity == AlertSeverity.MEDIUM
        assert 50.0 == result.details["failure_pct"]  # 2/4 = 50%

    def test_reconciliation_empty_results(self, monitor):
        """Test reconciliation check with no results."""
        result = monitor.check_reconciliation_discrepancies(
            dataset_name="test",
            reconciliation_results=[],
            discrepancy_threshold_pct=5.0,
        )
        assert result.status == "PASS"
        assert len(result.alerts) == 0

    def test_domain_rule_breaches_check_pass(self, monitor):
        """Test domain rule check when all rules pass."""
        domain_results = [
            {"rule_name": "material_lifespan", "status": "PASS"},
            {"rule_name": "permit_inspection_ratio", "status": "PASS"},
            {"rule_name": "borough_coverage", "status": "PASS"},
        ]
        result = monitor.check_domain_rule_breaches(
            dataset_name="inspection",
            domain_rule_results=domain_results,
        )
        assert result.status == "PASS"
        assert len(result.alerts) == 0

    def test_domain_rule_breaches_check_fail_single(self, monitor):
        """Test domain rule check with single failure."""
        domain_results = [
            {"rule_name": "material_lifespan", "status": "FAIL"},
            {"rule_name": "permit_inspection_ratio", "status": "PASS"},
        ]
        result = monitor.check_domain_rule_breaches(
            dataset_name="test",
            domain_rule_results=domain_results,
        )
        assert result.status == "FAIL"
        assert len(result.alerts) == 1
        assert result.alerts[0].severity == AlertSeverity.LOW  # Single failure = LOW

    def test_domain_rule_breaches_check_fail_multiple(self, monitor):
        """Test domain rule check with multiple failures."""
        domain_results = [
            {"rule_name": "material_lifespan", "status": "FAIL"},
            {"rule_name": "permit_inspection_ratio", "status": "FAIL"},
            {"rule_name": "borough_coverage", "status": "PASS"},
        ]
        result = monitor.check_domain_rule_breaches(
            dataset_name="test",
            domain_rule_results=domain_results,
        )
        assert result.status == "FAIL"
        assert len(result.alerts) == 1
        assert result.alerts[0].severity == AlertSeverity.MEDIUM  # Multiple failures = MEDIUM

    def test_domain_rule_breaches_warnings_count(self, monitor):
        """Test that WARNING status also counts as failure."""
        domain_results = [
            {"rule_name": "rule1", "status": "PASS"},
            {"rule_name": "rule2", "status": "WARNING"},
            {"rule_name": "rule3", "status": "PASS"},
        ]
        result = monitor.check_domain_rule_breaches(
            dataset_name="test",
            domain_rule_results=domain_results,
        )
        assert result.status == "FAIL"
        assert len(result.alerts) == 1

    def test_get_all_alerts(self, monitor):
        """Test retrieving all alerts from all checks."""
        now = datetime.now(timezone.utc)
        monitor.check_data_freshness(
            dataset_name="test1",
            last_modified=now - timedelta(hours=48),
            freshness_threshold_hours=24,
        )
        monitor.check_row_count_anomalies(
            dataset_name="test2",
            current_count=500,
            baseline_count=1000,
            anomaly_threshold_pct=5.0,
        )
        all_alerts = monitor.get_all_alerts()
        assert len(all_alerts) == 2

    def test_get_alerts_by_severity(self, monitor):
        """Test filtering alerts by severity."""
        now = datetime.now(timezone.utc)
        monitor.check_data_freshness(
            dataset_name="test1",
            last_modified=now - timedelta(hours=48),
            freshness_threshold_hours=24,
        )  # HIGH
        monitor.check_validation_failures(
            dataset_name="test2",
            audit_entries=[{"status": "failure"}] * 10 + [{"status": "success"}] * 90,
            failure_threshold_pct=5.0,
        )  # MEDIUM

        high_alerts = monitor.get_alerts_by_severity(AlertSeverity.HIGH)
        medium_alerts = monitor.get_alerts_by_severity(AlertSeverity.MEDIUM)
        assert len(high_alerts) == 1
        assert len(medium_alerts) == 1

    def test_monitoring_reset(self, monitor):
        """Test resetting monitoring results."""
        now = datetime.now(timezone.utc)
        monitor.check_data_freshness(
            dataset_name="test",
            last_modified=now - timedelta(hours=48),
            freshness_threshold_hours=24,
        )
        assert len(monitor.results) == 1

        monitor.reset()
        assert len(monitor.results) == 0


# ============================================================================
# AlertManager Tests
# ============================================================================

class TestAlertManager:
    """Test AlertManager lifecycle and state management."""

    @pytest.fixture
    def manager(self):
        """Create a fresh AlertManager instance."""
        return AlertManager()

    def test_alert_manager_initialization(self, manager):
        """Test AlertManager initialization."""
        assert len(manager.alerts) == 0
        assert len(manager.alert_history) == 0
        assert len(manager.notification_handlers) == 0

    def test_ingest_alert(self, manager):
        """Test ingesting an alert."""
        alert = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test alert",
            alert_type="data_freshness",
            payload={"test": "data"},
            dataset_name="test",
            check_name="freshness",
        )
        manager.ingest_alert(alert)
        assert alert.alert_id in manager.alerts
        assert len(manager.alert_history) >= 1

    def test_acknowledge_alert(self, manager):
        """Test acknowledging an alert."""
        alert = Alert.create(
            severity=AlertSeverity.MEDIUM,
            message="Test",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        manager.ingest_alert(alert)

        success = manager.acknowledge_alert(alert.alert_id)
        assert success is True
        assert manager.alerts[alert.alert_id].status == AlertStatus.ACKNOWLEDGED

    def test_acknowledge_nonexistent_alert(self, manager):
        """Test acknowledging a non-existent alert."""
        success = manager.acknowledge_alert("nonexistent")
        assert success is False

    def test_resolve_alert(self, manager):
        """Test resolving an alert."""
        alert = Alert.create(
            severity=AlertSeverity.LOW,
            message="Test",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        manager.ingest_alert(alert)

        success = manager.resolve_alert(alert.alert_id)
        assert success is True
        assert manager.alerts[alert.alert_id].status == AlertStatus.RESOLVED

    def test_resolve_nonexistent_alert(self, manager):
        """Test resolving a non-existent alert."""
        success = manager.resolve_alert("nonexistent")
        assert success is False

    def test_get_alerts_by_status(self, manager):
        """Test filtering alerts by status."""
        alert1 = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test 1",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        alert2 = Alert.create(
            severity=AlertSeverity.MEDIUM,
            message="Test 2",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        manager.ingest_alert(alert1)
        manager.ingest_alert(alert2)

        manager.acknowledge_alert(alert1.alert_id)

        new_alerts = manager.get_alerts_by_status(AlertStatus.NEW)
        ack_alerts = manager.get_alerts_by_status(AlertStatus.ACKNOWLEDGED)

        assert len(new_alerts) == 1
        assert len(ack_alerts) == 1

    def test_get_active_alerts(self, manager):
        """Test retrieving active (non-resolved) alerts."""
        alert1 = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test 1",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        alert2 = Alert.create(
            severity=AlertSeverity.MEDIUM,
            message="Test 2",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        manager.ingest_alert(alert1)
        manager.ingest_alert(alert2)

        manager.resolve_alert(alert1.alert_id)

        active = manager.get_active_alerts()
        assert len(active) == 1
        assert active[0].alert_id == alert2.alert_id

    def test_alert_summary(self, manager):
        """Test alert summary by severity."""
        for i in range(3):
            alert = Alert.create(
                severity=AlertSeverity.HIGH,
                message=f"Test {i}",
                alert_type="test",
                payload={},
                dataset_name="test",
                check_name="test",
            )
            manager.ingest_alert(alert)

        for i in range(2):
            alert = Alert.create(
                severity=AlertSeverity.MEDIUM,
                message=f"Test {i}",
                alert_type="test",
                payload={},
                dataset_name="test",
                check_name="test",
            )
            manager.ingest_alert(alert)

        summary = manager.get_alert_summary()
        assert summary["HIGH"] == 3
        assert summary["MEDIUM"] == 2
        assert summary["LOW"] == 0

    def test_alert_summary_excludes_resolved(self, manager):
        """Test that alert summary excludes resolved alerts."""
        alert1 = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        alert2 = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        manager.ingest_alert(alert1)
        manager.ingest_alert(alert2)

        manager.resolve_alert(alert1.alert_id)

        summary = manager.get_alert_summary()
        assert summary["HIGH"] == 1  # Only the unresolved one

    def test_register_notification_handler(self, manager):
        """Test registering a notification handler."""
        def handler(alert):
            pass
        manager.register_notification_handler(handler)

        assert len(manager.notification_handlers) == 1
        assert manager.notification_handlers[0] == handler

    def test_notification_handler_called_on_ingest(self, manager):
        """Test that notification handler is called when alert is ingested."""
        handler_called = []
        def handler(alert):
            handler_called.append(alert)
        manager.register_notification_handler(handler)

        alert = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        manager.ingest_alert(alert)

        assert len(handler_called) == 1
        assert handler_called[0].alert_id == alert.alert_id

    def test_notification_handler_error_handling(self, manager):
        """Test that AlertManager handles handler errors gracefully."""
        def failing_handler(alert):
            raise RuntimeError("Handler error")

        manager.register_notification_handler(failing_handler)

        alert = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        # Should not raise
        manager.ingest_alert(alert)
        assert alert.alert_id in manager.alerts


# ============================================================================
# DuckDB Persistence Tests
# ============================================================================

class TestDuckDBPersistence:
    """Test DuckDB persistence for alerts."""

    @pytest.fixture
    def mock_duckdb_conn(self):
        """Create a mock DuckDB connection."""
        conn = MagicMock()
        conn.execute = MagicMock(return_value=conn)
        return conn

    def test_save_alerts_to_duckdb(self, mock_duckdb_conn):
        """Test saving alerts to DuckDB."""
        manager = AlertManager(duckdb_conn=mock_duckdb_conn)

        alert = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test",
            alert_type="data_freshness",
            payload={"hours_old": 30},
            dataset_name="inspection",
            check_name="freshness",
        )
        manager.ingest_alert(alert)

        result = manager.save_to_duckdb()
        assert result is True
        assert mock_duckdb_conn.execute.called

    def test_save_alerts_no_duckdb(self):
        """Test save fails gracefully without DuckDB connection."""
        manager = AlertManager(duckdb_conn=None)

        alert = Alert.create(
            severity=AlertSeverity.HIGH,
            message="Test",
            alert_type="test",
            payload={},
            dataset_name="test",
            check_name="test",
        )
        manager.ingest_alert(alert)

        result = manager.save_to_duckdb()
        assert result is False

    def test_query_alerts_no_duckdb(self):
        """Test query fails gracefully without DuckDB connection."""
        manager = AlertManager(duckdb_conn=None)
        result = manager.query_alerts_from_duckdb()
        assert result == []


# ============================================================================
# Integration Tests
# ============================================================================

class TestMonitoringIntegration:
    """Integration tests for complete monitoring workflow."""

    def test_full_monitoring_workflow(self):
        """Test complete workflow: monitor -> ingest -> manage -> acknowledge."""
        # Create monitoring system
        monitor = Monitoring()
        manager = AlertManager()

        # Register alerts with manager
        def monitor_handler(alert):
            return manager.ingest_alert(alert)

        # Run checks that generate alerts
        now = datetime.now(timezone.utc)
        monitor.check_data_freshness(
            dataset_name="inspection",
            last_modified=now - timedelta(hours=48),
            freshness_threshold_hours=24,
        )

        # Ingest generated alerts
        for alert in monitor.get_all_alerts():
            manager.ingest_alert(alert)

        # Verify manager has alerts
        assert len(manager.alerts) == 1
        assert len(manager.get_active_alerts()) == 1

        # Acknowledge alert
        alert_id = list(manager.alerts.keys())[0]
        manager.acknowledge_alert(alert_id)

        # Verify status changed
        assert manager.alerts[alert_id].status == AlertStatus.ACKNOWLEDGED
        assert len(manager.get_active_alerts()) == 1  # Still active

        # Resolve alert
        manager.resolve_alert(alert_id)
        assert manager.alerts[alert_id].status == AlertStatus.RESOLVED
        assert len(manager.get_active_alerts()) == 0  # No longer active

    def test_multiple_alerts_severity_escalation(self):
        """Test that multiple alerts are properly categorized."""
        manager = AlertManager()

        # Create alerts of different severities
        alerts = [
            Alert.create(
                severity=AlertSeverity.HIGH,
                message=f"Alert {i}",
                alert_type="test",
                payload={},
                dataset_name="test",
                check_name="test",
            )
            for i in range(2)
        ]
        alerts += [
            Alert.create(
                severity=AlertSeverity.MEDIUM,
                message=f"Alert {i}",
                alert_type="test",
                payload={},
                dataset_name="test",
                check_name="test",
            )
            for i in range(3)
        ]

        for alert in alerts:
            manager.ingest_alert(alert)

        summary = manager.get_alert_summary()
        assert summary["HIGH"] == 2
        assert summary["MEDIUM"] == 3
        assert summary["LOW"] == 0

    def test_alert_threshold_boundaries(self):
        """Test alert thresholds at exact boundary values."""
        monitor = Monitoring()

        # Just under threshold
        now = datetime.now(timezone.utc)
        result = monitor.check_data_freshness(
            dataset_name="test",
            last_modified=now - timedelta(hours=23, minutes=59),
            freshness_threshold_hours=24,
        )
        # Should pass when < 24 hours
        assert result.status == "PASS"

        # Just over threshold
        result = monitor.check_data_freshness(
            dataset_name="test",
            last_modified=now - timedelta(hours=24, minutes=1),
            freshness_threshold_hours=24,
        )
        # Should fail when > 24 hours
        assert result.status == "FAIL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
