"""Tests for core.utils module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from socrata_toolkit.core.utils import (
    BOROUGH_LIST,
    BOROUGH_SET,
    SocrataToolkitError,
    coerce_datetime_column,
    coerce_datetime_columns,
    coerce_series_datetime,
    normalize_borough,
    normalize_formats,
    with_retries,
)


class TestSocrataToolkitError:
    """Tests for SocrataToolkitError exception class."""

    def test_error_creation(self):
        error = SocrataToolkitError("Test error message")
        assert isinstance(error, Exception)
        assert str(error) == "Test error message"


class TestWithRetries:
    """Tests for with_retries function."""

    def test_with_retries_success_first_attempt(self):
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status.return_value = None

        fn = MagicMock(return_value=mock_response)

        result = with_retries(fn)
        assert result == mock_response
        fn.assert_called_once()

    def test_with_retries_success_after_failure(self):
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status.return_value = None

        call_count = {"count": 0}

        def fn_impl():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise requests.RequestException("Connection failed")
            return mock_response

        fn = MagicMock(side_effect=fn_impl)

        with patch("time.sleep"):  # Don't actually sleep in tests
            result = with_retries(fn, retries=2)

        assert result == mock_response
        assert fn.call_count == 2

    def test_with_retries_all_failures(self):
        fn = MagicMock(side_effect=requests.RequestException("Failed"))

        with patch("time.sleep"):  # Don't actually sleep
            with pytest.raises(SocrataToolkitError, match="after 3 retries"):
                with_retries(fn, retries=3)

    def test_with_retries_custom_retries(self):
        fn = MagicMock(side_effect=requests.RequestException("Failed"))

        with patch("time.sleep"):
            with pytest.raises(SocrataToolkitError):
                with_retries(fn, retries=5)

        assert fn.call_count == 5

    def test_with_retries_backoff_increases_delay(self):
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status.return_value = None

        call_count = {"count": 0}

        def fn_impl():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise requests.RequestException("Failed")
            return mock_response

        fn = MagicMock(side_effect=fn_impl)

        with patch("time.sleep") as mock_sleep:
            result = with_retries(fn, retries=3, backoff=2.0)

        assert result == mock_response
        # Check that sleep was called with increasing delays (1.0, 2.0, ...)
        assert mock_sleep.call_count == 2
        first_delay = mock_sleep.call_args_list[0][0][0]
        second_delay = mock_sleep.call_args_list[1][0][0]
        assert second_delay > first_delay

    def test_with_retries_http_error(self):
        mock_response = MagicMock(spec=requests.Response)
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        fn = MagicMock(return_value=mock_response)

        with patch("time.sleep"):
            with pytest.raises(SocrataToolkitError):
                with_retries(fn, retries=2)


class TestNormalizeFormats:
    """Tests for normalize_formats function."""

    def test_normalize_formats_basic(self):
        result = normalize_formats(["JSON", "CSV", "XLSX"])
        assert result == ["json", "csv", "xlsx"]

    def test_normalize_formats_with_spaces(self):
        result = normalize_formats(["  JSON  ", "CSV ", " XLSX"])
        assert result == ["json", "csv", "xlsx"]

    def test_normalize_formats_empty_strings(self):
        result = normalize_formats(["", "JSON", "", "CSV"])
        assert result == ["json", "csv"]

    def test_normalize_formats_none_filtered(self):
        result = normalize_formats(["JSON", None, "CSV"])
        # None will cause AttributeError in the list comp - but the function filters falsy values
        # Actually, looking at the code: [v.strip().lower() for v in values if v and v.strip()]
        # This filters out None, empty strings, and whitespace-only strings
        assert result == ["json", "csv"]

    def test_normalize_formats_mixed_case(self):
        result = normalize_formats(["Json", "CsV", "XlSx"])
        assert result == ["json", "csv", "xlsx"]

    def test_normalize_formats_empty_list(self):
        result = normalize_formats([])
        assert result == []

    def test_normalize_formats_whitespace_only(self):
        result = normalize_formats(["   ", "\t", "\n"])
        assert result == []


class TestCoerceDatetimeColumn:
    """Tests for coerce_datetime_column function."""

    def test_coerce_datetime_column_valid(self):
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "value": [1, 2, 3],
            }
        )
        result = coerce_datetime_column(df, "date")
        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert len(result) == 3

    def test_coerce_datetime_column_with_invalid(self):
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "invalid", "2024-01-03"],
                "value": [1, 2, 3],
            }
        )
        result = coerce_datetime_column(df, "date")
        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert pd.isna(result.loc[1, "date"])

    def test_coerce_datetime_column_missing_column(self):
        df = pd.DataFrame({"value": [1, 2, 3]})
        result = coerce_datetime_column(df, "nonexistent")
        # Column doesn't exist, should return unchanged
        assert result.equals(df)

    def test_coerce_datetime_column_preserves_other_columns(self):
        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02"],
                "value": [1, 2],
            }
        )
        result = coerce_datetime_column(df, "date")
        assert "value" in result.columns
        assert result["value"].tolist() == [1, 2]

    def test_coerce_datetime_column_does_not_modify_original(self):
        df = pd.DataFrame({"date": ["2024-01-01"]})
        result = coerce_datetime_column(df, "date")
        assert not pd.api.types.is_datetime64_any_dtype(df["date"])
        assert pd.api.types.is_datetime64_any_dtype(result["date"])


class TestCoerceDatetimeColumns:
    """Tests for coerce_datetime_columns function."""

    def test_coerce_datetime_columns_multiple(self):
        df = pd.DataFrame(
            {
                "created": ["2024-01-01", "2024-01-02"],
                "updated": ["2024-02-01", "2024-02-02"],
                "value": [1, 2],
            }
        )
        result = coerce_datetime_columns(df, ["created", "updated"])
        assert pd.api.types.is_datetime64_any_dtype(result["created"])
        assert pd.api.types.is_datetime64_any_dtype(result["updated"])
        assert result["value"].dtype == df["value"].dtype

    def test_coerce_datetime_columns_missing_some(self):
        df = pd.DataFrame(
            {
                "created": ["2024-01-01"],
                "value": [1],
            }
        )
        result = coerce_datetime_columns(df, ["created", "nonexistent"])
        assert pd.api.types.is_datetime64_any_dtype(result["created"])

    def test_coerce_datetime_columns_empty_list(self):
        df = pd.DataFrame({"created": ["2024-01-01"]})
        result = coerce_datetime_columns(df, [])
        assert result.equals(df)


class TestCoerceSeriesDatetime:
    """Tests for coerce_series_datetime function."""

    def test_coerce_series_datetime_valid(self):
        series = pd.Series(["2024-01-01", "2024-01-02", "2024-01-03"])
        result = coerce_series_datetime(series)
        assert pd.api.types.is_datetime64_any_dtype(result)

    def test_coerce_series_datetime_with_invalid(self):
        series = pd.Series(["2024-01-01", "invalid", "2024-01-03"])
        result = coerce_series_datetime(series)
        assert pd.api.types.is_datetime64_any_dtype(result)
        assert pd.isna(result.iloc[1])

    def test_coerce_series_datetime_numeric(self):
        series = pd.Series([1704067200, 1704153600, 1704240000])  # Unix timestamps
        result = coerce_series_datetime(series)
        assert pd.api.types.is_datetime64_any_dtype(result)


class TestBoroughConstants:
    """Tests for borough-related constants."""

    def test_borough_list(self):
        assert BOROUGH_LIST == ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

    def test_borough_set(self):
        assert BOROUGH_SET == frozenset(
            ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
        )

    def test_borough_set_membership(self):
        assert "Manhattan" in BOROUGH_SET
        assert "Brooklyn" in BOROUGH_SET
        assert "InvalidBorough" not in BOROUGH_SET


class TestNormalizeBorough:
    """Tests for normalize_borough function."""

    def test_normalize_borough_numeric_codes(self):
        assert normalize_borough("1") == "Manhattan"
        assert normalize_borough("2") == "Bronx"
        assert normalize_borough("3") == "Brooklyn"
        assert normalize_borough("4") == "Queens"
        assert normalize_borough("5") == "Staten Island"

    def test_normalize_borough_abbreviations(self):
        assert normalize_borough("MN") == "Manhattan"
        assert normalize_borough("BX") == "Bronx"
        assert normalize_borough("BK") == "Brooklyn"
        assert normalize_borough("QN") == "Queens"
        assert normalize_borough("SI") == "Staten Island"

    def test_normalize_borough_alternate_names(self):
        assert normalize_borough("NEW YORK") == "Manhattan"
        assert normalize_borough("KINGS") == "Brooklyn"
        assert normalize_borough("RICHMOND") == "Staten Island"
        assert normalize_borough("THE BRONX") == "Bronx"

    def test_normalize_borough_uppercase_canonical(self):
        assert normalize_borough("MANHATTAN") == "Manhattan"
        assert normalize_borough("BRONX") == "Bronx"
        assert normalize_borough("BROOKLYN") == "Brooklyn"
        assert normalize_borough("QUEENS") == "Queens"
        assert normalize_borough("STATEN ISLAND") == "Staten Island"

    def test_normalize_borough_lowercase_canonical(self):
        assert normalize_borough("manhattan") == "Manhattan"
        assert normalize_borough("bronx") == "Bronx"
        assert normalize_borough("brooklyn") == "Brooklyn"

    def test_normalize_borough_mixed_case(self):
        assert normalize_borough("ManHattan") == "Manhattan"
        assert normalize_borough("bRoNx") == "Bronx"

    def test_normalize_borough_with_whitespace(self):
        assert normalize_borough("  MN  ") == "Manhattan"
        assert normalize_borough("\tBX\n") == "Bronx"

    def test_normalize_borough_invalid(self):
        assert normalize_borough("invalid") == "Unknown"
        assert normalize_borough("XYZ") == "Unknown"
        assert normalize_borough("") == "Unknown"

    def test_normalize_borough_preserves_canonical_form(self):
        # Verify that canonical forms are consistent
        assert normalize_borough("Manhattan") == "Manhattan"
        assert normalize_borough("mn") == "Manhattan"
        assert normalize_borough("1") == "Manhattan"
