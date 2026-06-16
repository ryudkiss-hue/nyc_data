"""
SLA Status Classifier - Dataset Freshness & Compliance Classification

Classifies datasets against SLA tiers (HIGH 14d, MEDIUM 30d, LOW 60d) and determines
compliance status, root causes, and trend direction. Designed for integration with
sla_compliance_workflow.py LangGraph orchestration.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

class SLATier(Enum):
    """SLA tiers based on dataset freshness requirements."""
    HIGH = 14  # Critical datasets, updated within 14 days
    MEDIUM = 30  # Standard datasets, updated within 30 days
    LOW = 60  # Archive datasets, updated within 60 days

class ComplianceStatus(Enum):
    """Dataset compliance status vs SLA tier."""
    COMPLIANT = "compliant"  # Data within SLA threshold
    AT_RISK = "at_risk"  # Data within 80% of SLA (e.g., 11d of 14d)
    BREACHED = "breached"  # Data exceeds SLA threshold

class RootCause(Enum):
    """Root cause classification for SLA breaches."""
    API_DOWN = "api_down"  # API unreachable or returning errors
    MAINTENANCE = "maintenance"  # Scheduled or emergency maintenance window
    DATA_QUALITY = "data_quality"  # Publisher-side data quality issues
    RESOURCE_CONSTRAINT = "resource_constraint"  # Socrata quota/rate limits
    UNKNOWN = "unknown"  # Unable to determine cause

class TrendDirection(Enum):
    """Trend in compliance status over recent history."""
    IMPROVING = "improving"  # Freshness getting better
    STABLE = "stable"  # Consistent freshness
    DEGRADING = "degrading"  # Freshness getting worse
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough historical data

@dataclass
class SLAMetricSnapshot:
    """Single point-in-time SLA measurement."""
    timestamp: datetime
    dataset_key: str
    fourfour: str
    last_modified: datetime
    row_count: int
    sla_tier: SLATier
    days_since_update: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "dataset_key": self.dataset_key,
            "fourfour": self.fourfour,
            "last_modified": self.last_modified.isoformat(),
            "row_count": self.row_count,
            "sla_tier": self.sla_tier.name,
            "days_since_update": round(self.days_since_update, 2),
        }

@dataclass
class SLAStatusRecord:
    """Complete SLA status for a single dataset."""
    dataset_key: str
    fourfour: str
    sla_tier: SLATier
    compliance_status: ComplianceStatus
    days_since_update: float
    sla_threshold_days: int
    freshness_percentage: float
    root_cause: RootCause
    confidence: float
    trend: TrendDirection
    last_measured: datetime
    historical_days_since_update: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_key": self.dataset_key,
            "fourfour": self.fourfour,
            "sla_tier": self.sla_tier.name,
            "compliance_status": self.compliance_status.value,
            "days_since_update": round(self.days_since_update, 2),
            "sla_threshold_days": self.sla_threshold_days,
            "freshness_percentage": round(self.freshness_percentage, 1),
            "root_cause": self.root_cause.value,
            "confidence": round(self.confidence, 2),
            "trend": self.trend.value,
            "last_measured": self.last_measured.isoformat(),
            "historical_days_since_update": [round(d, 2) for d in self.historical_days_since_update],
        }

@dataclass
class SLAComplianceReport:
    """Aggregate SLA compliance across all datasets."""
    timestamp: datetime
    total_datasets: int
    compliant_count: int
    at_risk_count: int
    breached_count: int
    overall_compliance_pct: float
    critical_breaches: list[str] = field(default_factory=list)
    by_tier: dict[str, dict[str, int]] = field(default_factory=dict)
    records: list[SLAStatusRecord] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    claude_analysis: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_datasets": self.total_datasets,
            "compliant_count": self.compliant_count,
            "at_risk_count": self.at_risk_count,
            "breached_count": self.breached_count,
            "overall_compliance_pct": round(self.overall_compliance_pct, 1),
            "critical_breaches": self.critical_breaches,
            "by_tier": self.by_tier,
            "records": [r.to_dict() for r in self.records],
            "recommendations": self.recommendations,
            "claude_analysis": self.claude_analysis,
        }

class SLAStatusClassifier:
    """Classifies dataset freshness against SLA tiers."""

    def __init__(self, at_risk_threshold_pct: float = 0.80):
        self.at_risk_threshold_pct = at_risk_threshold_pct
        logger.info(f"Initialized SLAStatusClassifier (at_risk_threshold={at_risk_threshold_pct*100}%)")

    def classify(
        self,
        snapshot: SLAMetricSnapshot,
        historical_snapshots: list[SLAMetricSnapshot] | None = None,
        error_context: dict[str, Any] | None = None,
    ) -> SLAStatusRecord:
        """Classify dataset freshness status."""
        sla_threshold = snapshot.sla_tier.value
        freshness_pct = (sla_threshold - snapshot.days_since_update) / sla_threshold * 100

        if snapshot.days_since_update <= sla_threshold:
            usage_pct = (snapshot.days_since_update / sla_threshold) * 100
            if usage_pct >= (self.at_risk_threshold_pct * 100):
                compliance_status = ComplianceStatus.AT_RISK
            else:
                compliance_status = ComplianceStatus.COMPLIANT
        else:
            compliance_status = ComplianceStatus.BREACHED

        root_cause, confidence = self._classify_root_cause(snapshot, compliance_status, error_context)
        trend = self._detect_trend(snapshot, historical_snapshots)

        record = SLAStatusRecord(
            dataset_key=snapshot.dataset_key,
            fourfour=snapshot.fourfour,
            sla_tier=snapshot.sla_tier,
            compliance_status=compliance_status,
            days_since_update=snapshot.days_since_update,
            sla_threshold_days=sla_threshold,
            freshness_percentage=freshness_pct,
            root_cause=root_cause,
            confidence=confidence,
            trend=trend,
            last_measured=snapshot.timestamp,
            historical_days_since_update=(
                [s.days_since_update for s in historical_snapshots[:7]]
                if historical_snapshots else []
            ),
        )

        logger.debug(f"Classified {snapshot.dataset_key}: {compliance_status.value} ({freshness_pct:.1f}%)")
        return record

    def _classify_root_cause(
        self,
        snapshot: SLAMetricSnapshot,
        status: ComplianceStatus,
        error_context: dict[str, Any] | None = None,
    ) -> tuple[RootCause, float]:
        if status == ComplianceStatus.COMPLIANT:
            return RootCause.UNKNOWN, 1.0

        if error_context:
            if error_context.get("api_error"):
                return RootCause.API_DOWN, 0.9
            if error_context.get("maintenance_window"):
                return RootCause.MAINTENANCE, 0.95
            if error_context.get("quality_issue"):
                return RootCause.DATA_QUALITY, 0.85
            if error_context.get("rate_limited"):
                return RootCause.RESOURCE_CONSTRAINT, 0.9

        if snapshot.sla_tier == SLATier.HIGH:
            return RootCause.API_DOWN, 0.6
        elif snapshot.sla_tier == SLATier.LOW:
            return RootCause.UNKNOWN, 0.3

        return RootCause.UNKNOWN, 0.5

    def _detect_trend(
        self,
        snapshot: SLAMetricSnapshot,
        historical_snapshots: list[SLAMetricSnapshot] | None = None,
    ) -> TrendDirection:
        if not historical_snapshots or len(historical_snapshots) < 2:
            return TrendDirection.INSUFFICIENT_DATA

        recent = [snapshot] + historical_snapshots[:2]
        days_values = [s.days_since_update for s in recent]

        if len(days_values) >= 3:
            # improvement = current - oldest (negative = fresher = better)
            improvement = days_values[0] - days_values[-1]
            if improvement < -1.0:  # Getting fresher by >1 day
                return TrendDirection.IMPROVING
            elif improvement > 1.0:  # Getting staler by >1 day
                return TrendDirection.DEGRADING
            else:
                return TrendDirection.STABLE

        return TrendDirection.INSUFFICIENT_DATA

    def compile_report(
        self,
        records: list[SLAStatusRecord],
        claude_analysis: str = "",
    ) -> SLAComplianceReport:
        """Compile SLA status records into aggregate report."""
        compliant = sum(1 for r in records if r.compliance_status == ComplianceStatus.COMPLIANT)
        at_risk = sum(1 for r in records if r.compliance_status == ComplianceStatus.AT_RISK)
        breached = sum(1 for r in records if r.compliance_status == ComplianceStatus.BREACHED)
        total = len(records)

        critical = [
            r.dataset_key for r in records
            if r.sla_tier == SLATier.HIGH and r.compliance_status == ComplianceStatus.BREACHED
        ]

        by_tier = {}
        for tier in SLATier:
            tier_records = [r for r in records if r.sla_tier == tier]
            if tier_records:
                by_tier[tier.name] = {
                    "total": len(tier_records),
                    "compliant": sum(1 for r in tier_records if r.compliance_status == ComplianceStatus.COMPLIANT),
                    "at_risk": sum(1 for r in tier_records if r.compliance_status == ComplianceStatus.AT_RISK),
                    "breached": sum(1 for r in tier_records if r.compliance_status == ComplianceStatus.BREACHED),
                }

        compliance_pct = (compliant / total * 100) if total > 0 else 100

        report = SLAComplianceReport(
            timestamp=datetime.now(timezone.utc),
            total_datasets=total,
            compliant_count=compliant,
            at_risk_count=at_risk,
            breached_count=breached,
            overall_compliance_pct=compliance_pct,
            critical_breaches=critical,
            by_tier=by_tier,
            records=records,
            claude_analysis=claude_analysis,
        )

        logger.info(
            f"Compiled SLA report: {compliant}/{total} compliant ({compliance_pct:.1f}%), "
            f"{len(critical)} critical breaches"
        )
        return report

