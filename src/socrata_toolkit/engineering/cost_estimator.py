from dataclasses import dataclass
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

class MonteCarloEstimator:
    """Industrial Probabilistic Cost Estimator for NYC DOT SIM."""

    @staticmethod
    def run_budget_simulation(base_cost: float, variance_pct: float = 0.15, iterations: int = 10000) -> SimulationResult:
        """
        Runs a Monte Carlo simulation for project budget risk.
        Fulfills Item 19 & 62: NPV Monte Carlo Visualizer.
        """
        # Assume a skewed normal distribution for infrastructure overruns
        # (Usually biased towards overspending)
        simulations = np.random.lognormal(
            mean=np.log(base_cost),
            sigma=variance_pct,
            size=iterations
        )

        return SimulationResult(
            mean_cost=float(np.mean(simulations)),
            std_dev=float(np.std(simulations)),
            confidence_95_low=float(np.percentile(simulations, 2.5)),
            confidence_95_high=float(np.percentile(simulations, 97.5)),
            raw_simulations=simulations
        )

    @staticmethod
    def calculate_npv(annual_costs: list[float], discount_rate: float = 0.03) -> float:
        """Calculates Net Present Value for LCCA."""
        npv = 0
        for t, cost in enumerate(annual_costs):
            npv += cost / ((1 + discount_rate) ** t)
        return float(npv)

def estimate_costs(df: pd.DataFrame, base_cost_col: str = "base_cost", variance_pct: float = 0.15) -> SimulationResult:
    """Estimate project costs using Monte Carlo simulation."""
    if base_cost_col not in df.columns or df.empty:
        return SimulationResult(0.0, 0.0, 0.0, 0.0, np.array([]))
    total_base_cost = float(df[base_cost_col].sum())
    return MonteCarloEstimator.run_budget_simulation(total_base_cost, variance_pct)
