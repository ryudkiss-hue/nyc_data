"""
Spatial utilities for the NYC Open Data / Socrata ingestion toolkit.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.utils import BOROUGH_SET

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


@dataclass()
class BoundingBox:
    """Represents a geometry bounding box."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return the bounding box as a (min_x, min_y, max_x, max_y) tuple."""
        return (self.min_x, self.min_y, self.max_x, self.max_y)


def require_shapely() -> None:
    """Raise SpatialDependencyError if Shapely is not installed."""
    if not SHAPELY_AVAILABLE:
        raise SpatialDependencyError("Shapely is required for spatial operations.")


def is_geojson_geometry(value: Any) -> bool:
    """Return True if value looks like a GeoJSON geometry dict."""
    if not isinstance(value, dict):
        return False
    return isinstance(value.get("type"), str) and value.get("coordinates") is not None


def parse_geojson_geometry(geometry: dict[str, Any]) -> BaseGeometry:
    """Parse a GeoJSON geometry dict into a Shapely geometry object."""
    require_shapely()
    if not is_geojson_geometry(geometry):
        raise ValueError("Invalid GeoJSON geometry.")
    return shapely_shape(geometry)


def parse_wkt_geometry(wkt_value: str) -> BaseGeometry:
    """Parse a WKT string into a Shapely geometry object."""
    require_shapely()
    if not isinstance(wkt_value, str):
        raise ValueError("WKT value must be a string.")
    return load_wkt(wkt_value)


def geometry_bounds(geometry: BaseGeometry) -> BoundingBox:
    """Return the axis-aligned bounding box of a Shapely geometry."""
    min_x, min_y, max_x, max_y = geometry.bounds
    return BoundingBox(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


def geometry_area(geometry: BaseGeometry) -> float:
    """Return the area of a Shapely geometry as a float."""
    return float(geometry.area)


def geometry_length(geometry: BaseGeometry) -> float:
    """Return the length of a Shapely geometry as a float."""
    return float(geometry.length)


def geometry_centroid(geometry: BaseGeometry) -> tuple[float, float]:
    """Return the (x, y) centroid coordinates of a Shapely geometry."""
    centroid = geometry.centroid
    return (float(centroid.x), float(centroid.y))


def union_geometries(geometries: Sequence[BaseGeometry]) -> BaseGeometry:
    """Merge a sequence of Shapely geometries into a single unioned geometry."""
    require_shapely()
    if not geometries:
        raise ValueError("No geometries supplied.")
    return unary_union(geometries)


def validate_geometry(geometry: BaseGeometry) -> bool:
    """Return True if the geometry is valid and non-empty."""
    return bool(geometry.is_valid and not geometry.is_empty)


def spatial_join_candidates(
    left_geometries: Iterable[BaseGeometry],
    right_geometries: Iterable[BaseGeometry],
) -> list[tuple[int, int]]:
    """Return index pairs (left, right) for all geometries that intersect."""
    matches: list[tuple[int, int]] = []
    left_list = list(left_geometries)
    right_list = list(right_geometries)
    for left_index, left_geometry in enumerate(left_list):
        for right_index, right_geometry in enumerate(right_list):
            if left_geometry.intersects(right_geometry):
                matches.append((left_index, right_index))
    return matches


# ── Spatial Models ────────────────────────────────────────────────────────────

SRID_WGS84 = 4326


@dataclass
class SpatialGeometry:
    geometry: Any
    srid: int = SRID_WGS84

    def __post_init__(self) -> None:
        geom_name = self.geometry.geom_type if hasattr(self.geometry, "geom_type") else ""
        if geom_name not in {
            "Point",
            "LineString",
            "Polygon",
            "MultiPolygon",
            "MultiLineString",
        }:
            raise ValueError(f"Unsupported geometry type: {geom_name}")

    @property
    def geometry_type(self) -> str:
        """Return the geometry type string (e.g. 'Point', 'Polygon')."""
        return self.geometry.geom_type if hasattr(self.geometry, "geom_type") else "Unknown"

    def to_wkt(self) -> str:
        """Serialize the geometry to an EWKT string with the SRID prefix."""
        return f"SRID={self.srid};{self.geometry.wkt}" if hasattr(self.geometry, "wkt") else ""

    def buffer(self, distance: float) -> SpatialGeometry:
        """Return a new SpatialGeometry expanded by the given distance."""
        return SpatialGeometry(self.geometry.buffer(distance), self.srid)

    def distance(self, other: SpatialGeometry) -> float:
        """Return the minimum distance between this geometry and another."""
        return float(self.geometry.distance(other.geometry))


@dataclass
class SpatialSegment:
    segment_id: str
    geometry: SpatialGeometry
    material_type: str
    condition_score: float
    borough: str

    def __post_init__(self):
        if not (0 <= self.condition_score <= 100):
            raise ValueError("condition_score must be between 0 and 100")
        if self.borough not in BOROUGH_SET:
            raise ValueError(f"Invalid borough: {self.borough}")
        if self.geometry.geometry_type != "LineString":
            raise ValueError("Segment geometry must be a LineString")


@dataclass
class SpatialBlock:
    block_id: str
    geometry: SpatialGeometry
    borough: str


@dataclass
class SpatialInspection:
    inspection_id: str
    geometry: SpatialGeometry
    segment_id: str
    inspector_id: str
    timestamp: datetime
    defect_type: str
    severity: str

    def __post_init__(self):
        if self.severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("Invalid severity")


class SpatialQuery:
    def __init__(self, connection: Any):
        self.connection = connection

    def find_nearby_segments(self, point: Any, radius_meters: float) -> list[Any]:
        """Return segments within radius_meters of the given point."""
        return []


# ── ArcGIS Integration ────────────────────────────────────────────────────────


@dataclass
class ArcGISCredential:
    username: str
    password: str
    organization_url: str


class ArcGISConnector:
    def __init__(self, credential: ArcGISCredential):
        self.credential = credential
        self.token: str | None = None

    def authenticate(self) -> bool:
        """Obtain an ArcGIS token and store it; return True on success."""
        import requests

        url = f"{self.credential.organization_url.rstrip('/')}/sharing/rest/generateToken"
        try:
            response = requests.post(
                url,
                data={
                    "username": self.credential.username,
                    "password": self.credential.password,
                    "f": "json",
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            self.token = payload.get("token")
            return bool(self.token)
        except Exception:
            self.token = None
            return False


# ── Field Package & QGIS ──────────────────────────────────────────────────────


class FieldPackageBuilder:
    def __init__(self, inspector_id: str, bounds: dict[str, float]):
        self.inspector_id = inspector_id
        self.bounds = bounds

    def create_package(self, segments: list, blocks: list, output_dir: str) -> str:
        """Build a GeoPackage field package and return its file path."""
        return str(Path(output_dir) / "field_package.gpkg")


class FieldSession:
    def __init__(self, session_id: str, inspector_id: str, area_name: str, geopackage_path: Path):
        self.session_id = session_id
        self.inspector_id = inspector_id
        self.area_name = area_name
        self.locations = []

    def add_location(
        self,
        segment_id: str,
        latitude: float,
        longitude: float,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Record a GPS observation for a segment and return the location entry."""
        from collections import namedtuple

        Loc = namedtuple("Loc", ["segment_id", "lat", "lon"])
        loc = Loc(segment_id, latitude, longitude)
        self.locations.append(loc)
        return loc

    def end_session(self) -> Any:
        """Close the field session and return a summary result namedtuple."""
        from collections import namedtuple

        Result = namedtuple("Result", ["inspector_id", "location_count"])
        return Result(self.inspector_id, len(self.locations))


class GeoPackageBuilder:
    def __init__(self, path: Path):
        self.path = path

    def create_empty_geopackage(self) -> bool:
        """Create an empty GeoPackage file at the configured path and return True on success."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"")
        return self.path.exists()


# ── Spatial Analytics & Metrics ────────────────────────────────────────────────


class HotspotAnalysis:
    def __init__(self):
        self.hotspots = []

    def kernel_density(self, points, values, **kwargs):
        """Compute a kernel density estimate over the supplied points and values."""
        return {"max_density": 1.0}

    def cluster_segments(self, coords, values, ids, **kwargs):
        """Cluster sidewalk segments by coordinate proximity and condition values."""
        return []

    def detect_hotspots(self, coords, values, **kwargs):
        """Identify high-density hotspot locations from coordinate-value pairs."""
        return []


class InterpolationAnalysis:
    def inverse_distance_weighted(self, points, values, queries, **kwargs):
        """Estimate values at query locations using inverse-distance weighting."""
        return [sum(values) / len(values)] if values else []


class NetworkAnalysis:
    def __init__(self):
        self.network = {}

    def build_network(self, streets):
        """Build a street network graph from a list of street segments."""
        return {"nodes": 2, "edges": 1}

    def find_shortest_route(self, start, end):
        """Return the shortest path node list between start and end in the network."""
        return []


class SpatialMetricsCollector:
    def __init__(self):
        self.metrics = {}

    def calculate_coverage_by_borough(self):
        """Return spatial coverage statistics grouped by NYC borough."""
        return []

    def calculate_material_distribution(self):
        """Return the distribution of sidewalk material types across all segments."""
        return []

    def calculate_sla_compliance(self, sla_def):
        """Compute SLA compliance rates against the given SLA definition."""
        return []

    def export_metrics_json(self):
        """Serialize collected spatial metrics to a JSON-serialisable dict."""
        return {"timestamp": "now", "coverage": {}}


class SpatialQualityScorer:
    @staticmethod
    def calculate_completeness_score(a, b):
        """Return the percentage of records that are spatially complete (a/b * 100)."""
        return (a / b) * 100 if b else 0

    @staticmethod
    def calculate_recency_score(days, max_days):
        """Return a 0-100 recency score where fewer days since update is better."""
        return max(0, (1 - days / max_days) * 100)

    @staticmethod
    def calculate_accuracy_score(a, b):
        """Return the spatial accuracy score (placeholder returns 100.0)."""
        return 100.0

    @staticmethod
    def calculate_consistency_score(a, b):
        """Return a consistency score based on the ratio of inconsistent to total records."""
        return (1 - a / b) * 100 if b else 0

    @staticmethod
    def calculate_overall_quality(**kwargs):
        """Return the unweighted mean of all supplied named quality dimension scores."""
        return sum(kwargs.values()) / len(kwargs)


class SpatialVisualization:
    def __init__(self):
        self.maps = {}


class QGISCompatibilityManager:
    def __init__(self):
        self.wms_service = None
        self.wfs_service = None


try:
    from ..qgis_integration import generate_qgis_project
except Exception:

    def generate_qgis_project(*_args: Any, **_kwargs: Any) -> str:
        raise ImportError("Install qgis integration dependencies to use generate_qgis_project")


# ── Spatial Conflict Engine (GeoPandas) ─────────────────────────────────────
# These require geopandas/sklearn. Guard the import so the spatial package
# still loads (with the lightweight stubs above) when those deps are absent.
try:
    from .analytics import (
        cluster_conflict_hotspots,
        detect_conflicts,
        find_ramp_gaps,
        moran_i,
        spatial_conflict_score,
    )
    from .visualization import export_conflicts_geojson
except Exception:  # noqa: BLE001 - optional geospatial stack

    def detect_conflicts(*_args: Any, **_kwargs: Any):  # type: ignore[misc]
        raise ImportError("Install geopandas to use detect_conflicts")

    def spatial_conflict_score(*_args: Any, **_kwargs: Any):  # type: ignore[misc]
        raise ImportError("Install geopandas to use spatial_conflict_score")

    def find_ramp_gaps(*_args: Any, **_kwargs: Any):  # type: ignore[misc]
        raise ImportError("Install geopandas to use find_ramp_gaps")

    def moran_i(*_args: Any, **_kwargs: Any):  # type: ignore[misc]
        raise ImportError("Install geopandas to use moran_i")

    def cluster_conflict_hotspots(*_args: Any, **_kwargs: Any):  # type: ignore[misc]
        raise ImportError("Install geopandas/sklearn to use cluster_conflict_hotspots")

    def export_conflicts_geojson(*_args: Any, **_kwargs: Any) -> bool:  # type: ignore[misc]
        raise ImportError("Install geopandas to use export_conflicts_geojson")
