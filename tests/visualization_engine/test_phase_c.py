"""Tests for Phase C visualizations (distribution classification).

Tests all Phase C charts with real test data, covering:
- Data fetching
- Individual chart rendering and statistics
- Empty data handling (expects RuntimeError, matching phase_b behavior)
- Chart structural characteristics
- All 13 charts rendered via render_all_phase_c_charts
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from app.visualization_engine.phase_c import PhaseCVisualizations
from app.visualization_engine.statistics_display import StatisticsPanel


@pytest.fixture
def phase_c_viz(mock_connection, phase_c_test_data):
    viz = PhaseCVisualizations(mock_connection)
    mock_connection.fetch_dataframe.return_value = phase_c_test_data
    return viz


class TestPhaseCVisualizationBasics:
    """Test basic functionality of Phase C visualizations."""

    def test_fetch_data(self, phase_c_viz, phase_c_test_data):
        data = phase_c_viz.fetch_data()
        assert len(data) == 5
        assert "borough" in data.columns
        assert "skewness" in data.columns

    def test_main_histogram_returns_figure_and_stats(self, phase_c_viz):
        fig, stats = phase_c_viz.render_main_histogram()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)
        assert stats.record_count > 0

    def test_distribution_type_pie(self, phase_c_viz):
        fig, stats = phase_c_viz.render_distribution_type_pie()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_box_plot(self, phase_c_viz):
        fig, stats = phase_c_viz.render_box_plot()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_mean_vs_median_scatter(self, phase_c_viz):
        fig, stats = phase_c_viz.render_mean_vs_median_scatter()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_skewness_chart(self, phase_c_viz):
        fig, stats = phase_c_viz.render_skewness_chart()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_std_dev_chart(self, phase_c_viz):
        fig, stats = phase_c_viz.render_std_dev_chart()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_concentration_gauge(self, phase_c_viz):
        fig, stats = phase_c_viz.render_concentration_gauge()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_concentration_comparison(self, phase_c_viz):
        fig, stats = phase_c_viz.render_concentration_comparison()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_borough_histogram_mn(self, phase_c_viz):
        fig, stats = phase_c_viz.render_borough_histogram("MN")
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_render_all_phase_c_charts(self, phase_c_viz):
        charts = phase_c_viz.render_all_phase_c_charts()
        assert len(charts) == 13
        assert all(isinstance(v, tuple) for v in charts.values())
        assert all(isinstance(v[0], go.Figure) for v in charts.values())
        assert all(isinstance(v[1], StatisticsPanel) for v in charts.values())


class TestPhaseCStatistics:
    """Test statistics in Phase C visualizations."""

    def test_statistics_panel_has_record_count(self, phase_c_viz):
        _, stats = phase_c_viz.render_main_histogram()
        assert stats.record_count > 0

    def test_statistics_to_html(self, phase_c_viz):
        _, stats = phase_c_viz.render_main_histogram()
        html = stats.to_html()
        assert isinstance(html, str)
        assert "statistics-panel" in html

    def test_statistics_to_dict(self, phase_c_viz):
        _, stats = phase_c_viz.render_main_histogram()
        d = stats.to_dict()
        assert "record_count" in d
        assert d["record_count"] > 0


class TestPhaseCDataValidation:
    """Test Phase C handles edge cases correctly."""

    def test_handles_empty_data_raises(self, mock_connection):
        """Verify fetch_data raises RuntimeError on empty warehouse view."""
        import pandas as pd

        mock_connection.fetch_dataframe.return_value = pd.DataFrame()
        viz = PhaseCVisualizations(mock_connection)
        with pytest.raises(RuntimeError):
            viz.fetch_data()

    def test_five_boroughs_present(self, phase_c_viz):
        data = phase_c_viz.fetch_data()
        boroughs = set(data["borough"])
        assert boroughs == {"MN", "BK", "BX", "QN", "SI"}

    def test_borough_histogram_all_boroughs(self, phase_c_viz):
        for borough in ["MN", "BK", "BX", "QN", "SI"]:
            fig, stats = phase_c_viz.render_borough_histogram(borough)
            assert isinstance(fig, go.Figure), f"{borough}: not a Figure"


class TestPhaseCChartCharacteristics:
    """Test structural properties of Phase C charts."""

    def test_all_charts_have_titles(self, phase_c_viz):
        charts = phase_c_viz.render_all_phase_c_charts()
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

    def test_figure_json_serializable(self, phase_c_viz):
        fig, _ = phase_c_viz.render_main_histogram()
        json_str = fig.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_distribution_type_pie_has_labels(self, phase_c_viz):
        """Pie chart must have labelled slices."""
        fig, _ = phase_c_viz.render_distribution_type_pie()
        assert len(fig.data) > 0
        pie = fig.data[0]
        assert hasattr(pie, "labels") and len(pie.labels) > 0
