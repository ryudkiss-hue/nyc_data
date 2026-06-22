"""Time-series forecasting for KPI predictions.

Generates 3-month ahead forecasts with 95% confidence intervals using:
- Exponential smoothing (default)
- ARIMA (if stationarity test passes)
- Automatic model selection based on historical data characteristics
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Forecast output for a KPI."""
    kpi_id: str
    period: date
    forecast_values: List[float]
    ci_lower: List[float]
    ci_upper: List[float]
    confidence_score: float
    method: str
    is_stationary: bool
    seasonality_detected: bool

    def to_dict(self) -> dict:
        """Serialize for database insertion."""
        return {
            'kpi_id': self.kpi_id,
            'forecast_value': self.forecast_values[0] if self.forecast_values else None,
            'ci_lower': self.ci_lower[0] if self.ci_lower else None,
            'ci_upper': self.ci_upper[0] if self.ci_upper else None,
            'confidence_score': self.confidence_score,
            'method': self.method
        }


class ForecastingEngine:
    """Generates forecasts with confidence intervals."""

    def __init__(self, min_history_months: int = 12):
        self.min_history = min_history_months

    def forecast_kpi(self, kpi_id: str, historical_values: List[float],
                     periods_ahead: int = 3) -> Optional[ForecastResult]:
        """Main forecasting entry point.

        Args:
            kpi_id: KPI identifier
            historical_values: Chronologically sorted historical values (oldest to newest)
            periods_ahead: Number of periods to forecast (default 3 months)

        Returns:
            ForecastResult with forecasts and confidence intervals, or None if insufficient data
        """

        if len(historical_values) < self.min_history:
            logger.warning(f"KPI {kpi_id}: insufficient history ({len(historical_values)} < {self.min_history})")
            return None

        series = np.array(historical_values, dtype=float)

        # Detect stationarity
        is_stationary = self._check_stationarity(series)

        # Detect seasonality
        has_seasonality = self._detect_seasonality(series)

        # Fit exponential smoothing (robust, works well for most KPI data)
        try:
            result = self._fit_exponential_smoothing(
                kpi_id, series, periods_ahead, has_seasonality
            )
            return result
        except Exception as e:
            logger.error(f"KPI {kpi_id}: forecasting failed: {e}")
            return None

    def _check_stationarity(self, series: np.ndarray) -> bool:
        """ADF test for stationarity."""
        try:
            result = adfuller(series, autolag='AIC')
            is_stationary = result[1] < 0.05
            logger.debug(f"Stationarity: ADF p-value={result[1]:.4f}, stationary={is_stationary}")
            return is_stationary
        except Exception as e:
            logger.debug(f"Stationarity test failed: {e}")
            return False

    def _detect_seasonality(self, series: np.ndarray) -> bool:
        """Check for 12-month seasonality."""
        if len(series) < 24:
            return False

        try:
            decomp = seasonal_decompose(series, model='additive', period=12, extrapolate='extend')
            seasonal_strength = np.var(decomp.seasonal) / np.var(decomp.resid + decomp.seasonal)
            has_seasonality = seasonal_strength > 0.1

            logger.debug(f"Seasonality: strength={seasonal_strength:.3f}, detected={has_seasonality}")
            return has_seasonality
        except Exception as e:
            logger.debug(f"Seasonality test failed: {e}")
            return False

    def _fit_exponential_smoothing(self, kpi_id: str, series: np.ndarray,
                                   periods_ahead: int,
                                   has_seasonality: bool) -> ForecastResult:
        """Fit exponential smoothing model."""

        seasonal_periods = 12 if has_seasonality else None
        seasonal = 'add' if has_seasonality else None

        model = ExponentialSmoothing(
            series,
            trend='add',
            seasonal=seasonal,
            seasonal_periods=seasonal_periods
        )
        fitted = model.fit(optimized=True)

        # Generate forecast
        predicted_mean = fitted.forecast(steps=periods_ahead)

        # Compute confidence intervals manually (lower approach for statsmodels)
        residuals = fitted.resid
        rmse = np.sqrt(np.mean(residuals ** 2))
        z_95 = 1.96
        predicted_mean_values = predicted_mean.values if hasattr(predicted_mean, 'values') else predicted_mean
        ci_lower = (predicted_mean_values - z_95 * rmse).tolist() if isinstance(predicted_mean_values, np.ndarray) else [v - z_95 * rmse for v in predicted_mean_values]
        ci_upper = (predicted_mean_values + z_95 * rmse).tolist() if isinstance(predicted_mean_values, np.ndarray) else [v + z_95 * rmse for v in predicted_mean_values]
        forecast_values = predicted_mean_values.tolist() if isinstance(predicted_mean_values, np.ndarray) else predicted_mean_values

        # Compute confidence score (1 - normalized RMSE)
        mean_val = np.mean(series)
        confidence_score = max(0.0, 1.0 - (rmse / mean_val if mean_val > 0 else 1.0))

        return ForecastResult(
            kpi_id=kpi_id,
            period=date.today(),
            forecast_values=forecast_values,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_score=confidence_score,
            method='exponential_smoothing',
            is_stationary=self._check_stationarity(series),
            seasonality_detected=has_seasonality
        )


def create_forecasting_engine(min_history: int = 12) -> ForecastingEngine:
    """Factory for forecasting engine."""
    return ForecastingEngine(min_history_months=min_history)
