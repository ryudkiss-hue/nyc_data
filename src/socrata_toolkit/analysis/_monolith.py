"""Internal monolith module for text analysis functionality.

This module provides text analysis capabilities including TF-IDF vectorization
and keyword extraction. It's used internally by the analysis module.
"""

from __future__ import annotations

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    TfidfVectorizer = None


def extract_keywords(texts: list[str], max_features: int = 100) -> dict[str, float]:
    """Extract keywords from a list of texts using TF-IDF."""
    if not texts or not TfidfVectorizer:
        return {}

    vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.mean(axis=0).A1
        return dict(zip(feature_names, scores))
    except Exception:
        return {}


__all__ = ["extract_keywords", "TfidfVectorizer"]
