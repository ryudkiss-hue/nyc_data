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
from typing import Optional

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
    """Create registry with 24 core NYC DOT SIM metrics (Total Recall Suite)."""
    registry = MetricsRegistry()

    # --- Phase F: Compliance & SLA ---
    registry.register(
        MetricDefinition(
            id="phase_f_sla_probability",
            name="SLA Compliance Probability",
            description="Likelihood of meeting 45-day inspection target",
            formula="SUM(CASE WHEN days_to_inspect <= 45 THEN 1 ELSE 0 END) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=90,
        )
    )
    registry.register(
        MetricDefinition(
            id="phase_f_investment_justification",
            name="Investment Justification Rate",
            description="% of locations verified for IFA capital upgrade",
            formula="SUM(CASE WHEN ifa_eligible='Y' THEN 1 ELSE 0 END) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=70,
        )
    )

    # --- Phase E: Temporal & Production ---
    registry.register(
        MetricDefinition(
            id="production_rate_linear_feet",
            name="Linear Feet per Crew-Day",
            description="Physical productivity of in-house crews",
            formula="SUM(linear_feet) / SUM(crew_days)",
            units="ft/day",
            sla_threshold=180,
            sla_direction="higher_is_better",
        )
    )
    registry.register(
        MetricDefinition(
            id="backlog_burn_rate",
            name="Backlog Burn Rate",
            description="Monthly completion volume vs open backlog",
            formula="SUM(monthly_completed) / MAX(total_backlog)",
            units="ratio",
            sla_threshold=0.15,
            sla_direction="higher_is_better",
        )
    )

    # --- Phase D: Priority & Scaling ---
    registry.register(
        MetricDefinition(
            id="hpr_resolution_speed",
            name="HPR Resolution Speed",
            description="Avg days to address High Priority Requests",
            formula="AVG(DATEDIFF('day', request_date, action_date))",
            units="days",
            sla_threshold=7,
            sla_direction="lower_is_better",
        )
    )
    registry.register(
        MetricDefinition(
            id="outlier_density_index",
            name="Outlier Density Index",
            description="Concentration of severe defects (Rating 1-2)",
            formula="SUM(CASE WHEN condition_rating <= 2 THEN 1 ELSE 0 END) / COUNT(*)",
            units="index",
            sla_threshold=0.05,
            sla_direction="lower_is_better",
        )
    )

    # --- Phase C: GIS & Conflicts ---
    registry.register(
        MetricDefinition(
            id="construction_list_validity",
            name="List Integrity Score",
            description="% of locations verified as conflict-free via GIS",
            formula="SUM(CASE WHEN gis_conflict_count = 0 THEN 1 ELSE 0 END) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=95,
        )
    )
    registry.register(
        MetricDefinition(
            id="spatial_clustering_efficiency",
            name="Clustering Efficiency",
            description="Average distance between adjacent work sites",
            formula="AVG(distance_to_nearest_site_ft)",
            units="ft",
            sla_threshold=500,
            sla_direction="lower_is_better",
        )
    )

    # --- Phase B: Financials & Contracts ---
    registry.register(
        MetricDefinition(
            id="cost_per_sq_ft",
            name="Unit Cost (Sq Ft)",
            description="Total spend per square foot repaired",
            formula="SUM(total_spend) / SUM(sq_ft)",
            units="USD/sqft",
            sla_threshold=45.0,
            sla_direction="lower_is_better",
        )
    )
    registry.register(
        MetricDefinition(
            id="budget_utilization_rate",
            name="Budget Utilization",
            description="YTD actual spend vs allocated budget",
            formula="(SUM(actual_spend) / SUM(budget_allocated)) * 100",
            units="%",
            sla_threshold=85,
        )
    )

    # --- Core Operational Metrics ---
    registry.register(
        MetricDefinition(
            id="completion_rate",
            name="Ramp Completion Rate",
            description="Percentage of ADA ramps completed",
            formula="SUM(CASE WHEN completion_status='completed' THEN 1 ELSE 0 END) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=85,
        )
    )
    registry.register(
        MetricDefinition(
            id="condition_failure_rate",
            name="Sidewalk Failure Rate",
            description="Percentage of sidewalks rated as failed (rating < 4)",
            formula="SUM(CASE WHEN condition_rating < 4 THEN 1 ELSE 0 END) / COUNT(*)",
            units="%",
            ci_method="wilson_score",
            sla_threshold=15,
            sla_direction="lower_is_better",
        )
    )
    
    # ... (Rest of existing default metrics)
    return registry
