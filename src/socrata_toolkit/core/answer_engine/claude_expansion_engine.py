from typing import Dict, Any, Optional
import json
from ..routing.models import ExpansionResult

class ClaudeExpansionEngine:
    """
    Claude-powered synthesis of query results (Tier 2).
    Generates insights and suggests follow-up questions.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude expansion engine.

        Args:
            api_key: Claude API key (for production use)
        """
        self.api_key = api_key

    def expand(
        self,
        question: str,
        kpi_name: str,
        query_results: Dict[str, Any]
    ) -> ExpansionResult:
        """
        Expand on query results with Claude synthesis.

        Args:
            question: Original analyst question
            kpi_name: Matched KPI name
            query_results: Query result data (JSON-serializable)

        Returns:
            ExpansionResult with synthesis + suggestions
        """
        synthesis = self._mock_synthesize(question, kpi_name, query_results)
        suggested = self._extract_suggestions(synthesis)

        return ExpansionResult(
            synthesis=synthesis,
            suggested_questions=suggested,
            query_results_summary=self._summarize_results(query_results)
        )

    def _mock_synthesize(self, question: str, kpi_name: str, results: Dict) -> str:
        """Mock Claude synthesis for testing"""
        return (
            f"Analysis of {kpi_name}: Based on query results, "
            f"{results} indicates a notable trend. "
            f"Consider exploring related metrics for deeper understanding."
        )

    def _extract_suggestions(self, synthesis: str) -> list:
        """Extract suggested questions from synthesis"""
        suggestions = []

        if "structural" in synthesis.lower():
            suggestions.append({
                "question": "What is causing the structural damage spike?",
                "related_kpi": "KPI-045",
                "command": "socrata nl-query 'structural damage trends'"
            })

        if "contractor" in synthesis.lower():
            suggestions.append({
                "question": "Are contractor quality metrics correlated?",
                "related_kpi": "KPI-067",
                "command": "socrata nl-query 'contractor performance metrics'"
            })

        return suggestions[:3]

    @staticmethod
    def _summarize_results(results: Dict) -> str:
        """Summarize query results for user"""
        if not results:
            return "No results"

        return json.dumps(results)[:200] + "..."


__all__ = ["ClaudeExpansionEngine"]
