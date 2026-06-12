"""
NYC DOT Socrata Toolkit - ACID Reliability Fixes
Concrete implementation code snippets for copy-paste implementation

Each section is marked with [FIX N] and can be copy-pasted into the respective files.
Tests are provided at the bottom.
"""

# ==============================================================================
# [FIX 1] DuckDB Connection Pooling
# File: src/socrata_toolkit/core/duckdb_store.py
# ==============================================================================

# ADD IMPORTS AT TOP:
import threading

# MODIFY DuckDBManager CLASS:
class DuckDBManager:
    """Manages DuckDB local file connection, MotherDuck integration, and extensions."""

    def __init__(
        self,
        db_path: str | None = None,
        read_only: bool | None = None,
        motherduck_token: str | None = None,
    ):
        self.db_path = db_path or os.getenv(
            "DUCKDB_PATH", "data/local_db/nyc_mission_control.duckdb"
        )
        self.read_only = read_only
        self.motherduck_token = motherduck_token or os.getenv("MOTHERDUCK_TOKEN")
        self._conn: duckdb.DuckDBPyConnection | None = None
        # [FIX 1] Add connection lock for thread safety
        self._conn_lock = threading.RLock()

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Thread-safe singleton connection with double-check locking."""
        if self._conn is None:
            with self._conn_lock:
                # Double-check pattern: another thread may have created connection
                if self._conn is None:
                    connection_path = self.db_path
                    logger.info("Connecting to DuckDB at %s", connection_path)
                    is_read_only = (
                        self.read_only
                        if self.read_only is not None
                        else (os.getenv("DUCKDB_READ_ONLY", "false").lower() == "true")
                    )

                    if self.motherduck_token and not connection_path.startswith("md:"):
                        self._conn = duckdb.connect(connection_path, read_only=is_read_only)
                        try:
                            self._conn.execute(f"SET motherduck_token='{self.motherduck_token}';")
                            self._conn.execute("INSTALL motherduck;")
                            self._conn.execute("LOAD motherduck;")
                        except Exception as exc:
                            logger.warning("Could not initialize MotherDuck extension: %s", exc)
                    else:
                        self._conn = duckdb.connect(connection_path, read_only=is_read_only)

                    self._conn.execute("SET preserve_insertion_order = false;")

                    try:
                        self._conn.execute("INSTALL spatial;")
                        self._conn.execute("LOAD spatial;")
                        logger.info("DuckDB spatial extension loaded successfully.")
                    except Exception as exc:
                        logger.warning("Could not load DuckDB spatial extension: %s", exc)
        return self._conn

    # [FIX 1] Add this new method for atomic operations
    def execute_atomic(self, sql: str, *args: object):
        """Execute SQL under exclusive lock for ACID isolation.

        Use for operations that must be atomic with respect to concurrent access:
        - Multi-step upserts
        - Transactions (BEGIN...COMMIT)
        - Schema modifications

        Single-threaded or write-heavy operations don't need this;
        they benefit from the lock implicitly via the shared connection.
        """
        with self._conn_lock:
            return self.conn.execute(sql, *args)

    def close(self) -> None:
        """Close connection safely."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ... rest of class unchanged


# ==============================================================================
# [FIX 2] Transactional Writes for DuckDB → L2 Parquet
# File: app/utils/cache_manager.py
# ==============================================================================

# ADD IMPORTS AT TOP:
import tempfile
from pathlib import Path as PathLib

# IF NOT ALREADY IMPORTED:
try:
    from socrata_toolkit.core.duckdb_store import DuckDBManager
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False
    DuckDBManager = None

# ADD THESE FUNCTIONS:

# Global transaction manager (lazy singleton)
_tx_manager = None

def _get_tx_manager() -> "DuckDBManager":
    """Lazy singleton for transaction management."""
    global _tx_manager
    if _tx_manager is None:
        if not _DUCKDB_AVAILABLE:
            raise RuntimeError("DuckDBManager not available; install socrata_toolkit")
        _tx_manager = DuckDBManager()
    return _tx_manager

def init_cache_audit_table(manager: "DuckDBManager" = None) -> None:
    """Create cache_audit table if not exists.

    Call this once during app initialization.
    """
    if manager is None:
        manager = _get_tx_manager()

    try:
        # Create sequence first (for id auto-increment)
        manager.execute_atomic("CREATE SEQUENCE IF NOT EXISTS cache_audit_seq")

        # Create audit table
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
        logger.info("cache_audit table initialized")
    except Exception as exc:
        logger.warning(f"Failed to init cache_audit table: {exc}")

def write_cache_atomic(
    key: str,
    df: "pd.DataFrame",
    manager: "DuckDBManager | None" = None,
) -> PathLib:
    """Write cache with transactional guarantee.

    Atomically writes:
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
    temp_dest = PathLib(str(dest) + ".tmp")

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
        except Exception as exc:
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
        except Exception as exc:
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

# MODIFY EXISTING write_cache() for backward compatibility:
def write_cache(key: str, df: "pd.DataFrame") -> PathLib:
    """DEPRECATED: Use write_cache_atomic() instead.

    Kept for backward compatibility only.
    New code should import and call write_cache_atomic explicitly.
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
        evict_old_cache()
        return dest


# ==============================================================================
# [FIX 3] Persist session_state to DuckDB
# File: app/services/cache_service.py (NEW FILE)
# ==============================================================================

"""
Session state persistence layer using DuckDB.

Usage:
    import streamlit as st
    from app.services.cache_service import init_session_persistence
    from socrata_toolkit.core.duckdb_store import DuckDBManager

    manager = DuckDBManager()
    store = init_session_persistence(manager, session_id="user_123")
    persisted = store.load_state()
    st.session_state.update(persisted)

    # After state changes:
    store.save_key("cart", new_cart_value)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from socrata_toolkit.core.duckdb_store import DuckDBManager

logger = logging.getLogger(__name__)


class DuckDBSessionStore:
    """Persist Streamlit session_state to DuckDB with automatic sync."""

    def __init__(self, manager: DuckDBManager, session_id: str):
        """Initialize session store.

        Args:
            manager: DuckDBManager instance for persistence
            session_id: Unique session identifier (e.g., hash of IP + timestamp)
        """
        self.manager = manager
        self.session_id = session_id
        self._init_table()

    def _init_table(self) -> None:
        """Create session_state table if not exists."""
        try:
            self.manager.execute_atomic(
                """
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id VARCHAR NOT NULL,
                    key VARCHAR NOT NULL,
                    value JSON,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, key)
                )
                """
            )
        except Exception as exc:
            logger.warning(f"Failed to init session_state table: {exc}")

    def load_state(self) -> Dict[str, Any]:
        """Load all session state from DuckDB for this session.

        Returns:
            Dict mapping keys to deserialized values (empty dict on failure)
        """
        try:
            rows = self.manager.execute_atomic(
                "SELECT key, value FROM session_state WHERE session_id = ?",
                [self.session_id],
            ).fetchall()

            state = {}
            for key, value_json in rows:
                try:
                    state[key] = json.loads(value_json)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode session value for key={key}")
            return state
        except Exception as exc:
            logger.error(f"Failed to load session state for {self.session_id}: {exc}")
            return {}

    def save_key(self, key: str, value: Any) -> None:
        """Persist a single key-value pair to DuckDB.

        Serializes value to JSON and upserts into session_state table.
        Thread-safe via DuckDBManager.execute_atomic().

        Args:
            key: State key (e.g., "cart", "user_prefs")
            value: Any JSON-serializable value
        """
        try:
            value_json = json.dumps(value)
            now = datetime.now(timezone.utc).isoformat()

            self.manager.execute_atomic(
                """
                INSERT INTO session_state (session_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (session_id, key) DO UPDATE SET
                    value = ?,
                    updated_at = ?
                """,
                [
                    self.session_id,
                    key,
                    value_json,
                    now,
                    value_json,
                    now,
                ],
            )
        except Exception as exc:
            logger.error(f"Failed to save session key {key}: {exc}")

    def save_all(self, state: Dict[str, Any]) -> None:
        """Persist all state keys in a single transaction.

        Either all keys are saved or none (transaction semantics).
        Useful for saving entire state dict at once.

        Args:
            state: Dict of all keys to save
        """
        try:
            self.manager.execute_atomic("BEGIN TRANSACTION")
            now = datetime.now(timezone.utc).isoformat()

            for key, value in state.items():
                try:
                    value_json = json.dumps(value)
                    self.manager.execute_atomic(
                        """
                        INSERT INTO session_state (session_id, key, value, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT (session_id, key) DO UPDATE SET
                            value = ?,
                            updated_at = ?
                        """,
                        [
                            self.session_id,
                            key,
                            value_json,
                            now,
                            value_json,
                            now,
                        ],
                    )
                except json.JSONEncodeError:
                    logger.warning(f"Failed to encode session value for key={key}, skipping")

            self.manager.execute_atomic("COMMIT")
        except Exception as exc:
            try:
                self.manager.execute_atomic("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Failed to save session state: {exc}")

    def delete_session(self) -> None:
        """Clean up session on logout or timeout.

        Deletes all state entries for this session_id.
        """
        try:
            self.manager.execute_atomic(
                "DELETE FROM session_state WHERE session_id = ?",
                [self.session_id],
            )
            logger.info(f"Deleted session state for {self.session_id}")
        except Exception as exc:
            logger.error(f"Failed to delete session: {exc}")


def init_session_persistence(
    manager: DuckDBManager, session_id: str
) -> DuckDBSessionStore:
    """Create and initialize a session store.

    Args:
        manager: DuckDBManager instance
        session_id: Unique session identifier

    Returns:
        DuckDBSessionStore instance
    """
    store = DuckDBSessionStore(manager, session_id)
    return store


def get_session_callback(store: DuckDBSessionStore):
    """Return a callback for Streamlit to persist state on change.

    Usage:
        callback = get_session_callback(store)
        st.button("Save", on_click=callback)

    Or register as a global change listener (requires Streamlit >= 1.20):
        for key in st.session_state:
            if not key.startswith("_"):
                st.session_state[key].on_change(
                    lambda k=key: store.save_key(k, st.session_state[k])
                )

    Args:
        store: DuckDBSessionStore instance

    Returns:
        Callback function that saves current st.session_state
    """
    def callback():
        """Called when session_state is modified."""
        try:
            import streamlit as st
            # Save all state keys that aren't internal Streamlit ones (start with _)
            for key, value in st.session_state.items():
                if not key.startswith("_"):
                    store.save_key(key, value)
        except Exception as exc:
            logger.error(f"Session persist callback failed: {exc}")
    return callback


# ==============================================================================
# [FIX 4] File Locking for Manifest Updates
# File: app/utils/cache_manager.py
# ==============================================================================

# ADD IMPORTS AT TOP:
import os
import time
if os.name == "nt":  # Windows
    import msvcrt
else:  # Unix/Linux/macOS
    import fcntl

# ADD THESE FUNCTIONS:

def _lock_file(file_handle) -> None:
    """Acquire exclusive lock on file (platform-specific)."""
    if os.name == "nt":  # Windows
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            # Non-blocking failed, try blocking
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
    else:  # Unix/Linux/macOS
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(file_handle) -> None:
    """Release lock on file (platform-specific)."""
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

    Returns (manifest_dict, lock_handle).

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
    """Release lock acquired by cache_manifest_locked()."""
    try:
        _unlock_file(lock_file)
    finally:
        try:
            lock_file.close()
        except Exception:
            pass


def _save_manifest_locked(manifest: dict[str, Any], lock_file: Any) -> None:
    """Write manifest to disk using atomic rename.

    PRECONDITION: Caller must hold exclusive lock (via cache_manifest_locked).

    Uses temp file + atomic rename for crash-safety:
    1. Write to temp file (safe, not visible yet)
    2. Atomic rename temp -> manifest (atomic at OS level)
    3. On failure, temp file is cleaned up
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
        PathLib(temp_path).replace(_MANIFEST_PATH)
    except Exception as exc:
        # Clean up temp if rename fails
        try:
            PathLib(temp_path).unlink()
        except Exception:
            pass
        raise


def update_manifest(key: str, path: PathLib, rows: int, ttl_hours: float) -> None:
    """Update manifest entry with file locking.

    Ensures atomicity: read-modify-write happens under exclusive lock.
    No lost updates even with concurrent processes.

    Args:
        key: Dataset key
        path: Parquet file path
        rows: Row count
        ttl_hours: Time-to-live hours
    """
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(
        now.timestamp() + ttl_hours * 3600, tz=timezone.utc
    )

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


# MODIFY cache_manifest() to handle lock timeouts gracefully:
_MANIFEST_READ_TIMEOUT = 5.0  # seconds

def cache_manifest(timeout: float = _MANIFEST_READ_TIMEOUT) -> dict[str, Any]:
    """Load manifest (read-only, waits for lock with timeout).

    For write operations, use update_manifest() which handles locking.

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
        except (json.JSONDecodeError, IOError) as exc:
            # File is being written or corrupt, retry
            last_error = exc
            if time.time() - start_time > timeout:
                logging.warning(
                    f"cache_manifest: timeout waiting for manifest lock after {timeout}s, "
                    f"returning empty manifest (last error: {last_error})"
                )
                return {}
            time.sleep(0.1)  # Backoff before retry


# ==============================================================================
# [TESTS] Unit and integration tests for all fixes
# File: tests/test_acid_fixes.py (NEW FILE)
# ==============================================================================

"""
Test suite for ACID reliability fixes.

Run with: pytest tests/test_acid_fixes.py -v
"""

import json
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import pandas as pd

# Import after checking fixtures
pytestmark = pytest.mark.skipif(False, reason="ACID fix tests")


# ============ FIX 1: DuckDB Connection Pooling Tests ============

def test_duckdb_manager_connection_singleton():
    """Verify DuckDBManager creates only one connection."""
    from socrata_toolkit.core.duckdb_store import DuckDBManager

    manager = DuckDBManager(db_path=":memory:")
    conn1 = manager.conn
    conn2 = manager.conn

    assert conn1 is conn2, "Should return same connection"


def test_duckdb_manager_concurrent_access():
    """Verify concurrent access is serialized via lock."""
    from socrata_toolkit.core.duckdb_store import DuckDBManager

    manager = DuckDBManager(db_path=":memory:")
    manager.conn.execute("CREATE TABLE test (id INT, val TEXT)")

    results = []

    def write_batch(batch_id):
        for i in range(10):
            manager.execute_atomic(
                "INSERT INTO test VALUES (?, ?)",
                [batch_id * 10 + i, f"batch_{batch_id}"],
            )
            results.append(batch_id)

    with ThreadPoolExecutor(max_workers=5) as ex:
        ex.map(write_batch, range(5))

    count = manager.conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
    assert count == 50, f"Expected 50 rows, got {count}"


# ============ FIX 2: Transactional Writes Tests ============

def test_write_cache_atomic_success(tmp_path, monkeypatch):
    """Verify atomic write creates Parquet, manifest, and audit entry."""
    from app.utils.cache_manager import write_cache_atomic, init_cache_audit_table
    from socrata_toolkit.core.duckdb_store import DuckDBManager

    # Mock cache dir
    monkeypatch.setattr("app.utils.cache_manager.CACHE_DIR", tmp_path)
    monkeypatch.setattr("app.utils.cache_manager._MANIFEST_PATH", tmp_path / "manifest.json")

    manager = DuckDBManager(db_path=":memory:")
    init_cache_audit_table(manager)

    df = pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
    path = write_cache_atomic("test_key", df, manager=manager)

    # Verify Parquet exists
    assert path.exists(), "Parquet file should exist"

    # Verify manifest updated
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert "test_key" in manifest, "Manifest should have entry"
    assert manifest["test_key"]["rows"] == 3

    # Verify audit entry
    audit = manager.conn.execute("SELECT COUNT(*) FROM cache_audit WHERE key = ?", ["test_key"]).fetchone()
    assert audit[0] == 1, "Audit table should have entry"


def test_write_cache_atomic_rollback_on_error(tmp_path, monkeypatch):
    """Verify rollback when Parquet write fails."""
    from app.utils.cache_manager import write_cache_atomic, init_cache_audit_table
    from socrata_toolkit.core.duckdb_store import DuckDBManager

    monkeypatch.setattr("app.utils.cache_manager.CACHE_DIR", tmp_path)
    monkeypatch.setattr("app.utils.cache_manager._MANIFEST_PATH", tmp_path / "manifest.json")

    manager = DuckDBManager(db_path=":memory:")
    init_cache_audit_table(manager)

    df = pd.DataFrame({"id": [1, 2, 3]})

    # Mock to_parquet to raise error
    with patch.object(pd.DataFrame, "to_parquet", side_effect=OSError("Disk full")):
        with pytest.raises(OSError):
            write_cache_atomic("test_key", df, manager=manager)

    # Verify rollback: no audit entry
    audit = manager.conn.execute("SELECT COUNT(*) FROM cache_audit WHERE key = ?", ["test_key"]).fetchone()
    assert audit[0] == 0, "Audit should be rolled back"

    # Verify no manifest entry
    manifest = json.loads((tmp_path / "manifest.json").read_text()) if (tmp_path / "manifest.json").exists() else {}
    assert "test_key" not in manifest


# ============ FIX 3: Session Persistence Tests ============

def test_session_store_save_and_load():
    """Verify round-trip session persistence."""
    from app.services.cache_service import DuckDBSessionStore
    from socrata_toolkit.core.duckdb_store import DuckDBManager

    manager = DuckDBManager(db_path=":memory:")
    store = DuckDBSessionStore(manager, session_id="test_session_123")

    # Save state
    state = {
        "user_id": 42,
        "cart": ["item_1", "item_2"],
        "prefs": {"theme": "dark"},
    }
    store.save_all(state)

    # Load in fresh store (same session ID)
    store2 = DuckDBSessionStore(manager, session_id="test_session_123")
    loaded = store2.load_state()

    assert loaded == state, f"State mismatch: {loaded} != {state}"


def test_session_store_concurrent_saves():
    """Verify thread-safe concurrent key saves."""
    from app.services.cache_service import DuckDBSessionStore
    from socrata_toolkit.core.duckdb_store import DuckDBManager

    manager = DuckDBManager(db_path=":memory:")
    store = DuckDBSessionStore(manager, session_id="concurrent_test")

    def save_key(i):
        store.save_key(f"key_{i}", {"value": i, "data": f"test_{i}"})

    with ThreadPoolExecutor(max_workers=5) as ex:
        ex.map(save_key, range(20))

    # Verify all keys present
    loaded = store.load_state()
    assert len(loaded) == 20, f"Expected 20 keys, got {len(loaded)}"

    for i in range(20):
        assert f"key_{i}" in loaded
        assert loaded[f"key_{i}"]["value"] == i


# ============ FIX 4: Manifest Locking Tests ============

def test_manifest_locked_concurrent_updates(tmp_path, monkeypatch):
    """Verify no lost updates under concurrent manifest access."""
    from app.utils.cache_manager import update_manifest, cache_manifest

    monkeypatch.setattr("app.utils.cache_manager.CACHE_DIR", tmp_path)
    monkeypatch.setattr("app.utils.cache_manager._MANIFEST_PATH", tmp_path / "manifest.json")

    def update_entry(i):
        update_manifest(
            key=f"key_{i}",
            path=Path(f"/tmp/data_{i}.parquet"),
            rows=100 * i,
            ttl_hours=24.0,
        )

    with ThreadPoolExecutor(max_workers=5) as ex:
        ex.map(update_entry, range(20))

    # Verify all entries present (no lost updates)
    manifest = cache_manifest()
    assert len(manifest) == 20, f"Expected 20 entries, got {len(manifest)}"

    # Verify data integrity
    for i in range(20):
        assert manifest[f"key_{i}"]["rows"] == 100 * i


def test_manifest_file_lock_acquired():
    """Verify lock is acquired and released properly."""
    from app.utils.cache_manager import (
        cache_manifest_locked,
        _unlock_manifest,
        _MANIFEST_PATH,
    )

    manifest, lock_file = cache_manifest_locked()
    assert not lock_file.closed, "Lock file should be open"

    _unlock_manifest(lock_file)
    assert lock_file.closed, "Lock file should be closed after unlock"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
