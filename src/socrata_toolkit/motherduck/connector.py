"""MotherDuck Connection Layer (motherduck-connect).

Provides a unified connection interface for MotherDuck cloud analytics platform
with automatic fallback to local DuckDB when cloud credentials are unavailable.

Key responsibilities:
- Accept token from environment or parameter
- Support custom database and database_path configuration
- Connect to MotherDuck if token present, else fallback to local DuckDB
- Provide standardized execute, fetch_all, fetch_df, and create_schema methods
- Report connection status with is_connected()
- Include custom user agent for analytics tracking
"""
import logging
import os
from typing import Any, Optional

import pandas as pd

try:
    import duckdb
except ImportError as e:
    raise ImportError("DuckDB is required. Install with: pip install duckdb") from e

logger = logging.getLogger(__name__)

class MotherDuckConnection:
    """MotherDuck connection handler with local DuckDB fallback.

    Manages connections to MotherDuck cloud analytics platform or local DuckDB,
    depending on token availability. Provides a unified interface for executing
    queries and managing database schemas.

    Attributes:
        token: MotherDuck authentication token
        database: Database name on MotherDuck (default: "nyc_dot_analytics")
        database_path: Path to local DuckDB file for fallback
        is_motherduck: Boolean indicating if connected to MotherDuck cloud
        conn: Underlying DuckDB connection object
        user_agent: Custom user agent string for tracking
    """

    # Custom user agent per specification
    USER_AGENT = "agent-skills/2.2.0(harness-claude-code;llm-haiku-4-5)"

    def __init__(
        self,
        token: Optional[str] = None,
        database: str = "nyc_dot_analytics",
        database_path: Optional[str] = None,
    ):
        """Initialize MotherDuck connection.

        Args:
            token: MotherDuck API token. If None, reads from MOTHERDUCK_TOKEN env var.
                   If neither provided, falls back to local DuckDB.
            database: Name of the database on MotherDuck. Default: "nyc_dot_analytics"
            database_path: Path for local DuckDB fallback. Default: :memory: (in-memory)

        Example:
            # Connect to MotherDuck (reads token from env)
            conn = MotherDuckConnection()

            # Connect to MotherDuck with explicit token
            conn = MotherDuckConnection(token="your_token_here")

            # Fallback to local DuckDB with persistent file
            conn = MotherDuckConnection(
                token=None,
                database_path="/data/nyc_analytics.duckdb"
            )
        """
        self.token = token if token is not None else os.getenv("MOTHERDUCK_TOKEN")
        self.database = database
        self.database_path = database_path or ":memory:"
        self.user_agent = self.USER_AGENT
        self.is_motherduck = False
        self.conn: Optional[duckdb.DuckDBPyConnection] = None

        self._connect()

    def _connect(self) -> None:
        """Establish connection to MotherDuck or fallback to local DuckDB.

        Attempts to connect to MotherDuck cloud if token is available.
        Falls back to local DuckDB if token is missing or connection fails.
        """
        try:
            if self.token and self.token.strip():
                # Connect to MotherDuck cloud
                os.environ["MOTHERDUCK_TOKEN"] = self.token
                connection_string = f"md:{self.database}"
                self.conn = duckdb.connect(connection_string)
                self.is_motherduck = True
                logger.info(
                    f"Connected to MotherDuck cloud (database: {self.database})"
                )
            else:
                # Fall back to local DuckDB
                logger.debug(
                    f"MOTHERDUCK_TOKEN not set; using local DuckDB at {self.database_path}"
                )
                self.conn = duckdb.connect(self.database_path)
                self.is_motherduck = False

        except Exception as e:
            logger.error(
                f"Failed to connect to MotherDuck ({e}); "
                f"falling back to local DuckDB"
            )
            self.conn = duckdb.connect(self.database_path)
            self.is_motherduck = False

    def is_connected(self) -> bool:
        """Check if connection is active and usable.

        Returns:
            True if connection is open and ready, False otherwise.
        """
        try:
            if self.conn is None:
                return False
            # Test connection with simple query
            self.conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def execute(self, query: str, params: Optional[list[Any]] = None):
        """Execute a SQL query.

        Args:
            query: SQL query string
            params: Optional list of parameters for parameterized queries

        Returns:
            DuckDB result object with fetch methods (fetchone, fetchall, etc.)

        Raises:
            RuntimeError: If connection is not active
            duckdb.Error: If query execution fails
        """
        if not self.is_connected():
            raise RuntimeError("Connection is not active. Call is_connected() to verify.")

        try:
            if params:
                return self.conn.execute(query, params)
            else:
                return self.conn.execute(query)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def fetch_all(self, query: str, params: Optional[list[Any]] = None) -> list[tuple]:
        """Execute query and fetch all results as list of tuples.

        Args:
            query: SQL query string
            params: Optional list of parameters for parameterized queries

        Returns:
            List of tuples representing query results

        Example:
            rows = conn.fetch_all("SELECT * FROM table")
            for row in rows:
                print(row[0], row[1])  # Access by index
        """
        result = self.execute(query, params)
        return result.fetchall()

    def fetch_df(
        self, query: str, params: Optional[list[Any]] = None
    ) -> pd.DataFrame:
        """Execute query and return results as pandas DataFrame.

        Args:
            query: SQL query string
            params: Optional list of parameters for parameterized queries

        Returns:
            pandas DataFrame with query results

        Example:
            df = conn.fetch_df(
                "SELECT borough, COUNT(*) FROM inspection GROUP BY borough"
            )
            print(df.groupby('borough').sum())
        """
        result = self.execute(query, params)
        return result.df()

    def create_schema(self, schema_name: str) -> None:
        """Create a new schema in the database.

        Args:
            schema_name: Name of schema to create

        Raises:
            RuntimeError: If connection is not active
            duckdb.Error: If schema creation fails (e.g., already exists without IF NOT EXISTS)

        Example:
            conn.create_schema("analytics")
            conn.execute("CREATE TABLE analytics.my_table (id INT)")
        """
        if not self.is_connected():
            raise RuntimeError("Connection is not active. Call is_connected() to verify.")

        try:
            self.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            logger.debug(f"Schema '{schema_name}' created or already exists")
        except Exception as e:
            logger.error(f"Failed to create schema '{schema_name}': {e}")
            raise

    def close(self) -> None:
        """Close the connection and clean up resources.

        Safe to call multiple times. Subsequent calls have no effect.

        Example:
            conn.close()
        """
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
                logger.debug("Connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation of connection."""
        mode = "MotherDuck" if self.is_motherduck else "Local DuckDB"
        db_info = self.database if self.is_motherduck else self.database_path
        status = "connected" if self.is_connected() else "disconnected"
        return f"<MotherDuckConnection [{mode}] {db_info} [{status}]>"
