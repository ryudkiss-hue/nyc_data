"""
Data Quality SLA Framework - SLA Definition and Monitoring

Manages data quality SLAs (Service Level Agreements), tracks metrics over time,
evaluates compliance, and detects trends. Integrates with observability module (W4)
for metrics emission and alerting.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of quality metrics tracked."""
    COMPLETENESS = "completeness"  # % non-null values
    VALIDITY = "validity"  # % values matching rules
    UNIQUENESS = "uniqueness"  # % unique values
    CONSISTENCY = "consistency"  # Cross-dataset consistency
    TIMELINESS = "timeliness"  # % data within acceptable age
    ACCURACY = "accuracy"  # % values matching reference data


class Severity(Enum):
    """Severity levels for SLA breaches."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TrendDirection(Enum):
    """Direction of trend over time."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


class MaterializationMode(Enum):
    """How SLA violations affect data materialization."""
    HARD = "hard"  # Block materialization on failure
    SOFT = "soft"  # Warn but continue


@dataclass
class MetricPoint:
    """A single measurement of a quality metric.
    
    Attributes:
        timestamp: When the measurement was taken
        value: The metric value (0-1 or 0-100)
        dataset: Which dataset this applies to
        metric_type: Type of metric
        window: Time window for aggregation
    """
    timestamp: datetime
    value: float
    dataset: str
    metric_type: MetricType
    window: str  # '5m', '1h', 'daily'

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "dataset": self.dataset,
            "metric_type": self.metric_type.value,
            "window": self.window,
        }


@dataclass
class SLADefinition:
    """Defines a data quality SLA.
    
    Attributes:
        metric_name: Name of the SLA (e.g., 'sidewalk_completeness')
        metric_type: Type of metric (completeness, validity, etc.)
        target: Target value (0-1, or 0-100 if percentage)
        window: Aggregation window ('5m', '1h', 'daily', 'weekly')
        severity: Severity if breached
        dataset: Dataset this applies to
        owner: Owner email for notifications
        materialization_mode: HARD (block) or SOFT (warn)
        grace_period: Minutes before alerting on breach
        created_at: When SLA was defined
    """
    metric_name: str
    metric_type: MetricType
    target: float
    window: str
    dataset: str
    severity: Severity
    owner: str
    materialization_mode: MaterializationMode = MaterializationMode.SOFT
    grace_period: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "target": self.target,
            "window": self.window,
            "dataset": self.dataset,
            "severity": self.severity.value,
            "owner": self.owner,
            "materialization_mode": self.materialization_mode.value,
            "grace_period": self.grace_period,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SLADefinition:
        """Create from dictionary."""
        return cls(
            metric_name=data["metric_name"],
            metric_type=MetricType(data["metric_type"]),
            target=data["target"],
            window=data["window"],
            dataset=data["dataset"],
            severity=Severity(data["severity"]),
            owner=data["owner"],
            materialization_mode=MaterializationMode(
                data.get("materialization_mode", "soft")
            ),
            grace_period=data.get("grace_period", 5),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
        )


@dataclass
class SLABreach:
    """Represents a breach of an SLA.
    
    Attributes:
        sla: The SLA that was breached
        timestamp: When the breach was detected
        actual_value: The actual measured value
        expected_value: The target value
        breach_duration: How long the breach lasted (if resolved)
        status: Current status (active, resolved)
    """
    sla: SLADefinition
    timestamp: datetime
    actual_value: float
    expected_value: float
    breach_duration: timedelta | None = None
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sla": self.sla.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "breach_duration": (
                str(self.breach_duration) if self.breach_duration else None
            ),
            "status": self.status,
        }


@dataclass
class SLATrend:
    """Trend analysis for an SLA metric.
    
    Attributes:
        sla_name: Name of the SLA
        direction: Improving, stable, or degrading
        current_value: Latest measured value
        previous_value: Previous measured value
        slope: Rate of change
        confidence: Confidence in trend (0-1)
    """
    sla_name: str
    direction: TrendDirection
    current_value: float
    previous_value: float | None
    slope: float
    confidence: float


class DataQualityTracker:
    """Tracks quality metrics over time and evaluates SLAs.
    
    Thread-safe metric collection with time-series storage and SLA evaluation.
    Detects trends, identifies breaches, and generates reports.
    """

    def __init__(self):
        """Initialize tracker."""
        self._lock = threading.Lock()
        self._metrics: list[MetricPoint] = []
        self._slas: dict[str, SLADefinition] = {}
        self._breaches: list[SLABreach] = []
        self._metric_history: dict[str, list[MetricPoint]] = defaultdict(list)

    def register_sla(self, sla: SLADefinition) -> None:
        """Register an SLA.
        
        Args:
            sla: SLA to register
        """
        with self._lock:
            self._slas[sla.metric_name] = sla
            logger.info(f"Registered SLA: {sla.metric_name} (target={sla.target})")

    def record_metric(
        self,
        metric_name: str,
        value: float,
        dataset: str,
        metric_type: MetricType,
        window: str = "5m",
    ) -> None:
        """Record a metric measurement.
        
        Args:
            metric_name: Name of the metric
            value: Measured value (0-1)
            dataset: Dataset name
            metric_type: Type of metric
            window: Time window
        """
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            dataset=dataset,
            metric_type=metric_type,
            window=window,
        )

        with self._lock:
            self._metrics.append(point)
            self._metric_history[metric_name].append(point)

            # Check if this triggers an SLA breach
            if metric_name in self._slas:
                sla = self._slas[metric_name]
                if value < sla.target:
                    self._record_breach(sla, value)

        logger.debug(f"Recorded metric {metric_name}={value}")

    def _record_breach(self, sla: SLADefinition, actual_value: float) -> None:
        """Record an SLA breach (must be called within lock).
        
        Args:
            sla: The SLA that was breached
            actual_value: The measured value
        """
        # Check if we already have an active breach
        active_breach = next(
            (b for b in self._breaches if b.sla.metric_name == sla.metric_name and b.status == "active"),
            None,
        )

        if not active_breach:
            breach = SLABreach(
                sla=sla,
                timestamp=datetime.now(timezone.utc),
                actual_value=actual_value,
                expected_value=sla.target,
                status="active",
            )
            self._breaches.append(breach)
            logger.warning(
                f"SLA breach: {sla.metric_name} = {actual_value} (target={sla.target})"
            )

    def evaluate_sla(self, sla_name: str, lookback_minutes: int = 60) -> tuple[bool, float]:
        """Evaluate if an SLA is currently being met.
        
        Args:
            sla_name: Name of the SLA
            lookback_minutes: How far back to look for metrics
            
        Returns:
            Tuple of (is_compliant, actual_value)
        """
        if sla_name not in self._slas:
            logger.warning(f"SLA {sla_name} not found")
            return True, 1.0

        sla = self._slas[sla_name]

        # Get recent metric points
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        recent_points = [
            p for p in self._metric_history[sla_name]
            if p.timestamp >= cutoff_time
        ]

        if not recent_points:
            logger.debug(f"No recent metrics for {sla_name}")
            return True, 1.0

        # Calculate average value for the window
        avg_value = sum(p.value for p in recent_points) / len(recent_points)
        is_compliant = avg_value >= sla.target

        logger.debug(f"SLA {sla_name}: {avg_value:.4f} vs {sla.target} = {'PASS' if is_compliant else 'FAIL'}")
        return is_compliant, avg_value

    def get_trend(
        self, sla_name: str, lookback_minutes: int = 1440
    ) -> SLATrend:
        """Analyze the trend for an SLA metric.
        
        Args:
            sla_name: Name of the SLA
            lookback_minutes: How far back to analyze
            
        Returns:
            SLATrend with direction and analysis
        """
        if sla_name not in self._metric_history:
            return SLATrend(
                sla_name=sla_name,
                direction=TrendDirection.INSUFFICIENT_DATA,
                current_value=0.0,
                previous_value=None,
                slope=0.0,
                confidence=0.0,
            )

        # Get recent points
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        points = [
            p for p in self._metric_history[sla_name]
            if p.timestamp >= cutoff_time
        ]

        if len(points) < 2:
            return SLATrend(
                sla_name=sla_name,
                direction=TrendDirection.INSUFFICIENT_DATA,
                current_value=points[0].value if points else 0.0,
                previous_value=None,
                slope=0.0,
                confidence=0.0,
            )

        # Sort by timestamp
        points = sorted(points, key=lambda p: p.timestamp)

        # Calculate slope using simple linear regression
        n = len(points)
        sum_x = sum(i for i in range(n))
        sum_y = sum(p.value for p in points)
        sum_xy = sum(i * p.value for i, p in enumerate(points))
        sum_x2 = sum(i * i for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0

        # Determine direction
        current = points[-1].value
        previous = points[-2].value if len(points) > 1 else points[0].value

        if slope > 0.01:
            direction = TrendDirection.IMPROVING
        elif slope < -0.01:
            direction = TrendDirection.DEGRADING
        else:
            direction = TrendDirection.STABLE

        # Calculate confidence (how consistent the trend is)
        values = [p.value for p in points]
        mean_value = sum_y / n
        variance = sum((v - mean_value) ** 2 for v in values) / n
        std_dev = variance ** 0.5
        confidence = max(0, 1 - (std_dev / (mean_value + 1e-6)))

        return SLATrend(
            sla_name=sla_name,
            direction=direction,
            current_value=current,
            previous_value=previous,
            slope=slope,
            confidence=confidence,
        )

    def get_breach_summary(self) -> dict[str, Any]:
        """Get summary of all SLA breaches.
        
        Returns:
            Dictionary with breach statistics
        """
        with self._lock:
            active_breaches = [b for b in self._breaches if b.status == "active"]
            critical_breaches = [
                b for b in active_breaches if b.sla.severity == Severity.CRITICAL
            ]

            return {
                "total_breaches": len(self._breaches),
                "active_breaches": len(active_breaches),
                "critical_breaches": len(critical_breaches),
                "breaches_by_severity": {
                    "critical": len([b for b in active_breaches if b.sla.severity == Severity.CRITICAL]),
                    "high": len([b for b in active_breaches if b.sla.severity == Severity.HIGH]),
                    "medium": len([b for b in active_breaches if b.sla.severity == Severity.MEDIUM]),
                    "low": len([b for b in active_breaches if b.sla.severity == Severity.LOW]),
                },
            }

    def get_sla_compliance_report(self, lookback_minutes: int = 1440) -> dict[str, Any]:
        """Generate SLA compliance report.
        
        Args:
            lookback_minutes: How far back to evaluate
            
        Returns:
            Dictionary with compliance metrics
        """
        report = {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "lookback_minutes": lookback_minutes,
            "sla_results": [],
            "overall_compliance": 0.0,
        }

        compliant_count = 0
        for sla_name, sla in self._slas.items():
            is_compliant, actual_value = self.evaluate_sla(sla_name, lookback_minutes)
            if is_compliant:
                compliant_count += 1

            report["sla_results"].append({
                "metric_name": sla_name,
                "target": sla.target,
                "actual": actual_value,
                "compliant": is_compliant,
                "severity": sla.severity.value,
                "window": sla.window,
            })

        if len(self._slas) > 0:
            report["overall_compliance"] = compliant_count / len(self._slas)

        return report

    def resolve_breach(self, sla_name: str) -> bool:
        """Mark an active breach as resolved.
        
        Args:
            sla_name: Name of the SLA
            
        Returns:
            True if breach was found and resolved
        """
        with self._lock:
            for breach in self._breaches:
                if breach.sla.metric_name == sla_name and breach.status == "active":
                    breach.status = "resolved"
                    breach.breach_duration = datetime.now(timezone.utc) - breach.timestamp
                    logger.info(f"Resolved breach for {sla_name}")
                    return True
        return False

    def clear_old_metrics(self, older_than_days: int = 30) -> int:
        """Remove old metric points (for storage management).
        
        Args:
            older_than_days: Remove metrics older than this many days
            
        Returns:
            Number of metrics removed
        """
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            removed_count = 0

            for key in self._metric_history:
                initial_count = len(self._metric_history[key])
                self._metric_history[key] = [
                    p for p in self._metric_history[key] if p.timestamp >= cutoff_time
                ]
                removed_count += initial_count - len(self._metric_history[key])

            self._metrics = [m for m in self._metrics if m.timestamp >= cutoff_time]
            removed_count += len([m for m in self._metrics if m.timestamp < cutoff_time])

        logger.info(f"Cleared {removed_count} old metric points")
        return removed_count


def create_standard_slas() -> list[SLADefinition]:
    """Create standard pre-built SLAs for common datasets.
    
    Returns:
        List of SLADefinitions
    """
    slas = [
        # Completeness SLAs
        SLADefinition(
            metric_name="sidewalk_inspections_completeness",
            metric_type=MetricType.COMPLETENESS,
            target=0.98,
            window="daily",
            dataset="sidewalk_inspections",
            severity=Severity.HIGH,
            owner="data-engineering@example.com",
        ),
        SLADefinition(
            metric_name="311_complaints_completeness",
            metric_type=MetricType.COMPLETENESS,
            target=0.99,
            window="daily",
            dataset="311_complaints",
            severity=Severity.HIGH,
            owner="data-engineering@example.com",
        ),
        # Validity SLAs
        SLADefinition(
            metric_name="sidewalk_inspections_validity",
            metric_type=MetricType.VALIDITY,
            target=0.95,
            window="daily",
            dataset="sidewalk_inspections",
            severity=Severity.HIGH,
            owner="data-engineering@example.com",
        ),
        # Timeliness SLAs
        SLADefinition(
            metric_name="sidewalk_inspections_timeliness",
            metric_type=MetricType.TIMELINESS,
            target=0.90,
            window="hourly",
            dataset="sidewalk_inspections",
            severity=Severity.MEDIUM,
            owner="data-engineering@example.com",
        ),
    ]

    return slas
