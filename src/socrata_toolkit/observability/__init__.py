"""Observability subsystem: metrics, logs, tracing, health, and SLA tracking.

Public entry point is :func:`get_observability_manager`, which returns a
process-wide :class:`ObservabilityManager` aggregating all sub-components.
"""

from __future__ import annotations

from .health import ComponentHealth, HealthMonitor
from .integration import (
    ObservabilityManager,
    get_observability_manager,
    reset_observability_manager,
)
from .logs import LogEntry, LogStore
from .metrics import HistogramData, MetricsCollector
from .sla import SLA, SLATracker
from .tracing import Span, Tracer

__all__ = [
    "ObservabilityManager",
    "get_observability_manager",
    "reset_observability_manager",
    "MetricsCollector",
    "HistogramData",
    "LogEntry",
    "LogStore",
    "Span",
    "Tracer",
    "HealthMonitor",
    "ComponentHealth",
    "SLA",
    "SLATracker",
]
