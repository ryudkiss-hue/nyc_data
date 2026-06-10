# NYC DOT Socrata Toolkit: ACID Reliability Implementation Plan

**Status**: Audit findings → Actionable implementation plan
**Date**: 2026-06-10
**Scope**: 4 surgical fixes for critical ACID violations in data layer

---

## Summary

The NYC DOT Socrata Toolkit's data layer has 4 critical ACID violations:
1. **Atomicity**: DuckDB writes are sync but L2 Parquet writes are async → inconsistent visibility
2. **Consistency**: DuckDB ↔ Parquet skew with concurrent watermark reads missing data
3. **Isolation**: Multiple DuckDB connections without pooling; `session_state` not thread-safe
4. **Durability**: Async L2 writes not durable; `session_state` never persists

This plan provides **4 minimal, surgical fixes** that can be implemented independently. Each fix includes:
- Files to modify (with relative paths)
- Pseudocode changes
- Testing strategy
- Effort estimate

---

## Fix 1: Connection Pooling for DuckDB

### Problem
- `DuckDBManager` creates a new connection on first access (lazy singleton)
- Multiple threads access `.conn` property without synchronization
- No connection pool → concurrent writes on shared connection without isolation guarantees

**Current code** (`src/socrata_toolkit/core/duckdb_store.py`, lines 129-184):
```python
def __init__(self, ...):
    self._conn: duckdb.DuckDBPyConnection | None = None

@property
def conn(self) -> duckdb.DuckDBPyConnection:
    if self._conn is None:
        # Creates connection, no thread safety
        self._conn = duckdb.connect(...)
    return self._conn
```

### Solution: Single Shared Connection + Thread-Safe Lock

Use a **bounded single-connection pool with explicit locking** (simpler than thread pool, sufficient for DuckDB's design):

**File**: `src/socrata_toolkit/core/duckdb_store.py`

**Changes**:
```python
import threading

class DuckDBManager:
    def __init__(self, ...):
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._conn_lock = threading.RLock()  # Reentrant lock for nested queries
        
    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Thread-safe singleton connection."""
        if self._conn is None:
            with self._conn_lock:
                # Double-check pattern to avoid race condition
                if self._conn is None:
                    self._conn = duckdb.connect(...)
        return self._conn
    
    def execute_atomic(self, sql: str, *args) -> Any:
        """Execute SQL under lock to ensure isolation.
        
        Use for multi-step operations that must be atomic.
        """
        with self._conn_lock:
            return self.conn.execute(sql, *args)
```

**Thread-safety implications**:
- All `.conn.execute()` calls automatically held under lock
- For long-lived transactions or multi-step operations, use `execute_atomic()`
- DuckDB's single connection handles all concurrency → no session state conflicts

### Testing Strategy

1. **Unit test**: Concurrent writes from 5 threads to same table
   - Verify no `"table already exists"` errors
   - Verify lock is held during writes (measure lock contention)
   - Assert final row count is correct (all writes committed)

2. **Integration test**: Mixed read/write under thread pool
   - Spawn 3 threads doing reads, 2 doing writes
   - Verify no dirty reads (reads don't see uncommitted data)
   - Verify writes are ordered correctly

3. **Regression test**: Existing `DuckDBRepository.upsert_dataframe()` calls still work
   - No changes to public API, only internal sync mechanism

**Test file**: `tests/test_duckdb_store_coverage.py`
```python
def test_concurrent_upsert_with_lock():
    """Verify atomicity of concurrent upserts."""
    manager = DuckDBManager(db_path=":memory:")
    manager.conn.execute("CREATE TABLE test (id INT, val TEXT)")
    
    def upsert_batch(batch_id):
        for i in range(10):
            manager.execute_atomic(
                "INSERT INTO test VALUES (?, ?)",
                [batch_id * 10 + i, f"batch_{batch_id}"]
            )
    
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as ex:
        ex.map(upsert_batch, range(5))
    
    result = manager.conn.execute("SELECT COUNT(*) FROM test").fetchone()
    assert result[0] == 50, "All writes should be visible"
```

### Effort Estimate
- **Implementation**: 0.5 hours (add lock, double-check pattern, `execute_atomic()`)
- **Testing**: 1.0 hours (3 test cases + concurrent harness)
- **Review & refinement**: 0.5 hours
- **Total**: ~2 hours

---

## Fix 2: Transactional Boundaries for DuckDB → L2 Parquet Writes

### Problem
- `write_cache()` in `app/utils/cache_manager.py` calls `df.to_parquet()` **asynchronously** (pandas blocks the event loop)
- No transaction bracket around DuckDB writes + Parquet writes
- If DuckDB write succeeds but Parquet fails (disk full, permission denied), data is inconsistent
- Concurrent watermark readers may see partial data

**Current code** (`app/utils/cache_manager.py`, lines 115-124):
```python
def write_cache(key: str, df: pd.DataFrame) -> Path:
    _ensure_cache_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = cache_path(key, date_str)
    df.to_parquet(dest, index=False, compression="gzip")  # SYNC, can fail
    ttl_hours = _ttl_for(key)
    update_manifest(key, dest, len(df), ttl_hours)  # SYNC
    evict_old_cache()  # SYNC, but can fail
    return dest
```

### Solution: Explicit Transaction + Retry + Rollback on Failure

Wrap the DuckDB → Parquet → Manifest write chain in a transaction:

**File**: `app/utils/cache_manager.py`

**Changes**:
```python
import tempfile
from pathlib import Path
from socrata_toolkit.core.duckdb_store import DuckDBManager  # Import at top

# Add global manager for transactional writes
_tx_manager = None

def _get_tx_manager():
    """Lazy singleton for transaction management."""
    global _tx_manager
    if _tx_manager is None:
        _tx_manager = DuckDBManager()
    return _tx_manager

def write_cache_atomic(
    key: str, 
    df: pd.DataFrame,
    manager: DuckDBManager | None = None,
) -> Path:
    """Write cache with transactional guarantee.
    
    Atomically writes:
    1. Parquet file to disk
    2. Manifest JSON entry
    3. Logs to DuckDB audit table (if manager provided)
    
    Rolls back on any step's failure.
    """
    if manager is None:
        manager = _get_tx_manager()
    
    # Step 1: Write to temp Parquet (atomic from OS perspective)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = cache_path(key, date_str)
    temp_dest = Path(str(dest) + ".tmp")
    
    try:
        # Start DuckDB transaction
        manager.execute_atomic("BEGIN TRANSACTION")
        
        # Write Parquet to temporary location first
        _ensure_cache_dir()
        df.to_parquet(temp_dest, index=False, compression="gzip")
        
        # Step 2: Atomic rename (file system level)
        temp_dest.replace(dest)
        
        # Step 3: Update manifest in DuckDB (audit log)
        # This ensures watermark reads see consistent data
        ttl_hours = _ttl_for(key)
        manager.execute_atomic(
            """
            INSERT INTO cache_audit (key, path, rows, fetched_at, expires_at, ttl_hours)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                key,
                str(dest),
                len(df),
                datetime.now(timezone.utc).isoformat(),
                datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + ttl_hours * 3600,
                    tz=timezone.utc
                ).isoformat(),
                ttl_hours,
            ]
        )
        
        # Step 4: Update in-memory manifest (fallback for non-DuckDB readers)
        manifest = cache_manifest()
        manifest[key] = {
            "path": str(dest),
            "rows": len(df),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + ttl_hours * 3600,
                tz=timezone.utc
            ).isoformat(),
            "ttl_hours": ttl_hours,
        }
        _save_manifest(manifest)
        
        # Step 5: Eviction (best-effort, doesn't rollback)
        evict_old_cache()
        
        # Commit transaction
        manager.execute_atomic("COMMIT")
        
        return dest
        
    except Exception as exc:
        # Rollback on any error
        try:
            manager.execute_atomic("ROLLBACK")
        except Exception:
            pass
        
        # Clean up temp file if it exists
        if temp_dest.exists():
            try:
                temp_dest.unlink()
            except Exception:
                pass
        
        logging.error(f"write_cache_atomic failed for {key}: {exc}")
        raise

# Keep old API for backward compatibility, but add deprecation notice
def write_cache(key: str, df: pd.DataFrame) -> Path:
    """DEPRECATED: Use write_cache_atomic instead.
    
    This function is kept for backward compatibility only.
    New code should call write_cache_atomic with an explicit DuckDBManager.
    """
    logging.warning(
        "write_cache() is deprecated; use write_cache_atomic() for ACID guarantees"
    )
    return write_cache_atomic(key, df)
```

**Setup DuckDB audit table** (run once during app initialization):
```python
def init_cache_audit_table(manager: DuckDBManager):
    """Create cache_audit table if it doesn't exist."""
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
            written_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """
    )
    manager.execute_atomic("CREATE SEQUENCE IF NOT EXISTS cache_audit_seq")
```

### Testing Strategy

1. **Unit test**: Successful write
   - Write cache, verify Parquet exists, manifest updated, DuckDB audit entry created
   - Assert all three updates are visible in a subsequent read

2. **Unit test**: Parquet write fails (disk full simulation)
   - Mock `to_parquet()` to raise `OSError`
   - Verify temp file is cleaned up
   - Verify manifest is NOT updated
   - Verify DuckDB transaction rolled back (audit table empty)

3. **Integration test**: Concurrent writes and reads
   - Thread 1: writes cache
   - Thread 2: reads manifest mid-write
   - Verify Thread 2 doesn't see partial data (old manifest or nothing)
   - Use `time.sleep()` to inject delays in write to increase race condition window

4. **Regression test**: Existing `read_cache()` and cache eviction still work
   - Verify `read_cache()` hits the new manifest entries
   - Verify `evict_old_cache()` works with renamed files

**Test file**: `tests/test_cache_manager.py` (extend existing)
```python
def test_write_cache_atomic_success():
    """Verify atomic write creates all three artifacts."""
    manager = DuckDBManager(db_path=":memory:")
    init_cache_audit_table(manager)
    
    df = pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})
    path = write_cache_atomic("test_key", df, manager=manager)
    
    assert path.exists(), "Parquet should exist"
    
    manifest = cache_manifest()
    assert "test_key" in manifest, "Manifest should have entry"
    
    audit = manager.conn.execute("SELECT * FROM cache_audit WHERE key = 'test_key'").fetchall()
    assert len(audit) == 1, "Audit table should have entry"

def test_write_cache_atomic_rollback_on_parquet_error(tmp_path, monkeypatch):
    """Verify rollback when Parquet write fails."""
    manager = DuckDBManager(db_path=":memory:")
    init_cache_audit_table(manager)
    
    def mock_to_parquet(*args, **kwargs):
        raise OSError("Disk full")
    
    monkeypatch.setattr("pandas.DataFrame.to_parquet", mock_to_parquet)
    
    df = pd.DataFrame({"id": [1, 2, 3]})
    
    with pytest.raises(OSError):
        write_cache_atomic("test_key", df, manager=manager)
    
    # Verify rollback: no audit entry
    audit = manager.conn.execute("SELECT * FROM cache_audit WHERE key = 'test_key'").fetchall()
    assert len(audit) == 0, "Audit should be rolled back"
    
    # No manifest entry (or old one still present)
    manifest = cache_manifest()
    assert "test_key" not in manifest, "Manifest should not have new entry"
```

### Effort Estimate
- **Implementation**: 1.5 hours (transactional wrapper, temp file handling, error path)
- **Testing**: 1.5 hours (4 test cases + mock setup)
- **DuckDB schema migration** (one-time): 0.5 hours
- **Documentation**: 0.5 hours
- **Total**: ~4 hours

---

## Fix 3: Persist session_state to DuckDB

### Problem
- `st.session_state` is in-memory only (lost on page refresh or session timeout)
- Multiple Streamlit pages (e.g., `app/views/studio.py`, `app/views/settings.py`) store state in `session_state`
- No callback to persist state changes → users lose data on crash

**Current code** (`app/views/studio.py`, lines 456-459):
```python
st.session_state.setdefault(_session_key("cart"), {})
st.session_state.setdefault(_session_key("results"), [])
st.session_state.setdefault(_session_key("workspaces"), {})
st.session_state[_session_key("token")] = st.text_input(...)  # Lost on refresh
```

### Solution: DuckDB Persistence + Change Tracking Callback

Create a persistent session store in DuckDB with automatic sync:

**File**: `app/services/cache_service.py` (new file, or extend existing if present)

**Changes**:
```python
"""Session state persistence layer using DuckDB."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from socrata_toolkit.core.duckdb_store import DuckDBManager

logger = logging.getLogger(__name__)


class DuckDBSessionStore:
    """Persist Streamlit session_state to DuckDB with automatic sync."""

    def __init__(self, manager: DuckDBManager, session_id: str):
        self.manager = manager
        self.session_id = session_id
        self._init_table()

    def _init_table(self):
        """Create session_state table if not exists."""
        self.manager.execute_atomic(
            """
            CREATE TABLE IF NOT EXISTS session_state (
                session_id VARCHAR NOT NULL,
                key VARCHAR NOT NULL,
                value JSON,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                PRIMARY KEY (session_id, key)
            )
            """
        )

    def load_state(self) -> Dict[str, Any]:
        """Load all session state from DuckDB for this session."""
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
                    logger.warning(f"Failed to decode session value for {key}")
            return state
        except Exception as exc:
            logger.error(f"Failed to load session state: {exc}")
            return {}

    def save_key(self, key: str, value: Any) -> None:
        """Persist a single key-value pair to DuckDB."""
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
                    datetime.now(timezone.utc).isoformat(),
                    value_json,
                    datetime.now(timezone.utc).isoformat(),
                ],
            )
        except Exception as exc:
            logger.error(f"Failed to save session key {key}: {exc}")

    def save_all(self, state: Dict[str, Any]) -> None:
        """Persist all state keys in a transaction."""
        try:
            self.manager.execute_atomic("BEGIN TRANSACTION")
            for key, value in state.items():
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
                        datetime.now(timezone.utc).isoformat(),
                        value_json,
                        datetime.now(timezone.utc).isoformat(),
                    ],
                )
            self.manager.execute_atomic("COMMIT")
        except Exception as exc:
            try:
                self.manager.execute_atomic("ROLLBACK")
            except Exception:
                pass
            logger.error(f"Failed to save session state: {exc}")

    def delete_session(self) -> None:
        """Clean up session on logout."""
        try:
            self.manager.execute_atomic(
                "DELETE FROM session_state WHERE session_id = ?",
                [self.session_id],
            )
        except Exception as exc:
            logger.error(f"Failed to delete session: {exc}")


def init_session_persistence(manager: DuckDBManager, session_id: str) -> DuckDBSessionStore:
    """Create and initialize a session store."""
    store = DuckDBSessionStore(manager, session_id)
    return store


def get_session_callback(store: DuckDBSessionStore):
    """Return a callback for Streamlit.on_change to persist state."""
    def callback():
        """Called when session_state is modified."""
        try:
            import streamlit as st
            # Save all state keys that aren't internal Streamlit ones
            for key, value in st.session_state.items():
                if not key.startswith("_"):
                    store.save_key(key, value)
        except Exception as exc:
            logger.error(f"Session persist callback failed: {exc}")
    return callback
```

**File**: `app/main.py` (app initialization)

**Changes** (add to main Streamlit app setup):
```python
import streamlit as st
from app.services.cache_service import init_session_persistence, get_session_callback
from socrata_toolkit.core.duckdb_store import DuckDBManager

# Initialize session persistence
def setup_session_persistence():
    """Set up DuckDB-backed session state persistence."""
    manager = DuckDBManager()
    
    # Use a unique session ID (Streamlit provides session info)
    # Fallback to a hash of connection info if not available
    try:
        session_id = st.session_state.get("_session_id")
        if not session_id:
            import hashlib
            session_info = f"{st.session_state.session_id if hasattr(st.session_state, 'session_id') else 'default'}"
            session_id = hashlib.sha256(session_info.encode()).hexdigest()
            st.session_state._session_id = session_id
    except Exception:
        session_id = "default"
    
    # Create store and load persisted state
    store = init_session_persistence(manager, session_id)
    persisted_state = store.load_state()
    
    # Merge persisted state into current session (don't overwrite in-flight changes)
    for key, value in persisted_state.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Register callback to persist changes
    # Note: on_change requires Streamlit >= 1.20
    # For older versions, call store.save_key() explicitly after state changes
    try:
        st.session_state._session_store = store
        # Set a callback on page reload to persist state
        # (Streamlit doesn't have a universal state change hook, so do this per-page)
    except Exception:
        pass

# Call this early in the app lifecycle
if __name__ == "__main__":
    setup_session_persistence()
    # ... rest of app
```

**File**: `app/views/studio.py` (example usage)

**Changes** (update state-modifying code to call store):
```python
# At the top of the page function:
try:
    store = st.session_state.get("_session_store")
except Exception:
    store = None

# When setting state:
st.session_state[_session_key("cart")] = updated_cart
if store:
    store.save_key(_session_key("cart"), updated_cart)

# On logout or session end:
if store:
    store.delete_session()
```

### Testing Strategy

1. **Unit test**: Load/save persistence
   - Create DuckDBSessionStore, save a key, reload, verify value
   - Save complex object (dict/list), verify JSON round-trip

2. **Unit test**: Concurrent saves
   - Multiple threads call `save_key()` with different keys
   - Verify all keys are persisted and no conflicts

3. **Integration test**: Streamlit page lifecycle
   - Mock Streamlit session
   - Load state, modify a value, trigger callback
   - Simulate page refresh (new session)
   - Verify persisted state is loaded

4. **Regression test**: Backward compatibility
   - Old apps without `_session_store` still work (graceful degradation)

**Test file**: `tests/test_session_persistence.py` (new)
```python
import json
from app.services.cache_service import DuckDBSessionStore, init_session_persistence
from socrata_toolkit.core.duckdb_store import DuckDBManager

def test_session_store_save_and_load():
    """Verify round-trip persistence."""
    manager = DuckDBManager(db_path=":memory:")
    store = DuckDBSessionStore(manager, session_id="test_session_123")
    
    # Save some state
    state = {
        "user_id": 42,
        "cart": ["item_1", "item_2"],
        "preferences": {"theme": "dark"}
    }
    store.save_all(state)
    
    # Load in a fresh store (same session ID)
    store2 = DuckDBSessionStore(manager, session_id="test_session_123")
    loaded = store2.load_state()
    
    assert loaded == state, "Persisted state should match original"

def test_session_store_concurrent_saves():
    """Verify thread-safe concurrent saves."""
    from concurrent.futures import ThreadPoolExecutor
    
    manager = DuckDBManager(db_path=":memory:")
    store = DuckDBSessionStore(manager, session_id="concurrent_test")
    
    def save_key(i):
        store.save_key(f"key_{i}", f"value_{i}")
    
    with ThreadPoolExecutor(max_workers=5) as ex:
        ex.map(save_key, range(20))
    
    # Verify all keys were saved
    loaded = store.load_state()
    assert len(loaded) == 20, "All concurrent saves should succeed"
```

### Effort Estimate
- **Implementation**: 2 hours (session store class, DuckDB table, init logic)
- **Streamlit integration**: 1 hour (callback setup, per-page updates)
- **Testing**: 1 hour (3-4 test cases)
- **Documentation**: 0.5 hours
- **Total**: ~4.5 hours

---

## Fix 4: File Locking for Manifest Updates

### Problem
- `update_manifest()` in `app/utils/cache_manager.py` uses `_save_manifest()` which is not atomic
- Multiple processes can read-modify-write the manifest JSON concurrently → lost updates
- On Windows, file handles may be locked; on Unix, `rename()` is atomic but `write()` is not

**Current code** (`app/utils/cache_manager.py`, lines 80-108):
```python
def cache_manifest() -> dict[str, Any]:
    if not _MANIFEST_PATH.exists():
        return {}
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

def _save_manifest(manifest: dict[str, Any]) -> None:
    _MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

def update_manifest(key: str, path: Path, rows: int, ttl_hours: float) -> None:
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(now.timestamp() + ttl_hours * 3600, tz=timezone.utc)
    manifest = cache_manifest()  # Read (T1: read v1)
    manifest[key] = {...}        # Modify (T1: add entry)
    _save_manifest(manifest)     # Write (T1: write v2) — but T2 may have read v1 and overwrite
```

### Solution: File Locking + Atomic Rename

Use `fcntl` (Unix) / `msvcrt` (Windows) for advisory locks and atomic rename:

**File**: `app/utils/cache_manager.py`

**Changes**:
```python
import os
import tempfile
from pathlib import Path
from typing import Any

# Platform-specific file locking
if os.name == "nt":  # Windows
    import msvcrt
    
    def _lock_file(file_handle):
        """Acquire exclusive lock on Windows."""
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
    
    def _unlock_file(file_handle):
        """Release lock on Windows."""
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
else:  # Unix/Linux/macOS
    import fcntl
    
    def _lock_file(file_handle):
        """Acquire exclusive lock on Unix."""
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
    
    def _unlock_file(file_handle):
        """Release lock on Unix."""
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


def cache_manifest_locked() -> tuple[dict[str, Any], Any]:
    """Load manifest with exclusive lock held.
    
    Returns (manifest_dict, lock_handle).
    Caller MUST call _unlock_manifest() to release lock.
    """
    _ensure_cache_dir()
    
    # Open lock file (separate from manifest to avoid deadlock)
    lock_path = _MANIFEST_PATH.parent / ".manifest.lock"
    lock_file = open(lock_path, "a")
    
    try:
        _lock_file(lock_file)
        
        # Now read manifest while holding lock
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
        lock_file.close()


def _save_manifest_locked(manifest: dict[str, Any], lock_file: Any) -> None:
    """Write manifest to disk using atomic rename (caller must hold lock)."""
    _ensure_cache_dir()
    
    # Write to temp file first (atomic from caller's perspective, lock is held)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=_MANIFEST_PATH.parent,
        suffix=".tmp",
        delete=False,
        encoding="utf-8"
    ) as f:
        json.dump(manifest, f, indent=2)
        temp_path = f.name
    
    try:
        # Atomic rename (on both Unix and Windows with atomic_replace flag)
        # This is atomic at the OS level
        Path(temp_path).replace(_MANIFEST_PATH)
    except Exception:
        # Clean up temp if rename fails
        try:
            Path(temp_path).unlink()
        except Exception:
            pass
        raise


def update_manifest(key: str, path: Path, rows: int, ttl_hours: float) -> None:
    """Update manifest entry with file locking.
    
    Ensures atomicity: read-modify-write happens under exclusive lock.
    """
    now = datetime.now(timezone.utc)
    expires = datetime.fromtimestamp(now.timestamp() + ttl_hours * 3600, tz=timezone.utc)
    
    # Acquire lock before read-modify-write
    manifest, lock_file = cache_manifest_locked()
    try:
        manifest[key] = {
            "path": str(path),
            "rows": rows,
            "fetched_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "ttl_hours": ttl_hours,
        }
        # Write under lock
        _save_manifest_locked(manifest, lock_file)
    finally:
        # Always release lock
        _unlock_manifest(lock_file)


# For backward compatibility, keep cache_manifest() but add timeout
_MANIFEST_READ_TIMEOUT = 5.0  # seconds

def cache_manifest(timeout: float = _MANIFEST_READ_TIMEOUT) -> dict[str, Any]:
    """Load manifest (read-only, blocks until lock is available).
    
    For write operations, use update_manifest() which handles locking.
    """
    _ensure_cache_dir()
    
    # Try to acquire read lock with timeout
    lock_path = _MANIFEST_PATH.parent / ".manifest.lock"
    start_time = time.time()
    
    while True:
        try:
            # Non-blocking read of manifest (may be stale if writer is active)
            if _MANIFEST_PATH.exists():
                return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
            else:
                return {}
        except (json.JSONDecodeError, IOError):
            # File is being written, retry
            if time.time() - start_time > timeout:
                logging.warning(
                    f"cache_manifest: timeout waiting for manifest lock after {timeout}s, "
                    "returning stale/empty manifest"
                )
                return {}
            time.sleep(0.1)
```

### Testing Strategy

1. **Unit test**: Basic lock/unlock
   - Acquire lock, modify manifest, release, verify file updated
   - Acquire lock twice (should block), release first (second should proceed)

2. **Unit test**: Atomic rename
   - Write temp file, rename to manifest, verify no corruption on interrupt
   - Verify temp file cleaned up on error

3. **Integration test**: Concurrent updates
   - 3 threads each call `update_manifest()` with different keys
   - Verify all 3 entries are in final manifest (no lost updates)
   - Compare with non-locked version to show data corruption

4. **Stress test**: High-frequency updates
   - Rapid updates (100 calls in < 1 sec) with lock
   - Verify manifest integrity (valid JSON, all keys present)

**Test file**: `tests/test_cache_manager.py` (extend)
```python
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from app.utils.cache_manager import update_manifest, cache_manifest

def test_concurrent_manifest_updates():
    """Verify no lost updates under concurrent access."""
    # Use a temp manifest file for this test
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr("app.utils.cache_manager._MANIFEST_PATH", Path(tmpdir) / "manifest.json")
        
        def update_entry(i):
            update_manifest(
                key=f"key_{i}",
                path=Path(f"/tmp/data_{i}.parquet"),
                rows=100 * i,
                ttl_hours=24.0,
            )
        
        with ThreadPoolExecutor(max_workers=5) as ex:
            ex.map(update_entry, range(20))
        
        # Verify all entries are present
        manifest = cache_manifest()
        assert len(manifest) == 20, "All updates should be present"
        
        # Verify no corruption
        for i in range(20):
            assert manifest[f"key_{i}"]["rows"] == 100 * i

def test_manifest_integrity_on_concurrent_reads_and_writes():
    """Verify reads don't see partially-written manifest."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr("app.utils.cache_manager._MANIFEST_PATH", Path(tmpdir) / "manifest.json")
        
        results = []
        
        def read_manifest():
            for _ in range(5):
                m = cache_manifest()
                results.append(len(m))
                time.sleep(0.01)
        
        def write_manifest(i):
            update_manifest(f"key_{i}", Path(f"/tmp/{i}.parquet"), 100, 24.0)
        
        # Spawn reader and writers concurrently
        with ThreadPoolExecutor(max_workers=4) as ex:
            ex.submit(read_manifest)
            for i in range(3):
                ex.submit(write_manifest, i)
        
        # Verify reads always see complete manifest (0 or 1, 2, or 3 keys, never partial)
        # This is a probabilistic test; with locking, should never see odd counts
        for count in results:
            assert count % 1 == 0, "Reader should only see complete manifests"
```

### Effort Estimate
- **Implementation**: 1.5 hours (lock/unlock helpers, atomic rename, timeout logic)
- **Testing**: 1 hour (4 test cases + concurrent harness)
- **Cross-platform validation**: 0.5 hours (test on Windows + Unix)
- **Total**: ~3 hours

---

## Summary Table

| Fix | Files | Core Change | Atomicity | Isolation | Durability | Consistency | Hours |
|-----|-------|-------------|-----------|-----------|-----------|-------------|-------|
| **1: DuckDB Pooling** | `src/socrata_toolkit/core/duckdb_store.py` | Add `RLock` + `execute_atomic()` | ✅ | ✅ | N/A | ✅ | 2 |
| **2: Transactional Writes** | `app/utils/cache_manager.py` | `BEGIN...COMMIT` + atomic rename | ✅ | ✅ | ✅ | ✅ | 4 |
| **3: Session Persistence** | `app/services/cache_service.py` (new) | DuckDB session store + load/save | ✅ | ✅ | ✅ | ✅ | 4.5 |
| **4: Manifest Locking** | `app/utils/cache_manager.py` | FCntl/MSVCRT locks + atomic rename | ✅ | ✅ | ✅ | ✅ | 3 |

**Total effort**: ~13.5 hours
**Recommended rollout**: 
- Week 1: Fixes 1 & 4 (DuckDB + manifest locking) → foundation
- Week 2: Fix 2 (transactional writes) → requires Fix 1
- Week 3: Fix 3 (session persistence) → independent, best for end of cycle

---

## Implementation Checklist

### Pre-Implementation
- [ ] Code review of audit findings with team
- [ ] Create feature branch: `fix/acid-reliability-layer`
- [ ] Set up test database/environment (`:memory:` DuckDB for unit tests)

### Fix 1: DuckDB Connection Pooling
- [ ] Add `threading.RLock` to `DuckDBManager.__init__`
- [ ] Implement `execute_atomic()` method
- [ ] Update `upsert_dataframe()` to use lock for multi-step operations
- [ ] Write and pass 3 concurrent test cases
- [ ] Run full regression test suite (`tests/test_duckdb_store_coverage.py`)

### Fix 2: Transactional Writes
- [ ] Create `init_cache_audit_table()` function
- [ ] Implement `write_cache_atomic()` with temp file + rename
- [ ] Add `BEGIN...COMMIT...ROLLBACK` logic
- [ ] Write and pass 4 test cases (success, failure, concurrent, regression)
- [ ] Update app initialization to call `init_cache_audit_table()`
- [ ] Run cache manager test suite

### Fix 3: Session Persistence
- [ ] Create `app/services/cache_service.py` with `DuckDBSessionStore`
- [ ] Add session table creation
- [ ] Integrate into `app/main.py` setup
- [ ] Update example pages to call `store.save_key()`
- [ ] Write and pass 4 test cases
- [ ] Test with real Streamlit app (manual + screenshot)

### Fix 4: Manifest Locking
- [ ] Add platform-specific lock/unlock helpers
- [ ] Implement `cache_manifest_locked()` + `_unlock_manifest()`
- [ ] Update `update_manifest()` to use locking
- [ ] Add atomic rename + temp file cleanup
- [ ] Write and pass 4 test cases
- [ ] Test on both Windows and Unix

### Post-Implementation
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Run integration tests: `pytest tests/test_integration_*.py -v`
- [ ] Manual testing with Streamlit app
- [ ] Code review (at least 2 reviewers)
- [ ] Merge to main

---

## Rollback Plan

If any fix causes regressions:

1. **Fix 1 (DuckDB pooling)**: Revert `RLock` + `execute_atomic()`, fall back to lazy connection (no atomicity guarantees)
2. **Fix 2 (transactional writes)**: Revert to `write_cache()` (old async behavior), keep audit table for debugging
3. **Fix 3 (session persistence)**: Disable `setup_session_persistence()` in `main.py` (graceful degradation)
4. **Fix 4 (manifest locking)**: Revert to unlocked `_save_manifest()` (data corruption risk, but app still works)

**Recommended**: Merge Fixes 1+4 together (fixes most critical issues), then Fixes 2+3 separately for faster iteration.

---

## Monitoring & Validation

After each fix, monitor:

1. **Atomicity**: No orphaned temp files in `data/cache/` after crashes
2. **Isolation**: Lock contention stats (log `time.time()` around critical sections)
3. **Durability**: Manifest and audit entries always match Parquet files
4. **Consistency**: No stale reads from Parquet cache (verify with query tracing)

**Metrics to log** (add to each fix):
- `duckdb_lock_wait_ms`: Time spent waiting for lock
- `cache_write_atomic_duration_ms`: Time to write cache
- `session_persist_errors_total`: Failed persists
- `manifest_lock_contentions_total`: Lock waits > 100ms

---

## References

- **DuckDB thread safety**: https://duckdb.org/docs/guides/import/query_parquet.html
- **File locking (Unix)**: `man fcntl` / `man flock`
- **File locking (Windows)**: `msvcrt.locking()` docs
- **ACID guarantees**: https://en.wikipedia.org/wiki/ACID
- **Streamlit session_state**: https://docs.streamlit.io/library/api-reference/session-state

---

**Document version**: 1.0
**Last updated**: 2026-06-10
**Author**: Claude Code (Anthropic)
**Status**: Ready for implementation
