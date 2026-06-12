"""Contract Analytics for DOT Sidewalk Inspection & Management.

Tools for analyzing sidewalk and pedestrian ramp contract performance,
budget tracking, and productivity measurement.

Key capabilities:
- Contract progress tracking (% complete, milestones, velocity)
- Budget analysis (planned vs actual spend, burn rate, forecast)
- Productivity metrics (linear feet/day, sqft/crew, cost efficiency)
- Contract comparison and benchmarking across boroughs
- Schedule variance and earned value analysis

Example::

    from socrata_toolkit.engineering.contract_analytics import (
        analyze_contract_progress,
        budget_analysis,
        productivity_metrics,
    )

    progress = analyze_contract_progress(contracts_df)
    budget = budget_analysis(contracts_df)
    productivity = productivity_metrics(contracts_df)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np  # type: ignore[import]
import pandas as pd  # type: ignore[import]

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ContractProgress:
    """Progress summary for a single contract or aggregated set."""
    contract_id: str
    status: str  # "not_started", "in_progress", "complete", "delayed"
    pct_complete: float
    planned_end: str | None
    projected_end: str | None
    days_remaining: int | None
    days_over: int  # 0 if on time, positive if overdue
    milestones_hit: int
    milestones_total: int
    velocity_sqft_per_day: float

@dataclass
class BudgetSummary:
    """Budget analysis for a contract or portfolio."""
    total_planned: float
    total_actual: float
    variance: float  # actual - planned (positive = over budget)
    variance_pct: float
    burn_rate_per_day: float
    forecast_at_completion: float
    cost_performance_index: float  # CPI: earned / actual (>1 = under budget)
    remaining_budget: float

@dataclass
class ProductivityReport:
    """Productivity metrics for a contract or crew."""
    total_sqft_installed: float
    total_linear_feet: float
    total_days_worked: float
    sqft_per_day: float
    linear_feet_per_day: float
    cost_per_sqft: float
    cost_per_linear_foot: float
    crew_efficiency: float  # ratio vs. baseline

# ---------------------------------------------------------------------------
# Contract Progress
# ---------------------------------------------------------------------------

def analyze_contract_progress(
    df: pd.DataFrame,
    contract_id_col: str = "contract_id",
    planned_sqft_col: str = "planned_sqft",
    actual_sqft_col: str = "actual_sqft",
    start_date_col: str = "start_date",
    end_date_col: str = "end_date",
    status_col: str = "status",
) -> list[ContractProgress]:
    """Analyze progress for each contract in the DataFrame.

    Returns a list of ContractProgress dataclasses, one per contract.
    """
    now = pd.Timestamp.now(tz="UTC")
    results = []

    grouped = df.groupby(contract_id_col) if contract_id_col in df.columns else [(None, df)]

    for contract_id, group in grouped:
        planned = float(group[planned_sqft_col].fillna(0).sum()) if planned_sqft_col in group.columns else 0
        actual = float(group[actual_sqft_col].fillna(0).sum()) if actual_sqft_col in group.columns else 0
        pct = round((actual / planned * 100) if planned > 0 else 0.0, 2)

        # Parse dates
        start = _parse_first_date(group, start_date_col)
        end = _parse_first_date(group, end_date_col)

        days_elapsed = (now - start).days if start else 0
        velocity = actual / max(days_elapsed, 1)

        # Project completion
        remaining_sqft = max(planned - actual, 0)
        projected_days = int(remaining_sqft / velocity) if velocity > 0 else None
        projected_end = (now + pd.Timedelta(days=projected_days)).strftime("%Y-%m-%d") if projected_days else None

        days_remaining = (end - now).days if end else None
        days_over = max(0, -days_remaining) if days_remaining is not None else 0

        # Determine status
        if pct >= 100:
            status = "complete"
        elif days_over > 0:
            status = "delayed"
        elif pct > 0:
            status = "in_progress"
        else:
            status = "not_started"

        results.append(ContractProgress(
            contract_id=str(contract_id or "aggregate"),
            status=status,
            pct_complete=pct,
            planned_end=end.strftime("%Y-%m-%d") if end else None,
            projected_end=projected_end,
            days_remaining=days_remaining,
            days_over=days_over,
            milestones_hit=int(group.get("milestone_complete", pd.Series([0])).sum()),
            milestones_total=int(group.get("milestone_total", pd.Series([0])).sum()),
            velocity_sqft_per_day=round(velocity, 2),
        ))

    return results

def _parse_first_date(group: pd.DataFrame, col: str) -> pd.Timestamp | None:
    if col not in group.columns:
        return None
    dates = pd.to_datetime(group[col], errors="coerce").dropna()
    if dates.empty:
        return None
    ts = dates.iloc[0]
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts

# ---------------------------------------------------------------------------
# Budget Analysis
# ---------------------------------------------------------------------------

def budget_analysis(
    df: pd.DataFrame,
    planned_col: str = "planned_spend",
    actual_col: str = "actual_spend",
    earned_col: str = "earned_value",
    start_date_col: str = "start_date",
) -> BudgetSummary:
    """Compute budget summary metrics using Earned Value Management principles.

    Args:
        df: Contract data with budget columns.
        planned_col: Column with planned (budgeted) spend.
        actual_col: Column with actual spend to date.
        earned_col: Column with earned value (budgeted cost of work performed).
            If absent, falls back to ``actual_col``.
        start_date_col: Used to compute burn rate (spend per day).

    Returns:
        BudgetSummary dataclass with variance, CPI, and forecast.
    """
    planned = float(df[planned_col].fillna(0).sum()) if planned_col in df.columns else 0.0
    actual = float(df[actual_col].fillna(0).sum()) if actual_col in df.columns else 0.0
    earned = float(df[earned_col].fillna(0).sum()) if earned_col in df.columns else actual

    variance = actual - planned
    variance_pct = round((variance / planned * 100) if planned > 0 else 0.0, 2)

    # Burn rate: actual spend / days elapsed
    start = _parse_first_date(df, start_date_col)
    now = pd.Timestamp.now(tz="UTC")
    days_elapsed = max((now - start).days, 1) if start else 1
    burn_rate = actual / days_elapsed

    # CPI (Cost Performance Index): earned value / actual cost
    cpi = earned / actual if actual > 0 else 1.0

    # EAC (Estimate At Completion): planned / CPI
    forecast_at_completion = planned / cpi if cpi > 0 else planned

    return BudgetSummary(
        total_planned=round(planned, 2),
        total_actual=round(actual, 2),
        variance=round(variance, 2),
        variance_pct=variance_pct,
        burn_rate_per_day=round(burn_rate, 2),
        forecast_at_completion=round(forecast_at_completion, 2),
        cost_performance_index=round(cpi, 4),
        remaining_budget=round(planned - actual, 2),
    )

# ---------------------------------------------------------------------------
# Productivity Metrics
# ---------------------------------------------------------------------------

def productivity_metrics(
    df: pd.DataFrame,
    sqft_col: str = "actual_sqft",
    linear_feet_col: str = "linear_feet",
    days_col: str = "days_worked",
    cost_col: str = "actual_spend",
    baseline_sqft_per_day: float = 500.0,
) -> ProductivityReport:
    """Compute productivity metrics for contracts or crews.

    Args:
        df: DataFrame with work output and cost data.
        baseline_sqft_per_day: Expected sqft/day for crew efficiency ratio.

    Returns:
        ProductivityReport with throughput and cost efficiency metrics.
    """
    sqft = float(df[sqft_col].fillna(0).sum()) if sqft_col in df.columns else 0.0
    lf = float(df[linear_feet_col].fillna(0).sum()) if linear_feet_col in df.columns else 0.0
    days = float(df[days_col].fillna(0).sum()) if days_col in df.columns else 1.0
    cost = float(df[cost_col].fillna(0).sum()) if cost_col in df.columns else 0.0

    days = max(days, 1.0)
    sqft_per_day = sqft / days
    lf_per_day = lf / days
    cost_per_sqft = cost / max(sqft, 1)
    cost_per_lf = cost / max(lf, 1)
    efficiency = sqft_per_day / baseline_sqft_per_day if baseline_sqft_per_day > 0 else 0.0

    return ProductivityReport(
        total_sqft_installed=round(sqft, 2),
        total_linear_feet=round(lf, 2),
        total_days_worked=round(days, 2),
        sqft_per_day=round(sqft_per_day, 2),
        linear_feet_per_day=round(lf_per_day, 2),
        cost_per_sqft=round(cost_per_sqft, 2),
        cost_per_linear_foot=round(cost_per_lf, 2),
        crew_efficiency=round(efficiency, 4),
    )

# ---------------------------------------------------------------------------
# Contract Comparison
# ---------------------------------------------------------------------------

def compare_contracts(
    df: pd.DataFrame,
    contract_id_col: str = "contract_id",
    sqft_col: str = "actual_sqft",
    cost_col: str = "actual_spend",
    days_col: str = "days_worked",
) -> pd.DataFrame:
    """Generate a comparison table of contracts ranked by cost efficiency.

    Returns a DataFrame with one row per contract including sqft, cost,
    days, cost/sqft, and sqft/day columns.
    """
    if contract_id_col not in df.columns:
        return pd.DataFrame()

    agg = df.groupby(contract_id_col).agg(
        total_sqft=(sqft_col, "sum"),
        total_cost=(cost_col, "sum"),
        total_days=(days_col, "sum"),
    ).reset_index()

    agg["cost_per_sqft"] = (agg["total_cost"] / agg["total_sqft"].replace(0, np.nan)).round(2)
    agg["sqft_per_day"] = (agg["total_sqft"] / agg["total_days"].replace(0, np.nan)).round(2)
    agg = agg.sort_values("cost_per_sqft", ascending=True).reset_index(drop=True)
    return agg

# ---------------------------------------------------------------------------
# Schedule Variance
# ---------------------------------------------------------------------------

def schedule_variance(
    df: pd.DataFrame,
    planned_end_col: str = "planned_end_date",
    actual_end_col: str = "actual_end_date",
    contract_id_col: str = "contract_id",
) -> pd.DataFrame:
    """Compute schedule variance (days early/late) for each contract.

    Adds ``_schedule_variance_days`` column: negative = early, positive = late.
    """
    out = df.copy()
    planned = pd.to_datetime(out[planned_end_col], errors="coerce")
    actual = pd.to_datetime(out[actual_end_col], errors="coerce")
    out["_schedule_variance_days"] = (actual - planned).dt.days
    return out
