"""ObservabilityManager — unified facade over metrics, logs, traces, health, SLA.

Exposes the interface consumed by the ``socrata observability`` CLI commands and
provides a process-wide singleton via ``get_observability_manager()``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .health import HealthMonitor
from .logs import LogStore
from .metrics import MetricsCollector
from .sla import SLATracker
from .tracing import Span, Tracer


class ObservabilityManager:
    """Aggregates the observability sub-components behind one object."""

    def __init__(self) -> None:
        self._metrics = MetricsCollector()
        self._logs = LogStore()
        self._tracer = Tracer()
        self._health = HealthMonitor()
        self._sla = SLATracker()
        # A process is "ready" by default; callers register real checks.
        self._health.register("core", lambda: ("HEALTHY", "core subsystem online"))

    # -- sub-component accessors ----------------------------------------
    def get_metrics(self) -> MetricsCollector:
        return self._metrics

    def get_logs(self) -> LogStore:
        return self._logs

    def get_tracer(self) -> Tracer:
        return self._tracer

    def get_health(self) -> HealthMonitor:
        return self._health

    def get_sla(self) -> SLATracker:
        return self._sla

    # -- health / readiness ---------------------------------------------
    def health_status(self) -> dict[str, Any]:
        return self._health.health_status()

    def readiness_status(self) -> dict[str, Any]:
        return self._health.readiness_status()

    # -- metrics --------------------------------------------------------
    def metrics_summary(self) -> dict[str, Any]:
        return self._metrics.summary_dict()

    def export_metrics_prometheus(self) -> str:
        return self._metrics.export_prometheus()

    def export_metrics_json(self) -> str:
        return self._metrics.export_json()

    # -- logs -----------------------------------------------------------
    def query_logs(self, **filters: Any) -> list:
        return self._logs.query(**filters)

    def export_logs_json(self, path: str | Path) -> None:
        self._logs.export_json(path)

    def export_logs_csv(self, path: str | Path) -> None:
        self._logs.export_csv(path)

    # -- traces ---------------------------------------------------------
    def get_trace(self, trace_id: str) -> list[Span] | None:
        return self._tracer.get_trace(trace_id)

    def export_traces_jaeger(self) -> str:
        return self._tracer.export_jaeger()

    # -- SLA ------------------------------------------------------------
    def sla_report(self) -> dict[str, Any]:
        return self._sla.report()


_MANAGER: ObservabilityManager | None = None


def get_observability_manager() -> ObservabilityManager:
    """Return the process-wide ObservabilityManager singleton."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ObservabilityManager()
    return _MANAGER


def reset_observability_manager() -> None:
    """Reset the singleton (primarily for tests)."""
    global _MANAGER
    _MANAGER = None
