"""
Spatial Query Engine for PostGIS-backed geographic analysis.

This module provides high-level spatial query operations including:
- Proximity queries (find nearby segments)
- Geometric intersections (segments in polygon)
- Distance measurements
- Buffering and zone creation
- Network shortest path
- Spatial aggregations and grouping
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import psycopg  # type: ignore[import]
from psycopg import sql  # type: ignore[import]
from shapely.geometry import Point, Polygon, LineString  # type: ignore[import]

from .spatial_database import (
    SpatialDatabaseConnection,
    SpatialSegment,
    SpatialBlock,
    SpatialInspection,
    SRID_WGS84,
)

logger = logging.getLogger(__name__)


@dataclass
class ProximityResult:
    """Result of a proximity query."""
    segment_id: str
    distance_meters: float
    material_type: str
    condition_score: float
    borough: str


@dataclass
class SpatialAggregation:
    """Result of spatial aggregation."""
    category: str
    total_length_meters: float
    segment_count: int
    average_condition: float
    borough: Optional[str] = None
    district: Optional[str] = None


class SpatialQuery:
    """
    High-performance spatial query engine for sidewalk data.
    
    All distances in meters, all areas in square meters.
    Uses PostGIS ST_* functions for efficient geographic analysis.
    """
    
    def __init__(self, db_connection: SpatialDatabaseConnection) -> None:
        """
        Initialize spatial query engine.
        
        Args:
            db_connection: SpatialDatabaseConnection instance
        """
        self.db = db_connection
        self.srid = SRID_WGS84
    
    def find_nearby_segments(
        self,
        point: Point,
        distance_meters: float,
        material_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[ProximityResult]:
        """
        Find sidewalk segments within specified distance of a point.
        
        Uses ST_DWithin for efficient proximity search with spatial index.
        
        Args:
            point: Shapely Point (lat/lon)
            distance_meters: Search radius in meters
            material_type: Optional filter by material type
            limit: Maximum results to return
            
        Returns:
            List of ProximityResult ordered by distance
            
        Example:
            >>> point = Point(-74.0060, 40.7128)  # NYC center
            >>> results = query.find_nearby_segments(point, 50)  # 50m radius
            >>> for r in results:
            ...     print(f"{r.segment_id}: {r.distance_meters:.2f}m")
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                # Convert to approximate distance in degrees for distance calculation
                # Rough approximation: 1 degree ≈ 111 km at equator
                # More accurate: ST_DWithin uses projected distance
                point_wkt = f"SRID={self.srid};POINT({point.x} {point.y})"
                
                query_parts = [
                    "SELECT segment_id, ",
                    "ST_Distance(geometry, ST_GeomFromText(%s, %s)) * 111000 as distance_m, ",
                    "material_type, condition_score, borough ",
                    "FROM sidewalk_segments ",
                    "WHERE ST_DWithin(geometry, ST_GeomFromText(%s, %s), %s / 111000.0) ",
                ]
                
                params = [
                    point_wkt,
                    self.srid,
                    point_wkt,
                    self.srid,
                    distance_meters,
                ]
                
                if material_type:
                    query_parts.append("AND material_type = %s ")
                    params.append(material_type)
                
                query_parts.extend([
                    "ORDER BY distance_m ASC ",
                    "LIMIT %s"
                ])
                params.append(limit)
                
                query_str = "".join(query_parts)
                cur.execute(query_str, params)
                
                results = []
                for row in cur.fetchall():
                    results.append(
                        ProximityResult(
                            segment_id=row[0],
                            distance_meters=row[1],
                            material_type=row[2],
                            condition_score=row[3],
                            borough=row[4],
                        )
                    )
                
                logger.info(
                    f"Found {len(results)} segments within {distance_meters}m of {point}"
                )
                return results
        
        except Exception as e:
            logger.error(f"Error in find_nearby_segments: {e}")
            return []
    
    def find_segments_in_polygon(
        self,
        polygon: Polygon,
        material_type: Optional[str] = None,
    ) -> list[str]:
        """
        Find all segments that intersect with a polygon.
        
        Uses ST_Intersects for spatial relationship detection.
        
        Args:
            polygon: Shapely Polygon
            material_type: Optional filter by material type
            
        Returns:
            List of segment IDs
            
        Example:
            >>> bounds = Polygon([...])  # Manhattan bounds
            >>> segments = query.find_segments_in_polygon(bounds)
            >>> print(f"Found {len(segments)} segments in polygon")
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                poly_wkt = f"SRID={self.srid};{polygon.wkt}"
                
                query_parts = [
                    "SELECT segment_id FROM sidewalk_segments ",
                    "WHERE ST_Intersects(geometry, ST_GeomFromText(%s, %s)) ",
                ]
                
                params = [poly_wkt, self.srid]
                
                if material_type:
                    query_parts.append("AND material_type = %s ")
                    params.append(material_type)
                
                query_str = "".join(query_parts)
                cur.execute(query_str, params)
                
                segment_ids = [row[0] for row in cur.fetchall()]
                logger.info(f"Found {len(segment_ids)} segments in polygon")
                return segment_ids
        
        except Exception as e:
            logger.error(f"Error in find_segments_in_polygon: {e}")
            return []
    
    def find_adjacent_blocks(self, block_id: str) -> list[str]:
        """
        Find blocks adjacent to (touching) the given block.
        
        Uses ST_Touches for boundary detection.
        
        Args:
            block_id: ID of reference block
            
        Returns:
            List of adjacent block IDs
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                cur.execute(
                    """
                    SELECT b2.block_id
                    FROM blocks b1
                    JOIN blocks b2 ON ST_Touches(b1.geometry, b2.geometry)
                    WHERE b1.block_id = %s
                    """,
                    (block_id,)
                )
                
                adjacent = [row[0] for row in cur.fetchall()]
                logger.info(f"Block {block_id} has {len(adjacent)} adjacent blocks")
                return adjacent
        
        except Exception as e:
            logger.error(f"Error in find_adjacent_blocks: {e}")
            return []
    
    def find_material_zones(
        self,
        material_type: str,
        borough: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Find zones with specific material type using aggregation.
        
        Returns areas where material type is dominant, computed from segments.
        
        Args:
            material_type: Material type to search for
            borough: Optional borough filter
            
        Returns:
            List of zone dictionaries with geometry and stats
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                query_parts = [
                    "SELECT district, COUNT(*) as count, ",
                    "AVG(condition_score) as avg_condition, ",
                    "ST_AsText(ST_Union(geometry)) as geometry_wkt ",
                    "FROM sidewalk_segments ",
                    "WHERE material_type = %s "
                ]
                
                params = [material_type]
                
                if borough:
                    query_parts.append("AND borough = %s ")
                    params.append(borough)
                
                query_parts.append("GROUP BY district")
                
                query_str = "".join(query_parts)
                cur.execute(query_str, params)
                
                zones = []
                for row in cur.fetchall():
                    zones.append({
                        "district": row[0],
                        "segment_count": row[1],
                        "average_condition": row[2],
                        "geometry_wkt": row[3],
                    })
                
                logger.info(f"Found {len(zones)} zones for material {material_type}")
                return zones
        
        except Exception as e:
            logger.error(f"Error in find_material_zones: {e}")
            return []
    
    def measure_distance(
        self,
        segment_id_1: str,
        segment_id_2: str,
    ) -> Optional[float]:
        """
        Measure distance between two segments.
        
        Returns Euclidean distance in meters.
        
        Args:
            segment_id_1: First segment ID
            segment_id_2: Second segment ID
            
        Returns:
            Distance in meters or None if error
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                cur.execute(
                    """
                    SELECT ST_Distance(
                        (SELECT geometry FROM sidewalk_segments WHERE segment_id = %s),
                        (SELECT geometry FROM sidewalk_segments WHERE segment_id = %s)
                    ) * 111000 as distance_m
                    """,
                    (segment_id_1, segment_id_2)
                )
                
                row = cur.fetchone()
                if row:
                    return float(row[0])
        
        except Exception as e:
            logger.error(f"Error measuring distance: {e}")
        
        return None
    
    def measure_area(self, block_id: str) -> Optional[float]:
        """
        Measure area of a block in square meters.
        
        Args:
            block_id: Block ID
            
        Returns:
            Area in square meters or None if error
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                cur.execute(
                    """
                    SELECT ST_Area(geometry::geography) as area_m2
                    FROM blocks
                    WHERE block_id = %s
                    """,
                    (block_id,)
                )
                
                row = cur.fetchone()
                if row:
                    return float(row[0])
        
        except Exception as e:
            logger.error(f"Error measuring area: {e}")
        
        return None
    
    def measure_length(self, segment_id: str) -> Optional[float]:
        """
        Measure length of a segment in meters.
        
        Args:
            segment_id: Segment ID
            
        Returns:
            Length in meters or None if error
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                cur.execute(
                    """
                    SELECT ST_Length(geometry::geography) as length_m
                    FROM sidewalk_segments
                    WHERE segment_id = %s
                    """,
                    (segment_id,)
                )
                
                row = cur.fetchone()
                if row:
                    return float(row[0])
        
        except Exception as e:
            logger.error(f"Error measuring length: {e}")
        
        return None
    
    def buffer_segment(
        self,
        segment_id: str,
        distance_meters: float,
    ) -> Optional[str]:
        """
        Create a buffer zone around a segment.
        
        Returns WKT representation of buffer geometry.
        
        Args:
            segment_id: Segment ID
            distance_meters: Buffer distance in meters
            
        Returns:
            WKT string of buffered geometry or None if error
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                cur.execute(
                    """
                    SELECT ST_AsText(
                        ST_Buffer(geometry::geography, %s)::geometry
                    ) as buffer_wkt
                    FROM sidewalk_segments
                    WHERE segment_id = %s
                    """,
                    (distance_meters, segment_id)
                )
                
                row = cur.fetchone()
                if row:
                    return row[0]
        
        except Exception as e:
            logger.error(f"Error buffering segment: {e}")
        
        return None
    
    def shortest_path(
        self,
        start_segment_id: str,
        end_segment_id: str,
    ) -> list[str]:
        """
        Find shortest path between two segments using network analysis.
        
        Requires street_network table with pgrouting installed.
        For basic implementation, returns segments in geographic proximity.
        
        Args:
            start_segment_id: Starting segment ID
            end_segment_id: Ending segment ID
            
        Returns:
            List of segment IDs forming the path
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                # Get start and end geometries
                cur.execute(
                    """
                    SELECT ST_AsText(geometry) FROM sidewalk_segments 
                    WHERE segment_id = %s
                    """,
                    (start_segment_id,)
                )
                start_geom = cur.fetchone()
                
                cur.execute(
                    """
                    SELECT ST_AsText(geometry) FROM sidewalk_segments 
                    WHERE segment_id = %s
                    """,
                    (end_segment_id,)
                )
                end_geom = cur.fetchone()
                
                if not start_geom or not end_geom:
                    return []
                
                # Simple greedy nearest-neighbor approach
                # In production, use pgRouting for proper network routing
                path = [start_segment_id]
                current_id = start_segment_id
                visited = {start_segment_id}
                
                while current_id != end_segment_id and len(visited) < 100:
                    cur.execute(
                        """
                        SELECT s2.segment_id,
                               ST_Distance(s1.geometry, s2.geometry) * 111000 as dist
                        FROM sidewalk_segments s1
                        JOIN sidewalk_segments s2 ON s1.borough = s2.borough
                        WHERE s1.segment_id = %s
                          AND s2.segment_id NOT IN ({})
                        ORDER BY dist ASC
                        LIMIT 1
                        """.format(
                            ",".join(f"'{sid}'" for sid in visited)
                        ),
                        (current_id,)
                    )
                    
                    result = cur.fetchone()
                    if result:
                        current_id = result[0]
                        path.append(current_id)
                        visited.add(current_id)
                    else:
                        break
                
                logger.info(f"Found path with {len(path)} segments")
                return path
        
        except Exception as e:
            logger.error(f"Error in shortest_path: {e}")
            return []
    
    def segments_by_borough(self) -> list[SpatialAggregation]:
        """
        Get segment statistics aggregated by borough.
        
        Returns:
            List of SpatialAggregation results
        """
        return self._aggregate_segments(["borough"])
    
    def segments_by_district(self) -> list[SpatialAggregation]:
        """
        Get segment statistics aggregated by district.
        
        Returns:
            List of SpatialAggregation results
        """
        return self._aggregate_segments(["district"])
    
    def segments_by_material(self) -> list[SpatialAggregation]:
        """
        Get segment statistics aggregated by material type.
        
        Returns:
            List of SpatialAggregation results
        """
        return self._aggregate_segments(["material_type"], "material_type")
    
    def _aggregate_segments(
        self,
        group_by_cols: list[str],
        primary_category: Optional[str] = None,
    ) -> list[SpatialAggregation]:
        """
        Generic spatial aggregation helper.
        
        Args:
            group_by_cols: Columns to group by
            primary_category: Primary category name
            
        Returns:
            List of SpatialAggregation results
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                group_by = ", ".join(group_by_cols)
                category_col = primary_category or group_by_cols[0]
                
                query = f"""
                    SELECT {category_col},
                           COUNT(*) as count,
                           AVG(condition_score) as avg_condition,
                           SUM(ST_Length(geometry::geography)) as total_length
                    FROM sidewalk_segments
                    GROUP BY {group_by}
                    ORDER BY total_length DESC
                """
                
                cur.execute(query)
                
                results = []
                for row in cur.fetchall():
                    results.append(
                        SpatialAggregation(
                            category=str(row[0]),
                            segment_count=row[1],
                            average_condition=row[2] or 0.0,
                            total_length_meters=row[3] or 0.0,
                        )
                    )
                
                return results
        
        except Exception as e:
            logger.error(f"Error in _aggregate_segments: {e}")
            return []
    
    def inspection_density(
        self,
        polygon: Polygon,
        buffer_meters: int = 100,
    ) -> float:
        """
        Calculate inspection density (inspections per square km) in area.
        
        Args:
            polygon: Area to analyze
            buffer_meters: Optional buffer around polygon
            
        Returns:
            Inspections per square kilometer
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                poly_wkt = f"SRID={self.srid};{polygon.wkt}"
                
                cur.execute(
                    """
                    SELECT COUNT(*) as count,
                           ST_Area(ST_Buffer(geometry::geography, %s)::geometry) / 1000000.0 as area_km2
                    FROM inspections
                    WHERE ST_DWithin(
                        geometry::geography,
                        ST_GeomFromText(%s, %s)::geography,
                        %s
                    )
                    """,
                    (buffer_meters, poly_wkt, self.srid, buffer_meters)
                )
                
                row = cur.fetchone()
                if row and row[1] > 0:
                    return float(row[0]) / float(row[1])
        
        except Exception as e:
            logger.error(f"Error calculating inspection density: {e}")
        
        return 0.0
    
    def condition_statistics(
        self,
        borough: Optional[str] = None,
        material_type: Optional[str] = None,
    ) -> dict[str, float]:
        """
        Get condition statistics for filtered segments.
        
        Args:
            borough: Optional borough filter
            material_type: Optional material type filter
            
        Returns:
            Dictionary with min, max, avg, median condition scores
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                
                query_parts = [
                    "SELECT MIN(condition_score) as min_score, ",
                    "MAX(condition_score) as max_score, ",
                    "AVG(condition_score) as avg_score, ",
                    "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY condition_score) as median_score ",
                    "FROM sidewalk_segments WHERE 1=1 "
                ]
                
                params = []
                
                if borough:
                    query_parts.append("AND borough = %s ")
                    params.append(borough)
                
                if material_type:
                    query_parts.append("AND material_type = %s ")
                    params.append(material_type)
                
                query_str = "".join(query_parts)
                cur.execute(query_str, params)
                
                row = cur.fetchone()
                if row:
                    return {
                        "min": row[0] or 0.0,
                        "max": row[1] or 0.0,
                        "average": row[2] or 0.0,
                        "median": row[3] or 0.0,
                    }
        
        except Exception as e:
            logger.error(f"Error in condition_statistics: {e}")
        
        return {"min": 0.0, "max": 0.0, "average": 0.0, "median": 0.0}
