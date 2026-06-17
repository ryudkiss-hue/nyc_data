"""
Data models for KPI Registry.

Defines all dataclasses for KPI definitions, thresholds, time-series config,
dimensions, and computation results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml


class ThresholdLevel(str, Enum):
    """Performance threshold levels."""

    BRONZE = "bronze"  # 0-60: Critical/Below target
    SILVER = "silver"  # 60-80: At risk
    GOLD = "gold"  # 80-100: On target


@dataclass
class ThresholdConfig:
    """Threshold configuration with colors and ranges."""

    bronze_min: float = 0.0
    silver_min: float = 60.0
    gold_min: float = 80.0
    max_value: float = 100.0
    bronze_color: str = "#ffcccc"
    silver_color: str = "#ffffcc"
    gold_color: str = "#ccffcc"

    def get_level(self, value: float) -> ThresholdLevel:
        """Determine threshold level for a value."""
        if value >= self.gold_min:
            return ThresholdLevel.GOLD
        elif value >= self.silver_min:
            return ThresholdLevel.SILVER
        else:
            return ThresholdLevel.BRONZE

    def get_color(self, value: float) -> str:
        """Get color for a value."""
        level = self.get_level(value)
        if level == ThresholdLevel.GOLD:
            return self.gold_color
        elif level == ThresholdLevel.SILVER:
            return self.silver_color
        else:
            return self.bronze_color


@dataclass
class TimeSeriesMetadata:
    """Configuration for time-series computation."""

    enabled: bool = True
    forecast_method: str = "exponential_smoothing"  # linear, exponential, arima
    forecast_periods: int = 3  # months
    confidence_interval: float = 0.95  # 95% CI
    seasonality_period: Optional[int] = 12  # months
    rolling_window: int = 12  # months
    anomaly_detection: bool = True
    anomaly_threshold: float = 3.0  # sigma

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []
        if self.forecast_method not in ["linear", "exponential", "arima"]:
            errors.append(
                f"Invalid forecast_method: {self.forecast_method}"
            )
        if not 0 < self.confidence_interval < 1:
            errors.append(
                f"Invalid confidence_interval: {self.confidence_interval}"
            )
        if self.anomaly_threshold <= 0:
            errors.append(
                f"Invalid anomaly_threshold: {self.anomaly_threshold}"
            )
        return errors


@dataclass
class DimensionConfig:
    """Dimension breakdown configuration."""

    name: str  # e.g., "borough", "contractor", "material_type"
    values: List[str] = field(default_factory=list)  # e.g., ["MN", "BK", "QN"]
    aggregation: str = "sum"  # sum, avg, count, max, min
    enabled: bool = True

    def validate(self) -> List[str]:
        """Validate dimension configuration."""
        errors = []
        if not self.name:
            errors.append("Dimension name is required")
        if self.aggregation not in ["sum", "avg", "count", "max", "min"]:
            errors.append(f"Invalid aggregation: {self.aggregation}")
        return errors


@dataclass
class KPIDefinition:
    """Complete KPI specification with all metadata."""

    kpi_id: str
    name: str
    category: str  # permits, pedestrian, safety, budget, compliance
    description: str = ""
    unit: str = "%"  # percent, count, days, hours, $, etc.
    direction: str = "up"  # up = higher is better, down = lower is better
    target: float = 100.0

    # Dataset source
    source_dataset_key: str = ""  # e.g., "inspection", "violations"
    source_fourfour: str = ""  # Socrata 4x4 code
    materialization_sql: str = ""  # SQL to compute KPI

    # Thresholds (bronze/silver/gold)
    threshold_config: ThresholdConfig = field(
        default_factory=ThresholdConfig
    )

    # Time-series & forecasting
    time_series_config: TimeSeriesMetadata = field(
        default_factory=TimeSeriesMetadata
    )

    # Dimension breakdowns
    dimensions: List[DimensionConfig] = field(default_factory=list)

    # Visualization
    primary_chart_type: str = "gauge"  # indicator, bar, heatmap, etc.
    alternative_chart_types: List[str] = field(
        default_factory=lambda: ["bar", "line"]
    )
    chart_height: int = 400
    chart_width: int = 400

    # Dashboard & refresh
    dashboard_sections: List[str] = field(
        default_factory=list
    )  # ["overview", "borough-detail"]
    refresh_frequency: str = "daily"  # hourly, daily, weekly, monthly
    refresh_sla_hours: int = 24

    # Metadata
    owner: str = ""
    created_date: Optional[str] = None
    last_updated: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    def validate(self) -> List[str]:
        """Validate KPI definition."""
        errors = []

        # Required fields
        if not self.kpi_id:
            errors.append("kpi_id is required")
        if not self.name:
            errors.append("name is required")
        if not self.category:
            errors.append("category is required")

        # Threshold validation
        if self.threshold_config:
            threshold_errors = self.threshold_config.validate()
            errors.extend(
                [f"Threshold: {e}" for e in threshold_errors]
            )

        # Time series validation
        if self.time_series_config:
            ts_errors = self.time_series_config.validate()
            errors.extend([f"TimeSeries: {e}" for e in ts_errors])

        # Dimension validation
        for dim in self.dimensions:
            dim_errors = dim.validate()
            errors.extend(
                [f"Dimension {dim.name}: {e}" for e in dim_errors]
            )

        # Direction must be up or down
        if self.direction not in ["up", "down"]:
            errors.append(f"Invalid direction: {self.direction}")

        return errors

    def is_valid(self) -> bool:
        """Check if KPI is valid."""
        return len(self.validate()) == 0


@dataclass
class KPIValue:
    """Single KPI value snapshot."""

    value: float
    timestamp: datetime
    period: str = "current"  # current, 1m_ago, 3m_ago, 12m_ago
    dimension_name: Optional[str] = None
    dimension_value: Optional[str] = None


@dataclass
class Trend:
    """Trend information for a KPI."""

    period_over_period: float = 0.0  # % change vs previous period
    historical_average_variance: float = 0.0  # % variance from 12m avg
    forecast_next_period: Optional[float] = None
    forecast_ci_lower: Optional[float] = None
    forecast_ci_upper: Optional[float] = None
    anomaly_flagged: bool = False
    anomaly_severity: str = "none"  # none, low, medium, high
    anomaly_z_score: Optional[float] = None


@dataclass
class KPIResult:
    """Dashboard contract — computation result for a KPI."""

    kpi_id: str
    kpi_definition: KPIDefinition
    current_value: float
    target: float
    status: str = "neutral"  # green, yellow, red, neutral

    # Trend information
    trend: Trend = field(default_factory=Trend)

    # Time series data
    time_series: List[KPIValue] = field(default_factory=list)
    forecast_series: List[KPIValue] = field(default_factory=list)

    # Dimension breakdowns
    dimension_breakdown: Dict[str, Dict[str, float]] = field(
        default_factory=dict
    )

    # Month-over-month
    month_over_month: Dict[str, float] = field(default_factory=dict)

    # Generated insights
    generated_insights: List[str] = field(default_factory=list)

    # Metadata
    computed_at: datetime = field(default_factory=datetime.utcnow)
    data_freshness_hours: int = 0

    def get_status_color(self) -> str:
        """Get color for status."""
        level = self.kpi_definition.threshold_config.get_level(
            self.current_value
        )
        if level == ThresholdLevel.GOLD:
            return "#2ecc71"  # Green
        elif level == ThresholdLevel.SILVER:
            return "#f39c12"  # Yellow
        else:
            return "#e74c3c"  # Red

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "kpi_id": self.kpi_id,
            "current_value": self.current_value,
            "target": self.target,
            "status": self.status,
            "period_over_period": self.trend.period_over_period,
            "forecast_next": self.trend.forecast_next_period,
            "anomaly_flagged": self.trend.anomaly_flagged,
            "computed_at": self.computed_at.isoformat(),
        }
