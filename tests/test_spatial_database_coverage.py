"""Comprehensive tests for spatial.database module."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers: detect optional deps and skip when genuinely absent
# ---------------------------------------------------------------------------

try:
    from shapely.geometry import LineString, MultiPolygon, Point, Polygon
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

shapely_required = pytest.mark.skipif(not HAS_SHAPELY, reason="shapely not installed")

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from socrata_toolkit.spatial.database import (
    SRID_NAD83,
    SRID_WGS84,
    GeometryHandler,
    SpatialIndex,
    SpatialQuery,
    create_spatial_index,
    query_geographic_area,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_conn() -> MagicMock:
    """Return a mock SpatialDatabaseConnection whose get_connection works."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (True,)
    cursor.fetchall.return_value = []
    conn.cursor.return_value = cursor

    db = MagicMock()

    @contextmanager
    def _get_connection():
        yield conn

    db.get_connection = _get_connection
    return db

@pytest.fixture
def point_geom():
    """Return a Shapely Point if available, else skip."""
    if not HAS_SHAPELY:
        pytest.skip("shapely not installed")
    return Point(-74.0060, 40.7128)

@pytest.fixture
def linestring_geom():
    """Return a Shapely LineString representing a sidewalk segment."""
    if not HAS_SHAPELY:
        pytest.skip("shapely not installed")
    return LineString([(-74.0060, 40.7128), (-74.0065, 40.7133)])

@pytest.fixture
def polygon_geom():
    """Return a Shapely Polygon representing a city block."""
    if not HAS_SHAPELY:
        pytest.skip("shapely not installed")
    return Polygon([
        (-74.0060, 40.7128),
        (-74.0070, 40.7128),
        (-74.0070, 40.7138),
        (-74.0060, 40.7138),
        (-74.0060, 40.7128),
    ])

@pytest.fixture
def multipolygon_geom():
    """Return a Shapely MultiPolygon representing a material zone."""
    if not HAS_SHAPELY:
        pytest.skip("shapely not installed")
    p1 = Polygon([(-74.006, 40.713), (-74.007, 40.713), (-74.007, 40.714), (-74.006, 40.714), (-74.006, 40.713)])
    p2 = Polygon([(-74.008, 40.715), (-74.009, 40.715), (-74.009, 40.716), (-74.008, 40.716), (-74.008, 40.715)])
    return MultiPolygon([p1, p2])

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

class TestModuleConstants:
    """Verify exported SRID constants are correct."""

    def test_srid_wgs84_value(self):
        """SRID_WGS84 must equal 4326."""
        assert SRID_WGS84 == 4326

    def test_srid_nad83_value(self):
        """SRID_NAD83 must equal 2263."""
        assert SRID_NAD83 == 2263

# ---------------------------------------------------------------------------
# SpatialGeometry dataclass
# ---------------------------------------------------------------------------

class TestSpatialGeometry:
    """Tests for SpatialGeometry dataclass."""

    @shapely_required
    def test_geometry_type_classified_point(self, point_geom):
        """SpatialGeometry sets geometry_type to 'Point' for Point input."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(point_geom)
        assert sg.geometry_type == "Point"

    @shapely_required
    def test_geometry_type_classified_linestring(self, linestring_geom):
        """SpatialGeometry sets geometry_type to 'LineString' for LineString input."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(linestring_geom)
        assert sg.geometry_type == "LineString"

    @shapely_required
    def test_geometry_type_classified_polygon(self, polygon_geom):
        """SpatialGeometry sets geometry_type to 'Polygon' for Polygon input."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(polygon_geom)
        assert sg.geometry_type == "Polygon"

    @shapely_required
    def test_geometry_type_classified_multipolygon(self, multipolygon_geom):
        """SpatialGeometry sets geometry_type to 'MultiPolygon' for MultiPolygon input."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(multipolygon_geom)
        assert sg.geometry_type == "MultiPolygon"

    @shapely_required
    def test_srid_defaults_to_wgs84(self, point_geom):
        """SpatialGeometry.srid defaults to SRID_WGS84 when not supplied."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(point_geom)
        assert sg.srid == SRID_WGS84

    @shapely_required
    def test_srid_custom(self, point_geom):
        """SpatialGeometry accepts a custom SRID."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(point_geom, srid=SRID_NAD83)
        assert sg.srid == SRID_NAD83

    @shapely_required
    def test_to_wkt_returns_bare_wkt(self, point_geom):
        """to_wkt() returns standard WKT (no SRID prefix) for DuckDB ST_GeomFromText."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(point_geom)
        wkt = sg.to_wkt()
        assert wkt.upper().startswith("POINT")
        assert "SRID" not in wkt.upper()

    @shapely_required
    def test_to_geojson_returns_feature(self, point_geom):
        """to_geojson() returns a dict with type == 'Feature'."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(point_geom)
        gj = sg.to_geojson()
        assert gj["type"] == "Feature"
        assert "geometry" in gj

    @shapely_required
    def test_buffer_returns_spatial_geometry(self, point_geom):
        """buffer() returns a new SpatialGeometry with the same SRID."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg = SpatialGeometry(point_geom)
        buffered = sg.buffer(0.001)
        assert isinstance(buffered, SpatialGeometry)
        assert buffered.srid == sg.srid

    @shapely_required
    def test_distance_same_srid(self, point_geom):
        """distance() returns a float for two geometries with the same SRID."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg1 = SpatialGeometry(point_geom)
        sg2 = SpatialGeometry(Point(-74.0070, 40.7140))
        d = sg1.distance(sg2)
        assert isinstance(d, float)
        assert d >= 0.0

    @shapely_required
    def test_distance_different_srids_raises(self, point_geom):
        """distance() raises ValueError when SRIDs differ."""
        from socrata_toolkit.spatial.database import SpatialGeometry
        sg1 = SpatialGeometry(point_geom, srid=SRID_WGS84)
        sg2 = SpatialGeometry(point_geom, srid=SRID_NAD83)
        with pytest.raises(ValueError, match="SRID"):
            sg1.distance(sg2)

    @shapely_required
    def test_invalid_geom_type_raises(self):
        """SpatialGeometry raises ValueError for unsupported geometry types."""
        from shapely.geometry import GeometryCollection

        from socrata_toolkit.spatial.database import SpatialGeometry
        gc = GeometryCollection()
        with pytest.raises(ValueError, match="Unsupported geometry type"):
            SpatialGeometry(gc)

# ---------------------------------------------------------------------------
# SpatialSegment dataclass
# ---------------------------------------------------------------------------

class TestSpatialSegment:
    """Tests for SpatialSegment validation logic."""

    @shapely_required
    def test_valid_segment_creation(self, linestring_geom):
        """SpatialSegment is created without error for valid inputs."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialSegment
        seg = SpatialSegment(
            segment_id="seg-001",
            geometry=SpatialGeometry(linestring_geom),
            material_type="concrete",
            condition_score=75.0,
            borough="Manhattan",
        )
        assert seg.segment_id == "seg-001"

    @shapely_required
    def test_segment_invalid_geometry_type_raises(self, point_geom):
        """SpatialSegment raises ValueError when geometry is not a LineString."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialSegment
        with pytest.raises(ValueError, match="LineString"):
            SpatialSegment(
                segment_id="seg-002",
                geometry=SpatialGeometry(point_geom),
                material_type="concrete",
                condition_score=50.0,
                borough="Brooklyn",
            )

    @shapely_required
    def test_segment_condition_score_out_of_range_raises(self, linestring_geom):
        """SpatialSegment raises ValueError when condition_score exceeds 100."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialSegment
        with pytest.raises(ValueError, match="condition_score"):
            SpatialSegment(
                segment_id="seg-003",
                geometry=SpatialGeometry(linestring_geom),
                material_type="concrete",
                condition_score=150.0,
                borough="Queens",
            )

    @shapely_required
    def test_segment_invalid_borough_raises(self, linestring_geom):
        """SpatialSegment raises ValueError for an unknown borough."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialSegment
        with pytest.raises(ValueError, match="borough"):
            SpatialSegment(
                segment_id="seg-004",
                geometry=SpatialGeometry(linestring_geom),
                material_type="asphalt",
                condition_score=60.0,
                borough="NotABorough",
            )

    @shapely_required
    def test_segment_geometry_not_spatial_geometry_raises(self, linestring_geom):
        """SpatialSegment raises ValueError when geometry is not SpatialGeometry."""
        from socrata_toolkit.spatial.database import SpatialSegment
        with pytest.raises(ValueError, match="SpatialGeometry"):
            SpatialSegment(
                segment_id="seg-005",
                geometry=linestring_geom,  # raw shapely, not wrapped
                material_type="concrete",
                condition_score=50.0,
                borough="Bronx",
            )

# ---------------------------------------------------------------------------
# SpatialIndex
# ---------------------------------------------------------------------------

class TestSpatialIndex:
    """Tests for SpatialIndex class."""

    def test_build_index_returns_true(self):
        """build_index returns True for a non-empty list."""
        idx = SpatialIndex()
        result = idx.build_index(["a", "b", "c"])
        assert result is True

    def test_build_index_empty_list(self):
        """build_index returns True for an empty list."""
        idx = SpatialIndex()
        result = idx.build_index([])
        assert result is True

    def test_query_by_bounds_returns_all(self):
        """query_by_bounds returns all items currently in the index."""
        idx = SpatialIndex()
        items = ["item1", "item2", "item3"]
        idx.build_index(items)
        result = idx.query_by_bounds((-74.3, 40.4, -73.7, 40.9))
        assert len(result) == 3

    def test_query_by_distance_returns_all(self):
        """query_by_distance returns all items currently in the index."""
        idx = SpatialIndex()
        items = ["x", "y"]
        idx.build_index(items)
        result = idx.query_by_distance((-74.0, 40.7), 500)
        assert len(result) == 2

    def test_empty_index_returns_empty_list(self):
        """Querying an empty index returns an empty list."""
        idx = SpatialIndex()
        assert idx.query_by_bounds((-74.3, 40.4, -73.7, 40.9)) == []
        assert idx.query_by_distance((-74.0, 40.7), 100) == []

# ---------------------------------------------------------------------------
# GeometryHandler
# ---------------------------------------------------------------------------

class TestGeometryHandler:
    """Tests for GeometryHandler class."""

    def test_validate_geometry_returns_true(self):
        """validate_geometry returns True for any input."""
        gh = GeometryHandler()
        assert gh.validate_geometry("POINT(0 0)") is True
        assert gh.validate_geometry(None) is True

    def test_convert_format_returns_input(self):
        """convert_format returns the geometry unchanged."""
        gh = GeometryHandler()
        sentinel = object()
        assert gh.convert_format(sentinel, "wkt") is sentinel

    def test_buffer_returns_input(self):
        """buffer returns the geometry unchanged."""
        gh = GeometryHandler()
        sentinel = object()
        assert gh.buffer(sentinel, 50) is sentinel

# ---------------------------------------------------------------------------
# SpatialQuery dataclass
# ---------------------------------------------------------------------------

class TestSpatialQueryDataclass:
    """Tests for the SpatialQuery dataclass."""

    def test_default_filter_type_is_intersect(self):
        """SpatialQuery defaults filter_type to 'intersect'."""
        sq = SpatialQuery()
        assert sq.filter_type == "intersect"

    def test_bounds_set_correctly(self):
        """SpatialQuery stores bounding box correctly."""
        sq = SpatialQuery(bounds=(-74.3, 40.4, -73.7, 40.9))
        assert sq.bounds == (-74.3, 40.4, -73.7, 40.9)

    def test_center_and_radius(self):
        """SpatialQuery stores center and radius correctly."""
        sq = SpatialQuery(center=(-74.006, 40.713), radius=500.0)
        assert sq.center == (-74.006, 40.713)
        assert sq.radius == 500.0

# ---------------------------------------------------------------------------
# create_spatial_index helper
# ---------------------------------------------------------------------------

class TestCreateSpatialIndex:
    """Tests for the create_spatial_index module-level helper."""

    def test_returns_spatial_index(self):
        """create_spatial_index returns a SpatialIndex instance."""
        result = create_spatial_index(["a", "b"])
        assert isinstance(result, SpatialIndex)

    def test_index_contains_input_items(self):
        """create_spatial_index populates the index with provided items."""
        result = create_spatial_index(["item1", "item2"])
        assert len(result.query_by_bounds((0, 0, 1, 1))) == 2

# ---------------------------------------------------------------------------
# query_geographic_area helper
# ---------------------------------------------------------------------------

class TestQueryGeographicArea:
    """Tests for the query_geographic_area module-level helper."""

    def test_returns_empty_list_by_default(self):
        """query_geographic_area always returns an empty list."""
        result = query_geographic_area(SpatialQuery())
        assert result == []

    def test_accepts_various_query_configs(self):
        """query_geographic_area accepts queries with bounds, center, or radius."""
        sq = SpatialQuery(bounds=(-74.3, 40.4, -73.7, 40.9), filter_type="within")
        assert query_geographic_area(sq) == []

# ---------------------------------------------------------------------------
# DuckDBSpatialConnection — error-handling tests with a failing manager
# ---------------------------------------------------------------------------

class TestDuckDBSpatialConnection:
    """Tests for DuckDBSpatialConnection error handling.

    The migration replaced the psycopg/PostGIS-backed SpatialDatabaseConnection
    with an in-process DuckDB connection. These tests drive the error paths by
    supplying a manager whose connection raises on execute.
    """

    def _make_failing_db(self):
        """Construct a DuckDBSpatialConnection whose manager raises on execute."""
        from socrata_toolkit.spatial.database import DuckDBSpatialConnection
        manager = MagicMock()
        manager.conn.execute.side_effect = Exception("db error")
        return DuckDBSpatialConnection(manager)

    @shapely_required
    def test_insert_segment_returns_false_on_error(self, linestring_geom):
        """insert_segment returns False when the DB raises an exception."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialSegment
        db = self._make_failing_db()
        seg = SpatialSegment(
            segment_id="seg-100",
            geometry=SpatialGeometry(linestring_geom),
            material_type="concrete",
            condition_score=70.0,
            borough="Manhattan",
        )
        assert db.insert_segment(seg) is False

    @shapely_required
    def test_insert_block_returns_false_on_error(self, polygon_geom):
        """insert_block returns False when the DB raises an exception."""
        from socrata_toolkit.spatial.database import SpatialBlock, SpatialGeometry
        db = self._make_failing_db()
        block = SpatialBlock(
            block_id="blk-001",
            geometry=SpatialGeometry(polygon_geom),
            borough="Brooklyn",
        )
        assert db.insert_block(block) is False

    @shapely_required
    def test_insert_inspection_returns_false_on_error(self, point_geom):
        """insert_inspection returns False when the DB raises an exception."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialInspection
        db = self._make_failing_db()
        insp = SpatialInspection(
            inspection_id="insp-001",
            geometry=SpatialGeometry(point_geom),
            segment_id="seg-100",
            inspector_id="inspector-1",
            timestamp=datetime(2026, 1, 15, 9, 0),
            defect_type="crack",
            severity="high",
        )
        assert db.insert_inspection(insp) is False

    @shapely_required
    def test_insert_material_zone_returns_false_on_error(self, multipolygon_geom):
        """insert_material_zone returns False when the DB raises an exception."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialMaterialZone
        db = self._make_failing_db()
        zone = SpatialMaterialZone(
            zone_id="zone-001",
            geometry=SpatialGeometry(multipolygon_geom),
            material_type="asphalt",
        )
        assert db.insert_material_zone(zone) is False

    def test_get_segment_returns_none_on_error(self):
        """get_segment returns None when the DB raises an exception."""
        db = self._make_failing_db()
        assert db.get_segment("seg-999") is None

    def test_str_manager_is_wrapped(self):
        """A string path is wrapped in a DuckDBManager rather than used directly."""
        from socrata_toolkit.spatial.database import DuckDBManager, DuckDBSpatialConnection
        db = DuckDBSpatialConnection(":memory:")
        assert isinstance(db.manager, DuckDBManager)

# ---------------------------------------------------------------------------
# SpatialDataModel
# ---------------------------------------------------------------------------

class TestSpatialDataModel:
    """Tests for SpatialDataModel in-memory caching behavior."""

    @shapely_required
    def test_segment_count_increments(self, linestring_geom, mock_db_conn):
        """segments_count increases after add_segment."""
        from socrata_toolkit.spatial.database import (
            SpatialDataModel,
            SpatialGeometry,
            SpatialSegment,
        )
        mock_db_conn.insert_segment = MagicMock(return_value=True)
        model = SpatialDataModel(mock_db_conn)
        assert model.segments_count() == 0
        seg = SpatialSegment(
            segment_id="seg-m1",
            geometry=SpatialGeometry(linestring_geom),
            material_type="concrete",
            condition_score=80.0,
            borough="Manhattan",
        )
        model.add_segment(seg)
        assert model.segments_count() == 1

    @shapely_required
    def test_get_segment_from_cache(self, linestring_geom, mock_db_conn):
        """get_segment returns cached segment without hitting the DB."""
        from socrata_toolkit.spatial.database import (
            SpatialDataModel,
            SpatialGeometry,
            SpatialSegment,
        )
        mock_db_conn.insert_segment = MagicMock(return_value=True)
        model = SpatialDataModel(mock_db_conn)
        seg = SpatialSegment(
            segment_id="seg-cache",
            geometry=SpatialGeometry(linestring_geom),
            material_type="concrete",
            condition_score=65.0,
            borough="Queens",
        )
        model.add_segment(seg)
        retrieved = model.get_segment("seg-cache")
        assert retrieved is seg

    @shapely_required
    def test_get_segment_falls_back_to_db(self, mock_db_conn):
        """get_segment queries the DB for an ID not in the cache."""
        from socrata_toolkit.spatial.database import SpatialDataModel
        mock_db_conn.get_segment = MagicMock(return_value=None)
        model = SpatialDataModel(mock_db_conn)
        result = model.get_segment("unknown-id")
        mock_db_conn.get_segment.assert_called_once_with("unknown-id")
        assert result is None

    @shapely_required
    def test_blocks_count_increments(self, polygon_geom, mock_db_conn):
        """blocks_count increases after add_block."""
        from socrata_toolkit.spatial.database import SpatialBlock, SpatialDataModel, SpatialGeometry
        mock_db_conn.insert_block = MagicMock(return_value=True)
        model = SpatialDataModel(mock_db_conn)
        assert model.blocks_count() == 0
        block = SpatialBlock(
            block_id="blk-m1",
            geometry=SpatialGeometry(polygon_geom),
            borough="Bronx",
        )
        model.add_block(block)
        assert model.blocks_count() == 1

    @shapely_required
    def test_inspections_count_increments(self, point_geom, mock_db_conn):
        """inspections_count increases after add_inspection."""
        from socrata_toolkit.spatial.database import (
            SpatialDataModel,
            SpatialGeometry,
            SpatialInspection,
        )
        mock_db_conn.insert_inspection = MagicMock(return_value=True)
        model = SpatialDataModel(mock_db_conn)
        assert model.inspections_count() == 0
        insp = SpatialInspection(
            inspection_id="insp-m1",
            geometry=SpatialGeometry(point_geom),
            segment_id="seg-100",
            inspector_id="inspector-1",
            timestamp=datetime(2026, 2, 1),
            defect_type="crack",
            severity="low",
        )
        model.add_inspection(insp)
        assert model.inspections_count() == 1

# ---------------------------------------------------------------------------
# SpatialInspection validation
# ---------------------------------------------------------------------------

class TestSpatialInspection:
    """Tests for SpatialInspection validation."""

    @shapely_required
    def test_invalid_geometry_type_raises(self, linestring_geom):
        """SpatialInspection raises ValueError when geometry is not a Point."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialInspection
        with pytest.raises(ValueError, match="Point"):
            SpatialInspection(
                inspection_id="insp-err",
                geometry=SpatialGeometry(linestring_geom),
                segment_id="seg-100",
                inspector_id="inspector-1",
                timestamp=datetime(2026, 3, 1),
                defect_type="crack",
                severity="high",
            )

    @shapely_required
    def test_invalid_severity_raises(self, point_geom):
        """SpatialInspection raises ValueError for an unknown severity."""
        from socrata_toolkit.spatial.database import SpatialGeometry, SpatialInspection
        with pytest.raises(ValueError, match="severity"):
            SpatialInspection(
                inspection_id="insp-sev",
                geometry=SpatialGeometry(point_geom),
                segment_id="seg-100",
                inspector_id="inspector-1",
                timestamp=datetime(2026, 3, 1),
                defect_type="crack",
                severity="extreme",
            )
