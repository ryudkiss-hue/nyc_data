"""Construction List Manager for DOT Sidewalk Inspection & Management.

This module provides tools to create, manage, and prioritize construction
lists for sidewalk repair and pedestrian ramp contracts across the five
boroughs of New York City.

Key capabilities:
- Build construction lists from inspection data with priority scoring
- Detect spatial conflicts between proposed work and existing permits/utilities
- Merge and deduplicate work orders across boroughs
- Apply scope filters (sidewalk vs. ramp vs. curb) and flag ADA compliance
- Export construction lists in formats suitable for QGIS, ArcGIS, and reporting

Typical workflow:
    1. Load inspection records via ``load_inspections()``
    2. Score and prioritize via ``prioritize_construction_list()``
    3. Check for conflicts via ``detect_construction_conflicts()``
    4. Export via ``export_construction_list()``

Example::

    import pandas as pd
    from socrata_toolkit.construction_list import (
        prioritize_construction_list,
        detect_construction_conflicts,
        export_construction_list,
    )

    inspections = pd.read_csv("inspections.csv")
    prioritized = prioritize_construction_list(inspections)
    conflicts = detect_construction_conflicts(prioritized, permits_df)
    export_construction_list(conflicts.clean, "construction_list.xlsx")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: NYC borough codes used throughout DOT systems.
BOROUGH_CODES: Dict[str, int] = {
    "MANHATTAN": 1,
    "BRONX": 2,
    "BROOKLYN": 3,
    "QUEENS": 4,
    "STATEN ISLAND": 5,
}

#: Standard work scope categories for sidewalk contracts.
SCOPE_CATEGORIES = [
    "sidewalk_repair",
    "pedestrian_ramp",
    "curb_replacement",
    "ada_compliance",
    "tree_pit",
    "driveway_apron",
]

#: Default priority weights used in scoring (higher = more important).
DEFAULT_PRIORITY_WEIGHTS: Dict[str, float] = {
    "severity": 0.30,
    "pedestrian_volume": 0.20,
    "age_days": 0.15,
    "ada_flag": 0.15,
    "smart_spine": 0.10,
    "complaint_count": 0.10,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ConstructionItem:
    """A single item on a construction list."""
    location_id: str
    borough: str
    address: str
    scope: str
    priority_score: float
    has_conflict: bool = False
    conflict_details: List[str] = field(default_factory=list)
    ada_required: bool = False
    estimated_sqft: float = 0.0
    notes: str = ""


@dataclass
class ConflictCheckResult:
    """Results from running conflict detection on a construction list."""
    total_items: int
    conflict_count: int
    conflict_rate: float
    clean: pd.DataFrame
    conflicts: pd.DataFrame
    summary_by_borough: Dict[str, int]


@dataclass
class ConstructionListSummary:
    """Summary statistics for a construction list."""
    total_locations: int
    by_borough: Dict[str, int]
    by_scope: Dict[str, int]
    ada_count: int
    total_estimated_sqft: float
    avg_priority_score: float
    high_priority_count: int  # score >= 0.7


# ---------------------------------------------------------------------------
# Priority Scoring
# ---------------------------------------------------------------------------

def compute_priority_score(
    row: pd.Series,
    weights: Optional[Dict[str, float]] = None,
    severity_col: str = "severity_rating",
    volume_col: str = "pedestrian_volume",
    issued_date_col: str = "issued_date",
    ada_col: str = "ada_flag",
    smart_spine_col: str = "smart_spine",
    complaint_col: str = "complaint_count",
) -> float:
    """Compute a normalized priority score (0-1) for a single work item.

    The score is a weighted combination of:
    - **Severity** (0-10 scale from inspections)
    - **Pedestrian volume** (normalized by max in dataset)
    - **Age** (days since issued_date)
    - **ADA flag** (boolean: 1 if ADA compliance needed)
    - **Smart Spine** (boolean: 1 if on a high-pedestrian corridor)
    - **Complaint count** (number of 311 complaints at location)

    All components are normalized to 0-1 before weighting.
    """
    w = weights or DEFAULT_PRIORITY_WEIGHTS

    severity = float(row.get(severity_col, 0) or 0) / 10.0
    volume = min(float(row.get(volume_col, 0) or 0) / 10000.0, 1.0)

    age = 0.0
    issued = row.get(issued_date_col)
    if issued and not pd.isna(issued):
        try:
            dt = pd.to_datetime(issued)
            if dt.tzinfo is None:
                dt = dt.tz_localize("UTC")
            age = min((pd.Timestamp.now(tz="UTC") - dt).days / 365.0, 1.0)
        except Exception:
            pass

    ada = 1.0 if row.get(ada_col) else 0.0
    spine = 1.0 if row.get(smart_spine_col) else 0.0
    complaints = min(float(row.get(complaint_col, 0) or 0) / 10.0, 1.0)

    score = (
        w.get("severity", 0) * severity
        + w.get("pedestrian_volume", 0) * volume
        + w.get("age_days", 0) * age
        + w.get("ada_flag", 0) * ada
        + w.get("smart_spine", 0) * spine
        + w.get("complaint_count", 0) * complaints
    )
    return round(min(max(score, 0.0), 1.0), 4)


def prioritize_construction_list(
    df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    **column_overrides: str,
) -> pd.DataFrame:
    """Score and sort a DataFrame of inspection records by priority.

    Adds ``_priority_score`` column and sorts descending (highest priority first).

    Args:
        df: DataFrame with inspection/work order data.
        weights: Optional custom weight dict (keys from DEFAULT_PRIORITY_WEIGHTS).
        **column_overrides: Override default column names
            (e.g., ``severity_col="defect_rating"``).

    Returns:
        Copy of the DataFrame with ``_priority_score`` added, sorted by priority.
    """
    out = df.copy()
    out["_priority_score"] = out.apply(
        lambda row: compute_priority_score(row, weights=weights, **column_overrides),
        axis=1,
    )
    return out.sort_values("_priority_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Conflict Detection
# ---------------------------------------------------------------------------

def detect_construction_conflicts(
    construction_df: pd.DataFrame,
    permits_df: pd.DataFrame,
    location_col: str = "location_id",
    permit_location_col: str = "location_id",
    buffer_col: Optional[str] = None,
) -> ConflictCheckResult:
    """Check a construction list against active permits for conflicts.

    A conflict exists when a proposed construction location matches (or is
    near) an active permit location. This is a tabular join-based check;
    for spatial (geometry) conflict detection, use ``ConflictResolver`` from
    the ``conflict`` module.

    Args:
        construction_df: Prioritized construction list.
        permits_df: Active permits (DOB, DOT, utilities, etc.).
        location_col: Column in construction_df identifying the location.
        permit_location_col: Column in permits_df identifying the location.
        buffer_col: (Optional) Not used in tabular mode but reserved for
            future spatial buffering.

    Returns:
        ConflictCheckResult with clean/conflict DataFrames and summary.
    """
    merged = construction_df.merge(
        permits_df[[permit_location_col]].drop_duplicates(),
        left_on=location_col,
        right_on=permit_location_col,
        how="left",
        indicator=True,
        suffixes=("", "_permit"),
    )
    has_conflict = merged["_merge"] == "both"
    merged["_has_conflict"] = has_conflict

    clean = merged[~has_conflict].drop(columns=["_merge", "_has_conflict"], errors="ignore")
    conflicts = merged[has_conflict].drop(columns=["_merge"], errors="ignore")

    # Borough summary
    borough_col = "borough" if "borough" in construction_df.columns else None
    summary_by_borough: Dict[str, int] = {}
    if borough_col and borough_col in conflicts.columns:
        summary_by_borough = conflicts[borough_col].value_counts().to_dict()

    total = len(construction_df)
    conflict_count = int(has_conflict.sum())
    return ConflictCheckResult(
        total_items=total,
        conflict_count=conflict_count,
        conflict_rate=round(conflict_count / max(total, 1) * 100, 2),
        clean=clean.reset_index(drop=True),
        conflicts=conflicts.reset_index(drop=True),
        summary_by_borough=summary_by_borough,
    )


# ---------------------------------------------------------------------------
# Scope and ADA Helpers
# ---------------------------------------------------------------------------

def classify_scope(
    df: pd.DataFrame,
    description_col: str = "description",
    scope_col: str = "_scope",
) -> pd.DataFrame:
    """Classify work items into scope categories based on description text.

    Adds a ``_scope`` column with values from ``SCOPE_CATEGORIES``.
    Uses keyword matching; for more precise classification, consider
    the LLM augmentation module.
    """
    out = df.copy()
    keywords = {
        "pedestrian_ramp": ["ramp", "ped ramp", "pedestrian ramp", "curb ramp", "ada ramp"],
        "curb_replacement": ["curb", "curb replacement"],
        "ada_compliance": ["ada", "accessible", "accessibility", "tactile"],
        "tree_pit": ["tree pit", "tree well"],
        "driveway_apron": ["driveway", "apron"],
        "sidewalk_repair": ["sidewalk", "flag", "concrete", "repair"],
    }

    def _classify(text: str) -> str:
        text_lower = str(text).lower()
        for scope, terms in keywords.items():
            if any(t in text_lower for t in terms):
                return scope
        return "sidewalk_repair"

    out[scope_col] = out[description_col].fillna("").apply(_classify)
    return out


def flag_ada_locations(
    df: pd.DataFrame,
    description_col: str = "description",
    scope_col: str = "_scope",
    ada_col: str = "_ada_required",
) -> pd.DataFrame:
    """Flag locations that require ADA compliance work.

    Sets ``_ada_required`` to True for pedestrian ramp and ADA scope items,
    or if the description mentions ADA-related keywords.
    """
    out = df.copy()
    ada_scopes = {"pedestrian_ramp", "ada_compliance"}
    ada_keywords = ["ada", "accessible", "ramp", "tactile", "detectable warning"]

    def _is_ada(row: pd.Series) -> bool:
        if scope_col in row and row[scope_col] in ada_scopes:
            return True
        desc = str(row.get(description_col, "")).lower()
        return any(kw in desc for kw in ada_keywords)

    out[ada_col] = out.apply(_is_ada, axis=1)
    return out


# ---------------------------------------------------------------------------
# Summary and Export
# ---------------------------------------------------------------------------

def summarize_construction_list(
    df: pd.DataFrame,
    borough_col: str = "borough",
    scope_col: str = "_scope",
    ada_col: str = "_ada_required",
    sqft_col: str = "estimated_sqft",
    priority_col: str = "_priority_score",
) -> ConstructionListSummary:
    """Generate summary statistics for a construction list.

    Args:
        df: Construction list DataFrame (output of ``prioritize_construction_list``).

    Returns:
        ConstructionListSummary dataclass with aggregate stats.
    """
    by_borough = df[borough_col].value_counts().to_dict() if borough_col in df.columns else {}
    by_scope = df[scope_col].value_counts().to_dict() if scope_col in df.columns else {}
    ada_count = int(df[ada_col].sum()) if ada_col in df.columns else 0
    total_sqft = float(df[sqft_col].fillna(0).sum()) if sqft_col in df.columns else 0.0
    avg_priority = float(df[priority_col].mean()) if priority_col in df.columns else 0.0
    high_priority = int((df[priority_col] >= 0.7).sum()) if priority_col in df.columns else 0

    return ConstructionListSummary(
        total_locations=len(df),
        by_borough=by_borough,
        by_scope=by_scope,
        ada_count=ada_count,
        total_estimated_sqft=round(total_sqft, 2),
        avg_priority_score=round(avg_priority, 4),
        high_priority_count=high_priority,
    )


def export_construction_list(
    df: pd.DataFrame,
    path: str,
    format: str = "auto",
    include_summary: bool = True,
) -> str:
    """Export a construction list to file.

    Supported formats (auto-detected from extension):
    - ``.xlsx`` -- Excel workbook with optional summary sheet
    - ``.csv`` -- Standard CSV
    - ``.json`` -- JSON records
    - ``.geojson`` -- GeoJSON (requires a geometry column)

    Args:
        df: Construction list DataFrame.
        path: Output file path.
        format: Force format or "auto" to detect from extension.
        include_summary: For XLSX, add a summary sheet.

    Returns:
        The output path as a string.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fmt = format if format != "auto" else p.suffix.lstrip(".").lower()

    if fmt == "xlsx":
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Construction List", index=False)
            ws = writer.book["Construction List"]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            if include_summary:
                summary = summarize_construction_list(df)
                summary_data = {
                    "Metric": [
                        "Total Locations", "ADA Required", "Total Est. SqFt",
                        "Avg Priority Score", "High Priority (>=0.7)",
                    ],
                    "Value": [
                        summary.total_locations, summary.ada_count,
                        summary.total_estimated_sqft, summary.avg_priority_score,
                        summary.high_priority_count,
                    ],
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
    elif fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "json":
        df.to_json(path, orient="records", indent=2)
    elif fmt == "geojson":
        _export_geojson(df, path)
    else:
        df.to_csv(path, index=False)

    return str(p)


def _export_geojson(df: pd.DataFrame, path: str) -> None:
    """Export DataFrame as GeoJSON FeatureCollection."""
    features = []
    geom_col = None
    for c in ["geometry", "geom", "the_geom", "wkt"]:
        if c in df.columns:
            geom_col = c
            break

    for _, row in df.iterrows():
        props = {k: v for k, v in row.items() if k != geom_col}
        # Convert numpy/pandas types to native Python
        props = {k: (v.item() if hasattr(v, "item") else v) for k, v in props.items()}
        geom = None
        if geom_col and row.get(geom_col):
            raw = row[geom_col]
            if isinstance(raw, dict):
                geom = raw
            elif isinstance(raw, str) and raw.strip().startswith("{"):
                try:
                    geom = json.loads(raw)
                except Exception:
                    geom = None
        features.append({"type": "Feature", "geometry": geom, "properties": props})

    fc = {"type": "FeatureCollection", "features": features}
    Path(path).write_text(json.dumps(fc, indent=2, default=str), encoding="utf-8")
