"""
MotherDuck Bridge Module
Handles connections, authentication, SQL execution, and transaction management for the NYC DOT pipeline.
Supports both MotherDuck (cloud) and local DuckDB for testing.
"""

import os
import logging
import duckdb
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a SQL execution."""
    success: bool
    rows_affected: int = 0
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    query: str = ""


class MotherDuckBridge:
    """
    Bridge to MotherDuck/DuckDB database.
    Handles connection lifecycle, authentication, and SQL execution with error handling.
    """

    def __init__(
        self,
        motherduck_token: Optional[str] = None,
        use_motherduck: bool = True,
        db_name: str = "nyc_dot_analytics",
        fallback_local: bool = True,
        connection_timeout: int = 30
    ):
        """
        Initialize MotherDuck bridge.

        Args:
            motherduck_token: MotherDuck API token (from env if not provided)
            use_motherduck: Try to connect to MotherDuck cloud (fallback to local if fails)
            db_name: Database name to use/create
            fallback_local: If MotherDuck fails, fallback to local DuckDB
            connection_timeout: Connection timeout in seconds
        """
        self.motherduck_token = motherduck_token or os.getenv("MOTHERDUCK_TOKEN", "")
        self.use_motherduck = use_motherduck and bool(self.motherduck_token)
        self.db_name = db_name
        self.fallback_local = fallback_local
        self.connection_timeout = connection_timeout
        self.connection = None
        self.is_local = False
        self._connect()

    def _connect(self) -> bool:
        """
        Establish connection to MotherDuck or local DuckDB.
        Returns True if successful, False otherwise.
        """
        try:
            if self.use_motherduck:
                logger.info(f"Connecting to MotherDuck with database: {self.db_name}")
                # Phase 3D-1: Add custom_user_agent per MotherDuck best practices
                connection_string = f"md:{self.db_name}?token={self.motherduck_token}&custom_user_agent=agent-skills/2.2.0(harness-claude;llm-haiku)"
                self.connection = duckdb.connect(connection_string, timeout=self.connection_timeout)
                self.is_local = False
                logger.info("Successfully connected to MotherDuck")
                return True
            else:
                raise ValueError("MotherDuck not configured")

        except Exception as e:
            logger.warning(f"MotherDuck connection failed: {str(e)}")

            if self.fallback_local:
                logger.info(f"Falling back to local DuckDB at: {self.db_name}")
                try:
                    db_path = f"{self.db_name}.duckdb"
                    self.connection = duckdb.connect(db_path)
                    self.is_local = True
                    logger.info(f"Successfully connected to local DuckDB: {db_path}")
                    return True
                except Exception as local_error:
                    logger.error(f"Local DuckDB connection also failed: {str(local_error)}")
                    return False
            else:
                logger.error("MotherDuck connection failed and fallback disabled")
                return False

    def execute_sql(self, sql: str, params: Optional[List[Any]] = None) -> ExecutionResult:
        """
        Execute SQL statement safely with error handling.

        Args:
            sql: SQL statement to execute
            params: Query parameters (for prepared statements)

        Returns:
            ExecutionResult with success status, rows affected, and any errors
        """
        if not self.connection:
            return ExecutionResult(
                success=False,
                error="Database connection not established",
                query=sql
            )

        start_time = datetime.now()

        try:
            logger.debug(f"Executing SQL: {sql[:100]}...")

            if params:
                result = self.connection.execute(sql, params)
            else:
                result = self.connection.execute(sql)

            # For SELECT queries, fetch results
            if sql.strip().upper().startswith("SELECT"):
                rows = result.fetchall()
                rows_affected = len(rows)
            else:
                # For INSERT/UPDATE/DELETE, get row count from result object
                # DuckDB returns rowcount as an attribute
                if hasattr(result, "rowcount") and result.rowcount is not None:
                    rows_affected = result.rowcount
                else:
                    # Fallback: try to execute a COUNT query to verify
                    # For INSERT statements, return 1+ as placeholder if rowcount unavailable
                    rows_affected = 1

            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(f"SQL executed successfully ({rows_affected} rows, {execution_time_ms:.2f}ms)")

            return ExecutionResult(
                success=True,
                rows_affected=rows_affected,
                execution_time_ms=execution_time_ms,
                query=sql
            )

        except Exception as e:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"SQL execution error: {str(e)}"
            logger.error(error_msg)

            return ExecutionResult(
                success=False,
                error=error_msg,
                execution_time_ms=execution_time_ms,
                query=sql
            )

    def execute_sql_file(self, file_path: str) -> ExecutionResult:
        """
        Execute SQL statements from a file.

        Args:
            file_path: Path to SQL file

        Returns:
            ExecutionResult from the last statement
        """
        try:
            with open(file_path, "r") as f:
                sql = f.read()

            logger.info(f"Executing SQL file: {file_path}")

            # Split by GO for SQL Server compatibility, then filter empty statements
            statements = [s.strip() for s in sql.split("GO") if s.strip()]

            last_result = None
            for i, statement in enumerate(statements):
                logger.debug(f"Statement {i+1}/{len(statements)}")
                result = self.execute_sql(statement)

                if not result.success:
                    logger.error(f"Failed at statement {i+1}: {result.error}")
                    return result

                last_result = result

            return last_result or ExecutionResult(success=True)

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                error=f"SQL file not found: {file_path}"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Error reading SQL file: {str(e)}"
            )

    def create_schema(self, schema_name: str) -> ExecutionResult:
        """
        Create a schema if it doesn't exist.

        Args:
            schema_name: Name of schema to create

        Returns:
            ExecutionResult
        """
        sql = f"CREATE SCHEMA IF NOT EXISTS {schema_name}"
        result = self.execute_sql(sql)
        if result.success:
            logger.info(f"Schema created/verified: {schema_name}")
        return result

    def create_table(
        self,
        schema_name: str,
        table_name: str,
        columns: Dict[str, str]
    ) -> ExecutionResult:
        """
        Create a table with specified columns.

        Args:
            schema_name: Schema name
            table_name: Table name
            columns: Dictionary of {column_name: sql_type}

        Returns:
            ExecutionResult
        """
        col_defs = ", ".join([f"{name} {sql_type}" for name, sql_type in columns.items()])
        sql = f"CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} ({col_defs})"
        result = self.execute_sql(sql)
        if result.success:
            logger.info(f"Table created/verified: {schema_name}.{table_name}")
        return result

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dicts.

        Args:
            sql: SELECT statement

        Returns:
            List of row dicts
        """
        try:
            result = self.connection.execute(sql).fetch_df()
            return result.to_dict("records")
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            return []

    def get_table_count(self, schema_name: str, table_name: str) -> int:
        """
        Get row count for a table.

        Args:
            schema_name: Schema name
            table_name: Table name

        Returns:
            Row count
        """
        try:
            result = self.connection.execute(
                f"SELECT COUNT(*) as cnt FROM {schema_name}.{table_name}"
            ).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.warning(f"Could not get count for {schema_name}.{table_name}: {str(e)}")
            return 0

    def list_tables(self, schema_name: str) -> List[str]:
        """
        List all tables in a schema.

        Args:
            schema_name: Schema name

        Returns:
            List of table names
        """
        try:
            result = self.connection.execute(
                f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}'"
            ).fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"Could not list tables in {schema_name}: {str(e)}")
            return []

    def begin_transaction(self) -> ExecutionResult:
        """Start a transaction."""
        return self.execute_sql("BEGIN TRANSACTION")

    def commit(self) -> ExecutionResult:
        """Commit current transaction."""
        return self.execute_sql("COMMIT")

    def rollback(self) -> ExecutionResult:
        """Rollback current transaction."""
        return self.execute_sql("ROLLBACK")

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Test the bridge
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with local DuckDB
    bridge = MotherDuckBridge(use_motherduck=False, db_name="test_db")

    # Create schema
    result = bridge.create_schema("test_schema")
    print(f"Create schema: {result.success}")

    # Create table
    result = bridge.create_table(
        "test_schema",
        "test_table",
        {"id": "INTEGER", "name": "VARCHAR"}
    )
    print(f"Create table: {result.success}")

    # Insert data
    result = bridge.execute_sql("INSERT INTO test_schema.test_table VALUES (1, 'Alice')")
    print(f"Insert: {result.success}, rows: {result.rows_affected}")

    # Query data
    rows = bridge.query("SELECT * FROM test_schema.test_table")
    print(f"Query result: {rows}")

    # Close
    bridge.close()
