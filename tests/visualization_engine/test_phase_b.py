"""Tests for Phase B visualizations (spatial clustering).

Tests all 12 Phase B charts with real test data.
"""
import pytest
import plotly.graph_objects as go
from app.visualization_engine.phase_b import PhaseBVisualizations
from app.visualization_engine.statistics_display import StatisticsPanel

@pytest.fixture
def phase_b_viz(mock_connection, phase_b_test_data):
    """Create Phase B visualizations instance with mocked connection.

    Args:
        mock_connection: Mocked MotherDuckConnection
        phase_b_test_data: Test data for Phase B

    Returns:
        PhaseBVisualizations instance
    """
    viz = PhaseBVisualizations(mock_connection)
    mock_connection.fetch_dataframe.return_value = phase_b_test_data
    return viz

class TestPhaseBVisualizationBasics:
    """Test basic functionality of Phase B visualizations."""

    def test_fetch_data(self, phase_b_viz, phase_b_test_data):
        """Test data fetching from MotherDuck."""
        data = phase_b_viz.fetch_data()
        assert len(data) == 5
        assert "morans_i_value" in data.columns
        assert "borough" in data.columns

    def test_main_gauge_chart_returns_figure_and_stats(self, phase_b_viz):
        """Test that main gauge chart returns valid figure and statistics."""
        fig, stats = phase_b_viz.render_main_gauge_chart()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)
        assert stats.record_count == 5
        assert stats.mean_value is not None

    def test_borough_gauge_mn(self, phase_b_viz):
        """Test Manhattan gauge chart."""
        fig, stats = phase_b_viz.render_borough_gauge("MN")

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)
        assert stats.record_count > 0

    def test_borough_gauge_invalid(self, phase_b_viz):
        """Test that invalid borough raises error."""
        with pytest.raises(ValueError):
            phase_b_viz.render_borough_gauge("INVALID")

    def test_classification_heatmap(self, phase_b_viz):
        """Test classification heatmap rendering."""
        fig, stats = phase_b_viz.render_classification_heatmap()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_p_value_scatter(self, phase_b_viz):
        """Test p-value scatter chart."""
        fig, stats = phase_b_viz.render_p_value_scatter()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)
        # Check that statistics include significance count
        assert "Significant Results (p<0.05)" in stats.additional_stats

    def test_location_count_bar(self, phase_b_viz):
        """Test location count bar chart."""
        fig, stats = phase_b_viz.render_location_count_bar()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_classification_pie(self, phase_b_viz):
        """Test classification pie chart."""
        fig, stats = phase_b_viz.render_classification_pie()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_significance_indicator(self, phase_b_viz):
        """Test significance indicator."""
        fig, stats = phase_b_viz.render_significance_indicator()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_render_all_phase_b_charts(self, phase_b_viz):
        """Test rendering all Phase B charts."""
        charts = phase_b_viz.render_all_phase_b_charts()

        assert len(charts) == 12
        assert all(isinstance(v, tuple) for v in charts.values())
        assert all(isinstance(v[0], go.Figure) for v in charts.values())
        assert all(isinstance(v[1], StatisticsPanel) for v in charts.values())

class TestPhaseBStatistics:
    """Test statistics calculation in Phase B visualizations."""

    def test_statistics_panel_has_required_fields(self, phase_b_viz):
        """Test that statistics panels include required information."""
        fig, stats = phase_b_viz.render_main_gauge_chart()

        assert stats.record_count > 0
        assert stats.mean_value is not None
        assert stats.last_timestamp is not None
        assert stats.calculation_method is not None
        assert stats.confidence_level is not None

    def test_statistics_to_html(self, phase_b_viz):
        """Test that statistics can be converted to HTML."""
        fig, stats = phase_b_viz.render_main_gauge_chart()
        html = stats.to_html()

        assert isinstance(html, str)
        assert "statistics-panel" in html
        assert "Summary Statistics" in html
        assert "Records:" in html

    def test_statistics_to_dict(self, phase_b_viz):
        """Test that statistics can be converted to dictionary."""
        fig, stats = phase_b_viz.render_main_gauge_chart()
        stats_dict = stats.to_dict()

        assert isinstance(stats_dict, dict)
        assert "record_count" in stats_dict
        assert "mean_value" in stats_dict
        assert "last_timestamp" in stats_dict

class TestPhaseBDataValidation:
    """Test data validation in Phase B visualizations."""

    def test_handles_empty_data(self, mock_connection):
        """Test that empty data is handled gracefully."""
        import pandas as pd

        viz = PhaseBVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = pd.DataFrame()

        with pytest.raises(RuntimeError):
            viz.fetch_data()

    def test_borough_codes(self, phase_b_viz):
        """Test all 5 borough codes are supported."""
        boroughs = ["MN", "BK", "BX", "QN", "SI"]
        for borough in boroughs:
            fig, stats = phase_b_viz.render_borough_gauge(borough)
            assert isinstance(fig, go.Figure)

class TestPhaseBChartCharacteristics:
    """Test specific characteristics of Phase B charts."""

    def test_main_gauge_has_delta(self, phase_b_viz):
        """Test that main gauge includes delta reference."""
        fig, stats = phase_b_viz.render_main_gauge_chart()
        # Check that figure has indicator with delta
        assert any("delta" in str(trace).lower() for trace in fig.data)

    def test_scatter_has_threshold_line(self, phase_b_viz):
        """Test that p-value scatter has threshold line."""
        fig, stats = phase_b_viz.render_p_value_scatter()
        # Check for hline (p=0.05 threshold)
        assert len(fig.layout.shapes) > 0

    def test_charts_have_proper_dimensions(self, phase_b_viz):
        """Test that charts have proper height/width settings."""
        fig, stats = phase_b_viz.render_main_gauge_chart()
        assert fig.layout.height > 0
        assert fig.layout.font.family == "Arial, sans-serif"

    def test_all_charts_have_titles(self, phase_b_viz):
        """Test that all charts have titles or title in trace."""
        charts = phase_b_viz.render_all_phase_b_charts()
        for name, (fig, stats) in charts.items():
            # Check either layout title or indicator title in trace
            has_layout_title = fig.layout.title and fig.layout.title.text
            has_trace_title = any(
                hasattr(trace, 'title') and trace.title and
                (isinstance(trace.title, dict) and trace.title.get('text') or
                 hasattr(trace.title, 'text') and trace.title.text)
                for trace in fig.data if hasattr(trace, 'title')
            )
            assert has_layout_title or has_trace_title, f"{name} has no title"
