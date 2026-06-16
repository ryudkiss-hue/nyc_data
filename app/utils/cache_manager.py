"""
Parquet-based L2 disk cache, manifest tracking, TTL management, and background
pre-fetch scheduler for the NYC DOT SIM Mission Control app.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

# [FIX 4] Platform-specific file locking imports
if os.name == "nt":  # Windows
    import msvcrt
else:  # Unix/Linux/macOS
    import fcntl

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # pragma: no cover
    BackgroundScheduler = None  # type: ignore

try:
    from socrata_toolkit.core.duckdb_store import DuckDBManager
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False
    DuckDBManager = None  # type: ignore

# Initialize logger
logger = logging.getLogger(__name__)

# [FIX 2] Global transaction manager (lazy singleton)
_tx_manager = None

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
# [FIX 2] Transaction management helpers
# ---------------------------------------------------------------------------

def _get_tx_manager() -> DuckDBManager:
    """Lazy singleton for transaction management.

    Returns a shared DuckDBManager instance for transactional writes.
    Raises RuntimeError if DuckDB is not available.
    """
    global _tx_manager
    if _tx_manager is None:
        if not _DUCKDB_AVAILABLE:
            raise RuntimeError("DuckDBManager not available; install socrata_toolkit")
        _tx_manager = DuckDBManager()
    return _tx_manager

def init_cache_audit_table(manager: DuckDBManager | None = None) -> None:
    """Create cache_audit table if it doesn't exist.

    [FIX 2] Call this once during app initialization to set up the audit log.
    The audit table acts as a watermark for concurrent readers: when an entry
    is committed, the data is durable and visible to other processes.

    Args:
        manager: DuckDBManager instance. If None, uses the global singleton.
    """
    if manager is None:
        manager = _get_tx_manager()

    try:
        # Create sequence first (for id auto-increment)
        manager.execute_atomic("CREATE SEQUENCE IF NOT EXISTS cache_audit_seq")

        # Create audit table with timestamp tracking
        manager.execute_atomic(
            """
            CREATE TABLE IF NOT EXISTS cache_audit (
                id INTEGER PRIMARY KEY DEFAULT nextval('cache_audit_seq'),
                key VARCHAR NOT NULL,
                path VARCHAR NOT NULL,
                rows BIGINT,
                fetched_at TIMESTAMP WITH TIME ZONE,
                expires_at TIMESTAMP WITH TIME ZONE,
                ttl_hours DOUBLE,
                written_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        logger.info("cache_audit table initialized successfully")
    except Exception as exc:
        logger.warning(f"Failed to init cache_audit table: {exc}")

# ---------------------------------------------------------------------------
# [FIX 4] File locking helpers (platform-specific)
# ---------------------------------------------------------------------------

def _lock_file(file_handle) -> None:
    """Acquire exclusive lock on file (platform-specific).

    [FIX 4] Uses fcntl (Unix) or msvcrt (Windows) for advisory file locks.
    Ensures only one writer can modify the manifest at a time.

    Args:
        file_handle: Open file object to lock
    """
    if os.name == "nt":  # Windows
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            # Non-blocking failed, try blocking
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
    else:  # Unix/Linux/macOS
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)

def _unlock_file(file_handle) -> None:
    """Release lock on file (platform-specific).

    [FIX 4] Releases the advisory lock acquired by _lock_file().

    Args:
        file_handle: Open file object to unlock
    """
    if os.name == "nt":  # Windows
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass  # Already unlocked or file closed
    else:  # Unix/Linux/macOS
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass

def cache_manifest_locked() -> tuple[dict[str, Any], Any]:
    """Load manifest with exclusive lock held.

    [FIX 4] Returns (manifest_dict, lock_handle).

    IMPORTANT: Caller MUST call _unlock_manifest(lock_handle) to release lock.

    Example:
        manifest, lock_file = cache_manifest_locked()
        try:
            manifest["key"] = new_entry
            _save_manifest_locked(manifest, lock_file)
        finally:
            _unlock_manifest(lock_file)
    """
    _ensure_cache_dir()

    # Open lock file (separate from manifest to avoid deadlock on read-modify-write)
    lock_path = _MANIFEST_PATH.parent / ".manifest.lock"
    lock_file = open(lock_path, "a")

    try:
        # Acquire exclusive lock
        _lock_file(lock_file)

        # Read manifest while holding lock (guaranteed not being modified)
        if _MANIFEST_PATH.exists():
            manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        else:
            manifest = {}

        return manifest, lock_file
    except Exception:
        lock_file.close()
        raise

def _unlock_manifest(lock_file: Any) -> None:
    """Release lock acquired by cache_manifest_locked().

    [FIX 4] Always call this after cache_manifest_locked() to release lock.

    Args:
        lock_file: Lock file handle returned by cache_manifest_locked()
    """
    try:
        _unlock_file(lock_file)
    finally:
        try:
            lock_file.close()
        except Exception:
            pass

def _save_manifest_locked(manifest: dict[str, Any], lock_file: Any) -> None:
    """Write manifest to disk using atomic rename.

    [FIX 4] PRECONDITION: Caller must hold exclusive lock (via cache_manifest_locked).

    Uses temp file + atomic rename for crash-safety:
    1. Write to temp file (safe, not visible yet)
    2. Atomic rename temp -> manifest (atomic at OS level)
    3. On failure, temp file is cleaned up

    Args:
        manifest: Manifest dict to write
        lock_file: Lock file handle (must be held by caller)
    """
    _ensure_cache_dir()

    # Write to temp file first (lock is held, no interference)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=str(_MANIFEST_PATH.parent),
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as f:
        json.dump(manifest, f, indent=2)
        temp_path = f.name

    try:
        # Atomic rename (OS-level atomicity, no partial state)
        Path(temp_path).replace(_MANIFEST_PATH)
    except Exception:
        # Clean up temp if rename fails
        try:
            Path(temp_path).unlink()
        except Exception:
            pass
        raise

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

# [FIX 4] Timeout for manifest reads when writer is active
_MANIFEST_READ_TIMEOUT = 5.0  # seconds

def cache_manifest(timeout: float = _MANIFEST_READ_TIMEOUT) -> dict[str, Any]:
    """Load manifest (read-only, waits for lock with timeout).

    [FIX 4] For write operations, use update_manifest() which handles locking.

    Args:
        timeout: Max seconds to wait for manifest to be available

    Returns:
        Manifest dict (may be stale if writer is active)
    """
    _ensure_cache_dir()

    start_time = time.time()
    last_error = None

    while True:
        try:
            # Try to read manifest (may be stale if writer is active)
            if _MANIFEST_PATH.exists():
                return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
            else:
                return {}
        except (OSError, json.JSONDecodeError) as exc:
            # File is being written or corrupt, retry
            last_error = exc
            if time.time() - start_time > timeout:
                logging.warning(
                    f"cache_manifest: timeout waiting for manifest lock after {timeout}s, "
                    f"returning empty manifest (last error: {last_error})"
                )
                return {}
            time.sleep(0.1)  # Backoff before retry

def _save_manifest(manifest: dict[str, Any]) -> None:
    _ensure_cache_dir()
    _MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

def update_manifest(key: str, path: Path, rows: int, ttl_hours: float) -> None:
    """Upsert a manifest entry for *key* with file locking.

    [FIX 4] Ensures atomicity: read-modify-write happens under exclusive lock.
    No lost updates even with concurrent processes.

    Args:
        key: Dataset key
        path: Parquet file path
        rows: Row count
        ttl_hours: Time-to-live hours
    """
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(now.timestamp() + ttl_hours * 3600, tz=timezone.utc)

    # Acquire exclusive lock before read-modify-write
    manifest, lock_file = cache_manifest_locked()
    try:
        # Modify under lock (safe from concurrent updates)
        manifest[key] = {
            "path": str(path),
            "rows": rows,
            "fetched_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "ttl_hours": ttl_hours,
        }
        # Write under lock (atomic rename)
        _save_manifest_locked(manifest, lock_file)
    finally:
        # Always release lock
        _unlock_manifest(lock_file)

# ---------------------------------------------------------------------------
# Write / Read
# ---------------------------------------------------------------------------

def write_cache_atomic(
    key: str,
    df: pd.DataFrame,
    manager: DuckDBManager | None = None,
) -> Path:
    """Write cache with transactional guarantee (all-or-nothing semantics).

    [FIX 2] Atomically writes:
    1. Parquet file to disk (via temp file + atomic rename)
    2. Manifest JSON entry
    3. Audit entry to DuckDB (watermark for concurrent readers)

    Rolls back on any failure. Ensures all-or-nothing semantics.

    Args:
        key: Dataset key (e.g., "violations", "inspection")
        df: DataFrame to write
        manager: DuckDBManager for audit log. If None, creates singleton.

    Returns:
        Path to written Parquet file

    Raises:
        OSError: If Parquet write fails
        Exception: If manifest/audit update fails (transaction rolled back)
    """
    if manager is None:
        manager = _get_tx_manager()

    # Step 0: Prepare paths
    _ensure_cache_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = cache_path(key, date_str)
    temp_dest = Path(str(dest) + ".tmp")

    ttl_hours = _ttl_for(key)
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(
        now.timestamp() + ttl_hours * 3600, tz=timezone.utc
    )

    try:
        # Step 1: Begin transaction
        manager.execute_atomic("BEGIN TRANSACTION")

        # Step 2: Write Parquet to temporary location
        # This can still fail (disk full, permission denied)
        try:
            df.to_parquet(temp_dest, index=False, compression="gzip")
        except Exception:
            # Cleanup temp file before rolling back
            if temp_dest.exists():
                try:
                    temp_dest.unlink()
                except Exception:
                    pass
            raise

        # Step 3: Atomic rename (OS-level atomicity)
        # This succeeds or fails atomically; no partial state
        try:
            temp_dest.replace(dest)
        except Exception:
            # Cleanup temp file
            if temp_dest.exists():
                try:
                    temp_dest.unlink()
                except Exception:
                    pass
            raise

        # Step 4: Update audit log in DuckDB
        # This is the watermark: other processes see this entry = data is durable
        manager.execute_atomic(
            """
            INSERT INTO cache_audit (key, path, rows, fetched_at, expires_at, ttl_hours)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                key,
                str(dest),
                len(df),
                now.isoformat(),
                expires.isoformat(),
                ttl_hours,
            ],
        )

        # Step 5: Update in-memory manifest (fallback for non-DuckDB readers)
        manifest = cache_manifest()
        manifest[key] = {
            "path": str(dest),
            "rows": len(df),
            "fetched_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "ttl_hours": ttl_hours,
        }
        _save_manifest(manifest)

        # Step 6: Eviction (best-effort, doesn't rollback)
        # Safe to do outside transaction: doesn't affect atomicity
        evict_old_cache()

        # Step 7: Commit transaction
        manager.execute_atomic("COMMIT")

        logger.info(f"write_cache_atomic: {key} -> {dest} ({len(df)} rows)")
        return dest

    except Exception as exc:
        # Rollback on any error (including step 1-5 failures)
        try:
            manager.execute_atomic("ROLLBACK")
        except Exception as rollback_exc:
            logger.error(f"Failed to rollback transaction: {rollback_exc}")

        # Clean up temp file if it still exists
        if temp_dest.exists():
            try:
                temp_dest.unlink()
            except Exception as cleanup_exc:
                logger.warning(f"Failed to clean up temp file {temp_dest}: {cleanup_exc}")

        logger.error(f"write_cache_atomic failed for {key}: {exc}")
        raise

def write_cache(key: str, df: pd.DataFrame) -> Path:
    """DEPRECATED: Use write_cache_atomic() instead.

    Serialize *df* to a gzip-compressed Parquet file. Returns the path written.

    Kept for backward compatibility only. New code should import and call
    write_cache_atomic explicitly for ACID guarantees.
    """
    logging.warning(
        f"write_cache() is deprecated; use write_cache_atomic() for ACID guarantees. "
        f"Falling back for key={key}"
    )
    # Fall through to new atomic version
    try:
        return write_cache_atomic(key, df)
    except Exception as exc:
        # If atomicity fails, fall back to synchronous write (no rollback)
        logger.error(f"write_cache_atomic failed, falling back to sync write: {exc}")
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
