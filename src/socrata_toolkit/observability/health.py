"""Health and readiness checks for the observability subsystem."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ComponentHealth:
    """Health result for a single named component."""

    name: str
    status: str = "HEALTHY"  # HEALTHY | DEGRADED | UNHEALTHY
    message: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }

class HealthMonitor:
    """Registry of component health checks.

    A check is a callable returning ``(status, message)`` or a bare bool.
    """

    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], Any]] = {}

    def register(self, name: str, check: Callable[[], Any]) -> None:
        self._checks[name] = check

    def _run_check(self, name: str, check: Callable[[], Any]) -> ComponentHealth:
        start = time.time()
        try:
            result = check()
            if isinstance(result, tuple):
                status, message = result
            elif isinstance(result, bool):
                status, message = ("HEALTHY" if result else "UNHEALTHY"), None
            else:
                status, message = "HEALTHY", str(result) if result is not None else None
        except Exception as exc:  # a failing check is unhealthy, never fatal
            status, message = "UNHEALTHY", str(exc)
        duration_ms = (time.time() - start) * 1000.0
        return ComponentHealth(name=name, status=status, message=message, duration_ms=duration_ms)

    def check_all(self) -> list[ComponentHealth]:
        return [self._run_check(name, chk) for name, chk in self._checks.items()]

    def health_status(self) -> dict[str, Any]:
        components = self.check_all()
        unhealthy = [c for c in components if c.status == "UNHEALTHY"]
        degraded = [c for c in components if c.status == "DEGRADED"]
        if unhealthy:
            overall = "UNHEALTHY"
        elif degraded:
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"
        return {
            "status": overall,
            "is_ready": not unhealthy,
            "unhealthy_count": len(unhealthy),
            "degraded_count": len(degraded),
            "components": [c.to_dict() for c in components],
        }

    def readiness_status(self) -> dict[str, Any]:
        status = self.health_status()
        return {"ready": status["is_ready"], "components": status["components"]}
