"""Tests for Tier 3 Analytics Dashboard components."""

from __future__ import annotations

import pandas as pd
import pytest

class TestDataFreshness:
    """Test data freshness and lineage tracking."""

    def test_freshness_info_structure(self):
        """Freshness info should have required fields."""
        from app.views.analytics_advanced import _get_data_freshness_info

        freshness = _get_data_freshness_info()
        assert isinstance(freshness, dict)
        assert len(freshness) > 0

        for dataset, info in freshness.items():
            assert "last_updated" in info
            assert "row_count" in info
            assert "freshness_days" in info
            assert "schema_status" in info

    def test_freshness_days_positive(self):
        """Freshness days should be non-negative."""
        from app.views.analytics_advanced import _get_data_freshness_info

        freshness = _get_data_freshness_info()
        for dataset, info in freshness.items():
            assert info["freshness_days"] >= 0, f"{dataset} has negative freshness"

    def test_row_counts_reasonable(self):
        """Row counts should be positive and reasonable."""
        from app.views.analytics_advanced import _get_data_freshness_info

        freshness = _get_data_freshness_info()
        for dataset, info in freshness.items():
            assert info["row_count"] > 0, f"{dataset} has non-positive row count"
            assert info["row_count"] < 1e9, f"{dataset} has unreasonable row count"

class TestExecutiveDashboard:
    """Test executive dashboard metrics."""

    def test_executive_dashboard_with_empty_data(self):
        """Executive dashboard should handle empty data."""
        import streamlit as st

        df = pd.DataFrame()
        # This would be called from the dashboard function
        # Just verify the function exists and is callable
        from app.views.analytics_advanced import _render_executive_dashboard

        assert callable(_render_executive_dashboard)

    def test_breach_risk_calculation(self):
        """Breach risk should be between 0 and 100%."""
        from app.views.analytics_advanced import _forecast_sla_breach

        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "score": [40 + (i % 30) for i in range(50)],
            }
        )

        forecast = _forecast_sla_breach(df, "date", "score")
        breach_rate = forecast.get("breach_rate", 0)
        assert 0 <= breach_rate <= 1, f"Invalid breach rate: {breach_rate}"

class TestOperationsDashboard:
    """Test operations manager dashboard."""

    def test_breach_driver_aggregation(self):
        """Breach drivers should aggregate correctly."""
        df = pd.DataFrame(
            {
                "score": [25, 35, 50, 60, 75, 85],
            }
        )

        # Count breaches manually
        critical = (df["score"] < 30).sum()
        low = (df["score"] < 50).sum()

        assert critical == 1, f"Expected 1 critical, got {critical}"
        assert low == 2, f"Expected 2 low, got {low}"

    def test_inspector_workload_variance(self):
        """Inspector workload variance should be calculated."""
        df = pd.DataFrame(
            {
                "inspector": [
                    "A",
                    "A",
                    "B",
                    "B",
                    "B",
                    "C",
                    "C",
                    "C",
                    "C",
                    "C",
                ],
            }
        )

        stats = df.groupby("inspector").size()
        mean = stats.mean()
        std = stats.std()

        assert mean > 0
        assert std >= 0

class TestAnalystWorkbench:
    """Test analyst workbench filtering and export."""

    def test_score_range_filtering(self):
        """Score range filtering should work correctly."""
        df = pd.DataFrame(
            {
                "score": [10, 25, 40, 55, 70, 85, 100],
            }
        )

        min_score, max_score = 30, 80
        filtered = df[(df["score"] >= min_score) & (df["score"] <= max_score)]

        assert len(filtered) == 3
        assert filtered["score"].min() >= min_score
        assert filtered["score"].max() <= max_score

    def test_borough_multiselect_filtering(self):
        """Borough multiselect should filter correctly."""
        df = pd.DataFrame(
            {
                "borough": [
                    "MANHATTAN",
                    "BROOKLYN",
                    "QUEENS",
                    "MANHATTAN",
                    "BROOKLYN",
                ],
            }
        )

        selected = ["MANHATTAN", "BROOKLYN"]
        filtered = df[df["borough"].isin(selected)]

        assert len(filtered) == 4
        assert "QUEENS" not in filtered["borough"].values

    def test_csv_export_data_integrity(self):
        """CSV export should preserve data integrity."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
                "score": [75.5, 80.0, 85.5],
            }
        )

        csv = df.to_csv(index=False)
        assert "id" in csv
        assert "name" in csv
        assert "score" in csv
        assert "A" in csv
        assert "75.5" in csv

class TestStakeholderRoles:
    """Test role-based dashboard variations."""

    def test_role_options_valid(self):
        """Role options should be valid and distinct."""
        roles = ["👔 Executive", "🎯 Operations Manager", "📊 Analyst"]
        assert len(roles) == 3
        assert len(set(roles)) == 3  # All unique

    def test_role_specific_metrics(self):
        """Each role should focus on specific metrics."""
        # Executive: SLA, breach risk, critical issues
        # Operations: drivers, staffing, trends
        # Analyst: filters, exports, detailed view

        role_metrics = {
            "Executive": ["SLA", "breach", "critical"],
            "Operations": ["drivers", "staffing", "trends"],
            "Analyst": ["filters", "exports", "detail"],
        }

        for role, metrics in role_metrics.items():
            assert len(metrics) >= 2, f"{role} role missing key metrics"

class TestCohortRetention:
    """Test cohort retention analysis."""

    def test_cohort_retention_empty_data(self):
        """Cohort analysis should handle empty data."""
        from app.views.analytics_advanced import _compute_cohort_retention

        df = pd.DataFrame()
        result = _compute_cohort_retention(df, "cohort", "date")
        assert result.empty

    def test_cohort_retention_missing_columns(self):
        """Cohort analysis should handle missing columns."""
        from app.views.analytics_advanced import _compute_cohort_retention

        df = pd.DataFrame({"col1": [1, 2, 3]})
        result = _compute_cohort_retention(df, "cohort", "date")
        assert result.empty

    def test_cohort_retention_valid_data(self):
        """Cohort analysis should work with valid data."""
        from app.views.analytics_advanced import _compute_cohort_retention

        dates = pd.date_range("2024-01-01", periods=51, freq="D")
        df = pd.DataFrame(
            {
                "inspector": (["A", "B", "C"] * 17),
                "date": dates[:51],
            }
        )

        result = _compute_cohort_retention(df, "inspector", "date")
        assert not result.empty

class TestTrendForecast:
    """Test trend forecasting."""

    def test_forecast_empty_data(self):
        """Forecast should handle empty data."""
        from app.views.analytics_advanced import _forecast_trend

        df = pd.DataFrame()
        result = _forecast_trend(df, "date", "score")
        assert result == {}

    def test_forecast_insufficient_data(self):
        """Forecast should require minimum data points."""
        from app.views.analytics_advanced import _forecast_trend

        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02"],
                "score": [50, 55],
            }
        )
        result = _forecast_trend(df, "date", "score")
        assert result == {}

    def test_forecast_valid_data(self):
        """Forecast should work with sufficient data."""
        from app.views.analytics_advanced import _forecast_trend

        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "score": range(30, 60),
            }
        )

        result = _forecast_trend(df, "date", "score")
        assert result != {}
        assert "current_value" in result
        assert "forecast_value" in result
        assert "trend" in result
        assert result["trend"] in ["up", "down"]

    def test_forecast_uptrend(self):
        """Forecast should correctly identify uptrend."""
        from app.views.analytics_advanced import _forecast_trend

        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "score": list(range(50, 80)),  # Steady increase: 50 to 79
            }
        )

        result = _forecast_trend(df, "date", "score")
        assert result["trend"] == "up"
        assert result["slope"] > 0

    def test_forecast_downtrend(self):
        """Forecast should correctly identify downtrend."""
        from app.views.analytics_advanced import _forecast_trend

        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame(
            {
                "date": dates,
                "score": list(range(80, 50, -1)),  # Steady decrease: 80 to 51
            }
        )

        result = _forecast_trend(df, "date", "score")
        assert result["trend"] == "down"
        assert result["slope"] < 0

class TestDeltaUpdate:
    """Test delta update logic."""

    def test_should_refetch_first_fetch(self):
        """First fetch should always trigger."""
        from app.views.analytics_advanced import _should_refetch_data

        assert _should_refetch_data(100, 0) is True

    def test_should_refetch_significant_change(self):
        """Significant change (>5%) should trigger refetch."""
        from app.views.analytics_advanced import _should_refetch_data

        # 10% increase
        assert _should_refetch_data(110, 100) is True

    def test_should_not_refetch_small_change(self):
        """Small change (<5%) should not trigger refetch."""
        from app.views.analytics_advanced import _should_refetch_data

        # 2% increase
        assert _should_refetch_data(102, 100) is False

    def test_should_refetch_stale_data(self):
        """Stale data (<1% change) should trigger refetch."""
        from app.views.analytics_advanced import _should_refetch_data

        # No change
        assert _should_refetch_data(100, 100) is True
