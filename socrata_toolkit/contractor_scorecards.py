"""Contractor Scorecards for DOT Sidewalk Toolkit.

Aggregate contract analytics by contractor to build performance profiles.

Example::

    from socrata_toolkit.contractor_scorecards import generate_scorecards

    scorecards = generate_scorecards(contracts_df)
    for sc in scorecards:
        print(f"{sc.contractor}: efficiency={sc.efficiency_rating}, on_time={sc.on_time_rate}%")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class ContractorScorecard:
    """Performance scorecard for a contractor."""
    contractor: str
    total_contracts: int
    completed_contracts: int
    total_sqft: float
    total_spend: float
    avg_cost_per_sqft: float
    avg_sqft_per_day: float
    on_time_rate: float  # percentage
    first_pass_yield: float  # percentage
    rework_rate: float  # percentage
    efficiency_rating: str  # "A", "B", "C", "D", "F"
    overall_score: float  # 0-100


def generate_scorecards(
    df: pd.DataFrame,
    contractor_col: str = "contractor",
    sqft_col: str = "actual_sqft",
    spend_col: str = "actual_spend",
    days_col: str = "days_worked",
    status_col: str = "status",
    planned_end_col: str = "planned_end_date",
    actual_end_col: str = "actual_end_date",
    first_pass_col: str = "first_pass",
    inspections_col: str = "total_inspections",
    rework_col: str = "rework_spend",
) -> List[ContractorScorecard]:
    """Generate performance scorecards for all contractors."""
    if contractor_col not in df.columns:
        return []

    scorecards = []
    for contractor, group in df.groupby(contractor_col):
        total_contracts = len(group)
        completed = int((group[status_col] == "complete").sum()) if status_col in group.columns else 0
        total_sqft = float(group[sqft_col].fillna(0).sum()) if sqft_col in group.columns else 0
        total_spend = float(group[spend_col].fillna(0).sum()) if spend_col in group.columns else 0
        total_days = float(group[days_col].fillna(0).sum()) if days_col in group.columns else 1

        avg_cost = total_spend / max(total_sqft, 1)
        avg_throughput = total_sqft / max(total_days, 1)

        # On-time rate
        on_time = 0.0
        if planned_end_col in group.columns and actual_end_col in group.columns:
            planned = pd.to_datetime(group[planned_end_col], errors="coerce")
            actual = pd.to_datetime(group[actual_end_col], errors="coerce")
            valid = planned.notna() & actual.notna()
            if valid.sum() > 0:
                on_time = float((actual[valid] <= planned[valid]).sum() / valid.sum() * 100)

        # First pass yield
        fpy = 0.0
        if first_pass_col in group.columns and inspections_col in group.columns:
            fp = float(group[first_pass_col].fillna(0).sum())
            ti = float(group[inspections_col].fillna(0).sum())
            fpy = (fp / ti * 100) if ti > 0 else 0.0

        # Rework rate
        rework_rate = 0.0
        if rework_col in group.columns:
            rework = float(group[rework_col].fillna(0).sum())
            rework_rate = (rework / max(total_spend, 1)) * 100

        # Overall score (weighted composite)
        score = (
            min(avg_throughput / 500, 1.0) * 25 +  # throughput (target 500 sqft/day)
            min(on_time / 100, 1.0) * 25 +          # on-time
            min(fpy / 100, 1.0) * 25 +              # first pass
            max(1.0 - rework_rate / 20, 0) * 15 +   # low rework
            max(1.0 - avg_cost / 50, 0) * 10         # cost efficiency
        )
        score = min(max(score, 0), 100)

        rating = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D" if score >= 40 else "F"

        scorecards.append(ContractorScorecard(
            contractor=str(contractor),
            total_contracts=total_contracts,
            completed_contracts=completed,
            total_sqft=round(total_sqft, 2),
            total_spend=round(total_spend, 2),
            avg_cost_per_sqft=round(avg_cost, 2),
            avg_sqft_per_day=round(avg_throughput, 2),
            on_time_rate=round(on_time, 1),
            first_pass_yield=round(fpy, 1),
            rework_rate=round(rework_rate, 1),
            efficiency_rating=rating,
            overall_score=round(score, 1),
        ))

    return sorted(scorecards, key=lambda s: s.overall_score, reverse=True)


def scorecards_to_dataframe(scorecards: List[ContractorScorecard]) -> pd.DataFrame:
    """Convert scorecards to a DataFrame for display or export."""
    return pd.DataFrame([s.__dict__ for s in scorecards])
