"""Tests for core.pipeline module - In-memory pipeline runner and SQL preview."""

from __future__ import annotations
import pytest


from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.core.pipeline import (
    _collect_columns_and_types,
    _sql_type,
    generate_postgres_preview,
    run_from_rows,
)


class TestSqlType:
    """Tests for _sql_type function."""

    def test_sql_type_boolean(self):
        """Test SQL type for boolean values."""
        assert _sql_type(True) == "BOOLEAN"
        assert _sql_type(False) == "BOOLEAN"

    def test_sql_type_integer(self):
        """Test SQL type for integer values."""
        assert _sql_type(42) == "BIGINT"
        assert _sql_type(0) == "BIGINT"
        assert _sql_type(-100) == "BIGINT"

    def test_sql_type_float(self):
        """Test SQL type for float values."""
        assert _sql_type(3.14) == "DOUBLE PRECISION"
        assert _sql_type(0.0) == "DOUBLE PRECISION"
        assert _sql_type(-2.5) == "DOUBLE PRECISION"

    def test_sql_type_string(self):
        """Test SQL type for string values."""
        assert _sql_type("hello") == "TEXT"
        assert _sql_type("") == "TEXT"
        assert _sql_type("123abc") == "TEXT"

    def test_sql_type_none(self):
        """Test SQL type for None values."""
        assert _sql_type(None) == "TEXT"

    def test_sql_type_list(self):
        """Test SQL type for list values."""
        assert _sql_type([1, 2, 3]) == "TEXT"

    def test_sql_type_dict(self):
        """Test SQL type for dict values."""
        assert _sql_type({"key": "value"}) == "TEXT"


class TestCollectColumnsAndTypes:
    """Tests for _collect_columns_and_types function."""

    def test_collect_columns_empty_rows(self):
        """Test collecting columns from empty row list."""
        result = _collect_columns_and_types([])
        assert result == {}

    def test_collect_columns_single_row(self):
        """Test collecting columns from single row."""
        rows = [{"id": 1, "name": "Alice", "score": 95.5}]
        result = _collect_columns_and_types(rows)
        assert result["id"] == "BIGINT"
        assert result["name"] == "TEXT"
        assert result["score"] == "DOUBLE PRECISION"

    def test_collect_columns_multiple_rows(self):
        """Test collecting columns from multiple rows."""
        rows = [
            {"id": 1, "active": True},
            {"id": 2, "active": False},
            {"id": 3, "active": True},
        ]
        result = _collect_columns_and_types(rows)
        assert result["id"] == "BIGINT"
        assert result["active"] == "BOOLEAN"

    def test_collect_columns_with_nulls(self):
        """Test collecting columns when some values are null."""
        rows = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": None},
            {"id": 3, "name": "Charlie"},
        ]
        result = _collect_columns_and_types(rows)
        assert result["id"] == "BIGINT"
        assert result["name"] == "TEXT"

    def test_collect_columns_all_nulls(self):
        """Test collecting columns when all values are null."""
        rows = [
            {"id": 1, "optional": None},
            {"id": 2, "optional": None},
        ]
        result = _collect_columns_and_types(rows)
        assert result["id"] == "BIGINT"
        assert result["optional"] == "TEXT"

    def test_collect_columns_sample_size(self):
        """Test that column collection samples rows correctly."""
        rows = [{"a": i} for i in range(100)]
        result = _collect_columns_and_types(rows, sample_n=10)
        assert result["a"] == "BIGINT"

    def test_collect_columns_mixed_types(self):
        """Test collecting columns with mixed data types."""
        rows = [
            {"id": 1, "name": "Alice", "score": 95.5, "active": True},
            {"id": 2, "name": "Bob", "score": 87.3, "active": False},
        ]
        result = _collect_columns_and_types(rows)
        assert len(result) == 4
        assert result["id"] == "BIGINT"
        assert result["name"] == "TEXT"
        assert result["score"] == "DOUBLE PRECISION"
        assert result["active"] == "BOOLEAN"

    def test_collect_columns_preserves_first_non_null(self):
        """Test that first non-null type is used for a column."""
        rows = [
            {"value": None},
            {"value": 42},
            {"value": 3.14},
        ]
        result = _collect_columns_and_types(rows)
        assert result["value"] == "BIGINT"


class TestGeneratePostgresPreview:
    """Tests for generate_postgres_preview function."""

    def test_generate_postgres_preview_empty_rows(self):
        """Test preview generation with no rows."""
        result = generate_postgres_preview([], "test_table")
        assert "create_table" in result
        assert "-- no rows" in result["create_table"]

    def test_generate_postgres_preview_basic(self):
        """Test basic preview generation."""
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users")
        assert "create_table" in result
        assert "CREATE TABLE" in result["create_table"]
        assert "users" in result["create_table"]
        assert '"id"' in result["create_table"]
        assert '"name"' in result["create_table"]

    def test_generate_postgres_preview_insert_example(self):
        """Test that insert example is generated."""
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users")
        assert "insert_example" in result
        assert "INSERT INTO" in result["insert_example"]
        assert "users" in result["insert_example"]

    def test_generate_postgres_preview_sample_row(self):
        """Test that sample row is included."""
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users")
        assert "sample_row" in result
        assert result["sample_row"] == {"id": 1, "name": "Alice"}

    def test_generate_postgres_preview_with_conflict_column(self):
        """Test preview generation with conflict column."""
        rows = [{"id": 1, "name": "Alice", "email": "alice@example.com"}]
        result = generate_postgres_preview(rows, "users", conflict_col="id")
        assert "index" in result
        assert "UNIQUE INDEX" in result["index"]
        assert "users_id_idx" in result["index"]
        assert "ON CONFLICT" in result["insert_example"]

    def test_generate_postgres_preview_conflict_column_not_in_row(self):
        """Test preview when conflict column not in data."""
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users", conflict_col="nonexistent")
        assert "index" in result
        assert result["index"] == ""

    def test_generate_postgres_preview_multiple_columns(self):
        """Test preview with multiple columns."""
        rows = [{"id": 1, "name": "Alice", "score": 95.5, "active": True}]
        result = generate_postgres_preview(rows, "data")
        assert "id" in result["create_table"]
        assert "name" in result["create_table"]
        assert "score" in result["create_table"]
        assert "active" in result["create_table"]

    def test_generate_postgres_preview_update_clause(self):
        """Test that UPDATE clause is generated correctly."""
        rows = [{"id": 1, "name": "Alice", "email": "alice@example.com"}]
        result = generate_postgres_preview(rows, "users", conflict_col="id")
        assert "DO UPDATE SET" in result["insert_example"]
        assert '"name" = EXCLUDED."name"' in result["insert_example"]
        assert '"email" = EXCLUDED."email"' in result["insert_example"]


class TestRunFromRows:
    """Tests for run_from_rows function."""

    def test_run_from_rows_empty_targets(self):
        """Test running with no targets."""
        rows = [{"id": 1, "name": "Alice"}]
        result = run_from_rows(rows, {}, dry_run=True)
        assert result["rows"] == 1
        assert result["targets"] == {}

    def test_run_from_rows_dry_run_postgres(self):
        """Test dry run with postgres target."""
        rows = [{"id": 1, "name": "Alice"}]
        targets = {
            "postgres": {
                "enabled": True,
                "table": "users",
                "dsn": "postgresql://localhost/test",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "postgres" in result["targets"]
        assert "preview" in result["targets"]["postgres"]
        assert "rows_upserted" not in result["targets"]["postgres"]

    def test_run_from_rows_dry_run_mongo(self):
        """Test dry run with mongo target."""
        rows = [{"id": 1, "name": "Alice"}]
        targets = {
            "mongo": {
                "enabled": True,
                "uri": "mongodb://localhost",
                "db": "test_db",
                "collection": "users",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "mongo" in result["targets"]
        assert "sample" in result["targets"]["mongo"]
        assert "count" in result["targets"]["mongo"]
        assert result["targets"]["mongo"]["count"] == 1

    def test_run_from_rows_dry_run_xlsx(self):
        """Test dry run with xlsx target."""
        rows = [{"id": 1, "name": "Alice"}]
        targets = {
            "xlsx": {
                "enabled": True,
                "path": "output.xlsx",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "xlsx" in result["targets"]
        assert "filename" in result["targets"]["xlsx"]
        assert "count" in result["targets"]["xlsx"]
        assert "written" not in result["targets"]["xlsx"]

    def test_run_from_rows_disabled_target(self):
        """Test that disabled targets are skipped."""
        rows = [{"id": 1}]
        targets = {
            "postgres": {"enabled": False},
            "mongo": {"enabled": False},
            "xlsx": {"enabled": False},
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert result["targets"] == {}

    def test_run_from_rows_multiple_targets(self):
        """Test running with multiple targets."""
        rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        targets = {
            "postgres": {"enabled": True, "table": "users", "dsn": "postgresql://localhost/test"},
            "xlsx": {"enabled": True, "path": "output.xlsx"},
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "postgres" in result["targets"]
        assert "xlsx" in result["targets"]
        assert result["rows"] == 2

    def test_run_from_rows_large_rows_sampled(self):
        """Test that large row sets are sampled correctly."""
        rows = [{"id": i, "name": f"User {i}"} for i in range(100)]
        targets = {
            "mongo": {
                "enabled": True,
                "uri": "mongodb://localhost",
                "db": "test_db",
                "collection": "users",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        # Mongo target should only show first 5 rows in sample
        assert len(result["targets"]["mongo"]["sample"]) <= 5
        assert result["targets"]["mongo"]["count"] == 100

    def test_run_from_rows_postgres_default_table(self):
        """Test postgres target uses default table name."""
        rows = [{"id": 1}]
        targets = {"postgres": {"enabled": True, "dsn": "postgresql://localhost/test"}}
        result = run_from_rows(rows, targets, dry_run=True)
        assert "socrata_data" in result["targets"]["postgres"]["preview"]["create_table"]

    def test_run_from_rows_xlsx_default_path(self):
        """Test xlsx target uses default path."""
        rows = [{"id": 1}]
        targets = {"xlsx": {"enabled": True}}
        result = run_from_rows(rows, targets, dry_run=True)
        assert "socrata_backup.xlsx" in result["targets"]["xlsx"]["filename"]

    @patch("socrata_toolkit.core.pipeline.PostgresExporter")
    def test_run_from_rows_postgres_upsert(self, mock_pg_exporter):
        """Test postgres target performs upsert on non-dry-run."""
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.upsert_batches.return_value = 1
        mock_pg_exporter.return_value = mock_instance

        rows = [{"id": 1, "name": "Alice"}]
        targets = {
            "postgres": {
                "enabled": True,
                "table": "users",
                "dsn": "postgresql://localhost/test",
            }
        }
        result = run_from_rows(rows, targets, dry_run=False)
        assert "rows_upserted" in result["targets"]["postgres"]
        assert result["targets"]["postgres"]["rows_upserted"] == 1

    @patch("socrata_toolkit.core.pipeline.XLSXExporter")
    def test_run_from_rows_xlsx_write(self, mock_xlsx_exporter):
        """Test xlsx target writes file on non-dry-run."""
        mock_instance = MagicMock()
        mock_xlsx_exporter.return_value = mock_instance

        rows = [{"id": 1, "name": "Alice"}]
        targets = {"xlsx": {"enabled": True, "path": "test.xlsx"}}
        result = run_from_rows(rows, targets, dry_run=False)
        assert "written" in result["targets"]["xlsx"]
        assert result["targets"]["xlsx"]["written"] is True
        mock_instance.write.assert_called_once()
