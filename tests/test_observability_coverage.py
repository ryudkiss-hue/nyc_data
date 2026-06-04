"""Tests for the socrata_toolkit.observability package.

Covers MetricsCollector, LogStore, Tracer, HealthMonitor, SLATracker, and the
ObservabilityManager facade / singleton.
"""

from __future__ import annotations

import csv
import json

import pytest

from socrata_toolkit.observability import (
    SLA,
    ComponentHealth,
    HealthMonitor,
    LogEntry,
    LogStore,
    MetricsCollector,
    ObservabilityManager,
    SLATracker,
    Span,
    Tracer,
    get_observability_manager,
    reset_observability_manager,
)
from socrata_toolkit.observability.metrics import HistogramData

# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

class TestMetricsCollector:
    def test_increment_counter(self):
        m = MetricsCollector()
        m.increment("requests")
        m.increment("requests", 4)
        assert m.counter_count == 1

    def test_set_gauge(self):
        m = MetricsCollector()
        m.set_gauge("queue_depth", 12)
        assert m.gauge_count == 1

    def test_histogram_and_summary(self):
        m = MetricsCollector()
        for v in (10, 20, 30):
            m.observe_histogram("latency", v)
        m.observe_summary("size", 100)
        assert m.histogram_count == 1
        assert m.summary_count == 1

    def test_summary_dict(self):
        m = MetricsCollector()
        m.increment("a")
        m.set_gauge("b", 1)
        d = m.summary_dict()
        assert d["counter_count"] == 1
        assert d["gauge_count"] == 1
        assert "timestamp" in d

    def test_export_json(self):
        m = MetricsCollector()
        m.increment("a", 3)
        m.observe_histogram("h", 5)
        payload = json.loads(m.export_json())
        assert payload["counters"]["a"] == 3
        assert payload["histograms"]["h"]["count"] == 1

    def test_export_prometheus(self):
        m = MetricsCollector()
        m.increment("a", 2)
        m.set_gauge("g", 7)
        m.observe_histogram("h", 1)
        m.observe_summary("s", 4)
        out = m.export_prometheus()
        assert "# TYPE a counter" in out
        assert "a 2" in out
        assert "# TYPE g gauge" in out
        assert "h_count 1" in out
        assert "s_count 1" in out

    def test_export_prometheus_empty(self):
        assert MetricsCollector().export_prometheus() == ""

    def test_export_csv(self, tmp_path):
        m = MetricsCollector()
        m.increment("a")
        m.set_gauge("g", 1)
        m.observe_histogram("h", 2)
        m.observe_summary("s", 3)
        out = tmp_path / "m.csv"
        m.export_csv(out)
        rows = list(csv.reader(out.open()))
        assert rows[0] == ["metric_type", "name", "value"]
        assert len(rows) == 5

    def test_reset(self):
        m = MetricsCollector()
        m.increment("a")
        m.reset()
        assert m.counter_count == 0


class TestHistogramData:
    def test_mean_and_quantiles(self):
        h = HistogramData()
        for v in range(1, 101):
            h.observe(v)
        assert h.count == 100
        assert h.mean == pytest.approx(50.5)
        assert h.quantile(0.5) == pytest.approx(50, abs=1)
        assert h.quantile(0.95) == pytest.approx(95, abs=1)

    def test_empty_quantile(self):
        h = HistogramData()
        assert h.quantile(0.5) == 0.0
        assert h.mean == 0.0

    def test_quantile_bounds(self):
        h = HistogramData()
        for v in (1, 2, 3):
            h.observe(v)
        assert h.quantile(0) == 1
        assert h.quantile(1) == 3


# ---------------------------------------------------------------------------
# LogStore
# ---------------------------------------------------------------------------

class TestLogStore:
    def test_log_and_len(self):
        s = LogStore()
        s.log("hello")
        s.log("world", level="ERROR")
        assert len(s) == 2

    def test_query_by_level(self):
        s = LogStore()
        s.log("a", level="INFO")
        s.log("b", level="ERROR")
        assert len(s.query(level="ERROR")) == 1

    def test_query_by_correlation_and_dataset(self):
        s = LogStore()
        s.log("a", correlation_id="c1", dataset_id="d1")
        s.log("b", correlation_id="c2", dataset_id="d2")
        assert len(s.query(correlation_id="c1")) == 1
        assert len(s.query(dataset_id="d2")) == 1

    def test_ring_buffer_trims(self):
        s = LogStore(max_entries=3)
        for i in range(5):
            s.log(f"m{i}")
        assert len(s) == 3

    def test_log_entry_to_dict(self):
        e = LogEntry(message="x", level="WARN", context={"k": "v"})
        d = e.to_dict()
        assert d["message"] == "x"
        assert d["level"] == "WARN"
        assert d["context"] == {"k": "v"}

    def test_export_json(self, tmp_path):
        s = LogStore()
        s.log("a")
        out = tmp_path / "logs.json"
        s.export_json(out)
        assert len(json.loads(out.read_text())) == 1

    def test_export_csv(self, tmp_path):
        s = LogStore()
        s.log("a", level="INFO")
        out = tmp_path / "logs.csv"
        s.export_csv(out)
        rows = list(csv.reader(out.open()))
        assert rows[0][0] == "timestamp"
        assert len(rows) == 2

    def test_clear(self):
        s = LogStore()
        s.log("a")
        s.clear()
        assert len(s) == 0


# ---------------------------------------------------------------------------
# Tracer / Span
# ---------------------------------------------------------------------------

class TestTracer:
    def test_start_span_and_get_trace(self):
        t = Tracer()
        span = t.start_span("op")
        assert t.get_trace(span.trace_id) == [span]

    def test_child_span_same_trace(self):
        t = Tracer()
        parent = t.start_span("parent")
        child = t.start_span("child", trace_id=parent.trace_id, parent_span_id=parent.span_id)
        trace = t.get_trace(parent.trace_id)
        assert len(trace) == 2
        assert child.parent_span_id == parent.span_id

    def test_get_missing_trace(self):
        assert Tracer().get_trace("nope") is None

    def test_span_finish_ok(self):
        s = Span(operation_name="op", trace_id="t")
        s.finish()
        assert s.status == "ok"
        assert s.duration_ms is not None

    def test_span_finish_error(self):
        s = Span(operation_name="op", trace_id="t")
        s.finish(error_message="boom")
        assert s.status == "error"
        assert s.error_message == "boom"

    def test_span_running_duration_none(self):
        assert Span(operation_name="op", trace_id="t").duration_ms is None

    def test_span_set_attribute_and_to_dict(self):
        s = Span(operation_name="op", trace_id="t")
        s.set_attribute("k", "v")
        d = s.to_dict()
        assert d["attributes"]["k"] == "v"
        assert d["operation_name"] == "op"

    def test_all_spans(self):
        t = Tracer()
        t.start_span("a")
        t.start_span("b")
        assert len(t.all_spans()) == 2

    def test_export_jaeger(self):
        t = Tracer()
        t.start_span("a")
        data = json.loads(t.export_jaeger())
        assert "data" in data
        assert len(data["data"]) == 1

    def test_clear(self):
        t = Tracer()
        t.start_span("a")
        t.clear()
        assert t.all_spans() == []


# ---------------------------------------------------------------------------
# HealthMonitor
# ---------------------------------------------------------------------------

class TestHealthMonitor:
    def test_all_healthy(self):
        h = HealthMonitor()
        h.register("db", lambda: True)
        status = h.health_status()
        assert status["status"] == "HEALTHY"
        assert status["is_ready"] is True

    def test_unhealthy_component(self):
        h = HealthMonitor()
        h.register("db", lambda: False)
        status = h.health_status()
        assert status["status"] == "UNHEALTHY"
        assert status["is_ready"] is False
        assert status["unhealthy_count"] == 1

    def test_degraded_via_tuple(self):
        h = HealthMonitor()
        h.register("cache", lambda: ("DEGRADED", "slow"))
        status = h.health_status()
        assert status["status"] == "DEGRADED"
        assert status["degraded_count"] == 1

    def test_check_raising_is_unhealthy(self):
        h = HealthMonitor()
        def _boom():
            raise RuntimeError("down")
        h.register("svc", _boom)
        status = h.health_status()
        assert status["status"] == "UNHEALTHY"
        assert "down" in status["components"][0]["message"]

    def test_string_result(self):
        h = HealthMonitor()
        h.register("svc", lambda: "all good")
        status = h.health_status()
        assert status["status"] == "HEALTHY"

    def test_readiness_status(self):
        h = HealthMonitor()
        h.register("db", lambda: True)
        r = h.readiness_status()
        assert r["ready"] is True
        assert "components" in r

    def test_component_health_to_dict(self):
        c = ComponentHealth(name="x", status="HEALTHY", message="ok", duration_ms=1.5)
        d = c.to_dict()
        assert d["name"] == "x"
        assert d["duration_ms"] == 1.5


# ---------------------------------------------------------------------------
# SLATracker
# ---------------------------------------------------------------------------

class TestSLATracker:
    def test_passing_lte(self):
        sla = SLA(name="latency", target=100, actual=80, comparison="lte")
        assert sla.passing is True

    def test_failing_lte(self):
        sla = SLA(name="latency", target=100, actual=120, comparison="lte")
        assert sla.passing is False

    def test_passing_gte(self):
        sla = SLA(name="uptime", target=99.0, actual=99.5, comparison="gte")
        assert sla.passing is True

    def test_report_all_passing(self):
        t = SLATracker()
        t.register(SLA(name="a", target=100, actual=50))
        report = t.report()
        assert report["total_slas"] == 1
        assert report["passing_slas"] == 1
        assert report["compliance_percent"] == 100.0
        assert report["trend"] == "healthy"

    def test_report_with_violations(self):
        t = SLATracker()
        t.register(SLA(name="a", target=10, actual=50, severity="high"))
        t.register(SLA(name="b", target=100, actual=50))
        report = t.report()
        assert report["failing_slas"] == 1
        assert report["compliance_percent"] == 50.0
        assert report["trend"] == "at_risk"
        assert report["violations"][0]["sla_name"] == "a"

    def test_report_empty(self):
        report = SLATracker().report()
        assert report["total_slas"] == 0
        assert report["compliance_percent"] == 100.0

    def test_update(self):
        t = SLATracker()
        t.register(SLA(name="a", target=100, actual=50))
        t.update("a", 150)
        assert t.report()["failing_slas"] == 1

    def test_watch_trend(self):
        t = SLATracker()
        # 9 passing, 1 failing -> 90% -> watch
        for i in range(9):
            t.register(SLA(name=f"ok{i}", target=100, actual=10))
        t.register(SLA(name="bad", target=10, actual=99))
        assert t.report()["trend"] == "watch"


# ---------------------------------------------------------------------------
# ObservabilityManager + singleton
# ---------------------------------------------------------------------------

class TestObservabilityManager:
    def test_facade_components(self):
        m = ObservabilityManager()
        assert isinstance(m.get_metrics(), MetricsCollector)
        assert isinstance(m.get_logs(), LogStore)
        assert isinstance(m.get_tracer(), Tracer)
        assert isinstance(m.get_health(), HealthMonitor)
        assert isinstance(m.get_sla(), SLATracker)

    def test_health_and_readiness(self):
        m = ObservabilityManager()
        assert m.health_status()["is_ready"] is True
        assert m.readiness_status()["ready"] is True

    def test_metrics_summary_and_exports(self):
        m = ObservabilityManager()
        m.get_metrics().increment("a")
        assert m.metrics_summary()["counter_count"] == 1
        assert "a" in m.export_metrics_prometheus()
        assert "counters" in m.export_metrics_json()

    def test_query_and_export_logs(self, tmp_path):
        m = ObservabilityManager()
        m.get_logs().log("hi", level="ERROR")
        assert len(m.query_logs(level="ERROR")) == 1
        m.export_logs_json(tmp_path / "l.json")
        m.export_logs_csv(tmp_path / "l.csv")
        assert (tmp_path / "l.json").exists()
        assert (tmp_path / "l.csv").exists()

    def test_traces(self):
        m = ObservabilityManager()
        span = m.get_tracer().start_span("op")
        assert m.get_trace(span.trace_id) is not None
        assert "data" in m.export_traces_jaeger()

    def test_sla_report(self):
        m = ObservabilityManager()
        m.get_sla().register(SLA(name="a", target=100, actual=10))
        assert m.sla_report()["total_slas"] == 1

    def test_singleton(self):
        reset_observability_manager()
        a = get_observability_manager()
        b = get_observability_manager()
        assert a is b
        reset_observability_manager()
        c = get_observability_manager()
        assert c is not a
