# coding=utf-8
"""
Spatial utilities for the NYC Open Data / Socrata ingestion toolkit.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

try:
    from shapely.geometry import shape as shapely_shape
    from shapely.geometry.base import BaseGeometry
    from shapely.ops import unary_union
    from shapely.wkt import loads as load_wkt
    SHAPELY_AVAILABLE = True
except ImportError:
    shapely_shape = None
    BaseGeometry = object
    unary_union = None
    load_wkt = None
    SHAPELY_AVAILABLE = False

class SpatialDependencyError(ImportError):
    """Raised when a spatial operation requires Shapely."""

@dataclass(slots=True)
class BoundingBox:
    """Represents a geometry bounding box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.min_x, self.min_y, self.max_x, self.max_y)

def require_shapely() -> None:
    if not SHAPELY_AVAILABLE:
        raise SpatialDependencyError("Shapely is required for spatial operations.")

def is_geojson_geometry(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return isinstance(value.get("type"), str) and value.get("coordinates") is not None

def parse_geojson_geometry(geometry: dict[str, Any]) -> BaseGeometry:
    require_shapely()
    if not is_geojson_geometry(geometry):
        raise ValueError("Invalid GeoJSON geometry.")
    return shapely_shape(geometry)

def parse_wkt_geometry(wkt_value: str) -> BaseGeometry:
    require_shapely()
    if not isinstance(wkt_value, str):
        raise ValueError("WKT value must be a string.")
    return load_wkt(wkt_value)

def geometry_bounds(geometry: BaseGeometry) -> BoundingBox:
    min_x, min_y, max_x, max_y = geometry.bounds
    return BoundingBox(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)

def geometry_area(geometry: BaseGeometry) -> float:
    return float(geometry.area)

def geometry_length(geometry: BaseGeometry) -> float:
    return float(geometry.length)

def geometry_centroid(geometry: BaseGeometry) -> tuple[float, float]:
    centroid = geometry.centroid
    return (float(centroid.x), float(centroid.y))

def union_geometries(geometries: Sequence[BaseGeometry]) -> BaseGeometry:
    require_shapely()
    if not geometries:
        raise ValueError("No geometries supplied.")
    return unary_union(geometries)

def validate_geometry(geometry: BaseGeometry) -> bool:
    return bool(geometry.is_valid and not geometry.is_empty)

def spatial_join_candidates(
    left_geometries: Iterable[BaseGeometry],
    right_geometries: Iterable[BaseGeometry],
) -> list[tuple[int, int]]:
    matches: list[tuple[int, int]] = []
    left_list = list(left_geometries)
    right_list = list(right_geometries)
    for left_index, left_geometry in enumerate(left_list):
        for right_index, right_geometry in enumerate(right_list):
            if left_geometry.intersects(right_geometry):
                matches.append((left_index, right_index))
    return matches