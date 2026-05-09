import pandas as pd
import pytest

from socrata_toolkit.sql_integration import (
    SQLQueryBuilder,
    dataframe_to_create_table,
    dataframe_to_insert_sql,
    dataframe_to_upsert_sql,
    export_as_sql_file,
    generate_analytics_view,
    generate_cte_summary,
    generate_window_query,
)


def _sample():
    return pd.DataFrame({
        "id": [1, 2, 3],
        "borough": ["MANHATTAN", "BROOKLYN", "QUEENS"],
        "violations": [5, 8, 2],
        "status": ["Pending", "Complete", "Pending"],
    })


def test_dataframe_to_create_table():
    df = _sample()
    sql = dataframe_to_create_table(df, "inspections", primary_key="id")
    assert "CREATE TABLE" in sql
    assert '"inspections"' in sql
    assert "PRIMARY KEY" in sql
    assert "BIGINT" in sql


def test_dataframe_to_create_table_sqlite():
    df = _sample()
    sql = dataframe_to_create_table(df, "t", dialect="sqlite")
    assert "INTEGER" in sql


def test_dataframe_to_insert_sql():
    df = _sample()
    sql = dataframe_to_insert_sql(df, "inspections")
    assert "INSERT INTO" in sql
    assert "'MANHATTAN'" in sql
    assert "5" in sql


def test_dataframe_to_insert_sql_empty():
    df = pd.DataFrame()
    sql = dataframe_to_insert_sql(df, "empty")
    assert "No data" in sql


def test_dataframe_to_upsert_sql():
    df = _sample()
    sql = dataframe_to_upsert_sql(df, "inspections", "id")
    assert "ON CONFLICT" in sql
    assert "EXCLUDED" in sql


def test_generate_analytics_view():
    sql = generate_analytics_view(
        "inspections", "borough_summary",
        group_cols=["borough"],
        agg_expressions={"total_violations": "SUM(violations)", "cnt": "COUNT(*)"},
    )
    assert "CREATE OR REPLACE VIEW" in sql
    assert "borough_summary" in sql
    assert "SUM(violations)" in sql


def test_generate_window_query():
    sql = generate_window_query("inspections", "borough", "id", "violations")
    assert "ROW_NUMBER()" in sql
    assert "PARTITION BY" in sql
    assert "LAG" in sql


def test_generate_cte_summary():
    sql = generate_cte_summary("inspections")
    assert "WITH borough_stats AS" in sql
    assert "RANK()" in sql


def test_sql_query_builder():
    q = (SQLQueryBuilder("inspections")
        .select("borough", "COUNT(*) as cnt")
        .where("status = 'Pending'")
        .group_by("borough")
        .having("COUNT(*) > 1")
        .order_by("cnt DESC")
        .limit(10)
        .build())
    assert "SELECT borough" in q
    assert "WHERE status" in q
    assert "GROUP BY borough" in q
    assert "HAVING COUNT" in q
    assert "ORDER BY cnt" in q
    assert "LIMIT 10" in q


def test_sql_query_builder_join():
    q = (SQLQueryBuilder("inspections")
        .select("*")
        .join("contracts", "inspections.contract_id = contracts.id", "LEFT")
        .build())
    assert "LEFT JOIN contracts" in q


def test_export_as_sql_file(tmp_path):
    df = _sample()
    path = str(tmp_path / "export.sql")
    result = export_as_sql_file(df, "inspections", path)
    content = open(result).read()
    assert "CREATE TABLE" in content
    assert "INSERT INTO" in content
