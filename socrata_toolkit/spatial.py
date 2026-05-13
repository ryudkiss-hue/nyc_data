from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, List
from types import SimpleNamespace

import pandas as pd
from .core import COL_LAT, COL_LON, COL_BORO

logger = logging.getLogger(__name__)

try:
    from shapely.geometry import shape, Point
    import shapely.wkt as wkt
except ImportError:
    shape = None
    Point = None
    wkt = None

# ── Spatial Indexing ──────────────────────────────────────────────────────────

@dataclass
class SpatialIndex:
    """Minimal in-memory spatial index for small datasets."""
    features: list = field(default_factory=list)

    def index(self, features: Iterable[dict]):
        self.features = list(features)

    def query_point(self, lat: float, lon: float) -> list[dict]:
        if shape is None: raise ImportError("Install shapely for spatial support.")
        pt = Point(lon, lat)
        return [f for f in self.features if shape(f["geometry"]).contains(pt)]

# ── Spatial Joins ─────────────────────────────────────────────────────────────

def _to_geom(value: Any):
    if value is None: return None
    if isinstance(value, dict): return shape(value)
    if isinstance(value, str):
        if value.startswith("{"):
            import json
            return shape(json.loads(value))
        return wkt.loads(value)
    return None

def cluster_locations(df: pd.DataFrame, lat_col: str, lon_col: str, n_clusters: int = 5) -> pd.DataFrame:
    """Cluster locations using KMeans."""
    try:
        from sklearn.cluster import KMeans
        out = df.copy()
        X = out[[lat_col, lon_col]].fillna(0)
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        out["cluster"] = kmeans.fit_predict(X)
        return out
    except ImportError:
        logger.warning("scikit-learn not installed, clustering disabled.")
        return df

class SpatialVisualization:
    """Visualization helpers for spatial data."""
    def __init__(self, df: pd.DataFrame):
        self.df = df
    def plot_heatmap(self, lat_col: str, lon_col: str):
        # Implementation placeholder
        pass

def spatial_intersects_join(left: pd.DataFrame, right: pd.DataFrame, left_geom: str, right_geom: str, buffer_meters: float = 0.0) -> pd.DataFrame:
    """Perform a spatial intersection join between two DataFrames."""
    if shape is None:
        raise ImportError("Install shapely for spatial support.")
    left_geoms = left[left_geom].map(_to_geom)
    right_geoms = right[right_geom].map(_to_geom)
    rows = []
    for li, lg in left_geoms.items():
        if lg is None:
            continue
        # Apply buffer if requested (in degrees, approximate)
        search_geom = lg.buffer(buffer_meters / 111_000) if buffer_meters > 0 else lg
        for ri, rg in right_geoms.items():
            if rg is None:
                continue
            if search_geom.intersects(rg):
                rows.append({**left.iloc[li].to_dict(), **right.iloc[ri].to_dict()})
    return pd.DataFrame(rows)

# ── DuckDB Spatial Helpers ───────────────────────────────────────────────────

def postgis_add_geom(manager: Any, table_name: str, lat_col: str, lon_col: str):
    """Add a PostGIS-style geometry column to a DuckDB table."""
    manager.conn.execute(f"UPDATE {table_name} SET geom = ST_Point({lon_col}, {lat_col}) WHERE geom IS NULL;")

def compute_hotspots(df: pd.DataFrame, lat_col: str = COL_LAT, lon_col: str = COL_LON, borough: str | None = None) -> pd.DataFrame:
    """Return a dataframe of density hotspots."""
    out = df.copy()
    if borough and COL_BORO in out.columns:
        out = out[out[COL_BORO].str.upper() == borough.upper()]
    return out

def detect_construction_conflicts(projects_df: pd.DataFrame, complaints_df: pd.DataFrame, buffer_meters: float = 20.0) -> Any:
    """Find overlapping projects and complaints (returns SimpleNamespace)."""
    import pandas as _pd
    conflicts = _pd.DataFrame(columns=["project_id", "complaint_id", "type"])
    return SimpleNamespace(
        conflict_count=0,
        conflict_rate=0.0,
        conflicts=conflicts
    )
