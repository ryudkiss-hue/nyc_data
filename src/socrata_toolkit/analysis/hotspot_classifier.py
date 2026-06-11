"""Hotspot Classification Engine for Geographic Analysis.

This module classifies geographic hotspots based on:
- Violation and complaint density
- Temporal trends (growing/stable/shrinking)
- Resource allocation efficiency
- Composite severity scoring

Classifications enable targeted resource allocation and prioritization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from enum import Enum

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class HotspotType(str, Enum):
    """Hotspot classification by data source."""
    VIOLATION = "VIOLATION"
    COMPLAINT = "COMPLAINT"
    COMBINED = "COMBINED"


class DensityLevel(str, Enum):
    """Density classification (events per sq km)."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Trend(str, Enum):
    """Temporal trend classification."""
    GROWING = "GROWING"
    STABLE = "STABLE"
    SHRINKING = "SHRINKING"


class ResourceAllocation(str, Enum):
    """Resource efficiency classification."""
    OVER_RESOURCED = "OVER_RESOURCED"
    OPTIMIZED = "OPTIMIZED"
    UNDER_RESOURCED = "UNDER_RESOURCED"


@dataclass
class HotspotMetrics:
    """Core metrics for a detected hotspot."""
    hotspot_id: str
    latitude: float
    longitude: float
    density_per_sqkm: float
    event_count: int
    recent_event_count: int
    event_types: list[str]
    trend_direction: Trend
    trend_pct_change: float
    estimated_personnel: int
    resource_efficiency: float


@dataclass
class HotspotClassifier:
    """Classified hotspot with actionable intelligence."""
    hotspot_id: str
    hotspot_type: HotspotType
    density_level: DensityLevel
    severity_score: float  # 0-100
    trend: Trend
    resource_allocation: ResourceAllocation

    # Reasoning
    classification_reasoning: str
    recommendation: str
    estimated_backlog_days: int
    priority_rank: int

    # Raw data references
    latitude: float
    longitude: float
    event_count: int
    density_per_sqkm: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            **asdict(self),
            "hotspot_type": self.hotspot_type.value,
            "density_level": self.density_level.value,
            "trend": self.trend.value,
            "resource_allocation": self.resource_allocation.value,
        }


class HotspotClassificationEngine:
    """Classify hotspots using multi-dimensional analysis.

    Scoring framework:
    - Density (40%): HIGH=40, MEDIUM=20, LOW=5
    - Trend (30%): GROWING=30, STABLE=15, SHRINKING=5
    - Resource efficiency (30%): UNDER_RESOURCED=30, OPTIMIZED=15, OVER_RESOURCED=5

    Resource allocation decision:
    - Density > 50 events/sq km OR recent spike → UNDER_RESOURCED
    - Trend GROWING + efficiency < 0.7 → UNDER_RESOURCED
    - Density < 10 AND trend SHRINKING → OVER_RESOURCED
    - Otherwise → OPTIMIZED
    """

    # Density thresholds (events per sq km)
    DENSITY_HIGH_THRESHOLD = 50
    DENSITY_MEDIUM_THRESHOLD = 15

    # Recent window for spike detection (days)
    RECENT_WINDOW_DAYS = 7

    # Trend thresholds (percent change over period)
    TREND_GROWING_THRESHOLD = 0.15  # > +15% = growing
    TREND_SHRINKING_THRESHOLD = -0.15  # < -15% = shrinking

    # Resource efficiency thresholds
    EFFICIENCY_OPTIMAL = 0.7
    EFFICIENCY_ACCEPTABLE = 0.5

    def __init__(self):
        """Initialize the classification engine."""
        self.hotspots: list[HotspotClassifier] = []
        self.priority_counter = 0

    def classify(
        self,
        metrics: HotspotMetrics,
        total_hotspots: int,
    ) -> HotspotClassifier:
        """Classify a single hotspot based on metrics.

        Args:
            metrics: HotspotMetrics with density, trend, resource data
            total_hotspots: Total number of hotspots for ranking context

        Returns:
            HotspotClassifier with classification, reasoning, and recommendations
        """
        # Determine hotspot type from event types
        has_violations = "violation" in [t.lower() for t in metrics.event_types]
        has_complaints = "complaint" in [t.lower() for t in metrics.event_types]

        if has_violations and has_complaints:
            hotspot_type = HotspotType.COMBINED
        elif has_violations:
            hotspot_type = HotspotType.VIOLATION
        else:
            hotspot_type = HotspotType.COMPLAINT

        # Density classification
        if metrics.density_per_sqkm >= self.DENSITY_HIGH_THRESHOLD:
            density_level = DensityLevel.HIGH
            density_score = 40
        elif metrics.density_per_sqkm >= self.DENSITY_MEDIUM_THRESHOLD:
            density_level = DensityLevel.MEDIUM
            density_score = 20
        else:
            density_level = DensityLevel.LOW
            density_score = 5

        # Trend scoring
        if metrics.trend_direction == Trend.GROWING:
            trend_score = 30
        elif metrics.trend_direction == Trend.STABLE:
            trend_score = 15
        else:  # SHRINKING
            trend_score = 5

        # Resource efficiency classification
        efficiency = metrics.resource_efficiency
        if efficiency < self.EFFICIENCY_ACCEPTABLE:
            resource_score = 30
        elif efficiency < self.EFFICIENCY_OPTIMAL:
            resource_score = 15
        else:
            resource_score = 5

        # Composite severity score
        severity_score = (
            density_score * 0.4 +
            trend_score * 0.3 +
            resource_score * 0.3
        )

        # Determine resource allocation
        recent_spike = (
            metrics.recent_event_count > metrics.event_count * 0.3
        )

        if (
            metrics.density_per_sqkm > self.DENSITY_HIGH_THRESHOLD
            or recent_spike
            or (metrics.trend_direction == Trend.GROWING and efficiency < 0.7)
        ):
            resource_allocation = ResourceAllocation.UNDER_RESOURCED
        elif (
            metrics.density_per_sqkm < self.DENSITY_MEDIUM_THRESHOLD
            and metrics.trend_direction == Trend.SHRINKING
            and efficiency > self.EFFICIENCY_OPTIMAL
        ):
            resource_allocation = ResourceAllocation.OVER_RESOURCED
        else:
            resource_allocation = ResourceAllocation.OPTIMIZED

        # Estimate backlog (days to address all open items)
        daily_rate = max(1, metrics.event_count // 30)  # Average daily rate
        estimated_backlog = max(1, metrics.event_count // max(1, metrics.estimated_personnel))

        # Priority ranking (higher severity = lower rank = higher priority)
        self.priority_counter += 1
        priority_rank = self.priority_counter

        # Build reasoning and recommendation
        reasoning, recommendation = self._generate_reasoning(
            hotspot_type=hotspot_type,
            density_level=density_level,
            trend=metrics.trend_direction,
            resource_allocation=resource_allocation,
            metrics=metrics,
        )

        return HotspotClassifier(
            hotspot_id=metrics.hotspot_id,
            hotspot_type=hotspot_type,
            density_level=density_level,
            severity_score=severity_score,
            trend=metrics.trend_direction,
            resource_allocation=resource_allocation,
            classification_reasoning=reasoning,
            recommendation=recommendation,
            estimated_backlog_days=estimated_backlog,
            priority_rank=priority_rank,
            latitude=metrics.latitude,
            longitude=metrics.longitude,
            event_count=metrics.event_count,
            density_per_sqkm=metrics.density_per_sqkm,
        )

    def _generate_reasoning(
        self,
        hotspot_type: HotspotType,
        density_level: DensityLevel,
        trend: Trend,
        resource_allocation: ResourceAllocation,
        metrics: HotspotMetrics,
    ) -> tuple[str, str]:
        """Generate classification reasoning and operational recommendation.

        Returns:
            (reasoning_text, recommendation_text)
        """
        # Reasoning: explain the classification
        reasoning_parts = [
            f"Type: {hotspot_type.value}.",
            f"Density: {density_level.value} ({metrics.density_per_sqkm:.1f} events/sq km).",
            f"Trend: {trend.value} ({metrics.trend_pct_change:+.1f}% over period).",
            f"Resource allocation: {resource_allocation.value} (efficiency: {metrics.resource_efficiency:.2f}).",
        ]
        reasoning = " ".join(reasoning_parts)

        # Recommendation: operational action
        if resource_allocation == ResourceAllocation.UNDER_RESOURCED:
            if trend == Trend.GROWING:
                rec = (
                    f"PRIORITY: This {hotspot_type.value} hotspot is growing and understaffed. "
                    f"Deploy additional personnel or expand operating hours. "
                    f"Estimated backlog: {metrics.event_count} items. "
                    f"Recommend weekly monitoring until trend stabilizes."
                )
            else:
                rec = (
                    f"This {hotspot_type.value} hotspot has persistent high density. "
                    f"Current resources insufficient to maintain service levels. "
                    f"Recommend deployment review and workload redistribution."
                )
        elif resource_allocation == ResourceAllocation.OVER_RESOURCED:
            rec = (
                f"This hotspot is stabilizing ({density_level.value} density, {trend.value} trend). "
                f"Current resource level appears sufficient. "
                f"Recommend reallocation to emerging problem areas."
            )
        else:  # OPTIMIZED
            if trend == Trend.GROWING:
                rec = (
                    f"This hotspot is growing but currently optimized. "
                    f"Monitor closely and be prepared to escalate resources if trend accelerates."
                )
            else:
                rec = (
                    f"This hotspot is at optimal resource allocation. "
                    f"Continue current staffing and response strategy. "
                    f"Schedule monthly review to confirm trend stability."
                )

        return reasoning, rec

    def rank_hotspots(
        self,
        classifiers: list[HotspotClassifier],
    ) -> list[HotspotClassifier]:
        """Sort hotspots by priority (severity score descending).

        Args:
            classifiers: List of classified hotspots

        Returns:
            Sorted list with priority_rank updated
        """
        sorted_list = sorted(
            classifiers,
            key=lambda x: x.severity_score,
            reverse=True,
        )
        for idx, classifier in enumerate(sorted_list, start=1):
            classifier.priority_rank = idx
        return sorted_list


def classify_hotspots_from_dataframe(
    violations_df: pd.DataFrame | None = None,
    complaints_df: pd.DataFrame | None = None,
    clusters: list[dict] | None = None,
) -> list[HotspotClassifier]:
    """Classify hotspots from raw violation/complaint DataFrames.

    Args:
        violations_df: DataFrame with violation data (must have geometry)
        complaints_df: DataFrame with complaint data (must have geometry)
        clusters: List of cluster dicts from DBSCAN with {cluster_id, centroid, size, items}

    Returns:
        List of classified HotspotClassifier objects
    """
    if clusters is None:
        clusters = []

    engine = HotspotClassificationEngine()
    classifiers = []

    for cluster in clusters:
        cluster_id = cluster.get("cluster_id", "unknown")
        centroid = cluster.get("centroid", (0, 0))
        items = cluster.get("items", [])

        # Determine event types in cluster
        event_types = []
        event_count = len(items)

        if violations_df is not None and event_count > 0:
            event_types.append("violation")
        if complaints_df is not None and event_count > 0:
            event_types.append("complaint")

        # Estimate density (events per sq km)
        # Rough estimate: cluster radius ~200m = 0.126 sq km
        cluster_area_sqkm = 0.126
        density = event_count / max(0.01, cluster_area_sqkm)

        # Recent event count (last 7 days) - simplified estimate
        recent_count = max(1, int(event_count * 0.2))

        # Trend estimation (simplified: based on recent count proportion)
        if recent_count > event_count * 0.25:
            trend = Trend.GROWING
            trend_pct = 0.25
        elif recent_count < event_count * 0.15:
            trend = Trend.SHRINKING
            trend_pct = -0.25
        else:
            trend = Trend.STABLE
            trend_pct = 0.0

        # Estimated personnel (1 person per 5 daily incidents)
        estimated_daily = max(1, event_count // 30)
        personnel = max(1, estimated_daily // 5)

        # Resource efficiency (0-1, higher is better)
        efficiency = min(1.0, personnel / max(0.1, event_count / 100))

        metrics = HotspotMetrics(
            hotspot_id=f"HS_{cluster_id}",
            latitude=centroid[1],
            longitude=centroid[0],
            density_per_sqkm=density,
            event_count=event_count,
            recent_event_count=recent_count,
            event_types=event_types,
            trend_direction=trend,
            trend_pct_change=trend_pct,
            estimated_personnel=personnel,
            resource_efficiency=efficiency,
        )

        classifier = engine.classify(metrics, len(clusters))
        classifiers.append(classifier)

    # Rank all hotspots
    ranked = engine.rank_hotspots(classifiers)
    return ranked
