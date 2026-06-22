from typing import Any, Dict, List

from socrata_toolkit.core.routing.claude_semantic_router import ClaudeSemanticRouter
from socrata_toolkit.core.routing.hybrid_router import HybridRouter
from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter


def evaluate_router(
    kpi_registry: Dict[str, Dict],
    variants: List[Dict],
    embeddings_cache: Dict = None
) -> Dict[str, Any]:
    """
    Evaluate router accuracy on variant dataset.

    Returns: {
        'accuracy': float,
        'confusion_matrix': {kpi_id: {correct: int, wrong: int}},
        'correct': int,
        'total': int
    }
    """
    if embeddings_cache is None:
        embeddings_cache = {}

    prog_router = ProgrammaticRouter(kpi_registry)
    claude_router = ClaudeSemanticRouter(kpi_registry, embeddings_cache)
    hybrid_router = HybridRouter(prog_router, claude_router)

    correct = 0
    total = 0
    confusion_matrix = {}

    for variant in variants:
        expected_kpi = variant['kpi_id']
        question = variant['question_variant']

        result = hybrid_router.match(question)
        matched_kpi = result.question_id if result else None

        total += 1

        if matched_kpi == expected_kpi:
            correct += 1

        if expected_kpi not in confusion_matrix:
            confusion_matrix[expected_kpi] = {"correct": 0, "wrong": 0}

        if matched_kpi == expected_kpi:
            confusion_matrix[expected_kpi]["correct"] += 1
        else:
            confusion_matrix[expected_kpi]["wrong"] += 1

    accuracy = correct / total if total > 0 else 0.0

    return {
        "accuracy": accuracy,
        "confusion_matrix": confusion_matrix,
        "correct": correct,
        "total": total
    }


__all__ = ["evaluate_router"]
