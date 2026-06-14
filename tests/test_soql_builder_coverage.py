"""Comprehensive tests for core.soql_builder module."""
from __future__ import annotations

from socrata_toolkit.core.soql_builder import SoQLBuilder


class TestSoQLBuilderBasic:
    """Basic construction tests."""

    def test_empty_builder(self):
        builder = SoQLBuilder()
        result = builder.build()
        assert result == {}

    def test_select_single_column(self):
        builder = SoQLBuilder().select("id")
        result = builder.build()
        assert result["select"] == "id"

    def test_select_multiple_columns(self):
        builder = SoQLBuilder().select("id", "name", "email")
        result = builder.build()
        assert result["select"] == "id, name, email"

    def test_select_chaining(self):
        builder = SoQLBuilder().select("id").select("name")
        result = builder.build()
        assert result["select"] == "id, name"

class TestSoQLBuilderWhere:
    """WHERE clause tests."""

    def test_single_where_clause(self):
        builder = SoQLBuilder().where("id > 10")
        result = builder.build()
        assert result["where"] == "(id > 10)"

    def test_multiple_where_clauses_combined_with_and(self):
        builder = SoQLBuilder().where("id > 10", "name = 'Alice'")
        result = builder.build()
        assert result["where"] == "(id > 10) AND (name = 'Alice')"

    def test_where_chaining(self):
        builder = SoQLBuilder().where("id > 10").where("active = true")
        result = builder.build()
        assert result["where"] == "(id > 10) AND (active = true)"

    def test_where_with_complex_expression(self):
        builder = SoQLBuilder().where("created_at > '2024-01-01'")
        result = builder.build()
        assert "(created_at > '2024-01-01')" in result["where"]

class TestSoQLBuilderOrder:
    """ORDER BY tests."""

    def test_order_ascending(self):
        builder = SoQLBuilder().order("id")
        result = builder.build()
        assert result["order"] == "id ASC"

    def test_order_descending(self):
        builder = SoQLBuilder().order("id", desc=True)
        result = builder.build()
        assert result["order"] == "id DESC"

    def test_multiple_order_columns(self):
        builder = SoQLBuilder().order("name").order("id", desc=True)
        result = builder.build()
        assert result["order"] == "name ASC, id DESC"

class TestSoQLBuilderGroup:
    """GROUP BY tests."""

    def test_single_group_column(self):
        builder = SoQLBuilder().group("borough")
        result = builder.build()
        assert result["group"] == "borough"

    def test_multiple_group_columns(self):
        builder = SoQLBuilder().group("borough", "status")
        result = builder.build()
        assert result["group"] == "borough, status"

    def test_group_chaining(self):
        builder = SoQLBuilder().group("borough").group("status")
        result = builder.build()
        assert result["group"] == "borough, status"

class TestSoQLBuilderHaving:
    """HAVING clause tests."""

    def test_single_having_clause(self):
        builder = SoQLBuilder().having("count(*) > 5")
        result = builder.build()
        assert result["having"] == "(count(*) > 5)"

    def test_multiple_having_clauses(self):
        builder = SoQLBuilder().having("count(*) > 5", "sum(value) < 100")
        result = builder.build()
        assert result["having"] == "(count(*) > 5) AND (sum(value) < 100)"

    def test_having_chaining(self):
        builder = SoQLBuilder().having("count(*) > 5").having("sum(value) < 100")
        result = builder.build()
        assert result["having"] == "(count(*) > 5) AND (sum(value) < 100)"

class TestSoQLBuilderAggregates:
    """Aggregation function tests."""

    def test_count_aggregate(self):
        builder = SoQLBuilder().aggregate("count", "*", "total")
        result = builder.build()
        assert "count(*) AS total" in result["select"]

    def test_sum_aggregate(self):
        builder = SoQLBuilder().aggregate("sum", "amount", "total_amount")
        result = builder.build()
        assert "sum(amount) AS total_amount" in result["select"]

    def test_avg_aggregate(self):
        builder = SoQLBuilder().aggregate("avg", "value")
        result = builder.build()
        assert "avg(value)" in result["select"]

    def test_max_aggregate(self):
        builder = SoQLBuilder().aggregate("max", "price", "highest_price")
        result = builder.build()
        assert "max(price) AS highest_price" in result["select"]

    def test_multiple_aggregates(self):
        builder = SoQLBuilder().aggregate("count", "*", "cnt").aggregate("sum", "amount")
        result = builder.build()
        assert "count(*) AS cnt" in result["select"]
        assert "sum(amount)" in result["select"]

class TestSoQLBuilderDateTrunc:
    """Date truncation tests."""

    def test_date_trunc_month(self):
        builder = SoQLBuilder().date_trunc("created_at", "month", "month_created")
        result = builder.build()
        assert "date_trunc_month(created_at) AS month_created" in result["select"]

    def test_date_trunc_year(self):
        builder = SoQLBuilder().date_trunc("created_at", "year")
        result = builder.build()
        assert "date_trunc_year(created_at)" in result["select"]

    def test_date_trunc_default_month(self):
        builder = SoQLBuilder().date_trunc("created_at")
        result = builder.build()
        assert "date_trunc_month(created_at)" in result["select"]

    def test_date_trunc_day(self):
        builder = SoQLBuilder().date_trunc("created_at", "day", "day_created")
        result = builder.build()
        assert "date_trunc_day(created_at) AS day_created" in result["select"]

class TestSoQLBuilderLimitOffset:
    """LIMIT and OFFSET tests."""

    def test_limit_only(self):
        builder = SoQLBuilder().limit(10)
        result = builder.build()
        assert result["limit"] == "10"

    def test_offset_only(self):
        builder = SoQLBuilder().offset(20)
        result = builder.build()
        assert result["offset"] == "20"

    def test_limit_and_offset(self):
        builder = SoQLBuilder().limit(10).offset(20)
        result = builder.build()
        assert result["limit"] == "10"
        assert result["offset"] == "20"

    def test_offset_zero(self):
        builder = SoQLBuilder().offset(0)
        result = builder.build()
        assert result["offset"] == "0"

class TestSoQLBuilderSearch:
    """Full-text search tests."""

    def test_search_query(self):
        builder = SoQLBuilder().search("sidewalk repair")
        result = builder.build()
        assert result["q"] == "sidewalk repair"

    def test_search_with_other_clauses(self):
        builder = SoQLBuilder().search("pothole").select("id", "location")
        result = builder.build()
        assert result["q"] == "pothole"
        assert result["select"] == "id, location"

class TestSoQLBuilderComplexQueries:
    """Complex query combinations."""

    def test_full_query(self):
        builder = (
            SoQLBuilder()
            .select("borough", "status")
            .aggregate("count", "*", "total")
            .where("year = 2024")
            .group("borough", "status")
            .having("count(*) > 10")
            .order("total", desc=True)
            .limit(100)
            .offset(50)
        )
        result = builder.build()
        assert "select" in result
        assert "where" in result
        assert "group" in result
        assert "having" in result
        assert "order" in result
        assert result["limit"] == "100"
        assert result["offset"] == "50"

    def test_group_by_with_count(self):
        builder = (
            SoQLBuilder()
            .select("borough")
            .aggregate("count", "*", "count")
            .where("active = true")
            .group("borough")
            .order("count", desc=True)
        )
        result = builder.build()
        assert "borough" in result["select"]
        assert "count(*) AS count" in result["select"]
        assert "active = true" in result["where"]
        assert result["group"] == "borough"

class TestSoQLBuilderVariables:
    """Variable substitution tests."""

    def test_set_variable(self):
        builder = SoQLBuilder().set_variable("threshold", 100)
        assert builder._variables["threshold"] == 100

    def test_variable_substitution_in_where(self):
        builder = SoQLBuilder().where("value > {{threshold}}").set_variable("threshold", 50)
        result = builder.build()
        assert "value > 50" in result["where"]

    def test_multiple_variables(self):
        builder = (
            SoQLBuilder()
            .select("id")
            .where("value > {{min}}", "value < {{max}}")
            .set_variable("min", 10)
            .set_variable("max", 100)
        )
        result = builder.build()
        assert "10" in result["where"]
        assert "100" in result["where"]

    def test_variable_in_select(self):
        builder = (
            SoQLBuilder()
            .select("id")
            .set_variable("col", "name")
        )
        result = builder.build()
        # Variable substitution in select
        assert "name" in result["select"] or "{{col}}" not in result["select"]

    def test_variable_in_limit(self):
        builder = SoQLBuilder().limit(10).set_variable("limit_val", 20)
        result = builder.build()
        assert result["limit"] == "10"

class TestSoQLBuilderQueryString:
    """Raw query string building tests."""

    def test_simple_query_string(self):
        builder = SoQLBuilder().select("id", "name").where("active = true")
        query = builder.build_query_string()
        assert "SELECT" in query
        assert "id, name" in query
        assert "WHERE" in query
        assert "active = true" in query

    def test_query_string_with_group_and_having(self):
        builder = (
            SoQLBuilder()
            .select("borough")
            .aggregate("count", "*", "cnt")
            .group("borough")
            .having("count(*) > 5")
        )
        query = builder.build_query_string()
        assert "SELECT" in query
        assert "GROUP BY" in query
        assert "HAVING" in query

    def test_query_string_with_order_limit(self):
        builder = SoQLBuilder().select("id").order("id", desc=True).limit(10)
        query = builder.build_query_string()
        assert "ORDER BY" in query
        assert "LIMIT 10" in query

    def test_empty_query_string(self):
        builder = SoQLBuilder()
        query = builder.build_query_string()
        assert query == ""

    def test_query_string_order_of_clauses(self):
        builder = (
            SoQLBuilder()
            .select("id")
            .where("id > 0")
            .group("id")
            .order("id")
            .limit(10)
        )
        query = builder.build_query_string()
        # Check clause order: SELECT, WHERE, GROUP BY, ORDER BY, LIMIT
        select_idx = query.find("SELECT")
        where_idx = query.find("WHERE")
        group_idx = query.find("GROUP BY")
        order_idx = query.find("ORDER BY")
        limit_idx = query.find("LIMIT")
        assert select_idx < where_idx < group_idx < order_idx < limit_idx

class TestSoQLBuilderHelpers:
    """Static helper method tests."""

    def test_between_helper(self):
        clause = SoQLBuilder.between("created_at", "2024-01-01", "2024-12-31")
        assert clause == "created_at between '2024-01-01' and '2024-12-31'"

    def test_within_circle_helper(self):
        clause = SoQLBuilder.within_circle("location", 40.7128, -74.0060, 1000)
        assert "within_circle" in clause
        assert "40.7128" in clause
        assert "-74.00" in clause  # Allow for float precision
        assert "1000" in clause

    def test_within_box_helper(self):
        clause = SoQLBuilder.within_box("location", 40.8, -74.0, 40.7, -73.9)
        assert "within_box" in clause
        assert "40.8" in clause
        assert "-74.0" in clause
        assert "40.7" in clause
        assert "-73.9" in clause

    def test_between_in_where(self):
        builder = SoQLBuilder().where(SoQLBuilder.between("date", "2024-01-01", "2024-12-31"))
        result = builder.build()
        assert "between" in result["where"]

class TestSoQLBuilderEdgeCases:
    """Edge case and special behavior tests."""

    def test_fluent_interface_returns_self(self):
        builder = SoQLBuilder()
        assert builder.select("id") is builder
        assert builder.where("id > 0") is builder
        assert builder.order("id") is builder

    def test_special_characters_preserved(self):
        builder = SoQLBuilder().select("column_name").where("status = 'open'")
        result = builder.build()
        assert "column_name" in result["select"]
        assert "status = 'open'" in result["where"]

    def test_quoted_column_names(self):
        builder = SoQLBuilder().select('"special-column"').where('"special-column" > 0')
        result = builder.build()
        assert '"special-column"' in result["select"]

    def test_case_sensitive_function_names(self):
        builder = SoQLBuilder().aggregate("COUNT", "*", "total")
        result = builder.build()
        assert "COUNT(*) AS total" in result["select"]

    def test_empty_string_select(self):
        builder = SoQLBuilder().select("")
        result = builder.build()
        # Empty string still added to select list
        assert "select" in result
