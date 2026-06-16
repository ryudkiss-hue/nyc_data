"""Tests for the Operational Monitoring System.

Tests cover:
- Alert creation and dataclass functionality
- AlertManager lifecycle (ingest, batch mode, shutdown)
- Notifiers (CLI, Email)
- HealthMonitor and Monitoring system
"""

from __future__ import annotations
import pytest


import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

from socrata_toolkit.observability.monitoring import (
    HealthCheck,
    HealthMonitor,
    Monitoring,
    MonitoringResult,
)
from socrata_toolkit.alerts.manager import (
    Alert,
    AlertManager,
    AlertSeverity,
    AlertStatus,
    CLINotifier,
    EmailNotifier,
)

# ============================================================================
# Alert & AlertManager Tests
# ============================================================================

class TestAlert:
    """Test Alert dataclass functionality."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert.create(
            severity=AlertSeverity.CRITICAL,
            message="Test alert",
            alert_type="test",
            payload={"test": "value"}
        )
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.message == "Test alert"
        assert alert.payload == {"test": "value"}
        assert alert.created_at > 0

class DummySubscriber:
    def __init__(self):
        self.alerts = []
    def notify(self, alert: Alert) -> None:
        self.alerts.append(alert)

class TestAlertManager:
    """Test AlertManager lifecycle and state management."""

    def test_manager_registration(self):
        manager = AlertManager(batch_mode=False)
        sub1 = DummySubscriber()
        manager.register(sub1)
        assert len(manager.subscribers) == 1
        manager.unregister(sub1)
        assert len(manager.subscribers) == 0

    def test_manager_emit_sync(self):
        manager = AlertManager(batch_mode=False)
        sub = DummySubscriber()
        manager.register(sub)
        alert = Alert.create(severity=AlertSeverity.WARNING, message="sync msg", alert_type="sync", payload={})
        manager.emit(alert)
        assert len(sub.alerts) == 1
        assert sub.alerts[0].message == "sync msg"

    def test_manager_emit_batch(self):
        manager = AlertManager(batch_mode=True, batch_interval=0.1)
        sub = DummySubscriber()
        manager.register(sub)
        alert = Alert.create(severity=AlertSeverity.CRITICAL, message="batch msg", alert_type="batch", payload={})
        manager.emit(alert)
        assert len(sub.alerts) == 0  # not emitted yet
        time.sleep(0.2)  # wait for thread
        assert len(sub.alerts) == 1
        assert sub.alerts[0].message == "batch msg"
        manager.shutdown()

    def test_manager_shutdown(self):
        manager = AlertManager(batch_mode=True, batch_interval=10.0)
        sub = DummySubscriber()
        manager.register(sub)
        alert = Alert.create(severity=AlertSeverity.WARNING, message="shutdown msg", alert_type="shutdown", payload={})
        manager.emit(alert)
        manager.shutdown()
        # Should flush on shutdown
        assert len(sub.alerts) == 1

class TestNotifiers:
    def test_cli_notifier(self, capsys):
        notifier = CLINotifier(show_payload=True)
        alert = Alert.create(severity=AlertSeverity.WARNING, message="cli msg", alert_type="cli", payload={"x": 1})
        notifier.notify(alert)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "cli msg" in captured.out
        assert "x" in captured.out

    @patch("smtplib.SMTP")
    def test_email_notifier(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        config = {
            "from_addr": "test@example.com",
            "recipients": ["user@example.com"],
            "host": "localhost",
            "port": 25,
            "username": "user",
            "password": "pwd"
        }
        notifier = EmailNotifier(config)
        alert = Alert.create(severity=AlertSeverity.CRITICAL, message="email msg", alert_type="email", payload={"x": 1})
        notifier.notify(alert)
        
        mock_smtp.assert_called_once_with("localhost", 25)
        mock_server.starttls.assert_called_once()
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

# ============================================================================
# Monitoring Tests
# ============================================================================

class TestMonitoring:
    def test_health_monitor(self):
        hm = HealthMonitor()
        assert hm.get_status("db") is None
        hm.record_check("db", "OK", latency_ms=10.0)
        assert hm.get_status("db") == "OK"
        hm.record_check("db", "FAIL", latency_ms=15.0)
        assert hm.get_status("db") == "FAIL"

    def test_monitoring_facade(self):
        m = Monitoring()
        m.health_monitor.record_check("api", "OK")
        assert m.check_service("api") == "OK"
        assert m.check_service("unknown") is None
