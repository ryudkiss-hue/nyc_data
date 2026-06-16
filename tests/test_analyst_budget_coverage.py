"""Comprehensive tests for analyst.budget module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from socrata_toolkit.analyst.budget import (
    load_budget_rules,
    validate_budget_codes,
)


class TestLoadBudgetRules:
    """Tests for load_budget_rules function."""

    def test_load_budget_rules_none_path(self):
        result = load_budget_rules(None)
        assert result == {}

    def test_load_budget_rules_nonexistent_path(self):
        result = load_budget_rules("/nonexistent/path/rules.yaml")
        assert result == {}

    def test_load_budget_rules_empty_string(self):
        result = load_budget_rules("")
        assert result == {}

    def test_load_budget_rules_valid_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_file = Path(tmpdir) / "rules.yaml"
            rules_file.write_text(
                "allowed_codes:\n  - B001\n  - B002\nrequire_code: true\n",
                encoding="utf-8",
            )

            result = load_budget_rules(rules_file)
            assert "allowed_codes" in result
            assert "B001" in result["allowed_codes"]
            assert result["require_code"] is True

    def test_load_budget_rules_empty_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_file = Path(tmpdir) / "empty.yaml"
            rules_file.write_text("", encoding="utf-8")

            result = load_budget_rules(rules_file)
            assert result == {}

    def test_load_budget_rules_with_path_object(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_file = Path(tmpdir) / "rules.yaml"
            rules_file.write_text("key: value\n", encoding="utf-8")

            result = load_budget_rules(rules_file)
            assert result["key"] == "value"

    def test_load_budget_rules_with_string_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_file = Path(tmpdir) / "rules.yaml"
            rules_file.write_text("test_key: test_value\n", encoding="utf-8")

            result = load_budget_rules(str(rules_file))
            assert result["test_key"] == "test_value"


class TestValidateBudgetCodes:
    """Tests for validate_budget_codes function."""

    def test_validate_budget_codes_empty_rules(self):
        df = pd.DataFrame({"budget_code": ["B001", "B002"]})
        result = validate_budget_codes(df, {})
        assert result == []

    def test_validate_budget_codes_empty_contracts(self):
        df = pd.DataFrame()
        rules = {"allowed_codes": ["B001", "B002"]}
        result = validate_budget_codes(df, rules)
        assert result == []

    def test_validate_budget_codes_none_rules(self):
        df = pd.DataFrame({"budget_code": ["B001"]})
        result = validate_budget_codes(df, None)
        assert result == []

    def test_validate_budget_codes_valid_codes(self):
        df = pd.DataFrame({"budget_code": ["B001", "B002", "B001"]})
        rules = {
            "allowed_codes": ["B001", "B002", "B003"],
            "require_code": False,
        }
        result = validate_budget_codes(df, rules)
        assert result == []

    def test_validate_budget_codes_invalid_codes(self):
        df = pd.DataFrame({"budget_code": ["B001", "B999", "B001"]})
        rules = {"allowed_codes": ["B001", "B002"]}
        result = validate_budget_codes(df, rules)
        assert len(result) == 1
        assert "B999" in result[0]

    def test_validate_budget_codes_multiple_invalid(self):
        df = pd.DataFrame({"budget_code": ["B001", "B999", "B888", "B777"]})
        rules = {"allowed_codes": ["B001", "B002"]}
        result = validate_budget_codes(df, rules)
        assert len(result) == 3

    def test_validate_budget_codes_missing_column(self):
        df = pd.DataFrame({"other_col": ["B001"]})
        rules = {"allowed_codes": ["B001"], "require_code": False}
        result = validate_budget_codes(df, rules)
        assert result == []

    def test_validate_budget_codes_missing_column_required(self):
        df = pd.DataFrame({"other_col": ["B001"]})
        rules = {"allowed_codes": ["B001"], "require_code": True}
        result = validate_budget_codes(df, rules)
        assert len(result) == 1
        assert "missing" in result[0].lower()

    def test_validate_budget_codes_with_null_values(self):
        df = pd.DataFrame({"budget_code": ["B001", None, "B002", None]})
        rules = {
            "allowed_codes": ["B001", "B002"],
            "require_code": False,
        }
        result = validate_budget_codes(df, rules)
        assert result == []

    def test_validate_budget_codes_missing_values_not_required(self):
        df = pd.DataFrame({"budget_code": ["B001", None, "B002"]})
        rules = {
            "allowed_codes": ["B001", "B002"],
            "require_code": False,
        }
        result = validate_budget_codes(df, rules)
        assert result == []

    def test_validate_budget_codes_missing_values_required(self):
        df = pd.DataFrame({"budget_code": ["B001", None, "B002", None]})
        rules = {
            "allowed_codes": ["B001", "B002"],
            "require_code": True,
        }
        result = validate_budget_codes(df, rules)
        assert len(result) == 1
        assert "2" in result[0]
        assert "missing" in result[0].lower()

    def test_validate_budget_codes_no_allowed_codes_no_require(self):
        df = pd.DataFrame({"budget_code": ["B001", "B999"]})
        rules = {"allowed_codes": [], "require_code": False}
        result = validate_budget_codes(df, rules)
        assert result == []

    def test_validate_budget_codes_custom_code_col(self):
        df = pd.DataFrame({"custom_code": ["C001", "C999"]})
        rules = {"allowed_codes": ["C001", "C002"]}
        result = validate_budget_codes(df, rules, code_col="custom_code")
        assert len(result) == 1
        assert "C999" in result[0]

    def test_validate_budget_codes_numeric_coercion(self):
        df = pd.DataFrame({"budget_code": [1001, 2001, 1001]})
        rules = {"allowed_codes": ["1001", "2001", "3001"]}
        result = validate_budget_codes(df, rules)
        assert result == []

    def test_validate_budget_codes_all_null(self):
        df = pd.DataFrame({"budget_code": [None, None, None]})
        rules = {
            "allowed_codes": ["B001"],
            "require_code": True,
        }
        result = validate_budget_codes(df, rules)
        assert len(result) == 1
        assert "3" in result[0]

    def test_validate_budget_codes_mixed_valid_invalid_null(self):
        df = pd.DataFrame({"budget_code": ["B001", "B999", None, "B002"]})
        rules = {
            "allowed_codes": ["B001", "B002"],
            "require_code": True,
        }
        result = validate_budget_codes(df, rules)
        assert len(result) == 2
        assert any("B999" in w for w in result)
        assert any("1" in w and "missing" in w.lower() for w in result)
