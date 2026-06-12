"""Tests for MotherDuck integration and SQL compatibility validation."""
import duckdb
import pytest

from socrata_toolkit.core.motherduck_integration import (
    DuckDBConnection,
    MotherDuckConnection,
    MotherDuckValidator,
    get_connection,
)

class TestMotherDuckValidator:
    """Test SQL compatibility validation."""

    def test_variant_type_detected(self):
        """Test VARIANT type is flagged as incompatible."""
        validator = MotherDuckValidator()
        sql = "SELECT CAST(col AS VARIANT) FROM table"
        issues = validator.validate(sql)

        assert len(issues) == 1
        assert "VARIANT" in issues[0].reason
        assert issues[0].severity == "error"

    def test_geometry_type_detected(self):
        """Test GEOMETRY type is flagged as incompatible."""
        validator = MotherDuckValidator()
        sql = "SELECT ST_Point(1, 2)::GEOMETRY FROM table"
        issues = validator.validate(sql)

        assert any("GEOMETRY" in issue.reason for issue in issues)
        assert any(issue.severity == "error" for issue in issues)

    def test_merge_into_detected(self):
        """Test MERGE INTO is flagged as incompatible."""
        validator = MotherDuckValidator()
        sql = """
        MERGE INTO target t
        USING source s ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET val = s.val
        WHEN NOT MATCHED THEN INSERT VALUES (s.id, s.val)
        """
        issues = validator.validate(sql)

        assert any("MERGE" in issue.reason for issue in issues)
        assert any(issue.severity == "error" for issue in issues)

    def test_load_statement_warning(self):
        """Test LOAD statement is flagged as warning."""
        validator = MotherDuckValidator()
        sql = "LOAD httpfs; SELECT * FROM read_parquet('s3://bucket/file.parquet')"
        issues = validator.validate(sql)

        assert any("LOAD" in issue.reason for issue in issues)
        assert any(issue.severity == "warning" for issue in issues)

    def test_compatible_sql_passes(self):
        """Test that compatible SQL passes validation."""
        validator = MotherDuckValidator()
        sql = """
        SELECT
          material,
          borough,
          COUNT(*) as cnt,
          AVG(rating) as avg_rating
        FROM staging.inspection
        WHERE created_date > CURRENT_DATE - INTERVAL '30 days'
        GROUP BY material, borough
        ORDER BY cnt DESC
        """
        issues = validator.validate(sql)

        assert len(issues) == 0

    def test_is_compatible_with_errors(self):
        """Test is_compatible returns False when errors present."""
        validator = MotherDuckValidator()
        sql_with_error = "SELECT CAST(x AS VARIANT) FROM t"

        assert not validator.is_compatible(sql_with_error)

    def test_is_compatible_with_warnings_only(self):
        """Test is_compatible returns True when only warnings present."""
        validator = MotherDuckValidator()
        sql_with_warning = "CREATE TEMPORARY TABLE t (id INT)"

        assert validator.is_compatible(sql_with_warning)

class TestDuckDBConnection:
    """Test local DuckDB connection with validation."""

    def test_local_connection_creation(self):
        """Test creating a local DuckDB connection."""
        conn = DuckDBConnection(":memory:")

        assert conn.is_motherduck is False
        assert conn.db_path == ":memory:"
        conn.close()

    def test_execute_query_without_validation(self):
        """Test executing query without compatibility check."""
        conn = DuckDBConnection(":memory:")
        conn.conn.execute("CREATE TABLE test (id INT, name VARCHAR)")
        conn.conn.execute("INSERT INTO test VALUES (1, 'Alice')")

        result = conn.execute("SELECT * FROM test", validate=False).fetchall()

        assert len(result) == 1
        assert result[0][0] == 1
        conn.close()

    def test_execute_query_with_validation_pass(self):
        """Test executing valid query with validation enabled."""
        conn = DuckDBConnection(":memory:")
        conn.conn.execute("CREATE TABLE test (id INT, value FLOAT)")
        conn.conn.execute("INSERT INTO test VALUES (1, 3.14)")

        result = conn.execute(
            "SELECT AVG(value) FROM test",
            validate=True
        ).fetchall()

        assert len(result) == 1
        conn.close()

    def test_execute_query_with_validation_fail(self):
        """Test executing incompatible query raises error."""
        conn = DuckDBConnection(":memory:")
        sql_with_variant = "SELECT CAST(1 AS VARIANT) as x"

        with pytest.raises(ValueError, match="compatibility"):
            conn.execute(sql_with_variant, validate=True)

        conn.close()

class TestMotherDuckConnection:
    """Test MotherDuck cloud connection with fallback."""

    def test_motherduck_token_missing_falls_back_to_local(self):
        """Test that missing token falls back to local DuckDB."""
        import os

        # Clear token if set
        old_token = os.environ.get("MOTHERDUCK_TOKEN")
        if "MOTHERDUCK_TOKEN" in os.environ:
            del os.environ["MOTHERDUCK_TOKEN"]

        try:
            conn = MotherDuckConnection(token=None)

            # Should fall back to local even if token was unset
            assert isinstance(conn.conn, duckdb.DuckDBPyConnection)
            conn.close()
        finally:
            # Restore token
            if old_token:
                os.environ["MOTHERDUCK_TOKEN"] = old_token

    def test_motherduck_connection_validation(self):
        """Test validation works on MotherDuck connection."""
        conn = MotherDuckConnection(token=None)  # Falls back to local

        # Valid query should work
        result = conn.execute(
            "SELECT 1 as x",
            validate=True
        ).fetchone()
        assert result[0] == 1

        # Invalid query should fail
        with pytest.raises(ValueError, match="compatibility"):
            conn.execute(
                "SELECT CAST(1 AS VARIANT) as x",
                validate=True
            )

        conn.close()

class TestConnectionFactory:
    """Test get_connection factory function."""

    def test_get_local_connection(self):
        """Test getting local DuckDB connection."""
        conn = get_connection(use_motherduck=False)

        assert isinstance(conn, DuckDBConnection)
        assert conn.is_motherduck is False
        conn.close()

    def test_get_motherduck_connection_falls_back(self):
        """Test getting MotherDuck connection falls back to local."""
        import os

        old_token = os.environ.get("MOTHERDUCK_TOKEN")
        if "MOTHERDUCK_TOKEN" in os.environ:
            del os.environ["MOTHERDUCK_TOKEN"]

        try:
            conn = get_connection(use_motherduck=True)

            # Should fall back to local if token missing
            assert isinstance(conn.conn, duckdb.DuckDBPyConnection)
            conn.close()
        finally:
            if old_token:
                os.environ["MOTHERDUCK_TOKEN"] = old_token

class TestMotherDuckCompatibility:
    """Integration tests verifying SQL works on both DuckDB and MotherDuck paths."""

    def test_cross_tab_sql_compatible(self):
        """Verify cross-tab SQL is compatible."""
        validator = MotherDuckValidator()

        sql = """
        SELECT
          'inspection' as dataset,
          material_type as row_val,
          borough as col_val,
          COUNT(*) as metric_value
        FROM table
        GROUP BY material_type, borough
        """

        assert validator.is_compatible(sql)

    def test_completion_rate_sql_compatible(self):
        """Verify completion rate SQL is compatible."""
        validator = MotherDuckValidator()

        sql = """
        WITH rates AS (
          SELECT
            borough,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)::FLOAT as completed,
            COUNT(*) as total
          FROM ramp_progress
          GROUP BY borough
        )
        SELECT
          borough,
          ROUND(100 * completed / total, 2) as completion_pct
        FROM rates
        """

        assert validator.is_compatible(sql)

    def test_statistical_summary_sql_compatible(self):
        """Verify statistical summary SQL is compatible."""
        validator = MotherDuckValidator()

        sql = """
        SELECT
          COUNT(*) as count,
          AVG(row_count) as mean,
          MEDIAN(row_count) as median,
          STDDEV(row_count) as stddev,
          MIN(row_count) as min,
          MAX(row_count) as max,
          QUANTILE_CONT(row_count, 0.25) as q1,
          QUANTILE_CONT(row_count, 0.75) as q3
        FROM analytics.raw_counts_summary
        WHERE row_count IS NOT NULL
        """

        assert validator.is_compatible(sql)
