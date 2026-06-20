from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class MatchResult:
    """Result of fuzzy question matching (Tier 1 routing)"""
    question_id: str
    confidence: float  # 0.0-1.0
    strategy: str  # 'exact', 'bm25', 'fasttext', 'jaccard', 'claude', 'ensemble'
    source: str  # 'programmatic', 'claude', 'hybrid_router'
    alternatives: List[str] = field(default_factory=list)  # Backup matches

@dataclass
class AnswerResult:
    """Pre-built answer (Tier 1 output)"""
    kpi_id: str
    kpi_name: str
    summary: str
    datasets: List[Dict[str, str]]  # [{key, fourfour, role}]
    sql_pattern: str
    visualizations: List[str]
    confidence: float
    source: str
    related_kpis: List[str] = field(default_factory=list)

@dataclass
class ExpansionResult:
    """Claude expansion output (Tier 2)"""
    synthesis: str
    suggested_questions: List[Dict[str, str]]  # [{question, related_kpi, command}]
    query_results_summary: str
