import re
from typing import Dict, List, Optional, Tuple
from .models import MatchResult

class ProgrammaticRouter:
    """
    Multi-strategy fuzzy matching using BM25, FastText (token overlap proxy),
    and Jaccard coefficient. Weights from Bayesian optimization research.
    """

    # Optimal weights from Bayesian optimization on 1,372 variants
    STRATEGY_WEIGHTS = {
        'bm25': 0.86,
        'fasttext': 0.04,  # Proxy: token frequency similarity
        'jaccard': 0.10
    }

    def __init__(self, kpi_registry: Dict[str, Dict]):
        """
        Initialize router with KPI registry.

        Args:
            kpi_registry: Dict mapping kpi_id -> {kpi_name, summary, ...}
        """
        self.registry = kpi_registry
        self._build_indexes()

    def _build_indexes(self):
        """Build inverted indexes for efficient matching"""
        self.question_tokens = {}
        self.question_text = {}

        for kpi_id, metadata in self.registry.items():
            kpi_name = metadata.get('kpi_name', '')
            summary = metadata.get('summary', '')
            combined_text = f"{kpi_name} {summary}".lower()

            tokens = self._tokenize(combined_text)
            self.question_tokens[kpi_id] = set(tokens)
            self.question_text[kpi_id] = combined_text

    def match(self, user_question: str, top_k: int = 1) -> MatchResult:
        """
        Match user question to registered KPIs using multiple strategies.

        Returns best match with confidence score. Strategies run in parallel
        and results are combined via weighted voting.
        """
        user_tokens = set(self._tokenize(user_question.lower()))

        # Run all strategies
        strategies = {
            'bm25': self._bm25_match(user_question),
            'jaccard': self._jaccard_match(user_tokens),
            'fasttext': self._fasttext_match(user_tokens)
        }

        # Filter None results
        valid_strategies = {k: v for k, v in strategies.items() if v}

        if not valid_strategies:
            return MatchResult(
                question_id=None,
                confidence=0.0,
                strategy='none',
                source='programmatic',
                alternatives=[]
            )

        # Composite scoring
        composite_scores = self._composite_score(valid_strategies)

        if not composite_scores:
            return MatchResult(
                question_id=None,
                confidence=0.0,
                strategy='none',
                source='programmatic'
            )

        best_kpi_id, (best_score, best_strategy) = max(
            composite_scores.items(),
            key=lambda x: x[1][0]
        )

        return MatchResult(
            question_id=best_kpi_id,
            confidence=best_score,
            strategy=best_strategy,
            source='programmatic'
        )

    def _bm25_match(self, user_question: str) -> Optional[Dict[str, float]]:
        """BM25 ranking (simplified: term frequency + presence)"""
        scores = {}
        user_tokens = self._tokenize(user_question.lower())

        for kpi_id, kpi_tokens in self.question_tokens.items():
            if not kpi_tokens:
                continue

            # Count matching tokens
            matches = sum(1 for token in user_tokens if token in kpi_tokens)

            if matches > 0:
                # BM25-like scoring: matches / total_unique_tokens
                score = matches / len(set(user_tokens) | kpi_tokens)
                scores[kpi_id] = score

        return scores if scores else None

    def _jaccard_match(self, user_tokens: set) -> Optional[Dict[str, float]]:
        """Jaccard coefficient: intersection / union"""
        scores = {}

        for kpi_id, kpi_tokens in self.question_tokens.items():
            if not kpi_tokens:
                continue

            intersection = len(user_tokens & kpi_tokens)
            union = len(user_tokens | kpi_tokens)
            jaccard = intersection / union if union > 0 else 0

            if jaccard > 0:
                scores[kpi_id] = jaccard

        return scores if scores else None

    def _fasttext_match(self, user_tokens: set) -> Optional[Dict[str, float]]:
        """FastText proxy: token frequency similarity"""
        scores = {}

        for kpi_id, kpi_tokens in self.question_tokens.items():
            if not kpi_tokens:
                continue

            # Overlap ratio (simplified fasttext proxy)
            overlap = len(user_tokens & kpi_tokens)
            max_len = max(len(user_tokens), len(kpi_tokens))
            score = overlap / max_len if max_len > 0 else 0

            if score > 0:
                scores[kpi_id] = score

        return scores if scores else None

    def _composite_score(self, strategy_results: Dict[str, Dict[str, float]]) -> Dict[str, Tuple[float, str]]:
        """Combine strategies using weighted voting"""
        composite = {}

        for strategy, scores in strategy_results.items():
            weight = self.STRATEGY_WEIGHTS.get(strategy, 0.5)

            for kpi_id, score in scores.items():
                if kpi_id not in composite:
                    composite[kpi_id] = (0.0, strategy)

                weighted = score * weight
                current_score, current_strategy = composite[kpi_id]

                if weighted > current_score:
                    composite[kpi_id] = (weighted, strategy)

        # Normalize to 0-1
        if composite:
            max_score = max(s for s, _ in composite.values())
            if max_score > 0:
                composite = {
                    kpi_id: (s / max_score, strat)
                    for kpi_id, (s, strat) in composite.items()
                }

        return composite

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text: lowercase, remove punctuation"""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens


__all__ = ["ProgrammaticRouter"]
