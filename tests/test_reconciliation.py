"""Test suite for data reconciliation module.

Tests for the DataReconciliation class, including:
- Row count discrepancy detection
- Tolerance-based status determination
- Report generation
- Edge cases and error handling
"""

from __future__ import annotations

import pytest

from socrata_toolkit.quality.reconciliation import DataReconciliation, ReconciliationResult


class TestReconciliationResult:
    """Test suite for ReconciliationResult dataclass."""

    def test_reconciliation_result_creation(self):
        """Test creating a ReconciliationResult."""
        result = ReconciliationResult(
            table="test_table",
            expected=1000,
            actual=1050,
            variance=50,
            variance_pct=5.0,
            status="OK",
        )
        assert result.table == "test_table"
        assert result.expected == 1000
        assert result.actual == 1050
        assert result.variance == 50
        assert result.variance_pct == 5.0
        assert result.status == "OK"

    def test_reconciliation_result_to_dict(self):
        """Test converting ReconciliationResult to dict."""
        result = ReconciliationResult(
            table="test_table",
            expected=1000,
            actual=1050,
            variance=50,
            variance_pct=5.0,
            status="OK",
            timestamp="2026-06-10T12:00:00+00:00",
        )
        result_dict = result.to_dict()
        assert result_dict["table"] == "test_table"
        assert result_dict["expected"] == 1000
        assert result_dict["actual"] == 1050
        assert result_dict["variance"] == 50
        assert result_dict["variance_pct"] == 5.0
        assert result_dict["status"] == "OK"
        assert result_dict["timestamp"] == "2026-06-10T12:00:00+00:00"


class TestDataReconciliation:
    """Test suite for DataReconciliation class."""

    @pytest.fixture
    def sample_expected_counts(self) -> dict[str, int]:
        """Sample expected row counts."""
        return {
            "inspection": 100_000,
            "violations": 50_000,
            "permits": 10_000,
        }

    @pytest.fixture
    def sample_actual_counts(self) -> dict[str, int]:
        """Sample actual row counts matching expected."""
        return {
            "inspection": 100_000,
            "violations": 50_000,
            "permits": 10_000,
        }

    def test_reconciliation_initialization(self, sample_expected_counts, sample_actual_counts):
        """Test DataReconciliation initialization."""
        recon = DataReconciliation(
            "test_dataset",
            sample_expected_counts,
            sample_actual_counts,
        )
        assert recon.dataset_name == "test_dataset"
        assert recon.expected_counts == sample_expected_counts
        assert recon.actual_counts == sample_actual_counts
        assert recon.results == []

    def test_reconciliation_detects_row_count_discrepancy(self):
        """Test that reconciliation detects row count discrepancies."""
        expected = {"table_a": 1000, "table_b": 5000}
        actual = {"table_a": 950, "table_b": 5500}  # 5% and 10% variance

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.03)

        # table_a: 5% variance
        # 5% > 3% tolerance, but 5% < 6% (2x tolerance)
        # So should be WARNING
        table_a_result = [r for r in results if r.table == "table_a"][0]
        assert table_a_result.expected == 1000
        assert table_a_result.actual == 950
        assert table_a_result.variance == -50
        assert abs(table_a_result.variance_pct - (-5.0)) < 0.01
        assert table_a_result.status == "WARNING"

        # table_b: 10% variance
        # 10% > 6% (2x tolerance), so FAIL
        table_b_result = [r for r in results if r.table == "table_b"][0]
        assert table_b_result.expected == 5000
        assert table_b_result.actual == 5500
        assert table_b_result.variance == 500
        assert abs(table_b_result.variance_pct - 10.0) < 0.01
        assert table_b_result.status == "FAIL"

    def test_reconciliation_ok_within_tolerance(self):
        """Test that reconciliation marks OK when within tolerance."""
        expected = {"table_a": 1000}
        actual = {"table_a": 1020}  # 2% variance

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)  # 5% tolerance

        result = results[0]
        assert result.variance_pct == 2.0
        assert result.status == "OK"

    def test_reconciliation_warning_within_2x_tolerance(self):
        """Test that reconciliation marks WARNING when between tolerance and 2x tolerance."""
        expected = {"table_a": 1000}
        actual = {"table_a": 1070}  # 7% variance

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)  # 5% tolerance

        result = results[0]
        assert abs(result.variance_pct - 7.0) < 0.01
        # 7% is between 5% (tolerance) and 10% (2x tolerance), so WARNING
        assert result.status == "WARNING"

    def test_reconciliation_fail_beyond_2x_tolerance(self):
        """Test that reconciliation marks FAIL when beyond 2x tolerance."""
        expected = {"table_a": 1000}
        actual = {"table_a": 1150}  # 15% variance

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)  # 5% tolerance

        result = results[0]
        assert result.variance_pct == 15.0
        # 15% is beyond 10% (2x tolerance), so FAIL
        assert result.status == "FAIL"

    def test_reconciliation_handles_missing_tables(self):
        """Test reconciliation when actual has tables not in expected."""
        expected = {"table_a": 1000}
        actual = {"table_a": 1000, "table_b": 500}  # table_b is new

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        assert len(results) == 2
        assert {r.table for r in results} == {"table_a", "table_b"}

    def test_reconciliation_handles_missing_actual(self):
        """Test reconciliation when expected has tables not in actual."""
        expected = {"table_a": 1000, "table_b": 2000}
        actual = {"table_a": 1000}  # table_b is missing

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        assert len(results) == 2
        table_b_result = [r for r in results if r.table == "table_b"][0]
        assert table_b_result.expected == 2000
        assert table_b_result.actual == 0
        assert table_b_result.variance == -2000
        # 100% variance when expected > 0 but actual = 0
        assert table_b_result.variance_pct == -100.0
        assert table_b_result.status == "FAIL"

    def test_reconciliation_handles_zero_expected(self):
        """Test reconciliation when expected count is 0."""
        expected = {"table_a": 0}
        actual = {"table_a": 10}

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        result = results[0]
        assert result.expected == 0
        assert result.actual == 10
        assert result.variance == 10
        # When expected is 0, any non-zero actual = 100% variance
        assert result.variance_pct == 100.0
        assert result.status == "FAIL"

    def test_reconciliation_handles_zero_expected_and_actual(self):
        """Test reconciliation when both expected and actual are 0."""
        expected = {"table_a": 0}
        actual = {"table_a": 0}

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        result = results[0]
        assert result.expected == 0
        assert result.actual == 0
        assert result.variance == 0
        assert result.variance_pct == 0.0
        assert result.status == "OK"

    def test_reconciliation_report_generation(self):
        """Test reconciliation report generation."""
        expected = {"inspection": 1000, "violations": 500}
        actual = {"inspection": 1050, "violations": 480}

        recon = DataReconciliation("NYC Datasets", expected, actual)
        recon.check_counts(tolerance_pct=0.05)

        report = recon.generate_reconciliation_report()

        assert "DATA RECONCILIATION REPORT" in report
        assert "NYC Datasets" in report
        assert "inspection" in report
        assert "violations" in report
        assert "SUMMARY" in report
        assert "DETAILED RESULTS" in report

    def test_reconciliation_report_includes_discrepancies(self):
        """Test that report includes discrepancies section."""
        expected = {"table_a": 1000}
        actual = {"table_a": 500}  # 50% variance

        recon = DataReconciliation("test", expected, actual)
        recon.check_counts(tolerance_pct=0.05)

        report = recon.generate_reconciliation_report()

        assert "DISCREPANCIES REQUIRING ATTENTION" in report
        assert "table_a" in report
        assert "FAIL" in report

    def test_reconciliation_get_failed_tables(self):
        """Test getting list of failed tables."""
        expected = {"a": 100, "b": 100, "c": 100}
        actual = {"a": 100, "b": 10, "c": 150}

        recon = DataReconciliation("test", expected, actual)
        recon.check_counts(tolerance_pct=0.05)

        failed = recon.get_failed_tables()
        assert "a" not in failed  # OK
        assert "b" in failed  # FAIL (90% variance)
        assert "c" in failed  # FAIL (50% variance)

    def test_reconciliation_get_warning_tables(self):
        """Test getting list of warning tables."""
        expected = {"a": 1000}
        actual = {"a": 1070}  # 7% variance (WARNING at 5% tolerance)

        recon = DataReconciliation("test", expected, actual)
        recon.check_counts(tolerance_pct=0.05)

        warnings = recon.get_warning_tables()
        assert "a" in warnings

    def test_reconciliation_summary_stats(self):
        """Test summary statistics calculation."""
        expected = {"a": 1000, "b": 1000, "c": 1000}
        actual = {"a": 1020, "b": 500, "c": 1100}

        recon = DataReconciliation("test", expected, actual)
        recon.check_counts(tolerance_pct=0.05)

        stats = recon.summary_stats()

        assert stats["total_checks"] == 3
        assert "ok_count" in stats
        assert "warning_count" in stats
        assert "fail_count" in stats
        assert "ok_pct" in stats
        assert "warning_pct" in stats
        assert "fail_pct" in stats
        assert "max_variance_pct" in stats
        # Check that percentages sum to ~100% (allow for rounding)
        total_pct = stats["ok_pct"] + stats["warning_pct"] + stats["fail_pct"]
        assert abs(total_pct - 100.0) < 0.5

    def test_reconciliation_with_negative_variance(self):
        """Test reconciliation with negative variance (actual < expected)."""
        expected = {"table": 1000}
        actual = {"table": 850}  # 15% variance (beyond 2x tolerance)

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        result = results[0]
        assert result.variance == -150
        assert abs(result.variance_pct - (-15.0)) < 0.01
        # 15% variance > 10% (2x tolerance), so FAIL
        assert result.status == "FAIL"

    def test_reconciliation_edge_case_empty_dicts(self):
        """Test reconciliation with empty expected and actual dicts."""
        recon = DataReconciliation("test", {}, {})
        results = recon.check_counts(tolerance_pct=0.05)

        assert len(results) == 0
        assert recon.get_failed_tables() == []
        assert recon.get_warning_tables() == []

    def test_reconciliation_report_empty_data(self):
        """Test report generation with no data."""
        recon = DataReconciliation("test", {}, {})
        recon.check_counts()

        report = recon.generate_reconciliation_report()
        assert "DATA RECONCILIATION REPORT" in report
        assert "Total Tables Checked: 0" in report

    def test_reconciliation_multiple_calls_accumulate_results(self):
        """Test that calling check_counts multiple times replaces results."""
        recon = DataReconciliation(
            "test",
            {"a": 100},
            {"a": 100},
        )

        results1 = recon.check_counts(tolerance_pct=0.05)
        assert len(results1) == 1
        assert results1[0].status == "OK"

        # Change actual counts and check again
        recon.actual_counts = {"a": 50}
        results2 = recon.check_counts(tolerance_pct=0.05)
        assert len(results2) == 1
        assert results2[0].status == "FAIL"
        # Second call should replace, not append
        assert len(recon.results) == 1

    def test_reconciliation_variance_calculation_precision(self):
        """Test variance calculation precision."""
        expected = {"table": 33333}
        actual = {"table": 33333}

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        result = results[0]
        assert abs(result.variance_pct - 0.0) < 0.01

    def test_reconciliation_large_numbers(self):
        """Test reconciliation with large row counts."""
        expected = {"table": 100_000_000}
        actual = {"table": 101_000_000}

        recon = DataReconciliation("test", expected, actual)
        results = recon.check_counts(tolerance_pct=0.05)

        result = results[0]
        assert result.variance == 1_000_000
        assert abs(result.variance_pct - 1.0) < 0.01
        assert result.status == "OK"
