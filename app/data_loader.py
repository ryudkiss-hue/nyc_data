"""
Centralized Socrata ingestion for Manhattan Mission Control.

Registry: config/datasets.yaml. Optional parquet cache under data/local_db/socrata_cache/.
Demo/offline: MISSION_DEMO=1 or no Socrata credentials.
"""

from __future__ import annotations

import logging
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from app.ingest_log import log_event

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
_DATASETS_YAML = _REPO_ROOT / "config" / "datasets.yaml"
_PARQUET_CACHE_DIR = _REPO_ROOT / "data" / "local_db" / "socrata_cache"


def _bootstrap_env() -> None:
    if load_dotenv is None:
        return
    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(_REPO_ROOT / ".env.socrata", override=False)


_bootstrap_env()

DOMAIN = os.getenv("SOCRATA_DOMAIN", "data.cityofnewyork.us")
CACHE_TTL_SECONDS = 86_400
NYC_CRS = "EPSG:2263"
WGS84 = "EPSG:4326"

BBL_CANDIDATES = ("bbl", "lot_bbl", "tax_lot", "taxblock", "boro_block_lot")
LAT_CANDIDATES = ("latitude", "lat", "y", "ycoord")
LON_CANDIDATES = ("longitude", "lon", "lng", "long", "x", "xcoord")
DATE_CANDIDATES = ("created_date", "created", "date", "open_date", "requested_datetime")
OWNER_CANDIDATES = ("owner", "owner_type", "ownership", "lot_owner", "agency")
GRACE_CANDIDATES = ("grace_pd", "grace_period", "grace_date", "graceperiod")


def _load_registry_from_yaml() -> tuple[dict[str, dict[str, str]], tuple[str, ...], dict[str, tuple[str, ...]]]:
    if not _DATASETS_YAML.exists():
        raise FileNotFoundError(f"Missing dataset registry: {_DATASETS_YAML}")
    raw = yaml.safe_load(_DATASETS_YAML.read_text(encoding="utf-8"))
    registry = {k: dict(v) for k, v in raw["datasets"].items()}
    map_keys = tuple(raw.get("manhattan_map_keys", ()))
    workflow = {k: tuple(v) for k, v in raw.get("workflow_datasets", {}).items()}
    return registry, map_keys, workflow


DATASET_REGISTRY, MANHATTAN_MAP_KEYS, WORKFLOW_DATASETS = _load_registry_from_yaml()


def _require_sodapy() -> None:
    if Socrata is None:
        raise ImportError(
            'sodapy is required for live Socrata pulls. Install with: pip install -e ".[mission]"'
        )


def demo_mode_enabled() -> bool:
    if os.getenv("MISSION_DEMO", "").strip().lower() in ("1", "true", "yes"):
        return True
    token = (os.getenv("SOCRATA_APP_TOKEN") or "").strip()
    key_id = (os.getenv("SOCRATA_KEY_ID") or "").strip()
    key_secret = (os.getenv("SOCRATA_KEY_SECRET") or "").strip()
    return not token and not (key_id and key_secret)


def get_socrata_client() -> Any:
    _require_sodapy()
    token = (os.getenv("SOCRATA_APP_TOKEN") or "").strip() or None
    username = (os.getenv("SOCRATA_KEY_ID") or os.getenv("SOCRATA_USERNAME") or "").strip() or None
    password = (os.getenv("SOCRATA_KEY_SECRET") or os.getenv("SOCRATA_PASSWORD") or "").strip() or None
    return Socrata(DOMAIN, token, username=username, password=password, timeout=90)


def normalize_bbl(series: pd.Series) -> pd.Series:
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
    return lambda f: f


def _parquet_path(dataset_key: str) -> Path:
    _PARQUET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _PARQUET_CACHE_DIR / f"{dataset_key}.parquet"


def _parquet_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) < CACHE_TTL_SECONDS


def _read_parquet_cache(dataset_key: str) -> pd.DataFrame | None:
    path = _parquet_path(dataset_key)
    if not _parquet_fresh(path):
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


def _write_parquet_cache(dataset_key: str, df: pd.DataFrame) -> None:
    if df.empty or "_error" in df.columns:
        return
    try:
        df.to_parquet(_parquet_path(dataset_key), index=False)
    except Exception:
        pass


def _demo_frame(dataset_key: str) -> pd.DataFrame:
    """Minimal synthetic rows so workflows run offline."""
    bbl = "1000010001"
    templates: dict[str, dict[str, list]] = {
        "lot_info": {"bbl": [bbl], "owner": ["City"]},
        "mappluto": {"bbl": [bbl], "ownername": ["Private"]},
        "complaints_311": {"created_date": ["2020-01-01"], "bbl": [bbl]},
        "violations": {"bbl": [bbl], "grace_pd": ["2020-01-01"]},
        "tree_damage": {"bbl": [bbl], "agency": ["Parks"]},
        "built": {"length": [100.0]},
        "ramp_progress": {"latitude": [40.75], "longitude": [-73.99]},
        "pedestrian_demand": {"latitude": [40.76], "longitude": [-73.98]},
        "weekly_construction": {"latitude": [40.75], "longitude": [-73.99]},
        "street_permits": {"latitude": [40.75], "longitude": [-73.99], "borough": ["MANHATTAN"]},
        "capital_blocks": {"latitude": [40.75], "longitude": [-73.99]},
        "inspection": {"latitude": [40.75], "longitude": [-73.99], "borough": ["MANHATTAN"]},
    }
    data = templates.get(dataset_key, {"note": ["demo row"]})
    return _postprocess_dataset(dataset_key, pd.DataFrame(data))


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


def _fetch_live(
    dataset_key: str,
    *,
    limit: int,
    where: str | None,
    retries: int = 3,
    backoff: float = 2.0,
) -> pd.DataFrame:
    """Fetch from Socrata with exponential-backoff retry."""
    meta = DATASET_REGISTRY[dataset_key]
    client = get_socrata_client()
    kwargs: dict[str, Any] = {"limit": limit}
    if where:
        kwargs["where"] = where

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            rows = client.get(meta["fourfour"], **kwargs)
            df = pd.DataFrame.from_records(rows) if rows else pd.DataFrame()
            return _postprocess_dataset(dataset_key, df)
        except Exception as exc:
            last_exc = exc
            exc_str = str(exc)
            # 429 = Socrata throttle. Surface a clear message and back off longer.
            if "429" in exc_str or "Too Many Requests" in exc_str:
                wait = backoff ** (attempt + 2)  # longer wait for throttle
                logging.warning(
                    "Socrata rate-limited (429) on %s — no app token or abusive rate. "
                    "Set SOCRATA_APP_TOKEN env var. Backing off %.0fs.",
                    dataset_key, wait,
                )
                if attempt < retries - 1:
                    time.sleep(wait)
                continue
            wait = backoff ** attempt
            logging.warning(
                "Socrata fetch attempt %d/%d failed for %s: %s — retrying in %.1fs",
                attempt + 1, retries, dataset_key, exc, wait,
            )
            if attempt < retries - 1:
                time.sleep(wait)

    # Surface a helpful message for 429 exhaustion
    if last_exc and ("429" in str(last_exc) or "Too Many Requests" in str(last_exc)):
        raise RuntimeError(
            f"Socrata rate-limited (HTTP 429) for '{dataset_key}'. "
            "Add SOCRATA_APP_TOKEN to your .env file (Settings → API Tokens) "
            "to get a dedicated request pool with no throttling."
        ) from last_exc
    raise RuntimeError(
        f"All {retries} fetch attempts failed for {dataset_key}: {last_exc}"
    ) from last_exc


@_cache_decorator()
def fetch_dataset(dataset_key: str, *, limit: int = 50_000, where: str | None = None) -> pd.DataFrame:
    if dataset_key not in DATASET_REGISTRY:
        raise KeyError(f"Unknown dataset_key: {dataset_key}")
    if demo_mode_enabled():
        log_event("fetch_demo", dataset=dataset_key, rows=1)
        return _demo_frame(dataset_key)
    # Apply dataset-level default WHERE filter when caller doesn't supply one
    if where is None:
        where = DATASET_REGISTRY[dataset_key].get("default_where")
    cached = _read_parquet_cache(dataset_key)
    if cached is not None:
        log_event("fetch_parquet", dataset=dataset_key, rows=len(cached))
        return _postprocess_dataset(dataset_key, cached)
    try:
        t0 = time.perf_counter()
        df = _fetch_live(dataset_key, limit=limit, where=where)
        _write_parquet_cache(dataset_key, df)
        log_event(
            "fetch_live",
            dataset=dataset_key,
            rows=len(df),
            seconds=round(time.perf_counter() - t0, 2),
            where=where or "",
        )
        return df
    except Exception as exc:
        log_event("fetch_error", dataset=dataset_key, error=str(exc))
        raise


def fetch_manhattan_map_layer(dataset_key: str, *, limit: int = 25_000) -> pd.DataFrame:
    if dataset_key not in MANHATTAN_MAP_KEYS:
        raise KeyError(f"Not a Manhattan map layer: {dataset_key}")
    where = DATASET_REGISTRY[dataset_key].get("manhattan_where")
    if not where:
        return fetch_dataset(dataset_key, limit=limit)
    try:
        return fetch_dataset(dataset_key, limit=limit, where=where)
    except Exception:
        return fetch_dataset(dataset_key, limit=limit)


def keys_for_workflow(workflow_key: str) -> tuple[str, ...]:
    if workflow_key == "ingest":
        return tuple(DATASET_REGISTRY.keys())
    return WORKFLOW_DATASETS.get(workflow_key, ())


def fetch_datasets_for_keys(
    keys: tuple[str, ...] | list[str],
    *,
    limit: int = 10_000,
    max_workers: int = 4,
) -> dict[str, pd.DataFrame]:
    """Load only requested datasets (parallel when live)."""
    key_list = list(keys)
    if not key_list:
        return {}
    if demo_mode_enabled() or len(key_list) == 1:
        return {k: fetch_dataset(k, limit=limit) for k in key_list}

    out: dict[str, pd.DataFrame] = {}

    def _one(k: str) -> tuple[str, pd.DataFrame]:
        try:
            return k, fetch_dataset(k, limit=limit)
        except Exception as exc:
            return k, pd.DataFrame({"_error": [str(exc)]})

    with ThreadPoolExecutor(max_workers=min(max_workers, len(key_list))) as pool:
        futures = {pool.submit(_one, k): k for k in key_list}
        for fut in as_completed(futures):
            key, df = fut.result()
            out[key] = df
    return out


def fetch_all_datasets(*, limit: int = 50_000) -> dict[str, pd.DataFrame]:
    return fetch_datasets_for_keys(tuple(DATASET_REGISTRY.keys()), limit=limit)


def df_to_gdf(df: pd.DataFrame) -> Any:
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
    if gdf is None or getattr(gdf, "empty", True):
        return pd.DataFrame(columns=["lat", "lon", "layer"])
    try:
        wgs = gdf.to_crs(WGS84)
        centroids = wgs.geometry.centroid
        out = pd.DataFrame({"lat": centroids.y, "lon": centroids.x, "layer": layer})
        return out.dropna(subset=["lat", "lon"])
    except Exception:
        return pd.DataFrame(columns=["lat", "lon", "layer"])


def dataframe_to_map_df(df: pd.DataFrame, *, layer: str) -> pd.DataFrame:
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
    if manhattan_only and dataset_key in MANHATTAN_MAP_KEYS:
        df = fetch_manhattan_map_layer(dataset_key, limit=limit)
    else:
        df = fetch_dataset(dataset_key, limit=limit)
    return df_to_gdf(df)


@_cache_decorator()
def load_manhattan_map_layers(*, limit: int = 25_000) -> dict[str, pd.DataFrame]:
    layers: dict[str, pd.DataFrame] = {}
    for key in MANHATTAN_MAP_KEYS:
        df = fetch_manhattan_map_layer(key, limit=limit)
        gdf = df_to_gdf(df)
        layers[key] = dataframe_to_map_df(df, layer=key) if gdf is None else gdf_to_map_df(gdf, layer=key)
    return layers


def token_status() -> dict[str, Any]:
    token = os.getenv("SOCRATA_APP_TOKEN", "").strip()
    key_id = os.getenv("SOCRATA_KEY_ID", "").strip()
    key_secret = os.getenv("SOCRATA_KEY_SECRET", "").strip()
    return {
        "configured": bool(token),
        "key_pair": bool(key_id and key_secret),
        "masked": f"{token[:4]}…{token[-4:]}" if len(token) > 8 else ("(set)" if token else "(missing)"),
        "domain": DOMAIN,
        "datasets": len(DATASET_REGISTRY),
        "demo_mode": demo_mode_enabled(),
    }


def ingestion_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for key, meta in DATASET_REGISTRY.items():
        df = frames.get(key, pd.DataFrame())
        err = df["_error"].iloc[0] if not df.empty and "_error" in df.columns else ""
        loaded = key in frames and not df.empty and "_error" not in df.columns

        # Cache freshness
        cache_path = _parquet_path(key)
        cache_age_h = (
            round((time.time() - cache_path.stat().st_mtime) / 3600, 1)
            if cache_path.exists()
            else None
        )
        source = (
            "demo" if not loaded else ("parquet" if cache_path.exists() and _parquet_fresh(cache_path) else "live")
        )

        rows.append(
            {
                "key": key,
                "label": meta["label"],
                "group": meta.get("group", "—"),
                "fourfour": meta["fourfour"],
                "rows": 0 if err else len(df),
                "columns": len(df.columns) if not df.empty and not err else 0,
                "bbl_coverage_%": (
                    round(df["_bbl"].notna().mean() * 100, 1)
                    if "_bbl" in df.columns and len(df)
                    else 0
                ),
                "cache_age_h": cache_age_h,
                "source": source,
                "status": "✅" if loaded else ("❌ error" if err else "—"),
                "error": err,
            }
        )
    return pd.DataFrame(rows)


def cache_freshness_report() -> pd.DataFrame:
    """Report on the age and size of all parquet caches."""
    rows = []
    for key in DATASET_REGISTRY:
        path = _parquet_path(key)
        if path.exists():
            stat = path.stat()
            age_h = round((time.time() - stat.st_mtime) / 3600, 1)
            size_kb = round(stat.st_size / 1024, 1)
            rows.append({
                "key": key,
                "age_hours": age_h,
                "size_kb": size_kb,
                "fresh": age_h < (CACHE_TTL_SECONDS / 3600),
                "path": str(path),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["key", "age_hours", "size_kb", "fresh", "path"]
    )
