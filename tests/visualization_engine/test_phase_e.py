"""Tests for Phase E visualizations (time series decomposition).

Tests all Phase E charts with real test data, covering:
- Data fetching
- Individual chart rendering and statistics
- Empty data handling (expects RuntimeError, matching phase_b behavior)
- Chart structural characteristics
- All 16 charts rendered via render_all_phase_e_charts
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from app.visualization_engine.phase_e import PhaseEVisualizations
from app.visualization_engine.statistics_display import StatisticsPanel


@pytest.fixture
def phase_e_viz(mock_connection, phase_e_test_data):
    viz = PhaseEVisualizations(mock_connection)
    mock_connection.fetch_dataframe.return_value = phase_e_test_data
    return viz


class TestPhaseEVisualizationBasics:
    """Test basic functionality of Phase E visualizations."""

    def test_fetch_data(self, phase_e_viz, phase_e_test_data):
        data = phase_e_viz.fetch_data()
        assert len(data) > 0
        assert "borough" in data.columns
        assert "trend_value" in data.columns

    def test_main_4panel_decomposition_returns_figure_and_stats(self, phase_e_viz):
        fig, stats = phase_e_viz.render_main_4panel_decomposition()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)
        assert stats.record_count > 0

    def test_borough_4panel_decomposition_mn(self, phase_e_viz):
        fig, stats = phase_e_viz.render_borough_4panel_decomposition("MN")
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_forecast_chart(self, phase_e_viz):
        fig, stats = phase_e_viz.render_forecast_chart()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_seasonal_strength_gauge(self, phase_e_viz):
        fig, stats = phase_e_viz.render_seasonal_strength_gauge()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_trend_analysis(self, phase_e_viz):
        fig, stats = phase_e_viz.render_trend_analysis()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_render_all_phase_e_charts(self, phase_e_viz):
        charts = phase_e_viz.render_all_phase_e_charts()
        assert len(charts) == 16
        assert all(isinstance(v, tuple) for v in charts.values())
        assert all(isinstance(v[0], go.Figure) for v in charts.values())
        assert all(isinstance(v[1], StatisticsPanel) for v in charts.values())


class TestPhaseEStatistics:
    """Test statistics in Phase E visualizations."""

    def test_statistics_panel_has_record_count(self, phase_e_viz):
        _, stats = phase_e_viz.render_main_4panel_decomposition()
        assert stats.record_count > 0

    def test_statistics_to_html(self, phase_e_viz):
        _, stats = phase_e_viz.render_main_4panel_decomposition()
        html = stats.to_html()
        assert isinstance(html, str)
        assert "statistics-panel" in html

    def test_statistics_to_dict(self, phase_e_viz):
        _, stats = phase_e_viz.render_main_4panel_decomposition()
        d = stats.to_dict()
        assert "record_count" in d
        assert d["record_count"] > 0


class TestPhaseEDataValidation:
    """Test Phase E handles edge cases correctly."""

    def test_handles_empty_data_raises(self, mock_connection):
        """Verify fetch_data raises RuntimeError on empty warehouse view."""
        import pandas as pd

        mock_connection.fetch_dataframe.return_value = pd.DataFrame()
        viz = PhaseEVisualizations(mock_connection)
        with pytest.raises(RuntimeError):
            viz.fetch_data()

    def test_five_boroughs_present(self, phase_e_viz):
        data = phase_e_viz.fetch_data()
        boroughs = set(data["borough"])
        assert boroughs == {"MN", "BK", "BX", "QN", "SI"}

    def test_time_series_has_date_column(self, phase_e_viz):
        data = phase_e_viz.fetch_data()
        assert "date" in data.columns

    def test_borough_4panel_all_boroughs(self, phase_e_viz):
        for borough in ["MN", "BK", "BX", "QN", "SI"]:
            fig, stats = phase_e_viz.render_borough_4panel_decomposition(borough)
            assert isinstance(fig, go.Figure), f"{borough}: not a Figure"


class TestPhaseEChartCharacteristics:
    """Test structural properties of Phase E charts."""

    def test_all_charts_have_titles(self, phase_e_viz):
        charts = phase_e_viz.render_all_phase_e_charts()
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

    def test_figure_json_serializable(self, phase_e_viz):
        fig, _ = phase_e_viz.render_main_4panel_decomposition()
        json_str = fig.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_forecast_chart_has_traces(self, phase_e_viz):
        """Forecast chart must have at least one trace with data."""
        fig, _ = phase_e_viz.render_forecast_chart()
        assert len(fig.data) > 0

    def test_trend_analysis_has_multiple_traces(self, phase_e_viz):
        """Trend analysis should separate actual vs trend components."""
        fig, _ = phase_e_viz.render_trend_analysis()
        assert len(fig.data) >= 2, (
            "Trend analysis should have at least 2 traces (actual + trend)"
        )
