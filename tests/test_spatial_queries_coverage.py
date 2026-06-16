"""Comprehensive tests for spatial.queries module."""
from __future__ import annotations
import pytest


from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Optional dep guard
# ---------------------------------------------------------------------------

try:
    from shapely.geometry import Point, Polygon
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

shapely_required = pytest.mark.skipif(not HAS_SHAPELY, reason="shapely not installed")

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from socrata_toolkit.spatial.queries import (
    ProximityResult,
    SpatialAggregation,
    SpatialQuery,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db() -> MagicMock:
    """Return a mock SpatialDatabaseConnection with a working get_connection."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    cursor.fetchall.return_value = []
    conn.cursor.return_value = cursor

    db = MagicMock()

    @contextmanager
    def _get_connection():
        yield conn

    db.get_connection = _get_connection
    return db

@pytest.fixture
def nyc_point():
    """Return a Point at NYC center."""
    if not HAS_SHAPELY:
        pytest.skip("shapely not installed")
    return Point(-74.0060, 40.7128)

@pytest.fixture
def manhattan_polygon():
    """Return a simplified Manhattan bounding polygon."""
    if not HAS_SHAPELY:
        pytest.skip("shapely not installed")
    return Polygon([
        (-74.02, 40.70),
        (-73.97, 40.70),
        (-73.97, 40.78),
        (-74.02, 40.78),
        (-74.02, 40.70),
    ])

# ---------------------------------------------------------------------------
# ProximityResult dataclass
# ---------------------------------------------------------------------------

class TestProximityResult:
    """Tests for the ProximityResult dataclass."""

    def test_proximity_result_fields(self):
        """ProximityResult stores all fields correctly."""
        pr = ProximityResult(
            segment_id="seg-001",
            distance_meters=25.3,
            material_type="concrete",
            condition_score=80.0,
            borough="Manhattan",
        )
        assert pr.segment_id == "seg-001"
        assert pr.distance_meters == 25.3
        assert pr.material_type == "concrete"
        assert pr.condition_score == 80.0
        assert pr.borough == "Manhattan"

# ---------------------------------------------------------------------------
# SpatialAggregation dataclass
# ---------------------------------------------------------------------------

class TestSpatialAggregation:
    """Tests for the SpatialAggregation dataclass."""

    def test_spatial_aggregation_required_fields(self):
        """SpatialAggregation stores required fields correctly."""
        sa = SpatialAggregation(
            category="asphalt",
            total_length_meters=1500.0,
            segment_count=42,
            average_condition=65.0,
        )
        assert sa.category == "asphalt"
        assert sa.total_length_meters == 1500.0
        assert sa.segment_count == 42
        assert sa.average_condition == 65.0

    def test_spatial_aggregation_optional_fields_default_none(self):
        """SpatialAggregation optional fields (borough, district) default to None."""
        sa = SpatialAggregation(
            category="concrete",
            total_length_meters=1000.0,
            segment_count=20,
            average_condition=70.0,
        )
        assert sa.borough is None
        assert sa.district is None

    def test_spatial_aggregation_with_borough(self):
        """SpatialAggregation accepts an optional borough."""
        sa = SpatialAggregation(
            category="brick",
            total_length_meters=500.0,
            segment_count=10,
            average_condition=55.0,
            borough="Brooklyn",
        )
        assert sa.borough == "Brooklyn"

# ---------------------------------------------------------------------------
# SpatialQuery.find_nearby_segments
# ---------------------------------------------------------------------------

class TestFindNearbySegments:
    """Tests for SpatialQuery.find_nearby_segments."""

    @shapely_required
    def test_returns_empty_list_when_no_results(self, mock_db, nyc_point):
        """find_nearby_segments returns [] when cursor returns no rows."""
        query = SpatialQuery(mock_db)
        results = query.find_nearby_segments(nyc_point, 100)
        assert results == []

    @shapely_required
    def test_returns_proximity_results(self, mock_db, nyc_point):
        """find_nearby_segments maps DB rows to ProximityResult objects."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("seg-001", 42.5, "concrete", 75.0, "Manhattan"),
            ("seg-002", 90.1, "asphalt", 60.0, "Manhattan"),
        ]
        conn.cursor.return_value = cursor
        mock_db2 = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        mock_db2.get_connection = _get_connection
        mock_db2.srid = 4326

        query = SpatialQuery(mock_db2)
        results = query.find_nearby_segments(nyc_point, 100)
        assert len(results) == 2
        assert results[0].segment_id == "seg-001"
        assert results[0].distance_meters == 42.5

    @shapely_required
    def test_returns_empty_list_on_exception(self, mock_db, nyc_point):
        """find_nearby_segments returns [] on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("db error"))
        query = SpatialQuery(bad_db)
        results = query.find_nearby_segments(nyc_point, 100)
        assert results == []

    @shapely_required
    def test_with_material_type_filter(self, mock_db, nyc_point):
        """find_nearby_segments appends material filter without error."""
        query = SpatialQuery(mock_db)
        results = query.find_nearby_segments(nyc_point, 200, material_type="concrete")
        assert isinstance(results, list)

    @shapely_required
    def test_limit_parameter_passed(self, mock_db, nyc_point):
        """find_nearby_segments accepts a custom limit parameter."""
        query = SpatialQuery(mock_db)
        results = query.find_nearby_segments(nyc_point, 500, limit=5)
        assert isinstance(results, list)

# ---------------------------------------------------------------------------
# SpatialQuery.find_segments_in_polygon
# ---------------------------------------------------------------------------

class TestFindSegmentsInPolygon:
    """Tests for SpatialQuery.find_segments_in_polygon."""

    @shapely_required
    def test_returns_empty_list_when_no_results(self, mock_db, manhattan_polygon):
        """find_segments_in_polygon returns [] when cursor returns no rows."""
        query = SpatialQuery(mock_db)
        results = query.find_segments_in_polygon(manhattan_polygon)
        assert results == []

    @shapely_required
    def test_returns_segment_ids(self, manhattan_polygon):
        """find_segments_in_polygon maps DB rows to segment ID strings."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [("seg-10",), ("seg-11",), ("seg-12",)]
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        results = query.find_segments_in_polygon(manhattan_polygon)
        assert results == ["seg-10", "seg-11", "seg-12"]

    @shapely_required
    def test_returns_empty_list_on_exception(self, manhattan_polygon):
        """find_segments_in_polygon returns [] on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("oops"))
        query = SpatialQuery(bad_db)
        results = query.find_segments_in_polygon(manhattan_polygon)
        assert results == []

    @shapely_required
    def test_with_material_filter(self, mock_db, manhattan_polygon):
        """find_segments_in_polygon appends material filter without error."""
        query = SpatialQuery(mock_db)
        results = query.find_segments_in_polygon(manhattan_polygon, material_type="asphalt")
        assert isinstance(results, list)

# ---------------------------------------------------------------------------
# SpatialQuery.find_adjacent_blocks
# ---------------------------------------------------------------------------

class TestFindAdjacentBlocks:
    """Tests for SpatialQuery.find_adjacent_blocks."""

    def test_returns_empty_list_when_no_results(self, mock_db):
        """find_adjacent_blocks returns [] when no adjacent blocks exist."""
        query = SpatialQuery(mock_db)
        results = query.find_adjacent_blocks("blk-001")
        assert results == []

    def test_returns_adjacent_block_ids(self):
        """find_adjacent_blocks maps DB rows to block ID strings."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [("blk-002",), ("blk-003",)]
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        results = query.find_adjacent_blocks("blk-001")
        assert results == ["blk-002", "blk-003"]

    def test_returns_empty_list_on_exception(self):
        """find_adjacent_blocks returns [] on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        query = SpatialQuery(bad_db)
        results = query.find_adjacent_blocks("blk-999")
        assert results == []

# ---------------------------------------------------------------------------
# SpatialQuery.find_material_zones
# ---------------------------------------------------------------------------

class TestFindMaterialZones:
    """Tests for SpatialQuery.find_material_zones."""

    def test_returns_empty_list_when_no_results(self, mock_db):
        """find_material_zones returns [] when no zones exist."""
        query = SpatialQuery(mock_db)
        results = query.find_material_zones("concrete")
        assert results == []

    def test_returns_zone_dicts(self):
        """find_material_zones maps DB rows to zone dictionaries."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("D1", 12, 70.5, "POLYGON((-74 40, -73 40, -73 41, -74 41, -74 40))"),
        ]
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        results = query.find_material_zones("concrete")
        assert len(results) == 1
        assert results[0]["district"] == "D1"
        assert results[0]["segment_count"] == 12

    def test_with_borough_filter(self, mock_db):
        """find_material_zones accepts an optional borough filter."""
        query = SpatialQuery(mock_db)
        results = query.find_material_zones("asphalt", borough="Bronx")
        assert isinstance(results, list)

    def test_returns_empty_list_on_exception(self):
        """find_material_zones returns [] on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        query = SpatialQuery(bad_db)
        results = query.find_material_zones("concrete")
        assert results == []

# ---------------------------------------------------------------------------
# SpatialQuery.measure_distance / area / length / buffer
# ---------------------------------------------------------------------------

class TestMeasurements:
    """Tests for measurement methods on SpatialQuery."""

    def test_measure_distance_returns_float_on_success(self):
        """measure_distance returns a float when DB returns a row."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (123.45,)
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        result = query.measure_distance("seg-001", "seg-002")
        assert result == pytest.approx(123.45)

    def test_measure_distance_returns_none_when_no_row(self, mock_db):
        """measure_distance returns None when the DB returns no row."""
        query = SpatialQuery(mock_db)
        result = query.measure_distance("seg-001", "seg-002")
        assert result is None

    def test_measure_distance_returns_none_on_exception(self):
        """measure_distance returns None on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        query = SpatialQuery(bad_db)
        assert query.measure_distance("a", "b") is None

    def test_measure_area_returns_float(self):
        """measure_area returns a float when DB returns a row."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (5000.0,)
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        assert query.measure_area("blk-001") == pytest.approx(5000.0)

    def test_measure_area_returns_none_when_no_row(self, mock_db):
        """measure_area returns None when the DB returns no row."""
        query = SpatialQuery(mock_db)
        assert query.measure_area("blk-999") is None

    def test_measure_area_returns_none_on_exception(self):
        """measure_area returns None on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        assert SpatialQuery(bad_db).measure_area("blk-001") is None

    def test_measure_length_returns_float(self):
        """measure_length returns a float when DB returns a row."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (250.0,)
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        assert query.measure_length("seg-001") == pytest.approx(250.0)

    def test_measure_length_returns_none_when_no_row(self, mock_db):
        """measure_length returns None when the DB returns no row."""
        query = SpatialQuery(mock_db)
        assert query.measure_length("seg-999") is None

    def test_measure_length_returns_none_on_exception(self):
        """measure_length returns None on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        assert SpatialQuery(bad_db).measure_length("seg-001") is None

    def test_buffer_segment_returns_wkt(self):
        """buffer_segment returns a WKT string when DB returns a row."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("POLYGON((...))",)
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        result = query.buffer_segment("seg-001", 50)
        assert result == "POLYGON((...))'"[:-1]

    def test_buffer_segment_returns_none_when_no_row(self, mock_db):
        """buffer_segment returns None when the DB returns no row."""
        query = SpatialQuery(mock_db)
        assert query.buffer_segment("seg-999", 50) is None

    def test_buffer_segment_returns_none_on_exception(self):
        """buffer_segment returns None on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        assert SpatialQuery(bad_db).buffer_segment("seg-001", 50) is None

# ---------------------------------------------------------------------------
# SpatialQuery aggregations
# ---------------------------------------------------------------------------

class TestAggregations:
    """Tests for aggregation methods on SpatialQuery."""

    def test_segments_by_borough_returns_list(self, mock_db):
        """segments_by_borough returns a list (possibly empty)."""
        query = SpatialQuery(mock_db)
        results = query.segments_by_borough()
        assert isinstance(results, list)

    def test_segments_by_district_returns_list(self, mock_db):
        """segments_by_district returns a list (possibly empty)."""
        query = SpatialQuery(mock_db)
        results = query.segments_by_district()
        assert isinstance(results, list)

    def test_segments_by_material_returns_list(self, mock_db):
        """segments_by_material returns a list (possibly empty)."""
        query = SpatialQuery(mock_db)
        results = query.segments_by_material()
        assert isinstance(results, list)

    def test_aggregate_returns_spatial_aggregation_objects(self):
        """_aggregate_segments maps DB rows to SpatialAggregation objects."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("Manhattan", 150, 72.5, 3500.0),
            ("Brooklyn", 200, 65.0, 4800.0),
        ]
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        results = query.segments_by_borough()
        assert len(results) == 2
        assert isinstance(results[0], SpatialAggregation)
        assert results[0].category == "Manhattan"

    def test_aggregate_returns_empty_on_exception(self):
        """_aggregate_segments returns [] on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        query = SpatialQuery(bad_db)
        assert query.segments_by_borough() == []

# ---------------------------------------------------------------------------
# SpatialQuery.condition_statistics
# ---------------------------------------------------------------------------

class TestConditionStatistics:
    """Tests for SpatialQuery.condition_statistics."""

    def test_returns_dict_with_expected_keys(self, mock_db):
        """condition_statistics returns dict with min/max/average/median keys."""
        query = SpatialQuery(mock_db)
        result = query.condition_statistics()
        assert set(result.keys()) == {"min", "max", "average", "median"}

    def test_returns_zeros_on_no_data(self, mock_db):
        """condition_statistics returns all-zero dict when cursor returns no row."""
        query = SpatialQuery(mock_db)
        result = query.condition_statistics()
        assert result == {"min": 0.0, "max": 0.0, "average": 0.0, "median": 0.0}

    def test_returns_real_values_from_db(self):
        """condition_statistics maps DB row values to the returned dict."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (10.0, 95.0, 62.5, 65.0)
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        result = query.condition_statistics()
        assert result["min"] == pytest.approx(10.0)
        assert result["max"] == pytest.approx(95.0)
        assert result["average"] == pytest.approx(62.5)
        assert result["median"] == pytest.approx(65.0)

    def test_accepts_borough_filter(self, mock_db):
        """condition_statistics accepts an optional borough filter."""
        query = SpatialQuery(mock_db)
        result = query.condition_statistics(borough="Queens")
        assert isinstance(result, dict)

    def test_accepts_material_type_filter(self, mock_db):
        """condition_statistics accepts an optional material type filter."""
        query = SpatialQuery(mock_db)
        result = query.condition_statistics(material_type="asphalt")
        assert isinstance(result, dict)

    def test_returns_zeros_on_exception(self):
        """condition_statistics returns all-zero dict on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        query = SpatialQuery(bad_db)
        result = query.condition_statistics()
        assert result == {"min": 0.0, "max": 0.0, "average": 0.0, "median": 0.0}

# ---------------------------------------------------------------------------
# SpatialQuery.inspection_density
# ---------------------------------------------------------------------------

class TestInspectionDensity:
    """Tests for SpatialQuery.inspection_density."""

    @shapely_required
    def test_returns_float(self, mock_db, manhattan_polygon):
        """inspection_density returns a float (0.0 when no data)."""
        query = SpatialQuery(mock_db)
        result = query.inspection_density(manhattan_polygon)
        assert isinstance(result, float)

    @shapely_required
    def test_returns_zero_when_area_is_zero(self, manhattan_polygon):
        """inspection_density returns 0.0 when area denominator is zero."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (5, 0)  # 5 inspections, 0 area
        conn.cursor.return_value = cursor
        db = MagicMock()

        @contextmanager
        def _get_connection():
            yield conn

        db.get_connection = _get_connection
        query = SpatialQuery(db)
        result = query.inspection_density(manhattan_polygon)
        assert result == 0.0

    @shapely_required
    def test_returns_zero_on_exception(self, manhattan_polygon):
        """inspection_density returns 0.0 on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        query = SpatialQuery(bad_db)
        result = query.inspection_density(manhattan_polygon)
        assert result == 0.0

# ---------------------------------------------------------------------------
# SpatialQuery.shortest_path
# ---------------------------------------------------------------------------

class TestShortestPath:
    """Tests for SpatialQuery.shortest_path."""

    def test_returns_empty_when_start_not_found(self, mock_db):
        """shortest_path returns [] when start segment is not found."""
        query = SpatialQuery(mock_db)
        result = query.shortest_path("missing-start", "missing-end")
        assert result == []

    def test_returns_empty_on_exception(self):
        """shortest_path returns [] on DB exception."""
        bad_db = MagicMock()
        bad_db.get_connection = MagicMock(side_effect=Exception("error"))
        query = SpatialQuery(bad_db)
        result = query.shortest_path("a", "b")
        assert result == []
