"""
Complaint Response Classifier for 311 Complaint Analysis.

Classifies 311 complaints and their response lifecycle into:
- Category (SIDEWALK_DAMAGE, HAZARD, DRAINAGE, DEBRIS, OTHER)
- Urgency (EMERGENCY, HIGH, MEDIUM, LOW)
- Response Status (RESOLVED, PENDING, DELAYED, ABANDONED)
- Time Adequacy (FAST, ON_TIME, SLOW, VERY_SLOW) — relative to SLA targets

Scoring:
- Category severity: Maps complaint type to inherent priority
- Urgency: Inferred from description and location precision
- Response status: Tracked from complaint open → inspection → resolution
- Time adequacy: Compares actual response/resolution time vs. SLA targets
  - SLA targets: EMERGENCY (1d), HIGH (3d), MEDIUM (7d), LOW (14d)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComplaintCategory(str, Enum):
    """311 complaint type classification."""
    SIDEWALK_DAMAGE = "SIDEWALK_DAMAGE"
    HAZARD = "HAZARD"
    DRAINAGE = "DRAINAGE"
    DEBRIS = "DEBRIS"
    OTHER = "OTHER"

class ComplaintUrgency(str, Enum):
    """Urgency tier based on severity and risk."""
    EMERGENCY = "EMERGENCY"  # Imminent safety risk
    HIGH = "HIGH"            # Significant problem, high impact
    MEDIUM = "MEDIUM"        # Moderate problem
    LOW = "LOW"              # Minor issue, low risk

class ResponseStatus(str, Enum):
    """Lifecycle status of complaint response."""
    RESOLVED = "RESOLVED"    # Complaint closed, work completed
    PENDING = "PENDING"      # Awaiting action (< SLA)
    DELAYED = "DELAYED"      # Past SLA, still open
    ABANDONED = "ABANDONED"  # No action taken, exceeded threshold

class TimeAdequacy(str, Enum):
    """Assessment of response timing vs. SLA."""
    FAST = "FAST"            # Resolved well before SLA
    ON_TIME = "ON_TIME"      # Resolved within SLA
    SLOW = "SLOW"            # Resolved after SLA (< 150% SLA)
    VERY_SLOW = "VERY_SLOW"  # Resolved > 150% of SLA or abandoned

@dataclass
class ComplaintMetrics:
    """Raw metrics for a single 311 complaint."""
    complaint_id: str
    description: str | None = None
    location_descriptor: str | None = None
    borough: str | None = None

    # Timing (days since complaint)
    days_open: float = 0.0
    days_to_inspection: float | None = None
    days_to_resolution: float | None = None

    # Status flags
    has_location_details: bool = False
    is_resolved: bool = False
    is_duplicate: bool = False
    is_reopened: bool = False

    # Metadata
    data_quality_flag: str = ""  # "LOW", "MEDIUM", "HIGH"
    sample_size: int = 0

@dataclass
class ComplaintResponseClassification:
    """Classification result for a 311 complaint."""
    complaint_id: str
    description: str | None = None
    borough: str | None = None

    # Classification
    category: ComplaintCategory
    urgency: ComplaintUrgency
    response_status: ResponseStatus
    time_adequacy: TimeAdequacy

    # Scores (0-100)
    category_severity_score: float = 0.0    # Inherent severity
    urgency_score: float = 0.0               # Inferred urgency
    response_timeliness_score: float = 0.0  # Response timing
    overall_satisfaction_score: float = 0.0 # Overall adequacy

    # Metrics (for reference)
    metrics: ComplaintMetrics | None = None

    # Recommendations
    flagged_issues: list[str] = field(default_factory=list)
    next_action: str = ""
    sla_target_days: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "complaint_id": self.complaint_id,
            "description": self.description,
            "borough": self.borough,
            "category": self.category.value,
            "urgency": self.urgency.value,
            "response_status": self.response_status.value,
            "time_adequacy": self.time_adequacy.value,
            "category_severity_score": round(self.category_severity_score, 1),
            "urgency_score": round(self.urgency_score, 1),
            "response_timeliness_score": round(self.response_timeliness_score, 1),
            "overall_satisfaction_score": round(self.overall_satisfaction_score, 1),
            "flagged_issues": self.flagged_issues,
            "next_action": self.next_action,
            "sla_target_days": self.sla_target_days,
        }

class ComplaintResponseClassifier:
    """
    311 complaint response classifier.

    Classifies complaints by category, urgency, response status, and time adequacy.
    Computes SLA compliance and identifies bottlenecks in response pipeline.
    """

    # Category severity scores (0-100)
    CATEGORY_SEVERITY = {
        ComplaintCategory.HAZARD: 80,       # Safety risk
        ComplaintCategory.SIDEWALK_DAMAGE: 60,
        ComplaintCategory.DRAINAGE: 55,
        ComplaintCategory.DEBRIS: 35,
        ComplaintCategory.OTHER: 40,
    }

    # SLA targets (days) by urgency
    SLA_TARGETS = {
        ComplaintUrgency.EMERGENCY: 1.0,   # 24 hours
        ComplaintUrgency.HIGH: 3.0,        # 3 days
        ComplaintUrgency.MEDIUM: 7.0,      # 1 week
        ComplaintUrgency.LOW: 14.0,        # 2 weeks
    }

    # Keywords for category detection
    CATEGORY_KEYWORDS = {
        ComplaintCategory.SIDEWALK_DAMAGE: [
            "sidewalk", "pavement", "concrete", "crack", "broken", "damaged",
            "trip hazard", "uneven", "pothole", "surface"
        ],
        ComplaintCategory.HAZARD: [
            "hazard", "dangerous", "unsafe", "risk", "injury", "exposed",
            "broken glass", "sharp", "protruding", "unstable"
        ],
        ComplaintCategory.DRAINAGE: [
            "drain", "water", "flood", "wet", "puddle", "standing water",
            "drainage", "gutter", "sewer", "clogged"
        ],
        ComplaintCategory.DEBRIS: [
            "debris", "trash", "garbage", "litter", "dirt", "dust",
            "fallen", "branches", "leaves", "mess"
        ],
    }

    # Keywords for urgency inference
    URGENCY_KEYWORDS = {
        ComplaintUrgency.EMERGENCY: [
            "imminent", "emergency", "critical", "life", "death", "risk",
            "children", "injured", "urgent", "immediate"
        ],
        ComplaintUrgency.HIGH: [
            "serious", "significant", "major", "important", "impede",
            "block", "prevent", "difficult"
        ],
    }

    def classify(
        self,
        metrics: ComplaintMetrics,
        sla_thresholds: dict[str, int] | None = None,
    ) -> ComplaintResponseClassification:
        """
        Classify complaint response.

        Args:
            metrics: Complaint metrics
            sla_thresholds: SLA config {HIGH: 14, MEDIUM: 30, LOW: 60} (default: internal SLA_TARGETS)

        Returns:
            ComplaintResponseClassification with category, urgency, status, and timing
        """
        if not metrics or not metrics.complaint_id:
            return self._create_no_data_classification(metrics)

        # Infer category from description
        category = self._infer_category(metrics.description)

        # Infer urgency from description, category, and location
        urgency = self._infer_urgency(metrics.description, category, metrics.location_descriptor)

        # Determine response status
        response_status = self._determine_response_status(metrics, urgency)

        # Assess time adequacy
        time_adequacy = self._assess_time_adequacy(metrics, urgency)

        # Score dimensions
        category_severity = self.CATEGORY_SEVERITY.get(category, 40.0)
        urgency_score = self._score_urgency(urgency)
        response_timeliness = self._score_response_timeliness(metrics, urgency, response_status)

        # Composite satisfaction score
        overall_score = (
            category_severity * 0.25 +
            urgency_score * 0.30 +
            response_timeliness * 0.45
        )

        # SLA target
        sla_target = self.SLA_TARGETS.get(urgency, 14.0)

        # Identify flagged issues
        flagged_issues = self._identify_issues(metrics, urgency, response_status, time_adequacy)

        # Recommend next action
        next_action = self._recommend_action(response_status, time_adequacy, urgency)

        return ComplaintResponseClassification(
            complaint_id=metrics.complaint_id,
            description=metrics.description,
            borough=metrics.borough,
            category=category,
            urgency=urgency,
            response_status=response_status,
            time_adequacy=time_adequacy,
            category_severity_score=category_severity,
            urgency_score=urgency_score,
            response_timeliness_score=response_timeliness,
            overall_satisfaction_score=overall_score,
            metrics=metrics,
            flagged_issues=flagged_issues,
            next_action=next_action,
            sla_target_days=sla_target,
        )

    def _infer_category(self, description: str | None) -> ComplaintCategory:
        """Infer category from complaint description."""
        if not description:
            return ComplaintCategory.OTHER

        desc_lower = description.lower()

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return category

        return ComplaintCategory.OTHER

    def _infer_urgency(
        self,
        description: str | None,
        category: ComplaintCategory,
        location_descriptor: str | None,
    ) -> ComplaintUrgency:
        """Infer urgency from description, category, and location."""
        if not description:
            # Default based on category
            if category in [ComplaintCategory.HAZARD, ComplaintCategory.SIDEWALK_DAMAGE]:
                return ComplaintUrgency.MEDIUM
            return ComplaintUrgency.LOW

        desc_lower = description.lower()

        # Check for emergency keywords
        for keyword in self.URGENCY_KEYWORDS[ComplaintUrgency.EMERGENCY]:
            if keyword in desc_lower:
                return ComplaintUrgency.EMERGENCY

        # Check for high urgency keywords
        for keyword in self.URGENCY_KEYWORDS[ComplaintUrgency.HIGH]:
            if keyword in desc_lower:
                return ComplaintUrgency.HIGH

        # Category-based default
        if category == ComplaintCategory.HAZARD:
            return ComplaintUrgency.HIGH
        elif category == ComplaintCategory.SIDEWALK_DAMAGE:
            return ComplaintUrgency.MEDIUM
        elif category == ComplaintCategory.DRAINAGE:
            return ComplaintUrgency.MEDIUM
        else:
            return ComplaintUrgency.LOW

    def _determine_response_status(
        self, metrics: ComplaintMetrics, urgency: ComplaintUrgency
    ) -> ResponseStatus:
        """Determine response status based on resolution and SLA."""
        if metrics.is_resolved:
            return ResponseStatus.RESOLVED

        sla_days = self.SLA_TARGETS.get(urgency, 14.0)
        threshold_days = sla_days * 1.5  # Allow 50% overage before "abandoned"

        if metrics.days_open > threshold_days:
            return ResponseStatus.ABANDONED
        elif metrics.days_open > sla_days:
            return ResponseStatus.DELAYED
        else:
            return ResponseStatus.PENDING

    def _assess_time_adequacy(
        self, metrics: ComplaintMetrics, urgency: ComplaintUrgency
    ) -> TimeAdequacy:
        """Assess timing of response/resolution."""
        if not metrics.is_resolved:
            # Use current open time
            days = metrics.days_open
        else:
            # Use resolution time
            days = metrics.days_to_resolution or metrics.days_open

        if days is None or days < 0:
            return TimeAdequacy.SLOW

        sla_target = self.SLA_TARGETS.get(urgency, 14.0)

        if days < sla_target * 0.5:
            return TimeAdequacy.FAST
        elif days <= sla_target:
            return TimeAdequacy.ON_TIME
        elif days <= sla_target * 1.5:
            return TimeAdequacy.SLOW
        else:
            return TimeAdequacy.VERY_SLOW

    def _score_urgency(self, urgency: ComplaintUrgency) -> float:
        """Score urgency (0-100)."""
        scores = {
            ComplaintUrgency.EMERGENCY: 95.0,
            ComplaintUrgency.HIGH: 75.0,
            ComplaintUrgency.MEDIUM: 50.0,
            ComplaintUrgency.LOW: 25.0,
        }
        return scores.get(urgency, 50.0)

    def _score_response_timeliness(
        self,
        metrics: ComplaintMetrics,
        urgency: ComplaintUrgency,
        status: ResponseStatus,
    ) -> float:
        """Score response timeliness (0-100)."""
        sla_days = self.SLA_TARGETS.get(urgency, 14.0)

        # Days to inspect (if available)
        if metrics.days_to_inspection is not None and metrics.days_to_inspection >= 0:
            insp_days = metrics.days_to_inspection
        else:
            # Use days open as proxy
            insp_days = metrics.days_open

        # Score based on status and time
        if status == ResponseStatus.RESOLVED:
            # Resolution within SLA = 90-100
            if metrics.days_to_resolution and metrics.days_to_resolution <= sla_days:
                return 95.0
            elif metrics.days_to_resolution and metrics.days_to_resolution <= sla_days * 1.5:
                return 70.0
            else:
                return 40.0
        elif status == ResponseStatus.PENDING:
            # Still open but within SLA = 70-80
            return 75.0
        elif status == ResponseStatus.DELAYED:
            # Past SLA = 30-50
            return 40.0
        else:  # ABANDONED
            return 10.0

    def _identify_issues(
        self,
        metrics: ComplaintMetrics,
        urgency: ComplaintUrgency,
        status: ResponseStatus,
        time_adequacy: TimeAdequacy,
    ) -> list[str]:
        """Identify flagged issues."""
        issues = []

        if status == ResponseStatus.ABANDONED:
            issues.append("CRITICAL: Complaint abandoned (no inspection)")

        if status == ResponseStatus.DELAYED:
            issues.append(f"URGENT: Response overdue by {max(0, metrics.days_open - self.SLA_TARGETS.get(urgency, 14.0)):.0f} days")

        if time_adequacy == TimeAdequacy.VERY_SLOW:
            issues.append("Resolution significantly delayed (> 150% of SLA)")

        if not metrics.has_location_details:
            issues.append("Missing location details — may slow inspection dispatch")

        if metrics.is_reopened:
            issues.append("Complaint reopened — previous resolution incomplete")

        if metrics.is_duplicate:
            issues.append("Duplicate complaint detected")

        return issues

    def _recommend_action(
        self, status: ResponseStatus, time_adequacy: TimeAdequacy, urgency: ComplaintUrgency
    ) -> str:
        """Recommend next action."""
        if status == ResponseStatus.ABANDONED:
            return "ESCALATE: Immediately assign inspector and track"
        elif status == ResponseStatus.DELAYED:
            return "PRIORITIZE: Expedite inspection, update requester"
        elif time_adequacy == TimeAdequacy.VERY_SLOW:
            return "REVIEW: Investigate delay, consider resource reallocation"
        elif status == ResponseStatus.PENDING and urgency == ComplaintUrgency.EMERGENCY:
            return "DISPATCH: Send inspector within 24 hours"
        elif status == ResponseStatus.RESOLVED:
            return "MONITOR: Track for reopens, collect feedback"
        else:
            return "CONTINUE: Standard tracking"

    def _create_no_data_classification(self, metrics: ComplaintMetrics | None) -> ComplaintResponseClassification:
        """Create a no-data classification."""
        m = metrics or ComplaintMetrics(complaint_id="UNKNOWN")
        return ComplaintResponseClassification(
            complaint_id=m.complaint_id,
            description=None,
            borough=None,
            category=ComplaintCategory.OTHER,
            urgency=ComplaintUrgency.LOW,
            response_status=ResponseStatus.PENDING,
            time_adequacy=TimeAdequacy.SLOW,
            category_severity_score=0.0,
            urgency_score=0.0,
            response_timeliness_score=0.0,
            overall_satisfaction_score=0.0,
            flagged_issues=["Insufficient data"],
            next_action="Request missing complaint details",
            sla_target_days=14.0,
        )
