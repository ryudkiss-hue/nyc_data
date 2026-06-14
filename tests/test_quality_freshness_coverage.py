"""Tests for quality.freshness module - Data freshness monitoring and SLA tracking."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from socrata_toolkit.quality.freshness import (
    AlertSeverity,
    DatasetFreshness,
    FreshnessAlert,
    FreshnessTracker,
)


class TestAlertSeverityEnum:
    """Tests for AlertSeverity enum."""

    def test_alert_severity_warning(self):
        """Test AlertSeverity.WARNING value."""
        assert AlertSeverity.WARNING.value == "warning"

    def test_alert_severity_critical(self):
        """Test AlertSeverity.CRITICAL value."""
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_severity_comparison(self):
        """Test AlertSeverity enum comparison."""
        assert AlertSeverity.WARNING != AlertSeverity.CRITICAL

class TestDatasetFreshness:
    """Tests for DatasetFreshness dataclass."""

    def test_dataset_freshness_creation(self):
        """Test creating a DatasetFreshness instance."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=now,
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.dataset_id == "nyc-311"
        assert df.dataset_name == "NYC 311 Service Requests"
        assert df.expected_update_frequency_hours == 24
        assert df.sla_threshold_hours == 48

    def test_dataset_freshness_is_fresh_recent_update(self):
        """Test is_fresh when dataset was recently updated."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=10),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.is_fresh() is True

    def test_dataset_freshness_is_fresh_just_within_sla(self):
        """Test is_fresh when dataset is just within SLA threshold."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=47),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.is_fresh() is True

    def test_dataset_freshness_is_fresh_just_outside_sla(self):
        """Test is_fresh when dataset just exceeded SLA threshold."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=49),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.is_fresh() is False

    def test_dataset_freshness_days_since_update_recent(self):
        """Test days_since_update for recently updated dataset."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=12),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        days = df.days_since_update()
        assert 0.4 < days < 0.6  # Should be ~0.5 days

    def test_dataset_freshness_days_since_update_old(self):
        """Test days_since_update for stale dataset."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(days=5),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        days = df.days_since_update()
        assert 4.9 < days < 5.1  # Should be ~5 days

    def test_dataset_freshness_sla_violated_not_violated(self):
        """Test sla_violated when SLA not exceeded."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=24),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.sla_violated() is False

    def test_dataset_freshness_sla_violated_is_violated(self):
        """Test sla_violated when SLA exceeded."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=72),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.sla_violated() is True

    def test_dataset_freshness_hours_until_sla_violation_positive(self):
        """Test hours_until_sla_violation when time remains."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=30),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        hours = df.hours_until_sla_violation()
        assert 17 < hours < 19  # Should be ~18 hours

    def test_dataset_freshness_hours_until_sla_violation_negative(self):
        """Test hours_until_sla_violation when SLA already violated."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=60),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        hours = df.hours_until_sla_violation()
        assert hours < 0  # Negative means already violated

    def test_dataset_freshness_hours_until_sla_violation_at_boundary(self):
        """Test hours_until_sla_violation at SLA boundary."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=48),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        hours = df.hours_until_sla_violation()
        assert -1 < hours < 1  # Should be ~0

class TestFreshnessAlert:
    """Tests for FreshnessAlert dataclass."""

    def test_freshness_alert_creation(self):
        """Test creating a FreshnessAlert instance."""
        now = datetime.now(timezone.utc)
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=now,
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        assert alert.alert_id == "alert-123"
        assert alert.dataset_id == "nyc-311"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.stale_hours == 72

    def test_freshness_alert_from_dataset_freshness_warning(self):
        """Test creating alert from fresh dataset (warning severity)."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=60),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        alert = FreshnessAlert.from_dataset_freshness(df)
        assert alert.dataset_id == "test"
        assert alert.severity == AlertSeverity.WARNING  # 60h stale, only 12h over SLA

    def test_freshness_alert_from_dataset_freshness_critical(self):
        """Test creating alert from stale dataset (critical severity)."""
        now = datetime.now(timezone.utc)
        df = DatasetFreshness(
            dataset_id="test",
            dataset_name="Test Dataset",
            last_updated_utc=now - timedelta(hours=100),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        alert = FreshnessAlert.from_dataset_freshness(df)
        assert alert.dataset_id == "test"
        assert alert.severity == AlertSeverity.CRITICAL  # 100h stale, 52h over SLA

    def test_freshness_alert_to_dict(self):
        """Test converting alert to dictionary."""
        now = datetime.now(timezone.utc)
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=now,
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        alert_dict = alert.to_dict()
        assert alert_dict["alert_id"] == "alert-123"
        assert alert_dict["dataset_id"] == "nyc-311"
        assert alert_dict["severity"] == "critical"
        assert "Z" in alert_dict["alert_time"]  # ISO 8601 with Z

    def test_freshness_alert_to_prometheus_metric(self):
        """Test converting alert to Prometheus metric format."""
        now = datetime.now(timezone.utc)
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=now,
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        metric = alert.to_prometheus_metric()
        assert "dataset_freshness_sla_violations_total" in metric
        assert "nyc-311" in metric
        assert "critical" in metric

    def test_freshness_alert_to_slack_json(self):
        """Test converting alert to Slack JSON payload."""
        now = datetime.now(timezone.utc)
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=now,
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        slack_msg = alert.to_slack_json()
        assert "blocks" in slack_msg
        assert len(slack_msg["blocks"]) > 0
        assert "NYC 311 Service Requests" in str(slack_msg)

    def test_freshness_alert_to_slack_json_warning_severity(self):
        """Test Slack JSON format with warning severity."""
        now = datetime.now(timezone.utc)
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=now,
            stale_hours=60,
            sla_threshold_hours=48,
            severity=AlertSeverity.WARNING,
        )
        slack_msg = alert.to_slack_json()
        # Warning should have yellow color, critical has red
        assert "blocks" in slack_msg
        assert len(slack_msg["blocks"]) > 0

    def test_freshness_alert_to_pagerduty(self):
        """Test converting alert to PagerDuty event format."""
        now = datetime.now(timezone.utc)
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=now,
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        pd_event = alert.to_pagerduty()
        assert "routing_key" in pd_event
        assert pd_event["event_action"] == "trigger"
        assert pd_event["payload"]["severity"] == "critical"
        assert "custom_details" in pd_event["payload"]

class TestFreshnessTracker:
    """Tests for FreshnessTracker class."""

    def test_freshness_tracker_initialization_in_memory(self):
        """Test initializing FreshnessTracker in in-memory mode."""
        tracker = FreshnessTracker()
        assert tracker.db_dsn is None
        assert tracker.table_name == "data_freshness_log"
        assert tracker._in_memory_store == {}

    def test_freshness_tracker_initialization_with_table_name(self):
        """Test initializing FreshnessTracker with custom table name."""
        tracker = FreshnessTracker(table_name="custom_table")
        assert tracker.table_name == "custom_table"

    def test_freshness_tracker_track_ingestion_basic(self):
        """Test tracking dataset ingestion."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="nyc-311",
            last_updated_utc=now,
            expected_frequency_hours=24,
            dataset_name="NYC 311 Service Requests",
        )
        assert "nyc-311" in tracker._in_memory_store

    def test_freshness_tracker_track_ingestion_default_sla(self):
        """Test that SLA defaults to 2x expected frequency."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now,
            expected_frequency_hours=24,
        )
        df = tracker._in_memory_store["test"]
        assert df.sla_threshold_hours == 48  # 2x24

    def test_freshness_tracker_track_ingestion_custom_sla(self):
        """Test tracking with custom SLA threshold."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now,
            expected_frequency_hours=24,
            sla_threshold_hours=72,
        )
        df = tracker._in_memory_store["test"]
        assert df.sla_threshold_hours == 72

    def test_freshness_tracker_track_ingestion_invalid_frequency(self):
        """Test error on negative frequency."""
        tracker = FreshnessTracker()
        with pytest.raises(ValueError):
            tracker.track_ingestion(
                dataset_id="test",
                last_updated_utc=datetime.now(timezone.utc),
                expected_frequency_hours=-1,
            )

    def test_freshness_tracker_get_freshness_status_fresh(self):
        """Test getting freshness status for fresh dataset."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now - timedelta(hours=10),
            expected_frequency_hours=24,
        )
        status = tracker.get_freshness_status("test")
        assert status["is_fresh"] is True
        assert status["sla_violated"] is False
        assert status["dataset_id"] == "test"

    def test_freshness_tracker_get_freshness_status_stale(self):
        """Test getting freshness status for stale dataset."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now - timedelta(hours=60),
            expected_frequency_hours=24,
        )
        status = tracker.get_freshness_status("test")
        assert status["is_fresh"] is False
        assert status["sla_violated"] is True

    def test_freshness_tracker_get_freshness_status_not_found(self):
        """Test error when querying non-existent dataset."""
        tracker = FreshnessTracker()
        with pytest.raises(KeyError):
            tracker.get_freshness_status("nonexistent")

    def test_freshness_tracker_get_freshness_status_includes_all_fields(self):
        """Test that freshness status includes all required fields."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now,
            expected_frequency_hours=24,
            dataset_name="Test Dataset",
        )
        status = tracker.get_freshness_status("test")
        assert "is_fresh" in status
        assert "sla_violated" in status
        assert "days_stale" in status
        assert "hours_stale" in status
        assert "sla_hours_allowed" in status
        assert "hours_until_violation" in status
        assert "dataset_name" in status
        assert "last_updated_utc" in status
        assert "expected_frequency_hours" in status

    def test_freshness_tracker_compute_freshness_sla_pct_no_data(self):
        """Test SLA computation with no datasets tracked."""
        tracker = FreshnessTracker()
        report = tracker.compute_freshness_sla_pct(period_days=30)
        assert report["compliance_pct"] == 100.0
        assert report["datasets_tracked"] == 0
        assert report["datasets_violated"] == 0

    def test_freshness_tracker_compute_freshness_sla_pct_all_compliant(self):
        """Test SLA computation when all datasets are compliant."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        for i in range(3):
            tracker.track_ingestion(
                dataset_id=f"dataset-{i}",
                last_updated_utc=now - timedelta(hours=10),
                expected_frequency_hours=24,
            )
        report = tracker.compute_freshness_sla_pct(period_days=30)
        assert report["compliance_pct"] == 100.0
        assert report["datasets_tracked"] == 3
        assert report["datasets_violated"] == 0

    def test_freshness_tracker_compute_freshness_sla_pct_partial_violation(self):
        """Test SLA computation with some datasets violated."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        # Add one fresh dataset
        tracker.track_ingestion(
            dataset_id="fresh",
            last_updated_utc=now - timedelta(hours=10),
            expected_frequency_hours=24,
        )
        # Add one stale dataset
        tracker.track_ingestion(
            dataset_id="stale",
            last_updated_utc=now - timedelta(hours=60),
            expected_frequency_hours=24,
        )
        report = tracker.compute_freshness_sla_pct(period_days=30)
        assert report["compliance_pct"] == 50.0
        assert report["datasets_tracked"] == 2
        assert report["datasets_violated"] == 1

    def test_freshness_tracker_get_stale_datasets_none(self):
        """Test getting stale datasets when none exist."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="fresh",
            last_updated_utc=now - timedelta(hours=10),
            expected_frequency_hours=24,
        )
        alerts = tracker.get_stale_datasets()
        assert len(alerts) == 0

    def test_freshness_tracker_get_stale_datasets_some(self):
        """Test getting alerts for stale datasets."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="fresh",
            last_updated_utc=now - timedelta(hours=10),
            expected_frequency_hours=24,
        )
        tracker.track_ingestion(
            dataset_id="stale",
            last_updated_utc=now - timedelta(hours=60),
            expected_frequency_hours=24,
        )
        alerts = tracker.get_stale_datasets()
        assert len(alerts) == 1
        assert alerts[0].dataset_id == "stale"

    def test_freshness_tracker_export_metrics_includes_compliance(self):
        """Test metrics export includes compliance percentage."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now,
            expected_frequency_hours=24,
        )
        metrics = tracker.export_metrics()
        assert "dataset_freshness_sla_compliance_pct" in metrics

    def test_freshness_tracker_export_metrics_includes_staleness(self):
        """Test metrics export includes dataset staleness."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now - timedelta(hours=12),
            expected_frequency_hours=24,
        )
        metrics = tracker.export_metrics()
        assert "dataset_hours_since_update" in metrics
        assert "test" in metrics

    def test_freshness_tracker_export_metrics_format(self):
        """Test Prometheus metrics format is valid."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        tracker.track_ingestion(
            dataset_id="dataset1",
            last_updated_utc=now - timedelta(hours=5),
            expected_frequency_hours=24,
        )
        tracker.track_ingestion(
            dataset_id="dataset2",
            last_updated_utc=now - timedelta(hours=25),
            expected_frequency_hours=24,
        )
        metrics = tracker.export_metrics()
        lines = metrics.split("\n")
        # Should have header, compliance metric, header, and dataset metrics
        assert len([line for line in lines if line.strip()]) >= 4
        assert all(line.startswith("#") or line.startswith("dataset_") for line in lines if line.strip())

    def test_freshness_tracker_multiple_datasets(self):
        """Test tracker with multiple datasets."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)
        datasets = [
            ("dataset-1", now - timedelta(hours=10)),
            ("dataset-2", now - timedelta(hours=30)),
            ("dataset-3", now - timedelta(hours=100)),
        ]
        for dataset_id, update_time in datasets:
            tracker.track_ingestion(
                dataset_id=dataset_id,
                last_updated_utc=update_time,
                expected_frequency_hours=24,
            )

        assert len(tracker._in_memory_store) == 3

        status1 = tracker.get_freshness_status("dataset-1")
        assert status1["is_fresh"] is True

        status3 = tracker.get_freshness_status("dataset-3")
        assert status3["is_fresh"] is False

    def test_freshness_tracker_update_existing_dataset(self):
        """Test updating freshness info for existing dataset."""
        tracker = FreshnessTracker()
        now = datetime.now(timezone.utc)

        # First tracking
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now - timedelta(hours=50),
            expected_frequency_hours=24,
        )
        first_status = tracker.get_freshness_status("test")
        assert first_status["sla_violated"] is True

        # Update with fresh timestamp
        tracker.track_ingestion(
            dataset_id="test",
            last_updated_utc=now,
            expected_frequency_hours=24,
        )
        second_status = tracker.get_freshness_status("test")
        assert second_status["sla_violated"] is False
