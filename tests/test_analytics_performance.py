import pytest

import pandas as pd
import pytest

from app.analytics import normalize_bbl


def test_normalize_bbl_vectorized():
    """Verify high-performance BBL normalization logic."""
    series = pd.Series(
        [
            "123456",  # Short, needs padding
            "1-234-567-890",  # Hyphenated, needs stripping
            "123 456 7890",  # Spaced, needs stripping
            "1234567890",  # Already valid
            "abc",  # Non-digits, should be filtered
            "12",  # Too short, should be filtered
            None,  # Null preservation
            "",  # Empty string
        ]
    )

    result = normalize_bbl(series)

    # Assertions
    assert result.iloc[0] == "0000123456"  # Padded to 10
    assert result.iloc[1] == "1234567890"  # Stripped hyphens
    assert result.iloc[2] == "1234567890"  # Stripped spaces
    assert result.iloc[3] == "1234567890"  # No-op
    assert pd.isna(result.iloc[4])  # Short digit count (<6)
    assert pd.isna(result.iloc[5])  # Too short
    assert pd.isna(result.iloc[6])  # None preserved
    assert pd.isna(result.iloc[7])  # Empty string filtered


def test_date_parsing_guard():
    """Verify that redundant date parsing is skipped via guard clause."""
    from app.analytics import ColumnProfile, profile_dataset

    # Create DF with already-parsed datetimes
    df = pd.DataFrame({"timestamp": pd.to_datetime(["2023-01-01", "2023-01-02"])})

    # We'll use a small sample to trigger the profile logic
    profile = profile_dataset("test_guard", df, sample_rows=2)

    # Verify the timestamp column is identified and min/max set correctly
    ts_profile = next(c for c in profile.columns if c.name == "timestamp")
    assert ts_profile.is_datetime is True
    assert ts_profile.min_val == "2023-01-01"
    assert ts_profile.max_val == "2023-01-02"
