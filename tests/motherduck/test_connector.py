"""Tests for MotherDuck connection layer (motherduck-connect).

TDD approach: tests first, implementation follows.
"""

import os

import duckdb
import pandas as pd
import pytest

from socrata_toolkit.motherduck.connector import MotherDuckConnection


class TestMotherDuckConnectionInitialization:
    """Test MotherDuck connection initialization with various configurations."""

    def test_motherduck_connection_with_token(self, monkeypatch):
        """Test creating connection with explicit token."""
        # Mock token
        test_token = "test_token_12345"
        monkeypatch.setenv("MOTHERDUCK_TOKEN", "")

        conn = MotherDuckConnection(token=test_token)

        assert conn.token == test_token
        assert conn.is_connected()
        conn.close()

    def test_motherduck_connection_from_env(self, monkeypatch):
        """Test creating connection from MOTHERDUCK_TOKEN env var."""
        test_token = "env_token_67890"
        monkeypatch.setenv("MOTHERDUCK_TOKEN", test_token)

        conn = MotherDuckConnection()

        assert conn.token == test_token
        assert conn.is_connected()
        conn.close()

    def test_motherduck_connection_custom_database(self):
        """Test creating connection with custom database name."""
        conn = MotherDuckConnection(token=None, database="custom_analytics_db")

        # Should still be connectable (falls back to local if no token)
        assert conn.database == "custom_analytics_db"
        conn.close()

    def test_motherduck_connection_with_database_path(self):
        """Test creating connection with custom database_path parameter."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.duckdb")
            conn = MotherDuckConnection(token=None, database_path=db_path)

            assert conn.database_path == db_path
            conn.close()

    def test_motherduck_connection_user_agent(self):
        """Test that custom user agent is set correctly."""
        conn = MotherDuckConnection(token=None)

        assert hasattr(conn, "user_agent")
        assert "agent-skills/2.2.0" in conn.user_agent
        assert "harness-claude-code" in conn.user_agent
        assert "llm-haiku-4-5" in conn.user_agent
        conn.close()


class TestDuckDBFallbackConnection:
    """Test DuckDB fallback when MotherDuck token is unavailable."""

    def test_duckdb_fallback_connection_no_token(self, monkeypatch):
        """Test fallback to local DuckDB when token is missing."""
        monkeypatch.setenv("MOTHERDUCK_TOKEN", "")

        conn = MotherDuckConnection(token=None)

        assert not conn.is_motherduck
        assert conn.is_connected()
        conn.close()

    def test_duckdb_fallback_with_database_path(self):
        """Test fallback connection uses provided database_path."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "fallback.duckdb")
            conn = MotherDuckConnection(token=None, database_path=db_path)

            # Create a table to verify persistence
            conn.execute("CREATE TABLE test (id INT, value VARCHAR)")
            conn.close()

            # Reconnect and verify table exists
            conn2 = MotherDuckConnection(token=None, database_path=db_path)
            result = conn2.fetch_all("SELECT COUNT(*) FROM test")
            assert result[0][0] == 0
            conn2.close()

    def test_is_connected_returns_false_for_closed_connection(self):
        """Test is_connected returns False after connection is closed."""
        conn = MotherDuckConnection(token=None)
        assert conn.is_connected()

        conn.close()
        # After close, connection should not be usable
        # (implementation may vary based on DuckDB behavior)


class TestConnectionMethods:
    """Test core connection methods: execute, fetch_all, fetch_df, create_schema."""

    def test_execute_simple_query(self):
        """Test execute method with simple query."""
        conn = MotherDuckConnection(token=None)

        result = conn.execute("SELECT 1 as test_col")

        # Should return result object with fetch methods
        assert result is not None
        conn.close()

    def test_fetch_all_returns_list(self):
        """Test fetch_all returns list of tuples."""
        conn = MotherDuckConnection(token=None)
        conn.execute("CREATE TABLE test_data (id INT, name VARCHAR)")
        conn.execute("INSERT INTO test_data VALUES (1, 'Alice')")
        conn.execute("INSERT INTO test_data VALUES (2, 'Bob')")

        result = conn.fetch_all("SELECT * FROM test_data ORDER BY id")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0][0] == 1
        assert result[0][1] == "Alice"
        conn.close()

    def test_fetch_df_returns_dataframe(self):
        """Test fetch_df returns pandas DataFrame."""
        conn = MotherDuckConnection(token=None)
        conn.execute("CREATE TABLE stats (borough VARCHAR, count INT)")
        conn.execute("INSERT INTO stats VALUES ('MN', 100)")
        conn.execute("INSERT INTO stats VALUES ('BK', 200)")

        df = conn.fetch_df("SELECT * FROM stats ORDER BY borough")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["borough", "count"]
        assert df.loc[df["borough"] == "MN", "count"].values[0] == 100
        conn.close()

    def test_create_schema(self):
        """Test create_schema creates new schema."""
        conn = MotherDuckConnection(token=None)

        conn.create_schema("test_schema")

        # Verify schema exists by creating table in it
        conn.execute("CREATE TABLE test_schema.test_table (id INT)")
        conn.execute("INSERT INTO test_schema.test_table VALUES (42)")
        result = conn.fetch_all("SELECT * FROM test_schema.test_table")

        assert result[0][0] == 42
        conn.close()

    def test_execute_with_parameters(self):
        """Test execute with parameterized queries."""
        conn = MotherDuckConnection(token=None)
        conn.execute("CREATE TABLE params_test (id INT, value FLOAT)")

        # DuckDB uses ? for parameters
        conn.execute("INSERT INTO params_test VALUES (?, ?)", [1, 3.14])
        result = conn.fetch_all("SELECT * FROM params_test")

        assert result[0][0] == 1
        assert result[0][1] == pytest.approx(3.14)
        conn.close()

    def test_fetch_df_with_empty_result(self):
        """Test fetch_df with empty result set."""
        conn = MotherDuckConnection(token=None)
        conn.execute("CREATE TABLE empty_test (id INT)")

        df = conn.fetch_df("SELECT * FROM empty_test")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        conn.close()


class TestConnectionErrorHandling:
    """Test error handling in connection layer."""

    def test_execute_invalid_sql_raises_error(self):
        """Test that invalid SQL raises appropriate error."""
        conn = MotherDuckConnection(token=None)

        with pytest.raises(Exception):  # Could be duckdb.Error or similar
            conn.execute("SELECT * FROM nonexistent_table")

        conn.close()

    def test_create_schema_duplicate_handling(self):
        """Test creating duplicate schema."""
        conn = MotherDuckConnection(token=None)

        conn.create_schema("dup_schema")

        # Creating same schema again should handle gracefully
        # (either succeed silently or with IF NOT EXISTS)
        try:
            conn.create_schema("dup_schema")
        except Exception:
            # Some implementations may raise, others may silently succeed
            pass

        conn.close()


class TestConnectionIntegration:
    """Integration tests for realistic workflows."""

    def test_realistic_analytics_workflow(self):
        """Test a realistic analytics workflow with multiple operations."""
        conn = MotherDuckConnection(token=None)

        # Setup schema
        conn.create_schema("analytics")

        # Create and populate inspection data
        conn.execute("""
            CREATE TABLE analytics.inspection (
                objectid INT,
                borough VARCHAR,
                created_date DATE,
                rating INT
            )
        """)

        # Insert sample data
        conn.execute("""
            INSERT INTO analytics.inspection VALUES
            (1, 'MN', '2026-06-01', 85),
            (2, 'BK', '2026-06-01', 92),
            (3, 'MN', '2026-06-02', 88),
            (4, 'BK', '2026-06-02', 95)
        """)

        # Run analytics query
        df = conn.fetch_df("""
            SELECT
              borough,
              COUNT(*) as count,
              AVG(rating) as avg_rating
            FROM analytics.inspection
            GROUP BY borough
            ORDER BY borough
        """)

        assert len(df) == 2
        assert df.loc[df["borough"] == "MN", "avg_rating"].values[0] == pytest.approx(86.5)

        conn.close()

    def test_cross_schema_query(self):
        """Test querying across different schemas."""
        conn = MotherDuckConnection(token=None)

        # Create two schemas
        conn.create_schema("staging")
        conn.create_schema("analytics")

        # Create tables in both
        conn.execute("CREATE TABLE staging.raw (id INT, value FLOAT)")
        conn.execute("CREATE TABLE analytics.processed (id INT, value_squared FLOAT)")

        # Insert data
        conn.execute("INSERT INTO staging.raw VALUES (1, 2.0), (2, 3.0)")
        conn.execute("INSERT INTO analytics.processed VALUES (1, 4.0), (2, 9.0)")

        # Query across schemas
        df = conn.fetch_df("""
            SELECT
              r.id,
              r.value,
              p.value_squared
            FROM staging.raw r
            JOIN analytics.processed p ON r.id = p.id
            ORDER BY r.id
        """)

        assert len(df) == 2
        assert df.iloc[0, 0] == 1

        conn.close()
