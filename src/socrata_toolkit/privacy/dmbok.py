"""
DAMA-DMBOK2 data-quality scoring.

Computes the six canonical DAMA-DMBOK2 data-quality dimensions directly from a
pandas DataFrame, reusing the dimension names from
``socrata_toolkit.quality.sla.MetricType`` (completeness, validity, uniqueness,
consistency, timeliness, accuracy). Each :class:`DimensionScore` is in [0, 100]
and the overall score is a documented weighted mean.

Standards: Python 3.9+, full type hints, concise docstrings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# Weights for the overall weighted mean (sum to 1.0). Completeness/validity are
# weighted highest because they most directly gate downstream usability.
_WEIGHTS: dict[str, float] = {
    "completeness": 0.25,
    "validity": 0.20,
    "uniqueness": 0.15,
    "consistency": 0.15,
    "timeliness": 0.10,
    "accuracy": 0.15,
}

_EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")

# Columns whose names imply non-negative counts/quantities.
_COUNT_RE = re.compile(r"count|qty|quantity|num_|_num|total|amount|age|population")

@dataclass
class DimensionScore:
    """Score for a single DAMA-DMBOK2 quality dimension.

    Attributes:
        dimension: Dimension name (one of the six MetricType names).
        score: Score in [0, 100] (higher is better).
        detail: Human-readable explanation of how the score was derived.
    """

    dimension: str
    score: float
    detail: str = ""

@dataclass
class DmbokReport:
    """Full DAMA-DMBOK2 quality report for a DataFrame.

    Attributes:
        overall: Weighted-mean score in [0, 100].
        dimensions: The six :class:`DimensionScore` objects.
        generated_at: UTC timestamp of generation.
    """

    overall: float
    dimensions: list[DimensionScore] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

def _completeness(df: pd.DataFrame) -> DimensionScore:
    """Completeness = non-null cells / total cells * 100."""
    total = df.size
    if total == 0:
        return DimensionScore("completeness", 100.0, "empty frame -> trivially complete")
    non_null = int(df.notna().to_numpy().sum())
    score = 100.0 * non_null / total
    return DimensionScore(
        "completeness", round(score, 2),
        f"{non_null}/{total} non-null cells",
    )

def _validity(df: pd.DataFrame) -> DimensionScore:
    """Validity = mean per-column type-parseable / regex-conformance ratio * 100.

    For each column we infer an expectation: numeric-looking columns must parse
    as numbers; email-looking columns must match an email regex; otherwise any
    non-null value is considered valid. Columns are averaged equally.
    """
    ratios: list[float] = []
    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            continue
        name = str(col).lower()
        if "email" in name:
            ok = s.map(lambda v: bool(_EMAIL_RE.match(str(v).strip()))).mean()
        else:
            coerced = pd.to_numeric(s, errors="coerce")
            if coerced.notna().mean() >= 0.5 or pd.api.types.is_numeric_dtype(s):
                # treat as numeric column: valid = parseable as number
                ok = coerced.notna().mean()
            else:
                ok = 1.0  # free text: any present value is "valid"
        ratios.append(float(ok))
    if not ratios:
        return DimensionScore("validity", 100.0, "no evaluable columns")
    score = 100.0 * float(np.mean(ratios))
    return DimensionScore("validity", round(score, 2),
                          f"mean conformance over {len(ratios)} columns")

def _uniqueness(df: pd.DataFrame, key_columns: list[str] | None) -> DimensionScore:
    """Uniqueness = (1 - duplicate_ratio) * 100.

    Duplicates are evaluated on ``key_columns`` if given, else on full rows.
    """
    if len(df) == 0:
        return DimensionScore("uniqueness", 100.0, "empty frame")
    subset = key_columns if key_columns else None
    dup_count = int(df.duplicated(subset=subset).sum())
    score = 100.0 * (1 - dup_count / len(df))
    basis = f"key columns {key_columns}" if key_columns else "full rows"
    return DimensionScore("uniqueness", round(score, 2),
                          f"{dup_count}/{len(df)} duplicates on {basis}")

def _consistency(df: pd.DataFrame) -> DimensionScore:
    """Consistency = fraction of cross-column/value sanity checks that pass * 100.

    Current checks: count-like columns (by name) must contain no negative
    values. Each count-like column contributes its pass ratio; if no such
    columns exist the dimension is treated as fully consistent.
    """
    ratios: list[float] = []
    for col in df.columns:
        if not _COUNT_RE.search(str(col).lower()):
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        ratios.append(float((s >= 0).mean()))
    if not ratios:
        return DimensionScore("consistency", 100.0, "no count-like columns to check")
    score = 100.0 * float(np.mean(ratios))
    return DimensionScore("consistency", round(score, 2),
                          f"non-negative ratio over {len(ratios)} count-like columns")

def _timeliness(df: pd.DataFrame, date_column: str | None) -> DimensionScore:
    """Timeliness = recency of ``date_column`` vs now, decaying over 365 days.

    score = max(0, 1 - age_days / 365) * 100, using the most recent parseable
    date. Without a date column the dimension is not penalised (100).
    """
    if not date_column or date_column not in df.columns:
        return DimensionScore("timeliness", 100.0, "no date column provided")
    parsed = pd.to_datetime(df[date_column], errors="coerce", utc=True).dropna()
    if parsed.empty:
        return DimensionScore("timeliness", 0.0, "date column unparseable")
    newest = parsed.max()
    age_days = (datetime.now(timezone.utc) - newest.to_pydatetime()).days
    score = max(0.0, 1 - age_days / 365.0) * 100.0
    return DimensionScore("timeliness", round(score, 2),
                          f"newest record {age_days} days old")

def _accuracy(df: pd.DataFrame) -> DimensionScore:
    """Accuracy (proxy) = fraction of numeric values within plausible range * 100.

    Plausibility heuristics applied per column by name:
    - latitude in [-90, 90], longitude in [-180, 180];
    - columns named like age/percent within sane bounds;
    - otherwise values within mean +/- 4*std (outlier proxy).
    Averaged equally over numeric columns.
    """
    ratios: list[float] = []
    for col in df.columns:
        name = str(col).lower()
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        if "lat" in name and "rel" not in name:
            ok = ((s >= -90) & (s <= 90)).mean()
        elif name.startswith("lon") or "longitude" in name or name in ("lng", "long"):
            ok = ((s >= -180) & (s <= 180)).mean()
        elif "percent" in name or name.endswith("_pct") or "rate" in name:
            ok = ((s >= 0) & (s <= 100)).mean()
        elif "age" in name:
            ok = ((s >= 0) & (s <= 130)).mean()
        else:
            if len(s) < 3 or s.std(ddof=0) == 0:
                ok = 1.0
            else:
                lo = s.mean() - 4 * s.std(ddof=0)
                hi = s.mean() + 4 * s.std(ddof=0)
                ok = ((s >= lo) & (s <= hi)).mean()
        ratios.append(float(ok))
    if not ratios:
        return DimensionScore("accuracy", 100.0, "no numeric columns to assess")
    score = 100.0 * float(np.mean(ratios))
    return DimensionScore("accuracy", round(score, 2),
                          f"plausible-value ratio over {len(ratios)} numeric columns")

def score_dataframe(
    df: pd.DataFrame,
    key_columns: list[str] | None = None,
    date_column: str | None = None,
) -> DmbokReport:
    """Compute a full DAMA-DMBOK2 quality report for ``df``.

    Args:
        df: Input DataFrame.
        key_columns: Columns defining row identity for the uniqueness check.
        date_column: Column used for the timeliness (recency) check.

    Returns:
        A :class:`DmbokReport` with six dimensions and a weighted-mean overall
        score. Weights: completeness 0.25, validity 0.20, uniqueness 0.15,
        consistency 0.15, accuracy 0.15, timeliness 0.10.
    """
    dimensions = [
        _completeness(df),
        _validity(df),
        _uniqueness(df, key_columns),
        _consistency(df),
        _timeliness(df, date_column),
        _accuracy(df),
    ]
    overall = sum(d.score * _WEIGHTS[d.dimension] for d in dimensions)
    return DmbokReport(overall=round(overall, 2), dimensions=dimensions)
