"""VAR multivariate time series analysis."""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.api import VAR
    from statsmodels.tsa.stattools import grangercausalitytests

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


class VARAnalyzer:
    """Vector Autoregression for multivariate KPI analysis."""

    def __init__(self, lag_order: int | None = None):
        """Initialize VAR analyzer.

        Args:
            lag_order: Fixed lag order, or None for auto-selection
        """
        if not HAS_STATSMODELS:
            logger.warning("statsmodels not available; VAR disabled")

        self.lag_order = lag_order
        self.model = None
        self.fitted_model = None

    def select_lag_order(self, data: Dict[str, np.ndarray], max_lags: int = 12) -> int:
        """Select optimal lag order by AIC.

        Args:
            data: Dict of KPI name -> values
            max_lags: Maximum lags to search

        Returns:
            Optimal lag order
        """
        if not HAS_STATSMODELS:
            logger.warning("Cannot select lag order; statsmodels unavailable")
            return 1

        try:
            df = pd.DataFrame(data)
            var_model = VAR(df)

            lag_order_result = var_model.select_order(maxlags=max_lags)
            best_lag = lag_order_result.aic

            logger.info(f"Selected VAR lag order: {best_lag} (AIC: {lag_order_result.aic})")
            return int(best_lag)

        except Exception as e:
            logger.error(f"Lag order selection failed: {str(e)}")
            return 1

    def fit(self, data: Dict[str, np.ndarray]) -> dict:
        """Fit VAR model.

        Args:
            data: Dict of KPI name -> values (must have same length)

        Returns:
            Dict with status, AIC, BIC, and n_equations
        """
        if not HAS_STATSMODELS:
            return {
                "status": "FAILED",
                "error": "statsmodels unavailable",
                "n_equations": len(data),
            }

        try:
            df = pd.DataFrame(data)
            self.model = VAR(df)

            lags = self.lag_order or self.select_lag_order(data)

            self.fitted_model = self.model.fit(maxlags=lags, ic="aic")

            return {
                "status": "SUCCESS",
                "aic": float(self.fitted_model.aic),
                "bic": float(self.fitted_model.bic),
                "n_equations": len(data),
                "lag_order": self.fitted_model.k_ar,
            }

        except Exception as e:
            logger.error(f"VAR fit failed: {str(e)}")
            return {"status": "FAILED", "error": str(e), "n_equations": len(data)}

    def forecast(self, steps: int) -> List[Dict[str, float]]:
        """Forecast future values.

        Args:
            steps: Number of steps ahead

        Returns:
            List of dicts with KPI values per step
        """
        if self.fitted_model is None:
            raise ValueError("Must fit model before forecasting")

        try:
            forecast_array = self.fitted_model.forecast(
                self.fitted_model.endog[-self.fitted_model.k_ar :], steps
            )

            col_names = self.fitted_model.endog.columns.tolist()

            result = []
            for step_idx, values in enumerate(forecast_array):
                step_dict = {col: float(val) for col, val in zip(col_names, values)}
                result.append(step_dict)

            return result

        except Exception as e:
            logger.error(f"VAR forecast failed: {str(e)}")
            raise


class GrangerCausalityTester:
    """Test for Granger causality between KPI pairs."""

    def test_causality(self, cause: np.ndarray, effect: np.ndarray, max_lag: int = 12) -> Dict:
        """Test if `cause` Granger-causes `effect`.

        H0: cause does NOT Granger-cause effect
        p < 0.05: Reject H0 → cause does Granger-cause effect

        Args:
            cause: Series hypothesized to cause
            effect: Series hypothesized to be affected
            max_lag: Maximum lag to test

        Returns:
            Dict with granger_causes (bool) and p_values
        """
        if not HAS_STATSMODELS:
            logger.warning("Cannot test causality; statsmodels unavailable")
            return {"granger_causes": False, "p_values": []}

        try:
            test_data = np.column_stack([effect, cause])

            results = grangercausalitytests(test_data, maxlag=max_lag, verbose=False)

            p_values = [results[lag][0]["ssr_ftest"][1] for lag in range(1, max_lag + 1)]

            granger_causes = any(p < 0.05 for p in p_values)

            return {
                "granger_causes": bool(granger_causes),
                "p_values": [float(p) for p in p_values],
                "min_p_value": float(min(p_values)),
            }

        except Exception as e:
            logger.error(f"Granger causality test failed: {str(e)}")
            return {"granger_causes": False, "p_values": [], "error": str(e)}
