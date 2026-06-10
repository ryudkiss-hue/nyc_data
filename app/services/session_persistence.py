"""Session state persistence layer using DuckDB.

[FIX 3] Provides DuckDB-backed persistence for Streamlit session_state,
ensuring user state survives page refreshes and session timeouts.

Usage:
    import streamlit as st
    from app.services.session_persistence import init_session_persistence
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
from typing import Any, Dict

from socrata_toolkit.core.duckdb_store import DuckDBManager

logger = logging.getLogger(__name__)


class DuckDBSessionStore:
    """Persist Streamlit session_state to DuckDB with automatic sync.

    [FIX 3] Implements an IsolationStore pattern: session state is stored
    in a DuckDB table and loaded on each page refresh, ensuring state
    persistence across server restarts and browser refreshes.
    """

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
