from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm

logger = logging.getLogger(__name__)

@dataclass
class BayesianInferenceResult:
    """Standardized result for Bayesian MCMC inference."""
    summary: pd.DataFrame
    hdi_intervals: dict[str, tuple[float, float]]
    r_hat_max: float
    ess_min: float
    converged: bool
    trace: az.InferenceData

class BayesianRegressionEngine:
    """
    Elite Bayesian Inference Engine using Markov Chain Monte Carlo (MCMC).
    Specialized for NYC DOT operational modeling (e.g., defect rates, SLA breach rates).
    """

    @staticmethod
    def run_poisson_regression(
        predictor: np.ndarray,
        observed: np.ndarray,
        draws: int = 1000,
        tune: int = 1000,
        chains: int = 2
    ) -> BayesianInferenceResult:
        """
        Performs Bayesian Poisson Regression for count-based operational data.
        Mandates NUTS sampling and formal convergence diagnostics.
        """
        with pm.Model() as model:
            # 1. Prior Justification: Weakly informative priors for operational stability
            alpha = pm.Normal("Intercept", mu=0, sigma=10)
            beta = pm.Normal("Predictor_Effect", mu=0, sigma=10)

            # 2. Stochastic Model Logic
            mu = pm.math.exp(alpha + beta * predictor)

            # 3. Likelihood
            pm.Poisson("Y_obs", mu=mu, observed=observed)

            # 4. MCMC Sampling (NUTS)
            trace = pm.sample(
                draws=draws,
                tune=tune,
                chains=chains,
                target_accept=0.9,
                return_inferencedata=True,
                progressbar=False,
                random_seed=42
            )

        # 5. Convergence Diagnostics (Mandated by GEMINI.md)
        summary = az.summary(trace)
        r_hat_max = float(summary["r_hat"].max())
        ess_min = float(summary["ess_bulk"].min())
        converged = r_hat_max < 1.05

        if not converged:
            logger.warning(f"MCMC Chain did not reach convergence benchmark (R-hat={r_hat_max:.4f}).")

        # 6. Uncertainty Quantification (94% HDI)
        hdi = az.hdi(trace, prob=0.94)
        hdi_dict = {}
        for var in ["Intercept", "Predictor_Effect"]:
            vals = hdi[var].values
            hdi_dict[var] = (float(vals[0]), float(vals[1]))

        return BayesianInferenceResult(
            summary=summary,
            hdi_intervals=hdi_dict,
            r_hat_max=r_hat_max,
            ess_min=ess_min,
            converged=converged,
            trace=trace
        )
