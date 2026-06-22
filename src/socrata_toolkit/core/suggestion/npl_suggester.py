import re
from typing import Dict, List


class NPLSuggester:
    """
    NLP-based suggestion of follow-up questions.
    Matches synthesis text against research question registry.
    """

    # Keywords that trigger specific question suggestions
    KEYWORD_MAPPING = {
        'structural': 'KPI-045',
        'damage': 'KPI-045',
        'contractor': 'KPI-067',
        'quality': 'KPI-067',
        'seasonal': 'KPI-123',
        'trend': 'KPI-123',
        'ramp': 'KPI-200',
        'accessibility': 'KPI-200'
    }

    def __init__(self, research_questions: List[Dict]):
        """
        Initialize with research questions registry.

        Args:
            research_questions: List of {question_id, text, related_kpi}
        """
        self.questions = research_questions
        self._build_keyword_index()

    def _build_keyword_index(self):
        """Build index of keywords -> questions"""
        self.keyword_index = {}

        for q in self.questions:
            text = q.get('text', '').lower()
            words = re.findall(r'\b\w+\b', text)

            for word in words:
                if word not in self.keyword_index:
                    self.keyword_index[word] = []
                self.keyword_index[word].append(q)

    def suggest_next_questions(self, synthesis: str, limit: int = 3) -> List[Dict]:
        """
        Suggest follow-up questions based on synthesis text.

        Args:
            synthesis: Claude synthesis of query results
            limit: Max # of suggestions to return

        Returns:
            List of suggested questions with related KPIs
        """
        synthesis_lower = synthesis.lower()
        scored_questions = {}

        # Score questions by keyword overlap
        for question in self.questions:
            text = question.get('text', '').lower()
            words = re.findall(r'\b\w+\b', text)

            score = sum(1 for word in words if word in synthesis_lower)

            if score > 0:
                q_id = question.get('question_id')
                scored_questions[q_id] = (score, question)

        # Sort by score and return top-k
        sorted_qs = sorted(
            scored_questions.values(),
            key=lambda x: x[0],
            reverse=True
        )

        suggestions = []
        for score, q in sorted_qs[:limit]:
            suggestions.append({
                "question": q.get('text'),
                "related_kpi": q.get('related_kpi'),
                "command": f"socrata nl-query '{q.get('text')}'"
            })

        return suggestions


__all__ = ["NPLSuggester"]
