"""Tests for data freshness monitoring and SLA compliance.

Tests cover freshness tracking, SLA computation, and alert generation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from socrata_toolkit.quality.freshness import (
    FreshnessTracker,
    DatasetFreshness,
    FreshnessAlert,
    AlertSeverity,
)


class TestDatasetFreshness:
    """Tests for DatasetFreshness class."""

    def test_is_fresh_within_sla(self):
        """Test dataset freshness check when within SLA."""
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=12),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.is_fresh() is True

    def test_is_fresh_exceeded_sla(self):
        """Test dataset freshness check when SLA exceeded."""
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=72),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.is_fresh() is False

    def test_days_since_update(self):
        """Test days since update calculation."""
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(days=5),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        days = df.days_since_update()
        assert 4.9 < days < 5.1  # Allow for timing variations

    def test_sla_violated(self):
        """Test SLA violation check."""
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=72),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        assert df.sla_violated() is True

    def test_hours_until_sla_violation(self):
        """Test hours remaining until SLA violation."""
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=30),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        hours_left = df.hours_until_sla_violation()
        assert 17 < hours_left < 19  # Allow for timing variations


class TestFreshnessAlert:
    """Tests for FreshnessAlert class."""

    def test_alert_from_dataset_freshness(self):
        """Test alert creation from dataset freshness."""
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=72),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        alert = FreshnessAlert.from_dataset_freshness(df)
        assert alert.dataset_id == "nyc-311"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.stale_hours > 70

    def test_alert_severity_warning(self):
        """Test alert severity for warning level."""
        df = DatasetFreshness(
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=50),
            expected_update_frequency_hours=24,
            sla_threshold_hours=48,
        )
        alert = FreshnessAlert.from_dataset_freshness(df)
        assert alert.severity == AlertSeverity.WARNING

    def test_alert_to_dict(self):
        """Test alert to dictionary conversion."""
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=datetime.now(timezone.utc),
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        alert_dict = alert.to_dict()
        assert alert_dict["dataset_id"] == "nyc-311"
        assert alert_dict["severity"] == "critical"
        assert "alert_time" in alert_dict

    def test_alert_to_prometheus_metric(self):
        """Test Prometheus metric format."""
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=datetime.now(timezone.utc),
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        metric = alert.to_prometheus_metric()
        assert "dataset_freshness_sla_violations_total" in metric
        assert "nyc-311" in metric
        assert "critical" in metric

    def test_alert_to_slack_json(self):
        """Test Slack message format."""
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=datetime.now(timezone.utc),
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        slack_msg = alert.to_slack_json()
        assert "blocks" in slack_msg
        assert len(slack_msg["blocks"]) > 0

    def test_alert_to_pagerduty(self):
        """Test PagerDuty event format."""
        alert = FreshnessAlert(
            alert_id="alert-123",
            dataset_id="nyc-311",
            dataset_name="NYC 311 Service Requests",
            alert_time=datetime.now(timezone.utc),
            stale_hours=72,
            sla_threshold_hours=48,
            severity=AlertSeverity.CRITICAL,
        )
        pd_event = alert.to_pagerduty()
        assert pd_event["event_action"] == "trigger"
        assert pd_event["payload"]["severity"] == "critical"
        assert "dataset_id" in pd_event["payload"]["custom_details"]


class TestFreshnessTracker:
    """Tests for FreshnessTracker class."""

    def test_tracker_in_memory_mode(self):
        """Test tracker in in-memory mode (no DB)."""
        tracker = FreshnessTracker()
        assert tracker.db_dsn is None

    def test_track_ingestion(self):
        """Test tracking ingestion event."""
        tracker = FreshnessTracker()
        tracker.track_ingestion(
            dataset_id="nyc-311",
            last_updated_utc=datetime.now(timezone.utc),
            expected_frequency_hours=24,
            dataset_name="NYC 311 Service Requests",
        )
        assert "nyc-311" in tracker._in_memory_store

    def test_track_ingestion_invalid_frequency(self):
        """Test tracking with invalid frequency."""
        tracker = FreshnessTracker()
        with pytest.raises(ValueError):
            tracker.track_ingestion(
                dataset_id="nyc-311",
                last_updated_utc=datetime.now(timezone.utc),
                expected_frequency_hours=-1,
            )

    def test_get_freshness_status(self):
        """Test getting freshness status."""
        tracker = FreshnessTracker()
        tracker.track_ingestion(
            dataset_id="nyc-311",
            last_updated_utc=datetime.now(timezone.utc),
            expected_frequency_hours=24,
        )
        status = tracker.get_freshness_status("nyc-311")
        assert status["is_fresh"] is True
        assert status["sla_violated"] is False
        assert "hours_stale" in status

    def test_get_freshness_status_not_found(self):
        """Test getting status for non-existent dataset."""
        tracker = FreshnessTracker()
        with pytest.raises(KeyError):
            tracker.get_freshness_status("nonexistent")

    def test_compute_freshness_sla_pct_empty(self):
        """Test SLA computation on empty tracker."""
        tracker = FreshnessTracker()
        sla_report = tracker.compute_freshness_sla_pct()
        assert sla_report["compliance_pct"] == 100.0
        assert sla_report["datasets_tracked"] == 0

    def test_compute_freshness_sla_pct_all_fresh(self):
        """Test SLA computation when all datasets are fresh."""
        tracker = FreshnessTracker()
        tracker.track_ingestion("nyc-311", datetime.now(timezone.utc), 24)
        tracker.track_ingestion("nyc-parking", datetime.now(timezone.utc), 24)
        sla_report = tracker.compute_freshness_sla_pct()
        assert sla_report["compliance_pct"] == 100.0
        assert sla_report["datasets_tracked"] == 2

    def test_compute_freshness_sla_pct_with_violations(self):
        """Test SLA computation with some violations."""
        tracker = FreshnessTracker()
        tracker.track_ingestion("fresh-dataset", datetime.now(timezone.utc), 24)
        tracker.track_ingestion("stale-dataset", datetime.now(timezone.utc) - timedelta(hours=72), 24)
        sla_report = tracker.compute_freshness_sla_pct()
        assert sla_report["datasets_tracked"] == 2
        assert sla_report["datasets_violated"] == 1
        assert sla_report["compliance_pct"] == 50.0

    def test_get_stale_datasets(self):
        """Test getting list of stale datasets."""
        tracker = FreshnessTracker()
        tracker.track_ingestion("fresh-dataset", datetime.now(timezone.utc), 24)
        tracker.track_ingestion("stale-dataset", datetime.now(timezone.utc) - timedelta(hours=72), 24)
        alerts = tracker.get_stale_datasets()
        assert len(alerts) == 1
        assert alerts[0].dataset_id == "stale-dataset"

    def test_export_metrics(self):
        """Test exporting metrics in Prometheus format."""
        tracker = FreshnessTracker()
        tracker.track_ingestion("nyc-311", datetime.now(timezone.utc), 24)
        metrics = tracker.export_metrics()
        assert "dataset_freshness_sla_compliance_pct" in metrics
        assert "dataset_hours_since_update" in metrics
        assert "nyc-311" in metrics

    def test_track_multiple_ingestions(self):
        """Test tracking multiple datasets."""
        tracker = FreshnessTracker()
        datasets = ["nyc-311", "nyc-parking", "nyc-buildings"]
        for dataset_id in datasets:
            tracker.track_ingestion(dataset_id, datetime.now(timezone.utc), 24)

        for dataset_id in datasets:
            status = tracker.get_freshness_status(dataset_id)
            assert status["is_fresh"] is True

    def test_custom_sla_threshold(self):
        """Test custom SLA threshold."""
        tracker = FreshnessTracker()
        tracker.track_ingestion(
            dataset_id="nyc-311",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=36),
            expected_frequency_hours=24,
            sla_threshold_hours=48,
        )
        status = tracker.get_freshness_status("nyc-311")
        assert status["is_fresh"] is True
        assert status["sla_violated"] is False

    def test_default_sla_threshold(self):
        """Test default SLA threshold (2x frequency)."""
        tracker = FreshnessTracker()
        tracker.track_ingestion(
            dataset_id="nyc-311",
            last_updated_utc=datetime.now(timezone.utc) - timedelta(hours=36),
            expected_frequency_hours=24,
            # No explicit sla_threshold_hours, should default to 48
        )
        status = tracker.get_freshness_status("nyc-311")
        assert status["sla_hours_allowed"] == 48
