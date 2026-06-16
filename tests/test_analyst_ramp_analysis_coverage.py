"""Comprehensive tests for analyst.ramp_analysis module."""

from __future__ import annotations

import pandas as pd
import pytest

from socrata_toolkit.analyst.ramp_analysis import compute_borough_completion_rates


class TestComputeBoroughCompletionRates:
    """Tests for compute_borough_completion_rates function."""

    def test_basic_completion_rates(self):
        df = pd.DataFrame(
            {
                "borough": ["MN", "MN", "BK", "BK"],
                "total_complaints": [100, 100, 100, 100],
                "resolved_complaints": [80, 80, 60, 60],
            }
        )
        result = compute_borough_completion_rates(df)
        assert "MN" in result
        assert "BK" in result
        assert result["MN"]["completion_rate"] == 0.8
        assert result["BK"]["completion_rate"] == 0.6

    def test_completion_rates_with_custom_columns(self):
        df = pd.DataFrame(
            {
                "location": ["MN", "MN", "BK"],
                "total": [100, 100, 100],
                "resolved": [50, 50, 75],
            }
        )
        result = compute_borough_completion_rates(
            df,
            borough_col="location",
            total_col="total",
            resolved_col="resolved",
        )
        assert "MN" in result
        assert result["MN"]["completion_rate"] == 0.5

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = compute_borough_completion_rates(df)
        assert "comparison_table" in result
        assert result["comparison_table"].empty
        assert result["overall_completion_rate"] == 0.0

    def test_missing_borough_column(self):
        df = pd.DataFrame(
            {
                "total_complaints": [100],
                "resolved_complaints": [80],
            }
        )
        with pytest.raises(ValueError, match="borough"):
            compute_borough_completion_rates(df, borough_col="missing_borough")

    def test_missing_total_column(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"],
                "resolved_complaints": [80],
            }
        )
        with pytest.raises(ValueError, match="not found"):
            compute_borough_completion_rates(df, total_col="missing_total")

    def test_missing_resolved_column(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"],
                "total_complaints": [100],
            }
        )
        with pytest.raises(ValueError, match="not found"):
            compute_borough_completion_rates(df, resolved_col="missing_resolved")

    def test_zero_total_complaints(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"],
                "total_complaints": [0],
                "resolved_complaints": [0],
            }
        )
        result = compute_borough_completion_rates(df)
        assert result["MN"]["completion_rate"] == 0.0
        assert result["MN"]["ci_lower"] == 0.0
        assert result["MN"]["ci_upper"] == 0.0

    def test_all_resolved(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"],
                "total_complaints": [100],
                "resolved_complaints": [100],
            }
        )
        result = compute_borough_completion_rates(df)
        assert result["MN"]["completion_rate"] == 1.0

    def test_confidence_intervals(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"],
                "total_complaints": [50],
                "resolved_complaints": [35],
            }
        )
        result = compute_borough_completion_rates(df)
        ci_lower = result["MN"]["ci_lower"]
        ci_upper = result["MN"]["ci_upper"]
        rate = result["MN"]["completion_rate"]
        # CI should contain the rate
        assert ci_lower <= rate <= ci_upper
        # CI bounds should be in [0, 1]
        assert 0 <= ci_lower <= 1
        assert 0 <= ci_upper <= 1

    def test_sample_size(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"] * 50,
                "total_complaints": [10] * 50,
                "resolved_complaints": [8] * 50,
            }
        )
        result = compute_borough_completion_rates(df)
        assert result["MN"]["sample_size"] == 50

    def test_power_analysis_high_power(self):
        # Large sample size and large effect size -> has_power = True
        df = pd.DataFrame(
            {
                "borough": ["MN"] * 1000,
                "total_complaints": [10] * 1000,
                "resolved_complaints": [8] * 1000,
            }
        )
        # With effect_size=0.2, min_sample = max(10, int(61.4336 / 0.04)) = 1536
        # So sample_size (1000) < min_sample (1536) still False
        # Use smaller effect_size = 0.3: min_sample = max(10, int(61.4336 / 0.09)) = 683
        # Then sample_size (1000) > min_sample (683) -> has_power = True
        result = compute_borough_completion_rates(df, effect_size=0.3)
        assert result["MN"]["has_power"] is True

    def test_power_analysis_low_power(self):
        # Small sample size -> has_power = False
        df = pd.DataFrame(
            {
                "borough": ["MN"] * 5,
                "total_complaints": [10] * 5,
                "resolved_complaints": [8] * 5,
            }
        )
        result = compute_borough_completion_rates(df, effect_size=0.08)
        assert result["MN"]["has_power"] is False

    def test_power_analysis_zero_effect_size(self):
        # Zero effect size should use default min_sample
        df = pd.DataFrame(
            {
                "borough": ["MN"] * 20,
                "total_complaints": [10] * 20,
                "resolved_complaints": [8] * 20,
            }
        )
        result = compute_borough_completion_rates(df, effect_size=0.0)
        # With effect_size=0, min_sample = 30, so sample_size=20 -> has_power=False
        assert result["MN"]["has_power"] is False

    def test_multiple_boroughs(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"] * 100 + ["BK"] * 100 + ["QN"] * 100,
                "total_complaints": [10] * 300,
                "resolved_complaints": [8] * 100 + [6] * 100 + [7] * 100,
            }
        )
        result = compute_borough_completion_rates(df)
        assert len(result) == 5  # 3 boroughs + comparison_table + overall_completion_rate
        assert "MN" in result
        assert "BK" in result
        assert "QN" in result
        assert result["MN"]["completion_rate"] == 0.8
        assert result["BK"]["completion_rate"] == 0.6

    def test_comparison_table(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"] * 50 + ["BK"] * 50,
                "total_complaints": [10] * 100,
                "resolved_complaints": [8] * 50 + [6] * 50,
            }
        )
        result = compute_borough_completion_rates(df)
        comparison_table = result["comparison_table"]
        assert len(comparison_table) == 2
        assert "borough" in comparison_table.columns
        assert "completion_rate" in comparison_table.columns
        assert "ci_lower" in comparison_table.columns
        assert "ci_upper" in comparison_table.columns

    def test_overall_completion_rate(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"] * 100 + ["BK"] * 100,
                "total_complaints": [10] * 200,
                "resolved_complaints": [8] * 100 + [6] * 100,
            }
        )
        result = compute_borough_completion_rates(df)
        # Overall: (800 + 600) / (1000 + 1000) = 1400 / 2000 = 0.7
        assert result["overall_completion_rate"] == 0.7

    def test_custom_confidence_level(self):
        df = pd.DataFrame(
            {
                "borough": ["MN"],
                "total_complaints": [50],
                "resolved_complaints": [25],
            }
        )
        result_90 = compute_borough_completion_rates(df, confidence_level=0.90)
        result_99 = compute_borough_completion_rates(df, confidence_level=0.99)
        # 99% CI should be wider than 90% CI
        width_90 = result_90["MN"]["ci_upper"] - result_90["MN"]["ci_lower"]
        width_99 = result_99["MN"]["ci_upper"] - result_99["MN"]["ci_lower"]
        assert width_99 > width_90

    def test_numeric_borough_values(self):
        df = pd.DataFrame(
            {
                "borough": [1, 1, 2, 2],
                "total_complaints": [100, 100, 100, 100],
                "resolved_complaints": [80, 80, 60, 60],
            }
        )
        result = compute_borough_completion_rates(df)
        # Borough values get converted to strings
        assert "1" in result
        assert "2" in result

    def test_null_values_in_complains(self):
        df = pd.DataFrame(
            {
                "borough": ["MN", "MN", "BK"],
                "total_complaints": [100.0, None, 100.0],
                "resolved_complaints": [80.0, None, 60.0],
            }
        )
        # sum() should ignore NaN values
        result = compute_borough_completion_rates(df)
        assert "MN" in result
        assert result["MN"]["total_count"] == 100  # Only the first row counts

    def test_fractional_complaints(self):
        df = pd.DataFrame(
            {
                "borough": ["MN", "BK"],
                "total_complaints": [100.5, 200.5],
                "resolved_complaints": [80.3, 150.2],
            }
        )
        result = compute_borough_completion_rates(df)
        # Values get converted to int via sum()
        mn_rate = result["MN"]["completion_rate"]
        assert 0 <= mn_rate <= 1
