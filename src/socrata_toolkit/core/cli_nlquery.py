import json
from typing import Dict, List, Optional
from .routing.hybrid_router import HybridRouter
from .routing.programmatic_router import ProgrammaticRouter
from .routing.claude_semantic_router import ClaudeSemanticRouter
from .answer_engine.prebuilt_answer_engine import PreBuiltAnswerEngine
from .answer_engine.claude_expansion_engine import ClaudeExpansionEngine
from .suggestion.npl_suggester import NPLSuggester
from .feedback.feedback_collector import FeedbackCollector

def run_nl_query(
    question: str,
    kpi_registry: Dict,
    research_questions: Optional[List[Dict]] = None,
    embeddings_cache: Optional[Dict] = None,
    expand: bool = False,
    mark_helpful: bool = False,
    mark_wrong: bool = False,
    corrected_kpi_id: Optional[str] = None
) -> Dict:
    """
    Execute natural language query with optional Tier 2 expansion.

    Args:
        question: Analyst's natural language question
        kpi_registry: Full KPI registry
        research_questions: Research questions for suggestions (required if expand=True)
        embeddings_cache: Claude embeddings cache (required for router)
        expand: If True, execute Tier 2 (Claude expansion + suggestions)
        mark_helpful: If True, mark result as helpful
        mark_wrong: If True, mark result as wrong
        corrected_kpi_id: Corrected KPI ID if mark_wrong=True

    Returns:
        Dict with Tier 1 + optional Tier 2 output
    """
    if embeddings_cache is None:
        embeddings_cache = {}
    if research_questions is None:
        research_questions = []

    # Initialize components
    prog_router = ProgrammaticRouter(kpi_registry)
    claude_router = ClaudeSemanticRouter(kpi_registry, embeddings_cache)
    hybrid_router = HybridRouter(prog_router, claude_router)
    answer_engine = PreBuiltAnswerEngine(kpi_registry)

    # Execute Tier 1
    match_result = hybrid_router.match(question)

    if match_result.question_id is None:
        tier1_output = {
            "matched_kpi": None,
            "confidence": 0.0,
            "datasets": [],
            "sql_pattern": None,
            "visualizations": [],
            "error": "No matching KPI found"
        }
    else:
        answer = answer_engine.get_answer(match_result.question_id)
        tier1_output = {
            "matched_kpi": answer.kpi_id,
            "kpi_name": answer.kpi_name,
            "summary": answer.summary,
            "confidence": match_result.confidence,
            "datasets": answer.datasets,
            "sql_pattern": answer.sql_pattern,
            "visualizations": answer.visualizations,
            "routing_source": match_result.source,
            "related_kpis": answer.related_kpis
        }

    # Tier 2 (optional)
    output = tier1_output.copy()

    if expand and match_result.question_id is not None:
        expansion_engine = ClaudeExpansionEngine()
        suggester = NPLSuggester(research_questions)

        # Mock query results (in production: execute SQL)
        mock_results = {"count": 120, "trend": "increasing"}
        expansion = expansion_engine.expand(question, answer.kpi_name, mock_results)
        suggestions = suggester.suggest_next_questions(expansion.synthesis)

        output['tier_2_expansion'] = {
            "claude_synthesis": expansion.synthesis,
            "query_results_summary": expansion.query_results_summary,
            "suggested_questions": suggestions
        }

    # Feedback (optional)
    if mark_helpful or mark_wrong:
        collector = FeedbackCollector()
        if mark_helpful:
            collector.mark_helpful(question, match_result.question_id)
        elif mark_wrong:
            collector.mark_wrong(question, match_result.question_id, corrected_kpi_id)

        output['feedback_recorded'] = True

    return output


__all__ = ["run_nl_query"]
