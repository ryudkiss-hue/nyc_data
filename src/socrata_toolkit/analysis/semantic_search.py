"""Semantic catalog search using sentence-transformers (optional)."""
from __future__ import annotations

from typing import Any

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    _ST = True
except ImportError:
    _ST = False

class SemanticCatalogSearch:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if not _ST:
            raise ImportError("sentence-transformers required")
        self._model = SentenceTransformer(model_name)
        self._embeddings = None
        self._records: list[dict[str, Any]] = []

    def index(self, records: list[dict[str, Any]], text_field: str = "name") -> None:
        self._records = records
        texts = [r.get(text_field, "") for r in records]
        self._embeddings = self._model.encode(texts, convert_to_numpy=True)

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        if self._embeddings is None:
            return []
        q = self._model.encode([query], convert_to_numpy=True)
        scores = (self._embeddings @ q.T).flatten()
        idx = scores.argsort()[::-1][:top_k]
        return [{"score": float(scores[i]), **self._records[i]} for i in idx]
