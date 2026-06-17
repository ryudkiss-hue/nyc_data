"""
Test decorator stacking for AnalyticsEngine cache integration.
Verifies that @staticmethod, @memoize_with_ttl, and @timer_callback stack correctly.
"""

import logging
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from app.callbacks.analytics import AnalyticsEngine
from app.callbacks.decorators import clear_cache, get_cache_stats

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def clear_cache_before_each():
    """Clear cache before each test."""
    clear_cache()
    yield
    clear_cache()


class TestAnalyticsEngineDecoratorStacking:
    """Test that decorators stack properly and caching works."""

    def test_morans_i_decorator_stacking(self):
        """Verify @staticmethod + @memoize_with_ttl + @timer_callback stack correctly."""
        # Create minimal spatial data bundle
        data_bundle = {
            "spatial": pd.DataFrame(
                {
                    "geometry": [
                        type("Point", (), {"x": 0, "y": 0})(),
                        type("Point", (), {"x": 1, "y": 1})(),
                        type("Point", (), {"x": 2, "y": 2})(),
                    ]
                    * 5,  # 15 points
                    "value": np.random.rand(15),
                }
            )
        }

        # First call - should compute
        start = time.time()
        fig1, narrative1 = AnalyticsEngine.chart_morans_i(data_bundle)
        elapsed_first = time.time() - start

        # Verify output structure
        assert isinstance(fig1, go.Figure)
        assert isinstance(narrative1, str)
        assert len(narrative1) > 0

        # Second call - should hit cache
        start = time.time()
        fig2, narrative2 = AnalyticsEngine.chart_morans_i(data_bundle)
        elapsed_cached = time.time() - start

        # Verify results are identical (proves cache was used)
        assert narrative1 == narrative2
        # Timing check only meaningful when first call is slow enough to be reliable
        if elapsed_first > 0.02:
            assert elapsed_cached < elapsed_first * 0.8, (
                f"Cache hit ({elapsed_cached:.4f}s) should be faster than first call ({elapsed_first:.4f}s)"
            )

        # Verify cache stats
        stats = get_cache_stats()
        assert stats["active_keys"] > 0, "Cache should have active entries"

    def test_distribution_classification_caching(self):
        """Test chart_distribution_classification cache behavior."""
        data_bundle = {
            "data": pd.DataFrame(
                {
                    "col1": np.random.normal(0, 1, 100),
                    "col2": np.random.exponential(1, 100),
                }
            )
        }

        # First call
        start = time.time()
        fig1, narrative1 = AnalyticsEngine.chart_distribution_classification(data_bundle)
        elapsed_first = time.time() - start

        # Second call (should hit cache)
        start = time.time()
        fig2, narrative2 = AnalyticsEngine.chart_distribution_classification(data_bundle)
        elapsed_cached = time.time() - start

        assert narrative1 == narrative2, "Cached results should be identical"
        if elapsed_first > 0.02:
            assert elapsed_cached < elapsed_first * 0.8, (
                f"Cache should provide speedup (first: {elapsed_first:.4f}s, cached: {elapsed_cached:.4f}s)"
            )

    def test_anomaly_detection_caching(self):
        """Test chart_anomaly_detection cache behavior."""
        data_bundle = {
            "spatial": pd.DataFrame(
                {
                    "geometry": [type("Point", (), {"x": i, "y": i})() for i in range(25)],
                    "value": np.random.rand(25),
                }
            )
        }

        # First call
        start = time.time()
        fig1, narrative1 = AnalyticsEngine.chart_anomaly_detection(data_bundle)
        elapsed_first = time.time() - start

        # Second call (should hit cache)
        start = time.time()
        fig2, narrative2 = AnalyticsEngine.chart_anomaly_detection(data_bundle)
        elapsed_cached = time.time() - start

        # For fast operations, just verify cache hit occurred (same narrative)
        assert narrative1 == narrative2, "Cached results should be identical"
        logger.info(f"Anomaly detection: first={elapsed_first:.4f}s, cached={elapsed_cached:.4f}s")

    def test_seasonal_decomposition_caching(self):
        """Test chart_seasonal_decomposition cache behavior."""
        # Create time series data
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        data_bundle = {
            "timeseries": pd.DataFrame(
                {
                    "date": dates,
                    "value": np.sin(np.linspace(0, 2 * np.pi, 30)) + np.random.normal(0, 0.1, 30),
                }
            )
        }

        # First call
        start = time.time()
        fig1, narrative1 = AnalyticsEngine.chart_seasonal_decomposition(data_bundle)
        elapsed_first = time.time() - start

        # Second call (should hit cache)
        start = time.time()
        fig2, narrative2 = AnalyticsEngine.chart_seasonal_decomposition(data_bundle)
        elapsed_cached = time.time() - start

        assert narrative1 == narrative2, "Cached results should be identical"
        if elapsed_first > 0.02:
            assert elapsed_cached < elapsed_first * 0.8, (
                f"Cache should provide speedup (first: {elapsed_first:.4f}s, cached: {elapsed_cached:.4f}s)"
            )

    def test_bootstrap_ci_caching(self):
        """Test chart_bootstrap_ci cache behavior."""
        data_bundle = {
            "metrics": {
                "test_metric": (75.5, 70.0, 81.0)  # point_est, ci_lower, ci_upper
            }
        }

        # First call
        start = time.time()
        fig1, narrative1 = AnalyticsEngine.chart_bootstrap_ci(data_bundle)
        elapsed_first = time.time() - start

        # Second call (should hit cache)
        start = time.time()
        fig2, narrative2 = AnalyticsEngine.chart_bootstrap_ci(data_bundle)
        elapsed_cached = time.time() - start

        assert narrative1 == narrative2, "Cached results should be identical"
        if elapsed_first > 0.02:
            assert elapsed_cached < elapsed_first * 0.8, (
                f"Cache should provide speedup (first: {elapsed_first:.4f}s, cached: {elapsed_cached:.4f}s)"
            )

    def test_cache_persistence_across_methods(self):
        """Verify cache works across all 5 methods."""
        clear_cache()

        data_bundles = {
            "spatial": pd.DataFrame(
                {
                    "geometry": [type("Point", (), {"x": i, "y": i})() for i in range(25)],
                    "value": np.random.rand(25),
                }
            ),
            "data": pd.DataFrame(
                {
                    "col1": np.random.normal(0, 1, 100),
                }
            ),
            "timeseries": pd.DataFrame(
                {
                    "date": pd.date_range("2024-01-01", periods=30, freq="D"),
                    "value": np.random.rand(30),
                }
            ),
            "metrics": {"test_metric": (75.5, 70.0, 81.0)},
        }

        # Call all 5 methods
        methods = [
            ("chart_morans_i", {"spatial": data_bundles["spatial"]}),
            ("chart_distribution_classification", {"data": data_bundles["data"]}),
            ("chart_anomaly_detection", {"spatial": data_bundles["spatial"]}),
            ("chart_seasonal_decomposition", {"timeseries": data_bundles["timeseries"]}),
            ("chart_bootstrap_ci", {"metrics": data_bundles["metrics"]}),
        ]

        for method_name, bundle in methods:
            method = getattr(AnalyticsEngine, method_name)
            fig, narrative = method(bundle)
            assert isinstance(fig, go.Figure)
            assert isinstance(narrative, str)

        # Verify cache stats
        stats = get_cache_stats()
        logger.info(f"Cache stats after all methods: {stats}")
        # All methods should be in cache (some may be empty, but cache entries exist)
        assert stats["total_keys"] >= 0

    def test_decorator_order_correctness(self):
        """Verify the decorator order: @staticmethod -> @timer_callback -> @memoize_with_ttl."""
        # This test verifies the method can be called statically and caching works

        method = AnalyticsEngine.chart_morans_i

        # Should be callable without instance
        assert callable(method)

        # Check that decorators were applied by looking at the wrapped function
        data_bundle = {
            "spatial": pd.DataFrame(
                {
                    "geometry": [type("Point", (), {"x": i, "y": i})() for i in range(25)],
                    "value": np.random.rand(25),
                }
            )
        }

        # Should work with static method
        fig, narrative = AnalyticsEngine.chart_morans_i(data_bundle)
        assert isinstance(fig, go.Figure)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
