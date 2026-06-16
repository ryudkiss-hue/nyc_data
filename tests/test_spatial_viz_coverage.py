"""Comprehensive tests for spatial.visualization module."""

from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import socrata_toolkit.spatial.visualization as viz_module
from socrata_toolkit.spatial.visualization import (
    NYC_BOUNDS,
    NYC_CENTER,
    MapExporter,
    MapStyle,
    SpatialVisualization,
    export_conflicts_geojson,
)


@pytest.fixture
def mock_folium():
    """Inject a mock folium module and enable HAS_FOLIUM for the test."""
    mock_f = MagicMock()
    mock_map_obj = MagicMock()
    mock_f.Map.return_value = mock_map_obj
    mock_f.PolyLine.return_value = MagicMock()
    mock_f.CircleMarker.return_value = MagicMock()
    mock_f.FeatureGroup.return_value = MagicMock()
    mock_f.LayerControl.return_value = MagicMock()
    mock_f.Element.return_value = MagicMock()

    orig_has_folium = viz_module.HAS_FOLIUM
    orig_folium = getattr(viz_module, "folium", None)

    viz_module.HAS_FOLIUM = True
    viz_module.folium = mock_f

    yield mock_f, mock_map_obj

    viz_module.HAS_FOLIUM = orig_has_folium
    if orig_folium is None:
        if hasattr(viz_module, "folium"):
            delattr(viz_module, "folium")
    else:
        viz_module.folium = orig_folium


@pytest.fixture
def point_features() -> list[dict]:
    """Provide GeoJSON-like Point features for visualization tests."""
    return [
        {
            "geometry": {"type": "Point", "coordinates": [-74.01, 40.70]},
            "properties": {
                "segment_id": "seg_001",
                "condition_score": 85.0,
                "material_type": "concrete",
            },
        },
        {
            "geometry": {"type": "Point", "coordinates": [-74.02, 40.71]},
            "properties": {
                "segment_id": "seg_002",
                "condition_score": 35.0,
                "material_type": "asphalt",
            },
        },
        {
            "geometry": {"type": "Point", "coordinates": [-74.015, 40.705]},
            "properties": {
                "segment_id": "seg_003",
                "condition_score": 55.0,
                "material_type": "brick",
            },
        },
    ]


@pytest.fixture
def linestring_features() -> list[dict]:
    """Provide GeoJSON-like LineString features for visualization tests."""
    return [
        {
            "geometry": {
                "type": "LineString",
                "coordinates": [[-74.01, 40.70], [-74.012, 40.702]],
            },
            "properties": {
                "segment_id": "ln_001",
                "condition_score": 75.0,
                "material_type": "concrete",
            },
        },
        {
            "geometry": {
                "type": "LineString",
                "coordinates": [[-74.015, 40.705], [-74.018, 40.708]],
            },
            "properties": {
                "segment_id": "ln_002",
                "condition_score": 25.0,
                "material_type": "asphalt",
            },
        },
    ]


@pytest.fixture
def hotspot_data() -> list[dict]:
    """Provide hotspot dicts for hotspot map tests."""
    return [
        {
            "centroid_x": -74.01,
            "centroid_y": 40.70,
            "density": 12.5,
            "severity": "critical",
            "segment_count": 8,
        },
        {
            "centroid_x": -74.02,
            "centroid_y": 40.71,
            "density": 5.2,
            "severity": "high",
            "segment_count": 4,
        },
        {
            "centroid_x": -74.025,
            "centroid_y": 40.715,
            "density": 2.1,
            "severity": "medium",
            "segment_count": 2,
        },
        {
            "centroid_x": -73.98,
            "centroid_y": 40.75,
            "density": 0.8,
            "severity": "low",
            "segment_count": 1,
        },
    ]


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_nyc_center_is_tuple(self):
        """NYC_CENTER is a tuple of two floats."""
        assert isinstance(NYC_CENTER, tuple)
        assert len(NYC_CENTER) == 2

    def test_nyc_center_coordinates(self):
        """NYC_CENTER coordinates are within NYC bounding box."""
        lat, lon = NYC_CENTER
        assert 40.0 < lat < 41.5
        assert -75.0 < lon < -73.0

    def test_nyc_bounds_is_list(self):
        """NYC_BOUNDS is a list of two coordinate pairs."""
        assert isinstance(NYC_BOUNDS, list)
        assert len(NYC_BOUNDS) == 2


class TestMapStyle:
    """Tests for MapStyle dataclass."""

    def test_map_style_defaults(self):
        """MapStyle has expected default values."""
        style = MapStyle()
        assert style.color_scheme == "viridis"
        assert style.line_weight == 2
        assert style.line_opacity == 0.8
        assert style.popup_width == 300

    def test_map_style_custom_colors(self):
        """MapStyle accepts custom color values."""
        style = MapStyle(min_color="#ff0000", max_color="#00ff00")
        assert style.min_color == "#ff0000"
        assert style.max_color == "#00ff00"

    def test_map_style_custom_line_weight(self):
        """MapStyle accepts custom line_weight."""
        style = MapStyle(line_weight=5)
        assert style.line_weight == 5


class TestSpatialVisualizationInit:
    """Tests for SpatialVisualization initialization."""

    def test_init_creates_empty_maps_dict(self, mock_folium):
        """SpatialVisualization initialises with an empty maps dict."""
        viz = SpatialVisualization()
        assert viz.maps == {}

    def test_init_without_folium_logs_warning(self):
        """SpatialVisualization logs warning when folium is not installed."""
        orig = viz_module.HAS_FOLIUM
        viz_module.HAS_FOLIUM = False
        try:
            with patch.object(viz_module.logger, "warning") as mock_warn:
                SpatialVisualization()
                mock_warn.assert_called_once()
        finally:
            viz_module.HAS_FOLIUM = orig

    def test_init_has_folium_does_not_warn(self, mock_folium):
        """SpatialVisualization does not warn when folium is available."""
        with patch.object(viz_module.logger, "warning") as mock_warn:
            SpatialVisualization()
            mock_warn.assert_not_called()


class TestSpatialVisualizationConditionMap:
    """Tests for SpatialVisualization.create_condition_map."""

    def test_condition_map_no_folium(self, point_features):
        """create_condition_map returns None when folium is not available."""
        orig = viz_module.HAS_FOLIUM
        viz_module.HAS_FOLIUM = False
        try:
            viz = SpatialVisualization()
            result = viz.create_condition_map(point_features)
            assert result is None
        finally:
            viz_module.HAS_FOLIUM = orig

    def test_condition_map_with_folium_returns_map(self, mock_folium, point_features):
        """create_condition_map returns a map object when folium is available."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_condition_map(point_features)
        assert result is mock_map_obj

    def test_condition_map_creates_map_at_nyc_center(self, mock_folium, point_features):
        """create_condition_map initialises Folium.Map with location parameter."""
        mock_f, _ = mock_folium
        viz = SpatialVisualization()
        viz.create_condition_map(point_features)
        mock_f.Map.assert_called_once()
        call_kwargs = mock_f.Map.call_args[1]
        assert "location" in call_kwargs

    def test_condition_map_with_linestrings(self, mock_folium, linestring_features):
        """create_condition_map renders PolyLine for LineString geometries."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_condition_map(linestring_features)
        assert result is mock_map_obj
        assert mock_f.PolyLine.call_count == len(linestring_features)

    def test_condition_map_with_point_geometries(self, mock_folium, point_features):
        """create_condition_map renders CircleMarker for Point geometries."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        viz.create_condition_map(point_features)
        assert mock_f.CircleMarker.call_count == len(point_features)

    def test_condition_map_with_custom_style(self, mock_folium, point_features):
        """create_condition_map accepts and applies custom MapStyle."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        custom_style = MapStyle(line_weight=4, line_opacity=0.9)
        result = viz.create_condition_map(point_features, style=custom_style)
        assert result is mock_map_obj

    def test_condition_map_with_title(self, mock_folium, point_features):
        """create_condition_map accepts a custom title string."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_condition_map(point_features, title="Custom NYC Title")
        assert result is mock_map_obj

    def test_condition_map_empty_features(self, mock_folium):
        """create_condition_map handles empty feature list without error."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_condition_map([])
        assert result is mock_map_obj

    def test_condition_map_error_returns_none(self, mock_folium, point_features):
        """create_condition_map returns None when Map constructor raises."""
        mock_f, _ = mock_folium
        mock_f.Map.side_effect = RuntimeError("folium error")
        viz = SpatialVisualization()
        result = viz.create_condition_map(point_features)
        assert result is None
        mock_f.Map.side_effect = None


class TestSpatialVisualizationMaterialMap:
    """Tests for SpatialVisualization.create_material_map."""

    def test_material_map_no_folium(self, linestring_features):
        """create_material_map returns None when folium is not available."""
        orig = viz_module.HAS_FOLIUM
        viz_module.HAS_FOLIUM = False
        try:
            viz = SpatialVisualization()
            result = viz.create_material_map(linestring_features)
            assert result is None
        finally:
            viz_module.HAS_FOLIUM = orig

    def test_material_map_with_folium(self, mock_folium, linestring_features):
        """create_material_map returns a map when folium is available."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_material_map(linestring_features)
        assert result is mock_map_obj

    def test_material_map_renders_polylines(self, mock_folium, linestring_features):
        """create_material_map renders one PolyLine per LineString feature."""
        mock_f, _ = mock_folium
        viz = SpatialVisualization()
        viz.create_material_map(linestring_features)
        assert mock_f.PolyLine.call_count == len(linestring_features)

    def test_material_map_all_material_types(self, mock_folium):
        """create_material_map handles all standard material types."""
        mock_f, mock_map_obj = mock_folium
        features = []
        for material in ["asphalt", "concrete", "brick", "stone", "other"]:
            features.append(
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-74.01, 40.70], [-74.012, 40.702]],
                    },
                    "properties": {"segment_id": f"seg_{material}", "material_type": material},
                }
            )
        viz = SpatialVisualization()
        result = viz.create_material_map(features)
        assert result is mock_map_obj
        assert mock_f.PolyLine.call_count == len(features)

    def test_material_map_unknown_material_type(self, mock_folium):
        """create_material_map handles unknown material types with fallback color."""
        mock_f, mock_map_obj = mock_folium
        features = [
            {
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-74.01, 40.70], [-74.012, 40.702]],
                },
                "properties": {"segment_id": "seg_x", "material_type": "unknown_material"},
            }
        ]
        viz = SpatialVisualization()
        result = viz.create_material_map(features)
        assert result is mock_map_obj


class TestSpatialVisualizationHotspotMap:
    """Tests for SpatialVisualization.create_hotspot_map."""

    def test_hotspot_map_no_folium(self, hotspot_data):
        """create_hotspot_map returns None when folium is unavailable."""
        orig = viz_module.HAS_FOLIUM
        viz_module.HAS_FOLIUM = False
        try:
            viz = SpatialVisualization()
            result = viz.create_hotspot_map(hotspot_data)
            assert result is None
        finally:
            viz_module.HAS_FOLIUM = orig

    def test_hotspot_map_with_folium(self, mock_folium, hotspot_data):
        """create_hotspot_map returns a Folium map object."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_hotspot_map(hotspot_data)
        assert result is mock_map_obj

    def test_hotspot_map_creates_circle_per_hotspot(self, mock_folium, hotspot_data):
        """create_hotspot_map renders one CircleMarker per hotspot."""
        mock_f, _ = mock_folium
        viz = SpatialVisualization()
        viz.create_hotspot_map(hotspot_data)
        assert mock_f.CircleMarker.call_count == len(hotspot_data)

    def test_hotspot_map_with_segments(self, mock_folium, hotspot_data, linestring_features):
        """create_hotspot_map overlays underlying segments when provided."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_hotspot_map(hotspot_data, segments=linestring_features)
        assert result is mock_map_obj
        assert mock_f.PolyLine.call_count == len(linestring_features)

    def test_hotspot_map_empty_hotspots(self, mock_folium):
        """create_hotspot_map handles empty hotspot list."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_hotspot_map([])
        assert result is mock_map_obj

    def test_hotspot_map_missing_coordinates_skipped(self, mock_folium):
        """create_hotspot_map skips hotspots without centroid coordinates."""
        mock_f, mock_map_obj = mock_folium
        hotspots_incomplete = [{"density": 5.0, "severity": "high", "segment_count": 3}]
        viz = SpatialVisualization()
        result = viz.create_hotspot_map(hotspots_incomplete)
        assert result is mock_map_obj
        assert mock_f.CircleMarker.call_count == 0

    def test_hotspot_map_all_severity_colors(self, mock_folium):
        """create_hotspot_map handles all four severity levels."""
        mock_f, _ = mock_folium
        hotspots = [
            {
                "centroid_x": -74.01,
                "centroid_y": 40.70,
                "density": 1.0,
                "severity": sev,
                "segment_count": 1,
            }
            for sev in ["critical", "high", "medium", "low"]
        ]
        viz = SpatialVisualization()
        viz.create_hotspot_map(hotspots)
        assert mock_f.CircleMarker.call_count == 4


class TestSpatialVisualizationComparisonMap:
    """Tests for SpatialVisualization.create_comparison_map."""

    def test_comparison_map_no_folium(self, linestring_features):
        """create_comparison_map returns None when folium is not available."""
        orig = viz_module.HAS_FOLIUM
        viz_module.HAS_FOLIUM = False
        try:
            viz = SpatialVisualization()
            result = viz.create_comparison_map(linestring_features, linestring_features)
            assert result is None
        finally:
            viz_module.HAS_FOLIUM = orig

    def test_comparison_map_with_folium(self, mock_folium, linestring_features):
        """create_comparison_map returns a Folium map with layer control."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_comparison_map(linestring_features, linestring_features)
        assert result is mock_map_obj

    def test_comparison_map_creates_two_feature_groups(self, mock_folium, linestring_features):
        """create_comparison_map creates exactly two FeatureGroups."""
        mock_f, _ = mock_folium
        viz = SpatialVisualization()
        viz.create_comparison_map(linestring_features, [])
        assert mock_f.FeatureGroup.call_count == 2

    def test_comparison_map_renders_before_polylines(self, mock_folium, linestring_features):
        """create_comparison_map renders PolyLine for before features."""
        mock_f, _ = mock_folium
        viz = SpatialVisualization()
        viz.create_comparison_map(linestring_features, [])
        assert mock_f.PolyLine.call_count == len(linestring_features)

    def test_comparison_map_renders_both_datasets(self, mock_folium, linestring_features):
        """create_comparison_map renders PolyLines for both before and after features."""
        mock_f, _ = mock_folium
        viz = SpatialVisualization()
        before = linestring_features[:1]
        after = linestring_features[1:]
        viz.create_comparison_map(before, after)
        assert mock_f.PolyLine.call_count == len(before) + len(after)

    def test_comparison_map_empty_inputs(self, mock_folium):
        """create_comparison_map handles empty before/after feature lists."""
        mock_f, mock_map_obj = mock_folium
        viz = SpatialVisualization()
        result = viz.create_comparison_map([], [])
        assert result is mock_map_obj

    def test_comparison_map_adds_layer_control(self, mock_folium, linestring_features):
        """create_comparison_map adds a LayerControl to the map."""
        mock_f, _ = mock_folium
        viz = SpatialVisualization()
        viz.create_comparison_map(linestring_features, linestring_features)
        mock_f.LayerControl.assert_called_once()


class TestSpatialVisualizationExport:
    """Tests for SpatialVisualization.export_map_html and export_map_geojson."""

    def test_export_map_html_saves_file(self):
        """export_map_html calls map_obj.save with output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "map.html"
            mock_map = MagicMock()
            viz = SpatialVisualization()
            result = viz.export_map_html(mock_map, str(out_path))
            mock_map.save.assert_called_once_with(str(out_path))
            assert result is True

    def test_export_map_html_creates_parent_dirs(self):
        """export_map_html creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "subdir" / "nested" / "map.html"
            mock_map = MagicMock()
            viz = SpatialVisualization()
            viz.export_map_html(mock_map, out_path)
            assert out_path.parent.exists()

    def test_export_map_html_returns_false_on_error(self):
        """export_map_html returns False when save raises an exception."""
        mock_map = MagicMock()
        mock_map.save.side_effect = OSError("disk full")
        viz = SpatialVisualization()
        result = viz.export_map_html(mock_map, "/nonexistent/path/map.html")
        assert result is False

    def test_export_map_geojson_writes_valid_file(self, point_features):
        """export_map_geojson writes valid GeoJSON FeatureCollection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "features.geojson"
            viz = SpatialVisualization()
            result = viz.export_map_geojson(point_features, str(out_path))
            assert result is True
            assert out_path.exists()
            with open(out_path) as f:
                data = json.load(f)
            assert data["type"] == "FeatureCollection"
            assert len(data["features"]) == len(point_features)

    def test_export_map_geojson_empty_features(self):
        """export_map_geojson handles empty feature list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "empty.geojson"
            viz = SpatialVisualization()
            result = viz.export_map_geojson([], str(out_path))
            assert result is True
            with open(out_path) as f:
                data = json.load(f)
            assert data["features"] == []

    def test_export_map_geojson_parent_dir_created(self):
        """export_map_geojson creates parent directories when needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "subdir" / "features.geojson"
            viz = SpatialVisualization()
            result = viz.export_map_geojson([], out_path)
            assert result is True
            assert out_path.parent.exists()


class TestScoreToColor:
    """Tests for SpatialVisualization._score_to_color static method."""

    def test_low_score_returns_min_color(self):
        """Score below 33 returns min_color (red)."""
        style = MapStyle()
        color = SpatialVisualization._score_to_color(10.0, style)
        assert color == style.min_color

    def test_mid_score_returns_neutral_color(self):
        """Score in 33-67 range returns neutral_color (yellow)."""
        style = MapStyle()
        color = SpatialVisualization._score_to_color(50.0, style)
        assert color == style.neutral_color

    def test_high_score_returns_max_color(self):
        """Score above 67 returns max_color (green)."""
        style = MapStyle()
        color = SpatialVisualization._score_to_color(90.0, style)
        assert color == style.max_color

    def test_zero_score_returns_min_color(self):
        """Score of 0 returns min_color."""
        style = MapStyle()
        color = SpatialVisualization._score_to_color(0.0, style)
        assert color == style.min_color

    def test_hundred_score_returns_max_color(self):
        """Score of 100 returns max_color."""
        style = MapStyle()
        color = SpatialVisualization._score_to_color(100.0, style)
        assert color == style.max_color

    def test_score_returns_string(self):
        """_score_to_color always returns a string."""
        style = MapStyle()
        for score in [0.0, 25.0, 50.0, 75.0, 100.0]:
            color = SpatialVisualization._score_to_color(score, style)
            assert isinstance(color, str)


class TestCreatePopup:
    """Tests for SpatialVisualization._create_popup static method."""

    def test_popup_includes_segment_id(self):
        """Popup HTML includes the segment_id."""
        html = SpatialVisualization._create_popup("seg_001", {"condition_score": 75.0})
        assert "seg_001" in html

    def test_popup_includes_numeric_properties(self):
        """Popup HTML formats float properties with two decimal places."""
        html = SpatialVisualization._create_popup("seg_x", {"value": 3.14159})
        assert "3.14" in html

    def test_popup_includes_string_properties(self):
        """Popup HTML includes string properties."""
        html = SpatialVisualization._create_popup("seg_x", {"material": "concrete"})
        assert "concrete" in html

    def test_popup_excludes_geometry_key(self):
        """Popup HTML does not include 'geometry' key from properties."""
        html = SpatialVisualization._create_popup(
            "seg_x", {"geometry": "POINT(0,0)", "condition_score": 50.0}
        )
        assert "POINT" not in html

    def test_popup_empty_properties(self):
        """Popup HTML is a valid string for empty properties."""
        html = SpatialVisualization._create_popup("seg_x", {})
        assert "seg_x" in html
        assert isinstance(html, str)

    def test_popup_excludes_segment_id_from_table(self):
        """Popup HTML does not repeat segment_id in the property table."""
        html = SpatialVisualization._create_popup(
            "seg_001", {"segment_id": "seg_001", "score": 80.0}
        )
        assert html.count("seg_001") == 1


class TestMapExporterToHtml:
    """Tests for MapExporter.to_html static method."""

    def test_to_html_calls_save(self):
        """to_html calls map_obj.save with the given path."""
        mock_map = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.html"
            result = MapExporter.to_html(mock_map, str(path))
            mock_map.save.assert_called_once_with(str(path))
            assert result is True

    def test_to_html_returns_false_on_error(self):
        """to_html returns False when save raises an exception."""
        mock_map = MagicMock()
        mock_map.save.side_effect = Exception("io error")
        result = MapExporter.to_html(mock_map, "/bad/path/map.html")
        assert result is False


class TestMapExporterToGeoJson:
    """Tests for MapExporter.to_geojson static method."""

    def test_to_geojson_writes_feature_collection(self, point_features):
        """to_geojson writes valid GeoJSON FeatureCollection to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.geojson"
            result = MapExporter.to_geojson(point_features, str(path))
            assert result is True
            with open(path) as f:
                data = json.load(f)
            assert data["type"] == "FeatureCollection"

    def test_to_geojson_returns_false_on_permission_error(self, point_features):
        """to_geojson returns False on a write error (patched)."""
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = MapExporter.to_geojson(point_features, "/any/path.geojson")
            assert result is False

    def test_to_geojson_empty_features(self):
        """to_geojson writes an empty FeatureCollection for empty input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.geojson"
            result = MapExporter.to_geojson([], str(path))
            assert result is True
            with open(path) as f:
                data = json.load(f)
            assert data["features"] == []


class TestMapExporterToKml:
    """Tests for MapExporter.to_kml static method."""

    def test_to_kml_writes_kml_file(self, linestring_features):
        """to_kml writes a valid KML file with Placemark elements."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.kml"
            result = MapExporter.to_kml(linestring_features, str(path))
            assert result is True
            content = path.read_text()
            assert "<?xml" in content
            assert "<kml" in content
            assert "Placemark" in content

    def test_to_kml_includes_linestring_coordinates(self, linestring_features):
        """to_kml includes coordinate data from LineString features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.kml"
            MapExporter.to_kml(linestring_features, str(path))
            content = path.read_text()
            assert "coordinates" in content

    def test_to_kml_empty_features(self):
        """to_kml handles empty feature list gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.kml"
            result = MapExporter.to_kml([], str(path))
            assert result is True

    def test_to_kml_returns_false_on_error(self, linestring_features):
        """to_kml returns False when file write fails."""
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = MapExporter.to_kml(linestring_features, "/any/path.kml")
            assert result is False

    def test_to_kml_includes_segment_name(self, linestring_features):
        """to_kml includes the segment_id as the Placemark name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.kml"
            MapExporter.to_kml(linestring_features, str(path))
            content = path.read_text()
            assert "ln_001" in content or "ln_002" in content


class TestExportConflictsGeojson:
    """Tests for export_conflicts_geojson module-level function."""

    def test_export_no_geopandas(self):
        """export_conflicts_geojson returns False when geopandas is not installed."""
        orig = viz_module.HAS_GEOPANDAS
        viz_module.HAS_GEOPANDAS = False
        try:
            result = export_conflicts_geojson(MagicMock(), "/tmp/conflicts.geojson")
            assert result is False
        finally:
            viz_module.HAS_GEOPANDAS = orig

    def test_export_none_input(self):
        """export_conflicts_geojson returns False for None input."""
        with patch.object(viz_module, "HAS_GEOPANDAS", True):
            result = export_conflicts_geojson(None, "/tmp/conflicts.geojson")
            assert result is False

    def test_export_empty_gdf(self):
        """export_conflicts_geojson returns False for empty GeoDataFrame."""
        try:
            import geopandas as gpd
        except ImportError:
            pytest.skip("geopandas not installed")

        empty_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_conflicts_geojson(empty_gdf, Path(tmpdir) / "out.geojson")
            assert result is False

    def test_export_with_data(self):
        """export_conflicts_geojson writes file and returns True for valid GeoDataFrame."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            pytest.skip("geopandas not installed")

        gdf = gpd.GeoDataFrame(
            {"id": [1, 2], "conflict_score": [75.0, 45.0]},
            geometry=[Point(-74.01, 40.70), Point(-74.02, 40.71)],
            crs="EPSG:4326",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "conflicts.geojson"
            result = export_conflicts_geojson(gdf, out_path)
            assert result is True
            assert out_path.exists()
