"""
Parquet-based L2 disk cache, manifest tracking, TTL management, and background
pre-fetch scheduler for the NYC DOT SIM Mission Control app.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # pragma: no cover
    BackgroundScheduler = None  # type: ignore

_REPO_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = _REPO_ROOT / "data" / "cache"
MAX_CACHE_BYTES = 1 * 1024**3  # 1 GB default

# Per-dataset TTL in hours. Datasets with no entry fall back to "_default".
DATASET_TTL_HOURS: dict[str, float] = {
    "complaints_311": 1.0,      # high frequency
    "inspection": 4.0,
    "street_permits": 4.0,
    "violations": 6.0,
    "mappluto": 720.0,          # 30 days
    "pedestrian_demand": 720.0,
    "ramp_full_corpus": 168.0,  # 1 week
    "_default": 24.0,
}

_MANIFEST_PATH = CACHE_DIR / "manifest.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _ttl_for(key: str) -> float:
    """Return TTL hours for *key*, falling back to the default."""
    return DATASET_TTL_HOURS.get(key, DATASET_TTL_HOURS["_default"])


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def cache_path(key: str, date_str: str) -> Path:
    """Return ``data/cache/<key>_<date_str>.parquet.gz``."""
    return CACHE_DIR / f"{key}_{date_str}.parquet.gz"


def _latest_cache_path(key: str) -> Path | None:
    """Return the most-recently-written .parquet.gz file for *key*, or None."""
    _ensure_cache_dir()
    candidates = sorted(CACHE_DIR.glob(f"{key}_*.parquet.gz"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def cache_manifest() -> dict[str, Any]:
    """Load the manifest JSON from disk; return empty dict if absent or corrupt."""
    _ensure_cache_dir()
    if not _MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_manifest(manifest: dict[str, Any]) -> None:
    _ensure_cache_dir()
    _MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def update_manifest(key: str, path: Path, rows: int, ttl_hours: float) -> None:
    """Upsert a manifest entry for *key*."""
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(now.timestamp() + ttl_hours * 3600, tz=timezone.utc)
    manifest = cache_manifest()
    manifest[key] = {
        "path": str(path),
        "rows": rows,
        "fetched_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "ttl_hours": ttl_hours,
    }
    _save_manifest(manifest)


# ---------------------------------------------------------------------------
# Write / Read
# ---------------------------------------------------------------------------

def write_cache(key: str, df: pd.DataFrame) -> Path:
    """Serialize *df* to a gzip-compressed Parquet file. Returns the path written."""
    _ensure_cache_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = cache_path(key, date_str)
    df.to_parquet(dest, index=False, compression="gzip")
    ttl_hours = _ttl_for(key)
    update_manifest(key, dest, len(df), ttl_hours)
    evict_old_cache()  # Item 11: keep total size within cap
    return dest


def read_cache(key: str, max_age_hours: float | None = None) -> pd.DataFrame | None:
    """Return a cached DataFrame if a fresh file exists, else ``None``.

    *max_age_hours* defaults to the dataset-specific TTL from ``DATASET_TTL_HOURS``.
    """
    if max_age_hours is None:
        max_age_hours = _ttl_for(key)

    manifest = cache_manifest()
    entry = manifest.get(key)
    if entry is None:
        return None

    path = Path(entry["path"])
    if not path.exists():
        return None

    # Check expiry via manifest expires_at
    try:
        expires_at = datetime.fromisoformat(entry["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            return None
    except Exception:
        # Fall back to mtime check
        age_seconds = time.time() - path.stat().st_mtime
        if age_seconds > max_age_hours * 3600:
            return None

    try:
        return pd.read_parquet(path)
    except Exception as exc:
        logging.warning("cache_manager: failed to read cache for %s: %s", key, exc)
        return None


def read_stale_cache(key: str) -> pd.DataFrame | None:
    """Return any cached file for *key* regardless of age (for offline mode)."""
    manifest = cache_manifest()
    entry = manifest.get(key)
    if entry:
        path = Path(entry["path"])
        if path.exists():
            try:
                return pd.read_parquet(path)
            except Exception:
                pass
    # Also try scanning disk directly in case manifest is stale
    path = _latest_cache_path(key)
    if path is None:
        return None
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


def last_fetched_iso(key: str) -> str | None:
    """Return the ISO-formatted fetched_at timestamp from the manifest, or None."""
    entry = cache_manifest().get(key)
    return entry["fetched_at"] if entry else None


# ---------------------------------------------------------------------------
# Eviction
# ---------------------------------------------------------------------------

def evict_old_cache(max_bytes: int = MAX_CACHE_BYTES) -> int:
    """Delete oldest .parquet.gz files until total size < *max_bytes*.

    Returns bytes freed.
    """
    _ensure_cache_dir()
    files = sorted(CACHE_DIR.glob("*.parquet.gz"), key=lambda p: p.stat().st_mtime)
    total = sum(p.stat().st_size for p in files)
    freed = 0
    while total > max_bytes and files:
        oldest = files.pop(0)
        size = oldest.stat().st_size
        try:
            oldest.unlink()
            freed += size
            total -= size
            logging.info("cache_manager: evicted %s (%d bytes)", oldest.name, size)
        except Exception as exc:
            logging.warning("cache_manager: could not evict %s: %s", oldest.name, exc)
    return freed


# ---------------------------------------------------------------------------
# Background pre-fetch scheduler (APScheduler)
# ---------------------------------------------------------------------------

def start_prefetch_scheduler(dataset_keys: list[str], interval_minutes: int = 60) -> None:
    """Start a background APScheduler job that refreshes each dataset on a schedule.

    Uses ``st.session_state["_prefetch_scheduler"]`` to prevent duplicate starts.
    Does nothing if APScheduler is not installed.
    """
    if BackgroundScheduler is None:
        logging.warning(
            "cache_manager: apscheduler not installed — background pre-fetch disabled. "
            'Install with: pip install apscheduler'
        )
        return

    # Avoid duplicate starts inside a single Streamlit session
    if st is not None:
        existing = st.session_state.get("_prefetch_scheduler")
        if existing is not None and getattr(existing, "running", False):
            return

    # Import here to avoid a circular import at module level
    try:
        from app.data_loader import fetch_dataset  # noqa: PLC0415
    except ImportError:
        logging.warning("cache_manager: could not import fetch_dataset for pre-fetch scheduler")
        return

    def _prefetch_all() -> None:
        for key in dataset_keys:
            try:
                fetch_dataset(key)
                logging.info("cache_manager: pre-fetched %s", key)
            except Exception as exc:
                logging.warning("cache_manager: pre-fetch failed for %s: %s", key, exc)

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(_prefetch_all, "interval", minutes=interval_minutes, id="prefetch_all")
    scheduler.start()
    logging.info(
        "cache_manager: started background pre-fetch scheduler (interval=%dm, keys=%s)",
        interval_minutes,
        dataset_keys,
    )

    if st is not None:
        st.session_state["_prefetch_scheduler"] = scheduler


# ---------------------------------------------------------------------------
# Ramp Analysis Caching (Full-Corpus)
# ---------------------------------------------------------------------------

def cache_ramp_corpus(df: pd.DataFrame) -> Path:
    """Cache the full ramp analysis corpus as gzip-compressed Parquet.

    *df* is serialized with a TTL of 168 hours (1 week).
    Returns the path written.
    """
    return write_cache("ramp_full_corpus", df)


def get_cached_ramp_corpus() -> pd.DataFrame | None:
    """Return the cached ramp analysis corpus if fresh, else None.

    Returns None on cache miss or TTL expiry.
    """
    return read_cache("ramp_full_corpus")


# Expose CACHE_DIR env-var override so deployments can redirect the cache location
_env_cache_dir = os.getenv("SOCRATA_CACHE_DIR", "").strip()
if _env_cache_dir:
    CACHE_DIR = Path(_env_cache_dir)
    _MANIFEST_PATH = CACHE_DIR / "manifest.json"
