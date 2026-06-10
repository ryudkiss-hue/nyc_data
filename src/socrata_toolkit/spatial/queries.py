"""
Spatial Query Engine for DuckDB Spatial-backed geographic analysis.

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
from typing import Any

from shapely.geometry import Point, Polygon  # type: ignore[import]

from .database import (
    SRID_WGS84,
    DuckDBSpatialConnection,
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
    borough: str | None = None
    district: str | None = None


class SpatialQuery:
    """
    High-performance spatial query engine for sidewalk data.

    All distances in meters, all areas in square meters.
    Uses DuckDB Spatial ST_* functions for efficient geographic analysis.
    SRID 4326 degree-to-meter approximation: 1 degree ≈ 111,000 meters.
    """

    def __init__(self, db_connection: DuckDBSpatialConnection) -> None:
        """
        Initialize spatial query engine.

        Args:
            db_connection: DuckDBSpatialConnection instance
        """
        self.db = db_connection
        self.srid = SRID_WGS84
        self.deg_to_m = 111000.0

    def find_nearby_segments(
        self,
        point: Point,
        distance_meters: float,
        material_type: str | None = None,
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
        """
        try:
            # Convert point to WKT
            point_wkt = point.wkt
            dist_deg = distance_meters / self.deg_to_m

            query_parts = [
                "SELECT segment_id, ",
                f"ST_Distance(geometry, ST_GeomFromText(?)) * {self.deg_to_m} as distance_m, ",
                "material_type, condition_score, borough ",
                "FROM sidewalk_segments ",
                "WHERE ST_DWithin(geometry, ST_GeomFromText(?), ?) ",
            ]

            params = [
                point_wkt,
                point_wkt,
                dist_deg,
            ]

            if material_type:
                query_parts.append("AND material_type = ? ")
                params.append(material_type)

            query_parts.extend([
                "ORDER BY distance_m ASC ",
                "LIMIT ?"
            ])
            params.append(limit)

            query_str = "".join(query_parts)
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_str, params)
                res = cursor.fetchall()

            results = []
            for row in res:
                results.append(
                    ProximityResult(
                        segment_id=str(row[0]),
                        distance_meters=float(row[1]),
                        material_type=str(row[2]),
                        condition_score=float(row[3]),
                        borough=str(row[4]),
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
        material_type: str | None = None,
    ) -> list[str]:
        """
        Find all segments that intersect with a polygon.

        Args:
            polygon: Shapely Polygon
            material_type: Optional filter by material type

        Returns:
            List of segment IDs
        """
        try:
            poly_wkt = polygon.wkt

            query_parts = [
                "SELECT segment_id FROM sidewalk_segments ",
                "WHERE ST_Intersects(geometry, ST_GeomFromText(?)) ",
            ]

            params = [poly_wkt]

            if material_type:
                query_parts.append("AND material_type = ? ")
                params.append(material_type)

            query_str = "".join(query_parts)
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_str, params)
                res = cursor.fetchall()

            segment_ids = [str(row[0]) for row in res]
            logger.info(f"Found {len(segment_ids)} segments in polygon")
            return segment_ids

        except Exception as e:
            logger.error(f"Error in find_segments_in_polygon: {e}")
            return []

    def find_adjacent_blocks(self, block_id: str) -> list[str]:
        """
        Find blocks adjacent to (touching) the given block.

        Args:
            block_id: ID of reference block

        Returns:
            List of adjacent block IDs
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT b2.block_id
                    FROM blocks b1
                    JOIN blocks b2 ON ST_Touches(b1.geometry, b2.geometry)
                    WHERE b1.block_id = ? AND b2.block_id != ?
                    """,
                    [block_id, block_id]
                )
                res = cursor.fetchall()

            adjacent = [str(row[0]) for row in res]
            logger.info(f"Block {block_id} has {len(adjacent)} adjacent blocks")
            return adjacent

        except Exception as e:
            logger.error(f"Error in find_adjacent_blocks: {e}")
            return []

    def find_material_zones(
        self,
        material_type: str,
        borough: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find zones with specific material type using aggregation.

        Args:
            material_type: Material type to search for
            borough: Optional borough filter

        Returns:
            List of zone dictionaries with geometry and stats
        """
        try:
            query_parts = [
                "SELECT district, COUNT(*) as count, ",
                "AVG(condition_score) as avg_condition, ",
                "ST_AsText(ST_Union_Agg(geometry)) as geometry_wkt ",
                "FROM sidewalk_segments ",
                "WHERE material_type = ? "
            ]

            params = [material_type]

            if borough:
                query_parts.append("AND borough = ? ")
                params.append(borough)

            query_parts.append("GROUP BY district")

            query_str = "".join(query_parts)
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_str, params)
                res = cursor.fetchall()

            zones = []
            for row in res:
                zones.append({
                    "district": str(row[0]),
                    "segment_count": int(row[1]),
                    "average_condition": float(row[2]),
                    "geometry_wkt": str(row[3]),
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
    ) -> float | None:
        """
        Measure distance between two segments.

        Returns Euclidean distance in meters.
        """
        try:
            query = f"""
                SELECT ST_Distance(
                    (SELECT geometry FROM sidewalk_segments WHERE segment_id = ?),
                    (SELECT geometry FROM sidewalk_segments WHERE segment_id = ?)
                ) * {self.deg_to_m} as distance_m
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, [segment_id_1, segment_id_2])
                res = cursor.fetchone()

            if res:
                return float(res[0])

        except Exception as e:
            logger.error(f"Error measuring distance: {e}")

        return None

    def measure_area(self, block_id: str) -> float | None:
        """
        Measure area of a block in square meters.
        """
        try:
            query = f"""
                SELECT ST_Area(geometry) * {self.deg_to_m} * {self.deg_to_m} as area_m2
                FROM blocks
                WHERE block_id = ?
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, [block_id])
                res = cursor.fetchone()

            if res:
                return float(res[0])

        except Exception as e:
            logger.error(f"Error measuring area: {e}")

        return None

    def measure_length(self, segment_id: str) -> float | None:
        """
        Measure length of a segment in meters.
        """
        try:
            query = f"""
                SELECT ST_Length(geometry) * {self.deg_to_m} as length_m
                FROM sidewalk_segments
                WHERE segment_id = ?
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, [segment_id])
                res = cursor.fetchone()

            if res:
                return float(res[0])

        except Exception as e:
            logger.error(f"Error measuring length: {e}")

        return None

    def buffer_segment(
        self,
        segment_id: str,
        distance_meters: float,
    ) -> str | None:
        """
        Create a buffer zone around a segment.
        """
        try:
            dist_deg = distance_meters / self.deg_to_m
            query = """
                SELECT ST_AsText(ST_Buffer(geometry, ?)) as buffer_wkt
                FROM sidewalk_segments
                WHERE segment_id = ?
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, [dist_deg, segment_id])
                res = cursor.fetchone()

            if res:
                return str(res[0])

        except Exception as e:
            logger.error(f"Error buffering segment: {e}")

        return None

    def shortest_path(
        self,
        start_segment_id: str,
        end_segment_id: str,
    ) -> list[str]:
        """
        Find shortest path between two segments using simple geographic greedy search.
        """
        try:
            # Get start and end geometries
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT ST_AsText(geometry) FROM sidewalk_segments WHERE segment_id = ?",
                    [start_segment_id]
                )
                start_row = cursor.fetchone()

                cursor.execute(
                    "SELECT ST_AsText(geometry) FROM sidewalk_segments WHERE segment_id = ?",
                    [end_segment_id]
                )
                end_row = cursor.fetchone()

            if not start_row or not end_row:
                return []

            path = [start_segment_id]
            current_id = start_segment_id
            visited = {start_segment_id}

            while current_id != end_segment_id and len(visited) < 100:
                visited_list = ", ".join(f"'{sid}'" for sid in visited)
                query = f"""
                    SELECT s2.segment_id,
                           ST_Distance(s1.geometry, s2.geometry) * {self.deg_to_m} as dist
                    FROM sidewalk_segments s1
                    JOIN sidewalk_segments s2 ON s1.borough = s2.borough
                    WHERE s1.segment_id = ?
                      AND s2.segment_id NOT IN ({visited_list})
                    ORDER BY dist ASC
                    LIMIT 1
                """
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, [current_id])
                    res = cursor.fetchone()

                if res:
                    current_id = str(res[0])
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
        """Get statistics aggregated by borough."""
        return self._aggregate_segments(["borough"])

    def segments_by_district(self) -> list[SpatialAggregation]:
        """Get statistics aggregated by district."""
        return self._aggregate_segments(["district"])

    def segments_by_material(self) -> list[SpatialAggregation]:
        """Get statistics aggregated by material type."""
        return self._aggregate_segments(["material_type"], "material_type")

    def _aggregate_segments(
        self,
        group_by_cols: list[str],
        primary_category: str | None = None,
    ) -> list[SpatialAggregation]:
        """Generic spatial aggregation helper."""
        try:
            group_by = ", ".join(group_by_cols)
            category_col = primary_category or group_by_cols[0]

            query = f"""
                SELECT {category_col},
                       COUNT(*) as count,
                       AVG(condition_score) as avg_condition,
                       SUM(ST_Length(geometry)) * {self.deg_to_m} as total_length
                FROM sidewalk_segments
                GROUP BY {group_by}
                ORDER BY total_length DESC
            """

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                res = cursor.fetchall()

            results = []
            for row in res:
                results.append(
                    SpatialAggregation(
                        category=str(row[0]),
                        segment_count=int(row[1]),
                        average_condition=float(row[2]) if row[2] is not None else 0.0,
                        total_length_meters=float(row[3]) if row[3] is not None else 0.0,
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
        """Calculate inspection density (inspections per square km) in area."""
        try:
            poly_wkt = polygon.wkt
            buff_deg = buffer_meters / self.deg_to_m

            # Area in sq km: area_sq_deg * deg_to_m^2 / 1,000,000
            area_scale = (self.deg_to_m * self.deg_to_m) / 1000000.0

            query = f"""
                SELECT COUNT(*) as count,
                       ST_Area(ST_Buffer(ST_GeomFromText(?), ?)) * {area_scale} as area_km2
                FROM inspections
                WHERE ST_DWithin(
                    geometry,
                    ST_GeomFromText(?),
                    ?
                )
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, [poly_wkt, buff_deg, poly_wkt, buff_deg])
                res = cursor.fetchone()

            if res and res[1] > 0:
                return float(res[0]) / float(res[1])

        except Exception as e:
            logger.error(f"Error calculating inspection density: {e}")

        return 0.0

    def condition_statistics(
        self,
        borough: str | None = None,
        material_type: str | None = None,
    ) -> dict[str, float]:
        """Get condition statistics for filtered segments."""
        try:
            query_parts = [
                "SELECT MIN(condition_score) as min_score, ",
                "MAX(condition_score) as max_score, ",
                "AVG(condition_score) as avg_score, ",
                "quantile_cont(condition_score, 0.5) as median_score ",
                "FROM sidewalk_segments WHERE 1=1 "
            ]

            params = []

            if borough:
                query_parts.append("AND borough = ? ")
                params.append(borough)

            if material_type:
                query_parts.append("AND material_type = ? ")
                params.append(material_type)

            query_str = "".join(query_parts)
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_str, params)
                res = cursor.fetchone()

            if res:
                return {
                    "min": float(res[0]) if res[0] is not None else 0.0,
                    "max": float(res[1]) if res[1] is not None else 0.0,
                    "average": float(res[2]) if res[2] is not None else 0.0,
                    "median": float(res[3]) if res[3] is not None else 0.0,
                }

        except Exception as e:
            logger.error(f"Error in condition_statistics: {e}")

        return {"min": 0.0, "max": 0.0, "average": 0.0, "median": 0.0}
