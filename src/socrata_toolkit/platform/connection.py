"""
Multi-platform connection management.

Provides unified interface to query data from:
- PRIMARY: MotherDuck (cloud DuckDB)
- FALLBACK: Local DuckDB (file-based, always available)

Usage:
    from socrata_toolkit.platform.connection import get_connection

    # Automatically tries MotherDuck, falls back to DuckDB
    conn = get_connection()
    df = conn.execute("SELECT * FROM inspection LIMIT 10").df()

    # Explicit platform selection
    conn = get_connection(platform='motherduck')  # Cloud
    conn = get_connection(platform='duckdb')      # Local
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Unified connection manager with MotherDuck primary, DuckDB fallback."""

    def __init__(self, auto_fallback: bool = True):
        """
        Initialize connection manager.

        Args:
            auto_fallback: If True, automatically fallback to DuckDB if MotherDuck unavailable
        """
        self.auto_fallback = auto_fallback
        self.conn = None
        self.platform = None

    def get_connection(self, platform: Optional[str] = None):
        """
        Get database connection (MotherDuck primary, DuckDB fallback).

        Args:
            platform: Explicit platform ('motherduck', 'duckdb', or None for auto)

        Returns:
            DuckDB connection object
        """
        try:
            import duckdb
        except ImportError:
            raise ImportError("duckdb not installed. Install with: pip install duckdb")

        # If already connected, return cached connection
        if self.conn and self.platform == platform:
            return self.conn

        if platform == "motherduck":
            return self._connect_motherduck(duckdb)

        elif platform == "duckdb":
            return self._connect_duckdb(duckdb)

        else:
            # Auto mode: try MotherDuck first, fallback to DuckDB
            try:
                return self._connect_motherduck(duckdb)
            except Exception as e:
                if self.auto_fallback:
                    logger.warning(f"MotherDuck connection failed ({e}), falling back to DuckDB")
                    return self._connect_duckdb(duckdb)
                else:
                    raise

    def _connect_motherduck(self, duckdb):
        """Connect to MotherDuck cloud."""
        token = os.getenv("MOTHERDUCK_TOKEN")

        if not token:
            raise ValueError(
                "MOTHERDUCK_TOKEN not set. Get from: https://console.motherduck.com/\n"
                "Set: export MOTHERDUCK_TOKEN='your_token'\n"
                "Or use DuckDB fallback: get_connection(platform='duckdb')"
            )

        try:
            conn = duckdb.connect(f"md:?motherduck_token={token}")
            # Test connection
            conn.execute("SELECT 1")
            self.conn = conn
            self.platform = "motherduck"
            logger.info("✓ Connected to MotherDuck")
            return conn
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MotherDuck: {e}")

    def _connect_duckdb(self, duckdb):
        """Connect to local DuckDB."""
        db_path = os.getenv("DUCKDB_PATH", "./data/local_db/nyc_mission_control.duckdb")

        # Ensure directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        try:
            conn = duckdb.connect(str(db_path))
            # Verify database is initialized
            conn.execute("SELECT * FROM information_schema.tables LIMIT 1")
            self.conn = conn
            self.platform = "duckdb"
            logger.info(f"✓ Connected to local DuckDB ({db_path})")
            return conn
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB: {e}")
            raise ConnectionError(
                f"Could not connect to local DuckDB at {db_path}.\n"
                "Initialize with: python .claude/analysis/complete_26_dataset_pipeline.py"
            )

    def close(self):
        """Close active connection."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self.conn = None
                self.platform = None


# Global connection manager
_manager = ConnectionManager(auto_fallback=True)


def get_connection(platform: Optional[str] = None):
    """
    Get database connection (MotherDuck primary, DuckDB fallback).

    Automatically tries MotherDuck first. If unavailable or token not set,
    falls back to local DuckDB.

    Args:
        platform: Explicit platform ('motherduck', 'duckdb', or None for auto)

    Returns:
        DuckDB connection object

    Examples:
        # Automatic (tries MotherDuck, falls back to DuckDB)
        conn = get_connection()
        df = conn.execute("SELECT * FROM inspection").df()

        # Force MotherDuck
        conn = get_connection(platform='motherduck')

        # Force local DuckDB
        conn = get_connection(platform='duckdb')

        # Complex query
        df = conn.execute('''
            SELECT borough, COUNT(*) as violations
            FROM violations
            WHERE created_date > CURRENT_DATE - 30
            GROUP BY borough
        ''').df()
    """
    return _manager.get_connection(platform=platform)


def query(sql: str, platform: Optional[str] = None):
    """
    Execute SQL query and return DataFrame.

    Args:
        sql: SQL query string
        platform: Explicit platform ('motherduck', 'duckdb', or None for auto)

    Returns:
        pandas DataFrame
    """
    conn = get_connection(platform=platform)
    return conn.execute(sql).df()


def get_platform_name() -> str:
    """Get active platform name ('motherduck' or 'duckdb')."""
    return _manager.platform or "unknown"


def is_motherduck() -> bool:
    """Check if connected to MotherDuck."""
    try:
        _manager.get_connection(platform="motherduck")
        return True
    except Exception:
        return False


def close_connection():
    """Close active connection."""
    _manager.close()
