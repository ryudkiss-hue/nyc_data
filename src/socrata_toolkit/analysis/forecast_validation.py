"""Forecast validation — compare predictions to actuals for retrospective analysis."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd


@dataclass
class ForecastValidationResult:
    forecast_id: str
    metric: str
    n_forecasts: int
    mae: float
    rmse: float
    bias: float
    within_ci_rate: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def validate_forecasts(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    forecast_col: str,
    actual_col: str,
    join_col: str,
    ci_lower_col: str | None = None,
    ci_upper_col: str | None = None,
) -> ForecastValidationResult:
    """
    Compare forecast predictions to actual outcomes.

    Args:
        forecasts: DataFrame with forecast values (must include join_col, forecast_col)
        actuals:   DataFrame with actual outcomes (must include join_col, actual_col)
        join_col:  Column to join on (e.g., "block_id", "date")
        ci_lower_col / ci_upper_col: Optional CI columns in forecasts DataFrame

    Returns ForecastValidationResult with MAE, RMSE, bias, and CI coverage.
    """
    if join_col not in forecasts.columns:
        raise ValueError(f"join_col '{join_col}' not in forecasts")
    if join_col not in actuals.columns:
        raise ValueError(f"join_col '{join_col}' not in actuals")

    merged = forecasts.merge(actuals[[join_col, actual_col]], on=join_col, how="inner")
    if len(merged) == 0:
        raise ValueError("No matching records between forecasts and actuals on join_col")

    pred = merged[forecast_col].values.astype(float)
    act = merged[actual_col].values.astype(float)
    errors = pred - act

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    bias = float(np.mean(errors))

    within_ci = 0.0
    if (
        ci_lower_col
        and ci_upper_col
        and ci_lower_col in merged.columns
        and ci_upper_col in merged.columns
    ):
        lo = merged[ci_lower_col].values.astype(float)
        hi = merged[ci_upper_col].values.astype(float)
        within_ci = float(np.mean((act >= lo) & (act <= hi)))

    return ForecastValidationResult(
        forecast_id=str(uuid.uuid4()),
        metric=forecast_col,
        n_forecasts=len(merged),
        mae=mae,
        rmse=rmse,
        bias=bias,
        within_ci_rate=within_ci,
    )


def summarize_forecast_accuracy(result: ForecastValidationResult) -> str:
    """Return a plain-English accuracy summary for inclusion in reports."""
    direction = "over-estimated" if result.bias > 0 else "under-estimated"
    bias_abs = abs(result.bias)
    ci_line = (
        f" The 95% confidence interval captured {result.within_ci_rate:.0%} of actual values."
        if result.within_ci_rate > 0
        else ""
    )
    return (
        f"Across {result.n_forecasts} forecasts, the model {direction} by {bias_abs:.2f} units on average "
        f"(MAE={result.mae:.2f}, RMSE={result.rmse:.2f}).{ci_line}"
    )
