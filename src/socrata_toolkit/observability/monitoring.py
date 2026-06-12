"""Monitoring module for observability subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..alerts.manager import Alert, AlertManager, AlertSeverity, AlertStatus


@dataclass
class HealthCheck:
    """Health check result."""

    service: str
    status: str
    timestamp: datetime
    latency_ms: float | None = None


@dataclass
class MonitoringResult:
    """Result of monitoring operation."""

    success: bool
    message: str
    timestamp: datetime


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


class Monitoring:
    """Main monitoring interface."""

    def __init__(self):
        self.health_monitor = HealthMonitor()

    def check_service(self, service: str) -> str | None:
        return self.health_monitor.get_status(service)


__all__ = ["HealthCheck", "HealthMonitor", "MonitoringResult", "Monitoring"]
