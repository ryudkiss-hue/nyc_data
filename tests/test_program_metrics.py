import pandas as pd
import pytest

from socrata_toolkit.analysis import (
    MetricsTracker,
    compute_program_dashboard,
)


def test_metrics_tracker_define_and_record():
    tracker = MetricsTracker()
    tracker.define(
        "test_metric",
        target=10.0,
        warning_threshold=15.0,
        critical_threshold=20.0,
        direction="lower_is_better",
    )
    snap = tracker.record("test_metric", 8.0)
    assert snap.status == "green"
    assert snap.value == 8.0

def test_metrics_tracker_yellow_status():
    tracker = MetricsTracker()
    tracker.define(
        "m",
        target=10.0,
        warning_threshold=15.0,
        critical_threshold=20.0,
        direction="lower_is_better",
    )
    snap = tracker.record("m", 17.0)
    assert snap.status == "yellow"

def test_metrics_tracker_red_status():
    tracker = MetricsTracker()
    tracker.define(
        "m",
        target=10.0,
        warning_threshold=15.0,
        critical_threshold=20.0,
        direction="lower_is_better",
    )
    snap = tracker.record("m", 25.0)
    assert snap.status == "red"

def test_metrics_tracker_higher_is_better():
    tracker = MetricsTracker()
    tracker.define(
        "m",
        target=90.0,
        warning_threshold=80.0,
        critical_threshold=70.0,
        direction="higher_is_better",
    )
    assert tracker.record("m", 95.0).status == "green"
    assert tracker.record("m", 85.0).status == "yellow"
    assert tracker.record("m", 60.0).status == "red"

def test_metrics_tracker_load_standard_kpis():
    tracker = MetricsTracker()
    tracker.load_standard_kpis()
    assert "defect_density" in tracker.definitions
    assert "throughput_velocity" in tracker.definitions
    assert len(tracker.definitions) >= 5

def test_metrics_tracker_dashboard():
    tracker = MetricsTracker()
    tracker.load_standard_kpis()
    tracker.record("defect_density", 1.5)
    tracker.record("throughput_velocity", 250.0)
    tracker.record("first_pass_yield", 92.0)
    dashboard = tracker.dashboard()
    assert dashboard.green_count >= 2
    assert dashboard.overall_health in ("green", "yellow", "red")

def test_metrics_tracker_budget_code():
    tracker = MetricsTracker()
    bc = tracker.add_budget_code(
        "PS-001", description="Personnel", category="personnel", allocated=100000, spent=60000
    )
    assert bc.remaining == 40000
    assert bc.pct_used == 60.0

def test_metrics_tracker_save_and_load(tmp_path):
    path = str(tmp_path / "metrics.json")
    tracker = MetricsTracker()
    tracker.define("m1", target=5.0, warning_threshold=8.0, critical_threshold=10.0)
    tracker.record("m1", 4.0)
    tracker.add_budget_code("BC-1", allocated=50000, spent=20000)
    tracker.save(path)

    tracker2 = MetricsTracker()
    tracker2.load(path)
    assert "m1" in tracker2.definitions
    assert len(tracker2.history["m1"]) == 1
    assert len(tracker2.budget_codes) == 1

def test_metrics_tracker_trend():
    tracker = MetricsTracker()
    tracker.define("m", target=5.0, warning_threshold=8.0, critical_threshold=10.0)
    for v in [3.0, 4.0, 5.0, 6.0, 7.0]:
        tracker.record("m", v)
    trend = tracker.trend("m", last_n=3)
    assert len(trend) == 3
    assert trend[-1].value == 7.0

def test_metrics_tracker_record_undefined_raises():
    tracker = MetricsTracker()
    with pytest.raises(KeyError):
        tracker.record("nonexistent", 5.0)

def test_compute_program_dashboard():
    df = pd.DataFrame(
        {
            "violations": [10, 15],
            "curb_miles": [2, 3],
            "built_linear_feet": [1000, 500],
            "days": [10, 5],
            "actual_spend": [100, 200],
            "planned_spend": [90, 210],
            "first_pass": [8, 10],
            "total_inspections": [10, 15],
            "rework_spend": [5, 10],
        }
    )
    dashboard = compute_program_dashboard(df)
    assert dashboard.overall_health in ("green", "yellow", "red")
    assert len(dashboard.metrics) >= 3
