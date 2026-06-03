"""Comprehensive tests for core.pipeline module."""
from __future__ import annotations

import pytest

from socrata_toolkit.core.pipeline import (
    _collect_columns_and_types,
    _sql_type,
    generate_postgres_preview,
    run_from_rows,
)


class TestSqlType:
    """Tests for _sql_type function."""

    def test_boolean_type(self):
        assert _sql_type(True) == "BOOLEAN"
        assert _sql_type(False) == "BOOLEAN"

    def test_integer_type(self):
        assert _sql_type(42) == "BIGINT"
        assert _sql_type(0) == "BIGINT"
        assert _sql_type(-100) == "BIGINT"

    def test_float_type(self):
        assert _sql_type(3.14) == "DOUBLE PRECISION"
        assert _sql_type(0.0) == "DOUBLE PRECISION"
        assert _sql_type(-2.5) == "DOUBLE PRECISION"

    def test_string_type(self):
        assert _sql_type("hello") == "TEXT"
        assert _sql_type("") == "TEXT"

    def test_none_type(self):
        assert _sql_type(None) == "TEXT"

    def test_list_type(self):
        assert _sql_type([1, 2, 3]) == "TEXT"

    def test_dict_type(self):
        assert _sql_type({"key": "value"}) == "TEXT"


class TestCollectColumnsAndTypes:
    """Tests for _collect_columns_and_types function."""

    def test_empty_rows(self):
        result = _collect_columns_and_types([])
        assert result == {}

    def test_single_row(self):
        rows = [{"id": 1, "name": "Alice", "active": True}]
        result = _collect_columns_and_types(rows)
        assert result == {"id": "BIGINT", "name": "TEXT", "active": "BOOLEAN"}

    def test_multiple_rows_with_consistent_types(self):
        rows = [
            {"id": 1, "value": 10.5},
            {"id": 2, "value": 20.3},
        ]
        result = _collect_columns_and_types(rows)
        assert result == {"id": "BIGINT", "value": "DOUBLE PRECISION"}

    def test_mixed_types_uses_first_non_null(self):
        rows = [
            {"id": 1, "data": None},
            {"id": 2, "data": "text"},
        ]
        result = _collect_columns_and_types(rows)
        assert result == {"id": "BIGINT", "data": "TEXT"}

    def test_all_none_values_default_to_text(self):
        rows = [
            {"id": 1, "missing": None},
            {"id": 2, "missing": None},
        ]
        result = _collect_columns_and_types(rows)
        assert result["missing"] == "TEXT"

    def test_varying_columns_across_rows(self):
        rows = [
            {"id": 1, "col_a": "text"},
            {"id": 2, "col_b": 42},
        ]
        result = _collect_columns_and_types(rows)
        assert "id" in result
        assert "col_a" in result
        assert "col_b" in result

    def test_sample_n_limits_rows_examined(self):
        rows = [
            {"id": i, "value": i * 1.0}
            for i in range(100)
        ]
        result = _collect_columns_and_types(rows, sample_n=5)
        # Should still detect types correctly even with small sample
        assert result["id"] == "BIGINT"
        assert result["value"] == "DOUBLE PRECISION"

    def test_boolean_not_confused_with_int(self):
        rows = [{"flag": True}]
        result = _collect_columns_and_types(rows)
        assert result["flag"] == "BOOLEAN"


class TestGeneratePostgresPreview:
    """Tests for generate_postgres_preview function."""

    def test_empty_rows(self):
        result = generate_postgres_preview([], "test_table")
        assert result["create_table"] == "-- no rows to infer schema"
        assert result["insert_example"] == "-- none"

    def test_simple_insert_preview(self):
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users")
        assert "CREATE TABLE" in result["create_table"]
        assert '"users"' in result["create_table"]
        assert '"id"' in result["create_table"]
        assert '"name"' in result["create_table"]
        assert "INSERT INTO" in result["insert_example"]

    def test_conflict_column_index_creation(self):
        rows = [{"id": 1, "email": "alice@example.com"}]
        result = generate_postgres_preview(rows, "users", conflict_col="id")
        assert "CREATE UNIQUE INDEX" in result["index"]
        assert '"users_id_idx"' in result["index"]
        assert '"id"' in result["index"]

    def test_conflict_column_upsert_sql(self):
        rows = [{"id": 1, "name": "Alice", "updated": "2024-01-01"}]
        result = generate_postgres_preview(rows, "users", conflict_col="id")
        insert_sql = result["insert_example"]
        assert "ON CONFLICT" in insert_sql
        assert '"id"' in insert_sql
        assert "DO UPDATE SET" in insert_sql

    def test_conflict_column_not_updated(self):
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users", conflict_col="id")
        insert_sql = result["insert_example"]
        # id should not be in the UPDATE SET clause
        assert 'SET "id"' not in insert_sql
        assert 'SET "name"' in insert_sql

    def test_conflict_column_not_in_table(self):
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users", conflict_col="nonexistent")
        # Should not create index if column doesn't exist
        assert result["index"] == ""

    def test_single_column_no_updates(self):
        rows = [{"id": 1}]
        result = generate_postgres_preview(rows, "ids", conflict_col="id")
        insert_sql = result["insert_example"]
        # When id is the only column, no UPDATE SET should be generated
        assert "DO NOTHING" in insert_sql

    def test_sample_row_included(self):
        rows = [{"id": 1, "name": "Alice"}]
        result = generate_postgres_preview(rows, "users")
        assert result["sample_row"] == {"id": 1, "name": "Alice"}


class TestRunFromRows:
    """Tests for run_from_rows function."""

    def test_dry_run_no_actual_export(self):
        rows = [{"id": 1, "value": 10}]
        targets = {
            "postgres": {
                "enabled": True,
                "table": "test_table",
                "dsn": "invalid_connection_string",
            }
        }
        # Dry run should not fail even with invalid DSN
        result = run_from_rows(rows, targets, dry_run=True)
        assert result["rows"] == 1
        assert "postgres" in result["targets"]
        assert "preview" in result["targets"]["postgres"]

    def test_empty_rows(self):
        result = run_from_rows([], {}, dry_run=True)
        assert result["rows"] == 0
        assert result["targets"] == {}

    def test_postgres_target_disabled(self):
        rows = [{"id": 1}]
        targets = {
            "postgres": {
                "enabled": False,
                "table": "test",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "postgres" not in result["targets"]

    def test_postgres_target_enabled(self):
        rows = [{"id": 1, "name": "Test"}]
        targets = {
            "postgres": {
                "enabled": True,
                "table": "test_table",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "postgres" in result["targets"]
        assert "preview" in result["targets"]["postgres"]
        preview = result["targets"]["postgres"]["preview"]
        assert "create_table" in preview
        assert "insert_example" in preview

    def test_mongo_target_disabled(self):
        rows = [{"id": 1}]
        targets = {
            "mongo": {
                "enabled": False,
                "uri": "mongodb://localhost",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "mongo" not in result["targets"]

    def test_mongo_target_enabled(self):
        rows = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
        targets = {
            "mongo": {
                "enabled": True,
                "uri": "mongodb://localhost",
                "db": "test_db",
                "collection": "test_col",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "mongo" in result["targets"]
        assert result["targets"]["mongo"]["count"] == 5
        assert len(result["targets"]["mongo"]["sample"]) == 5

    def test_mongo_target_sample_limit(self):
        rows = [{"id": i} for i in range(20)]
        targets = {
            "mongo": {
                "enabled": True,
                "uri": "mongodb://localhost",
                "db": "test",
                "collection": "col",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        # Sample should be limited to first 5
        assert len(result["targets"]["mongo"]["sample"]) == 5

    def test_xlsx_target_disabled(self):
        rows = [{"id": 1}]
        targets = {
            "xlsx": {
                "enabled": False,
                "path": "/tmp/test.xlsx",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "xlsx" not in result["targets"]

    def test_xlsx_target_enabled(self):
        rows = [{"id": 1}, {"id": 2}]
        targets = {
            "xlsx": {
                "enabled": True,
                "path": "/tmp/test.xlsx",
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "xlsx" in result["targets"]
        assert result["targets"]["xlsx"]["count"] == 2
        assert result["targets"]["xlsx"]["filename"] == "/tmp/test.xlsx"
        assert "written" not in result["targets"]["xlsx"]

    def test_xlsx_default_filename(self):
        rows = [{"id": 1}]
        targets = {
            "xlsx": {
                "enabled": True,
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert result["targets"]["xlsx"]["filename"] == "socrata_backup.xlsx"

    def test_postgres_default_table_name(self):
        rows = [{"id": 1}]
        targets = {
            "postgres": {
                "enabled": True,
            }
        }
        result = run_from_rows(rows, targets, dry_run=True)
        preview = result["targets"]["postgres"]["preview"]
        assert "socrata_data" in preview["create_table"]

    def test_multiple_targets_simultaneously(self):
        rows = [{"id": 1}]
        targets = {
            "postgres": {"enabled": True},
            "mongo": {"enabled": True, "uri": "mongodb://localhost", "db": "test"},
            "xlsx": {"enabled": True},
        }
        result = run_from_rows(rows, targets, dry_run=True)
        assert "postgres" in result["targets"]
        assert "mongo" in result["targets"]
        assert "xlsx" in result["targets"]

    def test_no_targets(self):
        rows = [{"id": 1}]
        result = run_from_rows(rows, {}, dry_run=True)
        assert result["rows"] == 1
        assert result["targets"] == {}
