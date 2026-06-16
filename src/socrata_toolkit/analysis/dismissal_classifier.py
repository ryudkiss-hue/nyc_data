"""
Dismissal Reason Classifier for Inspector Pattern Analysis.

Classifies dismissals into categories (LEGAL, ADMIN_ERROR, JUSTIFIED_CORRECTION, SUSPICIOUS)
with confidence levels and inspector consistency outlier detection.

Uses spaCy NLP for deterministic text classification (no LLM).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd
import spacy
from spacy.tokens import Doc

logger = logging.getLogger(__name__)

class DismissalCategory(str, Enum):
    """Dismissal classification category."""
    LEGAL = "LEGAL"
    ADMIN_ERROR = "ADMIN_ERROR"
    JUSTIFIED_CORRECTION = "JUSTIFIED_CORRECTION"
    SUSPICIOUS = "SUSPICIOUS"
    UNKNOWN = "UNKNOWN"

class ConfidenceLevel(str, Enum):
    """Confidence in the classification."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class InspectorConsistency(str, Enum):
    """Inspector consistency relative to cohort."""
    NORMAL = "NORMAL"
    OUTLIER_HIGH = "OUTLIER_HIGH"  # Dismisses much more than peers
    OUTLIER_LOW = "OUTLIER_LOW"    # Dismisses much less than peers

@dataclass
class DismissalMetrics:
    """Raw dismissal metrics for an inspector."""
    inspector_id: str
    inspector_name: str | None
    total_dismissals: int = 0
    dismissal_rate: float = 0.0  # dismissals / inspections
    avg_dismissals_per_defect: float = 0.0
    suspicious_count: int = 0
    suspicious_rate: float = 0.0

@dataclass
class DismissalClassification:
    """Classification result for a single dismissal."""
    dismissal_id: str
    inspection_id: str | None
    defect_type: str | None
    dismissal_reason_text: str

    # Classification
    category: DismissalCategory
    confidence: ConfidenceLevel

    # Inspector context
    inspector_id: str | None
    inspector_consistency: InspectorConsistency = InspectorConsistency.NORMAL

    # Scoring
    category_score: float = 0.0  # 0-100
    suspicion_score: float = 0.0  # 0-100 (0=not suspicious, 100=highly suspicious)

    # Extracted details
    keywords_matched: list[str] = field(default_factory=list)
    legal_citations: list[str] = field(default_factory=list)

    # Recommendations
    flagged_reason: str = ""
    requires_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "dismissal_id": self.dismissal_id,
            "inspection_id": self.inspection_id,
            "defect_type": self.defect_type,
            "dismissal_reason": self.dismissal_reason_text[:100],
            "category": self.category.value,
            "confidence": self.confidence.value,
            "inspector_id": self.inspector_id,
            "inspector_consistency": self.inspector_consistency.value,
            "category_score": round(self.category_score, 1),
            "suspicion_score": round(self.suspicion_score, 1),
            "keywords_matched": self.keywords_matched,
            "legal_citations": self.legal_citations,
            "flagged_reason": self.flagged_reason,
            "requires_review": self.requires_review,
        }

class DismissalReasonClassifier:
    """
    Classify dismissal reasons into categories with suspicion scoring.

    Categories:
    - LEGAL: Legitimate legal/regulatory reasons (code section citations, etc.)
    - ADMIN_ERROR: Clerical/administrative corrections (duplicate, wrong category, etc.)
    - JUSTIFIED_CORRECTION: Justified reclassification based on inspection data
    - SUSPICIOUS: Unusual patterns suggesting potential fraud/favoritism
    - UNKNOWN: Insufficient information
    """

    # Keyword patterns for each category
    LEGAL_KEYWORDS = {
        "keywords": [
            "legal", "code", "section", "statute", "law", "regulation", "complies",
            "compliant", "variance", "exemption", "permit", "licensed", "approved",
            "authorized", "rsa", "title", "article", "administrative code",
        ],
        "citations": [
            r"NYC\s*(?:Code|Admin)\s*§",
            r"Section\s+\d+",
            r"Title\s+\d+",
            r"SDOT",
            r"DOT",
            r"RSA",
        ]
    }

    ADMIN_ERROR_KEYWORDS = {
        "keywords": [
            "duplicate", "error", "mistake", "wrong", "incorrect", "misclassified",
            "category", "defect", "wrongly", "entered", "data entry", "typed",
            "removed in error", "do not open", "hold", "pending", "reassigned",
        ],
        "patterns": ["duplicate", "error", "wrong category", "data entry"]
    }

    JUSTIFIED_CORRECTION_KEYWORDS = {
        "keywords": [
            "reinspect", "reinspection", "corrected", "verified", "confirmed",
            "fixed", "repaired", "resolved", "already", "previously", "original",
            "mistake by inspector", "misidentified", "not actual", "resolved",
        ],
        "patterns": ["reinspection shows", "no longer present", "previously repaired"]
    }

    SUSPICIOUS_KEYWORDS = {
        "keywords": [
            "personal", "favor", "contractor", "friend", "relative", "relationship",
            "political", "influence", "pressure", "special", "consideration",
            "expedite", "rush", "fast track", "priority", "outside", "unusual",
        ],
        "patterns": ["personal favor", "special consideration", "under the table"]
    }

    # Suspicious indicators
    SUSPICIOUS_PATTERNS = {
        "high_dismissal_rate_for_inspector": 0.40,  # >40% dismissals = red flag
        "clustering_by_defect": True,  # Same defect type repeatedly dismissed
        "clustering_by_location": True,  # Same location repeatedly dismissed
        "temporal_clustering": True,  # Multiple dismissals in short time
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize classifier with spaCy model."""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(
                f"Model {model_name} not found. Install with: "
                f"python -m spacy download {model_name}"
            )
            raise

        self._add_dismissal_components()

    def _add_dismissal_components(self):
        """Add custom components to spaCy pipeline."""
        if not Doc.has_extension("dismissal_category"):
            Doc.set_extension("dismissal_category", default=None)
        if not Doc.has_extension("suspicion_score"):
            Doc.set_extension("suspicion_score", default=0)

    def classify(
        self,
        dismissal_id: str,
        dismissal_reason_text: str,
        inspection_id: str | None = None,
        defect_type: str | None = None,
        inspector_id: str | None = None,
        inspector_dismissal_rate: float | None = None,
        inspector_cohort_rate: float = 0.15,  # Average dismissal rate across inspectors
    ) -> DismissalClassification:
        """
        Classify a dismissal reason.

        Args:
            dismissal_id: Unique dismissal record ID
            dismissal_reason_text: Text explanation for dismissal
            inspection_id: Source inspection ID
            defect_type: Type of defect that was dismissed
            inspector_id: Inspector who dismissed the violation
            inspector_dismissal_rate: This inspector's overall dismissal rate
            inspector_cohort_rate: Average dismissal rate for comparison

        Returns:
            DismissalClassification with category, confidence, and suspicion score
        """
        if not dismissal_reason_text or not isinstance(dismissal_reason_text, str):
            return self._unknown_classification(dismissal_id, inspection_id, defect_type)

        text_lower = dismissal_reason_text.lower()
        doc = self.nlp(dismissal_reason_text)

        # Score each category
        legal_score = self._score_legal(text_lower, doc)
        admin_score = self._score_admin_error(text_lower, doc)
        justified_score = self._score_justified_correction(text_lower, doc)
        suspicious_score = self._score_suspicious(text_lower, doc)

        # Determine primary category
        scores = {
            DismissalCategory.LEGAL: legal_score,
            DismissalCategory.ADMIN_ERROR: admin_score,
            DismissalCategory.JUSTIFIED_CORRECTION: justified_score,
            DismissalCategory.SUSPICIOUS: suspicious_score,
        }

        primary_category = max(scores, key=scores.get)
        max_score = max(scores.values())

        # Determine confidence
        if max_score == 0:
            primary_category = DismissalCategory.UNKNOWN
            confidence = ConfidenceLevel.LOW
            category_score = 0.0
        else:
            confidence = self._confidence_from_score(max_score)
            category_score = min(100.0, max_score)

        # Extract keywords and citations
        keywords = self._extract_keywords(text_lower, primary_category)
        citations = self._extract_legal_citations(doc)

        # Inspector consistency check
        inspector_consistency = InspectorConsistency.NORMAL
        if inspector_dismissal_rate is not None and inspector_cohort_rate > 0:
            if inspector_dismissal_rate > inspector_cohort_rate * 1.5:
                inspector_consistency = InspectorConsistency.OUTLIER_HIGH
            elif inspector_dismissal_rate < inspector_cohort_rate * 0.5:
                inspector_consistency = InspectorConsistency.OUTLIER_LOW

        # Adjust suspicion based on inspector pattern
        suspicion_adj = 0.0
        if inspector_consistency == InspectorConsistency.OUTLIER_HIGH:
            suspicion_adj = 15.0

        # Cap suspicion score
        final_suspicion_score = min(100.0, suspicious_score + suspicion_adj)

        # Determine if requires review
        requires_review = (
            primary_category == DismissalCategory.SUSPICIOUS
            or final_suspicion_score >= 60.0
            or inspector_consistency == InspectorConsistency.OUTLIER_HIGH
        )

        # Flagged reason
        flagged_reason = self._generate_flagged_reason(
            primary_category, final_suspicion_score, inspector_consistency
        )

        return DismissalClassification(
            dismissal_id=dismissal_id,
            inspection_id=inspection_id,
            defect_type=defect_type,
            dismissal_reason_text=dismissal_reason_text,
            category=primary_category,
            confidence=confidence,
            inspector_id=inspector_id,
            inspector_consistency=inspector_consistency,
            category_score=category_score,
            suspicion_score=final_suspicion_score,
            keywords_matched=keywords,
            legal_citations=citations,
            flagged_reason=flagged_reason,
            requires_review=requires_review,
        )

    def _score_legal(self, text_lower: str, doc: Doc) -> float:
        """Score likelihood of legal/regulatory reason."""
        score = 0.0

        # Check keywords
        matches = sum(1 for kw in self.LEGAL_KEYWORDS["keywords"] if kw in text_lower)
        score += matches * 15.0

        # Check for code citations
        import re
        citations = 0
        for pattern in self.LEGAL_KEYWORDS["citations"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                citations += 1
                score += 30.0

        # Heuristic: legal reasons are often longer and more formal
        if len(text_lower) > 50:
            score += 10.0

        return min(100.0, score)

    def _score_admin_error(self, text_lower: str, doc: Doc) -> float:
        """Score likelihood of administrative error."""
        score = 0.0

        # Check keywords
        matches = sum(1 for kw in self.ADMIN_ERROR_KEYWORDS["keywords"] if kw in text_lower)
        score += matches * 12.0

        # Check patterns
        for pattern in self.ADMIN_ERROR_KEYWORDS["patterns"]:
            if pattern in text_lower:
                score += 25.0

        return min(100.0, score)

    def _score_justified_correction(self, text_lower: str, doc: Doc) -> float:
        """Score likelihood of justified correction based on inspection."""
        score = 0.0

        # Check keywords
        matches = sum(1 for kw in self.JUSTIFIED_CORRECTION_KEYWORDS["keywords"] if kw in text_lower)
        score += matches * 12.0

        # Check patterns
        for pattern in self.JUSTIFIED_CORRECTION_KEYWORDS["patterns"]:
            if pattern in text_lower:
                score += 25.0

        return min(100.0, score)

    def _score_suspicious(self, text_lower: str, doc: Doc) -> float:
        """Score likelihood of suspicious/fraudulent dismissal."""
        score = 0.0

        # Check keywords
        matches = sum(1 for kw in self.SUSPICIOUS_KEYWORDS["keywords"] if kw in text_lower)
        score += matches * 15.0

        # Check patterns
        for pattern in self.SUSPICIOUS_KEYWORDS["patterns"]:
            if pattern in text_lower:
                score += 40.0

        # Very short explanations are suspicious
        if len(text_lower) < 15:
            score += 20.0

        # Vague language is suspicious
        vague_terms = ["unclear", "just because", "felt like", "no reason", "na", "n/a"]
        for term in vague_terms:
            if term in text_lower:
                score += 25.0

        return min(100.0, score)

    def _confidence_from_score(self, score: float) -> ConfidenceLevel:
        """Map score to confidence level."""
        if score >= 70.0:
            return ConfidenceLevel.HIGH
        elif score >= 40.0:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _extract_keywords(
        self, text_lower: str, category: DismissalCategory
    ) -> list[str]:
        """Extract matching keywords for the category."""
        keywords = []

        if category == DismissalCategory.LEGAL:
            for kw in self.LEGAL_KEYWORDS["keywords"]:
                if kw in text_lower:
                    keywords.append(kw)
        elif category == DismissalCategory.ADMIN_ERROR:
            for kw in self.ADMIN_ERROR_KEYWORDS["keywords"]:
                if kw in text_lower:
                    keywords.append(kw)
        elif category == DismissalCategory.JUSTIFIED_CORRECTION:
            for kw in self.JUSTIFIED_CORRECTION_KEYWORDS["keywords"]:
                if kw in text_lower:
                    keywords.append(kw)
        elif category == DismissalCategory.SUSPICIOUS:
            for kw in self.SUSPICIOUS_KEYWORDS["keywords"]:
                if kw in text_lower:
                    keywords.append(kw)

        return keywords

    def _extract_legal_citations(self, doc: Doc) -> list[str]:
        """Extract legal/regulatory citations from text."""
        citations = []
        import re

        text = doc.text
        patterns = [
            r"(?:NYC\s+)?(?:Code|Admin|Administrative)\s+§\s+[\d\-\.]+",
            r"Section\s+\d+(?:\.\d+)*",
            r"Title\s+\d+",
            r"SDOT\s+[\w\d\-]+",
            r"RSA\s+[\w\d\-]+",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            citations.extend(matches)

        return list(set(citations))  # Deduplicate

    def _generate_flagged_reason(
        self,
        category: DismissalCategory,
        suspicion_score: float,
        inspector_consistency: InspectorConsistency,
    ) -> str:
        """Generate a brief flagged reason if needed."""
        reasons = []

        if category == DismissalCategory.SUSPICIOUS:
            reasons.append("Suspicious category classification")

        if suspicion_score >= 70.0:
            reasons.append(f"High suspicion score ({suspicion_score:.0f})")
        elif suspicion_score >= 60.0:
            reasons.append(f"Elevated suspicion score ({suspicion_score:.0f})")

        if inspector_consistency == InspectorConsistency.OUTLIER_HIGH:
            reasons.append("Inspector dismissal rate outlier (above cohort)")

        return "; ".join(reasons) if reasons else ""

    def _unknown_classification(
        self,
        dismissal_id: str,
        inspection_id: str | None,
        defect_type: str | None,
    ) -> DismissalClassification:
        """Create an unknown/no-data classification."""
        return DismissalClassification(
            dismissal_id=dismissal_id,
            inspection_id=inspection_id,
            defect_type=defect_type,
            dismissal_reason_text="",
            category=DismissalCategory.UNKNOWN,
            confidence=ConfidenceLevel.LOW,
            category_score=0.0,
            suspicion_score=0.0,
            flagged_reason="No dismissal reason text provided",
            requires_review=False,
        )
