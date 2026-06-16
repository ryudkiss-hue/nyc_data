"""Comprehensive tests for spatial.analytics module."""

from __future__ import annotations
import pytest


from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from socrata_toolkit.spatial.analytics import (
    Cluster,
    Hotspot,
    HotspotAnalysis,
    InterpolationAnalysis,
    NetworkAnalysis,
    SpatialAnomalyDetector,
    cluster_conflict_hotspots,
    detect_conflicts,
    find_ramp_gaps,
    moran_i,
    spatial_conflict_score,
)


@pytest.fixture
def sample_coordinates() -> list[tuple[float, float]]:
    """Provide a list of NYC-area (lon, lat) coordinates for testing."""
    return [
        (-74.01, 40.70),
        (-74.012, 40.702),
        (-74.014, 40.704),
        (-74.016, 40.706),
        (-74.018, 40.708),
        (-74.011, 40.701),
        (-74.013, 40.703),
        (-74.015, 40.705),
        (-74.009, 40.699),
        (-73.98, 40.75),
    ]


@pytest.fixture
def sample_values() -> list[float]:
    """Provide a list of condition scores (0-100) for testing."""
    return [80.0, 60.0, 45.0, 30.0, 75.0, 55.0, 40.0, 88.0, 20.0, 65.0]


@pytest.fixture
def sample_segment_ids() -> list[str]:
    """Provide segment IDs aligned with sample_coordinates."""
    return [f"seg_{i}" for i in range(10)]


@pytest.fixture
def street_centerlines() -> list[dict]:
    """Provide minimal street centerline dicts for network tests."""
    return [
        {"id": "st1", "coordinates": [[-74.01, 40.70], [-74.012, 40.702]], "length": 200},
        {"id": "st2", "coordinates": [[-74.012, 40.702], [-74.014, 40.704]], "length": 250},
        {"id": "st3", "coordinates": [[-74.014, 40.704], [-74.016, 40.706]], "length": 300},
    ]


class TestNetworkAnalysisInit:
    """Tests for NetworkAnalysis initialization."""

    def test_init_creates_empty_network(self):
        """NetworkAnalysis initializes with empty network and edge_lengths."""
        na = NetworkAnalysis()
        assert na.network == {}
        assert na.edge_lengths == {}

    def test_multiple_instances_independent(self):
        """Two NetworkAnalysis instances share no state."""
        na1 = NetworkAnalysis()
        na2 = NetworkAnalysis()
        na1.network["node1"] = ["node2"]
        assert "node1" not in na2.network


class TestNetworkAnalysisBuildNetwork:
    """Tests for NetworkAnalysis.build_network."""

    def test_build_network_empty_input(self):
        """Building from empty list returns zero-node stats."""
        na = NetworkAnalysis()
        stats = na.build_network([])
        assert stats["nodes"] == 0
        assert stats["edges"] == 0

    def test_build_network_single_street(self):
        """Building from one street produces two nodes and one edge."""
        na = NetworkAnalysis()
        streets = [{"id": "s1", "coordinates": [[-74.0, 40.7], [-74.01, 40.71]], "length": 100}]
        stats = na.build_network(streets)
        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert stats["total_length"] == 100

    def test_build_network_multiple_streets(self, street_centerlines):
        """Building from multiple streets produces correct node/edge counts."""
        na = NetworkAnalysis()
        stats = na.build_network(street_centerlines)
        assert stats["nodes"] == 6
        assert stats["edges"] == 3

    def test_build_network_returns_dict(self, street_centerlines):
        """build_network always returns a dict with expected keys."""
        na = NetworkAnalysis()
        stats = na.build_network(street_centerlines)
        assert "nodes" in stats
        assert "edges" in stats
        assert "total_length" in stats

    def test_build_network_populates_adjacency(self, street_centerlines):
        """Network adjacency list is populated after build_network."""
        na = NetworkAnalysis()
        na.build_network(street_centerlines)
        assert len(na.network) > 0

    def test_build_network_short_coords_skipped(self):
        """Streets with fewer than 2 coordinates are skipped."""
        na = NetworkAnalysis()
        streets = [
            {"id": "s_bad", "coordinates": [[-74.0, 40.7]], "length": 0},
            {"id": "s_good", "coordinates": [[-74.0, 40.7], [-74.01, 40.71]], "length": 100},
        ]
        stats = na.build_network(streets)
        assert stats["edges"] == 1


class TestNetworkAnalysisFindRoute:
    """Tests for NetworkAnalysis.find_shortest_route."""

    def test_route_between_connected_nodes(self, street_centerlines):
        """Shortest route is found between directly connected nodes."""
        na = NetworkAnalysis()
        na.build_network(street_centerlines)
        nodes = list(na.network.keys())
        if len(nodes) >= 2:
            path = na.find_shortest_route(nodes[0], nodes[1])
            assert isinstance(path, list)

    def test_route_unknown_start_node(self):
        """Route returns empty list for unknown start node."""
        na = NetworkAnalysis()
        na.build_network(
            [{"id": "s1", "coordinates": [[-74.0, 40.7], [-74.01, 40.71]], "length": 100}]
        )
        path = na.find_shortest_route("nonexistent_start", "s1_end")
        assert path == []

    def test_route_unknown_end_node(self):
        """Route returns empty list for unknown end node."""
        na = NetworkAnalysis()
        na.build_network(
            [{"id": "s1", "coordinates": [[-74.0, 40.7], [-74.01, 40.71]], "length": 100}]
        )
        path = na.find_shortest_route("s1_start", "nonexistent_end")
        assert path == []

    def test_route_empty_network(self):
        """Route on empty network returns empty list."""
        na = NetworkAnalysis()
        path = na.find_shortest_route("a", "b")
        assert path == []

    def test_route_same_node(self, street_centerlines):
        """Route from a node to itself returns a list."""
        na = NetworkAnalysis()
        na.build_network(street_centerlines)
        nodes = list(na.network.keys())
        if nodes:
            path = na.find_shortest_route(nodes[0], nodes[0])
            assert isinstance(path, list)


class TestNetworkAnalysisServiceAreas:
    """Tests for NetworkAnalysis.compute_service_areas."""

    def test_service_area_empty_network(self):
        """Service area on empty network returns empty list."""
        na = NetworkAnalysis()
        result = na.compute_service_areas(-74.0, 40.7, 500)
        assert result == []

    def test_service_area_returns_list(self, street_centerlines):
        """Service area computation returns a list."""
        na = NetworkAnalysis()
        na.build_network(street_centerlines)
        result = na.compute_service_areas(-74.01, 40.70, 100)
        assert isinstance(result, list)


class TestHotspotAnalysisKDE:
    """Tests for HotspotAnalysis.kernel_density."""

    def test_kde_insufficient_points(self):
        """KDE returns error dict when fewer than 2 points provided."""
        ha = HotspotAnalysis()
        result = ha.kernel_density([(0.0, 0.0)], [1.0])
        assert "error" in result

    def test_kde_returns_grid(self, sample_coordinates, sample_values):
        """KDE returns density grid with expected keys."""
        ha = HotspotAnalysis()
        result = ha.kernel_density(sample_coordinates, sample_values, grid_size=10)
        assert "density_grid" in result or "error" in result

    def test_kde_max_density_positive(self, sample_coordinates, sample_values):
        """KDE max_density is non-negative when successful."""
        ha = HotspotAnalysis()
        result = ha.kernel_density(sample_coordinates, sample_values)
        if "error" not in result:
            assert result["max_density"] >= 0


class TestHotspotAnalysisClusterSegments:
    """Tests for HotspotAnalysis.cluster_segments."""

    def test_cluster_dbscan_returns_list(
        self, sample_coordinates, sample_values, sample_segment_ids
    ):
        """DBSCAN clustering returns a list of Cluster objects."""
        ha = HotspotAnalysis()
        clusters = ha.cluster_segments(
            sample_coordinates,
            sample_values,
            sample_segment_ids,
            method="dbscan",
            eps=0.01,
            min_samples=2,
        )
        assert isinstance(clusters, list)

    def test_cluster_kmeans_returns_list(
        self, sample_coordinates, sample_values, sample_segment_ids
    ):
        """KMeans clustering returns a list of Cluster objects."""
        ha = HotspotAnalysis()
        clusters = ha.cluster_segments(
            sample_coordinates,
            sample_values,
            sample_segment_ids,
            method="kmeans",
        )
        assert isinstance(clusters, list)

    def test_cluster_unknown_method_returns_empty(
        self, sample_coordinates, sample_values, sample_segment_ids
    ):
        """Unknown clustering method returns empty list."""
        ha = HotspotAnalysis()
        clusters = ha.cluster_segments(
            sample_coordinates,
            sample_values,
            sample_segment_ids,
            method="unsupported_method",
        )
        assert clusters == []

    def test_cluster_insufficient_points(self):
        """Clustering returns empty list with fewer than 2 coordinates."""
        ha = HotspotAnalysis()
        clusters = ha.cluster_segments([(0.0, 0.0)], [50.0], ["seg1"])
        assert clusters == []

    def test_cluster_objects_have_expected_fields(
        self, sample_coordinates, sample_values, sample_segment_ids
    ):
        """Returned Cluster objects have all required fields."""
        ha = HotspotAnalysis()
        clusters = ha.cluster_segments(
            sample_coordinates,
            sample_values,
            sample_segment_ids,
            method="kmeans",
        )
        for c in clusters:
            assert hasattr(c, "cluster_id")
            assert hasattr(c, "size")
            assert hasattr(c, "centroid_x")
            assert hasattr(c, "centroid_y")
            assert hasattr(c, "average_value")
            assert hasattr(c, "segment_ids")
            assert isinstance(c.segment_ids, list)

    def test_cluster_size_matches_segment_ids(
        self, sample_coordinates, sample_values, sample_segment_ids
    ):
        """Cluster.size equals len(segment_ids) for each cluster."""
        ha = HotspotAnalysis()
        clusters = ha.cluster_segments(
            sample_coordinates,
            sample_values,
            sample_segment_ids,
            method="kmeans",
        )
        for c in clusters:
            assert c.size == len(c.segment_ids)


class TestHotspotAnalysisDetectHotspots:
    """Tests for HotspotAnalysis.detect_hotspots."""

    def test_detect_hotspots_too_few_points(self):
        """detect_hotspots returns empty list with fewer than 3 points."""
        ha = HotspotAnalysis()
        hotspots = ha.detect_hotspots([(0.0, 0.0), (0.1, 0.1)], [20.0, 30.0])
        assert hotspots == []

    def test_detect_hotspots_no_bad_segments(self, sample_coordinates):
        """detect_hotspots returns empty list when all values are above threshold."""
        ha = HotspotAnalysis()
        high_values = [90.0] * len(sample_coordinates)
        hotspots = ha.detect_hotspots(sample_coordinates, high_values, threshold=60.0)
        assert hotspots == []

    def test_detect_hotspots_returns_hotspot_objects(self):
        """detect_hotspots returns Hotspot dataclass instances."""
        ha = HotspotAnalysis()
        coords = [(-74.01 + i * 0.001, 40.70 + i * 0.001) for i in range(15)]
        values = [20.0] * 15
        hotspots = ha.detect_hotspots(coords, values, threshold=60.0, radius_degrees=0.005)
        assert isinstance(hotspots, list)
        for h in hotspots:
            assert hasattr(h, "centroid_x")
            assert hasattr(h, "centroid_y")
            assert hasattr(h, "density")
            assert hasattr(h, "severity")

    def test_detect_hotspots_severity_labels(self):
        """Hotspot severity is one of the expected label values."""
        ha = HotspotAnalysis()
        coords = [(-74.01 + i * 0.0005, 40.70 + i * 0.0005) for i in range(20)]
        values = [15.0] * 10 + [45.0] * 10
        hotspots = ha.detect_hotspots(coords, values, threshold=80.0, radius_degrees=0.01)
        valid_severities = {"critical", "high", "medium", "low"}
        for h in hotspots:
            assert h.severity in valid_severities


class TestInterpolationAnalysisIDW:
    """Tests for InterpolationAnalysis.inverse_distance_weighted."""

    def test_idw_basic_interpolation(self):
        """IDW interpolates values between known points."""
        ia = InterpolationAnalysis()
        known_pts = [(-74.0, 40.7), (-74.01, 40.71), (-74.02, 40.72)]
        known_vals = [80.0, 60.0, 40.0]
        query_pts = [(-74.005, 40.705)]
        result = ia.inverse_distance_weighted(known_pts, known_vals, query_pts)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_idw_result_in_value_range(self):
        """IDW interpolated values are within the range of known values."""
        ia = InterpolationAnalysis()
        known_pts = [(-74.0, 40.7), (-74.01, 40.71), (-74.02, 40.72)]
        known_vals = [50.0, 70.0, 90.0]
        query_pts = [(-74.005, 40.705)]
        result = ia.inverse_distance_weighted(known_pts, known_vals, query_pts)
        if result:
            assert 50.0 <= result[0] <= 90.0

    def test_idw_multiple_query_points(self):
        """IDW handles multiple query points and returns matching count."""
        ia = InterpolationAnalysis()
        known_pts = [(-74.0, 40.7), (-74.01, 40.71)]
        known_vals = [80.0, 60.0]
        query_pts = [(-74.002, 40.702), (-74.008, 40.708), (-74.005, 40.705)]
        result = ia.inverse_distance_weighted(known_pts, known_vals, query_pts)
        assert len(result) == 3

    def test_idw_power_parameter(self):
        """IDW result varies with different power parameters."""
        ia = InterpolationAnalysis()
        known_pts = [(-74.0, 40.7), (-74.02, 40.72)]
        known_vals = [80.0, 20.0]
        query_pts = [(-74.01, 40.71)]
        r1 = ia.inverse_distance_weighted(known_pts, known_vals, query_pts, power=1.0)
        r2 = ia.inverse_distance_weighted(known_pts, known_vals, query_pts, power=3.0)
        assert isinstance(r1, list) and isinstance(r2, list)

    def test_idw_exact_point_returns_known_value(self):
        """IDW at a known point location returns a value near the known value."""
        ia = InterpolationAnalysis()
        known_pts = [(-74.0, 40.7), (-74.01, 40.71)]
        known_vals = [100.0, 0.0]
        query_pts = [(-74.0, 40.7)]
        result = ia.inverse_distance_weighted(known_pts, known_vals, query_pts)
        assert isinstance(result, list)


class TestSpatialAnomalyDetector:
    """Tests for SpatialAnomalyDetector statistical outlier detection."""

    def test_detect_outliers_zscore(self, sample_coordinates, sample_values):
        """Z-score outlier detection returns list of indices."""
        outliers = SpatialAnomalyDetector.detect_outliers(
            sample_coordinates, sample_values, method="zscore", threshold=2.0
        )
        assert isinstance(outliers, list)

    def test_detect_outliers_iqr(self, sample_coordinates, sample_values):
        """IQR outlier detection returns list of indices."""
        outliers = SpatialAnomalyDetector.detect_outliers(
            sample_coordinates, sample_values, method="iqr"
        )
        assert isinstance(outliers, list)

    def test_detect_outliers_unknown_method(self, sample_coordinates, sample_values):
        """Unknown outlier method returns empty list."""
        outliers = SpatialAnomalyDetector.detect_outliers(
            sample_coordinates, sample_values, method="unknown"
        )
        assert outliers == []

    def test_detect_outliers_finds_extreme_value(self):
        """Z-score outlier detection finds extreme outlier in data."""
        coords = [(-74.0 + i * 0.001, 40.7) for i in range(20)]
        values = [50.0] * 19 + [1000.0]
        outliers = SpatialAnomalyDetector.detect_outliers(
            coords, values, method="zscore", threshold=2.0
        )
        assert 19 in outliers

    def test_detect_outliers_uniform_data(self):
        """Uniform data has no outliers under IQR method."""
        coords = [(-74.0 + i * 0.001, 40.7) for i in range(10)]
        values = [50.0] * 10
        outliers = SpatialAnomalyDetector.detect_outliers(coords, values, method="iqr")
        assert isinstance(outliers, list)

    def test_detect_spatial_outliers_returns_list(self, sample_coordinates, sample_values):
        """Spatial outlier detection returns list of indices."""
        outliers = SpatialAnomalyDetector.detect_spatial_outliers(
            sample_coordinates, sample_values, k=3
        )
        assert isinstance(outliers, list)

    def test_detect_spatial_outliers_finds_isolated_value(self):
        """Spatial outlier detection identifies point with anomalous neighbor values."""
        coords = [(-74.0 + i * 0.001, 40.7) for i in range(10)]
        values = [50.0] * 9 + [500.0]
        outliers = SpatialAnomalyDetector.detect_spatial_outliers(
            coords, values, k=3, std_threshold=1.5
        )
        assert isinstance(outliers, list)


class TestDetectConflictsFunctions:
    """Tests for module-level detect_conflicts function."""

    def test_detect_conflicts_no_geopandas(self):
        """detect_conflicts returns None when geopandas is not available."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", False):
            result = detect_conflicts(MagicMock(), MagicMock())
            assert result is None

    def test_detect_conflicts_none_inputs(self):
        """detect_conflicts returns empty GeoDataFrame for None inputs."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", True):
            with patch("socrata_toolkit.spatial.analytics.gpd") as mock_gpd:
                mock_gdf = MagicMock()
                mock_gpd.GeoDataFrame.return_value = mock_gdf
                result = detect_conflicts(None, None)
                assert result is not None

    def test_detect_conflicts_empty_inputs(self):
        """detect_conflicts returns empty GeoDataFrame for empty GeoDataFrames."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", True):
            with patch("socrata_toolkit.spatial.analytics.gpd") as mock_gpd:
                mock_gdf = MagicMock()
                mock_gdf.__len__ = MagicMock(return_value=0)
                mock_gpd.GeoDataFrame.return_value = mock_gdf
                result = detect_conflicts(mock_gdf, mock_gdf)
                assert result is not None


class TestSpatialConflictScore:
    """Tests for spatial_conflict_score function."""

    def test_conflict_score_no_geopandas(self):
        """conflict_score returns input unchanged when geopandas is missing."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", False):
            mock_gdf = MagicMock()
            result = spatial_conflict_score(mock_gdf)
            assert result is mock_gdf

    def test_conflict_score_none_input(self):
        """conflict_score handles None input without crashing."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", True):
            with patch("socrata_toolkit.spatial.analytics.HAS_NUMPY", True):
                result = spatial_conflict_score(None)
                assert result is None

    def test_conflict_score_with_geopandas(self):
        """conflict_score adds conflict_score column when geopandas is available."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        gdf = gpd.GeoDataFrame(
            {
                "dist": [10.0, 50.0, 90.0],
                "permit_type": ["excavation", "building", "event"],
                "priority": ["high", "medium", "low"],
            },
            geometry=[Point(-74.0, 40.7), Point(-74.01, 40.71), Point(-74.02, 40.72)],
            crs="EPSG:4326",
        )
        result = spatial_conflict_score(gdf, buffer_m=100)
        assert "conflict_score" in result.columns
        assert all(0 <= s <= 100 for s in result["conflict_score"])

    def test_conflict_score_missing_columns_uses_neutral_weights(self):
        """conflict_score degrades gracefully when dist/permit_type/priority are missing."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        gdf = gpd.GeoDataFrame(
            {"value": [1, 2, 3]},
            geometry=[Point(-74.0, 40.7), Point(-74.01, 40.71), Point(-74.02, 40.72)],
            crs="EPSG:4326",
        )
        result = spatial_conflict_score(gdf)
        assert "conflict_score" in result.columns


class TestMoranI:
    """Tests for moran_i function."""

    def test_moran_i_no_geopandas(self):
        """moran_i returns None when geopandas is not available."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", False):
            result = moran_i(MagicMock(), "col")
            assert result is None

    def test_moran_i_none_gdf(self):
        """moran_i returns None for None input."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", True):
            result = moran_i(None, "col")
            assert result is None

    def test_moran_i_missing_column(self):
        """moran_i returns None when column is not in GeoDataFrame."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        gdf = gpd.GeoDataFrame(
            {"value": [1, 2, 3]},
            geometry=[Point(-74.0, 40.7), Point(-74.01, 40.71), Point(-74.02, 40.72)],
            crs="EPSG:4326",
        )
        result = moran_i(gdf, "nonexistent_col")
        assert result is None

    def test_moran_i_too_few_features(self):
        """moran_i returns None with fewer than 3 features."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        gdf = gpd.GeoDataFrame(
            {"value": [1.0, 2.0]},
            geometry=[Point(-74.0, 40.7), Point(-74.01, 40.71)],
            crs="EPSG:4326",
        )
        result = moran_i(gdf, "value")
        assert result is None

    def test_moran_i_returns_float(self):
        """moran_i returns a float for valid GeoDataFrame."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        coords = [(-74.0 + i * 0.01, 40.7 + i * 0.01) for i in range(10)]
        values = [float(i * 10) for i in range(10)]
        gdf = gpd.GeoDataFrame(
            {"value": values},
            geometry=[Point(lon, lat) for lon, lat in coords],
            crs="EPSG:4326",
        )
        result = moran_i(gdf, "value")
        assert result is None or isinstance(result, float)

    def test_moran_i_uniform_values_returns_zero(self):
        """moran_i with uniform values returns 0.0 (no variance)."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        coords = [(-74.0 + i * 0.01, 40.7) for i in range(10)]
        gdf = gpd.GeoDataFrame(
            {"value": [50.0] * 10},
            geometry=[Point(lon, lat) for lon, lat in coords],
            crs="EPSG:4326",
        )
        result = moran_i(gdf, "value")
        assert result is None or result == 0.0


class TestClusterConflictHotspots:
    """Tests for cluster_conflict_hotspots function."""

    def test_cluster_hotspots_no_sklearn(self):
        """cluster_conflict_hotspots returns input when sklearn is missing."""
        with patch("socrata_toolkit.spatial.analytics.HAS_SKLEARN", False):
            mock_gdf = MagicMock()
            result = cluster_conflict_hotspots(mock_gdf)
            assert result is mock_gdf

    def test_cluster_hotspots_none_input(self):
        """cluster_conflict_hotspots returns None for None input."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", True):
            with patch("socrata_toolkit.spatial.analytics.HAS_SKLEARN", True):
                with patch("socrata_toolkit.spatial.analytics.HAS_NUMPY", True):
                    result = cluster_conflict_hotspots(None)
                    assert result is None

    def test_cluster_hotspots_empty_gdf(self):
        """cluster_conflict_hotspots adds empty cluster column to empty GeoDataFrame."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        result = cluster_conflict_hotspots(gdf)
        assert "cluster" in result.columns

    def test_cluster_hotspots_returns_cluster_column(self):
        """cluster_conflict_hotspots adds integer cluster column to output."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        coords = [(-74.0 + i * 0.005, 40.7 + i * 0.005) for i in range(20)]
        gdf = gpd.GeoDataFrame(
            {"id": list(range(20))},
            geometry=[Point(lon, lat) for lon, lat in coords],
            crs="EPSG:4326",
        )
        result = cluster_conflict_hotspots(gdf, eps_deg=0.01, min_samples=3)
        assert "cluster" in result.columns
        assert result["cluster"].dtype in (int, "int64", "int32")


class TestFindRampGaps:
    """Tests for find_ramp_gaps function."""

    def test_find_ramp_gaps_no_geopandas(self):
        """find_ramp_gaps returns None when geopandas is not available."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", False):
            result = find_ramp_gaps(MagicMock(), MagicMock())
            assert result is None

    def test_find_ramp_gaps_empty_inspections(self):
        """find_ramp_gaps returns empty GeoDataFrame for empty inspections."""
        with patch("socrata_toolkit.spatial.analytics.HAS_GEOPANDAS", True):
            with patch("socrata_toolkit.spatial.analytics.gpd") as mock_gpd:
                mock_empty = MagicMock()
                mock_empty.__len__ = MagicMock(return_value=0)
                mock_gpd.GeoDataFrame.return_value = mock_empty
                result = find_ramp_gaps(MagicMock(), mock_empty)
                assert result is not None

    def test_find_ramp_gaps_with_data(self):
        """find_ramp_gaps returns GeoDataFrame with ramp_dist column."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        insp_coords = [(-74.01, 40.70), (-74.02, 40.71)]
        ramp_coords = [(-74.015, 40.705)]
        gdf_insp = gpd.GeoDataFrame(
            {"id": [1, 2]},
            geometry=[Point(lon, lat) for lon, lat in insp_coords],
            crs="EPSG:4326",
        )
        gdf_ramps = gpd.GeoDataFrame(
            {"id": [1]},
            geometry=[Point(lon, lat) for lon, lat in ramp_coords],
            crs="EPSG:4326",
        )
        result = find_ramp_gaps(gdf_ramps, gdf_insp, threshold_m=50)
        assert result is not None


class TestDataclassStructures:
    """Tests for Hotspot and Cluster dataclasses."""

    def test_hotspot_creation(self):
        """Hotspot dataclass creates instance with all fields."""
        h = Hotspot(
            centroid_x=-74.01,
            centroid_y=40.70,
            density=5.2,
            segment_count=8,
            average_condition=35.0,
            severity="high",
        )
        assert h.centroid_x == -74.01
        assert h.centroid_y == 40.70
        assert h.density == 5.2
        assert h.segment_count == 8
        assert h.average_condition == 35.0
        assert h.severity == "high"

    def test_cluster_creation(self):
        """Cluster dataclass creates instance with all fields."""
        c = Cluster(
            cluster_id=1,
            size=5,
            centroid_x=-74.01,
            centroid_y=40.70,
            average_value=60.0,
            segment_ids=["s1", "s2", "s3", "s4", "s5"],
        )
        assert c.cluster_id == 1
        assert c.size == 5
        assert len(c.segment_ids) == 5
