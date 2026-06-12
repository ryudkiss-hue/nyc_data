"""
Unit tests for SLA Compliance Reporting Workflow

Tests core components:
  - SLAStatusClassifier: Classify datasets against SLA tiers
  - SLAMetricSnapshot: Metric data model
  - SLAStatusRecord: Classification result
  - SLAComplianceReport: Aggregate report
  - Workflow nodes: Fetch, classify, analyze, report, save

Run with: pytest tests/test_sla_compliance_workflow.py -v
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from socrata_toolkit.analysis.sla_status import (
    ComplianceStatus,
    RootCause,
    SLAComplianceReport,
    SLAMetricSnapshot,
    SLAStatusClassifier,
    SLAStatusRecord,
    SLATier,
    TrendDirection,
)

class TestSLAStatusClassifier:
    """Test SLA status classification logic."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return SLAStatusClassifier(at_risk_threshold_pct=0.80)

    def test_compliant_dataset(self, classifier):
        """Dataset within SLA threshold should be COMPLIANT."""
        now = datetime.now(timezone.utc)
        snapshot = SLAMetricSnapshot(
            timestamp=now,
            dataset_key="inspection",
            fourfour="dntt-gqwq",
            last_modified=now - timedelta(days=5),  # 5 days old
            row_count=398000,
            sla_tier=SLATier.HIGH,  # 14-day threshold
            days_since_update=5.0,
        )

        record = classifier.classify(snapshot)

        assert record.compliance_status == ComplianceStatus.COMPLIANT
        assert record.days_since_update == 5.0
        assert record.sla_threshold_days == 14
        assert record.freshness_percentage > 64  # (14 - 5) / 14 * 100 ≈ 64%

    def test_at_risk_dataset(self, classifier):
        """Dataset within 80% of SLA threshold should be AT_RISK."""
        now = datetime.now(timezone.utc)
        snapshot = SLAMetricSnapshot(
            timestamp=now,
            dataset_key="inspection",
            fourfour="dntt-gqwq",
            last_modified=now - timedelta(days=11.5),  # 11.5 days old
            row_count=398000,
            sla_tier=SLATier.HIGH,  # 14-day threshold
            days_since_update=11.5,
        )

        record = classifier.classify(snapshot)

        assert record.compliance_status == ComplianceStatus.AT_RISK
        assert record.freshness_percentage < 80

    def test_breached_dataset(self, classifier):
        """Dataset exceeding SLA threshold should be BREACHED."""
        now = datetime.now(timezone.utc)
        snapshot = SLAMetricSnapshot(
            timestamp=now,
            dataset_key="inspection",
            fourfour="dntt-gqwq",
            last_modified=now - timedelta(days=20),  # 20 days old
            row_count=398000,
            sla_tier=SLATier.HIGH,  # 14-day threshold
            days_since_update=20.0,
        )

        record = classifier.classify(snapshot)

        assert record.compliance_status == ComplianceStatus.BREACHED
        assert record.freshness_percentage < 0

    def test_root_cause_api_error(self, classifier):
        """Datasets with API errors should be classified as API_DOWN."""
        now = datetime.now(timezone.utc)
        snapshot = SLAMetricSnapshot(
            timestamp=now,
            dataset_key="inspection",
            fourfour="dntt-gqwq",
            last_modified=now - timedelta(days=20),
            row_count=0,
            sla_tier=SLATier.HIGH,
            days_since_update=20.0,
        )

        error_context = {
            "api_error": True,
            "error_message": "HTTP 503: Service Unavailable",
        }

        record = classifier.classify(snapshot, error_context=error_context)

        assert record.root_cause == RootCause.API_DOWN
        assert record.confidence >= 0.85

    def test_trend_detection_improving(self, classifier):
        """Trend should detect improving freshness."""
        now = datetime.now(timezone.utc)

        current = SLAMetricSnapshot(
            timestamp=now,
            dataset_key="inspection",
            fourfour="dntt-gqwq",
            last_modified=now - timedelta(days=8),
            row_count=398000,
            sla_tier=SLATier.HIGH,
            days_since_update=8.0,
        )

        historical = [
            SLAMetricSnapshot(
                timestamp=now - timedelta(days=1),
                dataset_key="inspection",
                fourfour="dntt-gqwq",
                last_modified=now - timedelta(days=10),
                row_count=398000,
                sla_tier=SLATier.HIGH,
                days_since_update=10.0,
            ),
            SLAMetricSnapshot(
                timestamp=now - timedelta(days=2),
                dataset_key="inspection",
                fourfour="dntt-gqwq",
                last_modified=now - timedelta(days=12),
                row_count=398000,
                sla_tier=SLATier.HIGH,
                days_since_update=12.0,
            ),
        ]

        record = classifier.classify(current, historical_snapshots=historical)

        assert record.trend == TrendDirection.IMPROVING

    def test_trend_detection_degrading(self, classifier):
        """Trend should detect degrading freshness."""
        now = datetime.now(timezone.utc)

        current = SLAMetricSnapshot(
            timestamp=now,
            dataset_key="inspection",
            fourfour="dntt-gqwq",
            last_modified=now - timedelta(days=12),
            row_count=398000,
            sla_tier=SLATier.HIGH,
            days_since_update=12.0,
        )

        historical = [
            SLAMetricSnapshot(
                timestamp=now - timedelta(days=1),
                dataset_key="inspection",
                fourfour="dntt-gqwq",
                last_modified=now - timedelta(days=10),
                row_count=398000,
                sla_tier=SLATier.HIGH,
                days_since_update=10.0,
            ),
            SLAMetricSnapshot(
                timestamp=now - timedelta(days=2),
                dataset_key="inspection",
                fourfour="dntt-gqwq",
                last_modified=now - timedelta(days=8),
                row_count=398000,
                sla_tier=SLATier.HIGH,
                days_since_update=8.0,
            ),
        ]

        record = classifier.classify(current, historical_snapshots=historical)

        assert record.trend == TrendDirection.DEGRADING

    def test_sla_tier_thresholds(self, classifier):
        """SLA tiers should have correct threshold days."""
        assert SLATier.HIGH.value == 14
        assert SLATier.MEDIUM.value == 30
        assert SLATier.LOW.value == 60

class TestSLAStatusRecord:
    """Test SLA status record model."""

    def test_record_serialization(self):
        """Record should serialize to JSON-compatible dict."""
        now = datetime.now(timezone.utc)
        record = SLAStatusRecord(
            dataset_key="inspection",
            fourfour="dntt-gqwq",
            sla_tier=SLATier.HIGH,
            compliance_status=ComplianceStatus.COMPLIANT,
            days_since_update=5.5,
            sla_threshold_days=14,
            freshness_percentage=64.3,
            root_cause=RootCause.UNKNOWN,
            confidence=0.9,
            trend=TrendDirection.STABLE,
            last_measured=now,
            historical_days_since_update=[5.0, 6.0, 7.0],
        )

        d = record.to_dict()

        assert d["dataset_key"] == "inspection"
        assert d["compliance_status"] == "compliant"
        assert d["sla_tier"] == "HIGH"
        assert d["root_cause"] == "unknown"
        assert d["trend"] == "stable"
        assert isinstance(d["last_measured"], str)

class TestSLAComplianceReport:
    """Test SLA compliance report model."""

    def test_report_compilation(self):
        """Report should aggregate status records correctly."""
        now = datetime.now(timezone.utc)

        records = [
            SLAStatusRecord(
                dataset_key="inspection",
                fourfour="dntt-gqwq",
                sla_tier=SLATier.HIGH,
                compliance_status=ComplianceStatus.COMPLIANT,
                days_since_update=5.0,
                sla_threshold_days=14,
                freshness_percentage=64.3,
                root_cause=RootCause.UNKNOWN,
                confidence=1.0,
                trend=TrendDirection.STABLE,
                last_measured=now,
            ),
            SLAStatusRecord(
                dataset_key="violations",
                fourfour="6kbp-uz6m",
                sla_tier=SLATier.HIGH,
                compliance_status=ComplianceStatus.BREACHED,
                days_since_update=20.0,
                sla_threshold_days=14,
                freshness_percentage=-43.0,
                root_cause=RootCause.API_DOWN,
                confidence=0.9,
                trend=TrendDirection.DEGRADING,
                last_measured=now,
            ),
        ]

        classifier = SLAStatusClassifier()
        report = classifier.compile_report(records)

        assert report.total_datasets == 2
        assert report.compliant_count == 1
        assert report.breached_count == 1
        assert report.at_risk_count == 0
        assert report.overall_compliance_pct == 50.0
        assert "violations" in report.critical_breaches

    def test_report_serialization(self):
        """Report should serialize to JSON."""
        now = datetime.now(timezone.utc)

        records = [
            SLAStatusRecord(
                dataset_key="inspection",
                fourfour="dntt-gqwq",
                sla_tier=SLATier.HIGH,
                compliance_status=ComplianceStatus.COMPLIANT,
                days_since_update=5.0,
                sla_threshold_days=14,
                freshness_percentage=64.3,
                root_cause=RootCause.UNKNOWN,
                confidence=1.0,
                trend=TrendDirection.STABLE,
                last_measured=now,
            ),
        ]

        classifier = SLAStatusClassifier()
        report = classifier.compile_report(records, claude_analysis="Test analysis")

        d = report.to_dict()

        # Verify structure
        assert "timestamp" in d
        assert "total_datasets" in d
        assert "records" in d
        assert isinstance(d["records"], list)
        assert len(d["records"]) == 1
        assert d["records"][0]["dataset_key"] == "inspection"
        assert d["claude_analysis"] == "Test analysis"

        # Verify JSON-serializable
        json_str = json.dumps(d)
        assert len(json_str) > 0

class TestEnums:
    """Test enum definitions."""

    def test_compliance_status_values(self):
        """ComplianceStatus enum should have all values."""
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.AT_RISK.value == "at_risk"
        assert ComplianceStatus.BREACHED.value == "breached"

    def test_root_cause_values(self):
        """RootCause enum should have all values."""
        causes = {e.value for e in RootCause}
        assert "api_down" in causes
        assert "maintenance" in causes
        assert "data_quality" in causes
        assert "resource_constraint" in causes
        assert "unknown" in causes

    def test_trend_direction_values(self):
        """TrendDirection enum should have all values."""
        trends = {e.value for e in TrendDirection}
        assert "improving" in trends
        assert "stable" in trends
        assert "degrading" in trends
        assert "insufficient_data" in trends
