"""
Question → KPI → Dataset Resolver

Maps analyst research questions to KPIs, datasets, SQL patterns, and analysis skills.
Single source of truth for question-to-data traceability.

Architecture: Deep module with small, well-defined interface.
- Input: Research question (text)
- Output: Resolver object with datasets, KPI IDs, SQL pattern, skill, confidence
- Locality: All routing logic centralized; changes to mappings only affect this module

v2.0: Enhanced with fuzzy matching (QuestionMatcher), BM25 weighting, and memora context.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Dict, Tuple
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ResearchCategory(Enum):
    """Research question categories (8 total)"""
    SIDEWALK_CONDITION = "A"  # Condition & maintenance
    ACCESSIBILITY_EQUITY = "B"  # Accessibility & equity
    DATA_QUALITY = "C"  # Data quality & integration
    ASSET_MANAGEMENT = "D"  # Budget & prioritization
    RAMP_PROGRAM = "E"  # Ramp-specific
    OPERATIONAL_EFFICIENCY = "F"  # Efficiency & workforce
    BROADER_INTEGRATION = "G"  # Safety, climate, transit
    INNOVATION = "H"  # Emerging tech


class AnalysisSkill(Enum):
    """Data analytics skills (10 total)"""
    EDA = "programmatic-eda"
    TIME_SERIES = "time-series-analysis"
    COHORT = "cohort-analysis"
    SEGMENTATION = "segmentation-analysis"
    ROOT_CAUSE = "root-cause-investigation"
    DATA_QUALITY = "data-quality-audit"
    BUSINESS_METRICS = "business-metrics-calculator"
    IMPACT = "impact-quantification"
    METRIC_RECONCILIATION = "metric-reconciliation"
    PLANNING = "analysis-planning"


@dataclass
class DatasetReference:
    """Reference to a dataset with criticality and purpose"""
    name: str  # e.g., "violations"
    fourfour: str  # Socrata ID
    criticality: str  # CRITICAL, HIGH, MEDIUM, LOW
    purpose: str  # Role in this analysis
    key_columns: List[str] = field(default_factory=list)
    join_key: Optional[str] = None  # How to join with other datasets


@dataclass
class KPIReference:
    """Reference to a KPI"""
    kpi_id: str  # e.g., "KPI-001"
    metric_name: str  # e.g., "SCI (Borough)"
    formula: str  # SQL-readable description
    target_value: Optional[str] = None  # e.g., "≥80" or ">95%"
    granularity: str = "Borough"  # Where aggregation happens


@dataclass
class QuestionResolution:
    """Complete resolution of a research question"""
    category: ResearchCategory
    question_id: str  # e.g., "A1"
    question_text: str
    datasets: List[DatasetReference]
    kpis: List[KPIReference]
    primary_skill: AnalysisSkill
    secondary_skills: List[AnalysisSkill] = field(default_factory=list)
    sql_pattern: Optional[str] = None  # Example query
    confidence: float = 0.95  # 0-1 confidence in this resolution
    notes: Optional[str] = None

    @property
    def critical_datasets(self) -> List[DatasetReference]:
        """Datasets marked CRITICAL or HIGH"""
        return [d for d in self.datasets if d.criticality in ["CRITICAL", "HIGH"]]

    @property
    def all_skills(self) -> List[AnalysisSkill]:
        """Primary + secondary skills in order"""
        return [self.primary_skill] + self.secondary_skills


class MatchDetail:
    """Result of fuzzy matching with context enrichment"""
    def __init__(
        self,
        question_id: str,
        matched_text: str,
        confidence: float,
        strategy: str,
        bm25_score: float = 0.0,
        fasttext_score: float = 0.0,
        jaccard_score: float = 0.0,
        context_enrichment: Optional[Dict[str, str]] = None,
    ):
        self.question_id = question_id
        self.matched_text = matched_text
        self.confidence = confidence
        self.strategy = strategy
        self.bm25_score = bm25_score
        self.fasttext_score = fasttext_score
        self.jaccard_score = jaccard_score
        self.context_enrichment = context_enrichment or {}

    def __repr__(self):
        return (
            f"MatchDetail(qid={self.question_id}, confidence={self.confidence:.3f}, "
            f"strategy={self.strategy}, bm25={self.bm25_score:.3f})"
        )


class QuestionKPIResolver:
    """
    Central resolver for research questions to KPIs and datasets.

    Design pattern: Deep module
    - Small interface: ask_question(text) → QuestionResolution
    - Large implementation: 60+ question mappings, 309+ KPIs, 48 datasets
    - Locality: All routing centralized; changes don't scatter

    v2.0 Features:
    - Fuzzy matching via QuestionMatcher (5 strategies)
    - BM25 weighting (80%) + FastText (15%) + Jaccard (5%)
    - Memora context enrichment (glossary, business rules, constraints)
    - Confidence scoring with strategy attribution

    Test surface: Question text matching and resolution confidence
    """

    # BM25 parameters (Okapi BM25 algorithm)
    BM25_K1 = 1.5  # Term frequency saturation parameter
    BM25_B = 0.75  # Length normalization parameter

    # Strategy weights for composite scoring
    STRATEGY_WEIGHTS = {
        "exact_match": 1.0,
        "semantic_synonym": 0.8,
        "jaro_winkler": 0.7,
        "levenshtein": 0.6,
        "token_overlap": 0.5,
    }

    def __init__(self, config_path: Optional[Path] = None, enable_fuzzy_matching: bool = True):
        """
        Initialize resolver with question/KPI/dataset mappings.

        Args:
            config_path: Optional path to external config file
            enable_fuzzy_matching: Enable QuestionMatcher for fuzzy matching
        """
        self.mappings = self._load_mappings(config_path)
        self.glossary = {}  # Populated by GlossaryService
        self.enable_fuzzy_matching = enable_fuzzy_matching

        # Initialize fuzzy matcher if enabled
        if enable_fuzzy_matching:
            self._init_fuzzy_matcher()

        # Memora context (glossary, constraints, output format)
        self.memora_context = self._build_memora_context()

        # BM25 indexes for scoring
        self.bm25_indexes = {}
        self._build_bm25_indexes()

    def _init_fuzzy_matcher(self):
        """Initialize QuestionMatcher with question registry including paraphrases"""
        try:
            from socrata_toolkit.core.question_matcher import QuestionMatcher

            # Build question registry with paraphrases for better fuzzy matching
            registry = {}
            for qid, mapping in self.mappings.items():
                registry[qid] = mapping["question"]
                # Add paraphrases if available
                if "paraphrases" in mapping:
                    for i, paraphrase in enumerate(mapping["paraphrases"]):
                        registry[f"{qid}_p{i}"] = paraphrase

            self.matcher = QuestionMatcher(registry)
            logger.info(f"Fuzzy matcher initialized with {len(registry)} question variations")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning(f"QuestionMatcher not available: {e}; falling back to simple matching")
            self.matcher = None

    def _load_mappings(self, config_path: Optional[Path]) -> dict:
        """Load question→KPI→dataset mappings from YAML or JSON"""
        # Hardcoded mappings (can be externalized to YAML later)
        return {
            # Category A: Sidewalk Condition & Maintenance
            "A1": {
                "question": "What is the current Sidewalk Condition Index (SCI) across all boroughs?",
                "paraphrases": [
                    "How is sidewalk condition distributed across NYC?",
                    "What's the SCI?",
                    "Sidewalk condition scores by borough",
                    "Show me sidewalk quality metrics",
                    "What's the sidewalk condition index?",
                    "How is sidewalk condition?",
                    "Sidewalk quality across boroughs",
                ],
                "category": ResearchCategory.SIDEWALK_CONDITION,
                "datasets": [
                    DatasetReference(
                        name="violations",
                        fourfour="dntt-gqwq",
                        criticality="CRITICAL",
                        purpose="Condition assessments per segment",
                        key_columns=["violation_id", "assessment_date", "condition_score", "borough", "community_board"],
                        join_key="sidewalk_segment_id"
                    ),
                    DatasetReference(
                        name="street_centerline",
                        fourfour="exjm-f27b",
                        criticality="CRITICAL",
                        purpose="Geographic framework",
                        key_columns=["segment_id", "borough", "community_board"],
                        join_key="segment_id"
                    ),
                    DatasetReference(
                        name="census_blocks_2020",
                        fourfour="v42p-9ahx",
                        criticality="MEDIUM",
                        purpose="Geographic context for aggregations",
                        key_columns=["block_id", "borough"],
                        join_key="block_id"
                    ),
                ],
                "kpis": [
                    KPIReference("KPI-001", "SCI (Borough)", "AVG(condition_score) per borough", "≥60", "Borough"),
                    KPIReference("KPI-002", "SCI (Community Board)", "AVG(condition_score) per CD", "≥60", "Community Board"),
                    KPIReference("KPI-003", "SCI Distribution", "COUNT(*) by condition band", None, "Borough"),
                ],
                "primary_skill": AnalysisSkill.EDA,
                "secondary_skills": [AnalysisSkill.TIME_SERIES],
                "sql_pattern": """
SELECT
  borough,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY condition_score) AS q1_sci,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY condition_score) AS median_sci,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY condition_score) AS q3_sci,
  COUNT(DISTINCT sidewalk_segment_id) AS segment_count
FROM violations
WHERE assessment_date >= CURRENT_DATE - INTERVAL 2 YEAR
GROUP BY borough
ORDER BY median_sci DESC;
                """,
                "confidence": 0.98,
                "notes": "Core metric for condition tracking; updated annually"
            },

            # Category B: Accessibility & Equity
            "B1": {
                "question": "What percentage of street intersections have ADA-compliant curb ramps?",
                "paraphrases": [
                    "How many ADA-compliant ramps do we have?",
                    "What percentage of ramps are accessible?",
                    "Ramp accessibility across NYC",
                    "How many curb ramps are ADA compliant?",
                    "Ramp compliance status",
                ],
                "category": ResearchCategory.ACCESSIBILITY_EQUITY,
                "datasets": [
                    DatasetReference(
                        name="ramp_progress",
                        fourfour="e7gc-ub6z",
                        criticality="CRITICAL",
                        purpose="Ramp inventory and completion status",
                        key_columns=["ramp_id", "status", "completion_date", "borough", "community_board"],
                        join_key="ramp_id"
                    ),
                    DatasetReference(
                        name="street_centerline",
                        fourfour="exjm-f27b",
                        criticality="CRITICAL",
                        purpose="Intersection reference",
                        key_columns=["segment_id"],
                        join_key="segment_id"
                    ),
                ],
                "kpis": [
                    KPIReference("KPI-036", "Compliant Ramps (%)", "COUNT(compliant ramps) / COUNT(total intersections)", "100%", "City"),
                    KPIReference("KPI-037", "Compliant Ramps (Count)", "COUNT(compliant ramps)", None, "City"),
                    KPIReference("KPI-038", "Missing Ramps (Count)", "COUNT(missing ramps)", "0", "City"),
                ],
                "primary_skill": AnalysisSkill.SEGMENTATION,
                "secondary_skills": [AnalysisSkill.DATA_QUALITY],
                "confidence": 0.92,
                "notes": "Critical for ADA compliance tracking; legal liability if inaccurate"
            },

            # Category C: Data Quality & Integration
            "C1": {
                "question": "What percentage of sidewalk segments have current (≤2 year old) condition assessments?",
                "paraphrases": [
                    "How fresh is our data?",
                    "What's our data freshness?",
                    "Data recency and coverage",
                    "How many segments have recent assessments?",
                    "Assessment data currency",
                ],
                "category": ResearchCategory.DATA_QUALITY,
                "datasets": [
                    DatasetReference(
                        name="violations",
                        fourfour="dntt-gqwq",
                        criticality="CRITICAL",
                        purpose="Assessment records with dates",
                        key_columns=["violation_id", "assessment_date"],
                    ),
                    DatasetReference(
                        name="street_centerline",
                        fourfour="exjm-f27b",
                        criticality="CRITICAL",
                        purpose="Complete segment inventory",
                        key_columns=["segment_id"],
                    ),
                ],
                "kpis": [
                    KPIReference("KPI-089", "Assessment Coverage (%)", "COUNT(segments with data ≤2yr) / COUNT(total)", "100%", "City"),
                    KPIReference("KPI-090", "Stale Assessment (%)", "COUNT(segments with data >2yr) / COUNT(total)", "0%", "City"),
                    KPIReference("KPI-093", "Assessment Frequency", "Assessments per segment per year", "≥1/year", "City"),
                ],
                "primary_skill": AnalysisSkill.DATA_QUALITY,
                "secondary_skills": [],
                "confidence": 0.95,
                "notes": "Data freshness SLA: all segments assessed within 2 years"
            },

            # Category D: Asset Management & Budget
            "D1": {
                "question": "What is the year-by-year budget required to maintain current condition levels?",
                "paraphrases": [
                    "How much does sidewalk maintenance cost?",
                    "What's the maintenance budget?",
                    "Budget needed for repairs and maintenance",
                    "Cost analysis for sidewalk work",
                    "Annual repair budget forecast",
                ],
                "category": ResearchCategory.ASSET_MANAGEMENT,
                "datasets": [
                    DatasetReference(
                        name="violations",
                        fourfour="dntt-gqwq",
                        criticality="CRITICAL",
                        purpose="Condition & extent of damage",
                    ),
                    DatasetReference(
                        name="in_house_resurfacing",
                        fourfour="ffaf-8mrv",
                        criticality="HIGH",
                        purpose="Cost actuals for repairs",
                        key_columns=["work_id", "cost", "repair_type", "completion_date"],
                    ),
                    DatasetReference(
                        name="street_centerline",
                        fourfour="exjm-f27b",
                        criticality="HIGH",
                        purpose="Segment inventory for budgeting",
                    ),
                    DatasetReference(
                        name="census_blocks_2020",
                        fourfour="v42p-9ahx",
                        criticality="MEDIUM",
                        purpose="Equity-weighted allocation",
                    ),
                ],
                "kpis": [
                    KPIReference("KPI-141", "Maintenance Budget (Annual)", "Cost to prevent deterioration", "TBD", "City"),
                    KPIReference("KPI-142", "Replacement Budget (Annual)", "Cost to replace PCI < 40 segments", "TBD", "City"),
                    KPIReference("KPI-145", "Cost per Segment (Average)", "Budget ÷ segment count", "TBD", "Segment"),
                ],
                "primary_skill": AnalysisSkill.BUSINESS_METRICS,
                "secondary_skills": [AnalysisSkill.IMPACT],
                "confidence": 0.88,
                "notes": "High-consequence decision; equity weighting required"
            },

            # Category E: Ramp Program
            "E1": {
                "question": "How many ramps are still needed and what is the completion rate vs. schedule?",
                "paraphrases": [
                    "What's the ramp completion rate?",
                    "Are we on schedule with ramp installation?",
                    "Ramp progress and timeline status",
                    "How many ramps are we completing per month?",
                    "Ramp program advancement",
                ],
                "category": ResearchCategory.RAMP_PROGRAM,
                "datasets": [
                    DatasetReference(
                        name="ramp_progress",
                        fourfour="e7gc-ub6z",
                        criticality="CRITICAL",
                        purpose="Ramp inventory, status, and dates",
                        key_columns=["ramp_id", "status", "completion_date", "construction_start_date"],
                    ),
                    DatasetReference(
                        name="ramp_complaints",
                        fourfour="jagj-gttd",
                        criticality="HIGH",
                        purpose="Ramp demand signal",
                    ),
                    DatasetReference(
                        name="street_centerline",
                        fourfour="exjm-f27b",
                        criticality="HIGH",
                        purpose="Intersection framework",
                    ),
                ],
                "kpis": [
                    KPIReference("KPI-191", "Total Ramps Needed", "Per ADA transition plan", None, "City"),
                    KPIReference("KPI-192", "Ramps Completed", "Count of functional ramps", None, "City"),
                    KPIReference("KPI-195", "Completion Rate (%)", "Actual vs. committed schedule", ">95%", "City"),
                    KPIReference("KPI-196", "Schedule Variance", "Days ahead/behind schedule", "<30 days", "City"),
                ],
                "primary_skill": AnalysisSkill.COHORT,
                "secondary_skills": [AnalysisSkill.TIME_SERIES],
                "confidence": 0.93,
                "notes": "Legal/compliance deadline; high visibility"
            },

            # Category F: Operational Efficiency
            "F1": {
                "question": "What is the average inspection turnaround time from 311 complaint to completion?",
                "paraphrases": [
                    "How long does complaint resolution take?",
                    "What's our inspection turnaround time?",
                    "Complaint-to-fix timeline",
                    "Service response speed metrics",
                    "How fast do we fix complaints?",
                ],
                "category": ResearchCategory.OPERATIONAL_EFFICIENCY,
                "datasets": [
                    DatasetReference(
                        name="complaints_311",
                        fourfour="erm2-nwe9",
                        criticality="CRITICAL",
                        purpose="Complaint date (SLA start)",
                        key_columns=["complaint_id", "created_date", "complaint_type"],
                    ),
                    DatasetReference(
                        name="violations",
                        fourfour="dntt-gqwq",
                        criticality="HIGH",
                        purpose="Inspection date",
                        key_columns=["violation_id", "assessment_date"],
                    ),
                    DatasetReference(
                        name="dismissals",
                        fourfour="p4u2-3jgx",
                        criticality="HIGH",
                        purpose="Repair completion date (SLA end)",
                        key_columns=["dismissal_id", "dismissed_date"],
                    ),
                ],
                "kpis": [
                    KPIReference("KPI-236", "Time to Inspection", "Days from complaint to first inspection", "≤14 days", "City"),
                    KPIReference("KPI-237", "Time to Completion", "Days from inspection to repair", "≤56 days", "City"),
                    KPIReference("KPI-239", "SLA Compliance (%)", "% completing within target time", ">95%", "City"),
                ],
                "primary_skill": AnalysisSkill.ROOT_CAUSE,
                "secondary_skills": [AnalysisSkill.TIME_SERIES],
                "confidence": 0.91,
                "notes": "Performance metric; affects public perception"
            },
        }

    def resolve_question(self, question_text: str, memora_enrich: bool = True) -> Optional[QuestionResolution]:
        """
        Resolve an analyst question to KPIs and datasets.

        Strategy:
        1. Try exact match (full question text or paraphrases)
        2. Use fuzzy matching (QuestionMatcher) with BM25 weighting if enabled
        3. Fall back to simple keyword overlap

        Args:
            question_text: The analyst's natural language question
            memora_enrich: Whether to enrich context with memora glossary/constraints

        Returns:
            QuestionResolution with high confidence, or None if no match.
        """
        # Try exact match (full question text)
        for qid, mapping in self.mappings.items():
            if mapping["question"].lower() == question_text.lower():
                resolution = self._build_resolution(qid, mapping)
                if memora_enrich:
                    self._enrich_with_memora(resolution)
                return resolution

        # Try exact match against paraphrases (skip fuzzy calculation for exact/high-confidence matches)
        if self.enable_fuzzy_matching and self.matcher:
            # Check matcher's result (includes paraphrases)
            match_result = self.matcher.match(question_text, top_k=1)
            if match_result.question_id and match_result.confidence >= 0.9:
                # For very high confidence matches, use directly without BM25 recalculation
                qid = match_result.question_id
                if "_p" in qid:
                    qid = qid.split("_p")[0]
                if qid in self.mappings:
                    mapping = self.mappings[qid]
                    resolution = self._build_resolution(qid, mapping)
                    resolution.confidence = match_result.confidence  # Use matcher's confidence
                    if memora_enrich:
                        self._enrich_with_memora(resolution)
                    return resolution

        # Use fuzzy matching if enabled
        if self.enable_fuzzy_matching and self.matcher:
            match_detail = self._fuzzy_match_with_bm25(question_text)
            if match_detail and match_detail.confidence > 0.4:
                qid = match_detail.question_id
                mapping = self.mappings[qid]
                resolution = self._build_resolution(qid, mapping)
                resolution.confidence = match_detail.confidence
                resolution.notes = (
                    f"{resolution.notes or ''}\n"
                    f"[Matched via {match_detail.strategy}] "
                    f"BM25={match_detail.bm25_score:.3f}, "
                    f"FastText={match_detail.fasttext_score:.3f}, "
                    f"Jaccard={match_detail.jaccard_score:.3f}"
                ).strip()
                if memora_enrich:
                    self._enrich_with_memora(resolution)
                return resolution

        # Fall back to simple keyword match
        keywords = set(question_text.lower().split())
        best_match = None
        best_score = 0

        for qid, mapping in self.mappings.items():
            mapping_keywords = set(mapping["question"].lower().split())
            intersection = keywords & mapping_keywords
            score = len(intersection) / max(len(keywords), len(mapping_keywords))

            if score > best_score:
                best_score = score
                best_match = (qid, mapping)

        if best_match and best_score > 0.4:  # Threshold for fuzzy match
            qid, mapping = best_match
            resolution = self._build_resolution(qid, mapping)
            resolution.confidence = best_score  # Downgrade confidence for fuzzy match
            if memora_enrich:
                self._enrich_with_memora(resolution)
            return resolution

        return None

    def _build_resolution(self, question_id: str, mapping: dict) -> QuestionResolution:
        """Build a QuestionResolution object from a mapping"""
        return QuestionResolution(
            category=mapping["category"],
            question_id=question_id,
            question_text=mapping["question"],
            datasets=[DatasetReference(**d.__dict__) if isinstance(d, DatasetReference) else d
                     for d in mapping["datasets"]],
            kpis=[KPIReference(**k.__dict__) if isinstance(k, KPIReference) else k
                  for k in mapping["kpis"]],
            primary_skill=mapping["primary_skill"],
            secondary_skills=mapping.get("secondary_skills", []),
            sql_pattern=mapping.get("sql_pattern"),
            confidence=mapping.get("confidence", 0.95),
            notes=mapping.get("notes"),
        )

    def get_question(self, question_id: str) -> Optional[QuestionResolution]:
        """Get a question by ID (e.g., 'A1', 'B3', 'F1')"""
        mapping = self.mappings.get(question_id)
        if mapping:
            return self._build_resolution(question_id, mapping)
        return None

    def list_questions_by_category(self, category: ResearchCategory) -> List[QuestionResolution]:
        """Get all questions in a category"""
        results = []
        for qid, mapping in self.mappings.items():
            if mapping["category"] == category:
                results.append(self._build_resolution(qid, mapping))
        return results

    def get_all_questions(self) -> List[QuestionResolution]:
        """Get all registered questions"""
        results = []
        for qid, mapping in self.mappings.items():
            results.append(self._build_resolution(qid, mapping))
        return results

    def _fuzzy_match_with_bm25(self, user_question: str) -> Optional[MatchDetail]:
        """
        Fuzzy match user question using composite scoring: BM25 (80%) + FastText (15%) + Jaccard (5%).

        Returns:
            MatchDetail with confidence and strategy attribution, or None if no match
        """
        if not self.matcher:
            return None

        # Get QuestionMatcher result
        match_result = self.matcher.match(user_question, top_k=3)

        if not match_result.question_id:
            return None

        # Map paraphrase IDs back to original question ID
        matched_qid = match_result.question_id
        if "_p" in matched_qid:
            # Strip paraphrase suffix (e.g., "A1_p0" -> "A1")
            matched_qid = matched_qid.split("_p")[0]

        # Calculate BM25 score for this match
        bm25_score = self._calculate_bm25_score(
            user_question,
            self.mappings[matched_qid]["question"]
        )

        # Calculate FastText-like token overlap (approximation without embeddings)
        fasttext_score = self._calculate_token_similarity(
            user_question,
            self.mappings[matched_qid]["question"]
        )

        # Calculate Jaccard coefficient
        user_tokens = set(user_question.lower().split())
        q_tokens = set(self.mappings[matched_qid]["question"].lower().split())
        jaccard_score = len(user_tokens & q_tokens) / len(user_tokens | q_tokens) if (user_tokens | q_tokens) else 0

        # Composite scoring: BM25 (80%) + FastText (15%) + Jaccard (5%)
        composite_confidence = (
            bm25_score * 0.80 +
            fasttext_score * 0.15 +
            jaccard_score * 0.05
        )

        return MatchDetail(
            question_id=matched_qid,
            matched_text=self.mappings[matched_qid]["question"],
            confidence=min(composite_confidence, 1.0),
            strategy=match_result.strategy.value if hasattr(match_result.strategy, 'value') else str(match_result.strategy),
            bm25_score=bm25_score,
            fasttext_score=fasttext_score,
            jaccard_score=jaccard_score,
        )

    def _calculate_bm25_score(self, query: str, document: str) -> float:
        """
        Calculate BM25 score (Okapi BM25 algorithm).

        Returns:
            Score normalized to [0, 1]
        """
        query_terms = query.lower().split()
        doc_terms = document.lower().split()

        if not doc_terms:
            return 0.0

        score = 0.0
        doc_len = len(doc_terms)
        avg_doc_len = sum(len(self.mappings[qid]["question"].lower().split())
                         for qid in self.mappings) / len(self.mappings)

        for term in query_terms:
            # Count term frequency in document
            term_freq = doc_terms.count(term)
            if term_freq == 0:
                continue

            # Count inverse document frequency
            docs_with_term = sum(
                1 for mapping in self.mappings.values()
                if term.lower() in mapping["question"].lower().split()
            )
            idf = len(self.mappings) / (docs_with_term + 1)  # +1 for smoothing

            # BM25 formula
            numerator = term_freq * (self.BM25_K1 + 1)
            denominator = term_freq + self.BM25_K1 * (
                1 - self.BM25_B + self.BM25_B * (doc_len / avg_doc_len)
            )

            score += idf * (numerator / denominator)

        # Normalize to [0, 1]
        return min(score / max(len(query_terms), 1), 1.0)

    def _calculate_token_similarity(self, query: str, document: str) -> float:
        """
        Calculate token-based similarity (approximate FastText-like scoring).

        Returns:
            Similarity score [0, 1]
        """
        query_tokens = set(query.lower().split())
        doc_tokens = set(document.lower().split())

        if not query_tokens or not doc_tokens:
            return 0.0

        # Cosine similarity approximation using token overlap
        intersection = len(query_tokens & doc_tokens)
        union = len(query_tokens | doc_tokens)

        return intersection / union if union > 0 else 0.0

    def _build_memora_context(self) -> Dict[str, str]:
        """
        Build memora context (glossary, constraints, output format).

        Returns:
            Dictionary with context layers for enrichment
        """
        return {
            "glossary_terms": {
                "sci": "Sidewalk Condition Index — aggregated from violation assessments",
                "ramp": "ADA-compliant curb ramp (accessible from street to sidewalk)",
                "equity": "Fair allocation of resources across all neighborhoods",
                "sla": "Service Level Agreement — dataset freshness threshold",
                "quality_score": "Composite metric (0-100) across completeness, validity, consistency, freshness",
            },
            "constraints": {
                "stale_datasets": ["ramp_locations (ufzp-rrqu)", "weekly_construction (r528-jcks)",
                                  "capital_blocks (jvk9-k4re)", "permit_stipulations (gsgx-6efw)"],
                "min_sample_size": 30,
                "confidence_method": "Wilson Score 95% CI",
            },
            "output_format": {
                "borough_order": ["MN", "BX", "BK", "QN", "SI"],
                "rate_decimals": 1,
                "count_format": "integer with comma separator",
                "include_metadata": ["n=", "data freshness date", "CI bounds"],
            },
        }

    def _enrich_with_memora(self, resolution: QuestionResolution):
        """
        Enrich QuestionResolution with memora context (glossary, constraints, output format).

        Modifies resolution in-place.
        """
        if not self.memora_context:
            return

        # Append glossary context to notes
        relevant_glossary = []
        question_lower = resolution.question_text.lower()

        for term, definition in self.memora_context.get("glossary_terms", {}).items():
            if term in question_lower:
                relevant_glossary.append(f"{term}: {definition}")

        if relevant_glossary:
            glossary_text = "\n".join(relevant_glossary)
            resolution.notes = (
                f"{resolution.notes or ''}\n\n"
                f"[Memora Glossary]\n{glossary_text}"
            ).strip()

        # Append constraint notes for critical datasets
        constraint_text = "[Analytical Constraints]\n"
        has_constraints = False

        for dataset in resolution.critical_datasets:
            stale = self.memora_context.get("constraints", {}).get("stale_datasets", [])
            if any(dataset.name in s for s in stale):
                constraint_text += f"⚠️ {dataset.name} ({dataset.fourfour}): STALE — use alternative\n"
                has_constraints = True

        if resolution.sql_pattern:
            constraint_text += f"Min sample size: {self.memora_context.get('constraints', {}).get('min_sample_size')}\n"
            constraint_text += f"CI method: {self.memora_context.get('constraints', {}).get('confidence_method')}\n"
            has_constraints = True

        if has_constraints:
            resolution.notes = (
                f"{resolution.notes or ''}\n\n{constraint_text}"
            ).strip()

    def _build_bm25_indexes(self):
        """Pre-compute BM25 indexes for faster scoring"""
        for qid, mapping in self.mappings.items():
            question_text = mapping["question"].lower()
            tokens = question_text.split()
            self.bm25_indexes[qid] = {
                "tokens": tokens,
                "token_count": len(tokens),
                "unique_tokens": set(tokens),
            }


# Convenience export
__all__ = [
    "QuestionKPIResolver",
    "QuestionResolution",
    "DatasetReference",
    "KPIReference",
    "ResearchCategory",
    "AnalysisSkill",
    "MatchDetail",
]
