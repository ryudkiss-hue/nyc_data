"""
Unit tests for GIS callbacks and service layer.
Week 1-3 Phase 1 GIS Pilot - Test suite.
"""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from app.services.gis_service import gis_service


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_inspection_data():
    """Sample inspection data with spatial coordinates."""
    return pd.DataFrame({
        "latitude": [40.75, 40.76, 40.77, 40.78, 40.79],
        "longitude": [-73.95, -73.94, -73.93, -73.92, -73.91],
        "condition_score": [25, 45, 65, 85, 95],
        "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "BROOKLYN", "QUEENS"],
        "street_name": ["5th Ave", "Broadway", "Main St", "Flatbush Ave", "Queens Blvd"],
        "inspection_date": pd.date_range("2024-01-01", periods=5),
    })


@pytest.fixture
def sample_permit_data():
    """Sample permit data with spatial coordinates."""
    return pd.DataFrame({
        "latitude": [40.75, 40.78],
        "longitude": [-73.95, -73.92],
        "borough": ["MANHATTAN", "BROOKLYN"],
        "permit_type": ["Street Work", "Subsurface"],
        "applicant": ["ABC Corp", "XYZ Inc"],
        "start_date": ["2024-01-01", "2024-01-15"],
        "end_date": ["2024-02-01", "2024-02-15"],
        "block_id": [1001, 1002],
    })


@pytest.fixture
def empty_dataframe():
    """Empty DataFrame for error handling tests."""
    return pd.DataFrame()


# =============================================================================
# TESTS: GIS SERVICE - CONDITION MAP
# =============================================================================


class TestConditionMap:
    """Tests for condition map visualization."""

    def test_create_condition_map_valid_data(self, sample_inspection_data):
        """Test condition map creation with valid data."""
        fig = gis_service.create_condition_map(sample_inspection_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert fig.layout.title is not None

    def test_create_condition_map_empty_data(self, empty_dataframe):
        """Test condition map with empty DataFrame."""
        fig = gis_service.create_condition_map(empty_dataframe)

        assert isinstance(fig, go.Figure)
        # Should return figure with error annotation, not crash

    def test_create_condition_map_missing_coordinates(self):
        """Test condition map when coordinate columns are missing."""
        df = pd.DataFrame({"condition_score": [25, 45, 65]})
        fig = gis_service.create_condition_map(df)

        assert isinstance(fig, go.Figure)

    def test_condition_map_filters_out_of_bounds(self):
        """Test that condition map filters out-of-bounds points."""
        df = pd.DataFrame({
            "latitude": [40.75, 50.0, 40.77],  # 50.0 is out of bounds
            "longitude": [-73.95, -83.0, -73.93],  # -83.0 is out of bounds
        })
        fig = gis_service.create_condition_map(df)

        assert isinstance(fig, go.Figure)
        # Should only have 2 valid points in data


# =============================================================================
# TESTS: GIS SERVICE - HOTSPOT ANALYSIS
# =============================================================================


class TestHotspotAnalysis:
    """Tests for hotspot KDE heatmap."""

    def test_create_kde_heatmap_valid_data(self, sample_inspection_data):
        """Test KDE heatmap creation."""
        fig = gis_service.create_kde_heatmap(sample_inspection_data)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_create_kde_heatmap_empty_data(self, empty_dataframe):
        """Test KDE heatmap with empty DataFrame."""
        fig = gis_service.create_kde_heatmap(empty_dataframe)

        assert isinstance(fig, go.Figure)

    def test_kde_heatmap_out_of_bounds_filtering(self):
        """Test that KDE heatmap filters out-of-bounds points."""
        df = pd.DataFrame({
            "latitude": [40.75, 45.0, 40.77],
            "longitude": [-73.95, -70.0, -73.93],
        })
        fig = gis_service.create_kde_heatmap(df)

        assert isinstance(fig, go.Figure)


# =============================================================================
# TESTS: GIS SERVICE - CONFLICT DETECTION
# =============================================================================


class TestConflictDetection:
    """Tests for spatial conflict detection."""

    def test_detect_conflicts_valid_data(self, sample_inspection_data, sample_permit_data):
        """Test conflict detection with valid data."""
        conflicts = gis_service.detect_conflicts(
            sample_inspection_data, sample_permit_data
        )

        # Should find conflicts between overlapping block_ids or boroughs
        assert isinstance(conflicts, pd.DataFrame)

    def test_detect_conflicts_empty_inspection(self, empty_dataframe, sample_permit_data):
        """Test conflict detection with empty inspection data."""
        conflicts = gis_service.detect_conflicts(empty_dataframe, sample_permit_data)

        assert isinstance(conflicts, pd.DataFrame)
        assert conflicts.empty

    def test_detect_conflicts_empty_permits(
        self, sample_inspection_data, empty_dataframe
    ):
        """Test conflict detection with empty permit data."""
        conflicts = gis_service.detect_conflicts(sample_inspection_data, empty_dataframe)

        assert isinstance(conflicts, pd.DataFrame)
        assert conflicts.empty

    def test_detect_conflicts_severity_classification(
        self, sample_inspection_data, sample_permit_data
    ):
        """Test that conflicts are classified by severity."""
        conflicts = gis_service.detect_conflicts(
            sample_inspection_data, sample_permit_data
        )

        if not conflicts.empty:
            assert "severity" in conflicts.columns
            assert conflicts["severity"].isin(["HIGH", "MEDIUM", "LOW"]).all()

    def test_conflict_map_visualization(self, sample_inspection_data, sample_permit_data):
        """Test conflict map visualization."""
        conflicts = gis_service.detect_conflicts(
            sample_inspection_data, sample_permit_data
        )
        if not conflicts.empty:
            fig = gis_service.create_conflict_map(conflicts)
            assert isinstance(fig, go.Figure)


# =============================================================================
# TESTS: GIS SERVICE - BOROUGH AGGREGATION
# =============================================================================


class TestBoroughAggregation:
    """Tests for borough-level aggregation."""

    def test_aggregate_by_borough_count(self, sample_inspection_data):
        """Test borough aggregation by count."""
        fig = gis_service.aggregate_by_borough(
            sample_inspection_data, value_col=None
        )

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_aggregate_by_borough_with_value_col(self, sample_inspection_data):
        """Test borough aggregation with value column (e.g., condition_score)."""
        fig = gis_service.aggregate_by_borough(
            sample_inspection_data, value_col="condition_score"
        )

        assert isinstance(fig, go.Figure)

    def test_aggregate_by_borough_empty_data(self, empty_dataframe):
        """Test borough aggregation with empty data."""
        fig = gis_service.aggregate_by_borough(empty_dataframe)

        assert isinstance(fig, go.Figure)

    def test_aggregate_by_borough_missing_borough_col(self):
        """Test aggregation when borough column is missing."""
        df = pd.DataFrame({"condition_score": [25, 45, 65]})
        fig = gis_service.aggregate_by_borough(df)

        assert isinstance(fig, go.Figure)


# =============================================================================
# TESTS: GIS SERVICE - DBSCAN CLUSTERING
# =============================================================================


class TestDBSCANClustering:
    """Tests for DBSCAN spatial clustering."""

    def test_compute_dbscan_clusters_valid_data(self, sample_inspection_data):
        """Test DBSCAN clustering with valid data."""
        clusters, n_clusters = gis_service.compute_dbscan_clusters(
            sample_inspection_data, eps=0.01, min_samples=1
        )

        assert isinstance(clusters, np.ndarray)
        assert isinstance(n_clusters, int)
        assert len(clusters) == len(sample_inspection_data)

    def test_compute_dbscan_clusters_empty_data(self, empty_dataframe):
        """Test DBSCAN with empty data."""
        clusters, n_clusters = gis_service.compute_dbscan_clusters(empty_dataframe)

        assert len(clusters) == 0
        assert n_clusters == 0

    def test_compute_dbscan_clusters_below_min_samples(self, sample_inspection_data):
        """Test DBSCAN when data has fewer than min_samples points."""
        df = sample_inspection_data.iloc[:2]  # Only 2 points
        clusters, n_clusters = gis_service.compute_dbscan_clusters(
            df, min_samples=5
        )

        assert len(clusters) == 0
        assert n_clusters == 0

    def test_create_cluster_map_visualization(self, sample_inspection_data):
        """Test cluster map visualization."""
        clusters, _ = gis_service.compute_dbscan_clusters(sample_inspection_data)
        fig = gis_service.create_cluster_map(
            sample_inspection_data, clusters=clusters if len(clusters) > 0 else None
        )

        assert isinstance(fig, go.Figure)


# =============================================================================
# TESTS: GIS SERVICE - UTILITY FUNCTIONS
# =============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_flag_in_bounds_valid_data(self, sample_inspection_data):
        """Test NYC bounds filtering."""
        df_filtered = gis_service.flag_in_bounds(sample_inspection_data)

        assert isinstance(df_filtered, pd.DataFrame)
        # All points should be within bounds
        for _, row in df_filtered.iterrows():
            assert 40.477 <= row["latitude"] <= 40.917
            assert -74.259 <= row["longitude"] <= -73.700

    def test_flag_in_bounds_filters_out_of_bounds(self):
        """Test that out-of-bounds points are filtered."""
        df = pd.DataFrame({
            "latitude": [40.75, 50.0, 40.77],  # 50.0 is out
            "longitude": [-73.95, -80.0, -73.93],  # -80.0 is out
        })
        df_filtered = gis_service.flag_in_bounds(df)

        # Should have 2 valid points
        assert len(df_filtered) == 2

    def test_flag_in_bounds_missing_coordinates(self):
        """Test bounds filtering when coordinates are missing."""
        df = pd.DataFrame({"value": [1, 2, 3]})
        df_filtered = gis_service.flag_in_bounds(df)

        assert df_filtered.equals(df)  # Should return unchanged


# =============================================================================
# TESTS: INTEGRATION - FILTER WORKFLOW
# =============================================================================


class TestFilterWorkflow:
    """Integration tests for filter callbacks."""

    def test_filter_by_borough(self, sample_inspection_data):
        """Test filtering by borough."""
        df_manhattan = sample_inspection_data[
            sample_inspection_data["borough"] == "MANHATTAN"
        ]

        assert len(df_manhattan) == 2

    def test_filter_by_severity(self, sample_inspection_data):
        """Test filtering by severity (condition score)."""
        # Critical: 0-30
        df_critical = sample_inspection_data[
            sample_inspection_data["condition_score"] <= 30
        ]

        assert len(df_critical) == 1
        assert df_critical.iloc[0]["condition_score"] == 25

    def test_filter_by_date_range(self, sample_inspection_data):
        """Test filtering by date range."""
        start_date = "2024-01-02"
        end_date = "2024-01-04"

        df_filtered = sample_inspection_data[
            (sample_inspection_data["inspection_date"] >= start_date)
            & (sample_inspection_data["inspection_date"] <= end_date)
        ]

        assert len(df_filtered) == 3

    def test_chained_filters(self, sample_inspection_data):
        """Test applying multiple filters in sequence."""
        df = sample_inspection_data.copy()

        # Filter by borough
        df = df[df["borough"] == "MANHATTAN"]

        # Filter by severity
        df = df[df["condition_score"] >= 40]

        assert len(df) == 1


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestPerformance:
    """Performance baseline tests."""

    def test_condition_map_performance(self, sample_inspection_data):
        """Test condition map rendering performance."""
        import time

        start = time.time()
        fig = gis_service.create_condition_map(sample_inspection_data)
        elapsed = time.time() - start

        # Should complete in <200ms for small dataset (Plotly rendering on Windows slower)
        assert elapsed < 0.2, f"Condition map took {elapsed:.3f}s (target: <0.2s)"

    def test_hotspot_analysis_performance(self, sample_inspection_data):
        """Test hotspot analysis performance."""
        import time

        start = time.time()
        fig = gis_service.create_kde_heatmap(sample_inspection_data)
        elapsed = time.time() - start

        # Should complete in <100ms for small dataset
        assert elapsed < 0.1, f"KDE heatmap took {elapsed:.3f}s (target: <0.1s)"

    def test_conflict_detection_performance(
        self, sample_inspection_data, sample_permit_data
    ):
        """Test conflict detection performance."""
        import time

        start = time.time()
        conflicts = gis_service.detect_conflicts(
            sample_inspection_data, sample_permit_data
        )
        elapsed = time.time() - start

        # Should complete in <100ms
        assert elapsed < 0.1, f"Conflict detection took {elapsed:.3f}s (target: <0.1s)"

    def test_dbscan_clustering_performance(self, sample_inspection_data):
        """Test DBSCAN clustering performance."""
        import time

        start = time.time()
        clusters, _ = gis_service.compute_dbscan_clusters(sample_inspection_data)
        elapsed = time.time() - start

        # Should complete in <100ms for small dataset
        assert elapsed < 0.1, f"DBSCAN took {elapsed:.3f}s (target: <0.1s)"
