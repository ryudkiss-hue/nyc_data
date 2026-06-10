"""
DuckDB Spatial Database Foundation for NYC DOT Sidewalk Toolkit.

This module provides the spatial data model layer for sidewalk infrastructure,
leveraging DuckDB's Spatial extension for efficient geographic queries and local analytics.

SRID 4326 (WGS84) is the default for NYC coordinates:
- Center: 40.7128°N, -74.0060°W
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from ..core.duckdb_store import DuckDBManager
from ..core.utils import BOROUGH_SET

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
    "DuckDBSpatialConnection",
    "SpatialDataModel",
]

# NYC Spatial Reference System
SRID_WGS84 = 4326
SRID_NAD83 = 2263  # NY Long Island (feet)

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
        """Convert to Well-Known Text format."""
        return self.geometry.wkt

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
        """Calculate distance to another geometry."""
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

        if self.borough not in BOROUGH_SET:
            raise ValueError(f"borough must be one of {BOROUGH_SET}")


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


class DuckDBSpatialConnection:
    """
    Manager for DuckDB Spatial connections and operations.

    Handles spatial schema creation, geometry-aware insertions, and spatial joins.
    """

    def __init__(self, manager: DuckDBManager | str | None = None) -> None:
        """
        Initialize DuckDB spatial connection.

        Args:
            manager: DuckDBManager instance or path to database file.
        """
        if isinstance(manager, str):
            self.manager = DuckDBManager(manager)
        elif manager is None:
            self.manager = DuckDBManager()
        else:
            self.manager = manager

        logger.info("Initialized DuckDB Spatial connection")

    def create_spatial_tables(self) -> None:
        """Create spatial tables for sidewalk infrastructure."""
        # Sidewalk segments table
        self.manager.conn.execute("""
            CREATE TABLE IF NOT EXISTS sidewalk_segments (
                segment_id VARCHAR PRIMARY KEY,
                geometry GEOMETRY NOT NULL,
                material_type VARCHAR,
                condition_score DOUBLE,
                borough VARCHAR,
                block_id VARCHAR,
                district VARCHAR,
                council_district VARCHAR,
                length_meters DOUBLE,
                last_inspection TIMESTAMP,
                defects INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Blocks table
        self.manager.conn.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                block_id VARCHAR PRIMARY KEY,
                geometry GEOMETRY NOT NULL,
                borough VARCHAR,
                district VARCHAR,
                council_district VARCHAR,
                area_square_meters DOUBLE,
                segments_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Inspections table
        self.manager.conn.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                inspection_id VARCHAR PRIMARY KEY,
                geometry GEOMETRY NOT NULL,
                segment_id VARCHAR,
                inspector_id VARCHAR,
                timestamp TIMESTAMP NOT NULL,
                defect_type VARCHAR,
                severity VARCHAR,
                photo_url VARCHAR,
                gps_accuracy_meters DOUBLE DEFAULT 5.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Material zones table
        self.manager.conn.execute("""
            CREATE TABLE IF NOT EXISTS material_zones (
                zone_id VARCHAR PRIMARY KEY,
                geometry GEOMETRY NOT NULL,
                material_type VARCHAR,
                area_square_meters DOUBLE,
                segment_count INTEGER DEFAULT 0,
                average_condition DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("DuckDB spatial tables created successfully")

    def insert_segment(self, segment: SpatialSegment) -> bool:
        """Insert a sidewalk segment."""
        try:
            self.manager.conn.execute(
                """
                INSERT INTO sidewalk_segments
                (segment_id, geometry, material_type, condition_score,
                 borough, block_id, district, council_district,
                 length_meters, last_inspection, defects)
                VALUES (?, ST_GeomFromText(?), ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (segment_id) DO UPDATE SET
                    geometry = EXCLUDED.geometry,
                    condition_score = EXCLUDED.condition_score,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    segment.segment_id,
                    segment.geometry.to_wkt(),
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
        """Insert a block."""
        try:
            self.manager.conn.execute(
                """
                INSERT INTO blocks
                (block_id, geometry, borough, district, council_district,
                 area_square_meters, segments_count)
                VALUES (?, ST_GeomFromText(?), ?, ?, ?, ?, ?)
                ON CONFLICT (block_id) DO UPDATE SET
                    geometry = EXCLUDED.geometry
                """,
                (
                    block.block_id,
                    block.geometry.to_wkt(),
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
        """Insert an inspection record."""
        try:
            self.manager.conn.execute(
                """
                INSERT INTO inspections
                (inspection_id, geometry, segment_id, inspector_id,
                 timestamp, defect_type, severity, photo_url, gps_accuracy_meters)
                VALUES (?, ST_GeomFromText(?), ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (inspection_id) DO NOTHING
                """,
                (
                    inspection.inspection_id,
                    inspection.geometry.to_wkt(),
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
        """Insert a material zone."""
        try:
            self.manager.conn.execute(
                """
                INSERT INTO material_zones
                (zone_id, geometry, material_type, area_square_meters,
                 segment_count, average_condition)
                VALUES (?, ST_GeomFromText(?), ?, ?, ?, ?)
                ON CONFLICT (zone_id) DO UPDATE SET
                    geometry = EXCLUDED.geometry,
                    average_condition = EXCLUDED.average_condition
                """,
                (
                    zone.zone_id,
                    zone.geometry.to_wkt(),
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

    def find_conflicts(self, buffer_meters: float) -> pd.DataFrame:
        """
        Find conflicts between sidewalk segments and inspections.

        Uses ST_Intersects with a buffer on segments to identify inspections
        that fall within the specified proximity.
        """
        # Conversion for 4326 (WGS84) if necessary - 1m approx 0.000009 degrees
        # For simplicity in this implementation, we use the buffer directly.
        # In production with 4326, we'd use a more precise distance calculation.
        conv = 0.000009
        buffer_val = buffer_meters * conv

        query = """
            SELECT
                s.segment_id,
                i.inspection_id,
                i.defect_type,
                i.severity,
                ST_Distance(s.geometry, i.geometry) as raw_distance
            FROM sidewalk_segments s
            JOIN inspections i ON ST_Intersects(ST_Buffer(s.geometry, ?), i.geometry)
        """
        return self.manager.conn.execute(query, [buffer_val]).df()

    def get_segment(self, segment_id: str) -> SpatialSegment | None:
        """Retrieve a segment by ID."""
        try:
            res = self.manager.conn.execute(
                """
                SELECT segment_id, ST_AsText(geometry), material_type,
                       condition_score, borough, block_id, district,
                       council_district, length_meters, last_inspection, defects
                FROM sidewalk_segments
                WHERE segment_id = ?
                """,
                [segment_id]
            ).fetchone()

            if res:
                from shapely.wkt import loads
                return SpatialSegment(
                    segment_id=res[0],
                    geometry=SpatialGeometry(loads(res[1])),
                    material_type=res[2],
                    condition_score=res[3],
                    borough=res[4],
                    block_id=res[5],
                    district=res[6],
                    council_district=res[7],
                    length_meters=res[8],
                    last_inspection=res[9],
                    defects=res[10] or 0,
                )
        except Exception as e:
            logger.error(f"Error retrieving segment {segment_id}: {e}")
        return None


class SpatialDataModel:
    """
    High-level spatial data model for NYC sidewalk infrastructure.

    Manages persistence to DuckDB Spatial database.
    """

    def __init__(self, db_connection: DuckDBSpatialConnection) -> None:
        """
        Initialize spatial data model.

        Args:
            db_connection: DuckDBSpatialConnection instance
        """
        self.db = db_connection
        self._segments: dict[str, SpatialSegment] = {}
        self._blocks: dict[str, SpatialBlock] = {}
        self._inspections: dict[str, SpatialInspection] = {}
        self._zones: dict[str, SpatialMaterialZone] = {}

    def add_segment(self, segment: SpatialSegment) -> bool:
        """Add segment and persist to database."""
        self._segments[segment.segment_id] = segment
        return self.db.insert_segment(segment)

    def add_block(self, block: SpatialBlock) -> bool:
        """Add block and persist to database."""
        self._blocks[block.block_id] = block
        return self.db.insert_block(block)

    def add_inspection(self, inspection: SpatialInspection) -> bool:
        """Add inspection and persist to database."""
        self._inspections[inspection.inspection_id] = inspection
        return self.db.insert_inspection(inspection)

    def add_material_zone(self, zone: SpatialMaterialZone) -> bool:
        """Add material zone and persist to database."""
        self._zones[zone.zone_id] = zone
        return self.db.insert_material_zone(zone)


@dataclass
class SpatialQuery:
    """Query parameters for spatial searches."""
    bounds: tuple[float, float, float, float] | None = None
    center: tuple[float, float] | None = None
    radius: float | None = None
    filter_type: str = "intersect"


class SpatialIndex:
    """Spatial index abstraction."""

    def __init__(self) -> None:
        self._index = {}

    def build_index(self, data: list) -> bool:
        self._index = {str(i): item for i, item in enumerate(data)}
        return True

    def query_by_bounds(self, bounds: tuple[float, float, float, float]) -> list:
        return list(self._index.values())


class GeometryHandler:
    """Handler for geometry validation."""

    def validate_geometry(self, geometry: Any) -> bool:
        return True

    def convert_format(self, geometry: Any, target_format: str) -> Any:
        return geometry


def create_spatial_index(data: list) -> SpatialIndex:
    index = SpatialIndex()
    index.build_index(data)
    return index


def query_geographic_area(query: SpatialQuery) -> list:
    return []
