from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SimulationResult:
    mean_cost: float
    std_dev: float
    confidence_95_low: float
    confidence_95_high: float
    raw_simulations: np.ndarray


@dataclass
class CostEstimate:
    base_cost: float
    borough_adjustment: float
    ada_surcharge: float
    total: float


@dataclass
class CostSummary:
    total_estimated: float
    location_count: int
    mean_cost: float = 0.0


@dataclass
class CompletionForecast:
    projected_days: int
    weekly_projection: list[dict]


_SCOPE_RATES: dict[str, float] = {
    "sidewalk_repair": 25.0,
    "pedestrian_ramp": 35.0,
    "curb_repair": 30.0,
    "tree_pit": 20.0,
}

_BOROUGH_MULTIPLIERS: dict[str, float] = {
    "MANHATTAN": 1.15,
    "BROOKLYN": 1.05,
    "QUEENS": 1.05,
    "BRONX": 1.00,
    "STATEN ISLAND": 1.00,
    "STATEN_ISLAND": 1.00,
}

_ADA_SURCHARGE_RATE = 0.20


class MonteCarloEstimator:
    """Industrial Probabilistic Cost Estimator for NYC DOT SIM."""

    @staticmethod
    def run_budget_simulation(
        base_cost: float, variance_pct: float = 0.15, iterations: int = 10000
    ) -> SimulationResult:
        simulations = np.random.lognormal(
            mean=np.log(max(base_cost, 1)), sigma=variance_pct, size=iterations
        )
        return SimulationResult(
            mean_cost=float(np.mean(simulations)),
            std_dev=float(np.std(simulations)),
            confidence_95_low=float(np.percentile(simulations, 2.5)),
            confidence_95_high=float(np.percentile(simulations, 97.5)),
            raw_simulations=simulations,
        )

    @staticmethod
    def calculate_npv(annual_costs: list[float], discount_rate: float = 0.03) -> float:
        return float(sum(c / (1 + discount_rate) ** t for t, c in enumerate(annual_costs)))


def estimate_single(
    sqft: float,
    scope: str = "sidewalk_repair",
    borough: str = "BRONX",
    ada_required: bool = False,
    variance_pct: float = 0.15,
) -> CostEstimate:
    """Estimate cost for a single location."""
    rate = _SCOPE_RATES.get(scope.lower(), 25.0)
    base_cost = float(sqft) * rate
    multiplier = _BOROUGH_MULTIPLIERS.get(borough.upper(), 1.0)
    borough_adj = base_cost * (multiplier - 1.0)
    ada_surcharge = base_cost * _ADA_SURCHARGE_RATE if ada_required else 0.0
    total = base_cost + borough_adj + ada_surcharge
    return CostEstimate(
        base_cost=base_cost,
        borough_adjustment=borough_adj,
        ada_surcharge=ada_surcharge,
        total=total,
    )


def estimate_costs(
    df: pd.DataFrame,
    sqft_col: str = "estimated_sqft",
    scope_col: str = "_scope",
    borough_col: str = "borough",
    ada_col: str = "_ada_required",
) -> pd.DataFrame:
    """Estimate costs for each row and add _cost_total column."""
    result = df.copy()
    totals: list[float] = []
    for _, row in df.iterrows():
        sqft = float(row.get(sqft_col, 0) or 0)
        scope = str(row.get(scope_col, "sidewalk_repair") or "sidewalk_repair")
        borough = str(row.get(borough_col, "BRONX") or "BRONX")
        ada = bool(row.get(ada_col, False))
        est = estimate_single(sqft, scope, borough, ada)
        totals.append(est.total)
    result["_cost_total"] = totals
    return result


def summarize_costs(df: pd.DataFrame, cost_col: str = "_cost_total") -> CostSummary:
    """Summarize costs from a DataFrame with a cost column."""
    if cost_col in df.columns:
        total = float(df[cost_col].sum())
        mean = float(df[cost_col].mean()) if len(df) > 0 else 0.0
    else:
        total = 0.0
        mean = 0.0
    return CostSummary(total_estimated=total, location_count=len(df), mean_cost=mean)


def forecast_completion(
    df: pd.DataFrame,
    daily_capacity: float = 100.0,
    sqft_col: str = "remaining_sqft",
) -> CompletionForecast:
    """Forecast completion timeline given daily capacity."""
    total_sqft = float(df[sqft_col].sum()) if sqft_col in df.columns else 0.0
    projected_days = int(total_sqft / max(daily_capacity, 1))

    weekly_projection: list[dict] = []
    remaining = total_sqft
    week = 0
    while remaining > 0 and week < 104:
        week_completion = min(daily_capacity * 7, remaining)
        remaining -= week_completion
        weekly_projection.append(
            {"week": week + 1, "completed": week_completion, "remaining": remaining}
        )
        week += 1
    return CompletionForecast(projected_days=projected_days, weekly_projection=weekly_projection)


def forecast_workload(
    backlog: int,
    weekly_intake: int = 0,
    weekly_completion: int = 0,
    horizon_weeks: int = 10,
) -> list[dict]:
    """Project workload backlog over a number of weeks."""
    result: list[dict] = []
    current = backlog
    for week in range(1, horizon_weeks + 1):
        current = current + weekly_intake - weekly_completion
        result.append({"week": week, "backlog": current})
    return result
