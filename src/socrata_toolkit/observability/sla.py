"""Service-level-agreement (SLA) tracking for the observability subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SLA:
    """An SLA definition with a target threshold and a current actual value.

    ``comparison`` controls the pass rule: "lte" means actual must be <= target
    (e.g. latency), "gte" means actual must be >= target (e.g. uptime %).
    """

    name: str
    target: float
    actual: float
    comparison: str = "lte"
    severity: str = "medium"

    @property
    def passing(self) -> bool:
        if self.comparison == "gte":
            return self.actual >= self.target
        return self.actual <= self.target

    def to_violation(self) -> dict[str, Any]:
        return {
            "sla_name": self.name,
            "target": self.target,
            "actual": self.actual,
            "severity": self.severity,
        }

class SLATracker:
    """Tracks a set of SLAs and produces a compliance report."""

    def __init__(self) -> None:
        self._slas: dict[str, SLA] = {}

    def register(self, sla: SLA) -> None:
        self._slas[sla.name] = sla

    def update(self, name: str, actual: float) -> None:
        if name in self._slas:
            self._slas[name].actual = actual

    def report(self) -> dict[str, Any]:
        slas = list(self._slas.values())
        total = len(slas)
        passing = [s for s in slas if s.passing]
        failing = [s for s in slas if not s.passing]
        compliance = (len(passing) / total * 100.0) if total else 100.0
        if compliance >= 99.0:
            trend = "healthy"
        elif compliance >= 90.0:
            trend = "watch"
        else:
            trend = "at_risk"
        return {
            "total_slas": total,
            "passing_slas": len(passing),
            "failing_slas": len(failing),
            "compliance_percent": compliance,
            "trend": trend,
            "violations": [s.to_violation() for s in failing],
        }
