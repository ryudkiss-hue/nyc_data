"""
Centralized Socrata ingestion for Manhattan Mission Control.

Uses sodapy with Streamlit caching (24h TTL). Normalizes BBL keys and builds
GeoDataFrames in EPSG:2263 (NYC State Plane, US feet) when geometry is available.
"""

from __future__ import annotations

import logging
import os
import re
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

warnings.filterwarnings("ignore", message=".*app_token.*", module="sodapy")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sodapy")
logging.getLogger("sodapy").setLevel(logging.ERROR)

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore

try:
    from sodapy import Socrata
except ImportError:
    Socrata = None  # type: ignore

try:
    import geopandas as gpd
    from shapely.geometry import Point
except ImportError:
    gpd = None  # type: ignore
    Point = None  # type: ignore

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _bootstrap_env() -> None:
    """Load .env and .env.socrata from repo root when python-dotenv is available."""
    if load_dotenv is None:
        return
    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(_REPO_ROOT / ".env.socrata", override=False)


_bootstrap_env()

DOMAIN = os.getenv("SOCRATA_DOMAIN", "data.cityofnewyork.us")
CACHE_TTL_SECONDS = 86_400  # 24 hours
NYC_CRS = "EPSG:2263"
WGS84 = "EPSG:4326"

# Map layers: Manhattan-filtered Socrata pulls (fourfour → registry key)
MANHATTAN_MAP_KEYS = ("inspection", "street_permits")

# 15 mandatory endpoints (fourfour → logical key)
DATASET_REGISTRY: dict[str, dict[str, str]] = {
    # Core SMD
    "inspection": {
        "fourfour": "dntt-gqwq",
        "group": "core_smd",
        "label": "SMD Inspection",
        "manhattan_where": "upper(borough) = 'MANHATTAN'",
    },
    "violations": {"fourfour": "6kbp-uz6m", "group": "core_smd", "label": "SMD Violations"},
    "built": {"fourfour": "ugc8-s3f6", "group": "core_smd", "label": "SMD Built"},
    "lot_info": {"fourfour": "i642-2fxq", "group": "core_smd", "label": "SMD Lot Info"},
    "reinspection": {"fourfour": "gx72-kirf", "group": "core_smd", "label": "SMD ReInspection"},
    "tree_damage": {"fourfour": "j6v2-6uxq", "group": "core_smd", "label": "All Tree Damage"},
    # Accessibility
    "ramp_locations": {"fourfour": "ufzp-rrqu", "group": "accessibility", "label": "Pedestrian Ramp Locations"},
    "ramp_complaints": {"fourfour": "jagj-gttd", "group": "accessibility", "label": "Ramp Complaints"},
    "ramp_progress": {"fourfour": "e7gc-ub6z", "group": "accessibility", "label": "Ramp Program Progress"},
    # Coordination
    "street_permits": {
        "fourfour": "tqtj-sjs8",
        "group": "coordination",
        "label": "Street Construction Permits",
        "manhattan_where": "upper(borough) = 'MANHATTAN' OR upper(permittee_s_borough) = 'MANHATTAN'",
    },
    "weekly_construction": {"fourfour": "r528-jcks", "group": "coordination", "label": "Weekly Construction Schedule"},
    "capital_blocks": {"fourfour": "jvk9-k4re", "group": "coordination", "label": "Capital Reconstruction Blocks"},
    # Overlays
    "sidewalk_planimetric": {"fourfour": "vfx9-tbb6", "group": "overlays", "label": "Planimetric Sidewalks"},
    "pedestrian_demand": {"fourfour": "fwpa-qxaf", "group": "overlays", "label": "Pedestrian Demand"},
    "mappluto": {"fourfour": "6fi9-q3ta", "group": "overlays", "label": "MapPLUTO"},
    "complaints_311": {"fourfour": "erm2-nwe9", "group": "overlays", "label": "311 Sidewalk/Curb"},
}

BBL_CANDIDATES = ("bbl", "lot_bbl", "tax_lot", "taxblock", "boro_block_lot")
LAT_CANDIDATES = ("latitude", "lat", "y", "ycoord")
LON_CANDIDATES = ("longitude", "lon", "lng", "long", "x", "xcoord")
DATE_CANDIDATES = ("created_date", "created", "date", "open_date", "requested_datetime")
OWNER_CANDIDATES = ("owner", "owner_type", "ownership", "lot_owner", "agency")
GRACE_CANDIDATES = ("grace_pd", "grace_period", "grace_date", "graceperiod")


def _require_sodapy() -> None:
    if Socrata is None:
        raise ImportError(
            "sodapy is required for Mission Control. Install with: "
            "pip install -e \".[mission]\""
        )


def get_socrata_client() -> Any:
    """
    Build sodapy client using env auth:
      SOCRATA_APP_TOKEN, SOCRATA_KEY_ID, SOCRATA_KEY_SECRET
    (key id/secret map to sodapy username/password).
    """
    _require_sodapy()
    token = (os.getenv("SOCRATA_APP_TOKEN") or "").strip() or None
    username = (os.getenv("SOCRATA_KEY_ID") or os.getenv("SOCRATA_USERNAME") or "").strip() or None
    password = (os.getenv("SOCRATA_KEY_SECRET") or os.getenv("SOCRATA_PASSWORD") or "").strip() or None
    return Socrata(DOMAIN, token, username=username, password=password, timeout=90)


def normalize_bbl(series: pd.Series) -> pd.Series:
    """Strip non-digits and zero-pad to 10-digit BBL when possible."""
    s = series.astype(str).str.replace(r"\D", "", regex=True)
    s = s.where(s.str.len() >= 6, other=pd.NA)
    return s.str.zfill(10)


def pick_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for col in df.columns:
        if any(cand in col.lower() for cand in candidates):
            return col
    return None


def _cache_decorator():
    if st is not None:
        return st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Fetching from Socrata…")
    return lambda f: f  # no-op when not in Streamlit


def _postprocess_dataset(dataset_key: str, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    meta = DATASET_REGISTRY[dataset_key]
    df = df.copy()
    df["_dataset_key"] = dataset_key
    df["_fourfour"] = meta["fourfour"]
    bbl_col = pick_column(df, BBL_CANDIDATES)
    if bbl_col:
        df["_bbl"] = normalize_bbl(df[bbl_col])
    return df


@_cache_decorator()
def fetch_dataset(dataset_key: str, *, limit: int = 50_000, where: str | None = None) -> pd.DataFrame:
    """Fetch one registry dataset; returns normalized DataFrame with `_bbl` when possible."""
    if dataset_key not in DATASET_REGISTRY:
        raise KeyError(f"Unknown dataset_key: {dataset_key}")
    meta = DATASET_REGISTRY[dataset_key]
    client = get_socrata_client()
    kwargs: dict[str, Any] = {"limit": limit}
    if where:
        kwargs["where"] = where
    rows = client.get(meta["fourfour"], **kwargs)
    return _postprocess_dataset(dataset_key, pd.DataFrame.from_records(rows))


@_cache_decorator()
def fetch_manhattan_map_layer(dataset_key: str, *, limit: int = 25_000) -> pd.DataFrame:
    """
    Manhattan-filtered pull for map layers (dntt-gqwq inspection, tqtj-sjs8 permits).
    Falls back to unfiltered fetch if the borough predicate is rejected by Socrata.
    """
    if dataset_key not in MANHATTAN_MAP_KEYS:
        raise KeyError(f"Not a Manhattan map layer: {dataset_key}")
    where = DATASET_REGISTRY[dataset_key].get("manhattan_where")
    if not where:
        return fetch_dataset(dataset_key, limit=limit)
    try:
        return fetch_dataset(dataset_key, limit=limit, where=where)
    except Exception:
        return fetch_dataset(dataset_key, limit=limit)


def fetch_all_datasets(*, limit: int = 50_000) -> dict[str, pd.DataFrame]:
    """Load full ingestion matrix (cached per dataset)."""
    out: dict[str, pd.DataFrame] = {}
    for key in DATASET_REGISTRY:
        try:
            out[key] = fetch_dataset(key, limit=limit)
        except Exception as exc:
            out[key] = pd.DataFrame({"_error": [str(exc)]})
    return out


def df_to_gdf(df: pd.DataFrame) -> Any:
    """Best-effort GeoDataFrame in EPSG:2263."""
    if gpd is None or df.empty:
        return None
    if "the_geom" in df.columns:
        try:
            gdf = gpd.GeoDataFrame(df.copy(), geometry=gpd.GeoSeries.from_wkt(df["the_geom"], crs=WGS84))
            return gdf.to_crs(NYC_CRS)
        except Exception:
            pass
    if "geometry" in df.columns:
        try:
            gdf = gpd.GeoDataFrame(df.copy(), geometry=df["geometry"], crs=WGS84)
            return gdf.to_crs(NYC_CRS)
        except Exception:
            pass
    lat_col = pick_column(df, LAT_CANDIDATES)
    lon_col = pick_column(df, LON_CANDIDATES)
    if lat_col and lon_col and Point is not None:
        geom = [
            Point(float(x), float(y)) if pd.notna(x) and pd.notna(y) else None
            for x, y in zip(df[lon_col], df[lat_col], strict=False)
        ]
        gdf = gpd.GeoDataFrame(df.copy(), geometry=geom, crs=WGS84)
        return gdf.to_crs(NYC_CRS)
    return None


def gdf_to_map_df(gdf: Any, *, layer: str) -> pd.DataFrame:
    """EPSG:4326 points for Streamlit st.map."""
    if gdf is None or getattr(gdf, "empty", True):
        return pd.DataFrame(columns=["lat", "lon", "layer"])
    try:
        wgs = gdf.to_crs(WGS84)
        centroids = wgs.geometry.centroid
        out = pd.DataFrame(
            {
                "lat": centroids.y,
                "lon": centroids.x,
                "layer": layer,
            }
        )
        return out.dropna(subset=["lat", "lon"])
    except Exception:
        return pd.DataFrame(columns=["lat", "lon", "layer"])


def dataframe_to_map_df(df: pd.DataFrame, *, layer: str) -> pd.DataFrame:
    """Lat/lon table for st.map from a plain DataFrame."""
    if df.empty:
        return pd.DataFrame(columns=["lat", "lon", "layer"])
    lat_col = pick_column(df, LAT_CANDIDATES)
    lon_col = pick_column(df, LON_CANDIDATES)
    if not lat_col or not lon_col:
        gdf = df_to_gdf(df)
        return gdf_to_map_df(gdf, layer=layer)
    out = pd.DataFrame(
        {
            "lat": pd.to_numeric(df[lat_col], errors="coerce"),
            "lon": pd.to_numeric(df[lon_col], errors="coerce"),
            "layer": layer,
        }
    )
    return out.dropna(subset=["lat", "lon"])


@_cache_decorator()
def fetch_geodataframe(dataset_key: str, *, limit: int = 50_000, manhattan_only: bool = False) -> Any:
    """Cached spatial layer for overlap analysis and maps."""
    if manhattan_only and dataset_key in MANHATTAN_MAP_KEYS:
        df = fetch_manhattan_map_layer(dataset_key, limit=limit)
    else:
        df = fetch_dataset(dataset_key, limit=limit)
    return df_to_gdf(df)


@_cache_decorator()
def load_manhattan_map_layers(*, limit: int = 25_000) -> dict[str, pd.DataFrame]:
    """Cached map-ready lat/lon frames for inspection + street permits."""
    layers: dict[str, pd.DataFrame] = {}
    for key in MANHATTAN_MAP_KEYS:
        df = fetch_manhattan_map_layer(key, limit=limit)
        gdf = df_to_gdf(df)
        layers[key] = dataframe_to_map_df(df, layer=key) if gdf is None else gdf_to_map_df(gdf, layer=key)
    return layers


def token_status() -> dict[str, Any]:
    """Auth health for UI header."""
    token = os.getenv("SOCRATA_APP_TOKEN", "").strip()
    key_id = os.getenv("SOCRATA_KEY_ID", "").strip()
    key_secret = os.getenv("SOCRATA_KEY_SECRET", "").strip()
    return {
        "configured": bool(token),
        "key_pair": bool(key_id and key_secret),
        "masked": f"{token[:4]}…{token[-4:]}" if len(token) > 8 else ("(set)" if token else "(missing)"),
        "domain": DOMAIN,
        "datasets": len(DATASET_REGISTRY),
    }


def ingestion_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Row counts and BBL coverage for utilities panel."""
    rows = []
    for key, meta in DATASET_REGISTRY.items():
        df = frames.get(key, pd.DataFrame())
        err = df["_error"].iloc[0] if not df.empty and "_error" in df.columns else ""
        rows.append(
            {
                "key": key,
                "label": meta["label"],
                "fourfour": meta["fourfour"],
                "rows": 0 if err else len(df),
                "bbl_coverage_pct": round(df["_bbl"].notna().mean() * 100, 1) if "_bbl" in df.columns and len(df) else 0,
                "error": err,
            }
        )
    return pd.DataFrame(rows)
