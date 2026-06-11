"""
Velocity Classifier for Inspector Performance Analysis.

Classifies inspector performance into tiers (HIGH/MEDIUM/LOW) based on:
- Inspection velocity (inspections/week)
- Quality metrics (violations per inspection, dismissal rate)
- Accuracy metrics (reopened violations, accuracy ratio)
- Efficiency trends (time-to-close, throughput consistency)
- Anomalies (sudden drops, plateaus, acceleration)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class PerformanceTier(str, Enum):
    """Performance classification tier."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MetricType(str, Enum):
    """Metric category for classification."""
    VELOCITY = "VELOCITY"           # Inspections/week
    QUALITY = "QUALITY"             # Violations/inspection, dismissal %
    ACCURACY = "ACCURACY"           # Reopened %, accuracy ratio
    EFFICIENCY = "EFFICIENCY"       # Time-to-close, consistency


class AnomalyType(str, Enum):
    """Anomaly classification for time-series patterns."""
    SUDDEN_DROP = "SUDDEN_DROP"
    PLATEAU = "PLATEAU"
    ACCELERATING = "ACCELERATING"
    NORMAL = "NORMAL"


@dataclass
class VelocityMetrics:
    """Raw metrics for a single inspector in a period."""
    inspector_id: str
    inspector_name: str | None
    period_start: pd.Timestamp
    period_end: pd.Timestamp

    # Velocity
    inspection_count: int = 0
    inspections_per_week: float = 0.0

    # Quality
    total_violations: int = 0
    violations_per_inspection: float = 0.0
    dismissal_count: int = 0
    dismissal_rate: float = 0.0  # 0.0-1.0

    # Accuracy
    reopened_count: int = 0
    reopened_rate: float = 0.0  # 0.0-1.0
    accuracy_ratio: float = 0.0  # (violations - reopened) / violations, clamped 0-1

    # Efficiency
    avg_days_to_close: float = 0.0
    median_days_to_close: float = 0.0
    velocity_std_dev: float = 0.0

    # Metadata
    data_quality_flag: str = ""  # "LOW", "MEDIUM", "HIGH"
    sample_size: int = 0


@dataclass
class VelocityClassification:
    """Classification result for an inspector."""
    inspector_id: str
    inspector_name: str | None
    period_start: pd.Timestamp
    period_end: pd.Timestamp

    # Classification
    performance_tier: PerformanceTier
    metric_drivers: list[MetricType] = field(default_factory=list)
    anomaly: AnomalyType = AnomalyType.NORMAL

    # Scores (0-100)
    velocity_score: float = 0.0
    quality_score: float = 0.0
    accuracy_score: float = 0.0
    efficiency_score: float = 0.0
    composite_score: float = 0.0

    # Raw metrics (for reference)
    metrics: VelocityMetrics | None = None

    # Recommendations (brief)
    flagged_issues: list[str] = field(default_factory=list)
    coaching_focus: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "inspector_id": self.inspector_id,
            "inspector_name": self.inspector_name,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "performance_tier": self.performance_tier.value,
            "metric_drivers": [m.value for m in self.metric_drivers],
            "anomaly": self.anomaly.value,
            "velocity_score": round(self.velocity_score, 1),
            "quality_score": round(self.quality_score, 1),
            "accuracy_score": round(self.accuracy_score, 1),
            "efficiency_score": round(self.efficiency_score, 1),
            "composite_score": round(self.composite_score, 1),
            "flagged_issues": self.flagged_issues,
            "coaching_focus": self.coaching_focus,
        }


class VelocityClassifier:
    """
    Inspector performance classifier.

    Assigns performance tier (HIGH/MEDIUM/LOW) based on multidimensional metrics.
    Identifies metric drivers and anomalies for coaching recommendations.
    """

    # Velocity thresholds (inspections per week)
    VELOCITY_HIGH_THRESHOLD = 6.0
    VELOCITY_MEDIUM_THRESHOLD = 3.0

    # Quality thresholds (violations per inspection)
    QUALITY_HIGH_THRESHOLD = 4.0
    QUALITY_MEDIUM_THRESHOLD = 2.0

    # Dismissal rate thresholds (0-1)
    DISMISSAL_HIGH_RATE = 0.35
    DISMISSAL_MEDIUM_RATE = 0.20

    # Accuracy thresholds (reopened rate)
    ACCURACY_HIGH_REOPENED = 0.15
    ACCURACY_MEDIUM_REOPENED = 0.25

    # Efficiency thresholds (days to close)
    EFFICIENCY_HIGH_DAYS = 30.0
    EFFICIENCY_MEDIUM_DAYS = 60.0

    # Anomaly detection thresholds
    ANOMALY_DROP_THRESHOLD = 0.5  # 50% drop in velocity
    ANOMALY_PLATEAU_WEEKS = 2  # Flat for N weeks
    ANOMALY_ACCELERATION_THRESHOLD = 1.3  # 30% increase

    def classify(
        self,
        metrics: VelocityMetrics,
        historical_metrics: list[VelocityMetrics] | None = None,
    ) -> VelocityClassification:
        """
        Classify inspector performance.

        Args:
            metrics: Current period metrics
            historical_metrics: Previous periods for anomaly detection (sorted by period_end)

        Returns:
            VelocityClassification with tier, scores, and recommendations
        """
        if not metrics or metrics.inspection_count == 0:
            return self._create_no_data_classification(metrics)

        # Score each dimension
        velocity_score = self._score_velocity(metrics)
        quality_score = self._score_quality(metrics)
        accuracy_score = self._score_accuracy(metrics)
        efficiency_score = self._score_efficiency(metrics)

        # Compute composite (weighted average)
        composite_score = (
            velocity_score * 0.35 +
            quality_score * 0.25 +
            accuracy_score * 0.25 +
            efficiency_score * 0.15
        )

        # Determine tier from composite score
        tier = self._tier_from_score(composite_score)

        # Identify metric drivers (outlier dimensions)
        metric_drivers = self._identify_metric_drivers(
            velocity_score, quality_score, accuracy_score, efficiency_score
        )

        # Detect anomalies in time-series
        anomaly = AnomalyType.NORMAL
        if historical_metrics:
            anomaly = self._detect_anomaly(metrics, historical_metrics)

        # Generate flagged issues and coaching
        flagged_issues = self._identify_issues(metrics, velocity_score, quality_score)
        coaching_focus = self._recommend_coaching(
            tier, metric_drivers, anomaly, flagged_issues
        )

        return VelocityClassification(
            inspector_id=metrics.inspector_id,
            inspector_name=metrics.inspector_name,
            period_start=metrics.period_start,
            period_end=metrics.period_end,
            performance_tier=tier,
            metric_drivers=metric_drivers,
            anomaly=anomaly,
            velocity_score=velocity_score,
            quality_score=quality_score,
            accuracy_score=accuracy_score,
            efficiency_score=efficiency_score,
            composite_score=composite_score,
            metrics=metrics,
            flagged_issues=flagged_issues,
            coaching_focus=coaching_focus,
        )

    def _score_velocity(self, metrics: VelocityMetrics) -> float:
        """Score velocity: inspections/week (0-100)."""
        v = metrics.inspections_per_week
        if v >= self.VELOCITY_HIGH_THRESHOLD:
            return min(100.0, 60.0 + (v - self.VELOCITY_HIGH_THRESHOLD) * 5)
        elif v >= self.VELOCITY_MEDIUM_THRESHOLD:
            return 30.0 + (v - self.VELOCITY_MEDIUM_THRESHOLD) * 15
        else:
            return max(0.0, v * 30)

    def _score_quality(self, metrics: VelocityMetrics) -> float:
        """Score quality: violations/inspection and dismissal rate (0-100)."""
        v_score = 100.0

        # Violations per inspection (higher is worse)
        vpi = metrics.violations_per_inspection
        if vpi > self.QUALITY_HIGH_THRESHOLD:
            v_score -= min(40.0, (vpi - self.QUALITY_HIGH_THRESHOLD) * 5)
        elif vpi > self.QUALITY_MEDIUM_THRESHOLD:
            v_score -= (vpi - self.QUALITY_MEDIUM_THRESHOLD) * 10

        # Dismissal rate (higher is worse)
        d_score = 100.0
        dr = metrics.dismissal_rate
        if dr > self.DISMISSAL_HIGH_RATE:
            d_score -= min(40.0, (dr - self.DISMISSAL_HIGH_RATE) * 100)
        elif dr > self.DISMISSAL_MEDIUM_RATE:
            d_score -= (dr - self.DISMISSAL_MEDIUM_RATE) * 50

        return max(0.0, (v_score + d_score) / 2)

    def _score_accuracy(self, metrics: VelocityMetrics) -> float:
        """Score accuracy: reopened rate and accuracy ratio (0-100)."""
        rr = metrics.reopened_rate
        if rr > self.ACCURACY_HIGH_REOPENED:
            score = max(0.0, 100.0 - (rr - self.ACCURACY_HIGH_REOPENED) * 200)
        elif rr > self.ACCURACY_MEDIUM_REOPENED:
            score = 50.0 - (rr - self.ACCURACY_MEDIUM_REOPENED) * 100
        else:
            score = 80.0 + (1.0 - rr) * 20

        return max(0.0, min(100.0, score))

    def _score_efficiency(self, metrics: VelocityMetrics) -> float:
        """Score efficiency: time-to-close and velocity consistency (0-100)."""
        # Days to close (lower is better)
        dtc = metrics.avg_days_to_close
        if dtc <= self.EFFICIENCY_HIGH_DAYS:
            score = 90.0
        elif dtc <= self.EFFICIENCY_MEDIUM_DAYS:
            score = 50.0 + (self.EFFICIENCY_MEDIUM_DAYS - dtc) / self.EFFICIENCY_MEDIUM_DAYS * 40
        else:
            score = max(10.0, 50.0 - (dtc - self.EFFICIENCY_MEDIUM_DAYS) / 30)

        # Consistency penalty (high std dev is bad)
        if metrics.velocity_std_dev > 0:
            consistency_factor = 1.0 - min(1.0, metrics.velocity_std_dev / 5.0)
            score *= consistency_factor

        return max(0.0, min(100.0, score))

    def _tier_from_score(self, composite_score: float) -> PerformanceTier:
        """Map composite score to tier."""
        if composite_score >= 70.0:
            return PerformanceTier.HIGH
        elif composite_score >= 40.0:
            return PerformanceTier.MEDIUM
        else:
            return PerformanceTier.LOW

    def _identify_metric_drivers(
        self, velocity: float, quality: float, accuracy: float, efficiency: float
    ) -> list[MetricType]:
        """Identify dimensions driving the classification."""
        drivers = []
        avg = (velocity + quality + accuracy + efficiency) / 4.0

        # Dimensions >10 points above average are drivers
        if velocity > avg + 10:
            drivers.append(MetricType.VELOCITY)
        if quality > avg + 10:
            drivers.append(MetricType.QUALITY)
        if accuracy > avg + 10:
            drivers.append(MetricType.ACCURACY)
        if efficiency > avg + 10:
            drivers.append(MetricType.EFFICIENCY)

        # If all are similar, list none (balanced profile)
        if not drivers and max(velocity, quality, accuracy, efficiency) - min(velocity, quality, accuracy, efficiency) < 10:
            return []

        return drivers

    def _detect_anomaly(
        self, current: VelocityMetrics, historical: list[VelocityMetrics]
    ) -> AnomalyType:
        """Detect anomalies in time-series velocity."""
        if len(historical) < 2:
            return AnomalyType.NORMAL

        # Recent baseline (last period)
        prev_velocity = historical[-1].inspections_per_week if historical else 0.0
        curr_velocity = current.inspections_per_week

        # Sudden drop (50%+ decrease)
        if prev_velocity > 0 and curr_velocity < prev_velocity * (1 - self.ANOMALY_DROP_THRESHOLD):
            return AnomalyType.SUDDEN_DROP

        # Plateau: flat for N weeks
        if len(historical) >= self.ANOMALY_PLATEAU_WEEKS:
            recent = [h.inspections_per_week for h in historical[-self.ANOMALY_PLATEAU_WEEKS:]]
            if max(recent) - min(recent) < 0.5:
                return AnomalyType.PLATEAU

        # Acceleration: 30%+ increase
        if prev_velocity > 0 and curr_velocity > prev_velocity * self.ANOMALY_ACCELERATION_THRESHOLD:
            return AnomalyType.ACCELERATING

        return AnomalyType.NORMAL

    def _identify_issues(
        self, metrics: VelocityMetrics, velocity_score: float, quality_score: float
    ) -> list[str]:
        """Identify flagged issues for coaching."""
        issues = []

        if metrics.inspections_per_week < 1.0:
            issues.append("CRITICAL: Very low velocity (< 1 inspection/week)")
        elif metrics.inspections_per_week < self.VELOCITY_MEDIUM_THRESHOLD:
            issues.append("Low velocity")

        if metrics.dismissal_rate > self.DISMISSAL_HIGH_RATE:
            issues.append(f"High dismissal rate ({metrics.dismissal_rate*100:.1f}%)")

        if metrics.reopened_rate > self.ACCURACY_HIGH_REOPENED:
            issues.append(f"High reopened rate ({metrics.reopened_rate*100:.1f}%)")

        if metrics.avg_days_to_close > self.EFFICIENCY_MEDIUM_DAYS:
            issues.append(f"Slow case closure ({metrics.avg_days_to_close:.0f} days)")

        if metrics.violations_per_inspection < self.QUALITY_MEDIUM_THRESHOLD:
            issues.append("Low violations per inspection (may indicate under-inspection)")

        return issues

    def _recommend_coaching(
        self,
        tier: PerformanceTier,
        metric_drivers: list[MetricType],
        anomaly: AnomalyType,
        flagged_issues: list[str],
    ) -> str:
        """Generate coaching recommendation."""
        focus = ""

        if tier == PerformanceTier.LOW:
            focus = "Priority: Intensive coaching required. Schedule 1:1 to understand barriers."
        elif tier == PerformanceTier.MEDIUM:
            focus = "Continue monitoring. Address specific metric gaps."
        else:  # HIGH
            focus = "Strong performer. Recognize and leverage as peer mentor."

        if anomaly == AnomalyType.SUDDEN_DROP:
            focus += " Flag: Recent velocity drop detected."
        elif anomaly == AnomalyType.PLATEAU:
            focus += " Flag: Velocity plateau — assess for burnout."
        elif anomaly == AnomalyType.ACCELERATING:
            focus += " Flag: Rapid acceleration — verify quality not sacrificed."

        if MetricType.ACCURACY in metric_drivers:
            focus += " | Focus: Improve case accuracy."
        elif MetricType.EFFICIENCY in metric_drivers:
            focus += " | Focus: Streamline case closure process."

        if flagged_issues:
            focus += f" | {flagged_issues[0]}"

        return focus

    def _create_no_data_classification(self, metrics: VelocityMetrics | None) -> VelocityClassification:
        """Create a no-data classification."""
        m = metrics or VelocityMetrics(
            inspector_id="UNKNOWN",
            inspector_name=None,
            period_start=pd.Timestamp.now(),
            period_end=pd.Timestamp.now(),
        )
        return VelocityClassification(
            inspector_id=m.inspector_id,
            inspector_name=m.inspector_name,
            period_start=m.period_start,
            period_end=m.period_end,
            performance_tier=PerformanceTier.MEDIUM,
            composite_score=0.0,
            coaching_focus="Insufficient data for classification.",
            flagged_issues=["No inspection data"],
        )
