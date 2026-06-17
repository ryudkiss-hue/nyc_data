"""Resource Allocation Classifier for Inspector Deployment Optimization.

Classifies geographic areas by priority and suggests resource allocation actions.
Integrates spatial clustering with inspector availability metrics to recommend
optimal deployment strategies.

Key Features:
- Area priority classification (CRITICAL, HIGH, MEDIUM, LOW)
- Action recommendation (DISPATCH, CONSOLIDATE, OPTIMIZE)
- Impact estimation (HIGH, MEDIUM, LOW)
- Inspector-to-violation ratio analysis
- Coverage gap identification
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd


class AreaPriority(str, Enum):
    """Classification of area urgency for inspector deployment."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class AllocationAction(str, Enum):
    """Recommended action for resource reallocation."""
    DISPATCH = "DISPATCH"  # Send inspectors immediately
    CONSOLIDATE = "CONSOLIDATE"  # Merge nearby inspector teams
    OPTIMIZE = "OPTIMIZE"  # Rebalance current allocation
    MONITOR = "MONITOR"  # Track but no action needed

class ImpactLevel(str, Enum):
    """Estimated impact of reallocation."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class AllocationClassification:
    """Result of resource allocation classification for a geographic area.

    Attributes:
        area_id: Unique identifier for the area (e.g., block ID, grid cell)
        area_name: Human-readable area name (e.g., "MN-001")
        priority: Area priority level
        action: Recommended action
        impact: Estimated impact of reallocation
        violation_count: Total violations in area
        response_time_days: Average response time in days
        inspector_count: Current number of inspectors assigned
        violations_per_inspector: Ratio of violations to inspectors
        coverage_gap_pct: Percentage of violations without timely response
        confidence_score: Confidence in classification (0.0-1.0)
        rationale: Human-readable explanation of classification
        alternative_actions: List of alternative actions to consider
    """
    area_id: str
    area_name: str
    priority: AreaPriority
    action: AllocationAction
    impact: ImpactLevel
    violation_count: int
    response_time_days: float
    inspector_count: int
    violations_per_inspector: float
    coverage_gap_pct: float
    confidence_score: float
    rationale: str
    alternative_actions: list[str]

class ResourceAllocationClassifier:
    """Classifies geographic areas and recommends inspector allocation strategies.

    This classifier uses violation density, response time, and inspector availability
    to recommend where to dispatch additional resources, consolidate operations, or
    optimize existing allocations.

    Thresholds (configurable):
    - CRITICAL: >50 violations/inspector OR response_time >14 days
    - HIGH: >35 violations/inspector OR response_time >10 days
    - MEDIUM: >20 violations/inspector OR response_time >7 days
    - LOW: otherwise
    """

    def __init__(
        self,
        critical_violations_per_inspector: float = 50.0,
        critical_response_days: float = 14.0,
        high_violations_per_inspector: float = 35.0,
        high_response_days: float = 10.0,
        medium_violations_per_inspector: float = 20.0,
        medium_response_days: float = 7.0,
    ):
        """Initialize classifier with configurable thresholds.

        Args:
            critical_violations_per_inspector: Threshold for CRITICAL priority
            critical_response_days: Response time threshold (days) for CRITICAL
            high_violations_per_inspector: Threshold for HIGH priority
            high_response_days: Response time threshold (days) for HIGH
            medium_violations_per_inspector: Threshold for MEDIUM priority
            medium_response_days: Response time threshold (days) for MEDIUM
        """
        self.critical_vpi = critical_violations_per_inspector
        self.critical_days = critical_response_days
        self.high_vpi = high_violations_per_inspector
        self.high_days = high_response_days
        self.medium_vpi = medium_violations_per_inspector
        self.medium_days = medium_response_days

    def classify_area(
        self,
        area_id: str,
        area_name: str,
        violation_count: int,
        response_time_days: float,
        inspector_count: int,
        violations_with_response: int,
    ) -> AllocationClassification:
        """Classify a single geographic area for resource allocation.

        Args:
            area_id: Unique identifier for the area
            area_name: Human-readable name for the area
            violation_count: Total violations in area
            response_time_days: Average response time in days
            inspector_count: Number of inspectors currently assigned
            violations_with_response: Count of violations with timely response

        Returns:
            AllocationClassification with priority, action, and rationale
        """
        if inspector_count <= 0:
            inspector_count = 1  # Avoid division by zero

        violations_per_inspector = violation_count / inspector_count
        coverage_gap_pct = (
            (violation_count - violations_with_response) / violation_count * 100
            if violation_count > 0
            else 0.0
        )

        # Determine priority
        if (violations_per_inspector >= self.critical_vpi or
            response_time_days >= self.critical_days):
            priority = AreaPriority.CRITICAL
        elif (violations_per_inspector >= self.high_vpi or
              response_time_days >= self.high_days):
            priority = AreaPriority.HIGH
        elif (violations_per_inspector >= self.medium_vpi or
              response_time_days >= self.medium_days):
            priority = AreaPriority.MEDIUM
        else:
            priority = AreaPriority.LOW

        # Determine action and impact
        action, impact, rationale, alternatives = self._recommend_action(
            priority,
            violations_per_inspector,
            response_time_days,
            inspector_count,
            coverage_gap_pct,
        )

        # Confidence score based on data completeness
        confidence = self._compute_confidence(
            violation_count, inspector_count, response_time_days
        )

        return AllocationClassification(
            area_id=area_id,
            area_name=area_name,
            priority=priority,
            action=action,
            impact=impact,
            violation_count=violation_count,
            response_time_days=response_time_days,
            inspector_count=inspector_count,
            violations_per_inspector=violations_per_inspector,
            coverage_gap_pct=coverage_gap_pct,
            confidence_score=confidence,
            rationale=rationale,
            alternative_actions=alternatives,
        )

    def classify_dataframe(
        self,
        df: pd.DataFrame,
        area_col: str,
        area_name_col: str,
        violations_col: str,
        response_time_col: str,
        inspector_col: str,
        response_violations_col: str,
    ) -> list[AllocationClassification]:
        """Classify multiple areas from a DataFrame.

        Args:
            df: DataFrame with area metrics
            area_col: Column name for area ID
            area_name_col: Column name for area name
            violations_col: Column name for violation count
            response_time_col: Column name for response time (days)
            inspector_col: Column name for inspector count
            response_violations_col: Column name for violations with timely response

        Returns:
            List of AllocationClassification objects
        """
        results = []
        for _, row in df.iterrows():
            result = self.classify_area(
                area_id=str(row[area_col]),
                area_name=str(row[area_name_col]),
                violation_count=int(row[violations_col]),
                response_time_days=float(row[response_time_col]),
                inspector_count=int(row[inspector_col]),
                violations_with_response=int(row[response_violations_col]),
            )
            results.append(result)
        return results

    def _recommend_action(
        self,
        priority: AreaPriority,
        violations_per_inspector: float,
        response_time_days: float,
        inspector_count: int,
        coverage_gap_pct: float,
    ) -> tuple[AllocationAction, ImpactLevel, str, list[str]]:
        """Recommend action based on priority and metrics.

        Returns:
            Tuple of (action, impact, rationale, alternative_actions)
        """
        alternatives = []

        if priority == AreaPriority.CRITICAL:
            action = AllocationAction.DISPATCH
            impact = ImpactLevel.HIGH
            rationale = (
                f"CRITICAL area: {violations_per_inspector:.1f} violations per inspector, "
                f"{response_time_days:.1f}d response time, {coverage_gap_pct:.0f}% coverage gap. "
                f"Dispatch additional inspectors immediately."
            )
            alternatives = [
                AllocationAction.CONSOLIDATE.value,
                AllocationAction.OPTIMIZE.value,
            ]

        elif priority == AreaPriority.HIGH:
            action = AllocationAction.CONSOLIDATE
            impact = ImpactLevel.MEDIUM
            rationale = (
                f"HIGH priority area: {violations_per_inspector:.1f} violations per inspector, "
                f"response time {response_time_days:.1f}d. Consolidate nearby teams to increase coverage."
            )
            alternatives = [
                AllocationAction.DISPATCH.value,
                AllocationAction.OPTIMIZE.value,
            ]

        elif priority == AreaPriority.MEDIUM:
            action = AllocationAction.OPTIMIZE
            impact = ImpactLevel.MEDIUM
            rationale = (
                f"MEDIUM priority area: {violations_per_inspector:.1f} violations per inspector. "
                f"Rebalance allocation to improve efficiency."
            )
            alternatives = [
                AllocationAction.CONSOLIDATE.value,
                AllocationAction.MONITOR.value,
            ]

        else:  # LOW
            action = AllocationAction.MONITOR
            impact = ImpactLevel.LOW
            rationale = (
                f"LOW priority area: {violations_per_inspector:.1f} violations per inspector, "
                f"response time {response_time_days:.1f}d. Current allocation is adequate."
            )
            alternatives = [
                AllocationAction.OPTIMIZE.value,
            ]

        return action, impact, rationale, alternatives

    def _compute_confidence(
        self,
        violation_count: int,
        inspector_count: int,
        response_time_days: float,
    ) -> float:
        """Compute confidence score based on data completeness.

        Confidence increases with larger sample sizes and more complete data.
        Returns score between 0.0 and 1.0.
        """
        # Sample size confidence
        min_violations = 10
        sample_confidence = min(violation_count / min_violations, 1.0)

        # Inspector assignment confidence
        inspector_confidence = 1.0 if inspector_count > 0 else 0.5

        # Response time data confidence
        time_confidence = 1.0 if response_time_days >= 0 else 0.7

        # Weighted average
        confidence = (
            sample_confidence * 0.5 +
            inspector_confidence * 0.3 +
            time_confidence * 0.2
        )

        return min(confidence, 1.0)

    def summarize_allocations(
        self, classifications: list[AllocationClassification]
    ) -> dict[str, Any]:
        """Summarize resource allocation classifications.

        Args:
            classifications: List of AllocationClassification results

        Returns:
            Dictionary with summary statistics
        """
        if not classifications:
            return {}

        df = pd.DataFrame([
            {
                "priority": c.priority.value,
                "action": c.action.value,
                "violation_count": c.violation_count,
                "inspector_count": c.inspector_count,
                "violations_per_inspector": c.violations_per_inspector,
                "response_time_days": c.response_time_days,
                "coverage_gap_pct": c.coverage_gap_pct,
            }
            for c in classifications
        ])

        return {
            "total_areas": len(classifications),
            "total_violations": int(df["violation_count"].sum()),
            "total_inspectors": int(df["inspector_count"].sum()),
            "avg_violations_per_inspector": float(
                df["violation_count"].sum() / df["inspector_count"].sum()
            ),
            "avg_response_time_days": float(df["response_time_days"].mean()),
            "priority_counts": df["priority"].value_counts().to_dict(),
            "action_counts": df["action"].value_counts().to_dict(),
            "critical_areas": len(df[df["priority"] == "CRITICAL"]),
            "high_areas": len(df[df["priority"] == "HIGH"]),
            "medium_areas": len(df[df["priority"] == "MEDIUM"]),
            "low_areas": len(df[df["priority"] == "LOW"]),
            "total_coverage_gap_pct": float(df["coverage_gap_pct"].mean()),
        }
