"""Cost Estimator for DOT Sidewalk Contracts.

Estimate costs for sidewalk repair, pedestrian ramps, and curb work
based on scope type, square footage, borough rate tables, and ADA
requirements.

Example::

    from socrata_toolkit.engineering.cost_estimator import estimate_costs, RATE_TABLE

    df = estimate_costs(construction_df)
    print(df[["address", "_estimated_cost", "_cost_breakdown"]].head())
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Rate Tables (per-unit costs in USD, approximate DOT averages)
# ---------------------------------------------------------------------------

#: Base rates per square foot by scope type.
SCOPE_RATES: Dict[str, float] = {
    "sidewalk_repair": 25.0,
    "pedestrian_ramp": 85.0,
    "curb_replacement": 45.0,
    "ada_compliance": 95.0,
    "tree_pit": 35.0,
    "driveway_apron": 40.0,
}

#: Borough multipliers (Manhattan is most expensive due to logistics).
BOROUGH_MULTIPLIERS: Dict[str, float] = {
    "MANHATTAN": 1.35,
    "BRONX": 1.05,
    "BROOKLYN": 1.15,
    "QUEENS": 1.10,
    "STATEN ISLAND": 1.00,
}

#: ADA compliance surcharge percentage.
ADA_SURCHARGE_PCT: float = 0.15

#: Mobilization/overhead flat fee per location.
MOBILIZATION_FEE: float = 500.0


@dataclass
class CostEstimate:
    """Cost breakdown for a single work item."""
    base_cost: float
    borough_adjustment: float
    ada_surcharge: float
    mobilization: float
    total: float
    rate_per_sqft: float
    scope: str
    sqft: float


@dataclass
class CostSummary:
    """Aggregate cost summary."""
    total_estimated: float
    by_borough: Dict[str, float]
    by_scope: Dict[str, float]
    avg_cost_per_location: float
    avg_cost_per_sqft: float
    location_count: int


def estimate_single(
    sqft: float,
    scope: str = "sidewalk_repair",
    borough: str = "",
    ada_required: bool = False,
) -> CostEstimate:
    """Estimate cost for a single work item."""
    rate = SCOPE_RATES.get(scope, SCOPE_RATES["sidewalk_repair"])
    base = sqft * rate

    multiplier = BOROUGH_MULTIPLIERS.get(borough.upper(), 1.0)
    borough_adj = base * (multiplier - 1.0)

    ada = (base + borough_adj) * ADA_SURCHARGE_PCT if ada_required else 0.0
    total = base + borough_adj + ada + MOBILIZATION_FEE

    return CostEstimate(
        base_cost=round(base, 2),
        borough_adjustment=round(borough_adj, 2),
        ada_surcharge=round(ada, 2),
        mobilization=MOBILIZATION_FEE,
        total=round(total, 2),
        rate_per_sqft=round(total / max(sqft, 1), 2),
        scope=scope,
        sqft=sqft,
    )


def estimate_costs(
    df: pd.DataFrame,
    sqft_col: str = "estimated_sqft",
    scope_col: str = "_scope",
    borough_col: str = "borough",
    ada_col: str = "_ada_required",
    output_prefix: str = "_cost",
) -> pd.DataFrame:
    """Estimate costs for an entire construction list.

    Adds columns: _cost_total, _cost_base, _cost_borough_adj,
    _cost_ada, _cost_rate_per_sqft.
    """
    out = df.copy()
    totals, bases, boro_adjs, ada_surcharges, rates = [], [], [], [], []

    for _, row in df.iterrows():
        sqft = float(row.get(sqft_col, 0) or 0)
        scope = str(row.get(scope_col, "sidewalk_repair"))
        borough = str(row.get(borough_col, ""))
        ada = bool(row.get(ada_col, False))
        est = estimate_single(sqft, scope, borough, ada)
        totals.append(est.total)
        bases.append(est.base_cost)
        boro_adjs.append(est.borough_adjustment)
        ada_surcharges.append(est.ada_surcharge)
        rates.append(est.rate_per_sqft)

    out[f"{output_prefix}_total"] = totals
    out[f"{output_prefix}_base"] = bases
    out[f"{output_prefix}_borough_adj"] = boro_adjs
    out[f"{output_prefix}_ada"] = ada_surcharges
    out[f"{output_prefix}_rate_per_sqft"] = rates
    return out


def summarize_costs(
    df: pd.DataFrame,
    cost_col: str = "_cost_total",
    borough_col: str = "borough",
    scope_col: str = "_scope",
) -> CostSummary:
    """Generate a cost summary from an estimated construction list."""
    total = float(df[cost_col].sum()) if cost_col in df.columns else 0
    by_borough = df.groupby(borough_col)[cost_col].sum().to_dict() if borough_col in df.columns and cost_col in df.columns else {}
    by_scope = df.groupby(scope_col)[cost_col].sum().to_dict() if scope_col in df.columns and cost_col in df.columns else {}
    avg_per_loc = total / max(len(df), 1)
    sqft_col = "estimated_sqft"
    total_sqft = float(df[sqft_col].sum()) if sqft_col in df.columns else 1
    avg_per_sqft = total / max(total_sqft, 1)

    return CostSummary(
        total_estimated=round(total, 2),
        by_borough={k: round(v, 2) for k, v in by_borough.items()},
        by_scope={k: round(v, 2) for k, v in by_scope.items()},
        avg_cost_per_location=round(avg_per_loc, 2),
        avg_cost_per_sqft=round(avg_per_sqft, 2),
        location_count=len(df),
    )
