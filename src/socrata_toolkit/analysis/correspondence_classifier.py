"""
Correspondence & Communication Classification — spaCy-based deterministic NLP.

Classifies correspondence/communication records from the NYC DOT correspondences dataset
(bheb-sjfi) for tone, type, compliance, and clarity.

Classes:
- CorrespondenceType: INITIAL_NOTICE, FOLLOW_UP, ESCALATION, THREAT_OF_PENALTY, RESOLUTION
- Tone: PROFESSIONAL, THREATENING, HARSH, CONCILIATORY, NEUTRAL
- Clarity: HIGH, MEDIUM, LOW
- Compliance: COMPLIANT, NEEDS_REVIEW, NON_COMPLIANT
"""

import logging
import spacy
from spacy.language import Language
from spacy.tokens import Doc
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CorrespondenceClassificationResult:
    """Result of correspondence classification."""
    text: str
    correspondence_type: str
    tone: str
    clarity_score: float  # 0-100
    compliance_status: str
    compliance_score: float  # 0-100
    keywords_matched: List[str]
    tone_indicators: List[str]
    compliance_issues: List[str]
    extracted_entities: List[Tuple[str, str]]
    category_details: Dict


class CorrespondenceClassifier:
    """Classify correspondence and communication messages for compliance audit."""

    CORRESPONDENCE_TYPES = {
        "INITIAL_NOTICE": {
            "keywords": ["notice", "initial", "notification", "inform", "advise", "alert",
                        "official notice", "notify", "acknowledge receipt"],
            "description": "First communication about a violation or issue"
        },
        "FOLLOW_UP": {
            "keywords": ["follow up", "follow-up", "pending", "awaiting", "status",
                        "update", "reminder", "further notice", "still waiting"],
            "description": "Subsequent communication regarding previous correspondence"
        },
        "ESCALATION": {
            "keywords": ["escalate", "escalated", "severe", "escalation", "urgent",
                        "imminent", "serious", "significant", "critical"],
            "description": "Escalation of previous issue"
        },
        "THREAT_OF_PENALTY": {
            "keywords": ["penalty", "fine", "violation", "violation of law", "liable",
                        "enforcement action", "legal action", "court", "breach",
                        "non-compliance", "failure to comply"],
            "description": "Communication of potential penalties or legal action"
        },
        "RESOLUTION": {
            "keywords": ["resolved", "closure", "closed", "complete", "completed",
                        "resolved", "settlement", "agreement", "approved"],
            "description": "Communication resolving an issue"
        },
    }

    TONE_KEYWORDS = {
        "PROFESSIONAL": {
            "keywords": ["respectfully", "sincerely", "professional", "formal",
                        "acknowledge", "appreciate", "cooperation"],
            "indicators": []
        },
        "THREATENING": {
            "keywords": ["must", "require", "failure to", "will be", "prosecute",
                        "liability", "liable", "enforcement"],
            "indicators": ["danger", "urgent action"]
        },
        "HARSH": {
            "keywords": ["unacceptable", "failure", "deficient", "inadequate",
                        "unsatisfactory", "violation", "breach"],
            "indicators": ["critical language"]
        },
        "CONCILIATORY": {
            "keywords": ["understand", "appreciate", "cooperate", "together",
                        "work with", "partner", "support", "assistance"],
            "indicators": ["collaborative"]
        },
        "NEUTRAL": {
            "keywords": ["information", "data", "record", "document", "date", "time",
                        "location", "address"],
            "indicators": ["factual tone"]
        },
    }

    COMPLIANCE_CHECKLIST = {
        "required_elements": [
            ("clear_reference", ["violation", "notice", "inspection", "issue", "osm", "ccm",
                                "case number", "ref", "identification"]),
            ("date_provided", ["date", "time", "received", "issued", "effective"]),
            ("action_required", ["must", "required", "need", "request", "comply", "respond"]),
            ("deadline", ["day", "days", "within", "week", "month", "by"]),
            ("contact_info", ["phone", "contact", "reach", "email", "office", "address"]),
        ],
        "accessibility_requirements": [
            ("clear_language", ["simple", "understand", "clear", "simple language",
                               "plain", "accessible"]),
            ("language_accessibility", ["spanish", "language", "interpreter", "translation"]),
        ],
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize classifier with spaCy model."""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(f"Model {model_name} not found. Install with: python -m spacy download {model_name}")
            raise

        self._add_correspondence_components()

    def _add_correspondence_components(self) -> None:
        """Add custom components to spaCy pipeline."""
        if not Doc.has_extension("correspondence_type"):
            Doc.set_extension("correspondence_type", default=None)
        if not Doc.has_extension("tone"):
            Doc.set_extension("tone", default=None)
        if not Doc.has_extension("compliance_status"):
            Doc.set_extension("compliance_status", default=None)
        if not Doc.has_extension("clarity_score"):
            Doc.set_extension("clarity_score", default=0)

    def classify(self, text: str) -> CorrespondenceClassificationResult:
        """
        Classify a correspondence message.

        Args:
            text: Correspondence message text (from issue, resolution columns)

        Returns:
            CorrespondenceClassificationResult with type, tone, clarity, and compliance
        """
        doc = self.nlp(text)
        text_lower = text.lower()

        # Classify correspondence type
        type_scores = {}
        matched_keywords = []

        for ctype, config in self.CORRESPONDENCE_TYPES.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                type_scores[ctype] = score

        # Determine primary type
        if type_scores:
            primary_type = max(type_scores, key=type_scores.get)
        else:
            primary_type = "OTHER"

        # Classify tone
        tone_scores = {}
        tone_indicators = []

        for tone, config in self.TONE_KEYWORDS.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += 1
                    tone_indicators.append(keyword)

            if score > 0:
                tone_scores[tone] = score

        primary_tone = max(tone_scores, key=tone_scores.get) if tone_scores else "NEUTRAL"

        # Calculate clarity score (higher word count + more references = clearer)
        words = text.split()
        word_count = len(words)
        sentence_count = len([s for s in doc.sents])

        clarity_factors = 0
        if word_count > 50:
            clarity_factors += 30
        elif word_count > 20:
            clarity_factors += 15

        if sentence_count > 1:
            clarity_factors += 20

        # Check for clear action items
        action_keywords = ["must", "should", "will", "need", "require"]
        if any(kw in text_lower for kw in action_keywords):
            clarity_factors += 25

        # Check for temporal information
        temporal_keywords = ["day", "week", "month", "date", "time", "deadline"]
        if any(kw in text_lower for kw in temporal_keywords):
            clarity_factors += 25

        clarity_score = min(100, clarity_factors)

        # Assess compliance
        compliance_issues = []
        elements_found = 0

        for element_name, element_keywords in self.COMPLIANCE_CHECKLIST["required_elements"]:
            found = any(kw in text_lower for kw in element_keywords)
            if found:
                elements_found += 1
            else:
                compliance_issues.append(f"Missing: {element_name}")

        # Accessibility check
        for access_name, access_keywords in self.COMPLIANCE_CHECKLIST["accessibility_requirements"]:
            found = any(kw in text_lower for kw in access_keywords)
            if not found:
                compliance_issues.append(f"Accessibility concern: {access_name}")

        # Determine compliance status
        compliance_percentage = (elements_found / len(self.COMPLIANCE_CHECKLIST["required_elements"])) * 100

        if compliance_percentage >= 80:
            compliance_status = "COMPLIANT"
        elif compliance_percentage >= 50:
            compliance_status = "NEEDS_REVIEW"
        else:
            compliance_status = "NON_COMPLIANT"

        # Extract entities
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        # Build category details
        category_details = {
            "type": primary_type,
            "tone": primary_tone,
            "elements_present": elements_found,
            "elements_total": len(self.COMPLIANCE_CHECKLIST["required_elements"]),
            "type_scores": type_scores,
            "tone_scores": tone_scores,
        }

        return CorrespondenceClassificationResult(
            text=text,
            correspondence_type=primary_type,
            tone=primary_tone,
            clarity_score=clarity_score,
            compliance_status=compliance_status,
            compliance_score=compliance_percentage,
            keywords_matched=list(set(matched_keywords)),
            tone_indicators=list(set(tone_indicators)),
            compliance_issues=compliance_issues,
            extracted_entities=entities,
            category_details=category_details
        )

    def batch_classify(self, texts: List[str]) -> List[CorrespondenceClassificationResult]:
        """
        Classify multiple correspondence messages.

        Args:
            texts: List of correspondence messages

        Returns:
            List of CorrespondenceClassificationResult objects
        """
        results = []
        for text in texts:
            if isinstance(text, str) and text.strip():
                results.append(self.classify(text))
        return results

    def enrich_dataframe(self, df, text_column: str = "issue") -> object:
        """
        Add classification columns to a correspondence dataframe.

        Args:
            df: Input dataframe with correspondence data
            text_column: Column name containing text to classify (default: "issue")

        Returns:
            Enriched dataframe with classification columns
        """
        import pandas as pd

        # Filter to non-null text
        valid_texts = df[text_column].fillna("").astype(str)
        results = self.batch_classify(valid_texts.tolist())

        df_enriched = df.copy()
        df_enriched["correspondence_type"] = [r.correspondence_type for r in results]
        df_enriched["tone"] = [r.tone for r in results]
        df_enriched["clarity_score"] = [r.clarity_score for r in results]
        df_enriched["compliance_status"] = [r.compliance_status for r in results]
        df_enriched["compliance_score"] = [r.compliance_score for r in results]

        return df_enriched

    def compliance_summary(self, df) -> Dict:
        """
        Generate compliance summary for a dataframe of classified correspondence.

        Args:
            df: Dataframe enriched with classification columns

        Returns:
            Dictionary with compliance statistics
        """
        if "compliance_status" not in df.columns:
            raise ValueError("Dataframe must be enriched with classification columns")

        total = int(len(df))
        compliant = int((df["compliance_status"] == "COMPLIANT").sum())
        needs_review = int((df["compliance_status"] == "NEEDS_REVIEW").sum())
        non_compliant = int((df["compliance_status"] == "NON_COMPLIANT").sum())

        # Convert tone/type counts to int to ensure JSON serializable
        by_tone = df["tone"].value_counts().to_dict() if "tone" in df.columns else {}
        by_tone = {k: int(v) for k, v in by_tone.items()}

        by_type = df["correspondence_type"].value_counts().to_dict() if "correspondence_type" in df.columns else {}
        by_type = {k: int(v) for k, v in by_type.items()}

        return {
            "total_correspondences": total,
            "compliant": compliant,
            "needs_review": needs_review,
            "non_compliant": non_compliant,
            "compliance_rate": float((compliant / total * 100)) if total > 0 else 0.0,
            "by_tone": by_tone,
            "by_type": by_type,
            "avg_clarity": float(df["clarity_score"].mean()) if "clarity_score" in df.columns else 0.0,
            "avg_compliance": float(df["compliance_score"].mean()) if "compliance_score" in df.columns else 0.0,
        }
