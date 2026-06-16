"""Comprehensive tests for spatial.geodataframe module."""
from __future__ import annotations
import pytest


import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from socrata_toolkit.spatial.geodataframe import (
    HAS_GEOPANDAS,
    _parse_geom_value,
    geodataframe_from_socrata,
    spatial_stats,
    to_geojson,
    to_wkt_column,
)

# ---------------------------------------------------------------------------
# Optional dep guards
# ---------------------------------------------------------------------------

geopandas_required = pytest.mark.skipif(
    not HAS_GEOPANDAS, reason="geopandas not installed"
)

# ---------------------------------------------------------------------------
# _parse_geom_value
# ---------------------------------------------------------------------------

class TestParseGeomValue:
    """Tests for the internal _parse_geom_value helper."""

    def test_returns_none_for_none(self):
        """_parse_geom_value returns None when given None."""
        assert _parse_geom_value(None) is None

    def test_returns_none_for_nan(self):
        """_parse_geom_value returns None for float NaN values."""
        import math
        assert _parse_geom_value(float("nan")) is None

    def test_returns_none_for_empty_string(self):
        """_parse_geom_value returns None for empty strings."""
        assert _parse_geom_value("") is None
        assert _parse_geom_value("   ") is None

    @geopandas_required
    def test_parses_wkt_point(self):
        """_parse_geom_value parses a WKT POINT string into a geometry."""
        geom = _parse_geom_value("POINT(-74.006 40.7128)")
        assert geom is not None
        assert geom.geom_type == "Point"

    @geopandas_required
    def test_parses_wkt_linestring(self):
        """_parse_geom_value parses a WKT LINESTRING into a geometry."""
        geom = _parse_geom_value("LINESTRING(-74.006 40.71, -74.007 40.72)")
        assert geom is not None
        assert geom.geom_type == "LineString"

    @geopandas_required
    def test_parses_wkt_polygon(self):
        """_parse_geom_value parses a WKT POLYGON string into a geometry."""
        wkt = "POLYGON((-74.006 40.71, -74.007 40.71, -74.007 40.72, -74.006 40.72, -74.006 40.71))"
        geom = _parse_geom_value(wkt)
        assert geom is not None
        assert geom.geom_type == "Polygon"

    @geopandas_required
    def test_parses_geojson_dict(self):
        """_parse_geom_value parses a GeoJSON dict into a geometry."""
        geojson = {"type": "Point", "coordinates": [-74.006, 40.7128]}
        geom = _parse_geom_value(geojson)
        assert geom is not None

    @geopandas_required
    def test_parses_json_encoded_geojson_string(self):
        """_parse_geom_value parses a JSON-string-encoded GeoJSON into a geometry."""
        geojson_str = json.dumps({"type": "Point", "coordinates": [-74.006, 40.7128]})
        geom = _parse_geom_value(geojson_str)
        assert geom is not None

    def test_returns_none_for_invalid_wkt(self):
        """_parse_geom_value returns None for an invalid WKT string."""
        if not HAS_GEOPANDAS:
            pytest.skip("geopandas not installed")
        geom = _parse_geom_value("POINT NOT VALID")
        assert geom is None

    def test_returns_none_for_unrecognized_string(self):
        """_parse_geom_value returns None for arbitrary non-geometry strings."""
        assert _parse_geom_value("hello world") is None

    def test_returns_none_for_dict_without_geometry_keys(self):
        """_parse_geom_value returns None for a dict missing 'type'/'coordinates'."""
        assert _parse_geom_value({"key": "value"}) is None

# ---------------------------------------------------------------------------
# geodataframe_from_socrata — without geopandas
# ---------------------------------------------------------------------------

class TestGeodataframeFromSocrataNoGeopandas:
    """Tests for geodataframe_from_socrata when geopandas is absent."""

    def test_raises_import_error_without_geopandas(self):
        """geodataframe_from_socrata raises ImportError when geopandas is absent."""
        with patch("socrata_toolkit.spatial.geodataframe.HAS_GEOPANDAS", False):
            df = pd.DataFrame({"the_geom": ["POINT(-74 40)"], "value": [1]})
            with pytest.raises(ImportError, match="geopandas"):
                geodataframe_from_socrata(df)

    def test_raises_key_error_when_column_missing(self):
        """geodataframe_from_socrata raises KeyError when geom_col is absent."""
        if not HAS_GEOPANDAS:
            pytest.skip("geopandas not installed")
        df = pd.DataFrame({"value": [1, 2]})
        with pytest.raises(KeyError, match="the_geom"):
            geodataframe_from_socrata(df, geom_col="the_geom")

# ---------------------------------------------------------------------------
# geodataframe_from_socrata — with geopandas
# ---------------------------------------------------------------------------

class TestGeodataframeFromSocrataWithGeopandas:
    """Tests for geodataframe_from_socrata when geopandas is available."""

    @geopandas_required
    def test_converts_wkt_points(self):
        """geodataframe_from_socrata converts WKT POINT rows to GeoDataFrame."""
        df = pd.DataFrame({
            "the_geom": [
                "POINT(-74.006 40.713)",
                "POINT(-73.989 40.757)",
            ],
            "name": ["A", "B"],
        })
        gdf = geodataframe_from_socrata(df)
        assert len(gdf) == 2
        assert gdf.crs.to_epsg() == 4326

    @geopandas_required
    def test_drops_null_geometry_by_default(self):
        """geodataframe_from_socrata drops rows with unparseable geometry."""
        df = pd.DataFrame({
            "the_geom": ["POINT(-74.006 40.713)", None, "invalid"],
            "value": [1, 2, 3],
        })
        gdf = geodataframe_from_socrata(df, drop_null_geom=True)
        assert len(gdf) == 1

    @geopandas_required
    def test_keeps_null_geometry_when_drop_false(self):
        """geodataframe_from_socrata retains null-geom rows when drop_null_geom=False."""
        df = pd.DataFrame({
            "the_geom": ["POINT(-74.006 40.713)", None],
            "value": [1, 2],
        })
        gdf = geodataframe_from_socrata(df, drop_null_geom=False)
        assert len(gdf) == 2

    @geopandas_required
    def test_custom_geom_col_name(self):
        """geodataframe_from_socrata works with a non-default geometry column name."""
        df = pd.DataFrame({
            "geom": ["POINT(-74.006 40.713)"],
            "id": [1],
        })
        gdf = geodataframe_from_socrata(df, geom_col="geom")
        assert len(gdf) == 1

    @geopandas_required
    def test_custom_crs(self):
        """geodataframe_from_socrata sets the specified CRS on the GeoDataFrame."""
        df = pd.DataFrame({"the_geom": ["POINT(-74.006 40.713)"]})
        gdf = geodataframe_from_socrata(df, crs="EPSG:4326")
        assert gdf.crs.to_epsg() == 4326

# ---------------------------------------------------------------------------
# to_geojson
# ---------------------------------------------------------------------------

class TestToGeojson:
    """Tests for the to_geojson helper."""

    def test_raises_import_error_without_geopandas(self):
        """to_geojson raises ImportError when geopandas is absent."""
        with patch("socrata_toolkit.spatial.geodataframe.HAS_GEOPANDAS", False):
            with pytest.raises(ImportError):
                to_geojson(MagicMock())

    @geopandas_required
    def test_returns_string(self):
        """to_geojson returns a GeoJSON string for a valid GeoDataFrame."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame({"val": [1]}, geometry=[Point(-74.006, 40.713)], crs="EPSG:4326")
        result = to_geojson(gdf)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["type"] == "FeatureCollection"

# ---------------------------------------------------------------------------
# to_wkt_column
# ---------------------------------------------------------------------------

class TestToWktColumn:
    """Tests for the to_wkt_column helper."""

    def test_raises_import_error_without_geopandas(self):
        """to_wkt_column raises ImportError when geopandas is absent."""
        with patch("socrata_toolkit.spatial.geodataframe.HAS_GEOPANDAS", False):
            with pytest.raises(ImportError):
                to_wkt_column(MagicMock())

    @geopandas_required
    def test_returns_series_of_wkt(self):
        """to_wkt_column returns a pandas Series of WKT strings."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {"val": [1, 2]},
            geometry=[Point(-74.006, 40.713), Point(-73.989, 40.757)],
            crs="EPSG:4326",
        )
        result = to_wkt_column(gdf)
        assert isinstance(result, pd.Series)
        assert all(isinstance(v, str) for v in result)
        assert result.iloc[0].startswith("POINT")

# ---------------------------------------------------------------------------
# spatial_stats
# ---------------------------------------------------------------------------

class TestSpatialStats:
    """Tests for the spatial_stats helper."""

    def test_raises_import_error_without_geopandas(self):
        """spatial_stats raises ImportError when geopandas is absent."""
        with patch("socrata_toolkit.spatial.geodataframe.HAS_GEOPANDAS", False):
            with pytest.raises(ImportError):
                spatial_stats(MagicMock())

    @geopandas_required
    def test_returns_dict_with_expected_keys(self):
        """spatial_stats returns dict with total_features, bounds, crs, geometry_types."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {"val": [1, 2]},
            geometry=[Point(-74.006, 40.713), Point(-73.989, 40.757)],
            crs="EPSG:4326",
        )
        result = spatial_stats(gdf)
        assert "total_features" in result
        assert "geometry_types" in result
        assert "bounds" in result
        assert "crs" in result

    @geopandas_required
    def test_total_features_count_correct(self):
        """spatial_stats.total_features equals the number of rows in the GeoDataFrame."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {"val": [1, 2, 3]},
            geometry=[Point(-74.006, 40.713), Point(-73.989, 40.757), Point(-74.01, 40.72)],
            crs="EPSG:4326",
        )
        result = spatial_stats(gdf)
        assert result["total_features"] == 3

    @geopandas_required
    def test_bounds_is_list_of_four(self):
        """spatial_stats.bounds is a list of four floats [minx, miny, maxx, maxy]."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {"val": [1]},
            geometry=[Point(-74.006, 40.713)],
            crs="EPSG:4326",
        )
        result = spatial_stats(gdf)
        assert len(result["bounds"]) == 4
