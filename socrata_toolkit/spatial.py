from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from shapely.geometry import shape, Point
    from shapely.ops import unary_union
    import shapely.wkt as wkt
except ImportError:
    shape = None
    Point = None
    unary_union = None
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
        kmeans = KMeans(n_clusters=n_clusters, n_init=10)
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

def spatial_intersects_join(left: pd.DataFrame, right: pd.DataFrame, left_geom: str, right_geom: str) -> pd.DataFrame:
    """Perform a spatial intersection join between two DataFrames."""
    if shape is None: raise ImportError("Install shapely for spatial support.")
    
    left_geoms = left[left_geom].map(_to_geom)
    right_geoms = right[right_geom].map(_to_geom)
    
    rows = []
    for li, lg in left_geoms.items():
        if lg is None: continue
        for ri, rg in right_geoms.items():
            if rg is None: continue
            if lg.intersects(rg):
                rows.append({**left.iloc[li].to_dict(), **right.iloc[ri].to_dict()})
    return pd.DataFrame(rows)

# ── DuckDB Spatial Helpers ───────────────────────────────────────────────────

def ensure_spatial_table(conn: Any, table_name: str, lat_col: str, lon_col: str):
    """Adds a geometry column to a DuckDB table based on lat/lon."""
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS geom GEOMETRY;")
    conn.execute(f"UPDATE {table_name} SET geom = ST_Point({lon_col}, {lat_col}) WHERE geom IS NULL;")
