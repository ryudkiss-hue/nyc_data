from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-']+")


@dataclass
class TextInsights:
    top_terms: list[tuple[str, int]]
    regex_hits: dict[str, int]
    tags: list[str]
    row_count: int


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def build_corpus(df: pd.DataFrame, columns: list[str]) -> list[str]:
    tokens: list[str] = []
    for col in columns:
        if col in df.columns:
            for v in df[col].fillna(""):
                tokens.extend(WORD_RE.findall(normalize_text(v)))
    return tokens


def top_terms(df: pd.DataFrame, columns: list[str], limit: int = 30, min_len: int = 3) -> list[tuple[str, int]]:
    c = Counter(t for t in build_corpus(df, columns) if len(t) >= min_len)
    return c.most_common(limit)


def regex_scan(df: pd.DataFrame, columns: list[str], patterns: dict[str, str]) -> dict[str, int]:
    out: dict[str, int] = {k: 0 for k in patterns}
    compiled = {k: re.compile(v, re.IGNORECASE) for k, v in patterns.items()}
    for col in columns:
        if col not in df.columns:
            continue
        for text in df[col].fillna("").astype(str):
            for name, cre in compiled.items():
                if cre.search(text):
                    out[name] += 1
    return out


def attach_descriptive_tags(df: pd.DataFrame, text_columns: list[str], geo_column: str | None = None) -> pd.DataFrame:
    tagged = df.copy()
    tags: list[list[str]] = []
    terms = dict(top_terms(df, text_columns, limit=50))
    high_value_terms = {k for k, v in terms.items() if v >= max(2, math.ceil(len(df) * 0.02))}

    for _, row in df.iterrows():
        row_tags: set[str] = set()
        for col in text_columns:
            if col in df.columns:
                tokens = WORD_RE.findall(normalize_text(row.get(col, "")))
                row_tags.update(t for t in tokens if t in high_value_terms)
        if geo_column and geo_column in df.columns and row.get(geo_column):
            row_tags.add("has_geo")
        if not row_tags:
            row_tags.add("untagged")
        tags.append(sorted(row_tags)[:15])

    tagged["descriptive_tags"] = tags
    return tagged


def generate_text_insights(df: pd.DataFrame, text_columns: list[str], regex_patterns: dict[str, str] | None = None, geo_column: str | None = None) -> tuple[pd.DataFrame, TextInsights]:
    regex_patterns = regex_patterns or {
        "emails": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "phones": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "urls": r"https?://\S+",
        "ids": r"\b[A-Z]{2,}-?\d{2,}\b",
    }
    tagged = attach_descriptive_tags(df, text_columns=text_columns, geo_column=geo_column)
    insights = TextInsights(
        top_terms=top_terms(df, text_columns),
        regex_hits=regex_scan(df, text_columns, regex_patterns),
        tags=sorted({t for tags in tagged["descriptive_tags"] for t in tags}),
        row_count=len(df),
    )
    return tagged, insights
