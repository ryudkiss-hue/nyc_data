import numpy as np
import pandas as pd
import pytest

from socrata_toolkit.analysis.bayesian import BayesianRegressionEngine
from socrata_toolkit.engineering.infrastructure import (
    AssetCondition,
    MarkovDeteriorationModel,
    MROptimization,
)

def test_markov_stochastic_matrix_validation():
    """Verify that the Markov model rejects non-stochastic matrices."""
    # Rows don't sum to 1.0
    bad_matrix = np.array([
        [0.8, 0.2],
        [0.1, 0.7] # Sums to 0.8
    ])
    with pytest.raises(ValueError, match="must sum to 1.0"):
        MarkovDeteriorationModel(bad_matrix)

    # Valid matrix
    good_matrix = np.array([
        [0.9, 0.1],
        [0.0, 1.0]
    ])
    model = MarkovDeteriorationModel(good_matrix)
    assert np.allclose(model.tpm.sum(axis=1), 1.0)

def test_markov_forecast_convergence():
    """Verify state distribution forecast over time."""
    tpm = np.array([
        [0.8, 0.2],
        [0.0, 1.0] # State 2 is absorbing (Failed)
    ])
    model = MarkovDeteriorationModel(tpm)
    initial = np.array([1.0, 0.0]) # 100% in Excellent

    # After 1 year
    y1 = model.forecast_state_distribution(initial, 1)
    assert np.allclose(y1, [0.8, 0.2])

    # After many years, should converge to Failed state
    y_long = model.forecast_state_distribution(initial, 50)
    assert y_long[1] > 0.99

def test_mr_optimization_greedy_logic():
    """Verify that MROptimization selects the highest benefit-cost ratio."""
    assets = [
        AssetCondition("A1", 50, 3, 10, 1000, 5), # ratio 0.05 (Benefit 50)
        AssetCondition("A2", 90, 4, 15, 1000, 2), # ratio 0.09 (Benefit 90)
        AssetCondition("A3", 30, 2, 5, 200, 8),   # ratio 0.15 (Benefit 30)
    ]

    def simple_benefit(a): return a.condition_index

    # Budget of 1200
    # Should pick A3 (best ratio 30/200=0.15) then A2 (90/1000=0.09)
    # Total spent = 1200.
    selected = MROptimization.schedule_rehabilitation(assets, 1200, simple_benefit)

    assert len(selected) == 2
    assert selected[0].asset_id == "A3"
    assert selected[1].asset_id == "A2"

@pytest.mark.slow
def test_bayesian_poisson_regression_recovery():
    """Verify that PyMC model can recover parameters from synthetic data."""
    # Generate data: y = exp(0.5 + 0.2 * x)
    np.random.seed(42)
    x = np.linspace(0, 10, 20)
    true_alpha = 0.5
    true_beta = 0.2
    mu = np.exp(true_alpha + true_beta * x)
    y = np.random.poisson(mu)

    engine = BayesianRegressionEngine()
    # Use few draws for faster test
    result = engine.run_poisson_regression(x, y, draws=500, tune=500, chains=2)

    assert result.converged is True
    # HDI should contain the true parameters
    assert result.hdi_intervals["Intercept"][0] < true_alpha < result.hdi_intervals["Intercept"][1]
    assert result.hdi_intervals["Predictor_Effect"][0] < true_beta < result.hdi_intervals["Predictor_Effect"][1]
