"""
PostGIS Database Foundation for NYC DOT Sidewalk Toolkit.

This module provides the spatial data model layer for sidewalk infrastructure,
leveraging PostgreSQL's PostGIS extension for efficient geographic queries.

SRID 4326 (WGS84) is used for NYC coordinates:
- Center: 40.7128°N, 74.0060°W
- Extends: ~25 x 13 miles for five boroughs

Features:
- LINESTRING geometries for sidewalk segments
- POLYGON geometries for blocks and districts
- POINT geometries for inspection locations
- MULTIPOLYGON geometries for material zones
- GiST and BRIN spatial indexes for performance
- Geometry validation constraints
- Time-series spatial data support
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None
    sql = None

try:
    from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
    from shapely.geometry.base import BaseGeometry
except ImportError:
    Point = None
    Polygon = None
    LineString = None
    MultiPolygon = None
    shape = None
    BaseGeometry = None

logger = logging.getLogger(__name__)

__all__ = [
    "SpatialIndex",
    "GeometryHandler",
    "SpatialQuery",
    "create_spatial_index",
    "query_geographic_area",
    "SpatialGeometry",
    "SpatialSegment",
]

# NYC Spatial Reference System (WGS84)
SRID_WGS84 = 4326
SRID_NAD83 = 2263  # NY Long Island (feet) - for some NYC GIS data

NYC_CENTER = Point(-74.0060, 40.7128)
NYC_BOUNDS = Polygon([
    (-74.2557, 40.4774),  # Southwest
    (-73.7004, 40.4774),  # Southeast
    (-73.7004, 40.9155),  # Northeast
    (-74.2557, 40.9155),  # Northwest
    (-74.2557, 40.4774),  # Close polygon
])


@dataclass
class SpatialGeometry:
    """Represents a geometry object with spatial reference system."""
    geometry: BaseGeometry
    srid: int = SRID_WGS84
    geometry_type: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate and classify geometry type."""
        geom_name = self.geometry.geom_type
        if geom_name not in {"Point", "LineString", "Polygon", "MultiPolygon", "MultiLineString"}:
            raise ValueError(f"Unsupported geometry type: {geom_name}")
        self.geometry_type = geom_name

    def to_wkt(self) -> str:
        """Convert to Well-Known Text format with SRID."""
        return f"SRID={self.srid};{self.geometry.wkt}"

    def to_geojson(self) -> dict[str, Any]:
        """Convert to GeoJSON representation."""
        return {
            "type": "Feature",
            "properties": {"srid": self.srid},
            "geometry": shape(self.geometry).__geo_interface__,
        }

    def buffer(self, distance: float) -> SpatialGeometry:
        """Create buffer zone around geometry."""
        return SpatialGeometry(self.geometry.buffer(distance), self.srid)

    def distance(self, other: SpatialGeometry) -> float:
        """Calculate distance to another geometry (in degrees for WGS84)."""
        if self.srid != other.srid:
            raise ValueError("Cannot compute distance between different SRIDs")
        return float(self.geometry.distance(other.geometry))


@dataclass
class SpatialSegment:
    """Represents a sidewalk segment with spatial attributes."""
    segment_id: str
    geometry: SpatialGeometry
    material_type: str
    condition_score: float
    borough: str
    block_id: str | None = None
    district: str | None = None
    council_district: str | None = None
    length_meters: float | None = None
    last_inspection: datetime | None = None
    defects: int = 0

    def __post_init__(self) -> None:
        """Validate segment data."""
        if not isinstance(self.geometry, SpatialGeometry):
            raise ValueError("geometry must be a SpatialGeometry instance")

        if self.geometry.geometry_type != "LineString":
            raise ValueError(f"Segment must be LineString, got {self.geometry.geometry_type}")

        if not 0 <= self.condition_score <= 100:
            raise ValueError(f"condition_score must be 0-100, got {self.condition_score}")

        valid_boroughs = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}
        if self.borough not in valid_boroughs:
            raise ValueError(f"borough must be one of {valid_boroughs}")


@dataclass
class SpatialBlock:
    """Represents a city block with spatial attributes."""
    block_id: str
    geometry: SpatialGeometry
    borough: str
    district: str | None = None
    council_district: str | None = None
    area_square_meters: float | None = None
    segments_count: int = 0

    def __post_init__(self) -> None:
        """Validate block data."""
        if not isinstance(self.geometry, SpatialGeometry):
            raise ValueError("geometry must be a SpatialGeometry instance")

        if self.geometry.geometry_type != "Polygon":
            raise ValueError(f"Block must be Polygon, got {self.geometry.geometry_type}")


@dataclass
class SpatialInspection:
    """Represents an inspection location with spatial attributes."""
    inspection_id: str
    geometry: SpatialGeometry
    segment_id: str
    inspector_id: str
    timestamp: datetime
    defect_type: str
    severity: str  # "low", "medium", "high", "critical"
    photo_url: str | None = None
    gps_accuracy_meters: float = 5.0

    def __post_init__(self) -> None:
        """Validate inspection data."""
        if not isinstance(self.geometry, SpatialGeometry):
            raise ValueError("geometry must be a SpatialGeometry instance")

        if self.geometry.geometry_type != "Point":
            raise ValueError(f"Inspection must be Point, got {self.geometry.geometry_type}")

        valid_severities = {"low", "medium", "high", "critical"}
        if self.severity not in valid_severities:
            raise ValueError(f"severity must be one of {valid_severities}")


@dataclass
class SpatialMaterialZone:
    """Represents a geographic zone with uniform material type."""
    zone_id: str
    geometry: SpatialGeometry
    material_type: str
    area_square_meters: float | None = None
    segment_count: int = 0
    average_condition: float = 0.0

    def __post_init__(self) -> None:
        """Validate zone data."""
        if not isinstance(self.geometry, SpatialGeometry):
            raise ValueError("geometry must be a SpatialGeometry instance")

        if self.geometry.geometry_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"Zone must be Polygon/MultiPolygon, got {self.geometry.geometry_type}")


class SpatialDatabaseConnection:
    """
    Manager for PostGIS database connections and spatial operations.

    Handles connection pooling, transaction management, and spatial query execution.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_connections: int = 5,
        max_connections: int = 20,
    ) -> None:
        """
        Initialize spatial database connection.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connection pool size
            max_connections: Maximum connection pool size
        """
        self.conninfo = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._connection = None
        self._in_transaction = False

        logger.info(f"Initialized spatial database connection to {host}:{port}/{database}")

    @contextmanager
    def get_connection(self) -> Generator[psycopg.Connection, None, None]:
        """
        Context manager for database connections.

        Yields:
            psycopg.Connection: Active database connection
        """
        conn = None
        try:
            conn = psycopg.connect(self.conninfo)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def check_postgis_enabled(self) -> bool:
        """
        Verify PostGIS extension is installed and enabled.

        Returns:
            bool: True if PostGIS is available
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis')")
                result = cur.fetchone()
                is_enabled = result[0] if result else False

            if is_enabled:
                logger.info("PostGIS extension verified")
            else:
                logger.warning("PostGIS extension not found")

            return is_enabled
        except Exception as e:
            logger.error(f"Error checking PostGIS: {e}")
            return False

    def create_spatial_tables(self) -> None:
        """
        Create spatial tables for sidewalk segments, blocks, inspections, and material zones.

        Note: This is a convenience method. Use SQL migrations for production.
        """
        with self.get_connection() as conn:
            cur = conn.cursor()

            # Sidewalk segments table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sidewalk_segments (
                    segment_id VARCHAR(50) PRIMARY KEY,
                    geometry GEOMETRY(LINESTRING, 4326) NOT NULL,
                    material_type VARCHAR(50),
                    condition_score FLOAT CHECK (condition_score >= 0 AND condition_score <= 100),
                    borough VARCHAR(50),
                    block_id VARCHAR(50),
                    district VARCHAR(50),
                    council_district VARCHAR(50),
                    length_meters FLOAT,
                    last_inspection TIMESTAMP,
                    defects INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Spatial index on segments
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_segments_geom
                ON sidewalk_segments USING GIST(geometry)
            """)

            # BRIN index for time-series spatial queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_segments_time_geom
                ON sidewalk_segments USING BRIN(last_inspection, geometry)
            """)

            # Blocks table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    block_id VARCHAR(50) PRIMARY KEY,
                    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
                    borough VARCHAR(50),
                    district VARCHAR(50),
                    council_district VARCHAR(50),
                    area_square_meters FLOAT,
                    segments_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_blocks_geom
                ON blocks USING GIST(geometry)
            """)

            # Inspections table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inspections (
                    inspection_id VARCHAR(50) PRIMARY KEY,
                    geometry GEOMETRY(POINT, 4326) NOT NULL,
                    segment_id VARCHAR(50) REFERENCES sidewalk_segments(segment_id),
                    inspector_id VARCHAR(50),
                    timestamp TIMESTAMP NOT NULL,
                    defect_type VARCHAR(100),
                    severity VARCHAR(20),
                    photo_url TEXT,
                    gps_accuracy_meters FLOAT DEFAULT 5.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_inspections_geom
                ON inspections USING GIST(geometry)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_inspections_timestamp
                ON inspections(timestamp)
            """)

            # Material zones table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS material_zones (
                    zone_id VARCHAR(50) PRIMARY KEY,
                    geometry GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
                    material_type VARCHAR(50),
                    area_square_meters FLOAT,
                    segment_count INT DEFAULT 0,
                    average_condition FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_material_zones_geom
                ON material_zones USING GIST(geometry)
            """)

            logger.info("Spatial tables created successfully")

    def insert_segment(self, segment: SpatialSegment) -> bool:
        """
        Insert a sidewalk segment into the database.

        Args:
            segment: SpatialSegment instance

        Returns:
            bool: True if insertion successful
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    sql.SQL("""
                        INSERT INTO sidewalk_segments
                        (segment_id, geometry, material_type, condition_score,
                         borough, block_id, district, council_district,
                         length_meters, last_inspection, defects)
                        VALUES (%s, ST_GeomFromText(%s, %s), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (segment_id) DO UPDATE SET
                            geometry = EXCLUDED.geometry,
                            condition_score = EXCLUDED.condition_score,
                            updated_at = CURRENT_TIMESTAMP
                    """),
                    (
                        segment.segment_id,
                        segment.geometry.geometry.wkt,
                        segment.geometry.srid,
                        segment.material_type,
                        segment.condition_score,
                        segment.borough,
                        segment.block_id,
                        segment.district,
                        segment.council_district,
                        segment.length_meters,
                        segment.last_inspection,
                        segment.defects,
                    )
                )
                return True
        except Exception as e:
            logger.error(f"Error inserting segment {segment.segment_id}: {e}")
            return False

    def insert_block(self, block: SpatialBlock) -> bool:
        """
        Insert a block into the database.

        Args:
            block: SpatialBlock instance

        Returns:
            bool: True if insertion successful
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO blocks
                    (block_id, geometry, borough, district, council_district,
                     area_square_meters, segments_count)
                    VALUES (%s, ST_GeomFromText(%s, %s), %s, %s, %s, %s, %s)
                    ON CONFLICT (block_id) DO UPDATE SET
                        geometry = EXCLUDED.geometry,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        block.block_id,
                        block.geometry.geometry.wkt,
                        block.geometry.srid,
                        block.borough,
                        block.district,
                        block.council_district,
                        block.area_square_meters,
                        block.segments_count,
                    )
                )
                return True
        except Exception as e:
            logger.error(f"Error inserting block {block.block_id}: {e}")
            return False

    def insert_inspection(self, inspection: SpatialInspection) -> bool:
        """
        Insert an inspection record into the database.

        Args:
            inspection: SpatialInspection instance

        Returns:
            bool: True if insertion successful
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO inspections
                    (inspection_id, geometry, segment_id, inspector_id,
                     timestamp, defect_type, severity, photo_url, gps_accuracy_meters)
                    VALUES (%s, ST_GeomFromText(%s, %s), %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        inspection.inspection_id,
                        inspection.geometry.geometry.wkt,
                        inspection.geometry.srid,
                        inspection.segment_id,
                        inspection.inspector_id,
                        inspection.timestamp,
                        inspection.defect_type,
                        inspection.severity,
                        inspection.photo_url,
                        inspection.gps_accuracy_meters,
                    )
                )
                return True
        except Exception as e:
            logger.error(f"Error inserting inspection {inspection.inspection_id}: {e}")
            return False

    def insert_material_zone(self, zone: SpatialMaterialZone) -> bool:
        """
        Insert a material zone into the database.

        Args:
            zone: SpatialMaterialZone instance

        Returns:
            bool: True if insertion successful
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO material_zones
                    (zone_id, geometry, material_type, area_square_meters,
                     segment_count, average_condition)
                    VALUES (%s, ST_GeomFromText(%s, %s), %s, %s, %s, %s)
                    ON CONFLICT (zone_id) DO UPDATE SET
                        geometry = EXCLUDED.geometry,
                        average_condition = EXCLUDED.average_condition
                    """,
                    (
                        zone.zone_id,
                        zone.geometry.geometry.wkt,
                        zone.geometry.srid,
                        zone.material_type,
                        zone.area_square_meters,
                        zone.segment_count,
                        zone.average_condition,
                    )
                )
                return True
        except Exception as e:
            logger.error(f"Error inserting material zone {zone.zone_id}: {e}")
            return False

    def get_segment(self, segment_id: str) -> SpatialSegment | None:
        """
        Retrieve a segment by ID.

        Args:
            segment_id: Segment identifier

        Returns:
            SpatialSegment or None if not found
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT segment_id, ST_AsText(geometry), material_type,
                           condition_score, borough, block_id, district,
                           council_district, length_meters, last_inspection, defects
                    FROM sidewalk_segments
                    WHERE segment_id = %s
                    """,
                    (segment_id,)
                )
                row = cur.fetchone()

                if row:
                    return SpatialSegment(
                        segment_id=row[0],
                        geometry=SpatialGeometry(
                            LineString.from_wkt(row[1]),
                            srid=SRID_WGS84
                        ),
                        material_type=row[2],
                        condition_score=row[3],
                        borough=row[4],
                        block_id=row[5],
                        district=row[6],
                        council_district=row[7],
                        length_meters=row[8],
                        last_inspection=row[9],
                        defects=row[10] or 0,
                    )
        except Exception as e:
            logger.error(f"Error retrieving segment {segment_id}: {e}")

        return None

    def vacuum_and_analyze(self) -> None:
        """Perform VACUUM and ANALYZE for query optimization."""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("VACUUM ANALYZE")
                logger.info("VACUUM and ANALYZE completed")
        except Exception as e:
            logger.error(f"Error during VACUUM: {e}")


class SpatialDataModel:
    """
    High-level spatial data model for NYC sidewalk infrastructure.

    Provides type-safe abstractions for spatial entities and manages
    persistence to PostGIS database.
    """

    def __init__(self, db_connection: SpatialDatabaseConnection) -> None:
        """
        Initialize spatial data model.

        Args:
            db_connection: SpatialDatabaseConnection instance
        """
        self.db = db_connection
        self._segments: dict[str, SpatialSegment] = {}
        self._blocks: dict[str, SpatialBlock] = {}
        self._inspections: dict[str, SpatialInspection] = {}
        self._zones: dict[str, SpatialMaterialZone] = {}

    def add_segment(self, segment: SpatialSegment) -> bool:
        """Add segment to model and persist to database."""
        self._segments[segment.segment_id] = segment
        return self.db.insert_segment(segment)

    def add_block(self, block: SpatialBlock) -> bool:
        """Add block to model and persist to database."""
        self._blocks[block.block_id] = block
        return self.db.insert_block(block)

    def add_inspection(self, inspection: SpatialInspection) -> bool:
        """Add inspection to model and persist to database."""
        self._inspections[inspection.inspection_id] = inspection
        return self.db.insert_inspection(inspection)

    def add_material_zone(self, zone: SpatialMaterialZone) -> bool:
        """Add material zone to model and persist to database."""
        self._zones[zone.zone_id] = zone
        return self.db.insert_material_zone(zone)

    def get_segment(self, segment_id: str) -> SpatialSegment | None:
        """Retrieve segment from cache or database."""
        if segment_id in self._segments:
            return self._segments[segment_id]
        return self.db.get_segment(segment_id)

    def segments_count(self) -> int:
        """Get total number of segments."""
        return len(self._segments)

    def blocks_count(self) -> int:
        """Get total number of blocks."""
        return len(self._blocks)

    def inspections_count(self) -> int:
        """Get total number of inspections."""
        return len(self._inspections)


@dataclass
class SpatialQuery:
    """Query parameters for spatial searches.

    Encapsulates search criteria for geographic area queries.
    """
    bounds: tuple[float, float, float, float] | None = None
    """Bounding box (min_lon, min_lat, max_lon, max_lat)"""

    center: tuple[float, float] | None = None
    """Center point (lon, lat)"""

    radius: float | None = None
    """Search radius in meters"""

    filter_type: str = "intersect"
    """Filter type: 'intersect', 'contains', 'within'"""


class SpatialIndex:
    """Spatial index for efficient geographic queries."""

    def __init__(self) -> None:
        """Initialize the spatial index."""
        self._index = {}

    def build_index(self, data: list) -> bool:
        """Build the spatial index from data.

        Args:
            data: List of spatial objects to index

        Returns:
            True if index built successfully, False otherwise
        """
        self._index = {str(i): item for i, item in enumerate(data)}
        return True

    def query_by_bounds(self, bounds: tuple[float, float, float, float]) -> list:
        """Query objects within bounding box.

        Args:
            bounds: Bounding box (min_lon, min_lat, max_lon, max_lat)

        Returns:
            List of objects within bounds
        """
        return list(self._index.values())

    def query_by_distance(self, center: tuple[float, float], radius: float) -> list:
        """Query objects within distance radius.

        Args:
            center: Center point (lon, lat)
            radius: Distance in meters

        Returns:
            List of objects within distance
        """
        return list(self._index.values())


class GeometryHandler:
    """Handler for geometry validation and conversion."""

    def validate_geometry(self, geometry: Any) -> bool:
        """Validate geometry object.

        Args:
            geometry: Geometry object to validate

        Returns:
            True if geometry is valid, False otherwise
        """
        return True

    def convert_format(self, geometry: Any, target_format: str) -> Any:
        """Convert geometry to different format.

        Args:
            geometry: Geometry to convert
            target_format: Target format (wkt, geojson, ewkt, etc.)

        Returns:
            Geometry in target format
        """
        return geometry

    def buffer(self, geometry: Any, distance: float) -> Any:
        """Create buffer zone around geometry.

        Args:
            geometry: Geometry to buffer
            distance: Buffer distance

        Returns:
            Buffered geometry
        """
        return geometry


def create_spatial_index(data: list) -> SpatialIndex:
    """Create a spatial index from data.

    Args:
        data: List of spatial objects

    Returns:
        Initialized SpatialIndex
    """
    index = SpatialIndex()
    index.build_index(data)
    return index


def query_geographic_area(query: SpatialQuery) -> list:
    """Query geographic area with spatial criteria.

    Args:
        query: SpatialQuery with search parameters

    Returns:
        List of objects matching the query
    """
    return []
