"""Unit tests for dataset health classifier and workflow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from socrata_toolkit.analysis.dataset_health import (
    DatasetHealthClassifier,
    DatasetHealthMetrics,
    HealthStatus,
    Severity,
)


class TestDatasetHealthClassifier:
    """Test DatasetHealthClassifier."""

    @pytest.fixture
    def classifier(self):
        return DatasetHealthClassifier(sla_thresholds={"HIGH": 14, "MEDIUM": 30, "LOW": 60})

    def test_healthy_dataset(self, classifier):
        """Test classification of healthy dataset."""
        now = datetime.now(timezone.utc)
        metrics = DatasetHealthMetrics(
            key="violations",
            fourfour="6kbp-uz6m",
            row_count=312000,
            last_modified=now - timedelta(days=2),
            schema_snapshot={"id": "int64", "status": "object"},
            schema_baseline={"id": "int64", "status": "object"},
            is_accessible=True,
        )

        report = classifier.classify(metrics)

        assert report.status == HealthStatus.HEALTHY
        assert report.severity >= 70
        assert len(report.alerts) == 0
        assert report.row_count == 312000
        assert report.freshness_days == 2

    def test_stale_dataset(self, classifier):
        """Test classification of stale dataset."""
        now = datetime.now(timezone.utc)
        metrics = DatasetHealthMetrics(
            key="ramp_locations",
            fourfour="ufzp-rrqu",
            row_count=217000,
            last_modified=now - timedelta(days=100),
            schema_snapshot={"id": "int64"},
            schema_baseline={"id": "int64"},
            is_accessible=True,
        )

        report = classifier.classify(metrics)

        assert report.status == HealthStatus.STALE
        assert report.severity < 70
        assert len(report.alerts) > 0
        assert "stale" in report.alerts[0].lower()
        assert report.freshness_days == 100

    def test_empty_dataset(self, classifier):
        """Test classification of empty dataset."""
        metrics = DatasetHealthMetrics(
            key="capital_blocks",
            fourfour="jvk9-k4re",
            row_count=0,
            last_modified=None,
            schema_snapshot={},
            schema_baseline={},
            is_accessible=True,
        )

        report = classifier.classify(metrics)

        assert report.status == HealthStatus.EMPTY_OR_ERROR
        assert report.severity <= 20
        assert len(report.alerts) > 0
        assert report.row_count == 0

    def test_inaccessible_dataset(self, classifier):
        """Test classification of inaccessible dataset."""
        metrics = DatasetHealthMetrics(
            key="permit_stipulations",
            fourfour="gsgx-6efw",
            row_count=None,
            last_modified=None,
            schema_snapshot=None,
            schema_baseline=None,
            is_accessible=False,
            error_message="HTTP 403 Forbidden",
        )

        report = classifier.classify(metrics)

        assert report.status == HealthStatus.EMPTY_OR_ERROR
        assert report.severity <= 20
        assert "accessible" in report.alerts[0].lower()

    def test_schema_drift_detection(self, classifier):
        """Test schema drift detection."""
        now = datetime.now(timezone.utc)
        metrics = DatasetHealthMetrics(
            key="violations",
            fourfour="6kbp-uz6m",
            row_count=312000,
            last_modified=now - timedelta(days=5),
            schema_snapshot={
                "id": "int64",
                "status": "object",
                "new_field": "string",  # Added field
            },
            schema_baseline={
                "id": "int64",
                "status": "object",
            },
            is_accessible=True,
        )

        report = classifier.classify(metrics)

        # Should still be mostly healthy but note the changes
        assert report.schema_changes.get("added_columns") == ["new_field"]
        assert len(report.recommendations) > 0

    def test_schema_drift_type_change(self, classifier):
        """Test detection of type changes."""
        now = datetime.now(timezone.utc)
        metrics = DatasetHealthMetrics(
            key="violations",
            fourfour="6kbp-uz6m",
            row_count=312000,
            last_modified=now - timedelta(days=5),
            schema_snapshot={
                "id": "object",  # Changed from int64 to object
                "status": "object",
            },
            schema_baseline={
                "id": "int64",
                "status": "object",
            },
            is_accessible=True,
        )

        report = classifier.classify(metrics)

        changes = report.schema_changes.get("type_changes", [])
        assert len(changes) > 0
        assert any(c["column"] == "id" for c in changes)

    def test_severity_levels(self, classifier):
        """Test severity level assignment."""
        now = datetime.now(timezone.utc)

        # Critical severity
        metrics_critical = DatasetHealthMetrics(
            key="test_critical",
            fourfour="test-xxxx",
            row_count=0,
            last_modified=None,
            schema_snapshot={},
            schema_baseline={},
            is_accessible=True,
        )
        report_critical = classifier.classify(metrics_critical)
        assert report_critical.severity_level == Severity.CRITICAL
        assert report_critical.severity <= 20

        # High severity (stale)
        metrics_high = DatasetHealthMetrics(
            key="test_high",
            fourfour="test-yyyy",
            row_count=1000,
            last_modified=now - timedelta(days=60),
            schema_snapshot={"id": "int64"},
            schema_baseline={"id": "int64"},
            is_accessible=True,
        )
        report_high = classifier.classify(metrics_high)
        assert report_high.severity_level == Severity.HIGH
        assert 21 <= report_high.severity <= 50

        # Low severity (healthy)
        metrics_low = DatasetHealthMetrics(
            key="test_low",
            fourfour="test-zzzz",
            row_count=50000,
            last_modified=now - timedelta(days=1),
            schema_snapshot={"id": "int64"},
            schema_baseline={"id": "int64"},
            is_accessible=True,
        )
        report_low = classifier.classify(metrics_low)
        assert report_low.severity_level == Severity.LOW
        assert report_low.severity >= 71

    def test_classify_batch(self, classifier):
        """Test batch classification."""
        now = datetime.now(timezone.utc)
        metrics_list = [
            DatasetHealthMetrics(
                key="violations",
                fourfour="6kbp-uz6m",
                row_count=312000,
                last_modified=now - timedelta(days=2),
                schema_snapshot={"id": "int64"},
                schema_baseline={"id": "int64"},
                is_accessible=True,
            ),
            DatasetHealthMetrics(
                key="ramp_locations",
                fourfour="ufzp-rrqu",
                row_count=217000,
                last_modified=now - timedelta(days=100),
                schema_snapshot={"id": "int64"},
                schema_baseline={"id": "int64"},
                is_accessible=True,
            ),
        ]

        reports = classifier.classify_batch(metrics_list)

        assert len(reports) == 2
        assert reports[0].key == "violations"
        assert reports[1].key == "ramp_locations"

    def test_summarize(self, classifier):
        """Test report summarization."""
        now = datetime.now(timezone.utc)
        metrics_list = [
            DatasetHealthMetrics(
                key=f"dataset_{i}",
                fourfour=f"xxxx-{i:04d}",
                row_count=100000 if i % 2 == 0 else 0,
                last_modified=now - timedelta(days=2 if i % 2 == 0 else 100),
                schema_snapshot={"id": "int64"},
                schema_baseline={"id": "int64"},
                is_accessible=True if i % 3 != 0 else False,
            )
            for i in range(10)
        ]

        reports = classifier.classify_batch(metrics_list)
        summary = classifier.summarize(reports)

        assert summary["total"] == 10
        assert summary["healthy"] > 0
        assert summary["stale"] > 0
        assert summary["empty_or_error"] > 0
        assert len(summary["critical_alerts"]) > 0
        assert len(summary["needs_attention"]) > 0

    def test_report_to_dict(self, classifier):
        """Test report serialization to dict."""
        now = datetime.now(timezone.utc)
        metrics = DatasetHealthMetrics(
            key="violations",
            fourfour="6kbp-uz6m",
            row_count=312000,
            last_modified=now - timedelta(days=2),
            schema_snapshot={"id": "int64"},
            schema_baseline={"id": "int64"},
            is_accessible=True,
        )

        report = classifier.classify(metrics)
        report_dict = report.to_dict()

        assert isinstance(report_dict, dict)
        assert report_dict["key"] == "violations"
        assert report_dict["status"] == "healthy"
        assert isinstance(report_dict["severity"], int)
        assert report_dict["severity_level"] == "low"

class TestDatasetHealthMetrics:
    """Test DatasetHealthMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating metrics object."""
        now = datetime.now(timezone.utc)
        metrics = DatasetHealthMetrics(
            key="test",
            fourfour="test-1234",
            row_count=1000,
            last_modified=now,
            schema_snapshot={"col1": "int64"},
            schema_baseline={"col1": "int64"},
            is_accessible=True,
        )

        assert metrics.key == "test"
        assert metrics.fourfour == "test-1234"
        assert metrics.row_count == 1000
        assert metrics.is_accessible is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
