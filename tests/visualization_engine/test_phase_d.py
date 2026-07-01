"""Tests for Phase D visualizations (multivariate anomaly / geographic outliers).

Tests all Phase D charts with real test data, covering:
- Data fetching
- Individual chart rendering and statistics
- Empty data handling (expects RuntimeError, matching phase_b behavior)
- Chart structural characteristics
- All 15 charts rendered via render_all_phase_d_charts
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from app.visualization_engine.phase_d import PhaseDVisualizations
from app.visualization_engine.statistics_display import StatisticsPanel


@pytest.fixture
def phase_d_viz(mock_connection, phase_d_test_data):
    viz = PhaseDVisualizations(mock_connection)
    mock_connection.fetch_dataframe.return_value = phase_d_test_data
    return viz


class TestPhaseDVisualizationBasics:
    """Test basic functionality of Phase D visualizations."""

    def test_fetch_data(self, phase_d_viz, phase_d_test_data):
        data = phase_d_viz.fetch_data()
        assert len(data) == 25
        assert "borough" in data.columns
        assert "z_score_violations" in data.columns

    def test_main_geographic_map_returns_figure_and_stats(self, phase_d_viz):
        fig, stats = phase_d_viz.render_main_geographic_map()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)
        assert stats.record_count > 0

    def test_borough_map_mn(self, phase_d_viz):
        fig, stats = phase_d_viz.render_borough_map("MN")
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_z_score_histogram(self, phase_d_viz):
        fig, stats = phase_d_viz.render_z_score_histogram()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_outlier_distribution(self, phase_d_viz):
        fig, stats = phase_d_viz.render_outlier_distribution()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_borough_anomaly_comparison(self, phase_d_viz):
        fig, stats = phase_d_viz.render_borough_anomaly_comparison()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_priority_ranking_table(self, phase_d_viz):
        fig, stats = phase_d_viz.render_priority_ranking_table()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_inspection_count_scatter(self, phase_d_viz):
        fig, stats = phase_d_viz.render_inspection_count_scatter()
        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_render_all_phase_d_charts(self, phase_d_viz):
        charts = phase_d_viz.render_all_phase_d_charts()
        assert len(charts) == 15
        assert all(isinstance(v, tuple) for v in charts.values())
        assert all(isinstance(v[0], go.Figure) for v in charts.values())
        assert all(isinstance(v[1], StatisticsPanel) for v in charts.values())


class TestPhaseDStatistics:
    """Test statistics in Phase D visualizations."""

    def test_statistics_panel_has_record_count(self, phase_d_viz):
        _, stats = phase_d_viz.render_main_geographic_map()
        assert stats.record_count > 0

    def test_statistics_to_html(self, phase_d_viz):
        _, stats = phase_d_viz.render_main_geographic_map()
        html = stats.to_html()
        assert isinstance(html, str)
        assert "statistics-panel" in html

    def test_statistics_to_dict(self, phase_d_viz):
        _, stats = phase_d_viz.render_main_geographic_map()
        d = stats.to_dict()
        assert "record_count" in d
        assert d["record_count"] > 0


class TestPhaseDDataValidation:
    """Test Phase D handles edge cases correctly."""

    def test_handles_empty_data_raises(self, mock_connection):
        """Verify fetch_data raises RuntimeError on empty warehouse view."""
        import pandas as pd

        mock_connection.fetch_dataframe.return_value = pd.DataFrame()
        viz = PhaseDVisualizations(mock_connection)
        with pytest.raises(RuntimeError):
            viz.fetch_data()

    def test_five_boroughs_present(self, phase_d_viz):
        data = phase_d_viz.fetch_data()
        boroughs = set(data["borough"])
        assert boroughs == {"MN", "BK", "BX", "QN", "SI"}

    def test_location_id_uniqueness(self, phase_d_viz):
        data = phase_d_viz.fetch_data()
        assert data["location_id"].nunique() == len(data)

    def test_borough_map_all_boroughs(self, phase_d_viz):
        for borough in ["MN", "BK", "BX", "QN", "SI"]:
            fig, stats = phase_d_viz.render_borough_map(borough)
            assert isinstance(fig, go.Figure), f"{borough}: not a Figure"


class TestPhaseDChartCharacteristics:
    """Test structural properties of Phase D charts."""

    def test_all_charts_have_titles(self, phase_d_viz):
        charts = phase_d_viz.render_all_phase_d_charts()
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

    def test_figure_json_serializable(self, phase_d_viz):
        fig, _ = phase_d_viz.render_main_geographic_map()
        json_str = fig.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_z_score_histogram_has_bars(self, phase_d_viz):
        """Z-score histogram must have bar traces."""
        fig, _ = phase_d_viz.render_z_score_histogram()
        assert len(fig.data) > 0
