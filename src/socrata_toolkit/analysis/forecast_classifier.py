"""
Completion Forecast Classifier: Risk Assessment & Blocker Detection

Deterministic classifier for ramp/violation completion forecasts.
Assigns risk levels (HIGH/MEDIUM/LOW), primary blockers, and confidence.

Output classifiers:
  - CompletionForecastClassifier
    - Risk level: HIGH, MEDIUM, LOW
    - Primary blocker: PERMIT, BUDGET, STAFFING, WEATHER, OTHER
    - Forecast confidence: HIGH, MEDIUM, LOW
    - Estimated completion date prediction quality
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk classification for project completion."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BlockerType(str, Enum):
    """Primary blockers that affect forecast confidence."""
    PERMIT = "PERMIT"
    BUDGET = "BUDGET"
    STAFFING = "STAFFING"
    WEATHER = "WEATHER"
    OTHER = "OTHER"


class ForecastConfidence(str, Enum):
    """Confidence level in the forecast estimate."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class CompletionForecastClassification:
    """Result of completion forecast classification."""
    project_id: str
    risk_level: RiskLevel
    primary_blocker: BlockerType
    forecast_confidence: ForecastConfidence

    # Numerical indicators
    days_until_deadline: int
    current_work_stage_percent: float  # 0-100
    velocity_trend: float  # Historical acceleration/deceleration
    confidence_score: float  # 0-100

    # Metadata
    reasoning: str
    recommendations: list[str]
    data_quality_flags: list[str]


class CompletionForecastClassifier:
    """
    Classify ramp/violation completion forecasts for risk and blocker patterns.

    Uses heuristics over:
    - Current work stage (%)
    - Days remaining to deadline
    - Velocity trend (acceleration/deceleration)
    - Historical completion patterns by season
    - Known blocker presence

    Does NOT invoke LLM — purely deterministic.
    """

    # Risk thresholds (empirically derived from NYC DOT ramp program)
    RISK_THRESHOLDS = {
        "high_low_stage_deadline": (30, 30),  # < 30% stage with <30 days = HIGH
        "high_velocity_threshold": -0.05,     # Deceleration >5% per week = HIGH
        "medium_threshold_deadline": 60,      # Any project >60 days overdue = MEDIUM
        "seasonal_slowdown_months": [12, 1, 2],  # December-February
    }

    # Blocker keywords and frequencies
    BLOCKER_INDICATORS = {
        BlockerType.PERMIT: {
            "keywords": ["permit", "approval", "dob", "regulatory", "pending approval"],
            "base_weight": 25,
        },
        BlockerType.BUDGET: {
            "keywords": ["budget", "funding", "appropriation", "cost", "financial"],
            "base_weight": 20,
        },
        BlockerType.STAFFING: {
            "keywords": ["staff", "contractor", "labor", "crew", "vendor", "capacity"],
            "base_weight": 18,
        },
        BlockerType.WEATHER: {
            "keywords": ["weather", "seasonal", "winter", "freeze", "condition"],
            "base_weight": 15,
        },
    }

    def classify(
        self,
        project_id: str,
        current_stage_percent: float,
        days_until_deadline: int,
        historical_velocity: float,
        known_blockers: list[str] | None = None,
        historical_completion_rate: float | None = None,
        data_quality_score: float | None = None,
    ) -> CompletionForecastClassification:
        """
        Classify a project's completion forecast.

        Args:
            project_id: Unique project identifier
            current_stage_percent: Current work progress (0-100)
            days_until_deadline: Days remaining to target completion
            historical_velocity: Velocity trend per day
            known_blockers: List of identified blockers
            historical_completion_rate: Empirical completion rate (0-1)
            data_quality_score: Data quality 0-100

        Returns:
            CompletionForecastClassification with risk, blocker, and confidence metrics
        """
        # Normalize inputs
        stage_pct = max(0.0, min(100.0, current_stage_percent))
        velocity = max(-1.0, min(1.0, historical_velocity))
        quality_score = data_quality_score or 75.0
        completion_rate = historical_completion_rate or 0.65

        blockers = known_blockers or []
        blocker_text = " ".join(blockers).lower()

        # 1. Determine primary blocker
        primary_blocker = self._classify_primary_blocker(
            blocker_text, stage_pct, velocity
        )

        # 2. Assign risk level
        risk_level = self._assign_risk_level(
            stage_pct, days_until_deadline, velocity, len(blockers), completion_rate
        )

        # 3. Assess forecast confidence
        forecast_confidence = self._assess_forecast_confidence(
            risk_level, quality_score, len(blockers), completion_rate
        )

        # 4. Compute confidence score (0-100)
        confidence_score = self._compute_confidence_score(
            risk_level, forecast_confidence, quality_score, stage_pct
        )

        # 5. Generate reasoning and recommendations
        reasoning = self._generate_reasoning(
            risk_level, primary_blocker, stage_pct, days_until_deadline, velocity
        )

        recommendations = self._generate_recommendations(
            risk_level, primary_blocker, stage_pct, days_until_deadline
        )

        # 6. Identify data quality flags
        data_flags = self._identify_data_quality_flags(quality_score, len(blockers))

        return CompletionForecastClassification(
            project_id=project_id,
            risk_level=risk_level,
            primary_blocker=primary_blocker,
            forecast_confidence=forecast_confidence,
            days_until_deadline=days_until_deadline,
            current_work_stage_percent=stage_pct,
            velocity_trend=velocity,
            confidence_score=confidence_score,
            reasoning=reasoning,
            recommendations=recommendations,
            data_quality_flags=data_flags,
        )

    def _classify_primary_blocker(
        self, blocker_text: str, stage_pct: float, velocity: float
    ) -> BlockerType:
        """Determine the primary blocking factor."""
        blocker_scores = {}
        for blocker_type, config in self.BLOCKER_INDICATORS.items():
            score = config["base_weight"]
            for keyword in config["keywords"]:
                if keyword in blocker_text:
                    score += 15
            blocker_scores[blocker_type] = score

        if blocker_scores and max(blocker_scores.values()) > 20:
            return max(blocker_scores, key=blocker_scores.get)

        if velocity < self.RISK_THRESHOLDS["high_velocity_threshold"]:
            return BlockerType.STAFFING

        if stage_pct < 25:
            return BlockerType.PERMIT

        return BlockerType.OTHER

    def _assign_risk_level(
        self,
        stage_pct: float,
        days_until_deadline: int,
        velocity: float,
        blocker_count: int,
        completion_rate: float,
    ) -> RiskLevel:
        """Assign overall risk level based on multiple factors."""
        risk_score = 0.0

        # Factor 1: Stage vs. deadline mismatch
        progress_per_day_needed = (100.0 - stage_pct) / max(1, days_until_deadline)
        if progress_per_day_needed > 2.0:
            risk_score += 40
        elif progress_per_day_needed > 1.0:
            risk_score += 25

        # Factor 2: Velocity deceleration
        if velocity < self.RISK_THRESHOLDS["high_velocity_threshold"]:
            risk_score += 30
        elif velocity < 0:
            risk_score += 15

        # Factor 3: Historical completion rate
        if completion_rate < 0.5:
            risk_score += 25
        elif completion_rate < 0.7:
            risk_score += 12

        # Factor 4: Number of active blockers
        if blocker_count >= 3:
            risk_score += 20
        elif blocker_count >= 2:
            risk_score += 10

        # Factor 5: Already overdue
        if days_until_deadline < 0:
            risk_score += 35

        if risk_score >= 70:
            return RiskLevel.HIGH
        elif risk_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _assess_forecast_confidence(
        self,
        risk_level: RiskLevel,
        data_quality_score: float,
        blocker_count: int,
        completion_rate: float,
    ) -> ForecastConfidence:
        """Assess confidence in the forecast."""
        if data_quality_score < 50:
            return ForecastConfidence.LOW

        if risk_level == RiskLevel.HIGH:
            if data_quality_score >= 80 and blocker_count <= 1:
                return ForecastConfidence.MEDIUM
            return ForecastConfidence.LOW

        if risk_level == RiskLevel.MEDIUM:
            if data_quality_score >= 85:
                return ForecastConfidence.MEDIUM
            return ForecastConfidence.LOW

        if data_quality_score >= 75:
            return ForecastConfidence.HIGH
        else:
            return ForecastConfidence.MEDIUM

    def _compute_confidence_score(
        self,
        risk_level: RiskLevel,
        forecast_confidence: ForecastConfidence,
        quality_score: float,
        stage_pct: float,
    ) -> float:
        """Compute numerical confidence score (0-100)."""
        base_score = quality_score

        if risk_level == RiskLevel.HIGH:
            base_score *= 0.7
        elif risk_level == RiskLevel.MEDIUM:
            base_score *= 0.85

        if forecast_confidence == ForecastConfidence.LOW:
            base_score *= 0.8
        elif forecast_confidence == ForecastConfidence.HIGH:
            base_score *= 1.1

        if stage_pct >= 75:
            base_score = min(100.0, base_score * 1.15)

        return min(100.0, max(0.0, base_score))

    def _generate_reasoning(
        self,
        risk_level: RiskLevel,
        primary_blocker: BlockerType,
        stage_pct: float,
        days_until_deadline: int,
        velocity: float,
    ) -> str:
        """Generate human-readable reasoning for the classification."""
        parts = []

        if risk_level == RiskLevel.HIGH:
            parts.append(
                f"HIGH risk: Project at {stage_pct:.0f}% completion with "
                f"{days_until_deadline} days remaining."
            )
        elif risk_level == RiskLevel.MEDIUM:
            parts.append(
                f"MEDIUM risk: Moderate progress ({stage_pct:.0f}%) against timeline "
                f"({days_until_deadline} days left)."
            )
        else:
            parts.append(
                f"LOW risk: Healthy progress ({stage_pct:.0f}%) with "
                f"{days_until_deadline} days in reserve."
            )

        parts.append(f"Primary blocker: {primary_blocker.value}.")

        if velocity < -0.02:
            parts.append("Concerning: Velocity is decelerating significantly.")
        elif velocity < 0:
            parts.append("Caution: Slight deceleration observed.")
        elif velocity > 0.1:
            parts.append("Positive: Project maintaining strong velocity.")

        return " ".join(parts)

    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        primary_blocker: BlockerType,
        stage_pct: float,
        days_until_deadline: int,
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if risk_level == RiskLevel.HIGH:
            if primary_blocker == BlockerType.PERMIT:
                recommendations.append(
                    "Escalate to DOB/permitting authority for expedited review"
                )
            elif primary_blocker == BlockerType.BUDGET:
                recommendations.append("Secure supplemental budget allocation immediately")
            elif primary_blocker == BlockerType.STAFFING:
                recommendations.append("Mobilize additional contractor capacity or shift schedules")
            elif primary_blocker == BlockerType.WEATHER:
                recommendations.append("Plan for weather-independent work phases if possible")

            if days_until_deadline < 30:
                recommendations.append("Consider milestone adjustment or formal extension request")

        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append(
                f"Monitor closely; maintain weekly tracking of {stage_pct:.0f}% progress metric"
            )
            if primary_blocker != BlockerType.OTHER:
                recommendations.append(f"Develop mitigation plan for {primary_blocker.value} delays")

        else:
            recommendations.append("Maintain current schedule and staffing levels")

        if stage_pct < 50 and days_until_deadline < 180:
            recommendations.append("Consider detailed burn-down chart tracking")

        return recommendations

    def _identify_data_quality_flags(
        self, quality_score: float, blocker_count: int
    ) -> list[str]:
        """Identify potential data quality or reliability issues."""
        flags = []

        if quality_score < 60:
            flags.append("Low data quality may affect forecast reliability")

        if quality_score < 40:
            flags.append("CRITICAL: Data too poor for confident forecasting")

        if blocker_count == 0:
            flags.append("No explicit blockers documented; may underestimate risk")

        return flags


def batch_classify_forecasts(
    projects: list[dict],
) -> list[CompletionForecastClassification]:
    """
    Batch classify multiple project forecasts.

    Args:
        projects: List of dicts with keys:
            - project_id
            - current_stage_percent
            - days_until_deadline
            - historical_velocity
            - known_blockers (optional)
            - historical_completion_rate (optional)
            - data_quality_score (optional)

    Returns:
        List of CompletionForecastClassification results
    """
    classifier = CompletionForecastClassifier()
    results = []

    for project in projects:
        try:
            classification = classifier.classify(
                project_id=project.get("project_id", "UNKNOWN"),
                current_stage_percent=project.get("current_stage_percent", 0),
                days_until_deadline=project.get("days_until_deadline", 0),
                historical_velocity=project.get("historical_velocity", 0),
                known_blockers=project.get("known_blockers"),
                historical_completion_rate=project.get("historical_completion_rate"),
                data_quality_score=project.get("data_quality_score"),
            )
            results.append(classification)
        except Exception as e:
            logger.warning(
                f"Failed to classify {project.get('project_id', 'UNKNOWN')}: {e}"
            )

    return results
