"""Tests for Prometheus metrics collection and export.

Tests cover metric registration, recording, and export formats.
"""

from socrata_toolkit.metrics import (
    DataQualityMetrics,
    MetricPoint,
    MetricsRegistry,
    PipelineMetrics,
    get_global_registry,
    reset_global_registry,
)


class TestMetricPoint:
    """Tests for MetricPoint class."""

    def test_metric_point_creation(self):
        """Test basic metric point creation."""
        point = MetricPoint(
            name="test_metric",
            value=42.0,
            labels={"dataset_id": "nyc-311"},
        )
        assert point.name == "test_metric"
        assert point.value == 42.0

    def test_metric_point_to_prometheus_line_no_labels(self):
        """Test Prometheus line format without labels."""
        point = MetricPoint(name="test_metric", value=42.0)
        line = point.to_prometheus_line()
        assert "test_metric 42.0" == line

    def test_metric_point_to_prometheus_line_with_labels(self):
        """Test Prometheus line format with labels."""
        point = MetricPoint(
            name="test_metric",
            value=42.0,
            labels={"dataset_id": "nyc-311", "status": "success"},
        )
        line = point.to_prometheus_line()
        assert "test_metric{" in line
        assert 'dataset_id="nyc-311"' in line


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_registry_initialization(self):
        """Test metrics registry initialization."""
        registry = MetricsRegistry(use_prometheus=False)
        assert registry.use_prometheus is False

    def test_register_counter(self):
        """Test registering a counter metric."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("test_total", "Test counter")
        assert counter is not None

    def test_register_gauge(self):
        """Test registering a gauge metric."""
        registry = MetricsRegistry(use_prometheus=False)
        gauge = registry.register_gauge("test_gauge", "Test gauge")
        assert gauge is not None

    def test_register_histogram(self):
        """Test registering a histogram metric."""
        registry = MetricsRegistry(use_prometheus=False)
        histogram = registry.register_histogram("test_histogram", "Test histogram")
        assert histogram is not None

    def test_counter_increment(self):
        """Test incrementing a counter."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("test_total", "Test counter")
        counter.inc(5)
        # Should not raise error

    def test_counter_with_labels(self):
        """Test counter with labels."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("test_total", "Test counter")
        labeled = counter.labels(dataset_id="nyc-311")
        labeled.inc(10)
        # Should not raise error

    def test_gauge_set_value(self):
        """Test setting gauge value."""
        registry = MetricsRegistry(use_prometheus=False)
        gauge = registry.register_gauge("test_gauge", "Test gauge")
        gauge.set(42.0)
        # Should not raise error

    def test_histogram_observe(self):
        """Test recording histogram observations."""
        registry = MetricsRegistry(use_prometheus=False)
        histogram = registry.register_histogram("test_histogram", "Test histogram")
        histogram.observe(0.5)
        histogram.observe(1.5)
        # Should not raise error

    def test_export_prometheus_format(self):
        """Test exporting metrics in Prometheus format."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("test_total", "Test counter")
        counter.inc(5)
        metrics_text = registry.export_prometheus()
        assert "test_total" in metrics_text

    def test_export_json_format(self):
        """Test exporting metrics as JSON."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("test_total", "Test counter")
        counter.inc(5)
        json_data = registry.export_json()
        assert isinstance(json_data, dict)


class TestPipelineMetrics:
    """Tests for PipelineMetrics class."""

    def test_pipeline_metrics_initialization(self):
        """Test pipeline metrics initialization."""
        registry = MetricsRegistry(use_prometheus=False)
        pm = PipelineMetrics(registry=registry)
        assert pm.registry is not None

    def test_record_ingestion_success(self):
        """Test recording successful ingestion."""
        registry = MetricsRegistry(use_prometheus=False)
        pm = PipelineMetrics(registry=registry)
        pm.record_ingestion_success("nyc-311", 1500, 2.5)
        # Should not raise error

    def test_record_ingestion_error(self):
        """Test recording ingestion error."""
        registry = MetricsRegistry(use_prometheus=False)
        pm = PipelineMetrics(registry=registry)
        pm.record_ingestion_error("nyc-311", "network")
        # Should not raise error

    def test_record_schema_violation(self):
        """Test recording schema violation."""
        registry = MetricsRegistry(use_prometheus=False)
        pm = PipelineMetrics(registry=registry)
        pm.record_schema_violation("nyc-311", "column_added")
        # Should not raise error

    def test_record_validation_failure(self):
        """Test recording validation failure."""
        registry = MetricsRegistry(use_prometheus=False)
        pm = PipelineMetrics(registry=registry)
        pm.record_validation_failure("nyc-311", "not_null_check")
        # Should not raise error

    def test_multiple_records(self):
        """Test recording multiple metrics."""
        registry = MetricsRegistry(use_prometheus=False)
        pm = PipelineMetrics(registry=registry)
        pm.record_ingestion_success("nyc-311", 1500, 2.5)
        pm.record_ingestion_success("nyc-311", 1200, 2.1)
        pm.record_ingestion_error("nyc-parking", "timeout")
        # Should track all records


class TestDataQualityMetrics:
    """Tests for DataQualityMetrics class."""

    def test_data_quality_metrics_initialization(self):
        """Test data quality metrics initialization."""
        registry = MetricsRegistry(use_prometheus=False)
        dq = DataQualityMetrics(registry=registry)
        assert dq.registry is not None

    def test_record_completeness(self):
        """Test recording completeness metric."""
        registry = MetricsRegistry(use_prometheus=False)
        dq = DataQualityMetrics(registry=registry)
        dq.record_completeness("nyc-311", "created_date", 99.5)
        # Should not raise error

    def test_record_validity(self):
        """Test recording validity metric."""
        registry = MetricsRegistry(use_prometheus=False)
        dq = DataQualityMetrics(registry=registry)
        dq.record_validity("nyc-311", "latitude", 98.7)
        # Should not raise error

    def test_record_uniqueness(self):
        """Test recording uniqueness metric."""
        registry = MetricsRegistry(use_prometheus=False)
        dq = DataQualityMetrics(registry=registry)
        dq.record_uniqueness("nyc-311", "unique_id", 100.0)
        # Should not raise error

    def test_record_referential_integrity(self):
        """Test recording referential integrity metric."""
        registry = MetricsRegistry(use_prometheus=False)
        dq = DataQualityMetrics(registry=registry)
        dq.record_referential_integrity("nyc-311", "location_id", 99.8)
        # Should not raise error

    def test_multiple_columns(self):
        """Test recording metrics for multiple columns."""
        registry = MetricsRegistry(use_prometheus=False)
        dq = DataQualityMetrics(registry=registry)
        dq.record_completeness("nyc-311", "col1", 99.0)
        dq.record_completeness("nyc-311", "col2", 98.5)
        dq.record_validity("nyc-311", "col1", 99.5)
        # Should track all metrics


class TestGlobalRegistry:
    """Tests for global registry singleton."""

    def test_get_global_registry(self):
        """Test getting global registry."""
        reset_global_registry()
        registry = get_global_registry()
        assert registry is not None

    def test_global_registry_singleton(self):
        """Test that global registry is a singleton."""
        reset_global_registry()
        reg1 = get_global_registry()
        reg2 = get_global_registry()
        assert reg1 is reg2

    def test_global_registry_usage(self):
        """Test using global registry."""
        reset_global_registry()
        registry = get_global_registry()
        counter = registry.register_counter("global_test", "Global test")
        counter.inc(10)
        # Should work without error


class TestMetricsIntegration:
    """Integration tests for metrics."""

    def test_pipeline_and_quality_metrics_together(self):
        """Test using pipeline and data quality metrics together."""
        registry = MetricsRegistry(use_prometheus=False)
        pm = PipelineMetrics(registry=registry)
        dq = DataQualityMetrics(registry=registry)

        # Record some metrics
        pm.record_ingestion_success("dataset1", 1000, 1.5)
        dq.record_completeness("dataset1", "column1", 99.0)

        # Export and verify
        metrics = registry.export_prometheus()
        assert len(metrics) > 0

    def test_export_multiple_metric_types(self):
        """Test exporting multiple metric types."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("counter", "Test counter")
        gauge = registry.register_gauge("gauge", "Test gauge")
        hist = registry.register_histogram("histogram", "Test histogram")

        counter.inc(5)
        gauge.set(42.0)
        hist.observe(1.5)

        json_data = registry.export_json()
        assert "metrics" in json_data or "prometheus_format" in json_data


class TestMetricsEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_zero_metrics(self):
        """Test exporting when no metrics recorded."""
        registry = MetricsRegistry(use_prometheus=False)
        metrics = registry.export_prometheus()
        assert isinstance(metrics, str)

    def test_large_value_metrics(self):
        """Test handling large metric values."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("large_total", "Large value")
        counter.inc(1_000_000_000)
        metrics = registry.export_prometheus()
        assert len(metrics) > 0

    def test_negative_gauge_value(self):
        """Test setting negative gauge values."""
        registry = MetricsRegistry(use_prometheus=False)
        gauge = registry.register_gauge("negative", "Negative gauge")
        gauge.set(-42.0)
        # Should not raise error

    def test_multiple_label_combinations(self):
        """Test counter with multiple label combinations."""
        registry = MetricsRegistry(use_prometheus=False)
        counter = registry.register_counter("labeled_total", "Labeled counter")

        counter.labels(dataset_id="nyc-311", status="success").inc(100)
        counter.labels(dataset_id="nyc-311", status="failure").inc(10)
        counter.labels(dataset_id="nyc-parking", status="success").inc(50)

        metrics = registry.export_prometheus()
        assert "nyc-311" in metrics
        assert "nyc-parking" in metrics

    def test_histogram_buckets(self):
        """Test histogram with custom buckets."""
        registry = MetricsRegistry(use_prometheus=False)
        hist = registry.register_histogram(
            "duration_seconds", "Duration", buckets=(0.1, 0.5, 1.0, 5.0)
        )
        hist.observe(0.25)
        hist.observe(0.75)
        hist.observe(2.5)
        # Should not raise error
