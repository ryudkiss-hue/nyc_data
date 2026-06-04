"""Tests for quality.profiler module - Data profiling and schema analysis."""
from __future__ import annotations

import pandas as pd

from socrata_toolkit.quality.profiler import (
    ColumnProfile,
    DataProfiler,
    DataType,
    DriftReport,
    ProfileGenerator,
    TableProfile,
    generate_profile_report,
)


class TestDataType:
    """Tests for DataType enum."""

    def test_datatype_numeric(self):
        """Test DataType.NUMERIC value."""
        assert DataType.NUMERIC.value == "numeric"

    def test_datatype_string(self):
        """Test DataType.STRING value."""
        assert DataType.STRING.value == "string"

    def test_datatype_boolean(self):
        """Test DataType.BOOLEAN value."""
        assert DataType.BOOLEAN.value == "boolean"

    def test_datatype_datetime(self):
        """Test DataType.DATETIME value."""
        assert DataType.DATETIME.value == "datetime"

    def test_datatype_unknown(self):
        """Test DataType.UNKNOWN value."""
        assert DataType.UNKNOWN.value == "unknown"

    def test_datatype_comparison(self):
        """Test DataType enum comparison."""
        assert DataType.NUMERIC != DataType.STRING


class TestColumnProfile:
    """Tests for ColumnProfile dataclass."""

    def test_column_profile_creation(self):
        """Test creating a ColumnProfile."""
        prof = ColumnProfile(data_type=DataType.NUMERIC, min_value=0, max_value=100, cardinality=50)
        assert prof.data_type == DataType.NUMERIC
        assert prof.min_value == 0
        assert prof.max_value == 100
        assert prof.cardinality == 50

    def test_column_profile_defaults(self):
        """Test ColumnProfile with default values."""
        prof = ColumnProfile(data_type=DataType.STRING)
        assert prof.data_type == DataType.STRING
        assert prof.min_value is None
        assert prof.max_value is None
        assert prof.cardinality == 0


class TestTableProfile:
    """Tests for TableProfile dataclass."""

    def test_table_profile_creation(self):
        """Test creating a TableProfile."""
        col_profs = {
            "col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=10),
            "col2": ColumnProfile(data_type=DataType.STRING, cardinality=5),
        }
        prof = TableProfile(table_name="test_table", row_count=100, column_count=2, column_profiles=col_profs)
        assert prof.table_name == "test_table"
        assert prof.row_count == 100
        assert prof.column_count == 2
        assert len(prof.column_profiles) == 2

    def test_table_profile_to_dict(self):
        """Test serializing TableProfile to dict."""
        col_profs = {
            "id": ColumnProfile(data_type=DataType.NUMERIC, min_value=1, max_value=100, cardinality=100),
            "name": ColumnProfile(data_type=DataType.STRING, cardinality=50),
        }
        prof = TableProfile(table_name="users", row_count=100, column_count=2, column_profiles=col_profs)
        result = prof.to_dict()
        assert result["table_name"] == "users"
        assert result["row_count"] == 100
        assert result["column_count"] == 2
        assert "column_profiles" in result
        assert result["column_profiles"]["id"]["data_type"] == "numeric"
        assert result["column_profiles"]["name"]["data_type"] == "string"

    def test_table_profile_to_dict_with_datetime(self):
        """Test TableProfile serialization with datetime column."""
        col_profs = {
            "created_at": ColumnProfile(
                data_type=DataType.DATETIME,
                min_value="2023-01-01T00:00:00",
                max_value="2023-12-31T23:59:59",
                cardinality=365,
            ),
        }
        prof = TableProfile(table_name="events", row_count=1000, column_count=1, column_profiles=col_profs)
        result = prof.to_dict()
        assert result["column_profiles"]["created_at"]["data_type"] == "datetime"


class TestDriftReport:
    """Tests for DriftReport dataclass."""

    def test_drift_report_no_drift(self):
        """Test DriftReport with no drift."""
        report = DriftReport(is_drifted=False, drift_details={})
        assert report.is_drifted is False
        assert report.drift_details == {}

    def test_drift_report_with_drift(self):
        """Test DriftReport with drift detected."""
        details = {"column_removed": ["col1"], "column_added": ["col2"]}
        report = DriftReport(is_drifted=True, drift_details=details)
        assert report.is_drifted is True
        assert report.drift_details == details

    def test_drift_report_defaults(self):
        """Test DriftReport with default values."""
        report = DriftReport()
        assert report.is_drifted is False
        assert report.drift_details == {}


class TestProfileGenerator:
    """Tests for ProfileGenerator class."""

    def test_profile_generator_initialization(self):
        """Test ProfileGenerator initialization."""
        gen = ProfileGenerator(sample_size=500)
        assert gen.sample_size == 500

    def test_profile_generator_default_sample_size(self):
        """Test ProfileGenerator with default sample size."""
        gen = ProfileGenerator()
        assert gen.sample_size == 1000

    def test_profile_dataset_small_dataframe(self):
        """Test profiling a small DataFrame."""
        gen = ProfileGenerator()
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "score": [85.5, 90.0, 78.5],
        })
        profile = gen.profile_dataset(df, table_name="test_data")
        assert profile.table_name == "test_data"
        assert profile.row_count == 3
        assert profile.column_count == 3
        assert "id" in profile.column_profiles
        assert "name" in profile.column_profiles
        assert "score" in profile.column_profiles

    def test_profile_dataset_large_dataframe(self):
        """Test profiling a large DataFrame (tests sampling)."""
        gen = ProfileGenerator(sample_size=100)
        df = pd.DataFrame({
            "x": range(1000),
            "y": [i * 2 for i in range(1000)],
        })
        profile = gen.profile_dataset(df)
        assert profile.row_count == 1000  # Original size
        assert profile.column_count == 2

    def test_profile_column_numeric(self):
        """Test profiling a numeric column."""
        gen = ProfileGenerator()
        series = pd.Series([1, 2, 3, 4, 5])
        result = gen._profile_column(series, "numbers")
        assert result.data_type == DataType.NUMERIC
        assert result.min_value == 1.0
        assert result.max_value == 5.0
        assert result.cardinality == 5

    def test_profile_column_string(self):
        """Test profiling a string column."""
        gen = ProfileGenerator()
        series = pd.Series(["a", "b", "a", "c"])
        result = gen._profile_column(series, "letters")
        assert result.data_type == DataType.STRING
        assert result.cardinality == 3  # a, b, c

    def test_profile_column_boolean(self):
        """Test profiling a boolean column (classified as numeric due to check order)."""
        gen = ProfileGenerator()
        series = pd.Series([True, False, True, True], dtype="bool")
        result = gen._profile_column(series, "flags")
        # Boolean is classified as numeric because is_numeric_dtype check comes first
        assert result.data_type == DataType.NUMERIC
        assert result.cardinality == 2

    def test_profile_column_datetime(self):
        """Test profiling a datetime column."""
        gen = ProfileGenerator()
        series = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"])
        result = gen._profile_column(series, "dates")
        assert result.data_type == DataType.DATETIME
        assert result.min_value is not None
        assert result.max_value is not None
        assert result.cardinality == 3

    def test_profile_column_with_nulls(self):
        """Test profiling a column with null values."""
        gen = ProfileGenerator()
        series = pd.Series([1, 2, None, 4, 5])
        result = gen._profile_column(series, "values")
        assert result.data_type == DataType.NUMERIC
        assert result.cardinality == 4  # Excludes NaN

    def test_profile_column_all_nulls(self):
        """Test profiling a column with all null values."""
        gen = ProfileGenerator()
        series = pd.Series([None, None, None], dtype=float)
        result = gen._profile_column(series, "empty_col")
        assert result.data_type == DataType.NUMERIC
        assert result.min_value is None
        assert result.max_value is None

    def test_suggest_expectations_basic(self):
        """Test suggesting expectations from a profile."""
        gen = ProfileGenerator()
        col_profs = {
            "id": ColumnProfile(data_type=DataType.NUMERIC, cardinality=100),
            "category": ColumnProfile(data_type=DataType.STRING, cardinality=5),
        }
        profile = TableProfile(table_name="data", row_count=100, column_count=2, column_profiles=col_profs)
        suggestions = gen.suggest_expectations(profile)
        assert len(suggestions) >= 2
        # Should have column_exists for each column
        col_exists = [s for s in suggestions if s["expectation_type"] == "column_exists"]
        assert len(col_exists) == 2

    def test_suggest_expectations_low_cardinality(self):
        """Test suggestion of set membership expectation for low-cardinality strings."""
        gen = ProfileGenerator()
        col_profs = {
            "status": ColumnProfile(data_type=DataType.STRING, cardinality=3),
        }
        profile = TableProfile(table_name="data", row_count=100, column_count=1, column_profiles=col_profs)
        suggestions = gen.suggest_expectations(profile)
        set_expectations = [s for s in suggestions if s["expectation_type"] == "column_values_in_set"]
        assert len(set_expectations) > 0

    def test_compare_profiles(self):
        """Test comparing two profiles."""
        gen = ProfileGenerator()
        col_profs1 = {"col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=10)}
        col_profs2 = {"col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=15)}
        profile1 = TableProfile(table_name="t1", row_count=100, column_count=1, column_profiles=col_profs1)
        profile2 = TableProfile(table_name="t2", row_count=100, column_count=1, column_profiles=col_profs2)
        report = gen.compare_profiles(profile1, profile2)
        assert isinstance(report, DriftReport)

    def test_detect_schema_drift_no_change(self):
        """Test detecting schema drift when no columns changed."""
        gen = ProfileGenerator()
        col_profs = {
            "id": ColumnProfile(data_type=DataType.NUMERIC, cardinality=100),
            "name": ColumnProfile(data_type=DataType.STRING, cardinality=50),
        }
        profile1 = TableProfile(table_name="t1", row_count=100, column_count=2, column_profiles=col_profs)
        profile2 = TableProfile(table_name="t2", row_count=100, column_count=2, column_profiles=col_profs)
        drift = gen.detect_schema_drift(profile1, profile2)
        assert drift["columns_added"] == []
        assert drift["columns_removed"] == []

    def test_detect_schema_drift_columns_added(self):
        """Test detecting added columns."""
        gen = ProfileGenerator()
        col_profs1 = {"col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=10)}
        col_profs2 = {
            "col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=10),
            "col2": ColumnProfile(data_type=DataType.STRING, cardinality=5),
        }
        profile1 = TableProfile(table_name="t1", row_count=100, column_count=1, column_profiles=col_profs1)
        profile2 = TableProfile(table_name="t2", row_count=100, column_count=2, column_profiles=col_profs2)
        drift = gen.detect_schema_drift(profile1, profile2)
        assert "col2" in drift["columns_added"]
        assert drift["columns_removed"] == []

    def test_detect_schema_drift_columns_removed(self):
        """Test detecting removed columns."""
        gen = ProfileGenerator()
        col_profs1 = {
            "col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=10),
            "col2": ColumnProfile(data_type=DataType.STRING, cardinality=5),
        }
        col_profs2 = {"col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=10)}
        profile1 = TableProfile(table_name="t1", row_count=100, column_count=2, column_profiles=col_profs1)
        profile2 = TableProfile(table_name="t2", row_count=100, column_count=1, column_profiles=col_profs2)
        drift = gen.detect_schema_drift(profile1, profile2)
        assert drift["columns_added"] == []
        assert "col2" in drift["columns_removed"]

    def test_generate_summary(self):
        """Test generating summary from profile."""
        gen = ProfileGenerator()
        col_profs = {
            "col1": ColumnProfile(data_type=DataType.NUMERIC, cardinality=10),
            "col2": ColumnProfile(data_type=DataType.STRING, cardinality=5),
        }
        profile = TableProfile(table_name="test", row_count=1000, column_count=2, column_profiles=col_profs)
        summary = gen.generate_summary(profile)
        assert summary["row_count"] == 1000
        assert summary["column_count"] == 2


class TestDataProfilerLegacy:
    """Tests for legacy DataProfiler class."""

    def test_data_profiler_profile_dataset(self):
        """Test legacy DataProfiler.profile_dataset method."""
        profiler = DataProfiler()
        result = profiler.profile_dataset({"key": "value"})
        assert isinstance(result, dict)
        assert result == {}


class TestGenerateProfileReportLegacy:
    """Tests for legacy generate_profile_report function."""

    def test_generate_profile_report(self):
        """Test legacy generate_profile_report function."""
        result = generate_profile_report({"key": "value"})
        assert isinstance(result, str)
        assert result == ""
