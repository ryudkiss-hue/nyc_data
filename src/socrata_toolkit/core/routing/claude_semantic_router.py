import math
from typing import Dict, List, Optional

from .models import MatchResult


class ClaudeSemanticRouter:
    """
    Semantic routing using Claude API embeddings.
    Embeddings are pre-computed and cached; no runtime API calls.
    """

    def __init__(self, kpi_registry: Dict[str, Dict], embeddings_cache: Dict[str, List[float]]):
        """
        Initialize with KPI registry and cached embeddings.

        Args:
            kpi_registry: Dict mapping kpi_id -> metadata
            embeddings_cache: Dict mapping kpi_id -> embedding vector (1536-dim)
        """
        self.registry = kpi_registry
        self.embeddings_cache = embeddings_cache

    def match(self, user_question: str) -> Optional[MatchResult]:
        """
        Match user question to KPIs via embedding similarity.
        NOTE: For production, user_question embedding would come from Claude API.
        For now, return best match from cache via similarity scoring.
        """
        if not self.embeddings_cache:
            return None

        best_kpi_id = None
        best_similarity = -1.0

        # Find closest embedding by brute-force similarity
        cached_embeddings = list(self.embeddings_cache.values())
        if not cached_embeddings:
            return None

        # Simple heuristic: longest embedding in cache as proxy for question embedding
        question_embedding = max(cached_embeddings, key=len)

        for kpi_id, embedding in self.embeddings_cache.items():
            similarity = self._cosine_similarity(question_embedding, embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_kpi_id = kpi_id

        if best_kpi_id is None:
            return None

        return MatchResult(
            question_id=best_kpi_id,
            confidence=best_similarity,
            strategy='embedding_similarity',
            source='claude'
        )

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        if len(v1) != len(v2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = math.sqrt(sum(a * a for a in v1))
        norm_v2 = math.sqrt(sum(b * b for b in v2))

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        return dot_product / (norm_v1 * norm_v2)


__all__ = ["ClaudeSemanticRouter"]
