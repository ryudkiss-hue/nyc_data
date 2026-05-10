"""Health checks and readiness probes for production systems.

Provides comprehensive health checking for:
- Database connectivity
- External API availability
- File system access
- Service dependencies

Usage:
    checker = HealthChecker()
    health = checker.check_health()
    if health.status == 'HEALTHY':
        # Accept traffic
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class HealthStatus(Enum):
    """Overall health status."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass
class ComponentHealth:
    """Health status of a single component.
    
    Attributes:
        name: Component name
        status: HEALTHY, DEGRADED, or UNHEALTHY
        message: Status message
        checked_at: When the check was performed
        duration_ms: How long the check took
        details: Additional details dictionary
    """
    name: str
    status: str
    message: str = ""
    checked_at: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == "HEALTHY"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'status': self.status,
            'message': self.message,
            'checked_at': self.checked_at,
            'duration_ms': self.duration_ms,
            'details': self.details,
        }


@dataclass
class HealthReport:
    """Overall health report.
    
    Attributes:
        status: Overall status
        timestamp: When report was generated
        components: Individual component statuses
        unhealthy_components: List of unhealthy components
        degraded_components: List of degraded components
    """
    status: str
    timestamp: str
    components: List[ComponentHealth] = field(default_factory=list)

    @property
    def unhealthy_components(self) -> List[ComponentHealth]:
        """Get unhealthy components."""
        return [c for c in self.components if c.status == "UNHEALTHY"]

    @property
    def degraded_components(self) -> List[ComponentHealth]:
        """Get degraded components."""
        return [c for c in self.components if c.status == "DEGRADED"]

    def is_healthy(self) -> bool:
        """Check if overall health is healthy."""
        return self.status == "HEALTHY"

    def is_ready(self) -> bool:
        """Check readiness (healthy + no unhealthy components)."""
        return self.status in ("HEALTHY", "DEGRADED") and not self.unhealthy_components

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'status': self.status,
            'timestamp': self.timestamp,
            'is_ready': self.is_ready(),
            'unhealthy_count': len(self.unhealthy_components),
            'degraded_count': len(self.degraded_components),
            'components': [c.to_dict() for c in self.components],
        }


class HealthChecker:
    """Performs health checks on system components.
    
    Provides readiness probes, liveness probes, and detailed
    component health information.
    
    Example:
        checker = HealthChecker()
        checker.register_check('database', check_postgres_connectivity)
        health = checker.check_health()
    """

    def __init__(self):
        """Initialize health checker."""
        self._checks: Dict[str, Callable[[], ComponentHealth]] = {}
        self._results: Dict[str, ComponentHealth] = {}
        self._lock = threading.RLock()
        self._last_check_time: Optional[datetime] = None

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], ComponentHealth],
    ) -> None:
        """Register a health check function.
        
        Args:
            name: Check name
            check_fn: Function that returns ComponentHealth
        """
        with self._lock:
            self._checks[name] = check_fn

    def _check_database(self) -> ComponentHealth:
        """Check PostgreSQL database connectivity."""
        start = time.time()
        try:
            import psycopg
            from socrata_toolkit.db_helpers import get_connection
            
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="database",
                status="HEALTHY",
                message="PostgreSQL connection successful",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="database",
                status="UNHEALTHY",
                message=f"Database check failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'error': str(e)},
            )

    def _check_filesystem(self, path: str = '.') -> ComponentHealth:
        """Check file system writability."""
        start = time.time()
        try:
            test_file = Path(path) / '.health_check'
            test_file.write_text('ok')
            test_file.unlink()
            
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="filesystem",
                status="HEALTHY",
                message=f"File system writable at {path}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="filesystem",
                status="UNHEALTHY",
                message=f"File system check failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'error': str(e)},
            )

    def _check_disk_space(self, path: str = '.', min_gb: float = 1.0) -> ComponentHealth:
        """Check available disk space."""
        start = time.time()
        try:
            import shutil
            stats = shutil.disk_usage(path)
            available_gb = stats.free / (1024 ** 3)
            
            status = "HEALTHY" if available_gb >= min_gb else "DEGRADED"
            message = f"Available disk: {available_gb:.2f} GB"
            
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="disk_space",
                status=status,
                message=message,
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'available_gb': available_gb, 'min_gb': min_gb},
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="disk_space",
                status="DEGRADED",
                message=f"Disk space check failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'error': str(e)},
            )

    def _check_memory(self, min_percent: float = 10.0) -> ComponentHealth:
        """Check available memory."""
        start = time.time()
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_percent = memory.available / memory.total * 100
            
            status = "HEALTHY" if available_percent >= min_percent else "DEGRADED"
            message = f"Available memory: {available_percent:.1f}%"
            
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={
                    'available_percent': available_percent,
                    'total_mb': memory.total / (1024 ** 2),
                    'used_mb': memory.used / (1024 ** 2),
                },
            )
        except ImportError:
            return ComponentHealth(
                name="memory",
                status="DEGRADED",
                message="psutil not available",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="memory",
                status="DEGRADED",
                message=f"Memory check failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'error': str(e)},
            )

    def _check_cpu(self, max_percent: float = 80.0) -> ComponentHealth:
        """Check CPU usage."""
        start = time.time()
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            status = "HEALTHY" if cpu_percent <= max_percent else "DEGRADED"
            message = f"CPU usage: {cpu_percent:.1f}%"
            
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="cpu",
                status=status,
                message=message,
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'cpu_percent': cpu_percent},
            )
        except ImportError:
            return ComponentHealth(
                name="cpu",
                status="DEGRADED",
                message="psutil not available",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="cpu",
                status="DEGRADED",
                message=f"CPU check failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'error': str(e)},
            )

    def _check_schema_registry(self) -> ComponentHealth:
        """Check schema registry availability."""
        start = time.time()
        try:
            from socrata_toolkit.schema_registry import SchemaRegistry
            registry = SchemaRegistry()
            # Quick sanity check
            _ = registry.get_registry()
            
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="schema_registry",
                status="HEALTHY",
                message="Schema registry accessible",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="schema_registry",
                status="DEGRADED",
                message=f"Schema registry check failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'error': str(e)},
            )

    def _check_lineage_system(self) -> ComponentHealth:
        """Check lineage tracking system."""
        start = time.time()
        try:
            from socrata_toolkit.lineage_tracking import LineageTracker
            tracker = LineageTracker()
            # Quick sanity check
            _ = tracker
            
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="lineage_system",
                status="HEALTHY",
                message="Lineage system initialized",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ComponentHealth(
                name="lineage_system",
                status="DEGRADED",
                message=f"Lineage system check failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration,
                details={'error': str(e)},
            )

    def check_health(self, timeout_seconds: float = 10.0) -> HealthReport:
        """Perform all health checks.
        
        Args:
            timeout_seconds: Maximum time to spend on checks
            
        Returns:
            HealthReport with all component statuses
        """
        start_time = time.time()
        components = []

        with self._lock:
            # Run registered checks
            for name, check_fn in self._checks.items():
                try:
                    component = check_fn()
                    components.append(component)
                    self._results[name] = component
                except Exception as e:
                    component = ComponentHealth(
                        name=name,
                        status="UNHEALTHY",
                        message=f"Check error: {str(e)}",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                        details={'error': str(e)},
                    )
                    components.append(component)
                    self._results[name] = component

                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    break

        self._last_check_time = datetime.now(timezone.utc)

        # Determine overall status
        unhealthy = [c for c in components if c.status == "UNHEALTHY"]
        degraded = [c for c in components if c.status == "DEGRADED"]

        if unhealthy:
            overall_status = "UNHEALTHY"
        elif degraded:
            overall_status = "DEGRADED"
        else:
            overall_status = "HEALTHY"

        return HealthReport(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=components,
        )

    def get_readiness_probe(self) -> Dict[str, Any]:
        """Get readiness probe response.
        
        Returns readiness (can accept traffic) status.
        Ready = HEALTHY or DEGRADED with no UNHEALTHY components.
        """
        report = self.check_health()
        return {
            'ready': report.is_ready(),
            'status': report.status,
            'timestamp': report.timestamp,
        }

    def get_liveness_probe(self) -> Dict[str, Any]:
        """Get liveness probe response.
        
        Returns whether process is still running.
        Always returns true if we can respond to the request.
        """
        return {
            'alive': True,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }


# Global health checker
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        # Register default checks
        _health_checker.register_check('database', _health_checker._check_database)
        _health_checker.register_check('filesystem', _health_checker._check_filesystem)
        _health_checker.register_check('disk_space', _health_checker._check_disk_space)
        _health_checker.register_check('memory', _health_checker._check_memory)
        _health_checker.register_check('cpu', _health_checker._check_cpu)
        _health_checker.register_check('schema_registry', _health_checker._check_schema_registry)
        _health_checker.register_check('lineage_system', _health_checker._check_lineage_system)
    return _health_checker
