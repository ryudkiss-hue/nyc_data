"""Budget Forecasting for DOT Sidewalk Toolkit.

Time-series forecasting for spend, completion, and workload using
simple extrapolation methods (no heavy ML dependencies required).

Example::

    from socrata_toolkit.budget_forecast import forecast_spend, forecast_completion

    spend_fc = forecast_spend(monthly_spend_df, horizon_months=6)
    completion_fc = forecast_completion(contracts_df, daily_capacity=500)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np  # type: ignore[import]
import pandas as pd  # type: ignore[import]


@dataclass
class SpendForecast:
    """Budget spend forecast."""
    current_spend: float
    projected_total: float
    monthly_burn_rate: float
    months_remaining: int
    forecast_values: List[Dict[str, Any]]
    confidence: str  # "high", "medium", "low"


@dataclass
class CompletionForecast:
    """Work completion forecast."""
    total_sqft_remaining: float
    daily_capacity: float
    projected_days: int
    projected_date: str
    weekly_projection: List[Dict[str, Any]]


def forecast_spend(
    df: pd.DataFrame,
    spend_col: str = "actual_spend",
    date_col: str = "date",
    budget_total: float = 0,
    horizon_months: int = 6,
) -> SpendForecast:
    """Forecast future spend using linear extrapolation.

    Args:
        df: Historical spending data with date and spend columns.
        budget_total: Total budget for comparison. 0 = no cap.
        horizon_months: Months to project forward.
    """
    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp = tmp.dropna(subset=[date_col]).sort_values(date_col)

    if tmp.empty:
        return SpendForecast(0, 0, 0, horizon_months, [], "low")

    # Monthly aggregation
    monthly = tmp.set_index(date_col).resample("ME")[spend_col].sum().reset_index()
    monthly.columns = ["date", "spend"]

    if len(monthly) < 2:
        avg = float(monthly["spend"].mean())
        forecast_vals = [{"month": i + 1, "projected_spend": avg} for i in range(horizon_months)]
        return SpendForecast(
            current_spend=float(tmp[spend_col].sum()),
            projected_total=float(tmp[spend_col].sum()) + avg * horizon_months,
            monthly_burn_rate=avg,
            months_remaining=horizon_months,
            forecast_values=forecast_vals,
            confidence="low",
        )

    # Linear regression on monthly spend
    x = np.arange(len(monthly), dtype=float)
    y = monthly["spend"].values.astype(float)
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs

    current_total = float(tmp[spend_col].sum())
    forecast_vals = []
    projected = current_total
    for i in range(horizon_months):
        month_idx = len(monthly) + i
        predicted = max(slope * month_idx + intercept, 0)
        projected += predicted
        forecast_vals.append({"month": i + 1, "projected_spend": round(predicted, 2), "cumulative": round(projected, 2)})

    burn_rate = float(monthly["spend"].mean())
    confidence = "high" if len(monthly) >= 6 else "medium" if len(monthly) >= 3 else "low"

    return SpendForecast(
        current_spend=round(current_total, 2),
        projected_total=round(projected, 2),
        monthly_burn_rate=round(burn_rate, 2),
        months_remaining=horizon_months,
        forecast_values=forecast_vals,
        confidence=confidence,
    )


def forecast_completion(
    df: pd.DataFrame,
    sqft_col: str = "remaining_sqft",
    daily_capacity: float = 500.0,
    horizon_weeks: int = 26,
) -> CompletionForecast:
    """Forecast when remaining work will be completed.

    Args:
        df: DataFrame with remaining work estimates.
        daily_capacity: Expected sqft completed per working day.
        horizon_weeks: Max weeks to project.
    """
    remaining = float(df[sqft_col].fillna(0).sum()) if sqft_col in df.columns else 0
    work_days_per_week = 5
    weekly_capacity = daily_capacity * work_days_per_week

    projected_days = int(remaining / max(daily_capacity, 1))
    projected_date = (pd.Timestamp.now() + pd.Timedelta(days=projected_days)).strftime("%Y-%m-%d")

    weekly = []
    running = remaining
    for week in range(min(horizon_weeks, projected_days // 7 + 2)):
        running = max(running - weekly_capacity, 0)
        weekly.append({"week": week + 1, "remaining_sqft": round(running, 2), "pct_complete": round((1 - running / max(remaining, 1)) * 100, 1)})
        if running <= 0:
            break

    return CompletionForecast(
        total_sqft_remaining=round(remaining, 2),
        daily_capacity=daily_capacity,
        projected_days=projected_days,
        projected_date=projected_date,
        weekly_projection=weekly,
    )


def forecast_workload(
    current_backlog: int,
    weekly_intake: float = 50.0,
    weekly_completion: float = 40.0,
    horizon_weeks: int = 26,
) -> List[Dict[str, Any]]:
    """Project workload (backlog) over time given intake and completion rates.

    Returns weekly projections showing how the backlog grows or shrinks.
    """
    projection = []
    backlog = float(current_backlog)
    for week in range(horizon_weeks):
        backlog = backlog + weekly_intake - weekly_completion
        backlog = max(backlog, 0)
        projection.append({
            "week": week + 1,
            "backlog": round(backlog),
            "net_change": round(weekly_intake - weekly_completion),
        })
    return projection
