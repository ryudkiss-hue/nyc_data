import pytest

from socrata_toolkit.analysis import build_weighted_rank_sql, websearch_to_tsquery_sql


def test_build_weighted_rank_sql_basic():
    sql = build_weighted_rank_sql(["description", "name"])
    assert "ts_rank" in sql
    assert "final_rank" in sql
    assert "description" in sql
    assert "name" in sql


def test_build_weighted_rank_sql_empty_columns():
    with pytest.raises(ValueError, match="At least one text column"):
        build_weighted_rank_sql([])


def test_build_weighted_rank_sql_custom_weights():
    sql = build_weighted_rank_sql(["desc"], weight_text=2.0, weight_geo=0.5, weight_age=0.3)
    assert "2.0" in sql
    assert "0.5" in sql
    assert "0.3" in sql


def test_websearch_to_tsquery_sql():
    sql = websearch_to_tsquery_sql()
    assert "websearch_to_tsquery" in sql
    assert "%s" in sql
