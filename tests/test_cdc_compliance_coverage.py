"""Comprehensive tests for cdc.compliance module."""
from __future__ import annotations
import pytest


from contextlib import contextmanager
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.cdc.compliance import (
    CDCReconciler,
    ComplianceCheckResult,
    ComplianceReport,
    ReconciliationResult,
)

# ---------------------------------------------------------------------------
# Dataclass tests — no DB required
# ---------------------------------------------------------------------------

class TestComplianceCheckResult:
    """Tests for ComplianceCheckResult dataclass."""

    def test_default_severity_is_info(self):
        result = ComplianceCheckResult(check_name="test_check", passed=True)
        assert result.severity == "info"

    def test_passed_true_with_no_issues(self):
        result = ComplianceCheckResult(check_name="audit_check", passed=True)
        assert result.passed is True
        assert result.issues == []

    def test_passed_false_with_issues(self):
        result = ComplianceCheckResult(
            check_name="count_check",
            passed=False,
            issues=["count mismatch"],
            severity="warning",
        )
        assert result.passed is False
        assert len(result.issues) == 1
        assert result.severity == "warning"

    def test_timestamp_is_set_automatically(self):
        result = ComplianceCheckResult(check_name="ts_check", passed=True)
        assert isinstance(result.timestamp, datetime)
        assert result.timestamp.tzinfo is not None

    def test_critical_severity_stored(self):
        result = ComplianceCheckResult(
            check_name="critical_check", passed=False, severity="critical"
        )
        assert result.severity == "critical"

class TestReconciliationResult:
    """Tests for ReconciliationResult dataclass."""

    def test_defaults_to_not_reconciled(self):
        result = ReconciliationResult(
            source_system="source_table",
            cdc_record_count=10,
            source_record_count=10,
        )
        assert result.reconciled is False

    def test_missing_and_extra_default_empty(self):
        result = ReconciliationResult(
            source_system="src",
            cdc_record_count=0,
            source_record_count=0,
        )
        assert result.missing_events == []
        assert result.extra_events == []
        assert result.timestamp_mismatches == []

    def test_reconciled_flag_can_be_set(self):
        result = ReconciliationResult(
            source_system="src",
            cdc_record_count=5,
            source_record_count=5,
            reconciled=True,
        )
        assert result.reconciled is True

class TestComplianceReport:
    """Tests for ComplianceReport dataclass."""

    def _make_report(self, status: str = "compliant") -> ComplianceReport:
        checks = [
            ComplianceCheckResult(check_name="c1", passed=True),
            ComplianceCheckResult(check_name="c2", passed=True),
        ]
        return ComplianceReport(
            report_date=datetime.now(timezone.utc),
            total_checks=2,
            passed_checks=2,
            failed_checks=0,
            checks=checks,
            overall_status=status,
            summary="2/2 checks passed. All checks passed.",
        )

    def test_report_attributes(self):
        report = self._make_report()
        assert report.total_checks == 2
        assert report.passed_checks == 2
        assert report.failed_checks == 0
        assert report.overall_status == "compliant"

    def test_report_holds_check_list(self):
        report = self._make_report()
        assert len(report.checks) == 2

# ---------------------------------------------------------------------------
# CDCReconciler — ImportError path (psycopg absent)
# ---------------------------------------------------------------------------

class TestCDCReconcilerImportError:
    """Tests for ImportError when psycopg is not installed."""

    def test_init_raises_import_error_when_psycopg_missing(self):
        with patch("socrata_toolkit.cdc.compliance.psycopg", None):
            with pytest.raises(ImportError, match="postgres extras"):
                CDCReconciler(dsn="postgresql://localhost/test")

# ---------------------------------------------------------------------------
# CDCReconciler — DB-mocked helpers
# ---------------------------------------------------------------------------

def _make_reconciler() -> CDCReconciler:
    """Return a CDCReconciler with a fake psycopg module in place."""
    mock_psycopg = MagicMock()
    with patch("socrata_toolkit.cdc.compliance.psycopg", mock_psycopg):
        reconciler = CDCReconciler(dsn="postgresql://localhost/test")
    return reconciler

def _attach_fake_connection(reconciler: CDCReconciler, cur: MagicMock) -> None:
    """Attach a fake _get_connection context manager returning cur."""
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    @contextmanager
    def fake_conn():
        yield conn

    reconciler._get_connection = fake_conn

def _attach_raising_connection(reconciler: CDCReconciler, exc: Exception) -> None:
    """Attach a _get_connection that raises on enter."""
    @contextmanager
    def fake_conn():
        raise exc
        yield  # pragma: no cover

    reconciler._get_connection = fake_conn

# ---------------------------------------------------------------------------
# verify_audit_trail_completeness
# ---------------------------------------------------------------------------

class TestVerifyAuditTrailCompleteness:
    """Tests for CDCReconciler.verify_audit_trail_completeness."""

    def test_no_audit_entries_fails(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchone.side_effect = [(0,), (0,), (0,)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_audit_trail_completeness()

        assert result.passed is False
        assert any("No audit trail" in i for i in result.issues)

    def test_all_good_passes(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        # total_audit=100, gap_count=0, immutability_violations=0
        cur.fetchone.side_effect = [(100,), (0,), (0,)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_audit_trail_completeness()

        assert result.passed is True
        assert result.check_name == "audit_trail_completeness"

    def test_db_exception_produces_issue(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("DB down"))

        result = reconciler.verify_audit_trail_completeness()

        assert result.passed is False
        assert any("check failed" in i for i in result.issues)

    def test_gap_count_nonzero_adds_issue(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        # total_audit=50, gap_count=3, immutability=0
        cur.fetchone.side_effect = [(50,), (3,), (0,)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_audit_trail_completeness()

        assert result.passed is False
        assert any(">24hr gaps" in i for i in result.issues)

    def test_severity_is_critical_when_issues_present(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("err"))

        result = reconciler.verify_audit_trail_completeness()

        assert result.severity == "critical"

# ---------------------------------------------------------------------------
# verify_cdc_event_ordering
# ---------------------------------------------------------------------------

class TestVerifyCDCEventOrdering:
    """Tests for CDCReconciler.verify_cdc_event_ordering."""

    def test_no_duplicates_no_out_of_order_passes(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = []      # no duplicates
        cur.fetchone.side_effect = [(0,), (0,)]  # out_of_order=0, invalid_ops=0
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_cdc_event_ordering()

        assert result.passed is True
        assert result.check_name == "cdc_event_ordering"

    def test_duplicate_event_ids_fail(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = [("evt-1", 2), ("evt-2", 3)]
        cur.fetchone.side_effect = [(0,), (0,)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_cdc_event_ordering()

        assert result.passed is False
        assert any("duplicate event IDs" in i for i in result.issues)

    def test_out_of_order_events_fail(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = []
        cur.fetchone.side_effect = [(7,), (0,)]  # 7 out-of-order
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_cdc_event_ordering()

        assert result.passed is False
        assert any("out-of-order" in i for i in result.issues)

    def test_invalid_op_sequences_fail(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = []
        cur.fetchone.side_effect = [(0,), (3,)]  # 3 invalid op sequences
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_cdc_event_ordering()

        assert result.passed is False
        assert any("invalid operation sequences" in i for i in result.issues)

    def test_db_exception_produces_issue(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, ConnectionError("DB unreachable"))

        result = reconciler.verify_cdc_event_ordering()

        assert result.passed is False
        assert any("ordering check failed" in i for i in result.issues)

# ---------------------------------------------------------------------------
# verify_scd_integrity
# ---------------------------------------------------------------------------

class TestVerifySCDIntegrity:
    """Tests for CDCReconciler.verify_scd_integrity."""

    def test_clean_scd_passes(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = []      # no multiple is_current
        cur.fetchone.side_effect = [(0,), (0,)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_scd_integrity("sidewalk_conditions_scd")

        assert result.passed is True
        assert "sidewalk_conditions_scd" in result.check_name

    def test_multiple_is_current_fails(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = [("bk_001", 2)]
        cur.fetchone.side_effect = [(0,), (0,)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_scd_integrity("my_scd_table")

        assert result.passed is False
        assert any("Multiple is_current" in i for i in result.issues)

    def test_overlapping_dates_fail(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = []
        cur.fetchone.side_effect = [(5,), (0,)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_scd_integrity("my_scd_table")

        assert result.passed is False
        assert any("overlapping date ranges" in i for i in result.issues)

    def test_invalid_date_ranges_fail(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchall.return_value = []
        cur.fetchone.side_effect = [(0,), (2,)]  # 2 end < start violations
        _attach_fake_connection(reconciler, cur)

        result = reconciler.verify_scd_integrity("my_scd_table")

        assert result.passed is False
        assert any("invalid date ranges" in i for i in result.issues)

    def test_db_exception_produces_issue(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("timeout"))

        result = reconciler.verify_scd_integrity("any_table")

        assert result.passed is False
        assert any("SCD integrity check failed" in i for i in result.issues)

# ---------------------------------------------------------------------------
# reconcile_scd_with_source
# ---------------------------------------------------------------------------

class TestReconcileSCDWithSource:
    """Tests for CDCReconciler.reconcile_scd_with_source."""

    def test_perfect_reconciliation(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchone.side_effect = [(100,), (100,)]
        cur.fetchall.side_effect = [[], []]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.reconcile_scd_with_source("scd_table", "source_table")

        assert result.reconciled is True
        assert result.cdc_record_count == 100
        assert result.source_record_count == 100

    def test_missing_events_detected(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchone.side_effect = [(90,), (100,)]
        cur.fetchall.side_effect = [["id_1", "id_2"], []]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.reconcile_scd_with_source("scd_table", "source_table")

        assert result.reconciled is False
        assert len(result.missing_events) == 2

    def test_extra_events_detected(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchone.side_effect = [(105,), (100,)]
        cur.fetchall.side_effect = [[], ["extra_id_1", "extra_id_2", "extra_id_3"]]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.reconcile_scd_with_source("scd_table", "source_table")

        assert result.reconciled is False
        assert len(result.extra_events) == 3

    def test_db_exception_returns_failed_result(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("connection refused"))

        result = reconciler.reconcile_scd_with_source("scd", "src")

        assert result.reconciled is False
        assert result.cdc_record_count == 0
        assert result.source_system == "src"

# ---------------------------------------------------------------------------
# check_record_count_consistency
# ---------------------------------------------------------------------------

class TestCheckRecordCountConsistency:
    """Tests for CDCReconciler.check_record_count_consistency."""

    def test_db_exception_adds_issue(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("error"))

        result = reconciler.check_record_count_consistency("my_table", 50)

        assert result.passed is False
        assert any("Count check failed" in i for i in result.issues)

    def test_check_name_contains_table(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("err"))

        result = reconciler.check_record_count_consistency("specific_table", 10)

        assert "specific_table" in result.check_name

    def test_severity_is_warning_on_failure(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("err"))

        result = reconciler.check_record_count_consistency("t", 5)

        assert result.severity == "warning"

# ---------------------------------------------------------------------------
# check_audit_trail_coverage
# ---------------------------------------------------------------------------

class TestCheckAuditTrailCoverage:
    """Tests for CDCReconciler.check_audit_trail_coverage."""

    def test_no_entries_fails_critical(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchone.return_value = (None, None)
        _attach_fake_connection(reconciler, cur)

        result = reconciler.check_audit_trail_coverage()

        assert result.passed is False
        assert result.severity == "critical"

    def test_full_coverage_passes(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        cur.fetchone.side_effect = [
            (ts, ts),
            (30, 30),
        ]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.check_audit_trail_coverage()

        assert result.passed is True

    def test_partial_coverage_adds_issue(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        cur.fetchone.side_effect = [
            (ts, ts),
            (20, 30),
        ]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.check_audit_trail_coverage()

        assert result.passed is False
        assert any("coverage" in i.lower() for i in result.issues)

    def test_db_exception_adds_issue(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("DB error"))

        result = reconciler.check_audit_trail_coverage()

        assert result.passed is False
        assert any("Coverage check failed" in i for i in result.issues)

# ---------------------------------------------------------------------------
# generate_compliance_report
# ---------------------------------------------------------------------------

class TestGenerateComplianceReport:
    """Tests for CDCReconciler.generate_compliance_report."""

    def _patch_all_checks(self, reconciler: CDCReconciler, passed: bool) -> None:
        """Patch individual check methods to return deterministic results."""
        severity = "info" if passed else "critical"
        result = ComplianceCheckResult(
            check_name="mocked_check", passed=passed, severity=severity
        )
        reconciler.verify_audit_trail_completeness = MagicMock(return_value=result)
        reconciler.verify_cdc_event_ordering = MagicMock(return_value=result)
        reconciler.check_audit_trail_coverage = MagicMock(return_value=result)

    def test_all_passing_returns_compliant(self):
        reconciler = _make_reconciler()
        self._patch_all_checks(reconciler, passed=True)

        report = reconciler.generate_compliance_report()

        assert report.overall_status == "compliant"
        assert report.passed_checks == 3
        assert report.failed_checks == 0
        assert "All checks passed" in report.summary

    def test_all_failing_returns_critical(self):
        reconciler = _make_reconciler()
        self._patch_all_checks(reconciler, passed=False)

        report = reconciler.generate_compliance_report()

        assert report.overall_status == "critical"
        assert report.failed_checks == 3
        assert "CRITICAL" in report.summary

    def test_report_has_three_checks(self):
        reconciler = _make_reconciler()
        self._patch_all_checks(reconciler, passed=True)

        report = reconciler.generate_compliance_report()

        assert len(report.checks) == 3
        assert report.total_checks == 3

    def test_warning_status_when_non_critical_failure(self):
        reconciler = _make_reconciler()
        # Patch: audit=pass, ordering=pass, coverage=warning-fail
        pass_result = ComplianceCheckResult(
            check_name="ok", passed=True, severity="info"
        )
        warn_result = ComplianceCheckResult(
            check_name="coverage", passed=False, severity="warning"
        )
        reconciler.verify_audit_trail_completeness = MagicMock(return_value=pass_result)
        reconciler.verify_cdc_event_ordering = MagicMock(return_value=pass_result)
        reconciler.check_audit_trail_coverage = MagicMock(return_value=warn_result)

        report = reconciler.generate_compliance_report()

        assert report.overall_status == "warning"

# ---------------------------------------------------------------------------
# detect_missing_changes
# ---------------------------------------------------------------------------

class TestDetectMissingChanges:
    """Tests for CDCReconciler.detect_missing_changes."""

    def test_returns_dict_with_expected_keys(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchone.return_value = (0,)
        cur.fetchall.return_value = []
        _attach_fake_connection(reconciler, cur)

        result = reconciler.detect_missing_changes(
            date(2026, 1, 1), date(2026, 3, 31)
        )

        assert "entities_no_change" in result
        assert "high_frequency_changes" in result

    def test_db_exception_returns_empty_fallback(self):
        reconciler = _make_reconciler()
        _attach_raising_connection(reconciler, RuntimeError("timeout"))

        result = reconciler.detect_missing_changes(
            date(2026, 1, 1), date(2026, 3, 31)
        )

        assert result["entities_no_change"] == 0
        assert result["high_frequency_changes"] == []

    def test_high_frequency_changes_mapped_correctly(self):
        reconciler = _make_reconciler()
        cur = MagicMock()
        cur.fetchone.return_value = (5,)
        cur.fetchall.return_value = [("entity_abc", 250), ("entity_xyz", 200)]
        _attach_fake_connection(reconciler, cur)

        result = reconciler.detect_missing_changes(
            date(2026, 1, 1), date(2026, 3, 31)
        )

        assert len(result["high_frequency_changes"]) == 2
        assert result["high_frequency_changes"][0]["entity_id"] == "entity_abc"
        assert result["high_frequency_changes"][0]["count"] == 250

# ---------------------------------------------------------------------------
# export_compliance_report
# ---------------------------------------------------------------------------

class TestExportComplianceReport:
    """Tests for CDCReconciler.export_compliance_report."""

    def _make_report(self, status: str, passed: bool) -> ComplianceReport:
        checks = [
            ComplianceCheckResult(
                check_name="audit_trail_completeness",
                passed=passed,
                issues=[] if passed else ["some issue"],
                severity="info" if passed else "critical",
            )
        ]
        return ComplianceReport(
            report_date=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            total_checks=1,
            passed_checks=1 if passed else 0,
            failed_checks=0 if passed else 1,
            checks=checks,
            overall_status=status,
            summary="1/1 checks passed." if passed else "0/1 checks passed. CRITICAL.",
        )

    def test_export_contains_status(self):
        reconciler = _make_reconciler()
        report = self._make_report("compliant", passed=True)
        output = reconciler.export_compliance_report(report)

        assert "COMPLIANT" in output
        assert "CDC Compliance Report" in output

    def test_export_contains_pass_marker(self):
        reconciler = _make_reconciler()
        report = self._make_report("compliant", passed=True)
        output = reconciler.export_compliance_report(report)

        assert "PASS" in output
        assert "audit_trail_completeness" in output

    def test_export_contains_fail_marker_and_issue(self):
        reconciler = _make_reconciler()
        report = self._make_report("critical", passed=False)
        output = reconciler.export_compliance_report(report)

        assert "FAIL" in output
        assert "some issue" in output

    def test_export_contains_checks_ratio(self):
        reconciler = _make_reconciler()
        report = self._make_report("compliant", passed=True)
        output = reconciler.export_compliance_report(report)

        assert "1/1" in output

    def test_export_returns_string(self):
        reconciler = _make_reconciler()
        report = self._make_report("compliant", passed=True)
        output = reconciler.export_compliance_report(report)

        assert isinstance(output, str)
