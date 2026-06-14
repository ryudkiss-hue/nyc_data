"""Integration tests for all 73 visualizations.

Verifies that all visualizations can render with real test data
and that the total count matches expectations.
"""
import plotly.graph_objects as go
import pytest

from app.visualization_engine import (
    KPICards,
    PhaseBVisualizations,
    PhaseCVisualizations,
    PhaseDVisualizations,
    PhaseEVisualizations,
    PhaseFVisualizations,
    StatisticsPanel,
)


class TestPhase2VisualizationCounts:
    """Test that all visualization counts are correct."""

    def test_phase_b_has_12_charts(self, mock_connection, phase_b_test_data):
        """Test Phase B has exactly 12 visualizations."""
        viz = PhaseBVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_b_test_data
        charts = viz.render_all_phase_b_charts()

        assert len(charts) == 12, f"Phase B should have 12 charts, got {len(charts)}"

    def test_phase_c_has_13_charts(self, mock_connection, phase_c_test_data):
        """Test Phase C has exactly 13 visualizations."""
        viz = PhaseCVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_c_test_data
        charts = viz.render_all_phase_c_charts()

        assert len(charts) == 13, f"Phase C should have 13 charts, got {len(charts)}"

    def test_phase_d_has_15_charts(self, mock_connection, phase_d_test_data):
        """Test Phase D has exactly 15 visualizations."""
        viz = PhaseDVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_d_test_data
        charts = viz.render_all_phase_d_charts()

        assert len(charts) == 15, f"Phase D should have 15 charts, got {len(charts)}"

    def test_phase_e_has_16_charts(self, mock_connection, phase_e_test_data):
        """Test Phase E has exactly 16 visualizations."""
        viz = PhaseEVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_e_test_data
        charts = viz.render_all_phase_e_charts()

        assert len(charts) == 16, f"Phase E should have 16 charts, got {len(charts)}"

    def test_phase_f_has_17_charts(self, mock_connection, phase_f_test_data):
        """Test Phase F has exactly 17 visualizations."""
        viz = PhaseFVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_f_test_data
        charts = viz.render_all_phase_f_charts()

        assert len(charts) == 17, f"Phase F should have 17 charts, got {len(charts)}"

    def test_total_visualizations_is_73(self, mock_connection, phase_b_test_data,
                                         phase_c_test_data, phase_d_test_data,
                                         phase_e_test_data, phase_f_test_data):
        """Test that total visualization count is 73."""
        # Phase B: 12
        viz_b = PhaseBVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_b_test_data
        count_b = len(viz_b.render_all_phase_b_charts())

        # Phase C: 13
        viz_c = PhaseCVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_c_test_data
        count_c = len(viz_c.render_all_phase_c_charts())

        # Phase D: 15
        viz_d = PhaseDVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_d_test_data
        count_d = len(viz_d.render_all_phase_d_charts())

        # Phase E: 16
        viz_e = PhaseEVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_e_test_data
        count_e = len(viz_e.render_all_phase_e_charts())

        # Phase F: 17
        viz_f = PhaseFVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_f_test_data
        count_f = len(viz_f.render_all_phase_f_charts())

        total = count_b + count_c + count_d + count_e + count_f
        assert total == 73, f"Total should be 73 visualizations, got {total}"

class TestAllVisualizationsRender:
    """Test that all visualizations can render without errors."""

    def test_all_phase_b_charts_render(self, mock_connection, phase_b_test_data):
        """Test all Phase B charts render successfully."""
        viz = PhaseBVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_b_test_data
        charts = viz.render_all_phase_b_charts()

        for name, (fig, stats) in charts.items():
            assert isinstance(fig, go.Figure), f"{name}: figure is not a go.Figure"
            assert isinstance(stats, StatisticsPanel), f"{name}: stats is not StatisticsPanel"
            assert stats.record_count > 0, f"{name}: record_count is 0"

    def test_all_phase_c_charts_render(self, mock_connection, phase_c_test_data):
        """Test all Phase C charts render successfully."""
        viz = PhaseCVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_c_test_data
        charts = viz.render_all_phase_c_charts()

        for name, (fig, stats) in charts.items():
            assert isinstance(fig, go.Figure), f"{name}: figure is not a go.Figure"
            assert isinstance(stats, StatisticsPanel), f"{name}: stats is not StatisticsPanel"

    def test_all_phase_d_charts_render(self, mock_connection, phase_d_test_data):
        """Test all Phase D charts render successfully."""
        viz = PhaseDVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_d_test_data
        charts = viz.render_all_phase_d_charts()

        for name, (fig, stats) in charts.items():
            assert isinstance(fig, go.Figure), f"{name}: figure is not a go.Figure"
            assert isinstance(stats, StatisticsPanel), f"{name}: stats is not StatisticsPanel"

    def test_all_phase_e_charts_render(self, mock_connection, phase_e_test_data):
        """Test all Phase E charts render successfully."""
        viz = PhaseEVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_e_test_data
        charts = viz.render_all_phase_e_charts()

        for name, (fig, stats) in charts.items():
            assert isinstance(fig, go.Figure), f"{name}: figure is not a go.Figure"
            assert isinstance(stats, StatisticsPanel), f"{name}: stats is not StatisticsPanel"

    def test_all_phase_f_charts_render(self, mock_connection, phase_f_test_data):
        """Test all Phase F charts render successfully."""
        viz = PhaseFVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_f_test_data
        charts = viz.render_all_phase_f_charts()

        for name, (fig, stats) in charts.items():
            assert isinstance(fig, go.Figure), f"{name}: figure is not a go.Figure"
            assert isinstance(stats, StatisticsPanel), f"{name}: stats is not StatisticsPanel"

class TestKPICards:
    """Test KPI card rendering."""

    def test_kpi_has_18_metrics(self, mock_connection, kpi_test_data):
        """Test that KPI dashboard has 18 metrics."""
        kpi = KPICards(mock_connection)
        mock_connection.fetch_dataframe.return_value = kpi_test_data

        kpi_names = kpi.get_kpi_names()
        assert len(kpi_names) == 18, f"KPI should have 18 metrics, got {len(kpi_names)}"

    def test_all_kpi_cards_render(self, mock_connection, kpi_test_data):
        """Test all KPI cards render successfully."""
        kpi = KPICards(mock_connection)
        mock_connection.fetch_dataframe.return_value = kpi_test_data
        cards = kpi.render_all_kpi_cards()

        assert len(cards) == 18, f"Expected 18 KPI cards, got {len(cards)}"

        for name, (fig, stats) in cards.items():
            assert isinstance(fig, go.Figure), f"{name}: figure is not a go.Figure"
            assert isinstance(stats, StatisticsPanel), f"{name}: stats is not StatisticsPanel"

    def test_borough_radars_render(self, mock_connection, kpi_test_data):
        """Test borough KPI radar charts render successfully."""
        kpi = KPICards(mock_connection)
        mock_connection.fetch_dataframe.return_value = kpi_test_data
        radars = kpi.render_all_borough_radars()

        assert len(radars) == 5, f"Expected 5 borough radars, got {len(radars)}"

        for name, (fig, stats) in radars.items():
            assert isinstance(fig, go.Figure), f"{name}: figure is not a go.Figure"
            assert isinstance(stats, StatisticsPanel), f"{name}: stats is not StatisticsPanel"

    def test_kpi_summary_table(self, mock_connection, kpi_test_data):
        """Test KPI summary table renders successfully."""
        kpi = KPICards(mock_connection)
        mock_connection.fetch_dataframe.return_value = kpi_test_data
        fig, stats = kpi.render_kpi_summary_table()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

    def test_kpi_comparison_chart(self, mock_connection, kpi_test_data):
        """Test KPI comparison chart renders successfully."""
        kpi = KPICards(mock_connection)
        mock_connection.fetch_dataframe.return_value = kpi_test_data
        fig, stats = kpi.render_kpi_comparison_chart()

        assert isinstance(fig, go.Figure)
        assert isinstance(stats, StatisticsPanel)

class TestStatisticsDisplay:
    """Test statistics display component."""

    def test_statistics_panel_initialization(self):
        """Test that StatisticsPanel initializes correctly."""
        stats = StatisticsPanel(
            record_count=100,
            mean_value=50.5,
            min_value=0,
            max_value=100,
            calculation_method="Test",
            confidence_level="95%",
        )

        assert stats.record_count == 100
        assert stats.mean_value == 50.5

    def test_statistics_panel_to_html(self):
        """Test that StatisticsPanel generates valid HTML."""
        stats = StatisticsPanel(
            record_count=100,
            mean_value=50.5,
            min_value=0,
            max_value=100,
            calculation_method="Test",
            confidence_level="95%",
        )

        html = stats.to_html()
        assert isinstance(html, str)
        assert "statistics-panel" in html
        assert "100" in html
        assert "50.5" in html

    def test_statistics_panel_to_dict(self):
        """Test that StatisticsPanel converts to dictionary."""
        stats = StatisticsPanel(
            record_count=100,
            mean_value=50.5,
            min_value=0,
            max_value=100,
            calculation_method="Test",
            confidence_level="95%",
        )

        stats_dict = stats.to_dict()
        assert stats_dict["record_count"] == 100
        assert stats_dict["mean_value"] == 50.5
        assert stats_dict["calculation_method"] == "Test"

class TestDataSerialization:
    """Test that figures can be serialized for JSON output."""

    def test_phase_b_figure_serializable(self, mock_connection, phase_b_test_data):
        """Test that Phase B figures can be converted to JSON."""
        viz = PhaseBVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_b_test_data
        fig, stats = viz.render_main_gauge_chart()

        # Convert to JSON (for Dash transmission)
        json_str = fig.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_statistics_json_compatible(self, mock_connection, phase_b_test_data):
        """Test that statistics are JSON-compatible."""
        viz = PhaseBVisualizations(mock_connection)
        mock_connection.fetch_dataframe.return_value = phase_b_test_data
        fig, stats = viz.render_main_gauge_chart()

        import json
        stats_dict = stats.to_dict()
        json_str = json.dumps(stats_dict, default=str)
        assert isinstance(json_str, str)
