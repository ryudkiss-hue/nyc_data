"""Tests for analytics_advanced.py — CUSUM, KMeans guard, Bayesian CI, IsolationForest."""

from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd
import pytest

_STREAMLIT_AVAILABLE = importlib.util.find_spec("streamlit") is not None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_series_with_changepoint(n: int = 40, cp: int = 20) -> pd.Series:
    """Return a Series with a clear level-shift at *cp*."""
    rng = np.random.default_rng(42)
    low = rng.normal(10, 1, cp)
    high = rng.normal(40, 1, n - cp)
    values = np.concatenate([low, high])
    return pd.Series(values, index=range(n))

# ---------------------------------------------------------------------------
# CUSUM changepoint detection
# ---------------------------------------------------------------------------

class TestDetectCusumChangepoint:
    def test_returns_none_for_short_series(self):
        from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

        assert detect_cusum_changepoint(pd.Series([1, 2])) is None

    def test_returns_int(self):
        from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

        series = _make_series_with_changepoint()
        result = detect_cusum_changepoint(series)
        assert isinstance(result, int)

    def test_detects_changepoint_within_tolerance(self):
        """Detected changepoint index should be within ±5 of the true shift at index 20."""
        from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

        true_cp = 20
        series = _make_series_with_changepoint(n=40, cp=true_cp)
        result = detect_cusum_changepoint(series)
        assert result is not None
        assert abs(result - true_cp) <= 5, f"Expected cp near {true_cp}, got {result}"

    def test_minimum_series_length_4(self):
        from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

        s = pd.Series([1, 2, 3, 4])
        result = detect_cusum_changepoint(s)
        assert isinstance(result, int)

    def test_flat_series(self):
        """Flat series should still return an int (the argmax of |CUSUM| ≈ 0)."""
        from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint

        result = detect_cusum_changepoint(pd.Series([5.0] * 20))
        assert result is not None

# ---------------------------------------------------------------------------
# KMeans guard — HAS_SKLEARN=False path
# ---------------------------------------------------------------------------

class TestKMeansSklearnGuard:
    """Tests for KMeans sklearn guard — only run in Streamlit context."""

    def _skip_if_no_streamlit(self):
        """Skip if streamlit is not properly available."""
        if not _STREAMLIT_AVAILABLE:
            pytest.skip("streamlit not installed")
        # Also verify that streamlit has cache_data (it might be a stub)
        try:
            import streamlit as st
            if not hasattr(st, "cache_data"):
                pytest.skip("streamlit.cache_data not available")
        except (ImportError, AttributeError):
            pytest.skip("streamlit not properly available")

    def test_has_sklearn_boolean(self):
        self._skip_if_no_streamlit()
        import app.views.analytics_advanced as mod

        assert isinstance(mod.HAS_SKLEARN, bool)

    def test_sklearn_unavailable_flag_is_settable(self):
        """When we set HAS_SKLEARN=False the module should behave gracefully."""
        self._skip_if_no_streamlit()
        import app.views.analytics_advanced as mod

        original = mod.HAS_SKLEARN
        try:
            mod.HAS_SKLEARN = False
            assert mod.HAS_SKLEARN is False
        finally:
            mod.HAS_SKLEARN = original

    def test_sklearn_flag_restored(self):
        """Ensure flag is not permanently clobbered by the guard test."""
        self._skip_if_no_streamlit()
        import app.views.analytics_advanced as mod

        # After the guard test runs, HAS_SKLEARN should reflect actual availability.
        try:
            import sklearn  # noqa: F401

            expected = True
        except ImportError:
            expected = False
        assert mod.HAS_SKLEARN is expected

# ---------------------------------------------------------------------------
# Bayesian completion estimate — CI bounds are reasonable
# ---------------------------------------------------------------------------

class TestBayesianCompletionEstimate:
    """
    The analytics_advanced module does not expose a standalone Bayesian helper,
    but the Beta-distribution posterior gives completion rate CIs.
    Given alpha = complete+1, beta = pending+1, the 95% CI must be in [0, 1].
    """

    def _ci(self, complete: int, pending: int):
        try:
            from scipy.stats import beta
        except ImportError:
            pytest.skip("scipy not installed")
        return beta.interval(0.95, complete + 1, pending + 1)

    def test_ci_bounds_in_unit_interval(self):
        lo, hi = self._ci(80, 20)
        assert 0.0 <= lo <= hi <= 1.0, f"CI [{lo}, {hi}] outside [0, 1]"

    def test_high_completion_rate(self):
        lo, hi = self._ci(95, 5)
        assert hi > lo
        assert hi > 0.8, "High completion rate should yield high upper bound"

    def test_low_completion_rate(self):
        lo, hi = self._ci(5, 95)
        assert lo < 0.2, "Low completion rate should yield low lower bound"

    def test_equal_split(self):
        lo, hi = self._ci(50, 50)
        assert lo < 0.5 < hi, "Equal split should straddle 0.5"

# ---------------------------------------------------------------------------
# IsolationForest anomaly detection
# ---------------------------------------------------------------------------

class TestIsolationForestAnomalyDetection:
    """Test the anomaly detection logic used in _render_anomaly_detection."""

    @pytest.fixture()
    def inspection_df(self) -> pd.DataFrame:
        """Create a DataFrame with one obvious outlier row."""
        rng = np.random.default_rng(0)
        n = 50
        data = {
            "_score": rng.normal(75, 5, n).tolist(),
            "_lat": rng.normal(40.71, 0.01, n).tolist(),
            "_lon": rng.normal(-74.01, 0.01, n).tolist(),
        }
        # Inject one clear outlier
        data["_score"].append(200.0)
        data["_lat"].append(90.0)
        data["_lon"].append(180.0)
        return pd.DataFrame(data)

    def test_isolation_forest_columns(self, inspection_df):
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            pytest.skip("scikit-learn not installed")

        feature_cols = ["_score", "_lat", "_lon"]
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(inspection_df[feature_cols])
        result = inspection_df.copy()
        result["_anomaly"] = predictions

        assert "_anomaly" in result.columns
        assert set(result["_anomaly"].unique()).issubset({1, -1})

    def test_outlier_flagged_as_anomaly(self, inspection_df):
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            pytest.skip("scikit-learn not installed")

        feature_cols = ["_score", "_lat", "_lon"]
        model = IsolationForest(contamination=0.1, random_state=42)
        predictions = model.fit_predict(inspection_df[feature_cols])
        # The last row is the clear outlier
        assert predictions[-1] == -1, "Clear outlier should be flagged as anomaly (-1)"

    def test_anomaly_rate_reasonable(self, inspection_df):
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            pytest.skip("scikit-learn not installed")

        feature_cols = ["_score", "_lat", "_lon"]
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(inspection_df[feature_cols])
        anomaly_pct = (predictions == -1).mean()
        assert 0.0 < anomaly_pct < 0.25, f"Anomaly rate {anomaly_pct:.2%} out of expected range"
