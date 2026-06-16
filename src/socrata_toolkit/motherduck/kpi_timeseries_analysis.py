"""ARIMA/SARIMAX forecasting for KPI time series."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


@dataclass
class ForecastResult:
    """Forecast with confidence intervals."""

    mean: list
    ci_lower: list
    ci_upper: list
    steps: int


@dataclass
class ModelFitResult:
    """Result of fitting a time series model."""

    status: str
    aic: float | None = None
    bic: float | None = None
    model_object: object | None = None
    error_message: str | None = None


class ARIMAForecaster:
    """Fit ARIMA models and generate forecasts."""

    def __init__(self, order: Tuple[int, int, int], include_exog: bool = False):
        """Initialize ARIMA forecaster.

        Args:
            order: (p, d, q) tuple
            include_exog: Whether to include exogenous variables
        """
        if not HAS_STATSMODELS:
            logger.warning("statsmodels not available; ARIMA disabled")

        self.order = order
        self.include_exog = include_exog
        self.model = None
        self.fitted_model = None

    def fit(self, y: np.ndarray, exog: np.ndarray | None = None) -> ModelFitResult:
        """Fit ARIMA model to time series.

        Args:
            y: Time series values
            exog: Optional exogenous variables

        Returns:
            ModelFitResult with AIC/BIC and model object
        """
        if not HAS_STATSMODELS:
            return ModelFitResult(status="FAILED", error_message="statsmodels unavailable")

        try:
            self.model = ARIMA(y, order=self.order, exog=exog if self.include_exog else None)
            self.fitted_model = self.model.fit()

            return ModelFitResult(
                status="SUCCESS",
                aic=float(self.fitted_model.aic),
                bic=float(self.fitted_model.bic),
                model_object=self.fitted_model,
            )

        except Exception as e:
            logger.error(f"ARIMA fit failed: {str(e)}")
            return ModelFitResult(status="FAILED", error_message=str(e))

    def forecast(self, steps: int, exog: np.ndarray | None = None) -> ForecastResult:
        """Generate forecast with 95% CI.

        Args:
            steps: Number of steps ahead
            exog: Optional future exogenous variables

        Returns:
            ForecastResult with mean and bounds
        """
        if self.fitted_model is None:
            raise ValueError("Must fit model before forecasting")

        try:
            forecast_obj = self.fitted_model.get_forecast(
                steps=steps, exog=exog if self.include_exog else None
            )
            forecast_summary = forecast_obj.summary_frame()

            return ForecastResult(
                mean=forecast_summary["mean"].tolist(),
                ci_lower=forecast_summary["mean_ci_lower"].tolist(),
                ci_upper=forecast_summary["mean_ci_upper"].tolist(),
                steps=steps,
            )

        except Exception as e:
            logger.error(f"Forecast failed: {str(e)}")
            raise


class SARIMAXForecaster:
    """Fit SARIMAX models for seasonal data."""

    def __init__(
        self,
        order: Tuple[int, int, int],
        seasonal_order: Tuple[int, int, int, int],
        include_exog: bool = False,
    ):
        """Initialize SARIMAX forecaster.

        Args:
            order: (p, d, q) tuple
            seasonal_order: (P, D, Q, s) tuple where s is seasonal period
            include_exog: Whether to include exogenous variables
        """
        if not HAS_STATSMODELS:
            logger.warning("statsmodels not available; SARIMAX disabled")

        self.order = order
        self.seasonal_order = seasonal_order
        self.include_exog = include_exog
        self.model = None
        self.fitted_model = None

    def fit(self, y: np.ndarray, exog: np.ndarray | None = None) -> ModelFitResult:
        """Fit SARIMAX model."""
        if not HAS_STATSMODELS:
            return ModelFitResult(status="FAILED", error_message="statsmodels unavailable")

        try:
            self.model = SARIMAX(
                y,
                order=self.order,
                seasonal_order=self.seasonal_order,
                exog=exog if self.include_exog else None,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            self.fitted_model = self.model.fit(disp=False)

            return ModelFitResult(
                status="SUCCESS",
                aic=float(self.fitted_model.aic),
                bic=float(self.fitted_model.bic),
                model_object=self.fitted_model,
            )

        except Exception as e:
            logger.error(f"SARIMAX fit failed: {str(e)}")
            return ModelFitResult(status="FAILED", error_message=str(e))

    def forecast(self, steps: int, exog: np.ndarray | None = None) -> ForecastResult:
        """Generate forecast with 95% CI."""
        if self.fitted_model is None:
            raise ValueError("Must fit model before forecasting")

        try:
            forecast_obj = self.fitted_model.get_forecast(
                steps=steps, exog=exog if self.include_exog else None
            )
            forecast_summary = forecast_obj.summary_frame()

            return ForecastResult(
                mean=forecast_summary["mean"].tolist(),
                ci_lower=forecast_summary["mean_ci_lower"].tolist(),
                ci_upper=forecast_summary["mean_ci_upper"].tolist(),
                steps=steps,
            )

        except Exception as e:
            logger.error(f"Forecast failed: {str(e)}")
            raise


class ModelSelection:
    """Automatic ARIMA model selection."""

    def select_arima_order(
        self, y: np.ndarray, max_p: int = 5, max_d: int = 2, max_q: int = 5
    ) -> Tuple[int, int, int]:
        """Grid search for best (p,d,q) based on AIC.

        Args:
            y: Time series
            max_p, max_d, max_q: Maximum values to search

        Returns:
            Best (p, d, q) tuple
        """
        if not HAS_STATSMODELS:
            logger.warning("Cannot select ARIMA order; statsmodels unavailable")
            return (1, 1, 1)

        best_aic = np.inf
        best_order = (0, 0, 0)

        for p in range(max_p + 1):
            for d in range(max_d + 1):
                for q in range(max_q + 1):
                    try:
                        model = ARIMA(y, order=(p, d, q))
                        results = model.fit()
                        if results.aic < best_aic:
                            best_aic = results.aic
                            best_order = (p, d, q)
                    except (ValueError, np.linalg.LinAlgError):
                        continue

        logger.info(f"Best ARIMA order: {best_order} with AIC: {best_aic:.2f}")
        return best_order

    def grid_search_arima(
        self, y: np.ndarray, max_p: int = 5, max_d: int = 2, max_q: int = 5
    ) -> dict:
        """Grid search returning full results."""
        best_order = self.select_arima_order(y, max_p, max_d, max_q)

        try:
            model = ARIMA(y, order=best_order)
            results = model.fit()
            return {
                "best_order": best_order,
                "aic": float(results.aic),
                "bic": float(results.bic),
                "n_obs": len(y),
            }
        except Exception as e:
            logger.error(f"Grid search failed: {str(e)}")
            return {"best_order": (1, 1, 1), "aic": np.inf}
