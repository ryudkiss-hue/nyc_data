"""Stationarity testing and differencing for KPI time series."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.stattools import adfuller, kpss

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


@dataclass
class StationarityResult:
    """Result of stationarity test."""

    test_name: str
    statistic: float
    p_value: float
    is_stationary: bool
    n_obs: int
    lags_used: int
    critical_values: dict


class StationarityTester:
    """Test and prepare time series for ARIMA modeling."""

    def __init__(self):
        """Initialize tester."""
        if not HAS_STATSMODELS:
            logger.warning("statsmodels not available; stationarity tests skipped")

<<<<<<< Updated upstream
    def adf_test(self, series: np.ndarray, autolag: str = "AIC") -> StationarityResult | None:
=======
    def adf_test(self, series: np.ndarray, autolag: str = 'AIC') -> StationarityResult | None:
>>>>>>> Stashed changes
        """Augmented Dickey-Fuller test.

        H0: Series has unit root (non-stationary)
        If p < 0.05: Reject H0 → Series is stationary

        Args:
            series: Time series values
            autolag: Lag selection method ('AIC', 'BIC', 'FPE', 't-stat')

        Returns:
            StationarityResult or None if statsmodels unavailable
        """
        if not HAS_STATSMODELS:
            return None

        try:
            result = adfuller(series, autolag=autolag, regression="c")

            return StationarityResult(
                test_name="ADF",
                statistic=float(result[0]),
                p_value=float(result[1]),
                is_stationary=float(result[1]) > 0.05,
                n_obs=int(result[3]),
                lags_used=int(result[2]),
                critical_values={
                    "1%": float(result[4]["1%"]),
                    "5%": float(result[4]["5%"]),
                    "10%": float(result[4]["10%"]),
                },
            )
        except Exception as e:
            logger.error(f"ADF test failed: {str(e)}")
            return None

<<<<<<< Updated upstream
    def kpss_test(self, series: np.ndarray, regression: str = "c") -> StationarityResult | None:
=======
    def kpss_test(self, series: np.ndarray, regression: str = 'c') -> StationarityResult | None:
>>>>>>> Stashed changes
        """KPSS test (opposite hypothesis to ADF).

        H0: Series is stationary
        If p < 0.05: Reject H0 → Series is non-stationary

        Args:
            series: Time series values
            regression: Regression type ('c' for constant, 'ct' for constant+trend)

        Returns:
            StationarityResult or None if statsmodels unavailable
        """
        if not HAS_STATSMODELS:
            return None

        try:
            result = kpss(series, regression=regression, nlags="auto")

            return StationarityResult(
                test_name="KPSS",
                statistic=float(result[0]),
                p_value=float(result[1]),
                is_stationary=float(result[1]) > 0.05,
                n_obs=len(series),
                lags_used=result[3] if len(result) > 3 else 0,
                critical_values={
                    "10%": float(result[2]["10%"]),
                    "5%": float(result[2]["5%"]),
                    "1%": float(result[2]["1%"]),
                },
            )
        except Exception as e:
            logger.error(f"KPSS test failed: {str(e)}")
            return None

    def determine_differencing_order(
        self, series: np.ndarray, max_diff: int = 2, method: str = "adf"
    ) -> int:
        """Determine number of differences needed for stationarity.

        Args:
            series: Time series values
            max_diff: Maximum differencing to try (typically 0, 1, or 2)
            method: 'adf' or 'kpss' test

        Returns:
            Number of differences (0, 1, or max_diff)
        """
        if not HAS_STATSMODELS:
            logger.warning("Cannot determine differencing; statsmodels unavailable")
            return 0

        test_fn = self.adf_test if method == "adf" else self.kpss_test

        current_series = np.asarray(series, dtype=float)

        for d in range(max_diff + 1):
            result = test_fn(current_series)

            if result and result.is_stationary:
                logger.info(f"Series becomes stationary after {d} differencing(s)")
                return d

            if d < max_diff:
                current_series = np.diff(current_series)

        logger.warning(f"Series not stationary after {max_diff} differences; using d={max_diff}")
        return max_diff


def adf_test(series: np.ndarray) -> dict | None:
    """Convenience function for ADF test."""
    tester = StationarityTester()
    result = tester.adf_test(series)
    if result:
        return {
            "test": "ADF",
            "statistic": result.statistic,
            "p_value": result.p_value,
            "is_stationary": result.is_stationary,
        }
    return None


def kpss_test(series: np.ndarray) -> dict | None:
    """Convenience function for KPSS test."""
    tester = StationarityTester()
    result = tester.kpss_test(series)
    if result:
        return {
            "test": "KPSS",
            "statistic": result.statistic,
            "p_value": result.p_value,
            "is_stationary": result.is_stationary,
        }
    return None


def determine_differencing_order(series: np.ndarray, max_diff: int = 2) -> int:
    """Convenience function for determining d."""
    tester = StationarityTester()
    return tester.determine_differencing_order(series, max_diff)
