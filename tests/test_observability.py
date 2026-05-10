"""Comprehensive tests for observability stack.

Tests cover:
- Structured logging with correlation IDs
- Metrics collection (counters, gauges, histograms, summaries)
- Distributed tracing
- Health checks
- SLA tracking
- Integration scenarios
"""

from __future__ import annotations

import json
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.observability_logging import (
    CircularLogBuffer,
    LogAggregator,
    LogContext,
    LogRecord,
    StructuredLogger,
)
from socrata_toolkit.observability_metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    Summary,
)
from socrata_toolkit.observability_tracing import (
    ContextPropagator,
    Span,
    SpanEvent,
    SpanStatus,
    TracingContext,
    parse_traceparent,
    inject_traceparent,
    traced_operation,
)
from socrata_toolkit.observability_health import (
    ComponentHealth,
    HealthChecker,
    HealthReport,
    HealthStatus,
)
from socrata_toolkit.observability_sla import (
    SLADefinition,
    SLAReport,
    SLATracker,
    SLAViolation,
    Severity,
)
from socrata_toolkit.observability_integration import ObservabilityManager


class TestStructuredLogging:
    """Tests for structured logging module."""

    def test_log_record_creation(self):
        """Test LogRecord creation and serialization."""
        record = LogRecord(
            timestamp="2025-01-01T00:00:00Z",
            level="INFO",
            logger_name="test",
            correlation_id="req-123",
            message="Test message",
            context={"dataset_id": "nyc-311"},
        )
        assert record.level == "INFO"
        assert record.correlation_id == "req-123"
        
        data = record.to_dict()
        assert data["message"] == "Test message"
        assert data["context"]["dataset_id"] == "nyc-311"
        
        json_str = record.to_json()
        assert json.loads(json_str)["level"] == "INFO"

    def test_log_context_propagation(self):
        """Test LogContext creates and maintains correlation IDs."""
        with LogContext(dataset_id="test-1") as ctx:
            current = LogContext.get_current()
            assert current["dataset_id"] == "test-1"
            assert current["correlation_id"]

    def test_log_context_nesting(self):
        """Test nested log contexts."""
        with LogContext(dataset_id="parent"):
            parent_ctx = LogContext.get_current()
            
            with LogContext(node_id="child"):
                child_ctx = LogContext.get_current()
                assert child_ctx["dataset_id"] == "parent"
                assert child_ctx["node_id"] == "child"
            
            # Back to parent
            post_ctx = LogContext.get_current()
            assert post_ctx["dataset_id"] == "parent"
            assert "node_id" not in post_ctx

    def test_structured_logger_json_output(self):
        """Test StructuredLogger produces JSON output."""
        logger = StructuredLogger(__name__)
        with LogContext(dataset_id="test"):
            logger.info("Test message", extra={"count": 100})

    def test_circular_log_buffer(self):
        """Test CircularLogBuffer limits size."""
        buffer = CircularLogBuffer(max_size=5)
        
        for i in range(10):
            record = LogRecord(
                timestamp="2025-01-01T00:00:00Z",
                level="INFO",
                logger_name="test",
                correlation_id=str(uuid.uuid4()),
                message=f"Message {i}",
            )
            buffer.append(record)
        
        assert buffer.size() == 5

    def test_log_buffer_filtering(self):
        """Test log buffer filtering."""
        buffer = CircularLogBuffer()
        
        for i in range(5):
            record = LogRecord(
                timestamp="2025-01-01T00:00:00Z",
                level="ERROR" if i % 2 == 0 else "INFO",
                logger_name="test",
                correlation_id="req-123",
                message=f"Message {i}",
            )
            buffer.append(record)
        
        errors = buffer.filter_by_level("ERROR")
        assert len(errors) == 3
        
        by_corr = buffer.filter_by_correlation_id("req-123")
        assert len(by_corr) == 5

    def test_log_aggregator_export(self):
        """Test LogAggregator export functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            aggregator = LogAggregator(log_dir=Path(tmpdir))
            
            record = LogRecord(
                timestamp="2025-01-01T00:00:00Z",
                level="INFO",
                logger_name="test",
                correlation_id="req-123",
                message="Test",
            )
            aggregator.append(record)
            
            export_file = Path(tmpdir) / "export.json"
            aggregator.export_json(export_file)
            assert export_file.exists()


class TestMetricsCollection:
    """Tests for metrics collection module."""

    def test_counter_increment(self):
        """Test counter increment."""
        counter = Counter("test_counter")
        counter.inc(5)
        assert counter.value() == 5
        counter.inc(3)
        assert counter.value() == 8

    def test_counter_with_labels(self):
        """Test counter with labels."""
        counter = Counter("requests")
        counter.inc(1, labels={"method": "GET"})
        counter.inc(1, labels={"method": "POST"})
        
        get_count = counter.value(labels={"method": "GET"})
        post_count = counter.value(labels={"method": "POST"})
        assert get_count == 1
        assert post_count == 1

    def test_gauge_operations(self):
        """Test gauge set, inc, dec."""
        gauge = Gauge("temperature")
        gauge.set(72.5)
        assert gauge.value() == 72.5
        gauge.inc(2)
        assert gauge.value() == 74.5
        gauge.dec(1)
        assert gauge.value() == 73.5

    def test_histogram_percentiles(self):
        """Test histogram percentile calculation."""
        hist = Histogram("latency")
        values = [1, 2, 3, 4, 5, 100, 200, 300, 400, 500]
        for v in values:
            hist.observe(v)
        
        assert hist.count() == 10
        assert hist.sum() == sum(values)
        assert hist.percentile(50) > 0

    def test_summary_statistics(self):
        """Test summary statistics."""
        summary = Summary("request_time")
        for i in range(100):
            summary.observe(float(i))
        
        assert summary.count() == 100
        assert summary.sum() == sum(range(100))

    def test_metrics_collector(self):
        """Test MetricsCollector."""
        collector = MetricsCollector()
        
        collector.counter("requests", 100)
        collector.gauge("active_tasks", 5)
        collector.histogram("latency_ms", 234.5)
        collector.summary("duration_ms", 150)
        
        assert collector.get_counter("requests") == 100
        assert collector.get_gauge("active_tasks") == 5

    def test_metrics_export_prometheus(self):
        """Test Prometheus export format."""
        collector = MetricsCollector()
        collector.counter("test_counter", 42)
        
        prometheus = collector.export_prometheus()
        assert "test_counter" in prometheus
        assert "# TYPE test_counter counter" in prometheus

    def test_metrics_export_json(self):
        """Test JSON export format."""
        collector = MetricsCollector()
        collector.counter("test", 10)
        
        json_str = collector.export_json()
        data = json.loads(json_str)
        assert "counters" in data
        assert data["counters"]["test"]["values"]["__default__"] == 10


class TestDistributedTracing:
    """Tests for distributed tracing module."""

    def test_span_creation(self):
        """Test span creation."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            operation_name="test_op",
            start_time="2025-01-01T00:00:00Z",
        )
        assert span.operation_name == "test_op"
        assert span.status == "unset"

    def test_tracing_context_spans(self):
        """Test TracingContext span management."""
        tracer = TracingContext()
        span = tracer.start_span("operation")
        
        assert span.trace_id
        assert span.span_id
        
        tracer.end_span(span.span_id, status="ok")
        retrieved = tracer.get_span(span.span_id)
        assert retrieved.status == "ok"
        assert retrieved.duration_ms is not None

    def test_span_nesting(self):
        """Test nested spans."""
        tracer = TracingContext()
        parent = tracer.start_span("parent")
        child = tracer.start_span("child", parent_span_id=parent.span_id)
        
        assert child.parent_span_id == parent.span_id
        assert parent.trace_id == child.trace_id

    def test_span_events(self):
        """Test span events."""
        tracer = TracingContext()
        span = tracer.start_span("operation")
        
        tracer.add_event(span.span_id, "checkpoint_1", {"data": "value"})
        tracer.add_event(span.span_id, "checkpoint_2")
        
        retrieved = tracer.get_span(span.span_id)
        assert len(retrieved.events) == 2

    def test_trace_retrieval(self):
        """Test retrieving full trace."""
        tracer = TracingContext()
        trace_id = "trace-1"
        
        parent = tracer.start_span("parent", trace_id=trace_id)
        child = tracer.start_span("child", parent_span_id=parent.span_id)
        
        trace = tracer.get_trace(trace_id)
        assert len(trace) == 2

    def test_traceparent_parsing(self):
        """Test W3C traceparent header parsing."""
        header = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        parsed = parse_traceparent(header)
        
        assert parsed["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
        assert parsed["parent_id"] == "00f067aa0ba902b7"

    def test_traceparent_injection(self):
        """Test W3C traceparent header injection."""
        header = inject_traceparent("trace-1", "span-1")
        assert header.startswith("00-")
        assert "trace-1" in header
        assert "span-1" in header

    def test_context_propagator(self):
        """Test ContextPropagator."""
        tracer = TracingContext()
        span = tracer.start_span("operation")
        
        headers = ContextPropagator.inject_headers(tracer)
        assert "traceparent" in headers
        assert "x-b3-traceid" in headers

    def test_traced_operation_decorator(self):
        """Test @traced_operation decorator."""
        tracer_instance = TracingContext()
        
        @traced_operation(name="test_func")
        def test_func():
            return 42
        
        result = test_func()
        assert result == 42

    def test_traced_operation_error_handling(self):
        """Test @traced_operation with errors."""
        @traced_operation(name="failing_func")
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()


class TestHealthChecks:
    """Tests for health checking module."""

    def test_component_health_status(self):
        """Test ComponentHealth."""
        health = ComponentHealth(
            name="database",
            status="HEALTHY",
            message="Connected",
        )
        assert health.is_healthy()

    def test_health_report(self):
        """Test HealthReport."""
        component = ComponentHealth(
            name="db",
            status="HEALTHY",
        )
        report = HealthReport(
            status="HEALTHY",
            timestamp="2025-01-01T00:00:00Z",
            components=[component],
        )
        assert report.is_ready()
        assert report.is_healthy()

    def test_health_report_degraded(self):
        """Test HealthReport with degraded component."""
        component = ComponentHealth(
            name="disk",
            status="DEGRADED",
        )
        report = HealthReport(
            status="DEGRADED",
            timestamp="2025-01-01T00:00:00Z",
            components=[component],
        )
        assert report.is_ready()
        assert not report.is_healthy()

    def test_health_report_unhealthy(self):
        """Test HealthReport with unhealthy component."""
        component = ComponentHealth(
            name="database",
            status="UNHEALTHY",
        )
        report = HealthReport(
            status="UNHEALTHY",
            timestamp="2025-01-01T00:00:00Z",
            components=[component],
        )
        assert not report.is_ready()
        assert not report.is_healthy()

    def test_health_checker_registration(self):
        """Test registering custom health checks."""
        checker = HealthChecker()
        
        def custom_check() -> ComponentHealth:
            return ComponentHealth(
                name="custom",
                status="HEALTHY",
                message="All good",
            )
        
        checker.register_check("custom", custom_check)
        report = checker.check_health()
        
        custom_result = next(
            (c for c in report.components if c.name == "custom"),
            None,
        )
        assert custom_result is not None


class TestSLATracking:
    """Tests for SLA tracking module."""

    def test_sla_definition(self):
        """Test SLADefinition."""
        sla = SLADefinition(
            metric_name="latency_p99",
            target=5000,
            window="5m",
            severity="CRITICAL",
        )
        assert sla.target == 5000
        assert sla.severity == "CRITICAL"

    def test_sla_violation(self):
        """Test SLAViolation."""
        violation = SLAViolation(
            sla_name="latency",
            metric_name="p99",
            target=5000,
            actual=6000,
            violation_time="2025-01-01T00:00:00Z",
            window="5m",
            severity="CRITICAL",
        )
        assert violation.actual > violation.target

    def test_sla_tracker_add_sla(self):
        """Test adding SLAs."""
        tracker = SLATracker()
        tracker.add_sla("latency_p99", target=5000, window="5m")
        
        assert "latency_p99" in tracker._slas

    def test_sla_tracker_record_metric(self):
        """Test recording metrics."""
        tracker = SLATracker()
        tracker.add_sla("latency_p99", target=5000)
        
        tracker.record_metric("latency_p99", 4500)
        tracker.record_metric("latency_p99", 4600)
        
        assert len(tracker._metrics["latency_p99"]) == 2

    def test_sla_violation_detection(self):
        """Test SLA violation detection."""
        tracker = SLATracker()
        tracker.add_sla("latency_p99", target=5000, window="5m")
        
        # Record values above target
        for i in range(10):
            tracker.record_metric("latency_p99", 6000 + i)
        
        report = tracker.evaluate()
        assert report.failing_slas == 1

    def test_sla_compliance_calculation(self):
        """Test compliance percentage calculation."""
        tracker = SLATracker()
        tracker.add_sla("metric_1", target=100)
        tracker.add_sla("metric_2", target=100)
        
        tracker.record_metric("metric_1", 50)  # Pass
        tracker.record_metric("metric_2", 150)  # Fail
        
        report = tracker.evaluate()
        assert report.compliance_percent < 100

    def test_sla_alert_callback(self):
        """Test SLA alert callbacks."""
        tracker = SLATracker()
        tracker.add_sla("latency", target=1000)
        
        alerts_triggered = []
        
        def alert_callback(violation: SLAViolation):
            alerts_triggered.append(violation)
        
        tracker.register_alert_callback(alert_callback)
        
        # Trigger violation
        for i in range(10):
            tracker.record_metric("latency", 2000)
        
        tracker.evaluate()
        assert len(alerts_triggered) > 0

    def test_sla_report(self):
        """Test SLA report generation."""
        tracker = SLATracker()
        tracker.add_sla("metric", target=100, severity="HIGH")
        
        for i in range(10):
            tracker.record_metric("metric", 150)
        
        report = tracker.evaluate()
        assert report.total_slas == 1
        assert report.failing_slas == 1
        assert report.compliance_percent == 0.0


class TestObservabilityManager:
    """Tests for ObservabilityManager integration."""

    def test_manager_singleton(self):
        """Test ObservabilityManager is singleton."""
        manager1 = ObservabilityManager()
        manager2 = ObservabilityManager()
        
        assert manager1 is manager2

    def test_manager_get_logger(self):
        """Test getting logger from manager."""
        manager = ObservabilityManager()
        logger = manager.get_logger(__name__)
        
        assert isinstance(logger, StructuredLogger)

    def test_manager_get_metrics(self):
        """Test getting metrics from manager."""
        manager = ObservabilityManager()
        metrics = manager.get_metrics()
        
        assert isinstance(metrics, MetricsCollector)

    def test_manager_get_health(self):
        """Test getting health checker from manager."""
        manager = ObservabilityManager()
        checker = manager.get_health_checker()
        
        assert isinstance(checker, HealthChecker)

    def test_manager_configure_sla(self):
        """Test configuring SLA through manager."""
        manager = ObservabilityManager()
        manager.configure_sla("latency", target=5000)
        
        tracker = manager.get_sla_tracker()
        assert "latency" in tracker._slas

    def test_manager_health_status(self):
        """Test health status through manager."""
        manager = ObservabilityManager()
        status = manager.health_status()
        
        assert "status" in status
        assert "components" in status

    def test_manager_export_metrics(self):
        """Test exporting metrics through manager."""
        manager = ObservabilityManager()
        manager.get_metrics().counter("test", 42)
        
        prometheus = manager.export_metrics_prometheus()
        assert "test_counter" in prometheus or "test" in prometheus


class TestIntegration:
    """Integration tests across multiple components."""

    def test_end_to_end_pipeline_observability(self):
        """Test full observability pipeline."""
        manager = ObservabilityManager()
        manager.initialize()
        
        # Setup logging
        logger = manager.get_logger(__name__)
        
        # Setup metrics
        metrics = manager.get_metrics()
        
        # Setup tracing
        tracer = manager.get_tracing_context()
        
        # Setup SLAs
        manager.configure_sla("ingestion_latency", target=5000)
        
        # Simulate pipeline
        with manager.create_log_context(dataset_id="test-123"):
            logger.info("Starting pipeline")
            
            span = tracer.start_span("ingestion", attributes={"dataset": "test"})
            try:
                metrics.counter("records_ingested", 1000)
                metrics.histogram("latency_ms", 1234.5)
                tracer.add_event(span.span_id, "records_loaded")
                
                # Record SLA metric
                manager.get_sla_tracker().record_metric("ingestion_latency", 1234.5)
                
                tracer.end_span(span.span_id, status="ok")
                logger.info("Pipeline complete")
            except Exception as e:
                tracer.end_span(span.span_id, status="error", error_message=str(e))
                raise
        
        # Verify everything was recorded
        assert metrics.get_counter("records_ingested") > 0
        assert len(tracer.get_trace(span.trace_id)) > 0


class TestPerformance:
    """Performance tests for observability overhead."""

    def test_logging_overhead(self):
        """Test structured logging performance."""
        logger = StructuredLogger(__name__)
        
        start = time.time()
        for i in range(1000):
            logger.info("Test message", extra={"iteration": i})
        elapsed = (time.time() - start) * 1000  # milliseconds
        
        # Should be very fast (< 100ms for 1000 logs)
        assert elapsed < 100

    def test_metrics_overhead(self):
        """Test metrics collection performance."""
        collector = MetricsCollector()
        
        start = time.time()
        for i in range(1000):
            collector.counter("test", 1)
            collector.histogram("latency", float(i))
        elapsed = (time.time() - start) * 1000
        
        # Should be very fast
        assert elapsed < 100

    def test_tracing_overhead(self):
        """Test tracing performance."""
        tracer = TracingContext()
        
        start = time.time()
        for i in range(100):
            span = tracer.start_span(f"operation_{i}")
            tracer.end_span(span.span_id)
        elapsed = (time.time() - start) * 1000
        
        # Should be fast
        assert elapsed < 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
