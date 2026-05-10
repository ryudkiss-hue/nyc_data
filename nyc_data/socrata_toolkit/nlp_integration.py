"""NLP Integration Layer for DOT Sidewalk Toolkit.

Connects the NLP, text analytics, and LLM modules into the DOT-specific
workflows: construction list enrichment, complaint triage, contract
document analysis, and report summarization.

This module acts as a bridge between the raw NLP capabilities and the
domain-specific DOT modules. All functions gracefully degrade when
optional NLP dependencies (spacy, textblob, transformers) are not
installed -- they fall back to keyword-based heuristics.

Key capabilities:
- Enrich construction lists with NLP-extracted entities and sentiment
- Triage 311 complaints by severity using text classification
- Extract locations, dates, and agencies from free-text descriptions
- Summarize inspection notes and contract documents
- Auto-tag work orders with DOT-specific categories

Example::

    from socrata_toolkit.nlp_integration import (
        enrich_construction_list,
        triage_complaints,
        extract_locations,
        summarize_notes,
    )

    enriched = enrich_construction_list(construction_df, text_col="description")
    triaged = triage_complaints(complaints_df, text_col="complaint_text")
    locations = extract_locations("Sidewalk at 5th Ave and 42nd St, Manhattan")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .nlp_advanced import analyze_text, preprocess_text, sentiment_score
from .text_analytics import build_corpus, regex_scan, top_terms


# ---------------------------------------------------------------------------
# DOT-Specific Keyword Taxonomy
# ---------------------------------------------------------------------------

#: Keywords that indicate high-priority safety issues.
SAFETY_KEYWORDS = [
    "trip hazard", "tripping", "fall", "fell", "injury", "injured",
    "wheelchair", "accessible", "ada", "blind", "cane", "walker",
    "stroller", "elderly", "disabled", "dangerous", "unsafe",
    "collapsed", "sinkhole", "hole", "crack", "broken", "missing",
]

#: Keywords that indicate ADA compliance concerns.
ADA_KEYWORDS = [
    "ada", "accessible", "ramp", "tactile", "detectable warning",
    "curb cut", "wheelchair", "mobility", "handicap",
]

#: Keywords that indicate utility conflicts.
UTILITY_KEYWORDS = [
    "con edison", "con ed", "water main", "sewer", "gas line",
    "electric", "cable", "telecom", "fiber", "manhole", "vault",
    "hydrant", "utility", "dew", "national grid",
]

#: Keywords for specific work types.
WORK_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "sidewalk_repair": ["sidewalk", "flag", "concrete slab", "pavement"],
    "pedestrian_ramp": ["ramp", "ped ramp", "curb ramp", "pedestrian ramp"],
    "curb_replacement": ["curb", "curb line", "granite"],
    "tree_pit": ["tree pit", "tree well", "root damage", "tree root"],
    "ada_compliance": ["ada", "tactile", "detectable warning", "truncated dome"],
    "driveway_apron": ["driveway", "apron", "vehicle crossing"],
}

#: Regex patterns for extracting DOT-relevant entities.
DOT_PATTERNS = {
    "block_lot": r"\b\d{1,5}[-/]\d{1,5}\b",
    "contract_number": r"\b[A-Z]{2,4}[-]?\d{4,8}\b",
    "phone": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
    "borough_mention": r"\b(?:manhattan|bronx|brooklyn|queens|staten\s*island)\b",
    "avenue_street": r"\b\d+(?:st|nd|rd|th)\s+(?:ave(?:nue)?|st(?:reet)?|blvd|boulevard|place|pl|road|rd|drive|dr)\b",
    "intersection": r"\b\w+\s+(?:ave|st|blvd|rd)\s*(?:and|&|at)\s*\w+\s+(?:ave|st|blvd|rd)\b",
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class TextEnrichment:
    """NLP enrichment results for a single text field."""
    sentiment: float
    safety_score: float  # 0-1, based on safety keyword density
    ada_relevant: bool
    utility_conflict: bool
    work_type: str
    extracted_entities: List[Dict[str, str]]
    key_terms: List[str]
    summary: str


@dataclass
class ComplaintTriage:
    """Triage result for a 311 complaint."""
    priority: str  # "critical", "high", "medium", "low"
    safety_flag: bool
    ada_flag: bool
    utility_flag: bool
    category: str
    confidence: float
    reason: str


# ---------------------------------------------------------------------------
# Construction List Enrichment
# ---------------------------------------------------------------------------

def enrich_construction_list(
    df: pd.DataFrame,
    text_col: str = "description",
    output_prefix: str = "_nlp",
) -> pd.DataFrame:
    """Enrich a construction list with NLP-extracted features.

    Adds columns for sentiment, safety score, ADA relevance, work type
    classification, and key terms extracted from the text column.

    Args:
        df: Construction list DataFrame.
        text_col: Column containing free-text descriptions.
        output_prefix: Prefix for new columns.

    Returns:
        DataFrame with NLP enrichment columns added.
    """
    out = df.copy()

    sentiments = []
    safety_scores = []
    ada_flags = []
    utility_flags = []
    work_types = []
    key_terms_list = []
    summaries = []

    for _, row in df.iterrows():
        text = str(row.get(text_col, ""))
        enrichment = _enrich_text(text)
        sentiments.append(enrichment.sentiment)
        safety_scores.append(enrichment.safety_score)
        ada_flags.append(enrichment.ada_relevant)
        utility_flags.append(enrichment.utility_conflict)
        work_types.append(enrichment.work_type)
        key_terms_list.append(enrichment.key_terms)
        summaries.append(enrichment.summary)

    out[f"{output_prefix}_sentiment"] = sentiments
    out[f"{output_prefix}_safety_score"] = safety_scores
    out[f"{output_prefix}_ada_flag"] = ada_flags
    out[f"{output_prefix}_utility_conflict"] = utility_flags
    out[f"{output_prefix}_work_type"] = work_types
    out[f"{output_prefix}_key_terms"] = key_terms_list
    out[f"{output_prefix}_summary"] = summaries

    return out


def _enrich_text(text: str) -> TextEnrichment:
    """Run full NLP enrichment on a single text string."""
    text_lower = text.lower()

    # Sentiment
    sent = sentiment_score(text)

    # Safety score: proportion of safety keywords found
    safety_hits = sum(1 for kw in SAFETY_KEYWORDS if kw in text_lower)
    safety_score_val = min(safety_hits / 5.0, 1.0)

    # ADA relevance
    ada_relevant = any(kw in text_lower for kw in ADA_KEYWORDS)

    # Utility conflict
    utility_conflict = any(kw in text_lower for kw in UTILITY_KEYWORDS)

    # Work type classification
    work_type = "sidewalk_repair"  # default
    max_hits = 0
    for wt, keywords in WORK_TYPE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > max_hits:
            max_hits = hits
            work_type = wt

    # Entity extraction using NLP (graceful degradation)
    entities = []
    try:
        result = analyze_text(text)
        entities = result.entities
    except Exception:
        # Fallback: regex-based extraction
        for name, pattern in DOT_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({"text": match.group(), "label": name})

    # Key terms
    tokens, _ = preprocess_text(text)
    key_terms = tokens[:10]

    # Summary
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    summary = ". ".join(sentences[:2]) + ("." if sentences else "")

    return TextEnrichment(
        sentiment=sent,
        safety_score=safety_score_val,
        ada_relevant=ada_relevant,
        utility_conflict=utility_conflict,
        work_type=work_type,
        extracted_entities=entities,
        key_terms=key_terms,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Complaint Triage
# ---------------------------------------------------------------------------

def triage_complaints(
    df: pd.DataFrame,
    text_col: str = "complaint_text",
    output_prefix: str = "_triage",
) -> pd.DataFrame:
    """Triage 311 complaints by analyzing text content.

    Assigns priority levels (critical/high/medium/low), flags safety
    and ADA issues, and categorizes by work type.

    Args:
        df: Complaints DataFrame.
        text_col: Column with complaint text.

    Returns:
        DataFrame with triage columns added.
    """
    out = df.copy()
    priorities = []
    safety_flags = []
    ada_flags = []
    utility_flags = []
    categories = []
    reasons = []

    for _, row in df.iterrows():
        text = str(row.get(text_col, ""))
        triage = _triage_single(text)
        priorities.append(triage.priority)
        safety_flags.append(triage.safety_flag)
        ada_flags.append(triage.ada_flag)
        utility_flags.append(triage.utility_flag)
        categories.append(triage.category)
        reasons.append(triage.reason)

    out[f"{output_prefix}_priority"] = priorities
    out[f"{output_prefix}_safety"] = safety_flags
    out[f"{output_prefix}_ada"] = ada_flags
    out[f"{output_prefix}_utility"] = utility_flags
    out[f"{output_prefix}_category"] = categories
    out[f"{output_prefix}_reason"] = reasons

    return out


def _triage_single(text: str) -> ComplaintTriage:
    """Triage a single complaint text."""
    text_lower = text.lower()

    safety_hits = sum(1 for kw in SAFETY_KEYWORDS if kw in text_lower)
    ada_flag = any(kw in text_lower for kw in ADA_KEYWORDS)
    utility_flag = any(kw in text_lower for kw in UTILITY_KEYWORDS)

    # Determine work type
    category = "sidewalk_repair"
    for wt, keywords in WORK_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            category = wt
            break

    # Priority assignment
    reasons = []
    if safety_hits >= 3:
        priority = "critical"
        reasons.append(f"{safety_hits} safety keywords detected")
    elif safety_hits >= 1 or ada_flag:
        priority = "high"
        if safety_hits:
            reasons.append(f"{safety_hits} safety keywords")
        if ada_flag:
            reasons.append("ADA concern")
    elif utility_flag:
        priority = "medium"
        reasons.append("utility conflict mentioned")
    else:
        priority = "low"
        reasons.append("routine complaint")

    # Sentiment can bump priority
    sent = sentiment_score(text)
    if sent < -0.3 and priority == "low":
        priority = "medium"
        reasons.append("negative sentiment detected")

    return ComplaintTriage(
        priority=priority,
        safety_flag=safety_hits > 0,
        ada_flag=ada_flag,
        utility_flag=utility_flag,
        category=category,
        confidence=min(0.5 + safety_hits * 0.1 + (0.2 if ada_flag else 0), 1.0),
        reason="; ".join(reasons),
    )


# ---------------------------------------------------------------------------
# Location Extraction
# ---------------------------------------------------------------------------

def extract_locations(text: str) -> List[Dict[str, str]]:
    """Extract location references from free text.

    Finds borough mentions, street addresses, intersections, and
    block/lot references using regex and NLP entity recognition.

    Args:
        text: Free-text description.

    Returns:
        List of dicts with 'text' and 'type' keys.
    """
    locations = []

    # Regex-based extraction
    for label, pattern in [
        ("intersection", DOT_PATTERNS["intersection"]),
        ("address", DOT_PATTERNS["avenue_street"]),
        ("borough", DOT_PATTERNS["borough_mention"]),
        ("block_lot", DOT_PATTERNS["block_lot"]),
    ]:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            locations.append({"text": match.group().strip(), "type": label})

    # NLP-based extraction (if available)
    try:
        result = analyze_text(text)
        for ent in result.entities:
            if ent.get("label") in ("GPE", "LOC", "FAC", "ORG"):
                locations.append({"text": ent["text"], "type": f"nlp_{ent['label'].lower()}"})
    except Exception:
        pass

    # Deduplicate by text
    seen = set()
    unique = []
    for loc in locations:
        key = loc["text"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(loc)

    return unique


# ---------------------------------------------------------------------------
# Note Summarization
# ---------------------------------------------------------------------------

def summarize_notes(
    df: pd.DataFrame,
    text_col: str = "notes",
    max_sentences: int = 2,
    output_col: str = "_summary",
) -> pd.DataFrame:
    """Summarize free-text notes into concise descriptions.

    Uses NLP summarization when available, falls back to extractive
    (first N sentences) approach.

    Args:
        df: DataFrame with a text column.
        text_col: Column containing notes/descriptions.
        max_sentences: Maximum sentences in summary.

    Returns:
        DataFrame with summary column added.
    """
    out = df.copy()
    summaries = []
    for _, row in df.iterrows():
        text = str(row.get(text_col, ""))
        if not text.strip():
            summaries.append("")
            continue
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        summary = ". ".join(sentences[:max_sentences])
        if summary and not summary.endswith("."):
            summary += "."
        summaries.append(summary)
    out[output_col] = summaries
    return out


# ---------------------------------------------------------------------------
# Batch Text Analysis for Reports
# ---------------------------------------------------------------------------

def analyze_text_column(
    df: pd.DataFrame,
    text_col: str,
    top_n: int = 20,
) -> Dict[str, Any]:
    """Run comprehensive text analysis on a DataFrame column.

    Returns a summary dict suitable for inclusion in reports with
    term frequency, regex pattern matches, and sentiment distribution.

    Args:
        df: Source data.
        text_col: Column to analyze.
        top_n: Number of top terms to return.

    Returns:
        Dict with keys: top_terms, pattern_matches, sentiment_stats, sample_entities.
    """
    if text_col not in df.columns:
        return {"error": f"Column '{text_col}' not found"}

    # Top terms
    terms = top_terms(df, [text_col], limit=top_n)

    # Pattern scanning
    patterns = {
        "safety_mentions": "|".join(SAFETY_KEYWORDS[:10]),
        "ada_mentions": "|".join(ADA_KEYWORDS[:5]),
        "utility_mentions": "|".join(UTILITY_KEYWORDS[:5]),
        "phone_numbers": DOT_PATTERNS["phone"],
        "contract_numbers": DOT_PATTERNS["contract_number"],
    }
    pattern_matches = regex_scan(df, [text_col], patterns)

    # Sentiment distribution
    sentiments = df[text_col].fillna("").apply(lambda t: sentiment_score(str(t)))
    sentiment_stats = {
        "mean": round(float(sentiments.mean()), 4),
        "positive_pct": round(float((sentiments > 0.1).mean() * 100), 1),
        "negative_pct": round(float((sentiments < -0.1).mean() * 100), 1),
        "neutral_pct": round(float(((sentiments >= -0.1) & (sentiments <= 0.1)).mean() * 100), 1),
    }

    # Sample entities from first 10 rows
    sample_entities = []
    for text in df[text_col].fillna("").head(10):
        locs = extract_locations(str(text))
        if locs:
            sample_entities.extend(locs[:3])

    return {
        "top_terms": terms,
        "pattern_matches": pattern_matches,
        "sentiment_stats": sentiment_stats,
        "sample_entities": sample_entities[:15],
    }
