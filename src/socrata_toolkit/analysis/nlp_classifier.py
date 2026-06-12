"""
NLP-based text classification for inspection violations and 311 complaints.

Hardcoded deterministic classifiers using spaCy — no LLM invocation.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import spacy
from spacy.language import Language
from spacy.tokens import Doc

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Result of text classification."""
    text: str
    primary_category: str
    confidence_score: float  # 0-100
    severity_score: float  # 0-100 (inspection-specific)
    extracted_entities: list[tuple[str, str]]  # (text, label)
    keywords_matched: list[str]
    category_details: dict  # Additional category-specific info

class InspectionViolationClassifier:
    """Classify inspection violation descriptions."""

    # Violation types observed in NYC SIM data
    VIOLATION_TYPES = {
        "STRUCTURAL_DAMAGE": {
            "keywords": ["crack", "broken", "damaged", "crumble", "fracture", "split",
                        "chip", "spall", "deteriorat", "eroded", "crumbling", "concrete failure"],
            "severity_base": 65,
            "description": "Physical damage to sidewalk structure"
        },
        "WATER_INTRUSION": {
            "keywords": ["water", "leak", "wet", "moisture", "puddle", "flooding", "drainage",
                        "seep", "saturated", "damp", "efflorescence"],
            "severity_base": 60,
            "description": "Water damage or drainage issues"
        },
        "TRIP_HAZARD": {
            "keywords": ["trip", "hazard", "uneven", "gap", "buckle", "heave", "displacement",
                        "raised", "depression", "void", "settlement", "tilted"],
            "severity_base": 75,
            "description": "Tripping or falling risk"
        },
        "POOR_MAINTENANCE": {
            "keywords": ["dirty", "debris", "litter", "stain", "discoloration", "algae",
                        "moss", "lichen", "trash", "neglected", "unkempt"],
            "severity_base": 20,
            "description": "Cleanliness and maintenance issues"
        },
        "SURFACE_HAZARD": {
            "keywords": ["smooth", "slippery", "icy", "slick", "loose", "unstable",
                        "patch", "repair", "patch repair", "temporary"],
            "severity_base": 50,
            "description": "Slipperiness or surface instability"
        },
        "UTILITY_ISSUE": {
            "keywords": ["utility", "pole", "wire", "cable", "grate", "cover", "manhole",
                        "vault", "telephone", "electric", "gas"],
            "severity_base": 45,
            "description": "Issues related to utilities in sidewalk"
        },
        "ACCESSIBILITY": {
            "keywords": ["ramp", "curb", "cut", "accessible", "wheelchair", "ada",
                        "barrier", "slope", "grade"],
            "severity_base": 70,
            "description": "ADA accessibility issues"
        },
    }

    CRITICAL_KEYWORDS = {
        "danger": 20,      # +20 to severity
        "unsafe": 20,
        "immediate": 15,
        "hazard": 10,
        "risk": 5,
        "severe": 15,
        "collapse": 25,
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize classifier with spaCy model."""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(f"Model {model_name} not found. Install with: python -m spacy download {model_name}")
            raise

        self._add_violation_components()

    def _add_violation_components(self):
        """Add custom components to spaCy pipeline."""

        # Add custom attributes
        if not Doc.has_extension("violation_type"):
            Doc.set_extension("violation_type", default=None)
        if not Doc.has_extension("severity_score"):
            Doc.set_extension("severity_score", default=0)
        if not Doc.has_extension("confidence_score"):
            Doc.set_extension("confidence_score", default=0)
        if not Doc.has_extension("keywords_matched"):
            Doc.set_extension("keywords_matched", default=[])

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify a violation description.

        Args:
            text: Violation description from inspection data

        Returns:
            ClassificationResult with category, severity, and entities
        """
        doc = self.nlp(text)
        text_lower = text.lower()

        # Score each violation type
        type_scores = {}
        matched_keywords = {}

        for vtype, config in self.VIOLATION_TYPES.items():
            score = 0
            keywords_found = []

            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += 1
                    keywords_found.append(keyword)

            if score > 0:
                type_scores[vtype] = score
                matched_keywords[vtype] = keywords_found

        # Determine primary category
        if type_scores:
            primary_type = max(type_scores, key=type_scores.get)
            # Normalize confidence (0-100)
            total_possible = len(self.VIOLATION_TYPES[primary_type]["keywords"])
            confidence = min(100, (type_scores[primary_type] / total_possible) * 100)
        else:
            primary_type = "OTHER"
            confidence = 0

        # Calculate severity score
        severity = self.VIOLATION_TYPES.get(primary_type, {}).get("severity_base", 30)

        # Boost severity based on critical keywords
        for critical_word, boost in self.CRITICAL_KEYWORDS.items():
            if critical_word in text_lower:
                severity = min(100, severity + boost)

        # Extract entities using spaCy NER
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        # Build category details
        category_details = {
            "type": primary_type,
            "description": self.VIOLATION_TYPES.get(primary_type, {}).get("description", "Unknown violation type"),
            "keywords_matched": matched_keywords.get(primary_type, []),
            "all_scores": type_scores,
        }

        return ClassificationResult(
            text=text,
            primary_category=primary_type,
            confidence_score=confidence,
            severity_score=severity,
            extracted_entities=entities,
            keywords_matched=matched_keywords.get(primary_type, []),
            category_details=category_details
        )

    def batch_classify(self, texts: list[str]) -> list[ClassificationResult]:
        """
        Classify multiple violation descriptions.

        Args:
            texts: List of violation descriptions

        Returns:
            List of ClassificationResult objects
        """
        results = []
        for text in texts:
            results.append(self.classify(text))
        return results

class Complaint311Classifier:
    """Classify 311 complaint descriptions."""

    # 311 complaint categories
    COMPLAINT_CATEGORIES = {
        "SIDEWALK_DAMAGE": {
            "keywords": ["sidewalk", "pavement", "concrete", "asphalt", "broken", "crack",
                        "damaged", "pothole", "uneven", "heave", "displacement"],
            "severity_base": 60,
            "description": "Physical sidewalk damage"
        },
        "STREET_CONDITION": {
            "keywords": ["street", "road", "pothole", "pavement", "asphalt", "filling",
                        "resurfacing", "pavement marking"],
            "severity_base": 55,
            "description": "Street surface or condition issues"
        },
        "HAZARD": {
            "keywords": ["hazard", "dangerous", "unsafe", "danger", "risk", "trip",
                        "fall", "injury", "accident", "exposure"],
            "severity_base": 80,
            "description": "Safety hazard to public"
        },
        "DRAINAGE": {
            "keywords": ["drain", "flooding", "water", "puddle", "wet", "drainage",
                        "clogged", "backup", "overflow"],
            "severity_base": 65,
            "description": "Water drainage or flooding"
        },
        "DEBRIS_LITTER": {
            "keywords": ["debris", "litter", "trash", "garbage", "dirty", "rubbish",
                        "waste", "junk", "illegal dumping"],
            "severity_base": 25,
            "description": "Debris or litter complaint"
        },
        "ACCESSIBILITY": {
            "keywords": ["ramp", "curb cut", "accessible", "wheelchair", "ada",
                        "barrier", "handicap", "mobility"],
            "severity_base": 70,
            "description": "Accessibility barrier"
        },
        "TREE_VEGETATION": {
            "keywords": ["tree", "branch", "root", "vegetation", "overgrown",
                        "limb", "foliage", "pruning"],
            "severity_base": 45,
            "description": "Tree or vegetation issue"
        },
        "GRAFFITI": {
            "keywords": ["graffiti", "vandal", "tag", "spray paint", "deface"],
            "severity_base": 30,
            "description": "Graffiti or vandalism"
        },
        "PARKING": {
            "keywords": ["parking", "illegal parking", "blocked", "sidewalk parking",
                        "parked", "vehicles"],
            "severity_base": 35,
            "description": "Parking violation or obstruction"
        },
        "SIGN_SIGNAL": {
            "keywords": ["sign", "signal", "traffic light", "street sign", "broken sign",
                        "damaged sign", "lighting"],
            "severity_base": 50,
            "description": "Traffic sign or signal issue"
        },
    }

    URGENCY_KEYWORDS = {
        "immediate": 25,
        "emergency": 30,
        "urgent": 20,
        "dangerous": 20,
        "child": 15,
        "elderly": 10,
        "rush hour": 5,
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize 311 classifier with spaCy model."""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(f"Model {model_name} not found. Install with: python -m spacy download {model_name}")
            raise

        self._add_complaint_components()

    def _add_complaint_components(self):
        """Add custom components to spaCy pipeline."""

        if not Doc.has_extension("complaint_category"):
            Doc.set_extension("complaint_category", default=None)
        if not Doc.has_extension("urgency_score"):
            Doc.set_extension("urgency_score", default=0)
        if not Doc.has_extension("confidence_score"):
            Doc.set_extension("confidence_score", default=0)

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify a 311 complaint description.

        Args:
            text: Complaint description from 311 data

        Returns:
            ClassificationResult with category and urgency
        """
        doc = self.nlp(text)
        text_lower = text.lower()

        # Score each complaint category
        category_scores = {}
        matched_keywords = {}

        for category, config in self.COMPLAINT_CATEGORIES.items():
            score = 0
            keywords_found = []

            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += 1
                    keywords_found.append(keyword)

            if score > 0:
                category_scores[category] = score
                matched_keywords[category] = keywords_found

        # Determine primary category
        if category_scores:
            primary_category = max(category_scores, key=category_scores.get)
            total_possible = len(self.COMPLAINT_CATEGORIES[primary_category]["keywords"])
            confidence = min(100, (category_scores[primary_category] / total_possible) * 100)
        else:
            primary_category = "OTHER"
            confidence = 0

        # Calculate urgency score (analogous to severity for inspections)
        urgency = self.COMPLAINT_CATEGORIES.get(primary_category, {}).get("severity_base", 40)

        # Boost urgency based on urgency keywords
        for urgent_word, boost in self.URGENCY_KEYWORDS.items():
            if urgent_word in text_lower:
                urgency = min(100, urgency + boost)

        # Extract entities
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        # Build category details
        category_details = {
            "category": primary_category,
            "description": self.COMPLAINT_CATEGORIES.get(primary_category, {}).get("description", "Other complaint"),
            "keywords_matched": matched_keywords.get(primary_category, []),
            "all_scores": category_scores,
        }

        return ClassificationResult(
            text=text,
            primary_category=primary_category,
            confidence_score=confidence,
            severity_score=urgency,  # Called "severity" for consistency with inspection classifier
            extracted_entities=entities,
            keywords_matched=matched_keywords.get(primary_category, []),
            category_details=category_details
        )

    def batch_classify(self, texts: list[str]) -> list[ClassificationResult]:
        """
        Classify multiple 311 complaints.

        Args:
            texts: List of complaint descriptions

        Returns:
            List of ClassificationResult objects
        """
        results = []
        for text in texts:
            results.append(self.classify(text))
        return results

class TreeDamageClassifier:
    """Classify tree damage descriptions."""

    DAMAGE_TYPES = {
        "BRANCH_DAMAGE": {
            "keywords": ["branch", "limb", "broken branch", "hanging branch", "dead branch",
                        "fallen branch", "overhanging", "low branch"],
            "severity_base": 55,
            "description": "Branch damage or overgrowth"
        },
        "ROOT_DAMAGE": {
            "keywords": ["root", "roots", "root damage", "root lifting", "heave",
                        "pavement damage", "sidewalk damage"],
            "severity_base": 70,
            "description": "Root damage affecting sidewalk"
        },
        "DISEASE_PEST": {
            "keywords": ["disease", "pest", "insect", "sick", "dying", "dead tree",
                        "blight", "fungal", "mold", "decay"],
            "severity_base": 60,
            "description": "Disease or pest infestation"
        },
        "HAZARDOUS": {
            "keywords": ["hazard", "danger", "unsafe", "risk", "leaning", "unstable",
                        "split trunk", "hollow"],
            "severity_base": 80,
            "description": "Hazardous tree condition"
        },
        "MAINTENANCE": {
            "keywords": ["prune", "trim", "cut", "pruning", "maintenance", "overgrown",
                        "foliage", "shade"],
            "severity_base": 30,
            "description": "Routine maintenance needed"
        },
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(f"Model {model_name} not found")
            raise

    def classify(self, text: str) -> ClassificationResult:
        """Classify tree damage description."""
        doc = self.nlp(text)
        text_lower = text.lower()

        type_scores = {}
        matched_keywords = {}

        for dtype, config in self.DAMAGE_TYPES.items():
            score = 0
            keywords_found = []

            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += 1
                    keywords_found.append(keyword)

            if score > 0:
                type_scores[dtype] = score
                matched_keywords[dtype] = keywords_found

        if type_scores:
            primary_type = max(type_scores, key=type_scores.get)
            total_possible = len(self.DAMAGE_TYPES[primary_type]["keywords"])
            confidence = min(100, (type_scores[primary_type] / total_possible) * 100)
        else:
            primary_type = "OTHER"
            confidence = 0

        severity = self.DAMAGE_TYPES.get(primary_type, {}).get("severity_base", 40)

        entities = [(ent.text, ent.label_) for ent in doc.ents]

        return ClassificationResult(
            text=text,
            primary_category=primary_type,
            confidence_score=confidence,
            severity_score=severity,
            extracted_entities=entities,
            keywords_matched=matched_keywords.get(primary_type, []),
            category_details={
                "type": primary_type,
                "description": self.DAMAGE_TYPES.get(primary_type, {}).get("description", "Unknown"),
                "keywords_matched": matched_keywords.get(primary_type, []),
            }
        )

    def batch_classify(self, texts: list[str]) -> list[ClassificationResult]:
        return [self.classify(text) for text in texts]

class ConstructionInspectionClassifier:
    """Classify street construction inspection findings."""

    FINDING_TYPES = {
        "QUALITY_ISSUE": {
            "keywords": ["quality", "workmanship", "defective", "defect", "poor quality",
                        "inferior", "faulty", "inadequate"],
            "severity_base": 65,
            "description": "Work quality issues"
        },
        "SCHEDULE_DELAY": {
            "keywords": ["delay", "behind schedule", "behind", "slow progress",
                        "not progressing", "incomplete"],
            "severity_base": 45,
            "description": "Schedule delays"
        },
        "SAFETY_CONCERN": {
            "keywords": ["safety", "unsafe", "hazard", "hazardous", "danger", "risk",
                        "barrier", "traffic control", "protective equipment"],
            "severity_base": 80,
            "description": "Safety concern"
        },
        "PERMIT_VIOLATION": {
            "keywords": ["permit", "violation", "violation of", "not permitted", "unauthorized",
                        "outside scope", "unapproved"],
            "severity_base": 75,
            "description": "Permit or scope violation"
        },
        "ENVIRONMENTAL": {
            "keywords": ["dust", "noise", "pollution", "water", "runoff", "environmental",
                        "impact", "mitigation"],
            "severity_base": 55,
            "description": "Environmental concern"
        },
        "DOCUMENTED_COMPLETE": {
            "keywords": ["complete", "completed", "approved", "passed inspection",
                        "satisfactory", "compliant"],
            "severity_base": 10,
            "description": "Work satisfactory"
        },
    }

    def __init__(self, model_name: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.warning(f"Model {model_name} not found")
            raise

    def classify(self, text: str) -> ClassificationResult:
        """Classify construction inspection finding."""
        doc = self.nlp(text)
        text_lower = text.lower()

        type_scores = {}
        matched_keywords = {}

        for ftype, config in self.FINDING_TYPES.items():
            score = 0
            keywords_found = []

            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += 1
                    keywords_found.append(keyword)

            if score > 0:
                type_scores[ftype] = score
                matched_keywords[ftype] = keywords_found

        if type_scores:
            primary_type = max(type_scores, key=type_scores.get)
            total_possible = len(self.FINDING_TYPES[primary_type]["keywords"])
            confidence = min(100, (type_scores[primary_type] / total_possible) * 100)
        else:
            primary_type = "OTHER"
            confidence = 0

        severity = self.FINDING_TYPES.get(primary_type, {}).get("severity_base", 40)

        entities = [(ent.text, ent.label_) for ent in doc.ents]

        return ClassificationResult(
            text=text,
            primary_category=primary_type,
            confidence_score=confidence,
            severity_score=severity,
            extracted_entities=entities,
            keywords_matched=matched_keywords.get(primary_type, []),
            category_details={
                "type": primary_type,
                "description": self.FINDING_TYPES.get(primary_type, {}).get("description", "Unknown"),
                "keywords_matched": matched_keywords.get(primary_type, []),
            }
        )

    def batch_classify(self, texts: list[str]) -> list[ClassificationResult]:
        return [self.classify(text) for text in texts]

class TextClassifierPipeline:
    """Unified pipeline for all NYC DOT text classification across datasets."""

    def __init__(self):
        """Initialize all classifiers."""
        self.violation_classifier = InspectionViolationClassifier()
        self.complaint_classifier = Complaint311Classifier()
        self.tree_damage_classifier = TreeDamageClassifier()
        self.construction_classifier = ConstructionInspectionClassifier()

    def classify_dataset(self, df: pd.DataFrame, dataset_key: str, text_column: str = "description") -> pd.DataFrame:
        """
        Classify text in a dataframe based on dataset type.

        Args:
            df: Input dataframe
            dataset_key: Key from dataset registry (e.g., 'violations', 'complaints_311', 'tree_damage')
            text_column: Name of column containing text to classify

        Returns:
            Enriched dataframe with classification columns

        Supported datasets:
            - inspection, violations, dismissals, correspondences → InspectionViolationClassifier
            - complaints_311, ramp_complaints → Complaint311Classifier
            - tree_damage → TreeDamageClassifier
            - street_construction_inspections, street_closures_block, street_permits → ConstructionInspectionClassifier
        """
        if text_column not in df.columns:
            logger.warning(f"Column '{text_column}' not found in dataframe. Skipping classification.")
            return df

        # Route to appropriate classifier
        if dataset_key in ["inspection", "violations", "dismissals", "correspondences", "curb_metal_protruding"]:
            return self.classify_violations_dataframe(df, text_column)

        elif dataset_key in ["complaints_311", "ramp_complaints"]:
            return self.classify_complaints_dataframe(df, text_column)

        elif dataset_key == "tree_damage":
            return self.classify_tree_damage_dataframe(df, text_column)

        elif dataset_key in ["street_construction_inspections", "street_closures_block", "street_permits"]:
            return self.classify_construction_dataframe(df, text_column)

        else:
            logger.warning(f"No classifier configured for dataset '{dataset_key}'")
            return df

    def classify_violations_dataframe(self, df: pd.DataFrame, text_column: str = "description") -> pd.DataFrame:
        """Add classification columns for inspection violations."""
        results = self.violation_classifier.batch_classify(df[text_column].tolist())

        df_enriched = df.copy()
        df_enriched["violation_type"] = [r.primary_category for r in results]
        df_enriched["violation_severity"] = [r.severity_score for r in results]
        df_enriched["violation_confidence"] = [r.confidence_score for r in results]
        df_enriched["violation_entities"] = [r.extracted_entities for r in results]

        return df_enriched

    def classify_complaints_dataframe(self, df: pd.DataFrame, text_column: str = "description") -> pd.DataFrame:
        """Add classification columns for 311 complaints."""
        results = self.complaint_classifier.batch_classify(df[text_column].tolist())

        df_enriched = df.copy()
        df_enriched["complaint_category"] = [r.primary_category for r in results]
        df_enriched["complaint_urgency"] = [r.severity_score for r in results]
        df_enriched["complaint_confidence"] = [r.confidence_score for r in results]
        df_enriched["complaint_entities"] = [r.extracted_entities for r in results]

        return df_enriched

    def classify_tree_damage_dataframe(self, df: pd.DataFrame, text_column: str = "description") -> pd.DataFrame:
        """Add classification columns for tree damage."""
        results = self.tree_damage_classifier.batch_classify(df[text_column].tolist())

        df_enriched = df.copy()
        df_enriched["damage_type"] = [r.primary_category for r in results]
        df_enriched["damage_severity"] = [r.severity_score for r in results]
        df_enriched["damage_confidence"] = [r.confidence_score for r in results]

        return df_enriched

    def classify_construction_dataframe(self, df: pd.DataFrame, text_column: str = "description") -> pd.DataFrame:
        """Add classification columns for construction inspection findings."""
        results = self.construction_classifier.batch_classify(df[text_column].tolist())

        df_enriched = df.copy()
        df_enriched["finding_type"] = [r.primary_category for r in results]
        df_enriched["finding_severity"] = [r.severity_score for r in results]
        df_enriched["finding_confidence"] = [r.confidence_score for r in results]

        return df_enriched

    def summarize_violations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate violations by type and severity."""
        return (
            df.groupby("violation_type")
            .agg({
                "violation_severity": ["mean", "max", "min"],
                "violation_confidence": "mean",
                "description": "count"
            })
            .rename(columns={"description": "count"})
            .sort_values(("violation_severity", "mean"), ascending=False)
        )

    def summarize_complaints(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate complaints by category and urgency."""
        return (
            df.groupby("complaint_category")
            .agg({
                "complaint_urgency": ["mean", "max", "min"],
                "complaint_confidence": "mean",
                "description": "count"
            })
            .rename(columns={"description": "count"})
            .sort_values(("complaint_urgency", "mean"), ascending=False)
        )

    def summarize_tree_damage(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate tree damage by type and severity."""
        return (
            df.groupby("damage_type")
            .agg({
                "damage_severity": ["mean", "max", "min"],
                "damage_confidence": "mean",
                "description": "count"
            })
            .rename(columns={"description": "count"})
            .sort_values(("damage_severity", "mean"), ascending=False)
        )

    def summarize_construction_findings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate construction findings by type and severity."""
        return (
            df.groupby("finding_type")
            .agg({
                "finding_severity": ["mean", "max", "min"],
                "finding_confidence": "mean",
                "description": "count"
            })
            .rename(columns={"description": "count"})
            .sort_values(("finding_severity", "mean"), ascending=False)
        )
