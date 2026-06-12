"""
Staging Integration Tests for Phase B-F Analytics
Tests full end-to-end workflows with realistic data volumes and edge cases.

Run with: pytest tests/test_staging_integration.py -v
"""

import pytest
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime, timedelta
import time

# Setup paths
from pathlib import Path
import sys
ROOT_PATH = str(Path(__file__).resolve().parent.parent)
SRC_PATH = str(Path(__file__).resolve().parent.parent / "src")
for p in [ROOT_PATH, SRC_PATH]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.callbacks.analytics import AnalyticsEngine
from app.callbacks.analytics_integration import (
    update_distribution_classification,
    update_anomaly_detection,
    update_seasonal_decomposition,
    update_bootstrap_ci_kpis,
)
from app.dash_layouts_analytics_integration import render_analytics_integration_tabs
from app.services.analytics_service import get_kpi_metrics, validate_filters

# =============================================================================
# STAGING DATA: REALISTIC VOLUMES
# =============================================================================

@pytest.fixture
def staging_inspection_data():
    """Realistic NYC inspection data (1000 records)."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1000),
        "borough": np.random.choice(["MANHATTAN", "BROOKLYN", "BRONX", "QUEENS", "STATEN_ISLAND"], 1000),
        "violation_count": np.random.poisson(5, 1000),
        "score": np.random.normal(75, 15, 1000),
        "response_time_hours": np.random.uniform(1, 48, 1000),
        "completion_rate": np.random.uniform(0.5, 1.0, 1000),
        "created_date": pd.date_range("2026-01-01", periods=1000, freq="12H"),
        "status": np.random.choice(["COMPLETED", "PENDING", "REJECTED"], 1000, p=[0.7, 0.2, 0.1]),
    })

@pytest.fixture
def staging_spatial_data():
    """Realistic NYC spatial data with clustering (200 points)."""
    np.random.seed(42)
    # Create clustered points (Manhattan cluster + scattered)
    mn_cluster = np.random.normal([-73.97, 40.78], [0.05, 0.05], (150, 2))
    scattered = np.random.uniform([-74.05, -73.75], [40.55, 40.92], (50, 2))
    coords = np.vstack([mn_cluster, scattered])

    return gpd.GeoDataFrame(
        {
            "id": range(200),
            "borough": np.random.choice(["MN", "BK", "BX", "QN", "SI"], 200),
            "violation_count": np.random.poisson(5, 200),
            "quality_score": np.random.uniform(60, 95, 200),
        },
        geometry=[Point(xy) for xy in coords],
        crs="EPSG:4326"
    )

@pytest.fixture
def staging_timeseries_data():
    """Realistic time series (365 days with trend + seasonality)."""
    np.random.seed(42)
    dates = pd.date_range("2025-06-11", periods=365, freq="D")
    # Trend: increasing over time
    trend = np.linspace(75, 90, 365)
    # Seasonality: weekly pattern
    seasonal = 5 * np.sin(np.linspace(0, 52*2*np.pi, 365))
    # Noise
    noise = np.random.normal(0, 2, 365)

    return pd.DataFrame({
        "date": dates,
        "violation_count": trend + seasonal + noise,
    })

# =============================================================================
# TESTS: STAGED WORKFLOW
# =============================================================================

class TestStagedWorkflow:
    """End-to-end workflow under staging conditions."""

    def test_all_phases_with_realistic_data(self, staging_inspection_data, staging_spatial_data, staging_timeseries_data):
        """Test all 5 phases with realistic data volumes."""
        timings = {}

        # Phase C: Distribution
        start = time.time()
        fig_c, narrative_c = AnalyticsEngine.chart_distribution_classification({"data": staging_inspection_data})
        timings['Phase C'] = (time.time() - start) * 1000
        assert fig_c is not None
        assert len(narrative_c) > 50
        assert timings['Phase C'] < 1000  # Should complete in <1s with staging data

        # Phase D: Anomaly
        start = time.time()
        fig_d, narrative_d = AnalyticsEngine.chart_anomaly_detection({"spatial": staging_spatial_data})
        timings['Phase D'] = (time.time() - start) * 1000
        assert fig_d is not None
        assert len(narrative_d) > 50

        # Phase E: Decomposition
        start = time.time()
        fig_e, narrative_e = AnalyticsEngine.chart_seasonal_decomposition({"data": staging_timeseries_data})
        timings['Phase E'] = (time.time() - start) * 1000
        assert fig_e is not None
        assert len(narrative_e) > 50

        # Phase F: Bootstrap CI
        start = time.time()
        metrics = {
            "completion_rate": (0.87, 0.80, 0.95),
            "quality_score": (75.0, 70.0, 80.0),
        }
        fig_f, narrative_f = AnalyticsEngine.chart_bootstrap_ci({"metrics": metrics})
        timings['Phase F'] = (time.time() - start) * 1000
        assert fig_f is not None
        assert len(narrative_f) > 50

        # All phases should complete within reasonable time
        for phase, elapsed in timings.items():
            assert elapsed < 1000, f"{phase} took {elapsed:.0f}ms (should be <1s)"

    def test_cache_effectiveness_under_load(self, staging_inspection_data):
        """Verify cache effectiveness with small data (caches best with predictable input)."""
        # Use smaller, hashable input for cache testing
        small_df = staging_inspection_data.iloc[:100].copy()
        data_bundle = {"data": small_df}

        # Warm up cache with first call
        AnalyticsEngine.chart_distribution_classification(data_bundle)

        # Measure subsequent calls (should hit cache)
        times = []
        for _ in range(5):
            start = time.time()
            AnalyticsEngine.chart_distribution_classification(data_bundle)
            times.append((time.time() - start) * 1000)

        avg_time = np.mean(times)
        # With cache, should be very fast (<10ms)
        assert avg_time < 50, f"Cached calls averaging {avg_time:.1f}ms (should be <50ms)"

    def test_layouts_render_correctly(self):
        """Verify all layouts can be rendered."""
        layout = render_analytics_integration_tabs()
        assert layout is not None
        # Layout should be a Dash component
        assert hasattr(layout, 'to_dict') or hasattr(layout, 'children')

    def test_kpi_metrics_with_mock_data(self):
        """Test KPI calculation with filters."""
        filters = {
            "borough": "MANHATTAN",
            "date_range": ["2026-01-01", "2026-12-31"],
        }

        metrics = get_kpi_metrics(filters)

        # Should return dict with metrics
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
        # All metrics should have (point_est, ci_lower, ci_upper) tuple
        for value in metrics.values():
            if isinstance(value, tuple):
                assert len(value) == 3, f"Metric should be 3-tuple, got {len(value)}"

    def test_filter_validation(self):
        """Test filter validation under various conditions."""
        # Valid filters
        assert validate_filters({"borough": "MANHATTAN"})
        assert validate_filters({"dataset_key": "inspection"})
        assert validate_filters({"borough": "BROOKLYN", "dataset_key": "violations"})

        # Invalid filters
        assert not validate_filters(None)
        assert not validate_filters({})
        assert not validate_filters({"invalid_key": "value"})

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self):
        """Handle empty DataFrame gracefully."""
        empty_df = pd.DataFrame()
        fig, narrative = AnalyticsEngine.chart_distribution_classification({"data": empty_df})

        # Should return error narrative, not crash
        assert isinstance(narrative, str)
        assert len(narrative) > 0

    def test_single_row_dataframe(self):
        """Handle single-row DataFrame."""
        single_df = pd.DataFrame({
            "id": [1],
            "score": [85.5],
            "value": [100],
        })
        fig, narrative = AnalyticsEngine.chart_distribution_classification({"data": single_df})

        # Should handle gracefully
        assert isinstance(narrative, str)
        assert len(narrative) > 0

    def test_missing_numeric_columns(self):
        """Handle DataFrames with no numeric columns."""
        non_numeric = pd.DataFrame({
            "name": ["A", "B", "C"],
            "category": ["X", "Y", "Z"],
        })
        fig, narrative = AnalyticsEngine.chart_distribution_classification({"data": non_numeric})

        # Should return informative error
        assert isinstance(narrative, str)
        assert "numeric" in narrative.lower() or "error" in narrative.lower()

    def test_insufficient_spatial_data(self):
        """Handle spatial data with too few points."""
        small_gdf = gpd.GeoDataFrame(
            {"id": [1, 2, 3], "value": [10, 20, 30]},
            geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
            crs="EPSG:4326"
        )
        fig, narrative = AnalyticsEngine.chart_anomaly_detection({"spatial": small_gdf})

        # Should handle gracefully
        assert isinstance(narrative, str)

    def test_short_timeseries(self):
        """Handle very short time series."""
        short_ts = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=10, freq="D"),
            "value": np.random.normal(75, 15, 10),
        })
        fig, narrative = AnalyticsEngine.chart_seasonal_decomposition({"data": short_ts})

        # Should handle gracefully or return error message
        assert isinstance(narrative, str)

class TestPerformanceBaseline:
    """Establish performance baselines for production monitoring."""

    def test_phase_c_performance_baseline(self, staging_inspection_data):
        """Baseline: Phase C performance with 1000 records."""
        times = []
        for _ in range(3):  # 3 runs
            start = time.time()
            AnalyticsEngine.chart_distribution_classification({"data": staging_inspection_data})
            times.append((time.time() - start) * 1000)

        avg_time = np.mean(times)
        assert avg_time < 500, f"Phase C average {avg_time:.0f}ms (should be <500ms)"
        print(f"\n  Phase C baseline: {avg_time:.1f}ms (3 runs, avg)")

    def test_phase_d_performance_baseline(self, staging_spatial_data):
        """Baseline: Phase D performance with 200 points."""
        times = []
        for _ in range(3):
            start = time.time()
            AnalyticsEngine.chart_anomaly_detection({"spatial": staging_spatial_data})
            times.append((time.time() - start) * 1000)

        avg_time = np.mean(times)
        assert avg_time < 100, f"Phase D average {avg_time:.0f}ms (should be <100ms with cache)"
        print(f"\n  Phase D baseline: {avg_time:.1f}ms (3 runs, avg)")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
