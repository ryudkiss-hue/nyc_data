"""Tests for Phase F visualizations (bootstrap CI and SLA forecast).

Tests all Phase F charts with real test data, covering:
- Data fetching
- Individual chart rendering and statistics
- Empty data handling (expects RuntimeError, matching phase_b behavior)
- Chart structural characteristics
- All 17 charts rendered via render_all_phase_f_charts
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from app.visualization_engine.phase_f import PhaseFVisualizations
from app.visualization_engine.statistics_display import StatisticsPanel


@pytest.fixture
def phase_f_viz(mock_connection, phase_f_test_data):
    viz = PhaseFVisualizations(mock_connection)
    mock_connection.fetch_dataframe.return_value = phase_f_test_data
    return viz


class TestPhaseFVisualizationBasics:
    """Test basic functionality of Phase F visualizations."""

    def test_fetch_data(self, phase_f_viz, phase_f_test_data):
        data = phase_f_viz.fetch_data()
        assert len(data) == 5
        assert "borough" in data.columns
        assert "prob_meets_sla" in data.columns

    def test_main_sla_gauge_returns_figure_and_stats(self, phase_f_viz):
        fig, stats = phase_f_viz.render_main_sla_gauge()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)
        assert stats.record_count > 0

    def test_borough_sla_gauge_mn(self, phase_f_viz):
        fig, stats = phase_f_viz.render_borough_sla_gauge("MN")
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_ci_visualization(self, phase_f_viz):
        fig, stats = phase_f_viz.render_ci_visualization()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_ci_width_comparison(self, phase_f_viz):
        fig, stats = phase_f_viz.render_ci_width_comparison()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_point_estimate_comparison(self, phase_f_viz):
        fig, stats = phase_f_viz.render_point_estimate_comparison()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_probability_distribution(self, phase_f_viz):
        fig, stats = phase_f_viz.render_probability_distribution()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_risk_level_indicator(self, phase_f_viz):
        fig, stats = phase_f_viz.render_risk_level_indicator()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_render_all_phase_f_charts(self, phase_f_viz):
        charts = phase_f_viz.render_all_phase_f_charts()
        assert len(charts) == 17
        assert all(isinstance(v, tuple) for v in charts.values())
        assert all(isinstance(v[0], go.Figure) for v in charts.values())
        assert all(isinstance(v[1], StatisticsPanel) for v in charts.values())


class TestPhaseFStatistics:
    """Test statistics in Phase F visualizations."""

    def test_statistics_panel_has_record_count(self, phase_f_viz):
        _, stats = phase_f_viz.render_main_sla_gauge()
        assert stats.record_count > 0

    def test_statistics_to_html(self, phase_f_viz):
        _, stats = phase_f_viz.render_main_sla_gauge()
        html = stats.to_html()
        assert isinstance(html, str)
        assert "statistics-panel" in html

    def test_statistics_to_dict(self, phase_f_viz):
        _, stats = phase_f_viz.render_main_sla_gauge()
        d = stats.to_dict()
        assert "record_count" in d
        assert d["record_count"] > 0


class TestPhaseFDataValidation:
    """Test Phase F handles edge cases correctly."""

    def test_handles_empty_data_raises(self, mock_connection):
        """Verify fetch_data raises RuntimeError on empty warehouse view."""
        import pandas as pd

        mock_connection.fetch_dataframe.return_value = pd.DataFrame()
        viz = PhaseFVisualizations(mock_connection)
        with pytest.raises(RuntimeError):
            viz.fetch_data()

    def test_five_boroughs_present(self, phase_f_viz):
        data = phase_f_viz.fetch_data()
        boroughs = set(data["borough"])
        assert boroughs == {"MN", "BK", "BX", "QN", "SI"}

    def test_ci_bounds_are_valid(self, phase_f_viz):
        data = phase_f_viz.fetch_data()
        assert (data["ci_lower_95"] <= data["point_estimate"]).all()
        assert (data["point_estimate"] <= data["ci_upper_95"]).all()

    def test_risk_levels_are_valid(self, phase_f_viz):
        data = phase_f_viz.fetch_data()
        valid_levels = {"HIGH", "MEDIUM", "LOW"}
        assert set(data["risk_level"]).issubset(valid_levels)

    def test_borough_sla_gauge_all_boroughs(self, phase_f_viz):
        for borough in ["MN", "BK", "BX", "QN", "SI"]:
            fig, stats = phase_f_viz.render_borough_sla_gauge(borough)
            assert isinstance(fig, go.Figure), f"{borough}: not a Figure"


class TestPhaseFChartCharacteristics:
    """Test structural properties of Phase F charts."""

    def test_all_charts_have_titles(self, phase_f_viz):
        charts = phase_f_viz.render_all_phase_f_charts()
        for name, (fig, _) in charts.items():
            has_layout_title = fig.layout.title and fig.layout.title.text
            has_trace_title = any(
                hasattr(t, "title")
                and t.title
                and (
                    isinstance(t.title, dict) and t.title.get("text")
                    or hasattr(t.title, "text") and t.title.text
                )
                for t in fig.data
                if hasattr(t, "title")
            )
            assert has_layout_title or has_trace_title, f"{name}: has no title"

    def test_figure_json_serializable(self, phase_f_viz):
        fig, _ = phase_f_viz.render_main_sla_gauge()
        json_str = fig.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_ci_visualization_has_uncertainty_representation(self, phase_f_viz):
        """CI chart must visually represent uncertainty bounds."""
        fig, _ = phase_f_viz.render_ci_visualization()
        has_error_bars = any(
            getattr(t, "error_y", None) is not None for t in fig.data
        )
        has_fill = any(
            getattr(t, "fill", None) not in (None, "none") for t in fig.data
        )
        assert has_error_bars or has_fill, (
            "CI visualization must show uncertainty via error bars or filled bands"
        )

    def test_risk_level_indicator_has_traces(self, phase_f_viz):
        """Risk level chart must have at least one data trace."""
        fig, _ = phase_f_viz.render_risk_level_indicator()
        assert len(fig.data) > 0, "Risk level indicator has no traces"
