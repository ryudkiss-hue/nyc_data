import pytest

from socrata_toolkit.core import build_fts_index_sql


def test_build_fts_index_sql_single_column():
    sql = build_fts_index_sql("complaints", ["description"])
    assert "CREATE INDEX IF NOT EXISTS" in sql
    assert "USING GIN" in sql
    assert "to_tsvector" in sql
    assert "description" in sql


def test_build_fts_index_sql_multiple_columns():
    sql = build_fts_index_sql("complaints", ["description", "status"])
    assert "description" in sql
    assert "status" in sql
    assert "||" in sql


def test_build_fts_index_sql_custom_name():
    sql = build_fts_index_sql("t", ["c"], index_name="my_idx")
    assert "my_idx" in sql


def test_build_fts_index_sql_empty_columns():
    with pytest.raises(ValueError, match="non-empty"):
        build_fts_index_sql("t", [])
