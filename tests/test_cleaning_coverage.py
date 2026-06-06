"""Tests for socrata_toolkit.cleaning module."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from socrata_toolkit.cleaning import (
    clean_column_names,
    infer_and_convert_types,
    remove_outliers,
    standardize_bbl,
    standardize_boroughs,
    standardize_postcodes,
)

# ---------------------------------------------------------------------------
# standardize_boroughs
# ---------------------------------------------------------------------------

class TestStandardizeBoroughs:
    """Tests for standardize_boroughs."""

    def _df(self, values: list[str]) -> pd.DataFrame:
        return pd.DataFrame({"boro": values})

    def test_numeric_codes_mapped(self):
        """Numeric codes 1-5 map to canonical borough names."""
        df = self._df(["1", "2", "3", "4", "5"])
        out = standardize_boroughs(df, "boro")
        assert out["boro"].tolist() == [
            "MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"
        ]

    def test_abbreviation_codes_mapped(self):
        """Two-letter abbreviations are normalised."""
        df = self._df(["MN", "BX", "BK", "QN", "SI"])
        out = standardize_boroughs(df, "boro")
        assert out["boro"].tolist() == [
            "MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"
        ]

    def test_alternate_names_mapped(self):
        """Alternate names (NEW YORK, KINGS, RICHMOND) are normalised."""
        df = self._df(["NEW YORK", "KINGS", "RICHMOND"])
        out = standardize_boroughs(df, "boro")
        assert out["boro"].tolist() == ["MANHATTAN", "BROOKLYN", "STATEN ISLAND"]

    def test_lowercase_input_normalised(self):
        """Input is uppercased before mapping."""
        df = self._df(["mn", "bk"])
        out = standardize_boroughs(df, "boro")
        assert out["boro"].tolist() == ["MANHATTAN", "BROOKLYN"]

    def test_unknown_values_become_unknown(self):
        """Values not in the mapping become 'UNKNOWN'."""
        df = self._df(["XYZ", "99"])
        out = standardize_boroughs(df, "boro")
        assert all(v == "UNKNOWN" for v in out["boro"])

    def test_missing_column_leaves_df_unchanged(self):
        """When the column does not exist the DataFrame is returned as-is."""
        df = pd.DataFrame({"other": ["a", "b"]})
        out = standardize_boroughs(df, "nonexistent")
        assert list(out.columns) == ["other"]

    def test_does_not_modify_original(self):
        """Original DataFrame is not mutated."""
        df = self._df(["MN"])
        _ = standardize_boroughs(df, "boro")
        assert df["boro"].iloc[0] == "MN"

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped before mapping."""
        df = self._df(["  MN  ", " BX "])
        out = standardize_boroughs(df, "boro")
        assert out["boro"].tolist() == ["MANHATTAN", "BRONX"]


# ---------------------------------------------------------------------------
# standardize_postcodes
# ---------------------------------------------------------------------------

class TestStandardizePostcodes:
    """Tests for standardize_postcodes."""

    def _df(self, values: list) -> pd.DataFrame:
        return pd.DataFrame({"zip": values})

    def test_five_digit_string_preserved(self):
        """Already valid 5-digit postcodes are unchanged."""
        df = self._df(["10001", "11201", "10451"])
        out = standardize_postcodes(df, "zip")
        assert out["zip"].tolist() == ["10001", "11201", "10451"]

    def test_nine_digit_code_truncated(self):
        """ZIP+4 strings are truncated to the 5-digit part."""
        df = self._df(["10001-1234"])
        out = standardize_postcodes(df, "zip")
        assert out["zip"].iloc[0] == "10001"

    def test_non_numeric_becomes_empty(self):
        """Non-numeric values that contain no 5-digit run become empty string."""
        df = self._df(["ABCDE", ""])
        out = standardize_postcodes(df, "zip")
        assert out["zip"].iloc[0] == ""

    def test_missing_column_leaves_df_unchanged(self):
        """When column absent the DataFrame is returned as-is."""
        df = pd.DataFrame({"other": [1, 2]})
        out = standardize_postcodes(df, "zip")
        assert list(out.columns) == ["other"]

    def test_does_not_modify_original(self):
        """Original DataFrame is not mutated."""
        df = self._df(["10001-9999"])
        _ = standardize_postcodes(df, "zip")
        assert df["zip"].iloc[0] == "10001-9999"


# ---------------------------------------------------------------------------
# standardize_bbl
# ---------------------------------------------------------------------------

class TestStandardizeBBL:
    """Tests for standardize_bbl."""

    def _df(self, boro: str, block: str, lot: str) -> pd.DataFrame:
        return pd.DataFrame({"boro": [boro], "block": [block], "lot": [lot]})

    def test_manhattan_bbl(self):
        """MANHATTAN boro-code is '1'."""
        df = self._df("MANHATTAN", "10", "5")
        out = standardize_bbl(df, "boro", "block", "lot")
        assert out["bbl"].iloc[0] == "1000100005"

    def test_brooklyn_bbl(self):
        """BROOKLYN boro-code is '3'."""
        df = self._df("BROOKLYN", "123", "45")
        out = standardize_bbl(df, "boro", "block", "lot")
        assert out["bbl"].iloc[0] == "3001230045"

    def test_unknown_boro_defaults_zero(self):
        """Unrecognised borough uses '0' as boro digit."""
        df = self._df("UNKNOWN_PLACE", "1", "1")
        out = standardize_bbl(df, "boro", "block", "lot")
        # boro_map.get returns "0" for unknown
        assert out["bbl"].iloc[0].startswith("0")

    def test_missing_column_no_target_column(self):
        """When required columns are absent, target column is not added."""
        df = pd.DataFrame({"a": [1]})
        out = standardize_bbl(df, "boro", "block", "lot")
        assert "bbl" not in out.columns

    def test_custom_target_column(self):
        """Target column name can be customised."""
        df = self._df("BRONX", "50", "10")
        out = standardize_bbl(df, "boro", "block", "lot", target_col="my_bbl")
        assert "my_bbl" in out.columns

    def test_does_not_modify_original(self):
        """Original DataFrame is not mutated."""
        df = self._df("QUEENS", "1", "1")
        _ = standardize_bbl(df, "boro", "block", "lot")
        assert "bbl" not in df.columns


# ---------------------------------------------------------------------------
# clean_column_names
# ---------------------------------------------------------------------------

class TestCleanColumnNames:
    """Tests for clean_column_names."""

    def test_spaces_become_underscores(self):
        """Spaces in column names are replaced with underscores."""
        df = pd.DataFrame(columns=["First Name", "Last Name"])
        out = clean_column_names(df)
        assert "first_name" in out.columns
        assert "last_name" in out.columns

    def test_uppercase_lowercased(self):
        """Column names are lowercased."""
        df = pd.DataFrame(columns=["Borough", "COUNT"])
        out = clean_column_names(df)
        assert "borough" in out.columns
        assert "count" in out.columns

    def test_hyphens_become_underscores(self):
        """Hyphens are replaced with underscores."""
        df = pd.DataFrame(columns=["created-date", "updated-at"])
        out = clean_column_names(df)
        assert "created_date" in out.columns
        assert "updated_at" in out.columns

    def test_special_chars_removed(self):
        """Non-alphanumeric characters (except underscore) are stripped."""
        df = pd.DataFrame(columns=["col!@#$%"])
        out = clean_column_names(df)
        assert "col" in out.columns

    def test_already_clean_unchanged(self):
        """Already clean snake_case names are not altered."""
        df = pd.DataFrame(columns=["borough", "violation_count"])
        out = clean_column_names(df)
        assert "borough" in out.columns
        assert "violation_count" in out.columns

    def test_does_not_modify_original(self):
        """Original DataFrame is not mutated."""
        df = pd.DataFrame(columns=["First Name"])
        _ = clean_column_names(df)
        assert "First Name" in df.columns


# ---------------------------------------------------------------------------
# infer_and_convert_types
# ---------------------------------------------------------------------------

class TestInferAndConvertTypes:
    """Tests for infer_and_convert_types."""

    def test_numeric_strings_converted(self):
        """String columns that are purely numeric become numeric dtype."""
        df = pd.DataFrame({"count": ["1", "2", "3"]})
        out = infer_and_convert_types(df)
        assert pd.api.types.is_numeric_dtype(out["count"])

    def test_date_column_converted(self):
        """Column with 'date' in its name and ISO strings becomes datetime."""
        df = pd.DataFrame({"created_date": ["2024-01-01", "2024-02-15"]})
        out = infer_and_convert_types(df)
        assert pd.api.types.is_datetime64_any_dtype(out["created_date"])

    def test_non_convertible_stays_object(self):
        """Mixed/non-parseable column remains as object dtype."""
        df = pd.DataFrame({"description": ["hello", "world"]})
        out = infer_and_convert_types(df)
        assert out["description"].dtype == object

    def test_already_numeric_unchanged(self):
        """Columns already numeric are left untouched."""
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
        out = infer_and_convert_types(df)
        assert pd.api.types.is_numeric_dtype(out["value"])

    def test_does_not_modify_original(self):
        """Original DataFrame is not mutated."""
        df = pd.DataFrame({"count": ["1", "2"]})
        _ = infer_and_convert_types(df)
        assert df["count"].dtype == object


# ---------------------------------------------------------------------------
# remove_outliers
# ---------------------------------------------------------------------------

class TestRemoveOutliers:
    """Tests for remove_outliers."""

    def test_removes_high_outliers(self):
        """Rows with z-score above threshold are removed."""
        values = list(range(1, 21)) + [1000]  # 1000 is a clear outlier
        df = pd.DataFrame({"val": values})
        out = remove_outliers(df, "val", z_threshold=3)
        assert 1000 not in out["val"].values

    def test_keeps_inliers(self):
        """Non-outlier rows are retained."""
        df = pd.DataFrame({"val": [10, 11, 12, 13, 14, 15]})
        out = remove_outliers(df, "val")
        assert len(out) == len(df)

    def test_non_numeric_column_unchanged(self):
        """Non-numeric column causes no removal."""
        df = pd.DataFrame({"name": ["a", "b", "c"]})
        out = remove_outliers(df, "name")
        assert len(out) == 3

    def test_missing_column_unchanged(self):
        """Missing column name returns df unchanged."""
        df = pd.DataFrame({"val": [1, 2, 3]})
        out = remove_outliers(df, "nonexistent")
        assert len(out) == 3

    def test_custom_threshold(self):
        """Custom z_threshold can be set (e.g. 2 removes moderate deviations)."""
        import numpy as np

        rng = np.random.default_rng(42)
        base = list(rng.normal(0, 1, 100))
        extremes = [50.0, -50.0]
        df = pd.DataFrame({"val": base + extremes})
        out = remove_outliers(df, "val", z_threshold=2)
        assert 50.0 not in out["val"].values

    def test_does_not_modify_original(self):
        """Original DataFrame is not mutated."""
        values = list(range(10)) + [9999]
        df = pd.DataFrame({"val": values})
        _ = remove_outliers(df, "val")
        assert len(df) == 11
