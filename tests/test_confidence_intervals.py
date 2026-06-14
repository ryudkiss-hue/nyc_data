"""
Tests for confidence interval computations module.

Covers Wilson Score, bootstrap, and t-test CI methods with realistic data.
"""

import numpy as np
import pytest
from scipy import stats

from socrata_toolkit.analysis.confidence_intervals import (
    bootstrap_confidence_interval,
    mean_confidence_interval,
    wilson_score_confidence_interval,
)


class TestWilsonScoreConfidenceInterval:
    """Tests for Wilson Score CI (proportion-based)."""

    def test_wilson_score_ci_proportion(self):
        """Test Wilson Score CI with realistic completion rate data (350/400 ramps)."""
        successes = 350
        total = 400
        result = wilson_score_confidence_interval(successes, total, confidence_level=0.95)

        # Check structure
        assert isinstance(result, dict)
        assert "point_estimate" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "standard_error" in result
        assert "margin_of_error" in result
        assert "confidence_level" in result
        assert "sample_size" in result

        # Check point estimate
        assert result["point_estimate"] == 0.875
        assert result["sample_size"] == 400

        # Check bounds are valid
        assert 0 <= result["lower_bound"] <= result["point_estimate"]
        assert result["point_estimate"] <= result["upper_bound"] <= 1.0

        # Check reasonable interval width
        interval_width = result["upper_bound"] - result["lower_bound"]
        assert 0 < interval_width < 0.2  # Should be narrower for n=400

        # Check confidence level
        assert result["confidence_level"] == 0.95

    def test_wilson_score_ci_small_sample(self):
        """Test Wilson Score CI with small sample (more conservative)."""
        successes = 8
        total = 10
        result = wilson_score_confidence_interval(successes, total, confidence_level=0.95)

        # Point estimate 80%
        assert result["point_estimate"] == 0.8

        # For small samples, Wilson Score should give wider interval
        assert 0 <= result["lower_bound"] < 0.8
        assert 0.8 < result["upper_bound"] <= 1.0

        interval_width = result["upper_bound"] - result["lower_bound"]
        assert 0.1 < interval_width < 0.5

    def test_wilson_score_ci_extreme_proportions(self):
        """Test Wilson Score CI at boundary cases (0% and 100%)."""
        # All successes (100%)
        result_100 = wilson_score_confidence_interval(100, 100, confidence_level=0.95)
        assert result_100["point_estimate"] == 1.0
        assert result_100["lower_bound"] > 0.95  # Should have lower bound but near 1.0
        assert result_100["upper_bound"] == 1.0

        # No successes (0%)
        result_0 = wilson_score_confidence_interval(0, 100, confidence_level=0.95)
        assert result_0["point_estimate"] == 0.0
        assert np.isclose(result_0["lower_bound"], 0.0, atol=1e-10)  # Should be ~0 (floating point precision)
        assert result_0["upper_bound"] < 0.05  # Should have upper bound but near 0.0

    def test_wilson_score_ci_confidence_levels(self):
        """Test different confidence levels (90%, 95%, 99%)."""
        successes, total = 75, 100

        result_90 = wilson_score_confidence_interval(successes, total, confidence_level=0.90)
        result_95 = wilson_score_confidence_interval(successes, total, confidence_level=0.95)
        result_99 = wilson_score_confidence_interval(successes, total, confidence_level=0.99)

        # Higher confidence should give wider interval
        width_90 = result_90["upper_bound"] - result_90["lower_bound"]
        width_95 = result_95["upper_bound"] - result_95["lower_bound"]
        width_99 = result_99["upper_bound"] - result_99["lower_bound"]

        assert width_90 < width_95 < width_99
        assert result_90["confidence_level"] == 0.90
        assert result_95["confidence_level"] == 0.95
        assert result_99["confidence_level"] == 0.99

    def test_wilson_score_ci_validation(self):
        """Test input validation."""
        # Invalid: successes > total
        with pytest.raises(ValueError, match="successes must be"):
            wilson_score_confidence_interval(101, 100)

        # Invalid: negative successes
        with pytest.raises(ValueError, match="successes must be"):
            wilson_score_confidence_interval(-5, 100)

        # Invalid: zero total
        with pytest.raises(ValueError, match="total must be"):
            wilson_score_confidence_interval(5, 0)

        # Invalid: confidence level out of range
        with pytest.raises(ValueError, match="confidence_level must be"):
            wilson_score_confidence_interval(50, 100, confidence_level=1.0)

        with pytest.raises(ValueError, match="confidence_level must be"):
            wilson_score_confidence_interval(50, 100, confidence_level=0.0)

class TestBootstrapConfidenceInterval:
    """Tests for bootstrap CI (non-parametric)."""

    def test_bootstrap_ci_mean(self):
        """Test bootstrap CI for mean with continuous data."""
        # Temperature measurements in Celsius (realistic sample)
        data = np.array([22.5, 23.1, 21.8, 22.9, 23.3, 22.0, 23.5])
        result = bootstrap_confidence_interval(data, np.mean, confidence_level=0.95)

        # Check structure
        assert isinstance(result, dict)
        assert "point_estimate" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "standard_error" in result
        assert "confidence_level" in result
        assert "n_bootstrap" in result
        assert "bootstrap_samples" in result

        # Check point estimate
        expected_mean = np.mean(data)
        assert np.isclose(result["point_estimate"], expected_mean)

        # Check bounds are valid
        assert result["lower_bound"] < result["point_estimate"]
        assert result["point_estimate"] < result["upper_bound"]

        # Check bootstrap samples
        assert len(result["bootstrap_samples"]) == 1000
        assert isinstance(result["bootstrap_samples"], np.ndarray)

        # Check bounds are within reasonable range of point estimate
        interval_width = result["upper_bound"] - result["lower_bound"]
        assert interval_width > 0
        assert interval_width < 2.0  # Should be tight for n=7

    def test_bootstrap_ci_median(self):
        """Test bootstrap CI for median (non-parametric)."""
        # Skewed data where median is different from mean
        data = np.array([1, 2, 3, 4, 5, 100])  # 100 is outlier
        result = bootstrap_confidence_interval(data, np.median, confidence_level=0.95)

        # Median should be between 3 and 4
        assert 3 <= result["point_estimate"] <= 4

        # Bounds should be valid
        assert result["lower_bound"] <= result["point_estimate"]
        assert result["point_estimate"] <= result["upper_bound"]

    def test_bootstrap_ci_custom_statistic(self):
        """Test bootstrap CI with custom statistic function."""
        data = np.array([10, 20, 30, 40, 50])

        # Custom statistic: coefficient of variation (std / mean)
        def cv_statistic(x):
            return np.std(x, ddof=1) / np.mean(x)

        result = bootstrap_confidence_interval(
            data, cv_statistic, confidence_level=0.95, n_bootstrap=500
        )

        # Check point estimate
        expected_cv = cv_statistic(data)
        assert np.isclose(result["point_estimate"], expected_cv)

        # Check bounds
        assert result["lower_bound"] <= result["point_estimate"]
        assert result["point_estimate"] <= result["upper_bound"]
        assert result["n_bootstrap"] == 500

    def test_bootstrap_ci_reproducibility(self):
        """Test that bootstrap with fixed seed is reproducible."""
        data = np.array([1.5, 2.3, 1.8, 2.5, 2.1])

        result1 = bootstrap_confidence_interval(
            data, np.mean, confidence_level=0.95, random_state=42
        )
        result2 = bootstrap_confidence_interval(
            data, np.mean, confidence_level=0.95, random_state=42
        )

        # Results should be identical
        assert result1["point_estimate"] == result2["point_estimate"]
        assert result1["lower_bound"] == result2["lower_bound"]
        assert result1["upper_bound"] == result2["upper_bound"]
        np.testing.assert_array_equal(
            result1["bootstrap_samples"], result2["bootstrap_samples"]
        )

    def test_bootstrap_ci_different_n_bootstrap(self):
        """Test bootstrap with different sample sizes."""
        data = np.array([5, 6, 7, 8, 9, 10])

        result_100 = bootstrap_confidence_interval(
            data, np.mean, confidence_level=0.95, n_bootstrap=100
        )
        result_5000 = bootstrap_confidence_interval(
            data, np.mean, confidence_level=0.95, n_bootstrap=5000
        )

        # Both should have same point estimate
        assert result_100["point_estimate"] == result_5000["point_estimate"]

        # But different bootstrap samples arrays
        assert len(result_100["bootstrap_samples"]) == 100
        assert len(result_5000["bootstrap_samples"]) == 5000

    def test_bootstrap_ci_validation(self):
        """Test input validation for bootstrap."""
        data = np.array([1, 2, 3, 4, 5])

        # Invalid: n_bootstrap <= 0
        with pytest.raises(ValueError, match="n_bootstrap must be"):
            bootstrap_confidence_interval(data, np.mean, n_bootstrap=0)

        # Invalid: confidence level out of range
        with pytest.raises(ValueError, match="confidence_level must be"):
            bootstrap_confidence_interval(data, np.mean, confidence_level=1.5)

    def test_bootstrap_ci_list_input(self):
        """Test that bootstrap accepts list input (not just numpy arrays)."""
        data_list = [1.5, 2.3, 1.8, 2.5, 2.1]
        data_array = np.array(data_list)

        result_list = bootstrap_confidence_interval(
            data_list, np.mean, random_state=42
        )
        result_array = bootstrap_confidence_interval(
            data_array, np.mean, random_state=42
        )

        # Results should be identical
        assert result_list["point_estimate"] == result_array["point_estimate"]
        np.testing.assert_array_equal(
            result_list["bootstrap_samples"], result_array["bootstrap_samples"]
        )

class TestMeanConfidenceInterval:
    """Tests for t-test CI (parametric, continuous)."""

    def test_mean_ci_t_test(self):
        """Test t-test CI for mean with small continuous sample."""
        # Temperature data (5 readings in Celsius)
        data = np.array([22.5, 23.1, 21.8, 22.9, 23.3])
        result = mean_confidence_interval(data, confidence_level=0.95)

        # Check structure
        assert isinstance(result, dict)
        assert "point_estimate" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "standard_error" in result
        assert "margin_of_error" in result
        assert "confidence_level" in result
        assert "sample_size" in result
        assert "degrees_of_freedom" in result

        # Check point estimate
        expected_mean = np.mean(data)
        assert np.isclose(result["point_estimate"], expected_mean)
        assert result["sample_size"] == 5
        assert result["degrees_of_freedom"] == 4

        # Check bounds
        assert result["lower_bound"] < result["point_estimate"]
        assert result["point_estimate"] < result["upper_bound"]

        # Check interval is reasonable
        interval_width = result["upper_bound"] - result["lower_bound"]
        assert 0 < interval_width < 2.0

    def test_mean_ci_known_case(self):
        """Test mean CI against known statistical case."""
        # Simple case: [10, 20, 30] -> mean = 20
        data = np.array([10.0, 20.0, 30.0])
        result = mean_confidence_interval(data, confidence_level=0.95)

        assert np.isclose(result["point_estimate"], 20.0)
        assert result["sample_size"] == 3
        assert result["degrees_of_freedom"] == 2

        # For df=2, t_crit ≈ 4.303 at 95% CI
        # SE should be sqrt(var(X) / n) where var(X) = 100, so SE ≈ 5.77
        # Margin should be approximately 4.303 * 5.77 ≈ 24.8
        assert result["margin_of_error"] > 20  # Conservative check
        assert result["lower_bound"] < 0
        assert result["upper_bound"] > 40

    def test_mean_ci_large_sample(self):
        """Test mean CI with large sample (t-dist approaches normal)."""
        # Large sample from normal distribution
        np.random.seed(42)
        data = np.random.normal(100, 10, size=500)
        result = mean_confidence_interval(data, confidence_level=0.95)

        # For large samples, CI should be narrow
        interval_width = result["upper_bound"] - result["lower_bound"]
        assert interval_width < 2.0  # Tighter for large sample

        # Point estimate should be close to population mean (100) due to law of large numbers
        assert 98 < result["point_estimate"] < 102

    def test_mean_ci_confidence_levels(self):
        """Test different confidence levels (90%, 95%, 99%)."""
        data = np.array([10, 20, 30, 40, 50])

        result_90 = mean_confidence_interval(data, confidence_level=0.90)
        result_95 = mean_confidence_interval(data, confidence_level=0.95)
        result_99 = mean_confidence_interval(data, confidence_level=0.99)

        # All should have same point estimate
        assert result_90["point_estimate"] == result_95["point_estimate"]
        assert result_95["point_estimate"] == result_99["point_estimate"]

        # But increasing confidence level should widen interval
        width_90 = result_90["upper_bound"] - result_90["lower_bound"]
        width_95 = result_95["upper_bound"] - result_95["lower_bound"]
        width_99 = result_99["upper_bound"] - result_99["lower_bound"]

        assert width_90 < width_95 < width_99

    def test_mean_ci_validation(self):
        """Test input validation for mean CI."""
        # Invalid: only 1 observation
        with pytest.raises(ValueError, match="at least 2 observations"):
            mean_confidence_interval(np.array([5.0]))

        # Invalid: empty array
        with pytest.raises(ValueError, match="at least 2 observations"):
            mean_confidence_interval(np.array([]))

        # Invalid: confidence level
        with pytest.raises(ValueError, match="confidence_level must be"):
            mean_confidence_interval(np.array([1.0, 2.0]), confidence_level=0.0)

    def test_mean_ci_list_input(self):
        """Test that mean CI accepts list input."""
        data_list = [22.5, 23.1, 21.8, 22.9, 23.3]
        data_array = np.array(data_list)

        result_list = mean_confidence_interval(data_list, confidence_level=0.95)
        result_array = mean_confidence_interval(data_array, confidence_level=0.95)

        # Results should be identical
        assert result_list["point_estimate"] == result_array["point_estimate"]
        assert result_list["lower_bound"] == result_array["lower_bound"]
        assert result_list["upper_bound"] == result_array["upper_bound"]

class TestConsistentDictStructure:
    """Tests that all CI methods return consistent dict structures."""

    def test_dict_keys_consistency(self):
        """Verify all methods include core keys."""
        # Data for testing
        proportions_data = (350, 400)
        continuous_data = np.array([22.5, 23.1, 21.8, 22.9, 23.3])

        wilson_result = wilson_score_confidence_interval(*proportions_data)
        bootstrap_result = bootstrap_confidence_interval(
            continuous_data, np.mean, random_state=42
        )
        mean_result = mean_confidence_interval(continuous_data)

        # All should have these core keys
        core_keys = {
            "point_estimate",
            "lower_bound",
            "upper_bound",
            "standard_error",
            "confidence_level",
        }

        assert core_keys.issubset(wilson_result.keys())
        assert core_keys.issubset(bootstrap_result.keys())
        assert core_keys.issubset(mean_result.keys())

    def test_bounds_ordering(self):
        """Verify lower_bound <= point_estimate <= upper_bound."""
        # Wilson Score
        w_result = wilson_score_confidence_interval(75, 100)
        assert (
            w_result["lower_bound"]
            <= w_result["point_estimate"]
            <= w_result["upper_bound"]
        )

        # Bootstrap
        b_result = bootstrap_confidence_interval(
            np.array([1, 2, 3, 4, 5]), np.mean, random_state=42
        )
        assert (
            b_result["lower_bound"]
            <= b_result["point_estimate"]
            <= b_result["upper_bound"]
        )

        # Mean
        m_result = mean_confidence_interval(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        assert (
            m_result["lower_bound"]
            <= m_result["point_estimate"]
            <= m_result["upper_bound"]
        )

class TestIntegrationScenarios:
    """Integration tests with realistic NYC DOT data scenarios."""

    def test_ramp_completion_rate_analysis(self):
        """Realistic scenario: NYC ramp completion rates by borough."""
        # Mock borough completion data
        boroughs = {
            "Manhattan": (180, 200),
            "Brooklyn": (340, 380),
            "Queens": (220, 280),
            "Bronx": (95, 120),
            "Staten Island": (45, 80),
        }

        results = {}
        for borough, (completed, total) in boroughs.items():
            ci = wilson_score_confidence_interval(completed, total, confidence_level=0.95)
            results[borough] = ci

        # Verify all computed successfully
        assert len(results) == 5

        # Check Bronx has wider CI due to smaller sample
        bronx_width = (
            results["Bronx"]["upper_bound"] - results["Bronx"]["lower_bound"]
        )
        manhattan_width = (
            results["Manhattan"]["upper_bound"] - results["Manhattan"]["lower_bound"]
        )
        assert bronx_width > manhattan_width  # Smaller sample = wider interval

    def test_temperature_measurements_confidence(self):
        """Realistic scenario: sidewalk temperature monitoring."""
        # Daily temperature readings (°C)
        temperatures = np.array(
            [22.5, 23.1, 21.8, 22.9, 23.3, 22.0, 23.5, 22.8, 23.2, 22.6]
        )

        # Mean with t-test
        mean_result = mean_confidence_interval(temperatures, confidence_level=0.95)

        # Bootstrap with median
        bootstrap_result = bootstrap_confidence_interval(
            temperatures, np.median, confidence_level=0.95, random_state=42
        )

        # Both should show similar central estimates
        assert 22.0 < mean_result["point_estimate"] < 24.0
        assert 22.0 < bootstrap_result["point_estimate"] < 24.0

        # Check that CIs are narrow enough to be useful
        mean_width = mean_result["upper_bound"] - mean_result["lower_bound"]
        bootstrap_width = (
            bootstrap_result["upper_bound"] - bootstrap_result["lower_bound"]
        )
        assert mean_width < 2.0
        assert bootstrap_width < 2.0
