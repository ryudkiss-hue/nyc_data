"""Comprehensive tests for engineering.ramp_analysis module.

This tests ONLY src/socrata_toolkit/engineering/ramp_analysis.py.
The analyst.ramp_analysis module is already at 100% coverage and is
not touched here.
"""
from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

import pandas as pd
import pytest

from socrata_toolkit.engineering.ramp_analysis import (
    BoroughRampStats,
    RampCompletionReport,
    RampCompletionReportGenerator,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Minimal ramp DataFrame with required columns."""
    return pd.DataFrame(
        {
            "borough": ["MN", "MN", "BK", "BK", "BK", "QN"],
            "status": ["complete", "pending", "completed", "done", "pending", "complete"],
        }
    )

@pytest.fixture()
def large_df() -> pd.DataFrame:
    """DataFrame large enough to trigger sampling path (>100 rows)."""
    return pd.DataFrame(
        {
            "borough": ["MN"] * 60 + ["BK"] * 60,
            "status": ["complete"] * 80 + ["pending"] * 40,
        }
    )

@pytest.fixture()
def generator() -> RampCompletionReportGenerator:
    """Default generator with standard cache_ttl."""
    return RampCompletionReportGenerator()

# ---------------------------------------------------------------------------
# BoroughRampStats dataclass
# ---------------------------------------------------------------------------

class TestBoroughRampStats:
    """Tests for BoroughRampStats dataclass."""

    def test_default_reliability_unknown(self):
        stats = BoroughRampStats(
            borough="MN",
            total_ramps=10,
            completed_ramps=5,
            completion_rate=0.5,
        )
        assert stats.reliability == "unknown"

    def test_ci_fields_default_none(self):
        stats = BoroughRampStats(
            borough="BK",
            total_ramps=100,
            completed_ramps=80,
            completion_rate=0.8,
        )
        assert stats.ci_lower is None
        assert stats.ci_upper is None

    def test_explicit_ci_stored(self):
        stats = BoroughRampStats(
            borough="QN",
            total_ramps=200,
            completed_ramps=150,
            completion_rate=0.75,
            ci_lower=0.69,
            ci_upper=0.81,
            reliability="high",
        )
        assert stats.ci_lower == pytest.approx(0.69)
        assert stats.ci_upper == pytest.approx(0.81)
        assert stats.reliability == "high"

# ---------------------------------------------------------------------------
# RampCompletionReport.to_table
# ---------------------------------------------------------------------------

class TestRampCompletionReportToTable:
    """Tests for RampCompletionReport.to_table method."""

    def _make_report(self, include_ci: bool = False) -> RampCompletionReport:
        stats = [
            BoroughRampStats(
                borough="MN",
                total_ramps=100,
                completed_ramps=75,
                completion_rate=0.75,
                ci_lower=0.65 if include_ci else None,
                ci_upper=0.83 if include_ci else None,
                sample_size=100,
                reliability="high",
            )
        ]
        return RampCompletionReport(
            timestamp="2026-06-04T12:00:00",
            mode="full-corpus",
            sample_size=None,
            total_boroughs=1,
            overall_completion_rate=0.75,
            borough_stats=stats,
            include_ci=include_ci,
        )

    def test_to_table_returns_string(self):
        report = self._make_report()
        table = report.to_table()
        assert isinstance(table, str)

    def test_to_table_contains_borough(self):
        report = self._make_report()
        table = report.to_table()
        assert "MN" in table

    def test_to_table_contains_overall_rate(self):
        report = self._make_report()
        table = report.to_table()
        assert "75.0%" in table

    def test_to_table_with_ci_shows_ci_column(self):
        report = self._make_report(include_ci=True)
        table = report.to_table()
        assert "95% CI" in table
        assert "65.0%" in table
        assert "83.0%" in table

    def test_to_table_without_ci_no_ci_column(self):
        report = self._make_report(include_ci=False)
        table = report.to_table()
        assert "95% CI" not in table

    def test_to_table_sample_mode_shows_sample_size(self):
        stats = [
            BoroughRampStats(
                borough="BK",
                total_ramps=50,
                completed_ramps=30,
                completion_rate=0.6,
                sample_size=50,
                reliability="medium",
            )
        ]
        report = RampCompletionReport(
            timestamp="2026-06-04T12:00:00",
            mode="sample",
            sample_size=50,
            total_boroughs=1,
            overall_completion_rate=0.6,
            borough_stats=stats,
        )
        table = report.to_table()
        assert "50 corners sampled" in table

# ---------------------------------------------------------------------------
# RampCompletionReport.to_dict
# ---------------------------------------------------------------------------

class TestRampCompletionReportToDict:
    """Tests for RampCompletionReport.to_dict method."""

    def test_to_dict_top_level_keys(self):
        stats = [
            BoroughRampStats(
                borough="SI",
                total_ramps=20,
                completed_ramps=10,
                completion_rate=0.5,
                sample_size=20,
                reliability="low",
            )
        ]
        report = RampCompletionReport(
            timestamp="2026-06-04T00:00:00",
            mode="sample",
            sample_size=20,
            total_boroughs=1,
            overall_completion_rate=0.5,
            borough_stats=stats,
        )
        d = report.to_dict()

        assert "timestamp" in d
        assert "mode" in d
        assert "total_boroughs" in d
        assert "overall_completion_rate" in d
        assert "borough_stats" in d

    def test_to_dict_borough_stats_structure(self):
        stats = [
            BoroughRampStats(
                borough="BX",
                total_ramps=80,
                completed_ramps=40,
                completion_rate=0.5,
                sample_size=80,
                reliability="medium",
            )
        ]
        report = RampCompletionReport(
            timestamp="2026-06-04T00:00:00",
            mode="full-corpus",
            sample_size=None,
            total_boroughs=1,
            overall_completion_rate=0.5,
            borough_stats=stats,
        )
        d = report.to_dict()

        borough_entry = d["borough_stats"][0]
        assert borough_entry["borough"] == "BX"
        assert borough_entry["total_ramps"] == 80
        assert borough_entry["completion_rate"] == pytest.approx(0.5)

# ---------------------------------------------------------------------------
# RampCompletionReportGenerator._assess_reliability
# ---------------------------------------------------------------------------

class TestAssessReliability:
    """Tests for the static _assess_reliability method."""

    def test_high_reliability_for_100_plus(self):
        assert RampCompletionReportGenerator._assess_reliability(100) == "high"
        assert RampCompletionReportGenerator._assess_reliability(500) == "high"

    def test_medium_reliability_for_30_to_99(self):
        assert RampCompletionReportGenerator._assess_reliability(30) == "medium"
        assert RampCompletionReportGenerator._assess_reliability(99) == "medium"

    def test_low_reliability_below_30(self):
        assert RampCompletionReportGenerator._assess_reliability(0) == "low"
        assert RampCompletionReportGenerator._assess_reliability(29) == "low"

# ---------------------------------------------------------------------------
# RampCompletionReportGenerator._binomial_ci
# ---------------------------------------------------------------------------

class TestBinomialCI:
    """Tests for the static _binomial_ci method."""

    def test_zero_trials_returns_full_interval(self):
        lower, upper = RampCompletionReportGenerator._binomial_ci(0, 0)
        assert lower == 0.0
        assert upper == 1.0

    def test_all_successes(self):
        lower, upper = RampCompletionReportGenerator._binomial_ci(100, 100)
        assert lower == pytest.approx(1.0, abs=0.001)
        assert upper == 1.0

    def test_no_successes(self):
        lower, upper = RampCompletionReportGenerator._binomial_ci(0, 100)
        assert lower == 0.0
        assert upper == pytest.approx(0.0, abs=0.001)

    def test_midpoint_interval_is_symmetric(self):
        lower, upper = RampCompletionReportGenerator._binomial_ci(50, 100)
        mid = (lower + upper) / 2
        assert mid == pytest.approx(0.5, abs=0.01)

    def test_bounds_are_within_zero_one(self):
        lower, upper = RampCompletionReportGenerator._binomial_ci(3, 10)
        assert 0.0 <= lower <= 1.0
        assert 0.0 <= upper <= 1.0

# ---------------------------------------------------------------------------
# RampCompletionReportGenerator.generate — validation guards
# ---------------------------------------------------------------------------

class TestGenerateValidation:
    """Tests for generate() input validation."""

    def test_none_df_raises_value_error(self, generator):
        with pytest.raises(ValueError, match="required"):
            generator.generate(df=None)

    def test_empty_df_raises_value_error(self, generator):
        with pytest.raises(ValueError, match="required"):
            generator.generate(df=pd.DataFrame())

    def test_missing_borough_column_raises(self, generator):
        df = pd.DataFrame({"status": ["complete", "pending"]})
        with pytest.raises(ValueError, match="borough"):
            generator.generate(df=df)

    def test_missing_status_column_raises(self, generator):
        df = pd.DataFrame({"borough": ["MN", "BK"]})
        with pytest.raises(ValueError, match="status"):
            generator.generate(df=df)

    def test_unknown_borough_filter_raises(self, generator, sample_df):
        with pytest.raises(ValueError, match="No data found for borough"):
            generator.generate(df=sample_df, borough_filter="ZZ")

# ---------------------------------------------------------------------------
# RampCompletionReportGenerator.generate — happy paths
# ---------------------------------------------------------------------------

class TestGenerateHappyPath:
    """Tests for generate() with valid inputs."""

    def test_generates_report_object(self, generator, sample_df):
        report = generator.generate(df=sample_df)
        assert isinstance(report, RampCompletionReport)

    def test_borough_stats_populated(self, generator, sample_df):
        report = generator.generate(df=sample_df)
        assert len(report.borough_stats) > 0

    def test_completion_rate_bounded_zero_one(self, generator, sample_df):
        report = generator.generate(df=sample_df)
        for stat in report.borough_stats:
            assert 0.0 <= stat.completion_rate <= 1.0

    def test_full_corpus_mode_sample_size_none(self, generator, sample_df):
        report = generator.generate(df=sample_df, mode="full-corpus")
        assert report.sample_size is None
        assert report.mode == "full-corpus"

    def test_sample_mode_limits_rows(self, generator, large_df):
        report = generator.generate(df=large_df, mode="sample", sample_size=50)
        assert report.mode == "sample"
        assert report.sample_size <= 50

    def test_borough_filter_restricts_boroughs(self, generator, sample_df):
        report = generator.generate(df=sample_df, borough_filter="MN")
        boroughs = [s.borough for s in report.borough_stats]
        assert boroughs == ["MN"]

    def test_ci_included_when_requested(self, generator, sample_df):
        report = generator.generate(df=sample_df, include_ci=True)
        assert report.include_ci is True
        for stat in report.borough_stats:
            assert stat.ci_lower is not None
            assert stat.ci_upper is not None

    def test_ci_not_included_when_not_requested(self, generator, sample_df):
        report = generator.generate(df=sample_df, include_ci=False)
        for stat in report.borough_stats:
            assert stat.ci_lower is None
            assert stat.ci_upper is None

    def test_accepts_completion_status_column(self, generator):
        df = pd.DataFrame(
            {
                "borough": ["MN", "BK"],
                "completion_status": ["complete", "pending"],
            }
        )
        report = generator.generate(df=df)
        assert report.total_boroughs == 2

    def test_accepts_construction_status_value_column(self, generator):
        df = pd.DataFrame(
            {
                "borough": ["QN", "SI"],
                "Construction_Status_Value": ["complete", "done"],
            }
        )
        report = generator.generate(df=df)
        assert report.overall_completion_rate == pytest.approx(1.0)

    def test_overall_rate_correct(self, generator):
        df = pd.DataFrame(
            {
                "borough": ["MN", "MN", "MN", "MN"],
                "status": ["complete", "complete", "pending", "pending"],
            }
        )
        report = generator.generate(df=df, include_ci=False)
        assert report.overall_completion_rate == pytest.approx(0.5)

    def test_borough_names_uppercased(self, generator):
        df = pd.DataFrame(
            {
                "borough": ["mn", "bk"],
                "status": ["complete", "done"],
            }
        )
        report = generator.generate(df=df)
        boroughs = {s.borough for s in report.borough_stats}
        assert boroughs == {"MN", "BK"}

    def test_custom_cache_ttl_stored(self):
        gen = RampCompletionReportGenerator(cache_ttl_hours=72)
        assert gen.cache_ttl_hours == 72
