from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

import pandas as pd

from . import _monolith as _text_monolith

logger = logging.getLogger(__name__)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-']+")


@dataclass
class TextInsights:
    """Insights derived from text analysis."""

    top_terms: list[tuple[str, int]]
    regex_hits: dict[str, int]
    tags: list[str]
    row_count: int


def generate_text_insights(
    df: pd.DataFrame,
    text_columns: list[str],
    regex_patterns: dict[str, str] | None = None,
    geo_column: str | None = None,
) -> tuple[pd.DataFrame, TextInsights]:
    """Analyze text columns for frequent terms, regex patterns, and descriptive tags."""
    patterns = regex_patterns or {
        "emails": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "phones": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "urls": r"https?://\S+",
        "ids": r"\b[A-Z]{2,}-?\d{2,}\b",
    }

    def top_terms(df, columns, limit=30):
        tokens = []
        for col in columns:
            if col in df.columns:
                for v in df[col].fillna(""):
                    tokens.extend(WORD_RE.findall(str(v).lower()))
        return Counter(t for t in tokens if len(t) >= 3).most_common(limit)

    def regex_scan(df, columns, patterns):
        out = dict.fromkeys(patterns, 0)
        compiled = {k: re.compile(v, re.IGNORECASE) for k, v in patterns.items()}
        for col in columns:
            if col in df.columns:
                for text in df[col].fillna("").astype(str):
                    for name, cre in compiled.items():
                        if cre.search(text):
                            out[name] += 1
        return out

    tagged = df.copy()
    terms_list = top_terms(df, text_columns, limit=50)
    high_value_terms = {k for k, v in terms_list if v >= max(2, math.ceil(len(df) * 0.02))}

    tags_col = []
    for _, row in df.iterrows():
        row_tags = set()
        for col in text_columns:
            if col in df.columns:
                tokens = WORD_RE.findall(str(row.get(col, "")).lower())
                row_tags.update(t for t in tokens if t in high_value_terms)
        if geo_column and geo_column in df.columns:
            geo_val = row.get(geo_column)
            if geo_val is not None and not (isinstance(geo_val, float) and pd.isna(geo_val)):
                if str(geo_val).strip() and str(geo_val).lower() not in ("none", "nan"):
                    row_tags.add("has_geo")
        if not row_tags:
            row_tags.add("untagged")
        tags_col.append(sorted(row_tags)[:15])

    tagged["descriptive_tags"] = tags_col
    insights = TextInsights(
        top_terms=terms_list[:30],
        regex_hits=regex_scan(df, text_columns, patterns),
        tags=sorted({t for tags in tags_col for t in tags if t != "untagged"}),
        row_count=len(df),
    )
    return tagged, insights


def extract_term_frequencies(text_list: list[str]) -> dict[str, int]:
    """Calculate frequency of terms in a list of strings."""
    tokens = []
    for text in text_list:
        tokens.extend(WORD_RE.findall(str(text).lower()))
    return dict(Counter(t for t in tokens if len(t) >= 4).most_common(100))


def extract_patterns(df: pd.DataFrame, column: str, pattern_type: str = "emails") -> dict[str, int]:
    """Count occurrences of specific regex patterns."""
    patterns = {
        "emails": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "phones": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    }
    pat = re.compile(patterns.get(pattern_type, patterns["emails"]), re.IGNORECASE)
    matches = df[column].dropna().astype(str).apply(lambda x: len(pat.findall(x))).sum()
    return {pattern_type: int(matches)}


def parse_sim_complaints(df: pd.DataFrame, text_col: str = "description") -> pd.DataFrame:
    """
    Quantitatively parse Sidewalk Inspection and Management (SIM) complaints.
    """
    import numpy as np

    out = df.copy()
    if text_col not in out.columns:
        logger.warning(f"Column '{text_col}' not found in DataFrame. Skipping SIM parsing.")
        return out

    taxonomies = {
        "ada_accessibility": r"\b(ada|wheelchair|ramp|curb cut|disabled|mobility|blind|walker)\b",
        "root_damage": r"\b(root|tree|heave|uplift|trunk)\b",
        "surface_damage": r"\b(crack|hole|pothole|spall|spalling|sunken|settlement|depression|loose|missing|cave)\b",
        "trip_hazard": r"\b(trip|fall|hazard|danger|protruding|rebar|metal|edge|uneven|step)\b",
        "water_pooling": r"\b(water|puddle|drain|drainage|flood|pond)\b",
    }
    compiled_taxonomies = {k: re.compile(v, re.IGNORECASE) for k, v in taxonomies.items()}
    texts = out[text_col].astype(str).fillna("")

    flags_series = texts.str.lower().apply(
        lambda text: [cat for cat, pattern in compiled_taxonomies.items() if pattern.search(text)]
    )
    out["_sim_flags"] = flags_series
    severity_map = {"trip_hazard": 0.4, "ada_accessibility": 0.35, "root_damage": 0.2}

    def calculate_severity(flags: list[str]) -> float:
        score = sum(severity_map.get(flag, 0.15) for flag in flags)
        return round(min(1.0, score), 2)

    out["_sim_severity_score"] = out["_sim_flags"].apply(calculate_severity)

    # Keyword extraction via TF-IDF
    if _text_monolith.TfidfVectorizer is not None:
        try:
            vectorizer = _text_monolith.TfidfVectorizer(max_features=100, stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(texts)
            scores_array = tfidf_matrix.toarray()
            feature_names = vectorizer.get_feature_names_out()
            keywords_list = []
            for row_scores in scores_array:
                ranked = sorted(
                    (
                        (feature_names[i], row_scores[i])
                        for i in range(len(row_scores))
                        if row_scores[i] > 0
                    ),
                    key=lambda x: x[1],
                    reverse=True,
                )
                keywords_list.append([kw for kw, _ in ranked])
            out["_sim_unique_keywords"] = keywords_list
        except Exception:
            out["_sim_unique_keywords"] = [[] for _ in range(len(out))]
    else:
        out["_sim_unique_keywords"] = [[] for _ in range(len(out))]

    def get_primary_cat(flags: list[str]) -> str:
        if "trip_hazard" in flags and "ada_accessibility" in flags:
            return "critical_accessibility_hazard"
        return flags[0] if flags else "general_maintenance"

    out["_sim_category"] = out["_sim_flags"].apply(get_primary_cat)
    mask = texts.str.strip() == ""
    out.loc[mask, "_sim_category"] = "unknown"
    out.loc[mask, "_sim_severity_score"] = 0.0

    return out
