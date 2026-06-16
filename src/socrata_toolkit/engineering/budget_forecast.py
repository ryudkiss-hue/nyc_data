"""Budget Forecasting for DOT Sidewalk Toolkit (Elite Engine).

Advanced stochastic forecasting for spend and completion using
Life-Cycle Cost Analysis (LCCA) and Monte Carlo simulations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .infrastructure import LifeCycleCostAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Risk-adjusted budget forecast snapshot."""

    mean_npv: float
    p95_risk_npv: float
    discount_rate: float
    analysis_period_years: int
    recommendations: list[str] = field(default_factory=list)
    monthly_projection: list[dict[str, Any]] = field(default_factory=list)


class EliteBudgetForecaster:
    """
    Advanced Infrastructure Budget Forecasting Engine.
    Leverages LCCA and Monte Carlo simulations for long-term fiscal planning.
    """

    def __init__(self, discount_rate: float = 0.04):
        self.lcca = LifeCycleCostAnalysis(discount_rate=discount_rate)

    def forecast_sidewalk_budget(self, df: pd.DataFrame, target_years: int = 10) -> ForecastResult:
        """
        Stochastic forecast of sidewalk repair budget needs using NPV.
        """
        if df.empty:
            return ForecastResult(0, 0, 0.04, target_years, ["No data to forecast"])

        # Calculate initial basis from historicals
        mean_unit_cost = df["actual_spend"].mean() if "actual_spend" in df.columns else 15000
        std_unit_cost = df["actual_spend"].std() if "actual_spend" in df.columns else 2500

        # Perform Monte Carlo simulation for risk-adjusted NPV
        mc_results = self.lcca.monte_carlo_lcca(
            initial_cost_mean=mean_unit_cost * len(df),
            initial_cost_std=std_unit_cost * np.sqrt(len(df)),
            life_years=target_years,
            iterations=2000,
        )

        recs = []
        if mc_results["p95_npv"] > mc_results["mean_npv"] * 1.3:
            recs.append("High fiscal volatility detected; increase contingency reserves.")

        # Build deterministic projection for the 'mean' case for reporting
        projection = []
        for yr in range(1, target_years + 1):
            projection.append(
                {
                    "year": yr,
                    "projected_cost_nominal": mean_unit_cost * len(df),
                    "present_value": (mean_unit_cost * len(df))
                    / ((1 + self.lcca.discount_rate) ** yr),
                }
            )

        return ForecastResult(
            mean_npv=mc_results["mean_npv"],
            p95_risk_npv=mc_results["p95_npv"],
            discount_rate=self.lcca.discount_rate,
            analysis_period_years=target_years,
            recommendations=recs,
            monthly_projection=projection,
        )


@dataclass
class SpendForecast:
    current_spend: float
    projected_total: float
    forecast_values: list[float]


def forecast_spend(
    df: pd.DataFrame, horizon_months: int = 6, value_col: str = "actual_spend"
) -> SpendForecast:
    """Forecast spend over the next N months based on historical actuals."""
    current_spend = float(df[value_col].sum()) if value_col in df.columns and not df.empty else 0.0
    n = max(len(df), 1)
    avg_monthly = current_spend / n
    growth_rate = 0.05
    forecast_values = [avg_monthly * (1 + growth_rate * i) for i in range(1, horizon_months + 1)]
    projected_total = current_spend + sum(forecast_values)
    return SpendForecast(
        current_spend=current_spend,
        projected_total=projected_total,
        forecast_values=forecast_values,
    )
