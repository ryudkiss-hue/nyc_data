from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

"""Lightweight local spatial helpers using Shapely.

This module provides a tiny in-memory spatial index and proximity utilities
useful for development and unit tests where PostGIS is not available. For
production-scale spatial joins prefer the PostGISConflictResolver in
`conflict.py` which delegates heavy lifting to the database.
"""

try:
    from shapely.geometry import shape
    from shapely.ops import unary_union
except Exception:  # pragma: no cover - optional dependency
    shape = None
    unary_union = None

@dataclass
class SpatialIndex:
    """A minimal in-memory spatial index backed by a list of GeoJSON-like features.

    Notes:
    - This is intentionally simple and not optimized. It's suitable for test
      scenarios and small datasets only.
    - Each feature is expected to have a `geometry` key compatible with
      Shapely's `shape()` constructor.
    """
    features: list

    def index(self, features: Iterable[dict]):
        self.features = list(features)

    def query_point(self, pt):
        """Return features that contain the given Shapely point.

        Args:
            pt: a Shapely Point to test

        Returns:
            list of feature dicts that contain the point
        """
        hits = []
        if shape is None:
            raise ImportError("Install shapely to use SpatialIndex: pip install shapely")
        for f in self.features:
            if shape(f["geometry"]).contains(pt):
                hits.append(f)
        return hits

@dataclass
class SpatialJoinResult:
    joined: pd.DataFrame
    conflict_rate: float
    overlap_count: int

def _to_geom(value: Any):
    try:
        from shapely import wkt
        from shapely.geometry import shape
    except ImportError as exc:
        raise ImportError("Install geospatial support: pip install shapely") from exc

    if value is None:
        return None
    if isinstance(value, dict):
        return shape(value)
    value = str(value).strip()
    if not value:
        return None
    if value.startswith("{"):
        import json

        return shape(json.loads(value))
    return wkt.loads(value)

def spatial_intersects_join(left: pd.DataFrame, right: pd.DataFrame, left_geom_col: str, right_geom_col: str) -> SpatialJoinResult:
    left_cp = left.copy()
    right_cp = right.copy()
    left_cp["_geom_left"] = left_cp[left_geom_col].map(_to_geom)
    right_cp["_geom_right"] = right_cp[right_geom_col].map(_to_geom)

    rows = []
    overlap = 0
    for li, lrow in left_cp.iterrows():
        lg = lrow["_geom_left"]
        found = False
        if lg is None:
            continue
        for ri, rrow in right_cp.iterrows():
            rg = rrow["_geom_right"]
            if rg is None:
                continue
            if lg.intersects(rg):
                found = True
                overlap += 1
                rows.append({**{f"left_{k}": v for k, v in lrow.items()}, **{f"right_{k}": v for k, v in rrow.items()}})
        if not found:
            rows.append({**{f"left_{k}": v for k, v in lrow.items()}})

    out_df = pd.DataFrame(rows)
    conflict_rate = (overlap / len(left_cp)) if len(left_cp) else 0.0
    return SpatialJoinResult(joined=out_df, conflict_rate=conflict_rate, overlap_count=overlap)
