from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class AssetCondition:
    """Represents the condition state of an infrastructure asset."""
    asset_id: str
    condition_index: float  # e.g., PCI 0-100
    state_class: int        # Discrete state (e.g., 1 to 5)
    age_years: float
    replacement_cost: float
    remaining_service_life: float

class MarkovDeteriorationModel:
    """
    Stochastic state-transition forecasting using Markov Chains.
    Predicts asset deterioration over discrete time intervals.
    """
    def __init__(self, transition_matrix: np.ndarray):
        """
        :param transition_matrix: A square matrix where element (i, j) is the probability
                                  of transitioning from state i to state j.
        """
        self.tpm = np.array(transition_matrix, dtype=float)
        # Validate that each row sums to 1 (stochastic matrix)
        if not np.allclose(self.tpm.sum(axis=1), 1.0):
            raise ValueError("Each row in the transition probability matrix must sum to 1.0.")

    def forecast_state_distribution(self, initial_state_vector: np.ndarray, years: int) -> np.ndarray:
        """
        Forecasts the probability distribution of asset states after N years.
        :param initial_state_vector: 1D array of initial state probabilities.
        :param years: Number of transition steps.
        """
        current_vector = np.array(initial_state_vector, dtype=float)
        tpm_power = np.linalg.matrix_power(self.tpm, years)
        return current_vector.dot(tpm_power)


class LifeCycleCostAnalysis:
    """
    Economic Valuation and Life-Cycle Cost Analysis (LCCA) for infrastructure.
    Uses Triple Bottom Line accounting principles and Discounted Cash Flow.
    """
    def __init__(self, discount_rate: float = 0.04):
        self.discount_rate = discount_rate

    def calculate_npv(self, initial_cost: float, recurring_costs: list[float], rehab_costs: dict[int, float], disposal_cost: float, life_years: int) -> float:
        """
        Calculate Net Present Value (NPV) over the asset's life cycle.
        """
        npv = initial_cost

        for year in range(1, life_years + 1):
            cost_this_year = 0.0
            if year <= len(recurring_costs):
                cost_this_year += recurring_costs[year - 1]
            elif len(recurring_costs) > 0:
                cost_this_year += recurring_costs[-1] # assume stable recurring if list is shorter

            if year in rehab_costs:
                cost_this_year += rehab_costs[year]

            npv += cost_this_year / ((1 + self.discount_rate) ** year)

        npv += disposal_cost / ((1 + self.discount_rate) ** life_years)
        return float(npv)

    def calculate_depreciated_replacement_cost(self, asset: AssetCondition, expected_total_life: float) -> float:
        """
        Calculates the DRC to reflect the remaining service life of the asset.
        DRC = Replacement Cost * (Remaining Useful Life / Expected Total Life)
        """
        if expected_total_life <= 0:
            return 0.0
        ratio = max(0.0, min(1.0, asset.remaining_service_life / expected_total_life))
        return float(asset.replacement_cost * ratio)

    def monte_carlo_lcca(self, initial_cost_mean: float, initial_cost_std: float, life_years: int, iterations: int = 1000) -> dict[str, float]:
        """
        Handles uncertainty in LCCA using Monte Carlo simulation.
        """
        npvs = []
        for _ in range(iterations):
            sampled_initial = max(0.0, np.random.normal(initial_cost_mean, initial_cost_std))
            # simplified model: assuming annual maintenance is a random percentage (1-3%) of initial cost
            sampled_annual = sampled_initial * np.random.uniform(0.01, 0.03)
            npv = self.calculate_npv(sampled_initial, [sampled_annual]*life_years, {}, 0.0, life_years)
            npvs.append(npv)

        return {
            "mean_npv": float(np.mean(npvs)),
            "std_npv": float(np.std(npvs)),
            "p5_npv": float(np.percentile(npvs, 5)),
            "p95_npv": float(np.percentile(npvs, 95))
        }


class MROptimization:
    """
    Optimization Framework for Maintenance & Rehabilitation (M&R) Scheduling.
    Implements a greedy heuristic logic as a proxy for Integer Programming to
    maximize condition improvement under a strict budget constraint.
    """
    @staticmethod
    def schedule_rehabilitation(assets: list[AssetCondition], budget: float, benefit_func: callable) -> list[AssetCondition]:
        """
        Prioritize assets for rehabilitation to maximize system performance given a budget.
        Uses a cost-benefit ratio greedy approach (knapsack approximation).

        :param benefit_func: A function that takes an AssetCondition and returns a 'benefit' float score.
        """
        # Calculate benefit and cost-benefit ratio
        scored_assets = []
        for a in assets:
            benefit = benefit_func(a)
            if a.replacement_cost > 0:
                scored_assets.append((a, benefit, benefit / a.replacement_cost))

        # Sort by cost-benefit ratio descending
        scored_assets.sort(key=lambda x: x[2], reverse=True)

        selected = []
        spent = 0.0
        for item in scored_assets:
            asset = item[0]
            if spent + asset.replacement_cost <= budget:
                selected.append(asset)
                spent += asset.replacement_cost

        return selected

def evaluate_system_resiliency(assets: list[AssetCondition], failure_threshold_state: int = 5) -> dict[str, float]:
    """
    Assesses 'system-of-systems' risk by calculating the proportion of the network at risk of failure.
    Uses Fault Tree Analysis (FTA) style leaf-node aggregation.
    """
    total_value = sum(a.replacement_cost for a in assets)
    if total_value == 0:
        return {"risk_ratio": 0.0, "value_at_risk": 0.0}

    at_risk_assets = [a for a in assets if a.state_class >= failure_threshold_state]
    value_at_risk = sum(a.replacement_cost for a in at_risk_assets)

    return {
        "risk_ratio": value_at_risk / total_value,
        "value_at_risk": value_at_risk,
        "critical_assets_count": len(at_risk_assets)
    }
