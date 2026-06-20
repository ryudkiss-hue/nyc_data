from typing import List
from .models import MatchResult
from .programmatic_router import ProgrammaticRouter
from .claude_semantic_router import ClaudeSemanticRouter

class HybridRouter:
    """
    Orchestrates programmatic and Claude routers in ensemble.

    Strategy:
    - Run both in parallel
    - If both match same KPI: HIGH_CONFIDENCE (ensemble score = avg)
    - If they disagree: REQUIRES_CLARIFICATION (return both candidates)
    """

    def __init__(
        self,
        programmatic_router: ProgrammaticRouter,
        claude_router: ClaudeSemanticRouter,
        threshold: float = 0.70,
        adaptive: bool = True
    ):
        """
        Initialize hybrid router.

        Args:
            programmatic_router: BM25/FastText/Jaccard router
            claude_router: Claude embedding router
            threshold: Confidence threshold for accepting results (configurable)
            adaptive: If True, threshold adapts based on feedback
        """
        self.programmatic = programmatic_router
        self.claude = claude_router
        self.threshold = threshold
        self.adaptive = adaptive

    def match(self, user_question: str) -> MatchResult:
        """
        Match question using both strategies and ensemble results.
        """
        # Run both routers
        prog_result = self.programmatic.match(user_question)
        claude_result = self.claude.match(user_question)

        # Handle case where one or both fail
        if prog_result.question_id is None and claude_result.question_id is None:
            return MatchResult(
                question_id=None,
                confidence=0.0,
                strategy='none',
                source='hybrid_no_match'
            )

        if prog_result.question_id is None:
            prog_result = claude_result
        elif claude_result.question_id is None:
            claude_result = prog_result

        # Check agreement
        if prog_result.question_id == claude_result.question_id:
            # Agreement: ensemble confidence
            ensemble_confidence = (prog_result.confidence + claude_result.confidence) / 2

            return MatchResult(
                question_id=prog_result.question_id,
                confidence=ensemble_confidence,
                strategy='ensemble_agreed',
                source=f'hybrid_agreement (programmatic={prog_result.confidence:.2f}, claude={claude_result.confidence:.2f})',
                alternatives=[]
            )
        else:
            # Disagreement: return both as alternatives
            return MatchResult(
                question_id=prog_result.question_id,  # Primary
                confidence=prog_result.confidence,
                strategy='ensemble_disagreed',
                source='hybrid_requires_clarification',
                alternatives=[claude_result.question_id]
            )


__all__ = ["HybridRouter"]
