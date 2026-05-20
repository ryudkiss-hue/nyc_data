"""Pure functions for what-if exploration of analyst pack outputs."""

from __future__ import annotations

from typing import Any

import pandas as pd

from socrata_toolkit.engineering.construction_list import (
    DEFAULT_PRIORITY_WEIGHTS,
    prioritize_construction_list,
)

WEIGHT_KEYS = tuple(DEFAULT_PRIORITY_WEIGHTS.keys())


def normalize_weights(
    severity: float,
    pedestrian_volume: float,
    age_days: float,
    ada_flag: float,
    smart_spine: float,
    complaint_count: float,
) -> dict[str, float]:
    """Scale slider inputs (0–1 or 1–5) into a weight dict that sums to 1."""
    raw = {
        "severity": max(float(severity), 0),
        "pedestrian_volume": max(float(pedestrian_volume), 0),
        "age_days": max(float(age_days), 0),
        "ada_flag": max(float(ada_flag), 0),
        "smart_spine": max(float(smart_spine), 0),
        "complaint_count": max(float(complaint_count), 0),
    }
    total = sum(raw.values()) or 1.0
    return {k: round(v / total, 4) for k, v in raw.items()}


def preview_priority(
    df: pd.DataFrame,
    *,
    weights: dict[str, float] | None = None,
    top_n: int = 25,
    borough: str | None = None,
    conflicts_only: bool = False,
    ada_only: bool = False,
    conflict_col: str = "_has_conflict",
) -> pd.DataFrame:
    """Re-rank construction list with custom weights; does not mutate pack files."""
    if df.empty:
        return df
    work = df.copy()
    if borough and borough != "ALL" and "borough" in work.columns:
        work = work[work["borough"].astype(str).str.upper() == borough.upper()]
    if ada_only:
        ada_col = "ada_flag" if "ada_flag" in work.columns else None
        if ada_col:
            work = work[work[ada_col].astype(bool)]
        elif "severity_rating" in work.columns:
            work = work[work["severity_rating"].astype(float) >= 5]
    if conflicts_only and conflict_col in work.columns:
        work = work[work[conflict_col].astype(bool)]
    elif conflicts_only and "has_conflict" in work.columns:
        work = work[work["has_conflict"].astype(bool)]
    ranked = prioritize_construction_list(work, weights=weights)
    n = max(1, int(top_n))
    return ranked.head(n).reset_index(drop=True)


def borough_bar_counts(df: pd.DataFrame, *, score_col: str = "_priority_score") -> dict[str, float]:
    """Aggregate mean priority score by borough for bar charts."""
    if df.empty or "borough" not in df.columns:
        return {}
    col = score_col if score_col in df.columns else None
    if col:
        grouped = df.groupby("borough")[col].mean()
    else:
        grouped = df.groupby("borough").size()
    return {str(k): round(float(v), 3) for k, v in grouped.items()}


def filter_kpi_metrics(
    metrics: list[dict[str, Any]],
    *,
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter KPI dicts by category tags (program, role, budget, etc.)."""
    if not categories or "all" in [c.lower() for c in categories]:
        return metrics
    cats = {c.lower() for c in categories}
    out = []
    for m in metrics:
        name = str(m.get("name", "")).lower()
        cat = str(m.get("category", "")).lower()
        tags = [t.lower() for t in m.get("tags", [])]
        if cat in cats or any(t in cats for t in tags):
            out.append(m)
            continue
        if "budget" in cats and ("budget" in name or "cpi" in name or "cost" in name):
            out.append(m)
        elif "backlog" in cats and ("backlog" in name or "open" in name):
            out.append(m)
        elif "ada" in cats and "ada" in name:
            out.append(m)
        elif "conflict" in cats and "conflict" in name:
            out.append(m)
        elif "completion" in cats and ("complete" in name or "completion" in name):
            out.append(m)
        elif "productivity" in cats and ("productivity" in name or "sqft" in name):
            out.append(m)
    return out if out else metrics


def profile_weight_snippet(weights: dict[str, float]) -> str:
    """YAML snippet for copy-paste (does not write files)."""
    lines = ["# Copy into analyst profile construction_list weights (if supported):"]
    lines.append("priority_weights:")
    for k, v in weights.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)
