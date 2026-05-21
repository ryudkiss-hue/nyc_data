"""
Anomaly Detection - Statistical Anomaly Detection and Drift Detection

Detects statistical anomalies in quality metrics using Z-score, moving averages,
and seasonal decomposition. Identifies data drift and schema changes.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class AnomalySeverity(Enum):
    """Severity of detected anomaly."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Anomaly:
    """Represents a detected anomaly.
    
    Attributes:
        timestamp: When anomaly was detected
        metric_name: Which metric showed anomaly
        anomaly_type: Type of anomaly (z_score, drift, seasonal_violation)
        value: The anomalous value
        expected_range: Expected min/max range
        severity: Severity of the anomaly
        z_score: Z-score if applicable
        explanation: Human-readable description
    """
    timestamp: datetime
    metric_name: str
    anomaly_type: str
    value: float
    expected_range: Tuple[float, float]
    severity: AnomalySeverity
    z_score: Optional[float] = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "anomaly_type": self.anomaly_type,
            "value": self.value,
            "expected_range": self.expected_range,
            "severity": self.severity.value,
            "z_score": self.z_score,
            "explanation": self.explanation,
        }


@dataclass
class AnomalyReport:
    """Report of detected anomalies.
    
    Attributes:
        detected_at: When report was generated
        anomalies: List of detected anomalies
        affected_metrics: Which metrics had anomalies
        severity_level: Overall severity
        suggested_actions: Recommended actions
    """
    detected_at: datetime
    anomalies: List[Anomaly] = field(default_factory=list)
    affected_metrics: List[str] = field(default_factory=list)
    severity_level: AnomalySeverity = AnomalySeverity.INFO
    suggested_actions: List[str] = field(default_factory=list)

    @property
    def has_critical_anomalies(self) -> bool:
        """Whether there are critical anomalies."""
        return any(a.severity == AnomalySeverity.CRITICAL for a in self.anomalies)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "detected_at": self.detected_at.isoformat(),
            "anomaly_count": len(self.anomalies),
            "severity_level": self.severity_level.value,
            "affected_metrics": self.affected_metrics,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "suggested_actions": self.suggested_actions,
        }


class AnomalyDetector:
    """Detects statistical anomalies in quality metrics.
    
    Uses Z-score, moving averages, and deviation from trend to identify
    unexpected changes in data quality metrics.
    """

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        min_history: int = 5,
    ):
        """Initialize detector.
        
        Args:
            z_score_threshold: Z-score threshold for anomaly (default 3.0 = 99.7%)
            min_history: Minimum points needed for analysis
        """
        self.z_score_threshold = z_score_threshold
        self.min_history = min_history

    def detect_outliers(
        self,
        metric_name: str,
        metric_history: List[Tuple[datetime, float]],
    ) -> AnomalyReport:
        """Detect outliers in metric history using Z-score.
        
        Args:
            metric_name: Name of the metric
            metric_history: List of (timestamp, value) tuples
            
        Returns:
            AnomalyReport with detected outliers
        """
        report = AnomalyReport(detected_at=datetime.now(timezone.utc))

        if len(metric_history) < self.min_history:
            logger.debug(f"Insufficient history for {metric_name}")
            return report

        # Extract values
        values = [v for _, v in metric_history]
        timestamps = [t for t, _ in metric_history]

        # Calculate statistics
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return report  # No variation

        # Detect outliers
        latest_value = values[-1]
        z_score = (latest_value - mean) / std_dev

        if abs(z_score) > self.z_score_threshold:
            severity = AnomalySeverity.HIGH if abs(z_score) > 4 else AnomalySeverity.MEDIUM

            anomaly = Anomaly(
                timestamp=timestamps[-1],
                metric_name=metric_name,
                anomaly_type="z_score",
                value=latest_value,
                expected_range=(mean - 3 * std_dev, mean + 3 * std_dev),
                severity=severity,
                z_score=z_score,
                explanation=f"Value {latest_value:.4f} is {abs(z_score):.2f} standard deviations from mean {mean:.4f}",
            )
            report.anomalies.append(anomaly)
            report.affected_metrics.append(metric_name)

            logger.warning(f"Anomaly detected in {metric_name}: z_score={z_score:.2f}")

        # Update overall severity
        if report.anomalies:
            report.severity_level = max(
                a.severity for a in report.anomalies
            )

        return report

    def detect_drift(
        self,
        metric_name: str,
        metric_history: List[Tuple[datetime, float]],
        window_size: int = 5,
        threshold: float = 0.1,
    ) -> AnomalyReport:
        """Detect drift from moving average (trend change).
        
        Args:
            metric_name: Name of the metric
            metric_history: List of (timestamp, value) tuples
            window_size: Size of moving average window
            threshold: Threshold for deviation (0-1)
            
        Returns:
            AnomalyReport with drift detection
        """
        report = AnomalyReport(detected_at=datetime.now(timezone.utc))

        if len(metric_history) < window_size * 2:
            return report

        values = [v for _, v in metric_history]
        timestamps = [t for t, _ in metric_history]

        # Calculate moving averages
        ma_old = sum(values[-(window_size*2):-window_size]) / window_size
        ma_new = sum(values[-window_size:]) / window_size

        # Calculate deviation
        deviation = abs(ma_new - ma_old) / (ma_old + 1e-6)

        if deviation > threshold:
            direction = "increasing" if ma_new > ma_old else "decreasing"
            severity = AnomalySeverity.HIGH if deviation > 0.2 else AnomalySeverity.MEDIUM

            anomaly = Anomaly(
                timestamp=timestamps[-1],
                metric_name=metric_name,
                anomaly_type="drift",
                value=ma_new,
                expected_range=(ma_old * 0.9, ma_old * 1.1),
                severity=severity,
                explanation=f"Drift detected: moving average {direction} from {ma_old:.4f} to {ma_new:.4f} ({deviation*100:.1f}%)",
            )
            report.anomalies.append(anomaly)
            report.affected_metrics.append(metric_name)
            report.suggested_actions.append(
                f"Investigate why {metric_name} is {direction}"
            )

            logger.warning(f"Drift detected in {metric_name}: {direction}")

        return report

    def detect_schema_changes(
        self,
        schema_old: Dict[str, Any],
        schema_new: Dict[str, Any],
    ) -> AnomalyReport:
        """Detect structural schema changes.
        
        Args:
            schema_old: Previous schema
            schema_new: Current schema
            
        Returns:
            AnomalyReport with schema changes
        """
        report = AnomalyReport(detected_at=datetime.now(timezone.utc))

        # Check for added/removed columns
        cols_old = set(schema_old.keys())
        cols_new = set(schema_new.keys())

        removed = cols_old - cols_new
        added = cols_new - cols_old

        if removed:
            for col in removed:
                anomaly = Anomaly(
                    timestamp=datetime.now(timezone.utc),
                    metric_name=f"schema:{col}",
                    anomaly_type="schema_change",
                    value=0,
                    expected_range=(0, 1),
                    severity=AnomalySeverity.CRITICAL,
                    explanation=f"Column {col} was removed",
                )
                report.anomalies.append(anomaly)
                report.affected_metrics.append(f"schema:{col}")

        if added:
            for col in added:
                anomaly = Anomaly(
                    timestamp=datetime.now(timezone.utc),
                    metric_name=f"schema:{col}",
                    anomaly_type="schema_change",
                    value=1,
                    expected_range=(0, 1),
                    severity=AnomalySeverity.INFO,
                    explanation=f"Column {col} was added",
                )
                report.anomalies.append(anomaly)
                report.affected_metrics.append(f"schema:{col}")

        # Check for type changes
        for col in cols_old & cols_new:
            old_type = schema_old[col].get("type")
            new_type = schema_new[col].get("type")
            if old_type != new_type:
                anomaly = Anomaly(
                    timestamp=datetime.now(timezone.utc),
                    metric_name=f"schema:{col}",
                    anomaly_type="type_change",
                    value=0,
                    expected_range=(0, 1),
                    severity=AnomalySeverity.CRITICAL,
                    explanation=f"Column {col} type changed from {old_type} to {new_type}",
                )
                report.anomalies.append(anomaly)

        if report.anomalies:
            report.severity_level = max(a.severity for a in report.anomalies)

        return report

    def detect_seasonality_violation(
        self,
        metric_name: str,
        metric_history: List[Tuple[datetime, float]],
        expected_period_hours: int = 24,
    ) -> AnomalyReport:
        """Detect violation of expected seasonality pattern.
        
        Args:
            metric_name: Name of the metric
            metric_history: List of (timestamp, value) tuples
            expected_period_hours: Expected period (e.g., 24 for daily pattern)
            
        Returns:
            AnomalyReport with seasonality violations
        """
        report = AnomalyReport(detected_at=datetime.now(timezone.utc))

        if len(metric_history) < expected_period_hours * 2:
            return report

        values = [v for _, v in metric_history]
        timestamps = [t for t, _ in metric_history]

        # Group by period
        period_values = {}
        for i, (ts, val) in enumerate(metric_history):
            hour_of_cycle = i % expected_period_hours
            if hour_of_cycle not in period_values:
                period_values[hour_of_cycle] = []
            period_values[hour_of_cycle].append(val)

        if len(period_values) < expected_period_hours:
            return report

        # Calculate expected patterns
        expected_by_hour = {
            h: sum(period_values[h]) / len(period_values[h])
            for h in range(expected_period_hours)
        }

        # Check latest value against expected pattern
        latest_hour = (len(metric_history) - 1) % expected_period_hours
        latest_value = values[-1]
        expected_value = expected_by_hour[latest_hour]

        deviation = abs(latest_value - expected_value) / (expected_value + 1e-6)

        if deviation > 0.3:  # 30% deviation threshold
            anomaly = Anomaly(
                timestamp=timestamps[-1],
                metric_name=metric_name,
                anomaly_type="seasonality_violation",
                value=latest_value,
                expected_range=(expected_value * 0.7, expected_value * 1.3),
                severity=AnomalySeverity.MEDIUM,
                explanation=f"Violation of seasonal pattern: expected {expected_value:.4f}, got {latest_value:.4f}",
            )
            report.anomalies.append(anomaly)
            report.affected_metrics.append(metric_name)

        return report

    def detect_multi_metric_anomaly(
        self,
        metrics: Dict[str, List[Tuple[datetime, float]]],
    ) -> AnomalyReport:
        """Detect anomalies across multiple related metrics.
        
        Args:
            metrics: Dict mapping metric names to history
            
        Returns:
            AnomalyReport with correlated anomalies
        """
        report = AnomalyReport(detected_at=datetime.now(timezone.utc))

        # Run detection on each metric
        all_anomalies = []
        for metric_name, history in metrics.items():
            outlier_report = self.detect_outliers(metric_name, history)
            all_anomalies.extend(outlier_report.anomalies)

            drift_report = self.detect_drift(metric_name, history)
            all_anomalies.extend(drift_report.anomalies)

        report.anomalies = all_anomalies
        report.affected_metrics = list(set(a.metric_name for a in all_anomalies))

        if report.anomalies:
            report.severity_level = max(a.severity for a in report.anomalies)

            # Suggest actions
            if report.severity_level == AnomalySeverity.CRITICAL:
                report.suggested_actions.append("Immediately investigate quality issues")
                report.suggested_actions.append("Check data source and pipelines")

        return report
