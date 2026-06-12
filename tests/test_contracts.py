"""Tests for socrata_toolkit.contracts data-contract validation."""

from __future__ import annotations

import pandas as pd

from socrata_toolkit.contracts import (
    ContractViolation,
    DataContract,
    FieldContract,
    ValidationResult,
)

def _contract() -> DataContract:
    return DataContract(
        name="people",
        fields=[
            FieldContract("id", "int", unique=True),
            FieldContract("age", "int", min=0, max=120),
            FieldContract("status", "str", allowed=["active", "inactive"]),
            FieldContract("email", "str", regex=r"[^@]+@[^@]+\.[^@]+"),
            FieldContract("note", "str", required=False, nullable=True),
        ],
        primary_key=["id"],
    )

def test_conforming_frame_passes():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "age": [30, 45, 22],
            "status": ["active", "inactive", "active"],
            "email": ["a@x.com", "b@y.org", "c@z.net"],
            "note": [None, "hi", None],
        }
    )
    result = _contract().validate(df)
    assert isinstance(result, ValidationResult)
    assert result.passed
    assert result.violations == []
    assert result.rows_checked == 3

def test_missing_required_field():
    df = pd.DataFrame({"id": [1], "age": [10], "status": ["active"], "email": ["a@x.com"]})
    df = df.drop(columns=["age"])
    result = _contract().validate(df)
    rules = {(v.field, v.rule) for v in result.violations}
    assert ("age", "required") in rules
    assert not result.passed

def test_null_policy_violation():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "age": [30, None],
            "status": ["active", "active"],
            "email": ["a@x.com", "b@y.com"],
        }
    )
    result = _contract().validate(df)
    nulls = [v for v in result.violations if v.rule == "nullable" and v.field == "age"]
    assert len(nulls) == 1
    assert nulls[0].count == 1

def test_dtype_violation():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "age": ["thirty", "forty"],
            "status": ["active", "active"],
            "email": ["a@x.com", "b@y.com"],
        }
    )
    result = _contract().validate(df)
    dtypes = [v for v in result.violations if v.rule == "dtype" and v.field == "age"]
    assert len(dtypes) == 1
    assert dtypes[0].count == 2

def test_min_max_violations():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "age": [-5, 200, 999],
            "status": ["active", "active", "active"],
            "email": ["a@x.com", "b@y.com", "c@z.com"],
        }
    )
    result = _contract().validate(df)
    below = [v for v in result.violations if v.rule == "min"]
    above = [v for v in result.violations if v.rule == "max"]
    assert below and below[0].count == 1
    assert above and above[0].count == 2

def test_allowed_violation():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "age": [30, 40],
            "status": ["active", "bogus"],
            "email": ["a@x.com", "b@y.com"],
        }
    )
    result = _contract().validate(df)
    allowed = [v for v in result.violations if v.rule == "allowed"]
    assert allowed and allowed[0].count == 1

def test_regex_violation():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "age": [30, 40],
            "status": ["active", "active"],
            "email": ["not-an-email", "b@y.com"],
        }
    )
    result = _contract().validate(df)
    rx = [v for v in result.violations if v.rule == "regex"]
    assert rx and rx[0].count == 1

def test_unique_and_primary_key_violation():
    df = pd.DataFrame(
        {
            "id": [1, 1, 2],
            "age": [30, 40, 50],
            "status": ["active", "active", "active"],
            "email": ["a@x.com", "b@y.com", "c@z.com"],
        }
    )
    result = _contract().validate(df)
    uniq = [v for v in result.violations if v.rule == "unique" and v.field == "id"]
    pk = [v for v in result.violations if v.rule == "primary_key"]
    assert uniq and uniq[0].count == 2
    assert pk and pk[0].count == 2

def test_yaml_round_trip(tmp_path):
    contract = _contract()
    path = tmp_path / "contract.yaml"
    contract.to_yaml(path)
    loaded = DataContract.from_yaml(path)
    assert loaded.to_dict() == contract.to_dict()
    assert loaded.name == "people"
    assert loaded.primary_key == ["id"]
    assert isinstance(loaded.fields[0], FieldContract)
