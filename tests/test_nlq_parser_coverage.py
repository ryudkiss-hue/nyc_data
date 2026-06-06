"""Tests for nlq_parser module."""
from __future__ import annotations

import pytest

from socrata_toolkit.nlq_parser import QueryIntent, parse_query


class TestQueryIntent:
    """Tests for QueryIntent dataclass."""

    def test_query_intent_creation(self):
        intent = QueryIntent(intent="show", target="defects")
        assert intent.intent == "show"
        assert intent.target == "defects"
        assert intent.group_by is None
        assert intent.filters == {}

    def test_query_intent_with_groupby(self):
        intent = QueryIntent(intent="count", target="inspections", group_by="borough")
        assert intent.group_by == "borough"

    def test_query_intent_with_filters(self):
        intent = QueryIntent(
            intent="show",
            target="defects",
            filters={"borough": "MANHATTAN", "severity": "critical"},
        )
        assert intent.filters["borough"] == "MANHATTAN"
        assert intent.filters["severity"] == "critical"


class TestParseQuery:
    """Tests for parse_query function."""

    def test_parse_query_show_intent(self):
        result = parse_query("show me the defects")
        assert result.intent == "show"
        assert result.target == "defects"

    def test_parse_query_map_intent(self):
        result = parse_query("map the inspections")
        assert result.intent == "show"

    def test_parse_query_count_intent(self):
        result = parse_query("count the violations")
        assert result.intent == "count"

    def test_parse_query_compare_intent(self):
        result = parse_query("compare costs across boroughs")
        assert result.intent == "compare"

    def test_parse_query_get_intent(self):
        result = parse_query("what is the compliance rate")
        assert result.intent == "get"

    def test_parse_query_defect_target(self):
        result = parse_query("show defects")
        assert result.target == "defects"

    def test_parse_query_inspection_target(self):
        result = parse_query("show inspections")
        assert result.target == "inspections"

    def test_parse_query_cost_target(self):
        result = parse_query("show cost")
        assert result.target == "cost"

    def test_parse_query_rate_target(self):
        result = parse_query("show rate")
        assert result.target == "rate"

    def test_parse_query_compliance_target(self):
        result = parse_query("show compliance")
        assert result.target == "compliance"

    def test_parse_query_group_by_borough(self):
        result = parse_query("show defects by borough")
        assert result.group_by == "borough"

    def test_parse_query_group_by_material(self):
        result = parse_query("count by material")
        assert result.group_by == "material_type"

    def test_parse_query_filter_manhattan(self):
        result = parse_query("defects in manhattan")
        assert result.filters.get("borough") == "MANHATTAN"

    def test_parse_query_filter_brooklyn(self):
        result = parse_query("brooklyn defects")
        assert result.filters.get("borough") == "BROOKLYN"

    def test_parse_query_filter_queens(self):
        result = parse_query("queens violations")
        assert result.filters.get("borough") == "QUEENS"

    def test_parse_query_filter_bronx(self):
        result = parse_query("bronx inspections")
        assert result.filters.get("borough") == "BRONX"

    def test_parse_query_filter_staten_island(self):
        result = parse_query("staten island complaints")
        assert result.filters.get("borough") == "STATEN ISLAND"

    def test_parse_query_severity_hazardous(self):
        result = parse_query("hazardous defects")
        assert result.filters.get("severity") == "hazardous"

    def test_parse_query_severity_critical(self):
        result = parse_query("critical violations")
        assert result.filters.get("severity") == "critical"

    def test_parse_query_severity_severe(self):
        result = parse_query("severe defects")
        assert result.filters.get("severity") == "severe"

    def test_parse_query_ada_compliance_special_case(self):
        result = parse_query("ada compliance rate")
        assert result.target == "ada_compliance_rate"
        assert result.intent == "get"

    def test_parse_query_cost_special_case(self):
        result = parse_query("what is the cost")
        assert result.target == "cost"

    def test_parse_query_default_intent(self):
        result = parse_query("xyz abc def")
        # No recognized intent, defaults to "show"
        assert result.intent == "show"

    def test_parse_query_default_target(self):
        result = parse_query("count something")
        # No recognized target, defaults to "defects"
        assert result.target == "defects"

    def test_parse_query_complex(self):
        result = parse_query("Show me inspections by borough for critical severity in manhattan")
        assert result.intent == "show"
        assert result.target == "inspections"
        assert result.group_by == "borough"
        assert result.filters.get("borough") == "MANHATTAN"
        assert result.filters.get("severity") == "critical"

    def test_parse_query_empty_string(self):
        result = parse_query("")
        assert result is not None
        assert result.intent == "show"  # default
        assert result.target == "defects"  # default

    def test_parse_query_none_returns_none_or_default(self):
        # Test edge case with minimal input
        result = parse_query("x")
        assert result is not None
