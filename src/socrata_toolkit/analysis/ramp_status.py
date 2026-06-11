"""
RampStatusClassifier: Deterministic classification of ramp progress descriptions.

Extracts status, completion percentage, and blocker types from ramp progress dataset
using spaCy NER and hardcoded keyword matching. No LLM invocation.

Output:
  - Status: COMPLETED, IN_PROGRESS, BLOCKED, NOT_STARTED
  - Work stage: 0-100% completion estimate
  - Blocker types: PERMIT, WEATHER, BUDGET, OTHER
  - Confidence score: 0-100 based on keyword matches
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from spacy.language import Language
    from spacy.tokens import Doc

logger = logging.getLogger(__name__)


class RampStatus(str, Enum):
    """Ramp project status classification."""
    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    NOT_STARTED = "NOT_STARTED"


class BlockerType(str, Enum):
    """Types of blockers that can delay ramp projects."""
    PERMIT = "PERMIT"
    WEATHER = "WEATHER"
    BUDGET = "BUDGET"
    MATERIAL = "MATERIAL"
    CONTRACTOR = "CONTRACTOR"
    UTILITY = "UTILITY"
    OTHER = "OTHER"


@dataclass
class RampClassificationResult:
    """Result of ramp status classification."""
    text: str
    status: RampStatus
    work_stage_percent: float  # 0-100
    blocker_types: List[BlockerType]
    confidence_score: float  # 0-100
    keywords_matched: List[str]
    extracted_dates: List[str]  # Extracted date references
    status_details: Dict  # Additional status-specific info


class RampStatusClassifier:
    """Classify ramp project status from progress descriptions."""

    # Status indicators: (keyword, status, confidence_boost, work_stage)
    STATUS_KEYWORDS = {
        # COMPLETED indicators
        "COMPLETED": {
            "keywords": [
                "completed", "finished", "done", "installed", "operational",
                "in service", "live", "activated", "open", "fully functional",
                "approved", "accepted", "signed off", "handed over"
            ],
            "status": RampStatus.COMPLETED,
            "default_stage": 100.0,
            "confidence_boost": 25,
        },
        # IN_PROGRESS indicators
        "IN_PROGRESS": {
            "keywords": [
                "in progress", "ongoing", "under construction", "in construction",
                "being built", "in process", "underway", "active", "in execution",
                "fabrication", "installation", "construction", "being installed",
                "design phase", "planning phase", "permitting phase"
            ],
            "status": RampStatus.IN_PROGRESS,
            "default_stage": 50.0,
            "confidence_boost": 20,
        },
        # BLOCKED indicators
        "BLOCKED": {
            "keywords": [
                "blocked", "stalled", "on hold", "paused", "suspended", "delayed",
                "halted", "stopped", "awaiting", "pending", "blocked by", "held up",
                "stuck", "issue", "problem", "cannot proceed", "waiting for"
            ],
            "status": RampStatus.BLOCKED,
            "default_stage": 40.0,
            "confidence_boost": 20,
        },
        # NOT_STARTED indicators
        "NOT_STARTED": {
            "keywords": [
                "not started", "planned", "queued", "scheduled", "upcoming",
                "future", "in queue", "pending start", "to be started",
                "not begun", "will start", "proposed", "designated",
                "identified", "selected", "not yet", "awaiting"
            ],
            "status": RampStatus.NOT_STARTED,
            "default_stage": 5.0,
            "confidence_boost": 15,
        },
    }

    # Blocker type indicators: (keyword, blocker_type, severity)
    BLOCKER_KEYWORDS = {
        BlockerType.PERMIT: {
            "keywords": ["permit", "permitting", "approval", "dob", "department",
                        "permit pending", "waiting for permit", "permit status",
                        "permit approval", "regulatory"],
            "severity": 80,
        },
        BlockerType.WEATHER: {
            "keywords": ["weather", "rain", "cold", "temperature", "seasonal",
                        "winter", "freeze", "snow", "storm", "conditions"],
            "severity": 60,
        },
        BlockerType.BUDGET: {
            "keywords": ["budget", "funding", "budget allocation", "cost",
                        "financial", "appropriation", "budget pending",
                        "funds", "budget approved"],
            "severity": 75,
        },
        BlockerType.MATERIAL: {
            "keywords": ["material", "supply", "shortage", "material delivery",
                        "supply chain", "vendor", "procurement"],
            "severity": 70,
        },
        BlockerType.CONTRACTOR: {
            "keywords": ["contractor", "vendor", "subcontractor", "crew",
                        "labor", "staffing", "capacity", "consultant"],
            "severity": 65,
        },
        BlockerType.UTILITY: {
            "keywords": ["utility", "water", "gas", "electric", "sewer",
                        "hydrant", "manhole", "underground", "coordination"],
            "severity": 85,
        },
    }

    # Work stage estimation: percentage keywords
    PERCENTAGE_PATTERN = r"(\d+)\s*%|(\d+)\s*percent"
    STAGE_KEYWORDS = {
        "design": 10.0,
        "planning": 15.0,
        "permitting": 25.0,
        "engineering": 30.0,
        "procurement": 35.0,
        "fabrication": 40.0,
        "installation": 60.0,
        "construction": 65.0,
        "testing": 85.0,
        "final": 95.0,
        "completion": 100.0,
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize classifier with spaCy model."""
        try:
            import spacy
            self.nlp = spacy.load(model_name)
        except ImportError:
            raise ImportError(
                "spaCy is required for RampStatusClassifier. "
                "Install with: pip install -e '.[nlp]' or pip install spacy"
            )
        except OSError:
            logger.warning(
                f"Model {model_name} not found. Install with: "
                f"python -m spacy download {model_name}"
            )
            raise

    def classify(self, text: str) -> RampClassificationResult:
        """
        Classify a ramp progress description.

        Args:
            text: Description text from ramp_progress dataset

        Returns:
            RampClassificationResult with status, stage, blockers, and confidence

        Raises:
            ValueError: If text is empty or None
        """
        if not text or not isinstance(text, str):
            raise ValueError("text must be a non-empty string")

        text_lower = text.lower()
        doc = self.nlp(text_lower) if hasattr(self, 'nlp') else None

        # 1. Determine primary status
        status, status_confidence, matched_keywords = self._classify_status(
            text_lower
        )

        # 2. Estimate work stage percentage
        work_stage = self._estimate_work_stage(text_lower, status)

        # 3. Identify blocker types
        blocker_types = self._identify_blockers(text_lower)

        # 4. Extract dates
        extracted_dates = self._extract_dates(doc)

        # 5. Calculate overall confidence
        overall_confidence = min(
            100.0,
            status_confidence + (len(blocker_types) * 5) + (len(extracted_dates) * 3)
        )

        # 6. Status-specific details
        status_details = {
            "status": status.value,
            "stage_percent": work_stage,
            "blockers": [b.value for b in blocker_types],
            "extracted_entities": self._extract_entities(doc),
        }

        return RampClassificationResult(
            text=text,
            status=status,
            work_stage_percent=work_stage,
            blocker_types=blocker_types,
            confidence_score=overall_confidence,
            keywords_matched=matched_keywords,
            extracted_dates=extracted_dates,
            status_details=status_details,
        )

    def _classify_status(
        self, text_lower: str
    ) -> Tuple[RampStatus, float, List[str]]:
        """Determine primary status and confidence score."""
        matched_keywords = []
        status_scores = {}

        # Score each status based on keyword matches
        for status_name, config in self.STATUS_KEYWORDS.items():
            score = 0.0
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    matched_keywords.append(keyword)
                    score += config["confidence_boost"]

            status_scores[status_name] = score

        # Return highest-scoring status
        if not any(status_scores.values()):
            # No clear status found, default to IN_PROGRESS
            return RampStatus.IN_PROGRESS, 10.0, []

        best_status_name = max(status_scores, key=status_scores.get)
        best_status = self.STATUS_KEYWORDS[best_status_name]["status"]
        best_score = status_scores[best_status_name]

        return best_status, best_score, matched_keywords

    def _estimate_work_stage(self, text_lower: str, status: RampStatus) -> float:
        """Estimate work stage completion percentage."""
        # 1. Check for explicit percentages
        matches = re.findall(self.PERCENTAGE_PATTERN, text_lower)
        if matches:
            # Extract first percentage
            for match in matches:
                if match[0]:
                    return float(match[0])
                elif match[1]:
                    return float(match[1])

        # 2. Check for stage-specific keywords
        for stage_keyword, percent in self.STAGE_KEYWORDS.items():
            if stage_keyword in text_lower:
                return percent

        # 3. Default based on status
        status_config = None
        for config in self.STATUS_KEYWORDS.values():
            if config["status"] == status:
                status_config = config
                break

        return status_config["default_stage"] if status_config else 50.0

    def _identify_blockers(self, text_lower: str) -> List[BlockerType]:
        """Identify blocker types mentioned in text."""
        blockers = []

        for blocker_type, config in self.BLOCKER_KEYWORDS.items():
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    if blocker_type not in blockers:
                        blockers.append(blocker_type)
                    break

        return blockers

    def _extract_dates(self, doc: Doc) -> List[str]:
        """Extract date references from text."""
        dates = []
        for ent in doc.ents:
            if ent.label_ == "DATE":
                dates.append(ent.text)
        return dates

    def _extract_entities(self, doc: Doc) -> List[Tuple[str, str]]:
        """Extract named entities from text."""
        entities = []
        for ent in doc.ents:
            if ent.label_ in ["DATE", "ORG", "GPE", "PERSON"]:
                entities.append((ent.text, ent.label_))
        return entities

    def classify_batch(
        self, texts: List[str]
    ) -> Dict[str, RampClassificationResult]:
        """
        Classify multiple ramp descriptions.

        Args:
            texts: List of description strings

        Returns:
            Dict mapping text → RampClassificationResult
        """
        results = {}
        for text in texts:
            try:
                results[text] = self.classify(text)
            except (ValueError, Exception) as e:
                logger.warning(f"Classification failed for text: {text[:50]}... ({e})")
        return results

    @staticmethod
    def summary_table(
        results: List[RampClassificationResult],
    ) -> Dict:
        """
        Summarize classification results across a batch.

        Args:
            results: List of RampClassificationResult objects

        Returns:
            Dict with counts and percentages by status and blocker
        """
        status_counts = {status.value: 0 for status in RampStatus}
        blocker_counts = {blocker.value: 0 for blocker in BlockerType}

        for result in results:
            status_counts[result.status.value] += 1
            for blocker in result.blocker_types:
                blocker_counts[blocker.value] += 1

        total = len(results)
        status_pcts = {
            status: (count / total * 100 if total > 0 else 0)
            for status, count in status_counts.items()
        }

        return {
            "total_records": total,
            "status_breakdown": status_counts,
            "status_percentages": status_pcts,
            "blocker_breakdown": blocker_counts,
            "avg_work_stage": (
                sum(r.work_stage_percent for r in results) / total
                if total > 0
                else 0
            ),
            "avg_confidence": (
                sum(r.confidence_score for r in results) / total
                if total > 0
                else 0
            ),
        }
