"""SLA (Service Level Agreement) tracking and violation detection.

Provides:
- SLA definition and configuration
- Metric evaluation against SLA targets
- Automatic alerting on violations
- SLA compliance reporting

Usage:
    sla_tracker = SLATracker()
    sla_tracker.add_sla(
        'ingestion_latency_p99',
        target=5000,
        window='5m',
        severity='CRITICAL',
    )
    report = sla_tracker.evaluate()
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class Severity(Enum):
    """Alert severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class SLADefinition:
    """Definition of a Service Level Agreement.
    
    Attributes:
        metric_name: Name of the metric to track
        target: Target value (upper bound for latency, lower for success rate)
        window: Time window ('5m', '1h', '1d')
        severity: Alert severity on violation
        channels: Notification channels (email, slack, pagerduty)
        description: Human-readable description
    """
    metric_name: str
    target: float
    window: str
    severity: str = "MEDIUM"
    channels: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'target': self.target,
            'window': self.window,
            'severity': self.severity,
            'channels': self.channels,
            'description': self.description,
        }


@dataclass
class SLAViolation:
    """Record of an SLA violation.
    
    Attributes:
        sla_name: Name of the SLA
        metric_name: Metric that violated
        target: Target value
        actual: Actual value
        violation_time: When violation occurred
        window: Time window
        severity: Alert severity
    """
    sla_name: str
    metric_name: str
    target: float
    actual: float
    violation_time: str
    window: str
    severity: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'sla_name': self.sla_name,
            'metric_name': self.metric_name,
            'target': self.target,
            'actual': self.actual,
            'violation_time': self.violation_time,
            'window': self.window,
            'severity': self.severity,
        }


@dataclass
class SLAReport:
    """SLA compliance report.
    
    Attributes:
        report_time: When report was generated
        window: Time window covered
        total_slas: Total number of SLAs
        passing_slas: Number of passing SLAs
        failing_slas: Number of failing SLAs
        violations: List of violations
        compliance_percent: Overall compliance percentage
        trend: Trend indicator (improving, stable, degrading)
    """
    report_time: str
    window: str
    total_slas: int = 0
    passing_slas: int = 0
    failing_slas: int = 0
    violations: List[SLAViolation] = field(default_factory=list)
    compliance_percent: float = 100.0
    trend: str = "stable"

    @property
    def is_compliant(self) -> bool:
        """Check if report is fully compliant."""
        return self.compliance_percent == 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'report_time': self.report_time,
            'window': self.window,
            'total_slas': self.total_slas,
            'passing_slas': self.passing_slas,
            'failing_slas': self.failing_slas,
            'violations': [v.to_dict() for v in self.violations],
            'compliance_percent': self.compliance_percent,
            'is_compliant': self.is_compliant,
            'trend': self.trend,
        }


class SLATracker:
    """Tracks SLAs and detects violations.
    
    Example:
        tracker = SLATracker()
        tracker.add_sla('p99_latency', target=5000, window='5m')
        tracker.record_metric('p99_latency', 4500)
        report = tracker.evaluate()
    """

    def __init__(self):
        """Initialize SLA tracker."""
        self._slas: Dict[str, SLADefinition] = {}
        self._metrics: Dict[str, List[Tuple[float, float]]] = {}  # metric_name -> [(timestamp, value)]
        self._violations: List[SLAViolation] = []
        self._alert_callbacks: List[Callable[[SLAViolation], None]] = []
        self._lock = threading.RLock()
        self._compliance_history: List[Tuple[str, float]] = []  # (timestamp, compliance_percent)

    def add_sla(
        self,
        metric_name: str,
        target: float,
        window: str = "5m",
        severity: str = "MEDIUM",
        channels: Optional[List[str]] = None,
        description: str = "",
    ) -> None:
        """Add an SLA definition.
        
        Args:
            metric_name: Name of metric to track
            target: Target value
            window: Time window (5m, 1h, 1d)
            severity: Alert severity
            channels: Notification channels
            description: Description
        """
        sla = SLADefinition(
            metric_name=metric_name,
            target=target,
            window=window,
            severity=severity,
            channels=channels or [],
            description=description,
        )
        with self._lock:
            self._slas[metric_name] = sla
            if metric_name not in self._metrics:
                self._metrics[metric_name] = []

    def remove_sla(self, metric_name: str) -> None:
        """Remove an SLA definition."""
        with self._lock:
            self._slas.pop(metric_name, None)

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        timestamp = time.time()
        with self._lock:
            if metric_name not in self._metrics:
                self._metrics[metric_name] = []
            self._metrics[metric_name].append((timestamp, value))
            
            # Keep only recent values (last 24 hours)
            cutoff = timestamp - (24 * 3600)
            self._metrics[metric_name] = [
                (ts, v) for ts, v in self._metrics[metric_name]
                if ts > cutoff
            ]

    def register_alert_callback(self, callback: Callable[[SLAViolation], None]) -> None:
        """Register a function to call on SLA violations.
        
        Args:
            callback: Function that takes SLAViolation
        """
        with self._lock:
            self._alert_callbacks.append(callback)

    def _get_metrics_for_window(
        self,
        metric_name: str,
        window: str,
    ) -> List[float]:
        """Get metric values for a time window.
        
        Args:
            metric_name: Name of metric
            window: Time window (5m, 1h, 1d)
            
        Returns:
            List of metric values in window
        """
        now = time.time()
        
        # Parse window
        if window.endswith('m'):
            seconds = int(window[:-1]) * 60
        elif window.endswith('h'):
            seconds = int(window[:-1]) * 3600
        elif window.endswith('d'):
            seconds = int(window[:-1]) * 86400
        else:
            seconds = 300  # Default to 5 minutes
        
        cutoff = now - seconds
        values = []
        
        with self._lock:
            if metric_name in self._metrics:
                for ts, val in self._metrics[metric_name]:
                    if ts >= cutoff:
                        values.append(val)
        
        return values

    def _is_violated(
        self,
        metric_name: str,
        target: float,
        values: List[float],
    ) -> Optional[float]:
        """Check if an SLA is violated.
        
        For latency metrics (lower is better), violation = actual > target
        For success rate metrics (higher is better), violation = actual < target
        
        Args:
            metric_name: Name of metric
            target: Target value
            values: Recent metric values
            
        Returns:
            Actual value if violated, None if compliant
        """
        if not values:
            return None
        
        # Determine metric type by name
        if 'latency' in metric_name or 'duration' in metric_name or 'time' in metric_name:
            # Lower is better
            p99 = sorted(values)[int(len(values) * 0.99)]
            if p99 > target:
                return p99
        elif 'success' in metric_name or 'rate' in metric_name or 'compliance' in metric_name:
            # Higher is better
            avg = sum(values) / len(values)
            if avg < target:
                return avg
        else:
            # Default: assume lower is better
            p99 = sorted(values)[int(len(values) * 0.99)]
            if p99 > target:
                return p99
        
        return None

    def evaluate(self) -> SLAReport:
        """Evaluate all SLAs and return report.
        
        Returns:
            SLAReport with compliance status
        """
        with self._lock:
            report = SLAReport(
                report_time=datetime.now(timezone.utc).isoformat(),
                window="since_last_evaluation",
                total_slas=len(self._slas),
            )

            new_violations = []
            
            for metric_name, sla in self._slas.items():
                values = self._get_metrics_for_window(metric_name, sla.window)
                
                if not values:
                    # No data, assume passing
                    report.passing_slas += 1
                else:
                    actual = self._is_violated(metric_name, sla.target, values)
                    
                    if actual is not None:
                        # SLA violated
                        report.failing_slas += 1
                        violation = SLAViolation(
                            sla_name=metric_name,
                            metric_name=metric_name,
                            target=sla.target,
                            actual=actual,
                            violation_time=datetime.now(timezone.utc).isoformat(),
                            window=sla.window,
                            severity=sla.severity,
                        )
                        new_violations.append(violation)
                    else:
                        # SLA passing
                        report.passing_slas += 1

            # Record violations
            self._violations.extend(new_violations)
            report.violations = new_violations

            # Calculate compliance
            if report.total_slas > 0:
                report.compliance_percent = (
                    report.passing_slas / report.total_slas * 100
                )
            
            # Record compliance history
            self._compliance_history.append(
                (datetime.now(timezone.utc).isoformat(), report.compliance_percent)
            )
            
            # Determine trend
            if len(self._compliance_history) >= 3:
                recent = self._compliance_history[-3:]
                if recent[-1][1] > recent[0][1]:
                    report.trend = "improving"
                elif recent[-1][1] < recent[0][1]:
                    report.trend = "degrading"
                else:
                    report.trend = "stable"

            # Trigger alerts
            for violation in new_violations:
                for callback in self._alert_callbacks:
                    try:
                        callback(violation)
                    except Exception:
                        pass  # Fail silently to not break main flow

            return report

    def get_violations(self, severity: Optional[str] = None) -> List[SLAViolation]:
        """Get recent violations.
        
        Args:
            severity: Optional filter by severity
            
        Returns:
            List of violations
        """
        with self._lock:
            if severity:
                return [v for v in self._violations if v.severity == severity]
            return list(self._violations)

    def clear_violations(self) -> None:
        """Clear violation history."""
        with self._lock:
            self._violations.clear()

    def export_slas_yaml(self, filepath: Path) -> None:
        """Export SLA definitions to YAML file.
        
        Args:
            filepath: Output file path
        """
        import yaml
        
        with self._lock:
            data = {
                'slas': [sla.to_dict() for sla in self._slas.values()]
            }
        
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def import_slas_yaml(self, filepath: Path) -> None:
        """Import SLA definitions from YAML file.
        
        Args:
            filepath: YAML file path
        """
        import yaml
        
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        with self._lock:
            for sla_data in data.get('slas', []):
                self.add_sla(**sla_data)

    def summary_dict(self) -> Dict[str, Any]:
        """Get a summary of SLA status."""
        with self._lock:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'total_slas': len(self._slas),
                'total_violations': len(self._violations),
                'critical_violations': len([v for v in self._violations if v.severity == 'CRITICAL']),
                'slas': {name: sla.to_dict() for name, sla in self._slas.items()},
            }


# Global SLA tracker
_sla_tracker: Optional[SLATracker] = None


def get_sla_tracker() -> SLATracker:
    """Get or create global SLA tracker."""
    global _sla_tracker
    if _sla_tracker is None:
        _sla_tracker = SLATracker()
    return _sla_tracker
