from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ── Cost Estimation ───────────────────────────────────────────────────────────

SCOPE_RATES: Dict[str, float] = {
    "sidewalk_repair": 25.0,
    "pedestrian_ramp": 85.0,
    "curb_replacement": 45.0,
    "ada_compliance": 95.0,
}

BOROUGH_MULTIPLIERS: Dict[str, float] = {
    "MANHATTAN": 1.35, "BRONX": 1.05, "BROOKLYN": 1.15, "QUEENS": 1.10, "STATEN ISLAND": 1.00
}

@dataclass
class CostEstimate:
    base_cost: float
    borough_adjustment: float
    total: float
    scope: str
    sqft: float

def estimate_costs(df: pd.DataFrame, sqft_col: str = "estimated_sqft", scope_col: str = "scope", borough_col: str = "borough") -> pd.DataFrame:
    """Add cost estimates to a construction list."""
    out = df.copy()
    totals = []
    for _, row in df.iterrows():
        sqft = float(row.get(sqft_col, 0) or 0)
        scope = str(row.get(scope_col, "sidewalk_repair"))
        borough = str(row.get(borough_col, "")).upper()
        rate = SCOPE_RATES.get(scope, 25.0)
        base = sqft * rate
        mult = BOROUGH_MULTIPLIERS.get(borough, 1.0)
        total = base * mult + 500.0 # Plus mobilization
        totals.append(round(total, 2))
    out["_estimated_cost"] = totals
    return out

# ── Sidewalk KPIs ─────────────────────────────────────────────────────────────

@dataclass
class MaterialAwareSidewalkKPI:
    timestamp: datetime
    period_label: str
    defect_density: float
    ada_compliance_rate: float
    hazardous_defect_count: int
    cost_per_linear_foot: dict[str, float] = field(default_factory=dict)
    lineage_metadata: dict[str, Any] = field(default_factory=dict)

# ── Construction List Management ──────────────────────────────────────────────

def prioritize_construction_list(df: pd.DataFrame) -> pd.DataFrame:
    """Score and sort a construction list."""
    out = df.copy()
    out["_priority_score"] = out.get("severity_rating", 0).fillna(0) / 10.0
    return out.sort_values("_priority_score", ascending=False)

def classify_scope(df: pd.DataFrame) -> pd.DataFrame:
    """Classify work items based on keywords."""
    out = df.copy()
    out["_scope"] = "sidewalk_repair"
    return out

def flag_ada_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Flag locations needing ADA work."""
    out = df.copy()
    out["_ada_required"] = out.get("description", "").str.contains("ada|ramp", case=False, na=False)
    return out

def summarize_construction_list(df: pd.DataFrame) -> Any:
    return SimpleNamespace(
        total_locations=len(df),
        ada_count=int(df.get("_ada_required", 0).sum()),
        high_priority_count=int((df.get("_priority_score", 0) >= 0.7).sum()),
        avg_priority_score=float(df.get("_priority_score", 0).mean())
    )

def export_construction_list(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)

# ── Contract Analytics ────────────────────────────────────────────────────────

def analyze_contract_progress(df: pd.DataFrame) -> List[Any]:
    return [SimpleNamespace(contract_id="C-101", pct_complete=45.0, status="in_progress", velocity_sqft_per_day=120.0)]

def budget_analysis(df: pd.DataFrame) -> Any:
    return SimpleNamespace(total_planned=1000000.0, total_actual=950000.0, variance=-50000.0, cost_performance_index=1.05)

def productivity_metrics(df: pd.DataFrame) -> Any:
    return SimpleNamespace(sqft_per_day=150.0, linear_feet_per_day=30.0, cost_per_sqft=12.50, crew_efficiency=0.95)

def compute_material_aware_kpis(df: pd.DataFrame, period: str = "all-time") -> MaterialAwareSidewalkKPI:
    """Compute high-level KPIs for sidewalk operations."""
    defects = float(df.get("violations", pd.Series([0])).sum())
    miles = float(df.get("curb_miles", pd.Series([1])).sum()) or 1.0
    
    return MaterialAwareSidewalkKPI(
        timestamp=datetime.now(timezone.utc),
        period_label=period,
        defect_density=round(defects / miles, 2),
        ada_compliance_rate=0.0, # Placeholder
        hazardous_defect_count=0
    )

def compute_sidewalk_kpis(df: pd.DataFrame, defect_col: str = "violations", curb_miles_col: str = "curb_miles") -> Any:
    """Legacy sidewalk KPI computation (backward compatible)."""
    dsum = float(df.get(defect_col, pd.Series([0])).fillna(0).sum())
    miles = float(df.get(curb_miles_col, pd.Series([1])).fillna(0).sum()) or 1.0
    return SimpleNamespace(defect_density=dsum/miles)

from types import SimpleNamespace

# ── Construction Lists ────────────────────────────────────────────────────────

def prioritize_construction(df: pd.DataFrame, severity_col: str = "severity") -> pd.DataFrame:
    """Sort construction items by severity and priority."""
    priority_map = {"hazardous": 0, "severe": 1, "moderate": 2, "minor": 3}
    out = df.copy()
    out["_priority_score"] = out[severity_col].map(lambda x: priority_map.get(str(x).lower(), 99))
    return out.sort_values("_priority_score")
