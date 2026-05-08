from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class SpatialJoinResult:
    joined: pd.DataFrame
    conflict_rate: float
    overlap_count: int


def _to_geom(value: Any):
    try:
        from shapely.geometry import shape
        from shapely import wkt
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
