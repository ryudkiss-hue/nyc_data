"""
Centralized Socrata ingestion for Manhattan Mission Control.

Registry: config/datasets.yaml. Optional parquet cache under data/local_db/socrata_cache/.
"""

from __future__ import annotations

import logging
import os
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry as _Retry

    _SESSION = requests.Session()
    _SESSION.mount(
        "https://",
        HTTPAdapter(
            max_retries=_Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
            )
        ),
    )
except ImportError:  # pragma: no cover
    requests = None  # type: ignore
    _SESSION = None  # type: ignore

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

# Pre-compile regex for BBL normalization (performance optimization)
_RE_NON_DIGIT = re.compile(r"\D")

try:
    from app.utils.cache_manager import (
        evict_old_cache as _evict_old_cache,
    )
    from app.utils.cache_manager import (
        last_fetched_iso as _last_fetched_iso,
    )
    from app.utils.cache_manager import (
        read_cache as _read_disk_cache,
    )
    from app.utils.cache_manager import (
        read_stale_cache as _read_stale_cache,
    )
    from app.utils.cache_manager import (
        write_cache as _write_disk_cache,
    )

    _DISK_CACHE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DISK_CACHE_AVAILABLE = False


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
    return False


def get_socrata_client() -> Any:
    _require_sodapy()
    token = (os.getenv("SOCRATA_APP_TOKEN") or "").strip() or None
    username = (os.getenv("SOCRATA_KEY_ID") or os.getenv("SOCRATA_USERNAME") or "").strip() or None
    password = (os.getenv("SOCRATA_KEY_SECRET") or os.getenv("SOCRATA_PASSWORD") or "").strip() or None
    return Socrata(DOMAIN, token, username=username, password=password, timeout=90)


def normalize_bbl(series: pd.Series) -> pd.Series:
    """Normalize BBL using pre-compiled regex for better performance."""
    s = series.astype(str).str.replace(_RE_NON_DIGIT, "", regex=False)
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
    if st is not None and hasattr(st, "cache_data"):
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


_DELTA_COLUMN_CANDIDATES = ("updated_at", "date_modified")

# Cache for detected delta columns to avoid repeated probes
_DELTA_COLUMN_CACHE: dict[str, str | None] = {}


def _detect_delta_column(dataset_key: str) -> str | None:
    """Return the name of a timestamp column suitable for delta fetching, or None.

    Fetches a single row from Socrata to inspect column names. Returns
    ``"updated_at"`` or ``"date_modified"`` if either is present; otherwise ``None``.
    
    Results are cached in-process to avoid repeated probes.
    """
    # Check in-process cache first
    if dataset_key in _DELTA_COLUMN_CACHE:
        return _DELTA_COLUMN_CACHE[dataset_key]
    
    meta = DATASET_REGISTRY.get(dataset_key, {})
    try:
        client = get_socrata_client()
        rows = client.get(meta["fourfour"], limit=1)
        if not rows:
            _DELTA_COLUMN_CACHE[dataset_key] = None
            return None
        cols = {c.lower() for c in rows[0].keys()}
        for candidate in _DELTA_COLUMN_CANDIDATES:
            if candidate in cols:
                _DELTA_COLUMN_CACHE[dataset_key] = candidate
                return candidate
    except Exception as exc:
        logging.debug("_detect_delta_column: probe failed for %s: %s", dataset_key, exc)
    
    _DELTA_COLUMN_CACHE[dataset_key] = None
    return None


def _fetch_live(
    dataset_key: str,
    *,
    limit: int,
    where: str | None,
    select: str | None = None,
    retries: int = 3,
    backoff: float = 2.0,
) -> pd.DataFrame:
    """Fetch from Socrata with exponential-backoff retry.

    *select*: optional ``$select`` column projection forwarded to Socrata.
    """
    meta = DATASET_REGISTRY[dataset_key]
    client = get_socrata_client()
    kwargs: dict[str, Any] = {"limit": limit}
    if where:
        kwargs["where"] = where
    if select:
        kwargs["select"] = select

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
def fetch_dataset(
    dataset_key: str,
    *,
    limit: int = 50_000,
    where: str | None = None,
    select: str | None = None,
) -> pd.DataFrame:
    """Fetch a dataset from Socrata, with multi-level caching.

    Layers:
    1. L1 — ``@st.cache_data`` (handled by callers / the decorator above).
    2. L2 — Parquet disk cache (``app/utils/cache_manager``).
    3. Live fetch from Socrata (with delta WHERE when a previous fetch exists).

    *select*: optional ``$select`` column projection (Item 13).
    *where*: extra SoQL WHERE clause fragment (caller-supplied).
    """
    if dataset_key not in DATASET_REGISTRY:
        raise KeyError(f"Unknown dataset_key: {dataset_key}")

    # Apply dataset-level default WHERE filter when caller doesn't supply one
    if where is None:
        where = DATASET_REGISTRY[dataset_key].get("default_where")

    # L2: Parquet disk cache (cache_manager)
    if _DISK_CACHE_AVAILABLE:
        cached = _read_disk_cache(dataset_key)
        if cached is not None:
            log_event("fetch_parquet_l2", dataset=dataset_key, rows=len(cached))
            return cached

    # Legacy L2: old-style parquet cache (backwards compat)
    legacy_cached = _read_parquet_cache(dataset_key)
    if legacy_cached is not None:
        log_event("fetch_parquet", dataset=dataset_key, rows=len(legacy_cached))
        return _postprocess_dataset(dataset_key, legacy_cached)

    # Delta fetch: if we have a prior fetch timestamp and the dataset has
    # a known timestamp column, narrow the query to only new/updated rows.
    effective_where = where
    if _DISK_CACHE_AVAILABLE:
        last_iso = _last_fetched_iso(dataset_key)
        if last_iso is not None:
            # Detect whether the dataset exposes an updated_at / date_modified column
            # by checking the cache; we probe lazily and cache the result.
            delta_col: str | None = _detect_delta_column(dataset_key)
            if delta_col:
                delta_clause = f"{delta_col} > '{last_iso}'"
                effective_where = (
                    f"({effective_where}) AND {delta_clause}"
                    if effective_where
                    else delta_clause
                )
                logging.info(
                    "fetch_dataset: delta fetch for %s using %s > %s",
                    dataset_key, delta_col, last_iso,
                )

    try:
        t0 = time.perf_counter()
        df = _fetch_live(dataset_key, limit=limit, where=effective_where, select=select)
        # Write to new L2 disk cache
        if _DISK_CACHE_AVAILABLE and not df.empty and "_error" not in df.columns:
            _write_disk_cache(dataset_key, df)
        # Also maintain legacy cache for backwards compat
        _write_parquet_cache(dataset_key, df)
        log_event(
            "fetch_live",
            dataset=dataset_key,
            rows=len(df),
            seconds=round(time.perf_counter() - t0, 2),
            where=effective_where or "",
        )
        return df
    except Exception as exc:
        log_event("fetch_error", dataset=dataset_key, error=str(exc))
        # Offline mode (Item 17): return stale cache if a live fetch fails
        if _DISK_CACHE_AVAILABLE:
            stale = _read_stale_cache(dataset_key)
            if stale is not None:
                logging.warning(
                    "fetch_dataset: live fetch failed for %s (%s) — returning stale cache.",
                    dataset_key, exc,
                )
                stale = stale.copy()
                stale.attrs["stale"] = True
                return stale
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
    if len(key_list) == 1:
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


def fetch_datasets_parallel(
    keys: list[str],
    *,
    limit: int = 25_000,
) -> dict[str, pd.DataFrame]:
    """Fetch multiple datasets concurrently using ThreadPoolExecutor."""
    results: dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=min(len(keys), 6)) as exe:
        future_to_key = {exe.submit(fetch_dataset, k, limit=limit): k for k in keys}
        for fut in as_completed(future_to_key):
            k = future_to_key[fut]
            try:
                results[k] = fut.result()
            except Exception as exc:
                logging.warning("parallel fetch %s failed: %s", k, exc)
                results[k] = pd.DataFrame()
    return results


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
            for x, y in zip(df[lon_col], df[lat_col])
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
