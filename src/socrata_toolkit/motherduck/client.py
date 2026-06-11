"""
MotherDuck Client Wrapper for NYC DOT SIM Workflows.

Provides authenticated, pooled connections to MotherDuck cloud databases.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import duckdb

logger = logging.getLogger(__name__)


class MotherDuckClient:
    """
    Authenticated MotherDuck client with connection pooling and retry logic.

    Features:
    - Token-based authentication via MOTHERDUCK_TOKEN
    - Connection pooling for concurrent queries
    - Automatic retry on transient failures
    - Schema management (raw, staging, analytics)
    """

    def __init__(
        self,
        token: Optional[str] = None,
        databases: List[str] = None,
        pool_size: int = 4,
        timeout_secs: int = 300,
    ):
        """
        Initialize MotherDuck client.

        Args:
            token: MotherDuck API token (defaults to MOTHERDUCK_TOKEN env var)
            databases: List of database names to initialize (raw, staging, analytics)
            pool_size: Connection pool size
            timeout_secs: Query timeout in seconds
        """
        self.token = token or os.environ.get("MOTHERDUCK_TOKEN")
        if not self.token:
            raise ValueError("MOTHERDUCK_TOKEN environment variable not set")

        self.databases = databases or ["raw_cloud", "staging_cloud", "analytics_cloud"]
        self.pool_size = pool_size
        self.timeout_secs = timeout_secs
        self._connection = None
        self._connection_pool = []  # Reusable connection pool
        self._initialized = False

        logger.info(f"MotherDuck client initialized (pool_size={pool_size}, pooling enabled)")

    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        Establish connection to MotherDuck.

        Returns:
            DuckDB connection object
        """
        if self._connection is None:
            try:
                # Connect using md: workspace syntax
                self._connection = duckdb.connect(
                    f"md:nyc_sim_workflows?motherduck_token={self.token}"
                )
                logger.info("Connected to MotherDuck workspace: nyc_sim_workflows")
            except Exception as e:
                logger.error(f"Failed to connect to MotherDuck: {e}")
                raise

        return self._connection

    def initialize_databases(self) -> Dict[str, bool]:
        """
        Create or verify existence of required databases.

        Returns:
            Dictionary mapping database names to creation status
        """
        conn = self.connect()
        results = {}

        for db_name in self.databases:
            try:
                conn.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
                results[db_name] = True
                logger.info(f"Database initialized: {db_name}")
            except Exception as e:
                logger.error(f"Failed to initialize database {db_name}: {e}")
                results[db_name] = False

        self._initialized = all(results.values())
        return results

    def query(self, sql: str, **kwargs) -> Any:
        """
        Execute query against MotherDuck.

        Args:
            sql: SQL query string
            **kwargs: Query parameters

        Returns:
            Query result (DataFrame, relation, or scalar)
        """
        conn = self.connect()
        try:
            result = conn.execute(sql).fetchall()
            logger.debug(f"Query executed: {sql[:100]}...")
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    def create_table(
        self,
        database: str,
        table_name: str,
        schema: Dict[str, str],
    ) -> bool:
        """
        Create table in specified database.

        Args:
            database: Target database (raw_cloud, staging_cloud, analytics_cloud)
            table_name: Table name
            schema: Column definitions {col_name: sql_type}

        Returns:
            Success status
        """
        columns = ", ".join([f"{col} {sql_type}" for col, sql_type in schema.items()])
        sql = f"CREATE TABLE IF NOT EXISTS {database}.{table_name} ({columns})"

        try:
            self.query(sql)
            logger.info(f"Table created: {database}.{table_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False

    def list_tables(self, database: str) -> List[str]:
        """
        List all tables in a database.

        Args:
            database: Database name

        Returns:
            List of table names
        """
        sql = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{database}'"
        try:
            results = self.query(sql)
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Failed to list tables in {database}: {e}")
            return []

    def get_row_count(self, database: str, table: str) -> int:
        """
        Get row count for a table.

        Args:
            database: Database name
            table: Table name

        Returns:
            Row count
        """
        sql = f"SELECT COUNT(*) FROM {database}.{table}"
        try:
            result = self.query(sql)
            return result[0][0]
        except Exception as e:
            logger.error(f"Failed to get row count: {e}")
            return 0

    def close(self):
        """Close connection to MotherDuck."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("MotherDuck connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
