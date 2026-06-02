"""Tests for borough aggregation and completion rates (ramp analysis)."""

import pandas as pd
import pytest

from socrata_toolkit.analyst.ramp_analysis import compute_borough_completion_rates


def _sample_complaints_data():
    """Create sample complaint data with multiple boroughs."""
    return pd.DataFrame(
        {
            "borough": ["MN"] * 100 + ["BK"] * 100 + ["BX"] * 50 + ["QN"] * 50 + ["SI"] * 30,
            "total_complaints": [10] * 330,
            "resolved_complaints": [8] * 100 + [6] * 100 + [7] * 50 + [9] * 50 + [5] * 30,
        }
    )


def test_compute_borough_completion_rates_basic():
    """Test basic borough aggregation and completion rate calculation."""
    df = _sample_complaints_data()
    rates = compute_borough_completion_rates(df)

    # Check that all 5 boroughs are present
    assert "MN" in rates
    assert "BK" in rates
    assert "BX" in rates
    assert "QN" in rates
    assert "SI" in rates

    # Check MN completion rate (100 rows * 8 resolved / 100 rows * 10 total)
    # = 800 / 1000 = 0.8
    assert rates["MN"]["completion_rate"] == 0.8
    assert rates["MN"]["resolved_count"] == 800
    assert rates["MN"]["total_count"] == 1000
    assert rates["MN"]["sample_size"] == 100

    # Check BK completion rate (100 rows * 6 resolved / 100 rows * 10 total)
    # = 600 / 1000 = 0.6
    assert rates["BK"]["completion_rate"] == 0.6
    assert rates["BK"]["resolved_count"] == 600
    assert rates["BK"]["total_count"] == 1000
    assert rates["BK"]["sample_size"] == 100


def test_compute_borough_completion_rates_confidence_interval():
    """Test that confidence intervals are computed correctly."""
    df = _sample_complaints_data()
    rates = compute_borough_completion_rates(df)

    # For each borough, CI bounds should be valid
    for borough in ["MN", "BK", "BX", "QN", "SI"]:
        data = rates[borough]
        # CI bounds should be between 0 and 1
        assert 0 <= data["ci_lower"] <= 1
        assert 0 <= data["ci_upper"] <= 1
        # CI lower should be less than or equal to point estimate
        assert data["ci_lower"] <= data["completion_rate"]
        # CI upper should be greater than or equal to point estimate
        assert data["completion_rate"] <= data["ci_upper"]


def test_compute_borough_completion_rates_power_analysis():
    """Test power analysis (has_power flag)."""
    df = _sample_complaints_data()
    rates = compute_borough_completion_rates(df)

    # All results should have a has_power boolean
    assert isinstance(rates["MN"]["has_power"], bool)
    assert isinstance(rates["BK"]["has_power"], bool)
    assert isinstance(rates["BX"]["has_power"], bool)
    assert isinstance(rates["QN"]["has_power"], bool)
    assert isinstance(rates["SI"]["has_power"], bool)

    # Test with very large effect size to ensure power for small samples
    rates_huge_effect = compute_borough_completion_rates(
        df, effect_size=0.50
    )
    # With effect_size=0.50, min_sample = max(10, int(61.4/0.25)) = 245
    # So samples with n >= 245 should have power (none in our data)
    assert isinstance(rates_huge_effect["MN"]["has_power"], bool)

    # Test with tiny effect size for minimal power requirement
    rates_tiny_effect = compute_borough_completion_rates(
        df, effect_size=1.0
    )
    # With effect_size=1.0, min_sample = max(10, 61) = 61
    # MN, BK have 100 samples (>61), should have power
    # BX, QN have 50 samples (<61), should NOT have power
    # SI has 30 samples (<61), should NOT have power
    assert rates_tiny_effect["MN"]["has_power"] is True  # 100 >= 61
    assert rates_tiny_effect["BK"]["has_power"] is True  # 100 >= 61
    assert rates_tiny_effect["BX"]["has_power"] is False  # 50 < 61
    assert rates_tiny_effect["QN"]["has_power"] is False  # 50 < 61
    assert rates_tiny_effect["SI"]["has_power"] is False  # 30 < 61


def test_compute_borough_completion_rates_comparison_table():
    """Test that comparison table is generated correctly."""
    df = _sample_complaints_data()
    rates = compute_borough_completion_rates(df)

    table = rates["comparison_table"]
    assert isinstance(table, pd.DataFrame)
    assert len(table) == 5  # 5 boroughs
    assert set(table.columns) == {
        "borough",
        "completion_rate",
        "resolved_count",
        "total_count",
        "ci_lower",
        "ci_upper",
        "sample_size",
        "has_power",
    }

    # Check borough column
    boroughs = set(table["borough"].tolist())
    assert boroughs == {"MN", "BK", "BX", "QN", "SI"}


def test_compute_borough_completion_rates_overall_rate():
    """Test overall completion rate calculation."""
    df = _sample_complaints_data()
    rates = compute_borough_completion_rates(df)

    # Overall should be weighted average
    # Total resolved: 800 + 600 + 350 + 450 + 150 = 2350
    # Total complaints: 1000 + 1000 + 500 + 500 + 300 = 3300
    # Overall rate = 2350 / 3300 ≈ 0.7121
    expected_overall = (800 + 600 + 350 + 450 + 150) / 3300
    assert abs(rates["overall_completion_rate"] - expected_overall) < 0.001


def test_compute_borough_completion_rates_empty_dataframe():
    """Test handling of empty DataFrame."""
    df = pd.DataFrame(
        {
            "borough": [],
            "total_complaints": [],
            "resolved_complaints": [],
        }
    )
    rates = compute_borough_completion_rates(df)

    assert rates["overall_completion_rate"] == 0.0
    assert len(rates["comparison_table"]) == 0


def test_compute_borough_completion_rates_missing_column():
    """Test error handling for missing columns."""
    df = pd.DataFrame(
        {
            "borough": ["MN"] * 10,
            "total_complaints": [10] * 10,
        }
    )

    with pytest.raises(ValueError, match="resolved_complaints"):
        compute_borough_completion_rates(df)


def test_compute_borough_completion_rates_zero_totals():
    """Test handling of zero total complaints."""
    df = pd.DataFrame(
        {
            "borough": ["MN"] * 10,
            "total_complaints": [0] * 10,
            "resolved_complaints": [0] * 10,
        }
    )
    rates = compute_borough_completion_rates(df)

    assert rates["MN"]["completion_rate"] == 0.0
    assert rates["MN"]["ci_lower"] == 0.0
    assert rates["MN"]["ci_upper"] == 0.0


def test_compute_borough_completion_rates_custom_columns():
    """Test with custom column names."""
    df = pd.DataFrame(
        {
            "location": ["MN"] * 100 + ["BK"] * 100,
            "total": [10] * 200,
            "resolved": [8] * 100 + [6] * 100,
        }
    )
    rates = compute_borough_completion_rates(
        df,
        borough_col="location",
        total_col="total",
        resolved_col="resolved",
    )

    assert "MN" in rates
    assert "BK" in rates
    assert rates["MN"]["completion_rate"] == 0.8
    assert rates["BK"]["completion_rate"] == 0.6


def test_compute_borough_completion_rates_custom_confidence_level():
    """Test with custom confidence level."""
    df = _sample_complaints_data()

    # Test with 90% confidence (narrower interval)
    rates_90 = compute_borough_completion_rates(df, confidence_level=0.90)
    # Test with 99% confidence (wider interval)
    rates_99 = compute_borough_completion_rates(df, confidence_level=0.99)

    # 99% CI should be wider than 90% CI
    assert (
        rates_99["MN"]["ci_upper"] - rates_99["MN"]["ci_lower"]
        > rates_90["MN"]["ci_upper"] - rates_90["MN"]["ci_lower"]
    )


def test_compute_borough_completion_rates_small_sample():
    """Test with small sample sizes that lack power."""
    df = pd.DataFrame(
        {
            "borough": ["MN"] * 5,
            "total_complaints": [10] * 5,
            "resolved_complaints": [8] * 5,
        }
    )
    rates = compute_borough_completion_rates(df)

    # With only 5 samples and default effect_size=0.08,
    # min_sample = (7.84^2) / 0.08^2 = ~9604, so has_power should be False
    assert rates["MN"]["has_power"] is False


def test_compute_borough_completion_rates_rounding():
    """Test that numeric results are properly rounded."""
    df = pd.DataFrame(
        {
            "borough": ["MN"] * 7,
            "total_complaints": [3] * 7,
            "resolved_complaints": [1] * 7,
        }
    )
    rates = compute_borough_completion_rates(df)

    # Check that rates are rounded to 4 decimal places
    rate_str = str(rates["MN"]["completion_rate"])
    # Should have at most 4 decimal places (1/3 ≈ 0.3333)
    assert len(rate_str.split(".")[1]) <= 4


def test_compute_borough_completion_rates_string_borough_names():
    """Test that borough names are converted to strings."""
    df = pd.DataFrame(
        {
            "borough": [1, 1, 2, 2],
            "total_complaints": [10, 10, 10, 10],
            "resolved_complaints": [8, 8, 6, 6],
        }
    )
    rates = compute_borough_completion_rates(df)

    # Borough names should be strings
    assert "1" in rates
    assert "2" in rates
    assert isinstance(rates["1"]["completion_rate"], float)
