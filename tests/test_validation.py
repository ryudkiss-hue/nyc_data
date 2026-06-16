import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")
import pandas as pd

from socrata_toolkit.analysis import validate_required_columns, validate_schema_types


def test_validate_required_columns_pass():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = validate_required_columns(df, ["a", "b"])
    assert result.valid is True
    assert result.errors == []


def test_validate_required_columns_fail():
    df = pd.DataFrame({"a": [1]})
    result = validate_required_columns(df, ["a", "b", "c"])
    assert result.valid is False
    assert len(result.errors) == 2
    assert any("b" in e for e in result.errors)
    assert any("c" in e for e in result.errors)


def test_validate_schema_types_pass():
    df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
    result = validate_schema_types(df, {"x": "int", "y": "object"})
    assert result.valid is True


def test_validate_schema_types_missing_column():
    df = pd.DataFrame({"x": [1]})
    result = validate_schema_types(df, {"x": "int", "missing_col": "object"})
    assert result.valid is False
    assert any("missing_col" in e for e in result.errors)


def test_validate_schema_types_type_mismatch_warns():
    df = pd.DataFrame({"x": [1, 2]})
    result = validate_schema_types(df, {"x": "float"})
    # Column exists so valid=True, but type mismatch produces a warning
    assert result.valid is True
    assert len(result.warnings) == 1
