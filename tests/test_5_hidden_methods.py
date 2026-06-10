"""
Unit and integration tests for the 5 hidden analysis methods.

Tests cover:
1. Moran's I spatial autocorrelation
2. Distribution classification
3. Multivariate anomaly detection
4. Seasonal decomposition
5. Bootstrap confidence intervals
"""

import time

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from app.callbacks.hidden_analysis_methods import (
    bootstrap_confidence_interval,
    decompose_timeseries,
)
from socrata_toolkit.analysis_advanced import (
    classify_all_distributions,
    classify_distribution,
)
from socrata_toolkit.spatial.analytics import SpatialAnomalyDetector, moran_i


# ==========================================
# FIXTURES
# ==========================================


@pytest.fixture
def sample_inspection_data():
    """Create sample inspection data."""
    np.random.seed(42)
    n = 1000
    return pd.DataFrame({
        "objectid": range(n),
        "latitude": np.random.uniform(40.4, 40.9, n),
        "longitude": np.random.uniform(-74.3, -73.7, n),
        "violation_count": np.random.poisson(3, n),
        "inspection_score": np.random.normal(85, 10, n),
        "created_date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "borough": np.random.choice(["MANHATTAN", "BROOKLYN", "QUEENS"], n),
        "_completion_status": np.random.choice(
            ["COMPLETED", "PENDING"], n, p=[0.7, 0.3]
        ),
    })


@pytest.fixture
def sample_geodataframe(sample_inspection_data):
    """Create sample GeoDataFrame."""
    gdf = gpd.GeoDataFrame(
        sample_inspection_data,
        geometry=[
            Point(xy)
            for xy in zip(
                sample_inspection_data["longitude"],
                sample_inspection_data["latitude"],
            )
        ],
        crs="EPSG:4326",
    )
    return gdf


@pytest.fixture
def clustered_data():
    """Create data with spatial clustering."""
    np.random.seed(42)
    # Create 2 clusters
    cluster1 = np.random.normal([40.7, -73.9], 0.05, (500, 2))
    cluster2 = np.random.normal([40.8, -73.8], 0.05, (500, 2))
    coords = np.vstack([cluster1, cluster2])

    values = np.concatenate([
        np.random.normal(10, 2, 500),
        np.random.normal(20, 2, 500),
    ])

    return coords, values


# ==========================================
# METHOD 1: MORAN'S I TESTS
# ==========================================


class TestMoransI:
    """Tests for Moran's I spatial autocorrelation."""

    def test_morans_i_with_valid_data(self, sample_geodataframe):
        """Test Moran's I computation with valid GeoDataFrame."""
        result = moran_i(sample_geodataframe, "inspection_score")
        assert result is not None
        assert -1 <= result <= 1, f"Moran's I out of range: {result}"

    def test_morans_i_with_clustered_data(self, clustered_data):
        """Test Moran's I detects clustering."""
        coords, values = clustered_data
        gdf = gpd.GeoDataFrame(
            {"value": values},
            geometry=[Point(xy) for xy in coords],
            crs="EPSG:4326",
        )
        result = moran_i(gdf, "value")
        assert result is not None
        assert result > 0.2, "Should detect positive spatial autocorrelation"

    def test_morans_i_missing_column(self, sample_geodataframe):
        """Test Moran's I with missing column."""
        result = moran_i(sample_geodataframe, "nonexistent_column")
        assert result is None

    def test_morans_i_too_few_points(self):
        """Test Moran's I with insufficient data."""
        gdf = gpd.GeoDataFrame(
            {"value": [1.0, 2.0]},
            geometry=[Point(0, 0), Point(1, 1)],
            crs="EPSG:4326",
        )
        result = moran_i(gdf, "value")
        assert result is None

    def test_morans_i_constant_values(self, sample_geodataframe):
        """Test Moran's I with constant values."""
        sample_geodataframe["constant"] = 5.0
        result = moran_i(sample_geodataframe, "constant")
        assert result == 0.0, "Should return 0 for constant values"


# ==========================================
# METHOD 2: DISTRIBUTION CLASSIFICATION TESTS
# ==========================================


class TestDistributionClassification:
    """Tests for distribution shape classification."""

    def test_classify_normal_distribution(self):
        """Test classification of normal distribution."""
        df = pd.DataFrame({
            "normal_data": np.random.normal(100, 15, 1000)
        })
        result = classify_distribution(df, "normal_data")
        assert result.classification in ["normal", "uniform"]
        assert abs(result.skewness) < 0.5

    def test_classify_right_skewed_distribution(self):
        """Test classification of right-skewed distribution."""
        df = pd.DataFrame({
            "right_skewed": np.random.exponential(2, 1000)
        })
        result = classify_distribution(df, "right_skewed")
        assert result.classification in ["right_skewed", "normal"]
        assert result.skewness > 0.5

    def test_classify_left_skewed_distribution(self):
        """Test classification of left-skewed distribution."""
        df = pd.DataFrame({
            "left_skewed": -np.random.exponential(2, 1000)
        })
        result = classify_distribution(df, "left_skewed")
        assert result.skewness < -0.5

    def test_classify_all_distributions(self, sample_inspection_data):
        """Test classification of multiple columns."""
        results = classify_all_distributions(sample_inspection_data)
        assert len(results) > 0
        # Should classify numeric columns only
        numeric_count = len(
            sample_inspection_data.select_dtypes(include=[np.number]).columns
        )
        assert len(results) == numeric_count

    def test_classify_sparse_distribution(self):
        """Test classification of sparse data."""
        df = pd.DataFrame({
            "sparse": [1, 1, 1, 1, 2]
        })
        result = classify_distribution(df, "sparse")
        assert result.unique_ratio < 0.1


# ==========================================
# METHOD 3: ANOMALY DETECTION TESTS
# ==========================================


class TestAnomalyDetection:
    """Tests for spatial anomaly detection."""

    def test_detect_spatial_outliers_basic(self, clustered_data):
        """Test basic outlier detection."""
        coords, values = clustered_data
        anomalies = SpatialAnomalyDetector.detect_spatial_outliers(
            list(zip(coords[:, 0], coords[:, 1])),
            values,
            k=5,
            std_threshold=2.0,
        )
        assert isinstance(anomalies, list)
        assert all(isinstance(idx, int) for idx in anomalies)

    def test_detect_spatial_outliers_with_outliers(self):
        """Test detection of known outliers."""
        coords = [[0, 0]] * 10 + [[1, 1]]
        values = [5.0] * 10 + [50.0]
        anomalies = SpatialAnomalyDetector.detect_spatial_outliers(
            coords, values, k=3, std_threshold=2.0
        )
        # Should detect the 50.0 value as an outlier
        assert len(anomalies) > 0

    def test_detect_spatial_outliers_no_outliers(self):
        """Test with normal data (no outliers)."""
        np.random.seed(42)
        coords = [
            [x, y]
            for x in np.linspace(0, 10, 10)
            for y in np.linspace(0, 10, 10)
        ]
        values = np.random.normal(50, 5, 100)
        anomalies = SpatialAnomalyDetector.detect_spatial_outliers(
            coords, values, k=5, std_threshold=3.0
        )
        # With 3 sigma threshold, should have few or no outliers
        assert len(anomalies) <= 5

    def test_detect_outliers_zscore(self):
        """Test Z-score outlier detection."""
        coords = [[0, 0]] * 10
        values = [5.0] * 9 + [100.0]
        anomalies = SpatialAnomalyDetector.detect_outliers(
            coords, values, method="zscore", threshold=2.5
        )
        assert len(anomalies) > 0

    def test_detect_outliers_iqr(self):
        """Test IQR outlier detection."""
        coords = [[0, 0]] * 10
        values = [5.0] * 9 + [100.0]
        anomalies = SpatialAnomalyDetector.detect_outliers(
            coords, values, method="iqr", threshold=1.5
        )
        assert len(anomalies) > 0


# ==========================================
# METHOD 4: SEASONAL DECOMPOSITION TESTS
# ==========================================


class TestSeasonalDecomposition:
    """Tests for time series decomposition."""

    def test_decompose_timeseries_basic(self, sample_inspection_data):
        """Test basic time series decomposition."""
        result = decompose_timeseries(
            sample_inspection_data,
            "created_date",
            "violation_count",
            period=7,
        )
        assert "error" not in result
        assert "original" in result
        assert "trend" in result
        assert "seasonal" in result
        assert "residual" in result
        assert len(result["original"]) == len(result["trend"])

    def test_decompose_timeseries_with_trend(self):
        """Test decomposition of data with clear trend."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        values = np.arange(100) + np.random.normal(0, 2, 100)
        df = pd.DataFrame({
            "date": dates,
            "value": values,
        })
        result = decompose_timeseries(df, "date", "value", period=7)
        assert "error" not in result
        trend = result["trend"][~np.isnan(result["trend"])]
        # Trend should be increasing
        assert trend[-1] > trend[0]

    def test_decompose_timeseries_insufficient_data(self):
        """Test with insufficient data."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "value": [1, 2, 3, 4, 5],
        })
        result = decompose_timeseries(df, "date", "value", period=7)
        assert "error" in result

    def test_decompose_timeseries_different_periods(self):
        """Test with different periods."""
        dates = pd.date_range("2024-01-01", periods=365, freq="D")
        values = (
            50
            + 10 * np.sin(2 * np.pi * np.arange(365) / 7)
            + np.random.normal(0, 2, 365)
        )
        df = pd.DataFrame({
            "date": dates,
            "value": values,
        })

        for period in [7, 14, 30]:
            result = decompose_timeseries(df, "date", "value", period=period)
            assert "error" not in result
            assert len(result["original"]) == 365


# ==========================================
# METHOD 5: BOOTSTRAP CONFIDENCE INTERVALS TESTS
# ==========================================


class TestBootstrapCI:
    """Tests for bootstrap confidence intervals."""

    def test_bootstrap_ci_basic(self):
        """Test basic bootstrap CI computation."""
        data = np.random.normal(100, 15, 1000)
        point, lower, upper = bootstrap_confidence_interval(
            data, confidence=0.95, n_resamples=1000
        )
        assert lower < point < upper
        assert abs(point - 100) < 5  # Should be close to true mean

    def test_bootstrap_ci_coverage(self):
        """Test CI coverage."""
        np.random.seed(42)
        # Generate data with known mean
        true_mean = 50.0
        data = np.random.normal(true_mean, 10, 500)

        point, lower, upper = bootstrap_confidence_interval(
            data, confidence=0.95, n_resamples=5000
        )
        # True mean should be within CI
        assert lower <= true_mean <= upper

    def test_bootstrap_ci_different_confidences(self):
        """Test with different confidence levels."""
        data = np.random.normal(100, 15, 1000)

        ci_90 = bootstrap_confidence_interval(
            data, confidence=0.90, n_resamples=1000
        )
        ci_95 = bootstrap_confidence_interval(
            data, confidence=0.95, n_resamples=1000
        )
        ci_99 = bootstrap_confidence_interval(
            data, confidence=0.99, n_resamples=1000
        )

        # Higher confidence → wider CI
        width_90 = ci_90[2] - ci_90[1]
        width_95 = ci_95[2] - ci_95[1]
        width_99 = ci_99[2] - ci_99[1]

        assert width_90 < width_95 < width_99

    def test_bootstrap_ci_with_nan(self):
        """Test handling of NaN values."""
        data = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        point, lower, upper = bootstrap_confidence_interval(data)
        assert not np.isnan(point)
        assert lower < point < upper

    def test_bootstrap_ci_small_sample(self):
        """Test with small sample size."""
        data = np.array([1.0, 2.0, 3.0])
        point, lower, upper = bootstrap_confidence_interval(data)
        assert point == 2.0


# ==========================================
# INTEGRATION TESTS
# ==========================================


class TestIntegration:
    """Integration tests for all methods."""

    def test_all_methods_with_sample_data(self, sample_inspection_data):
        """Test all methods run without error on sample data."""
        # Method 1: Moran's I
        gdf = gpd.GeoDataFrame(
            sample_inspection_data,
            geometry=[
                Point(xy)
                for xy in zip(
                    sample_inspection_data["longitude"],
                    sample_inspection_data["latitude"],
                )
            ],
            crs="EPSG:4326",
        )
        moran_result = moran_i(gdf, "inspection_score")
        assert moran_result is not None

        # Method 2: Distribution Classification
        dist_results = classify_all_distributions(sample_inspection_data)
        assert len(dist_results) > 0

        # Method 3: Anomaly Detection
        coords = list(
            zip(
                sample_inspection_data["longitude"].values,
                sample_inspection_data["latitude"].values,
            )
        )
        values = sample_inspection_data["inspection_score"].values
        anomalies = SpatialAnomalyDetector.detect_spatial_outliers(
            coords, values, k=5
        )
        assert isinstance(anomalies, list)

        # Method 4: Decomposition
        decomp_result = decompose_timeseries(
            sample_inspection_data, "created_date", "violation_count", period=7
        )
        assert "error" not in decomp_result

        # Method 5: Bootstrap CI
        ci = bootstrap_confidence_interval(
            sample_inspection_data["inspection_score"].values
        )
        assert len(ci) == 3

    def test_methods_handle_edge_cases(self):
        """Test all methods handle edge cases gracefully."""
        # Empty DataFrame
        empty_df = pd.DataFrame()
        results = classify_all_distributions(empty_df)
        assert results == []

        # Single row
        single_df = pd.DataFrame({"col": [1.0]})
        dist = classify_distribution(single_df, "col")
        assert dist.sample_size == 1

        # All NaN
        nan_data = np.array([np.nan] * 10)
        ci = bootstrap_confidence_interval(nan_data)
        assert ci[0] == 0.0


# ==========================================
# PERFORMANCE TESTS
# ==========================================


class TestPerformance:
    """Performance tests to ensure <500ms latency."""

    def test_morans_i_latency(self, sample_geodataframe):
        """Test Moran's I completes in <200ms."""
        start = time.time()
        result = moran_i(sample_geodataframe, "inspection_score")
        elapsed = time.time() - start
        assert elapsed < 0.2, f"Took {elapsed:.3f}s, target <0.2s"
        assert result is not None

    def test_distribution_classification_latency(self, sample_inspection_data):
        """Test distribution classification completes in <300ms."""
        start = time.time()
        results = classify_all_distributions(sample_inspection_data)
        elapsed = time.time() - start
        assert elapsed < 0.3, f"Took {elapsed:.3f}s, target <0.3s"
        assert len(results) > 0

    def test_anomaly_detection_latency(self, clustered_data):
        """Test anomaly detection completes in <400ms."""
        coords, values = clustered_data
        start = time.time()
        anomalies = SpatialAnomalyDetector.detect_spatial_outliers(
            list(zip(coords[:, 0], coords[:, 1])),
            values,
            k=5,
        )
        elapsed = time.time() - start
        assert elapsed < 0.4, f"Took {elapsed:.3f}s, target <0.4s"

    def test_decomposition_latency(self, sample_inspection_data):
        """Test decomposition completes in <500ms."""
        start = time.time()
        result = decompose_timeseries(
            sample_inspection_data,
            "created_date",
            "violation_count",
            period=7,
        )
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Took {elapsed:.3f}s, target <0.5s"
        assert "error" not in result

    def test_bootstrap_ci_latency(self, sample_inspection_data):
        """Test bootstrap CI completes in <300ms."""
        start = time.time()
        ci = bootstrap_confidence_interval(
            sample_inspection_data["inspection_score"].values,
            n_resamples=10000,
        )
        elapsed = time.time() - start
        assert elapsed < 0.3, f"Took {elapsed:.3f}s, target <0.3s"
        assert len(ci) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
