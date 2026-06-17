"""Tests for spatial conflict detection functions.

Requires geopandas + shapely; entire file is skipped when they are absent.
"""

from __future__ import annotations

import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")

from shapely.geometry import Point  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_inspection_df(lons, lats, **extra_cols):
    """Create a plain DataFrame with WKT the_geom column (as expected by detect_conflicts_geopandas)."""
    geom_wkt = [f"POINT ({lon} {lat})" for lon, lat in zip(lons, lats)]
    data = {"the_geom": geom_wkt}
    data.update(extra_cols)
    return pd.DataFrame(data)

@pytest.fixture()
def overlapping_gdf():
    """Two DataFrames with WKT the_geom whose buffered areas overlap."""
    inspections = _make_inspection_df(
        lons=[-73.9857, -73.9772],
        lats=[40.7484, 40.6892],
        inspection_id=["INS-001", "INS-002"],
        borough=["MANHATTAN", "BROOKLYN"],
    )
    # Permits placed at essentially the same locations → guaranteed overlap
    permits = _make_inspection_df(
        lons=[-73.9857, -73.9772],
        lats=[40.7484, 40.6892],
        permit_id=["PRM-001", "PRM-002"],
    )
    return inspections, permits

@pytest.fixture()
def non_overlapping_gdf():
    """Two DataFrames with WKT the_geom with points far apart — no overlap."""
    inspections = _make_inspection_df(
        lons=[-73.9857],
        lats=[40.7484],
        inspection_id=["INS-100"],
    )
    permits = _make_inspection_df(
        lons=[-74.5000],
        lats=[41.5000],
        permit_id=["PRM-100"],
    )
    return inspections, permits

@pytest.fixture()
def spatial_point_gdf():
    """A GeoDataFrame with enough points for spatial statistics."""
    import numpy as np

    rng = np.random.default_rng(7)
    lats = rng.normal(40.71, 0.05, 20)
    lons = rng.normal(-73.98, 0.05, 20)
    # Assign simple numeric attribute for Moran's I style test
    values = rng.normal(75, 10, 20)
    gdf = gpd.GeoDataFrame(
        {"value": values, "borough": ["MANHATTAN"] * 20},
        crs="EPSG:4326",
        geometry=[Point(lon, lat) for lon, lat in zip(lons, lats)],
    )
    return gdf

# ---------------------------------------------------------------------------
# detect_conflicts tests
# ---------------------------------------------------------------------------

class TestDetectConflictsBasic:
    def test_detect_conflicts_returns_geodataframe(self, overlapping_gdf):
        from socrata_toolkit.spatial.geodataframe import detect_conflicts_geopandas

        inspections, permits = overlapping_gdf
        conflicts = detect_conflicts_geopandas(inspections, permits, buffer_meters=100.0)
        assert isinstance(conflicts, gpd.GeoDataFrame)

    def test_detect_conflicts_overlapping_returns_at_least_one(self, overlapping_gdf):
        from socrata_toolkit.spatial.geodataframe import detect_conflicts_geopandas

        inspections, permits = overlapping_gdf
        conflicts = detect_conflicts_geopandas(inspections, permits, buffer_meters=100.0)
        assert len(conflicts) >= 1, "Expected at least one conflict for overlapping geometries"

    def test_detect_conflicts_no_overlap(self, non_overlapping_gdf):
        from socrata_toolkit.spatial.geodataframe import detect_conflicts_geopandas

        inspections, permits = non_overlapping_gdf
        # Very small buffer (1 meter) — points are ~60 km apart, no overlap expected
        conflicts = detect_conflicts_geopandas(inspections, permits, buffer_meters=1.0)
        assert len(conflicts) == 0, "Expected zero conflicts for non-overlapping geometries"

# ---------------------------------------------------------------------------
# Moran's I range test (using a lightweight numpy implementation)
# ---------------------------------------------------------------------------

class TestMoranIRange:
    def _simple_moran_i(self, values, coords) -> float:
        """Simple Global Moran's I using inverse-distance weights."""
        import numpy as np

        n = len(values)
        v = np.array(values)
        v_mean = v.mean()
        v_dev = v - v_mean

        # Build weight matrix (inverse distance, zero diagonal)
        W = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    d = np.sqrt((coords[i][0] - coords[j][0]) ** 2 + (coords[i][1] - coords[j][1]) ** 2)
                    W[i, j] = 1.0 / max(d, 1e-10)

        # Row-standardize
        row_sums = W.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1, row_sums)
        W = W / row_sums

        numerator = (v_dev @ W @ v_dev)
        denominator = (v_dev @ v_dev)
        if denominator == 0:
            return 0.0
        return float(n / W.sum() * numerator / denominator)

    def test_moran_i_range(self, spatial_point_gdf):
        """Moran's I must fall within [-1, 1]."""
        coords = [(geom.x, geom.y) for geom in spatial_point_gdf.geometry]
        values = spatial_point_gdf["value"].tolist()
        i_stat = self._simple_moran_i(values, coords)
        assert -1.0 <= i_stat <= 1.0, f"Moran's I={i_stat} outside [-1, 1]"

# ---------------------------------------------------------------------------
# Cluster conflict hotspots
# ---------------------------------------------------------------------------

class TestClusterConflictHotspots:
    def test_cluster_hotspots_returns_cluster_id_column(self, spatial_point_gdf):
        """After clustering, GeoDataFrame should have a cluster_id column."""
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            pytest.skip("scikit-learn not installed")

        import numpy as np

        gdf = spatial_point_gdf.copy()
        coords = np.array([[geom.x, geom.y] for geom in gdf.geometry])
        km = KMeans(n_clusters=3, random_state=42, n_init=10)
        gdf = gdf.copy()
        gdf["cluster_id"] = km.fit_predict(coords)

        assert "cluster_id" in gdf.columns
        assert gdf["cluster_id"].nunique() >= 2

    def test_cluster_hotspots_is_geodataframe(self, spatial_point_gdf):
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            pytest.skip("scikit-learn not installed")

        import numpy as np

        gdf = spatial_point_gdf.copy()
        coords = np.array([[geom.x, geom.y] for geom in gdf.geometry])
        km = KMeans(n_clusters=3, random_state=42, n_init=10)
        gdf = gdf.copy()
        gdf["cluster_id"] = km.fit_predict(coords)

        assert isinstance(gdf, gpd.GeoDataFrame)

    def test_cluster_hotspot_analysis_from_module(self):
        """Cluster via the HotspotAnalysis class in spatial/analytics.py."""
        from socrata_toolkit.spatial.analytics import HotspotAnalysis

        analysis = HotspotAnalysis()
        coords = [(-74.0 + i * 0.001, 40.7 + i * 0.001) for i in range(20)]
        values = [80.0 - i for i in range(20)]
        ids = [f"seg_{i}" for i in range(20)]
        clusters = analysis.cluster_segments(coords, values, ids, method="kmeans")
        assert isinstance(clusters, list)
        assert len(clusters) >= 1
