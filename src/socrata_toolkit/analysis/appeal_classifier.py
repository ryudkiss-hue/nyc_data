"""
Appeal & Reinspection Outcome Classifier

Deterministic spaCy-based classifier for extracting appeal outcomes, reasons,
and inspector performance signals from reinspection and dismissal records.

Key classifications:
  - Resolution: UPHELD, OVERTURNED, MODIFIED
  - Reason: PROCEDURAL_ERROR, NEW_EVIDENCE, JUDGMENT_CALL, ADMINISTRATIVE
  - Inspector Consistency: NORMAL, OUTLIER
  - Trend: IMPROVING, STABLE, DEGRADING
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd
import spacy
from spacy.language import Language
from spacy.tokens import Doc

logger = logging.getLogger(__name__)

class AppealResolution(Enum):
    """Outcome of appeal/reinspection."""
    UPHELD = "upheld"  # Original inspection decision confirmed
    OVERTURNED = "overturned"  # Original decision reversed
    MODIFIED = "modified"  # Partial modification to original finding
    INCONCLUSIVE = "inconclusive"  # No clear resolution

class AppealReason(Enum):
    """Reason for appeal reversal or modification."""
    PROCEDURAL_ERROR = "procedural_error"  # Inspector error in process
    NEW_EVIDENCE = "new_evidence"  # New facts/repairs made
    JUDGMENT_CALL = "judgment_call"  # Disagreement on interpretation
    ADMINISTRATIVE = "administrative"  # Clerical/process issue
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # Lack of documentation

class InspectorConsistency(Enum):
    """Inspector performance consistency signal."""
    NORMAL = "normal"  # Consistent with peer group
    OUTLIER_HIGH = "outlier_high"  # Unusually high overturn rate
    OUTLIER_LOW = "outlier_low"  # Unusually low overturn rate
    UNRELIABLE = "unreliable"  # Extreme variance

class PerformanceTrend(Enum):
    """Inspector performance trend over time."""
    IMPROVING = "improving"  # Fewer overturns over time
    STABLE = "stable"  # Consistent performance
    DEGRADING = "degrading"  # More overturns over time
    INSUFFICIENT_DATA = "insufficient_data"  # <5 appeals in period

@dataclass
class AppealClassificationResult:
    """Result of appeal outcome classification."""
    original_text: str
    resolution: AppealResolution
    resolution_confidence: float  # 0-100
    reason: AppealReason
    reason_confidence: float  # 0-100
    consistency_signal: InspectorConsistency
    keywords_matched: list[str]
    extracted_entities: list[tuple[str, str]]  # (text, label)
    details: dict  # Additional context

@dataclass
class InspectorAppealStats:
    """Aggregated appeal statistics for a single inspector."""
    inspector_id: str
    inspector_name: str
    total_inspections: int
    total_appeals: int
    appeal_rate: float  # 0-1 (appeals / total inspections)
    overturn_rate: float  # 0-1 (overturned / appeals)
    modification_rate: float  # 0-1 (modified / appeals)
    upheld_rate: float  # 0-1 (upheld / appeals)
    appeal_count_by_reason: dict[str, int]
    recent_trend: PerformanceTrend
    reliability: str  # "high" | "medium" | "low" (based on sample size)
    coaching_needed: bool
    coaching_reason: Optional[str]

class AppealOutcomeClassifier:
    """Classify appeal outcomes, reasons, and inspector consistency signals."""

    # Resolution indicators
    RESOLUTION_KEYWORDS = {
        AppealResolution.UPHELD: {
            "keywords": ["upheld", "sustained", "confirmed", "valid", "correct",
                        "affirmed", "stands", "justified", "appropriate", "defensible"],
            "confidence_base": 85,
        },
        AppealResolution.OVERTURNED: {
            "keywords": ["overturned", "reversed", "vacated", "dismissed", "invalid",
                        "withdrawn", "cancelled", "error", "incorrect", "unjustified"],
            "confidence_base": 85,
        },
        AppealResolution.MODIFIED: {
            "keywords": ["modified", "adjusted", "partial", "partially upheld",
                        "partial reversal", "partially sustained", "amended"],
            "confidence_base": 80,
        },
    }

    # Appeal reason indicators
    REASON_KEYWORDS = {
        AppealReason.PROCEDURAL_ERROR: {
            "keywords": ["procedure", "procedural", "improper", "failed to",
                        "did not follow", "violation of", "error in process",
                        "not recorded", "documentation missing"],
            "confidence_base": 75,
        },
        AppealReason.NEW_EVIDENCE: {
            "keywords": ["new evidence", "repairs made", "fixed", "corrected",
                        "condition improved", "remedied", "completed", "installed",
                        "repaired", "evidence of repair"],
            "confidence_base": 80,
        },
        AppealReason.JUDGMENT_CALL: {
            "keywords": ["judgment", "subjective", "interpretation", "disagreement",
                        "opinion", "standard", "severity", "discretion", "professional judgment"],
            "confidence_base": 70,
        },
        AppealReason.ADMINISTRATIVE: {
            "keywords": ["administrative", "clerical", "administrative error",
                        "paperwork", "filing", "records"],
            "confidence_base": 75,
        },
        AppealReason.INSUFFICIENT_EVIDENCE: {
            "keywords": ["insufficient evidence", "lack of evidence", "not documented",
                        "unclear", "ambiguous", "not substantiated"],
            "confidence_base": 75,
        },
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize classifier with spaCy model."""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(f"Model {model_name} not found. Install with: python -m spacy download {model_name}")
            raise

        self._add_appeal_components()

    def _add_appeal_components(self):
        """Add custom spaCy extensions for appeal classification."""
        if not Doc.has_extension("appeal_resolution"):
            Doc.set_extension("appeal_resolution", default=None)
        if not Doc.has_extension("appeal_reason"):
            Doc.set_extension("appeal_reason", default=None)
        if not Doc.has_extension("consistency_signal"):
            Doc.set_extension("consistency_signal", default=None)

    def classify(self, text: str) -> AppealClassificationResult:
        """
        Classify an appeal/reinspection outcome.

        Args:
            text: Appeal decision or reinspection notes

        Returns:
            AppealClassificationResult with resolution, reason, and consistency
        """
        doc = self.nlp(text)
        text_lower = text.lower()

        # Classify resolution
        resolution, res_conf = self._classify_resolution(text_lower)
        reason, reason_conf = self._classify_reason(text_lower)
        matched_keywords = self._extract_matched_keywords(text_lower)
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        details = {
            "resolution": resolution.value,
            "reason": reason.value,
            "entity_count": len(entities),
            "text_length": len(text_lower.split()),
        }

        return AppealClassificationResult(
            original_text=text,
            resolution=resolution,
            resolution_confidence=res_conf,
            reason=reason,
            reason_confidence=reason_conf,
            consistency_signal=InspectorConsistency.NORMAL,  # Set per-inspector in stats calculation
            keywords_matched=matched_keywords,
            extracted_entities=entities,
            details=details
        )

    def _classify_resolution(self, text_lower: str) -> tuple[AppealResolution, float]:
        """Determine appeal resolution (upheld/overturned/modified)."""
        scores = {}

        for resolution, config in self.RESOLUTION_KEYWORDS.items():
            score = sum(1 for kw in config["keywords"] if kw in text_lower)
            if score > 0:
                scores[resolution] = score

        if not scores:
            return AppealResolution.INCONCLUSIVE, 0

        primary_resolution = max(scores, key=scores.get)
        base_conf = self.RESOLUTION_KEYWORDS[primary_resolution]["confidence_base"]
        # Boost confidence for multiple keyword matches
        match_boost = min(20, scores[primary_resolution] * 5)
        confidence = min(100, base_conf + match_boost)

        return primary_resolution, confidence

    def _classify_reason(self, text_lower: str) -> tuple[AppealReason, float]:
        """Determine appeal reason (procedural_error/new_evidence/etc)."""
        scores = {}

        for reason, config in self.REASON_KEYWORDS.items():
            score = sum(1 for kw in config["keywords"] if kw in text_lower)
            if score > 0:
                scores[reason] = score

        if not scores:
            return AppealReason.ADMINISTRATIVE, 30  # Default to administrative

        primary_reason = max(scores, key=scores.get)
        base_conf = self.REASON_KEYWORDS[primary_reason]["confidence_base"]
        match_boost = min(20, scores[primary_reason] * 5)
        confidence = min(100, base_conf + match_boost)

        return primary_reason, confidence

    def _extract_matched_keywords(self, text_lower: str) -> list[str]:
        """Extract all matched keywords from text."""
        matched = []
        for resolution_config in self.RESOLUTION_KEYWORDS.values():
            matched.extend([kw for kw in resolution_config["keywords"] if kw in text_lower])
        for reason_config in self.REASON_KEYWORDS.values():
            matched.extend([kw for kw in reason_config["keywords"] if kw in text_lower])
        return list(set(matched))

    def batch_classify(self, texts: list[str]) -> list[AppealClassificationResult]:
        """Classify multiple appeal texts."""
        return [self.classify(text) for text in texts]

class InspectorAppealAnalyzer:
    """
    Analyze inspector performance through appeal/overturn patterns.

    Combines appeal classification with inspector-level statistics to identify:
    - High overturn rate outliers (need coaching)
    - Systematic procedural errors
    - Quality trends (improving/degrading)
    """

    def __init__(self, classifier: Optional[AppealOutcomeClassifier] = None):
        """Initialize with classifier."""
        self.classifier = classifier or AppealOutcomeClassifier()

    def compute_inspector_stats(
        self,
        appeals_df: pd.DataFrame,
        inspector_id_col: str = "inspector_id",
        inspector_name_col: str = "inspector_name",
        outcome_col: str = "appeal_decision",
        date_col: str = "created_date",
    ) -> dict[str, InspectorAppealStats]:
        """
        Compute appeal statistics by inspector.

        Args:
            appeals_df: DataFrame with appeals/reinspections
            inspector_id_col: Column name for inspector ID
            inspector_name_col: Column name for inspector name
            outcome_col: Column name for appeal decision text
            date_col: Column name for date (for trend analysis)

        Returns:
            Dict mapping inspector_id -> InspectorAppealStats
        """
        inspector_stats = {}

        # Classify all appeals
        classifications = self.classifier.batch_classify(
            appeals_df[outcome_col].fillna("").astype(str).tolist()
        )
        appeals_df["_appeal_resolution"] = [c.resolution for c in classifications]
        appeals_df["_appeal_reason"] = [c.reason for c in classifications]

        # Group by inspector
        for inspector_id, group in appeals_df.groupby(inspector_id_col):
            inspector_name = group[inspector_name_col].iloc[0]
            total_appeals = len(group)

            # Count resolutions
            upheld_count = (group["_appeal_resolution"] == AppealResolution.UPHELD).sum()
            overturned_count = (group["_appeal_resolution"] == AppealResolution.OVERTURNED).sum()
            modified_count = (group["_appeal_resolution"] == AppealResolution.MODIFIED).sum()

            # Rates
            upheld_rate = upheld_count / total_appeals if total_appeals > 0 else 0
            overturn_rate = overturned_count / total_appeals if total_appeals > 0 else 0
            modification_rate = modified_count / total_appeals if total_appeals > 0 else 0

            # Reason breakdown
            reason_counts = group["_appeal_reason"].value_counts().to_dict()

            # Compute trend (last 3 months vs previous)
            if date_col in group.columns:
                group_sorted = group.sort_values(date_col)
                mid_point = len(group_sorted) // 2
                recent = group_sorted.iloc[mid_point:]["_appeal_resolution"] == AppealResolution.OVERTURNED
                earlier = group_sorted.iloc[:mid_point]["_appeal_resolution"] == AppealResolution.OVERTURNED

                recent_overturn_rate = recent.mean() if len(recent) > 0 else 0
                earlier_overturn_rate = earlier.mean() if len(earlier) > 0 else 0

                if total_appeals < 5:
                    trend = PerformanceTrend.INSUFFICIENT_DATA
                elif recent_overturn_rate < earlier_overturn_rate * 0.8:
                    trend = PerformanceTrend.IMPROVING
                elif recent_overturn_rate > earlier_overturn_rate * 1.2:
                    trend = PerformanceTrend.DEGRADING
                else:
                    trend = PerformanceTrend.STABLE
            else:
                trend = PerformanceTrend.INSUFFICIENT_DATA

            # Reliability (sample size)
            if total_appeals >= 20:
                reliability = "high"
            elif total_appeals >= 10:
                reliability = "medium"
            else:
                reliability = "low"

            # Determine if coaching needed
            coaching_needed = False
            coaching_reason = None

            if overturn_rate > 0.3:  # >30% overturn rate is concerning
                coaching_needed = True
                coaching_reason = f"High overturn rate: {overturn_rate:.1%} ({overturned_count}/{total_appeals})"
            elif trend == PerformanceTrend.DEGRADING:
                coaching_needed = True
                coaching_reason = "Performance degrading over time"
            elif reason_counts.get(AppealReason.PROCEDURAL_ERROR, 0) >= total_appeals * 0.3:
                coaching_needed = True
                coaching_reason = f"Procedural errors in {reason_counts.get(AppealReason.PROCEDURAL_ERROR, 0)} appeals ({reason_counts.get(AppealReason.PROCEDURAL_ERROR, 0)/total_appeals:.1%})"

            # Estimate total inspections for appeal_rate
            # In practice, join with inspection dataset for actual count
            total_inspections = max(total_appeals * 10, 100)  # Placeholder

            inspector_stats[inspector_id] = InspectorAppealStats(
                inspector_id=str(inspector_id),
                inspector_name=str(inspector_name),
                total_inspections=total_inspections,
                total_appeals=total_appeals,
                appeal_rate=total_appeals / total_inspections if total_inspections > 0 else 0,
                overturn_rate=overturn_rate,
                modification_rate=modification_rate,
                upheld_rate=upheld_rate,
                appeal_count_by_reason=reason_counts,
                recent_trend=trend,
                reliability=reliability,
                coaching_needed=coaching_needed,
                coaching_reason=coaching_reason
            )

        return inspector_stats

    def identify_outliers(
        self,
        inspector_stats: dict[str, InspectorAppealStats],
        overturn_threshold: float = 0.25,
    ) -> list[InspectorAppealStats]:
        """
        Identify inspectors with concerning overturn rates or trends.

        Args:
            inspector_stats: Dict from compute_inspector_stats
            overturn_threshold: Alert threshold (default 25%)

        Returns:
            List of InspectorAppealStats for outliers
        """
        outliers = []

        for stats in inspector_stats.values():
            if stats.overturn_rate > overturn_threshold:
                outliers.append(stats)
            elif stats.recent_trend == PerformanceTrend.DEGRADING and stats.total_appeals >= 10:
                outliers.append(stats)

        return sorted(
            outliers,
            key=lambda x: x.overturn_rate,
            reverse=True
        )

    def compute_systemic_issues(
        self,
        appeals_df: pd.DataFrame,
        outcome_col: str = "appeal_decision",
    ) -> dict[str, any]:
        """
        Identify systemic process issues across all appeals.

        Returns dict with:
          - most_common_reversal_reasons
          - reversal_rate_by_reason
          - recommended_process_improvements
        """
        classifications = self.classifier.batch_classify(
            appeals_df[outcome_col].fillna("").astype(str).tolist()
        )

        reversals = [c for c in classifications if c.resolution == AppealResolution.OVERTURNED]
        reversal_rate = len(reversals) / len(classifications) if classifications else 0

        # Reason breakdown for reversals
        reason_counts = {}
        for rev in reversals:
            reason = rev.reason.value
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        # Compute rate by reason
        reason_rates = {}
        for reason_enum in AppealReason:
            reason_key = reason_enum.value
            reason_total = sum(1 for c in classifications if c.reason == reason_enum)
            reason_reversed = sum(1 for c in classifications if c.reason == reason_enum and c.resolution == AppealResolution.OVERTURNED)
            reason_rates[reason_key] = reason_reversed / reason_total if reason_total > 0 else 0

        # Identify top improvements
        improvements = []
        if reason_rates.get(AppealReason.PROCEDURAL_ERROR.value, 0) > 0.3:
            improvements.append("Standardize inspection documentation and procedures")
        if reason_rates.get(AppealReason.NEW_EVIDENCE.value, 0) > 0.3:
            improvements.append("Implement follow-up inspection requirement before closing tickets")
        if reversal_rate > 0.25:
            improvements.append("Institute peer review process for high-risk inspections")

        return {
            "overall_reversal_rate": reversal_rate,
            "reversal_count_by_reason": reason_counts,
            "reversal_rate_by_reason": reason_rates,
            "total_appeals": len(classifications),
            "recommended_improvements": improvements[:3]
        }
