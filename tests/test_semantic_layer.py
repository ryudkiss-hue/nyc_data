"""Tests for Semantic Layer: Define metrics once, reuse everywhere."""
import pytest
from datetime import datetime, timedelta

from socrata_toolkit.core.semantic_layer import (
    MetricDefinition,
    MetricsRegistry,
    MetricComputation,
    WilsonScoreCI,
)


class TestMetricDefinition:
    """Test metric definition and metadata."""

    def test_completion_rate_metric(self):
        """Test defining a completion rate metric."""
        metric = MetricDefinition(
            id="completion_rate",
            name="Ramp Completion Rate",
            description="Percentage of ramps completed out of total",
            formula="SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) / COUNT(*)",
            numerator_filter="status = 'completed'",
            denominator_filter="1=1",
            units="%",
            ci_method="wilson_score",
            sla_threshold=80,  # Should be >80%
            sla_direction="higher_is_better",
            sample_size_min=30,
        )

        assert metric.id == "completion_rate"
        assert metric.units == "%"
        assert metric.ci_method == "wilson_score"

    def test_freshness_metric(self):
        """Test defining a freshness metric."""
        metric = MetricDefinition(
            id="freshness_days",
            name="Data Freshness",
            description="Days since last update",
            formula="DATEDIFF(day, MAX(created_date), NOW())",
            units="days",
            ci_method="none",
            sla_threshold=14,  # Should be <14 days old
            sla_direction="lower_is_better",
        )

        assert metric.sla_direction == "lower_is_better"
        assert metric.ci_method == "none"

    def test_conflict_density_metric(self):
        """Test defining a spatial conflict metric."""
        metric = MetricDefinition(
            id="conflict_density",
            name="Permit-Inspection Conflict Density",
            description="% of inspections overlapping with active permits",
            formula="SUM(conflicts) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=5,
            sla_direction="lower_is_better",
        )

        assert metric.id == "conflict_density"
        assert metric.sla_direction == "lower_is_better"


class TestMetricsRegistry:
    """Test metric registration and lookup."""

    def test_register_metric(self):
        """Test registering a metric."""
        registry = MetricsRegistry()

        metric = MetricDefinition(
            id="completion_rate",
            name="Completion Rate",
            formula="COUNT(*) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
        )

        registry.register(metric)
        assert registry.get("completion_rate") == metric

    def test_get_nonexistent_metric(self):
        """Test retrieving a metric that doesn't exist."""
        registry = MetricsRegistry()

        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_register_multiple_metrics(self):
        """Test registering multiple metrics."""
        registry = MetricsRegistry()

        metrics = [
            MetricDefinition(id=f"metric_{i}", name=f"Metric {i}", formula="1", units="unit")
            for i in range(5)
        ]

        for m in metrics:
            registry.register(m)

        assert len(registry.list_metrics()) == 5

    def test_list_metrics(self):
        """Test listing all registered metrics."""
        registry = MetricsRegistry()

        registry.register(MetricDefinition(id="m1", name="Metric 1", formula="1", units="unit"))
        registry.register(MetricDefinition(id="m2", name="Metric 2", formula="2", units="unit"))

        metrics = registry.list_metrics()
        assert len(metrics) == 2
        assert "m1" in [m.id for m in metrics]


class TestMetricComputation:
    """Test computing metrics from data."""

    def test_compute_completion_rate(self):
        """Test computing a completion rate metric."""
        # Sample data: 8/10 completed
        computation = MetricComputation(
            metric_id="completion_rate",
            numerator=8,
            denominator=10,
            sample_size=10,
            ci_method="wilson_score",
        )

        rate = computation.compute_value()
        assert abs(rate - 80.0) < 0.1  # Should be 80%

    def test_compute_with_ci(self):
        """Test computing a metric with confidence interval."""
        # Large sample for stable CI
        computation = MetricComputation(
            metric_id="completion_rate",
            numerator=750,
            denominator=1000,
            sample_size=1000,
            ci_method="wilson_score",
            ci_level=0.95,
        )

        value = computation.compute_value()
        ci_lower, ci_upper = computation.compute_ci()

        assert value == 75.0
        assert ci_lower > 0
        assert ci_upper <= 100
        assert ci_lower < value < ci_upper


class TestWilsonScoreCI:
    """Test Wilson Score confidence interval computation."""

    def test_wilson_score_95_ci(self):
        """Test Wilson Score with 95% CI."""
        # Example: 8 successes out of 10
        ci = WilsonScoreCI(successes=8, total=10, confidence_level=0.95)

        lower, upper = ci.compute()

        # Expected range for 8/10 with 95% CI: roughly [0.55, 0.98]
        assert 0.4 < lower < 0.7
        assert 0.8 < upper < 1.0
        assert lower < 0.8 < upper

    def test_wilson_score_small_sample(self):
        """Test Wilson Score with small sample size."""
        # Example: 1 success out of 3
        ci = WilsonScoreCI(successes=1, total=3, confidence_level=0.95)

        lower, upper = ci.compute()

        assert 0 <= lower <= upper <= 1

    def test_wilson_score_large_sample(self):
        """Test Wilson Score with large sample size."""
        # Example: 750 successes out of 1000
        ci = WilsonScoreCI(successes=750, total=1000, confidence_level=0.95)

        lower, upper = ci.compute()

        # With large sample, CI should be tighter
        assert abs(lower - 0.75) < 0.05
        assert abs(upper - 0.75) < 0.05

    def test_wilson_score_zero_successes(self):
        """Test Wilson Score with zero successes."""
        ci = WilsonScoreCI(successes=0, total=100, confidence_level=0.95)

        lower, upper = ci.compute()

        assert lower == 0
        assert 0 < upper < 0.1


class TestMetricReuse:
    """Test metric reuse across multiple datasets."""

    def test_same_metric_id_produces_same_results(self):
        """Test that same metric ID produces consistent results."""
        registry = MetricsRegistry()

        metric = MetricDefinition(
            id="completion_rate",
            name="Completion Rate",
            formula="COUNT(*)",
            units="%",
            ci_method="wilson_score",
        )

        registry.register(metric)

        # Compute same metric twice with same data
        comp1 = MetricComputation(
            metric_id="completion_rate", numerator=80, denominator=100, sample_size=100
        )
        comp2 = MetricComputation(
            metric_id="completion_rate", numerator=80, denominator=100, sample_size=100
        )

        assert comp1.compute_value() == comp2.compute_value()

    def test_metric_across_datasets(self):
        """Test using same metric across different datasets."""
        registry = MetricsRegistry()

        # Register metric once
        metric = MetricDefinition(
            id="completion_rate",
            name="Completion Rate",
            formula="COUNT(*)",
            units="%",
            ci_method="wilson_score",
        )
        registry.register(metric)

        # Use for ramps
        ramp_computation = MetricComputation(
            metric_id="completion_rate", numerator=900, denominator=1000, sample_size=1000
        )

        # Use for inspection repairs
        repair_computation = MetricComputation(
            metric_id="completion_rate", numerator=7500, denominator=10000, sample_size=10000
        )

        ramp_rate = ramp_computation.compute_value()
        repair_rate = repair_computation.compute_value()

        assert ramp_rate == 90.0
        assert repair_rate == 75.0
        # Same metric ID, different values for different datasets
