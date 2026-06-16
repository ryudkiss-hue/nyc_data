"""Prometheus metrics export and observability instrumentation.

This module provides operational metrics collection and export in Prometheus format
for integration with Grafana, Prometheus, and other monitoring systems.

Key Classes:
    - MetricsRegistry: Central metrics collection and export
    - PipelineMetrics: Pipeline execution metrics
    - DataQualityMetrics: Data quality scorecards

Usage:
    registry = MetricsRegistry()
    counter = registry.register_counter('ingestion_records_total', 'Records ingested')
    counter.labels(dataset_id='nyc-311').inc(1500)
    metrics_text = registry.export_prometheus()
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Logging setup
logger = logging.getLogger(__name__)

# Try to import prometheus_client; graceful fallback if not available
try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    logger.warning("prometheus_client not installed; metrics will be collected in-memory only")

@dataclass
class MetricPoint:
    """Single metric data point with timestamp and labels.

    Attributes:
        name: Metric name (snake_case)
        value: Numeric value
        labels: Dict of label key-value pairs
        timestamp: ISO 8601 timestamp when metric was recorded
    """

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_prometheus_line(self) -> str:
        """Format metric as Prometheus text format line.

        Returns:
            str: Prometheus metric line

        Examples:
            >>> point = MetricPoint(
            ...     name='ingestion_records_total',
            ...     value=1500,
            ...     labels={'dataset_id': 'nyc-311'}
            ... )
            >>> line = point.to_prometheus_line()
            >>> 'dataset_id="nyc-311"' in line
            True
        """
        if not self.labels:
            return f"{self.name} {self.value}"

        labels_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        return f"{self.name}{{{labels_str}}} {self.value}"

class MetricsRegistry:
    """Central registry for metrics collection and export.

    Supports Prometheus client library if available, with fallback to
    in-memory metrics collection.

    Attributes:
        use_prometheus: Whether to use prometheus_client library
        registry: Prometheus CollectorRegistry if available
        in_memory_metrics: In-memory metric storage

    Examples:
        >>> reg = MetricsRegistry()
        >>> counter = reg.register_counter('test_total', 'Test counter')
        >>> counter.inc()
        >>> metrics = reg.export_prometheus()
        >>> 'test_total' in metrics
        True
    """

    def __init__(self, use_prometheus: bool = True):
        """Initialize metrics registry.

        Args:
            use_prometheus: Whether to use prometheus_client if available
        """
        self.use_prometheus = use_prometheus and HAS_PROMETHEUS
        self.registry = CollectorRegistry() if self.use_prometheus else None
        self.in_memory_metrics: dict[str, MetricPoint] = {}
        self._lock = threading.Lock()

    def register_counter(self, name: str, help_text: str) -> Counter | MockCounter:
        """Register a counter metric.

        Counter monotonically increases and is used for counting events.

        Args:
            name: Metric name (snake_case)
            help_text: Help documentation for metric

        Returns:
            Counter or MockCounter for recording events

        Examples:
            >>> reg = MetricsRegistry()
            >>> counter = reg.register_counter('http_requests_total', 'Total HTTP requests')
            >>> counter.labels(method='GET', status='200').inc()
        """
        if self.use_prometheus:
            return Counter(name, help_text, registry=self.registry)
        else:
            return MockCounter(name, help_text, self.in_memory_metrics, self._lock)

    def register_gauge(self, name: str, help_text: str) -> Gauge | MockGauge:
        """Register a gauge metric.

        Gauge can increase and decrease and is used for current values.

        Args:
            name: Metric name
            help_text: Help documentation

        Returns:
            Gauge or MockGauge for recording current values

        Examples:
            >>> reg = MetricsRegistry()
            >>> gauge = reg.register_gauge('queue_size', 'Current queue size')
            >>> gauge.set(42)
        """
        if self.use_prometheus:
            return Gauge(name, help_text, registry=self.registry)
        else:
            return MockGauge(name, help_text, self.in_memory_metrics, self._lock)

    def register_histogram(
        self, name: str, help_text: str, buckets: tuple | None = None
    ) -> Histogram | MockHistogram:
        """Register a histogram metric.

        Histogram records distribution of observations.

        Args:
            name: Metric name
            help_text: Help documentation
            buckets: Optional tuple of bucket boundaries

        Returns:
            Histogram or MockHistogram for recording observations

        Examples:
            >>> reg = MetricsRegistry()
            >>> hist = reg.register_histogram(
            ...     'request_duration_seconds',
            ...     'Request duration in seconds',
            ...     buckets=(0.1, 0.5, 1.0, 5.0)
            ... )
            >>> hist.observe(0.25)
        """
        if self.use_prometheus:
            kwargs = {"registry": self.registry}
            if buckets:
                kwargs["buckets"] = buckets
            return Histogram(name, help_text, **kwargs)
        else:
            return MockHistogram(name, help_text, self.in_memory_metrics, self._lock, buckets or ())

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format.

        Returns:
            str: Prometheus text format metrics

        Examples:
            >>> reg = MetricsRegistry()
            >>> counter = reg.register_counter('test_total', 'Test')
            >>> counter.inc(5)
            >>> metrics = reg.export_prometheus()
            >>> 'test_total 5' in metrics or '5.0' in metrics
            True
        """
        if self.use_prometheus:
            from prometheus_client import generate_latest
            return generate_latest(self.registry).decode("utf-8")
        else:
            # Export in-memory metrics
            lines = []
            for metric_point in self.in_memory_metrics.values():
                lines.append(metric_point.to_prometheus_line())
            return "\n".join(lines)

    def export_json(self) -> dict:
        """Export metrics as JSON.

        Returns:
            dict: Metrics as JSON-serializable dictionary

        Examples:
            >>> reg = MetricsRegistry()
            >>> counter = reg.register_counter('test_total', 'Test')
            >>> counter.inc()
            >>> json_data = reg.export_json()
            >>> 'metrics' in json_data
            True
        """
        if self.use_prometheus:
            # Parse Prometheus format to JSON
            metrics_text = self.export_prometheus()
            return {"prometheus_format": metrics_text}
        else:
            return {
                "metrics": [
                    {
                        "name": point.name,
                        "value": point.value,
                        "labels": point.labels,
                        "timestamp": point.timestamp.isoformat() + "Z",
                    }
                    for point in self.in_memory_metrics.values()
                ]
            }

class MockCounter:
    """Mock counter for when prometheus_client is not available."""

    def __init__(self, name: str, help_text: str, storage: dict, lock: threading.Lock):
        """Initialize mock counter."""
        self.name = name
        self.help_text = help_text
        self.storage = storage
        self.lock = lock
        self._labeled_instances: dict[str, MockCounter] = {}

    def labels(self, **kwargs) -> MockCounter:
        """Create labeled instance.

        Args:
            **kwargs: Label key-value pairs

        Returns:
            MockCounter with labels
        """
        label_key = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        if label_key not in self._labeled_instances:
            self._labeled_instances[label_key] = MockCounter(
                self.name, self.help_text, self.storage, self.lock
            )
            self._labeled_instances[label_key]._labels = kwargs
        return self._labeled_instances[label_key]

    def inc(self, amount: float = 1) -> None:
        """Increment counter.

        Args:
            amount: Amount to increment by (default 1)
        """
        with self.lock:
            key = self._make_key()
            if key not in self.storage:
                self.storage[key] = MetricPoint(self.name, 0, getattr(self, "_labels", {}))
            self.storage[key].value += amount

    def _make_key(self) -> str:
        """Create unique key for this metric instance."""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(getattr(self, "_labels", {}).items()))
        return f"{self.name}#{label_str}"

class MockGauge:
    """Mock gauge for when prometheus_client is not available."""

    def __init__(self, name: str, help_text: str, storage: dict, lock: threading.Lock):
        """Initialize mock gauge."""
        self.name = name
        self.help_text = help_text
        self.storage = storage
        self.lock = lock
        self._labeled_instances: dict[str, MockGauge] = {}

    def labels(self, **kwargs) -> MockGauge:
        """Create labeled instance.

        Args:
            **kwargs: Label key-value pairs

        Returns:
            MockGauge with labels
        """
        label_key = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        if label_key not in self._labeled_instances:
            self._labeled_instances[label_key] = MockGauge(
                self.name, self.help_text, self.storage, self.lock
            )
            self._labeled_instances[label_key]._labels = kwargs
        return self._labeled_instances[label_key]

    def set(self, value: float) -> None:
        """Set gauge to value.

        Args:
            value: New gauge value
        """
        with self.lock:
            key = self._make_key()
            self.storage[key] = MetricPoint(self.name, value, getattr(self, "_labels", {}))

    def _make_key(self) -> str:
        """Create unique key for this metric instance."""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(getattr(self, "_labels", {}).items()))
        return f"{self.name}#{label_str}"

class MockHistogram:
    """Mock histogram for when prometheus_client is not available."""

    def __init__(
        self, name: str, help_text: str, storage: dict, lock: threading.Lock, buckets: tuple
    ):
        """Initialize mock histogram."""
        self.name = name
        self.help_text = help_text
        self.storage = storage
        self.lock = lock
        self.buckets = buckets
        self.observations: list[float] = []
        self._labeled_instances: dict[str, MockHistogram] = {}

    def labels(self, **kwargs) -> MockHistogram:
        """Create labeled instance.

        Args:
            **kwargs: Label key-value pairs

        Returns:
            MockHistogram with labels
        """
        label_key = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        if label_key not in self._labeled_instances:
            inst = MockHistogram(self.name, self.help_text, self.storage, self.lock, self.buckets)
            inst._labels = kwargs
            self._labeled_instances[label_key] = inst
        return self._labeled_instances[label_key]

    def observe(self, value: float) -> None:
        """Record observation.

        Args:
            value: Observation value
        """
        with self.lock:
            self.observations.append(value)
            # Store mean as the metric value
            mean = sum(self.observations) / len(self.observations)
            key = self._make_key()
            self.storage[key] = MetricPoint(self.name, mean, getattr(self, "_labels", {}))

    def _make_key(self) -> str:
        """Create unique key for this metric instance."""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(getattr(self, "_labels", {}).items()))
        return f"{self.name}#{label_str}"

@dataclass
class PipelineMetrics:
    """Pipeline execution metrics for observability.

    Tracks ingestion, validation, and transformation metrics.

    Attributes:
        registry: MetricsRegistry instance
        ingestion_records_total: Counter of records ingested
        ingestion_errors_total: Counter of ingestion failures
        ingestion_duration_seconds: Histogram of ingestion time
        schema_violations_total: Counter of schema drift
        validation_failures_total: Counter of validation gate failures
    """

    registry: MetricsRegistry

    def __post_init__(self) -> None:
        """Initialize pipeline metrics."""
        self.ingestion_records_total = self.registry.register_counter(
            "ingestion_records_total", "Total records successfully ingested"
        )

        self.ingestion_errors_total = self.registry.register_counter(
            "ingestion_errors_total", "Total ingestion errors"
        )

        self.ingestion_duration_seconds = self.registry.register_histogram(
            "ingestion_duration_seconds",
            "Ingestion operation duration in seconds",
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0),
        )

        self.schema_violations_total = self.registry.register_counter(
            "schema_violations_total", "Total schema violation incidents"
        )

        self.validation_failures_total = self.registry.register_counter(
            "validation_failures_total", "Total data quality gate failures"
        )

    def record_ingestion_success(self, dataset_id: str, record_count: int, duration_seconds: float) -> None:
        """Record successful ingestion.

        Args:
            dataset_id: Dataset identifier
            record_count: Number of records ingested
            duration_seconds: Ingestion duration in seconds

        Examples:
            >>> registry = MetricsRegistry()
            >>> pm = PipelineMetrics(registry=registry)
            >>> pm.record_ingestion_success('nyc-311', 1500, 2.5)
        """
        self.ingestion_records_total.labels(dataset_id=dataset_id).inc(record_count)
        self.ingestion_duration_seconds.labels(dataset_id=dataset_id).observe(duration_seconds)
        logger.info(f"Recorded ingestion: {dataset_id} ({record_count} records, {duration_seconds:.2f}s)")

    def record_ingestion_error(self, dataset_id: str, error_type: str) -> None:
        """Record ingestion error.

        Args:
            dataset_id: Dataset identifier
            error_type: Type of error (e.g., 'network', 'parsing', 'validation')

        Examples:
            >>> registry = MetricsRegistry()
            >>> pm = PipelineMetrics(registry=registry)
            >>> pm.record_ingestion_error('nyc-311', 'network')
        """
        self.ingestion_errors_total.labels(dataset_id=dataset_id, error_type=error_type).inc()
        logger.warning(f"Recorded ingestion error: {dataset_id} ({error_type})")

    def record_schema_violation(self, dataset_id: str, violation_type: str) -> None:
        """Record schema drift incident.

        Args:
            dataset_id: Dataset identifier
            violation_type: Type of violation (e.g., 'column_added', 'type_changed')

        Examples:
            >>> registry = MetricsRegistry()
            >>> pm = PipelineMetrics(registry=registry)
            >>> pm.record_schema_violation('nyc-311', 'column_added')
        """
        self.schema_violations_total.labels(dataset_id=dataset_id, violation_type=violation_type).inc()
        logger.warning(f"Recorded schema violation: {dataset_id} ({violation_type})")

    def record_validation_failure(self, dataset_id: str, rule_name: str) -> None:
        """Record data quality gate failure.

        Args:
            dataset_id: Dataset identifier
            rule_name: Name of validation rule that failed

        Examples:
            >>> registry = MetricsRegistry()
            >>> pm = PipelineMetrics(registry=registry)
            >>> pm.record_validation_failure('nyc-311', 'not_null_check')
        """
        self.validation_failures_total.labels(dataset_id=dataset_id, rule_name=rule_name).inc()
        logger.warning(f"Recorded validation failure: {dataset_id} ({rule_name})")

@dataclass
class DataQualityMetrics:
    """Data quality scorecard metrics.

    Tracks completeness, validity, uniqueness, and referential integrity.

    Attributes:
        registry: MetricsRegistry instance
        completeness_pct: Gauge for % non-null values
        validity_pct: Gauge for % valid values
        uniqueness_pct: Gauge for % unique values
        referential_integrity_pct: Gauge for % valid foreign keys
    """

    registry: MetricsRegistry

    def __post_init__(self) -> None:
        """Initialize data quality metrics."""
        self.completeness_pct = self.registry.register_gauge(
            "data_completeness_pct", "Percentage of non-null values per column"
        )

        self.validity_pct = self.registry.register_gauge(
            "data_validity_pct", "Percentage of values conforming to type/range per column"
        )

        self.uniqueness_pct = self.registry.register_gauge(
            "data_uniqueness_pct", "Percentage of unique values per column"
        )

        self.referential_integrity_pct = self.registry.register_gauge(
            "referential_integrity_pct", "Percentage of valid foreign keys"
        )

    def record_completeness(
        self, dataset_id: str, column_name: str, completeness_pct: float
    ) -> None:
        """Record column completeness.

        Args:
            dataset_id: Dataset identifier
            column_name: Column name
            completeness_pct: Completeness percentage (0-100)

        Examples:
            >>> registry = MetricsRegistry()
            >>> dq = DataQualityMetrics(registry=registry)
            >>> dq.record_completeness('nyc-311', 'created_date', 99.5)
        """
        self.completeness_pct.labels(dataset_id=dataset_id, column=column_name).set(completeness_pct)
        logger.debug(f"Recorded completeness: {dataset_id}.{column_name} = {completeness_pct:.2f}%")

    def record_validity(self, dataset_id: str, column_name: str, validity_pct: float) -> None:
        """Record column validity.

        Args:
            dataset_id: Dataset identifier
            column_name: Column name
            validity_pct: Validity percentage (0-100)

        Examples:
            >>> registry = MetricsRegistry()
            >>> dq = DataQualityMetrics(registry=registry)
            >>> dq.record_validity('nyc-311', 'latitude', 98.7)
        """
        self.validity_pct.labels(dataset_id=dataset_id, column=column_name).set(validity_pct)
        logger.debug(f"Recorded validity: {dataset_id}.{column_name} = {validity_pct:.2f}%")

    def record_uniqueness(self, dataset_id: str, column_name: str, uniqueness_pct: float) -> None:
        """Record column uniqueness.

        Args:
            dataset_id: Dataset identifier
            column_name: Column name
            uniqueness_pct: Uniqueness percentage (0-100)

        Examples:
            >>> registry = MetricsRegistry()
            >>> dq = DataQualityMetrics(registry=registry)
            >>> dq.record_uniqueness('nyc-311', 'unique_id', 100.0)
        """
        self.uniqueness_pct.labels(dataset_id=dataset_id, column=column_name).set(uniqueness_pct)
        logger.debug(f"Recorded uniqueness: {dataset_id}.{column_name} = {uniqueness_pct:.2f}%")

    def record_referential_integrity(
        self, dataset_id: str, fk_name: str, integrity_pct: float
    ) -> None:
        """Record foreign key referential integrity.

        Args:
            dataset_id: Dataset identifier
            fk_name: Foreign key column name
            integrity_pct: Integrity percentage (0-100)

        Examples:
            >>> registry = MetricsRegistry()
            >>> dq = DataQualityMetrics(registry=registry)
            >>> dq.record_referential_integrity('nyc-311', 'location_id', 99.8)
        """
        self.referential_integrity_pct.labels(dataset_id=dataset_id, fk=fk_name).set(integrity_pct)
        logger.debug(f"Recorded referential integrity: {dataset_id}.{fk_name} = {integrity_pct:.2f}%")

# Global metrics registry singleton
_global_registry: MetricsRegistry | None = None
_registry_lock = threading.Lock()

def get_global_registry() -> MetricsRegistry:
    """Get or create global metrics registry singleton.

    Returns:
        MetricsRegistry: Global metrics registry

    Examples:
        >>> registry = get_global_registry()
        >>> counter = registry.register_counter('test', 'Test')
        >>> counter.inc()
    """
    global _global_registry
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = MetricsRegistry()
    return _global_registry

def reset_global_registry() -> None:
    """Reset global metrics registry (useful for testing).

    Examples:
        >>> reset_global_registry()
        >>> registry = get_global_registry()
    """
    global _global_registry
    with _registry_lock:
        _global_registry = None
