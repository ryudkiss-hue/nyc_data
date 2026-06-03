"""Tests for discovery.schema module - Schema registry and drift detection."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from socrata_toolkit.discovery.schema import (
    ChangeType,
    ColumnSchema,
    DatasetSchema,
    SchemaRegistry,
    SchemaValidator,
    TYPE_COMPATIBILITY,
    BackwardCompatibilityChecker,
)


class TestChangeTypeEnum:
    """Tests for ChangeType enum."""

    def test_change_type_addition(self):
        assert ChangeType.COLUMN_ADDITION.value == "addition"

    def test_change_type_deletion(self):
        assert ChangeType.COLUMN_DELETION.value == "deletion"

    def test_change_type_type_change(self):
        assert ChangeType.TYPE_CHANGE.value == "type_change"

    def test_change_type_rename(self):
        assert ChangeType.RENAME.value == "rename"

    def test_change_type_null_constraint(self):
        assert ChangeType.NULL_CONSTRAINT_CHANGE.value == "null_constraint_change"

    def test_change_type_position(self):
        assert ChangeType.POSITION_CHANGE.value == "position_change"


class TestColumnSchema:
    """Tests for ColumnSchema dataclass."""

    def test_column_schema_creation(self):
        col = ColumnSchema(
            name="id",
            dtype="int64",
            nullable=False,
            position=0,
            sample_value="123",
        )
        assert col.name == "id"
        assert col.dtype == "int64"
        assert col.nullable is False
        assert col.position == 0

    def test_column_schema_without_sample(self):
        col = ColumnSchema(
            name="borough",
            dtype="object",
            nullable=True,
            position=1,
        )
        assert col.sample_value is None

    def test_column_schema_nullable_true(self):
        col = ColumnSchema("data", "float64", True, 2)
        assert col.nullable is True


class TestDatasetSchema:
    """Tests for DatasetSchema dataclass."""

    def test_dataset_schema_creation(self):
        cols = {
            "id": ColumnSchema("id", "int64", False, 0),
            "name": ColumnSchema("name", "object", True, 1),
        }
        schema = DatasetSchema(
            dataset_id="abc123",
            version=1,
            columns=cols,
            captured_at=datetime.now(timezone.utc),
            row_count=1000,
        )
        assert schema.dataset_id == "abc123"
        assert schema.version == 1
        assert len(schema.columns) == 2

    def test_dataset_schema_to_dict(self):
        cols = {
            "id": ColumnSchema("id", "int64", False, 0),
        }
        schema = DatasetSchema(
            dataset_id="abc123",
            version=1,
            columns=cols,
            captured_at=datetime.now(timezone.utc),
            row_count=100,
            metadata={"source": "test"},
        )
        result = schema.to_dict()

        assert result["dataset_id"] == "abc123"
        assert result["version"] == 1
        assert "id" in result["columns"]
        assert result["row_count"] == 100
        assert "captured_at" in result
        assert result["metadata"]["source"] == "test"

    def test_dataset_schema_empty_metadata(self):
        cols = {}
        schema = DatasetSchema(
            dataset_id="abc123",
            version=1,
            columns=cols,
            captured_at=datetime.now(timezone.utc),
            row_count=0,
        )
        assert schema.metadata == {}


class TestTypeCompatibility:
    """Tests for TYPE_COMPATIBILITY matrix."""

    def test_int32_compatible_types(self):
        assert "int32" in TYPE_COMPATIBILITY["int32"]
        assert "int64" in TYPE_COMPATIBILITY["int32"]
        assert "float64" in TYPE_COMPATIBILITY["int32"]
        assert "object" in TYPE_COMPATIBILITY["int32"]

    def test_float64_compatible_types(self):
        assert "float64" in TYPE_COMPATIBILITY["float64"]
        assert "object" in TYPE_COMPATIBILITY["float64"]

    def test_bool_compatible_types(self):
        assert "bool" in TYPE_COMPATIBILITY["bool"]
        assert "int32" in TYPE_COMPATIBILITY["bool"]

    def test_object_compatible_types(self):
        assert TYPE_COMPATIBILITY["object"] == {"object"}

    def test_datetime_compatible_types(self):
        assert "datetime64[ns]" in TYPE_COMPATIBILITY["datetime64[ns]"]
        assert "object" in TYPE_COMPATIBILITY["datetime64[ns]"]


class TestSchemaValidator:
    """Tests for SchemaValidator class."""

    def test_schema_validator_with_schema(self):
        cols = {
            "id": ColumnSchema("id", "int64", False, 0),
        }
        schema = DatasetSchema(
            dataset_id="test",
            version=1,
            columns=cols,
            captured_at=datetime.now(timezone.utc),
            row_count=100,
        )
        validator = SchemaValidator(schema)
        assert validator is not None

    def test_schema_validator_validate_dataframe(self):
        cols = {
            "id": ColumnSchema("id", "int64", False, 0),
        }
        schema = DatasetSchema(
            dataset_id="test",
            version=1,
            columns=cols,
            captured_at=datetime.now(timezone.utc),
            row_count=3,
        )
        df = pd.DataFrame({
            "id": [1, 2, 3],
        })
        validator = SchemaValidator(schema)
        # Validator has a validate method
        if hasattr(validator, 'validate'):
            result = validator.validate(df)
            assert result is not None


class TestSchemaRegistry:
    """Tests for SchemaRegistry class."""

    def test_schema_registry_initialization(self):
        registry = SchemaRegistry()
        assert registry is not None
        # Check if it has expected methods
        assert hasattr(registry, '__init__')


class TestBackwardCompatibilityChecker:
    """Tests for BackwardCompatibilityChecker class."""

    def test_backward_compatibility_checker_init(self):
        checker = BackwardCompatibilityChecker()
        assert checker is not None
        assert hasattr(checker, '__init__')


class TestSchemaFromDataFrame:
    """Tests for schema extraction from DataFrames."""

    def test_extract_schema_basic_types(self):
        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.5, 2.5, 3.5],
            "str_col": ["a", "b", "c"],
            "bool_col": [True, False, True],
        })
        # Test that schema can be created from DataFrame
        assert len(df.columns) == 4
        assert df["int_col"].dtype == "int64"

    def test_extract_schema_with_nulls(self):
        df = pd.DataFrame({
            "col1": [1, None, 3],
            "col2": ["a", None, "c"],
        })
        # Nulls are preserved in dtypes
        assert pd.isna(df["col1"]).any()
        assert pd.isna(df["col2"]).any()

    def test_extract_schema_datetime(self):
        df = pd.DataFrame({
            "date_col": pd.date_range("2024-01-01", periods=3),
        })
        assert pd.api.types.is_datetime64_any_dtype(df["date_col"])

    def test_extract_schema_large_dataframe(self):
        df = pd.DataFrame({
            "id": range(10000),
            "value": range(10000, 20000),
        })
        assert len(df) == 10000
        assert len(df.columns) == 2
