"""Semantic Layer: Define metrics once, reuse everywhere.

Provides:
- MetricDefinition: Metric metadata (formula, CI method, SLA, units)
- MetricsRegistry: Central registry of all metrics
- MetricComputation: Compute metric values and confidence intervals
- WilsonScoreCI: Binomial proportion confidence intervals (accurate for small n)

Pattern: Define metric once, reuse across all datasets and marts.
Example:
  registry = MetricsRegistry()
  completion_rate = MetricDefinition(
    id="completion_rate",
    formula="SUM(completed) / COUNT(*)",
    ci_method="wilson_score",
    sla_threshold=80
  )
  registry.register(completion_rate)

  # Now use it anywhere:
  result = MetricComputation("completion_rate", numerator=8, denominator=10)
"""
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """Definition of a single metric."""

    id: str  # Unique identifier (e.g., "completion_rate")
    name: str  # Human-readable name
    formula: str  # SQL formula or description
    units: str = ""  # Units (%, days, count, etc.)
    description: str = ""  # Detailed description
    numerator_filter: Optional[str] = None  # Filter for numerator (e.g., "status='completed'")
    denominator_filter: Optional[str] = None  # Filter for denominator
    ci_method: str = "none"  # "wilson_score", "normal", "none"
    sla_threshold: Optional[float] = None  # SLA target value
    sla_direction: str = "higher_is_better"  # "higher_is_better" or "lower_is_better"
    sample_size_min: int = 1  # Minimum sample size for validity
    confidence_level: float = 0.95  # CI confidence level (default 95%)


class WilsonScoreCI:
    """Compute Wilson Score confidence interval for binomial proportions.

    More accurate than normal approximation, especially for small samples.
    Reference: https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
    """

    def __init__(self, successes: int, total: int, confidence_level: float = 0.95):
        """Initialize with binomial data.

        Args:
            successes: Number of successful outcomes
            total: Total number of trials
            confidence_level: CI confidence level (e.g., 0.95 for 95% CI)
        """
        self.successes = successes
        self.total = total
        self.confidence_level = confidence_level
        self.z = self._z_score(confidence_level)

    @staticmethod
    def _z_score(confidence_level: float) -> float:
        """Get z-score for given confidence level."""
        # Common values: 0.90 → 1.645, 0.95 → 1.96, 0.99 → 2.576
        z_values = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
            0.999: 3.291,
        }
        return z_values.get(confidence_level, 1.96)  # Default to 95%

    def compute(self) -> tuple[float, float]:
        """Compute Wilson Score confidence interval.

        Returns:
            (lower_bound, upper_bound) as proportions [0, 1]
        """
        if self.total == 0:
            return 0.0, 1.0

        p_hat = self.successes / self.total
        z_sq = self.z ** 2
        denominator = 1 + z_sq / self.total

        center = (p_hat + z_sq / (2 * self.total)) / denominator
        margin = self.z * math.sqrt(p_hat * (1 - p_hat) / self.total + z_sq / (4 * self.total ** 2)) / denominator

        lower = max(0.0, center - margin)
        upper = min(1.0, center + margin)

        return lower, upper


class MetricComputation:
    """Compute a metric value and optional confidence interval."""

    def __init__(
        self,
        metric_id: str,
        numerator: int,
        denominator: int,
        sample_size: Optional[int] = None,
        ci_method: str = "wilson_score",
        ci_level: float = 0.95,
    ):
        """Initialize metric computation.

        Args:
            metric_id: Reference to registered metric
            numerator: Numerator value (e.g., completed count)
            denominator: Denominator value (e.g., total count)
            sample_size: Sample size (defaults to denominator)
            ci_method: Method for confidence interval
            ci_level: Confidence level (e.g., 0.95)
        """
        self.metric_id = metric_id
        self.numerator = numerator
        self.denominator = denominator
        self.sample_size = sample_size or denominator
        self.ci_method = ci_method
        self.ci_level = ci_level

    def compute_value(self) -> float:
        """Compute metric value as percentage."""
        if self.denominator == 0:
            return 0.0
        return 100.0 * self.numerator / self.denominator

    def compute_ci(self) -> tuple[float, float]:
        """Compute confidence interval as percentages.

        Returns:
            (lower_percent, upper_percent)
        """
        if self.ci_method == "wilson_score":
            ci = WilsonScoreCI(self.numerator, self.denominator, self.ci_level)
            lower, upper = ci.compute()
            return 100.0 * lower, 100.0 * upper
        else:
            # No CI
            value = self.compute_value()
            return value, value

    def is_valid(self, min_sample_size: int = 1) -> bool:
        """Check if computation is statistically valid."""
        return self.sample_size >= min_sample_size


class MetricsRegistry:
    """Central registry of all metric definitions."""

    def __init__(self):
        self._metrics: dict[str, MetricDefinition] = {}

    def register(self, metric: MetricDefinition):
        """Register a metric definition.

        Args:
            metric: MetricDefinition to register
        """
        self._metrics[metric.id] = metric
        logger.info(f"Registered metric: {metric.id} ({metric.name})")

    def get(self, metric_id: str) -> MetricDefinition:
        """Get metric definition by ID.

        Raises:
            KeyError: If metric not found
        """
        if metric_id not in self._metrics:
            raise KeyError(f"Metric not found: {metric_id}")
        return self._metrics[metric_id]

    def list_metrics(self) -> list[MetricDefinition]:
        """List all registered metrics."""
        return list(self._metrics.values())

    def get_sla_threshold(self, metric_id: str) -> Optional[float]:
        """Get SLA threshold for metric."""
        metric = self.get(metric_id)
        return metric.sla_threshold

    def check_sla(self, metric_id: str, value: float) -> bool:
        """Check if metric value meets SLA.

        Returns:
            True if metric meets SLA, False otherwise
        """
        metric = self.get(metric_id)
        if metric.sla_threshold is None:
            return True

        if metric.sla_direction == "higher_is_better":
            return value >= metric.sla_threshold
        else:  # lower_is_better
            return value <= metric.sla_threshold


def create_default_registry() -> MetricsRegistry:
    """Create registry with 12 core NYC DOT metrics."""
    registry = MetricsRegistry()

    # Ramp accessibility metrics
    registry.register(
        MetricDefinition(
            id="completion_rate",
            name="Ramp Completion Rate",
            description="Percentage of ADA ramps completed",
            formula="SUM(CASE WHEN completion_status='completed' THEN 1 ELSE 0 END) / COUNT(*)",
            numerator_filter="completion_status = 'completed'",
            denominator_filter="1=1",
            units="%",
            ci_method="wilson_score",
            sla_threshold=85,
            sla_direction="higher_is_better",
        )
    )

    # Sidewalk inspection metrics
    registry.register(
        MetricDefinition(
            id="condition_failure_rate",
            name="Sidewalk Failure Rate",
            description="Percentage of sidewalks rated as failed (rating < 4)",
            formula="SUM(CASE WHEN condition_rating < 4 THEN 1 ELSE 0 END) / COUNT(*)",
            numerator_filter="condition_rating < 4",
            denominator_filter="1=1",
            units="%",
            ci_method="wilson_score",
            sla_threshold=15,
            sla_direction="lower_is_better",
        )
    )

    # Data freshness metrics
    registry.register(
        MetricDefinition(
            id="freshness_days",
            name="Data Freshness",
            description="Days since last update",
            formula="DATEDIFF(day, MAX(created_date), NOW())",
            units="days",
            ci_method="none",
            sla_threshold=14,
            sla_direction="lower_is_better",
        )
    )

    # Conflict detection metrics
    registry.register(
        MetricDefinition(
            id="conflict_density",
            name="Permit-Inspection Conflict Density",
            description="% of inspections overlapping with active permits",
            formula="SUM(CASE WHEN conflicts > 0 THEN 1 ELSE 0 END) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=5,
            sla_direction="lower_is_better",
        )
    )

    # Material-specific metrics
    registry.register(
        MetricDefinition(
            id="concrete_failure_rate",
            name="Concrete Failure Rate",
            description="Failure rate for concrete sidewalks",
            formula="SUM(CASE WHEN material='concrete' AND rating < 4 THEN 1 ELSE 0 END) / SUM(CASE WHEN material='concrete' THEN 1 ELSE 0 END)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=12,
            sla_direction="lower_is_better",
        )
    )

    registry.register(
        MetricDefinition(
            id="asphalt_failure_rate",
            name="Asphalt Failure Rate",
            description="Failure rate for asphalt sidewalks",
            formula="SUM(CASE WHEN material='asphalt' AND rating < 4 THEN 1 ELSE 0 END) / SUM(CASE WHEN material='asphalt' THEN 1 ELSE 0 END)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=20,
            sla_direction="lower_is_better",
        )
    )

    # Borough metrics
    registry.register(
        MetricDefinition(
            id="brooklyn_failure_rate",
            name="Brooklyn Failure Rate",
            description="Sidewalk failure rate in Brooklyn",
            formula="SUM(CASE WHEN borough='BK' AND rating < 4 THEN 1 ELSE 0 END) / SUM(CASE WHEN borough='BK' THEN 1 ELSE 0 END)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=18,
            sla_direction="lower_is_better",
        )
    )

    registry.register(
        MetricDefinition(
            id="manhattan_failure_rate",
            name="Manhattan Failure Rate",
            description="Sidewalk failure rate in Manhattan",
            formula="SUM(CASE WHEN borough='MN' AND rating < 4 THEN 1 ELSE 0 END) / SUM(CASE WHEN borough='MN' THEN 1 ELSE 0 END)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=16,
            sla_direction="lower_is_better",
        )
    )

    # Quality metrics
    registry.register(
        MetricDefinition(
            id="data_completeness",
            name="Data Completeness",
            description="% of records with all required fields",
            formula="SUM(CASE WHEN all_required_fields_present THEN 1 ELSE 0 END) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=95,
            sla_direction="higher_is_better",
        )
    )

    registry.register(
        MetricDefinition(
            id="schema_stability",
            name="Schema Stability",
            description="Whether schema matches expected structure",
            formula="CASE WHEN schema_matches_expected THEN 1 ELSE 0 END",
            units="binary",
            ci_method="none",
            sla_threshold=1,
            sla_direction="higher_is_better",
        )
    )

    # Unique value metrics
    registry.register(
        MetricDefinition(
            id="duplicate_rate",
            name="Duplicate Rate",
            description="% of records that are duplicates",
            formula="(COUNT(*) - COUNT(DISTINCT key_column)) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=1,
            sla_direction="lower_is_better",
        )
    )

    return registry
