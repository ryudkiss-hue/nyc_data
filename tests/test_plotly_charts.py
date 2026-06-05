import pandas as pd
import pytest

try:
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from socrata_toolkit.viz import (
    borough_bar_chart,
    contract_gantt,
    correlation_heatmap,
    hypothesis_test_results,
    inspector_performance_boxplot,
    kpi_gauge,
    priority_heatmap,
    save_chart,
    status_donut,
    trend_line,
    waterfall_chart,
)


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
class TestPlotlyCharts:
    def test_borough_bar_chart(self):
        df = pd.DataFrame(
            {"borough": ["MANHATTAN", "BROOKLYN", "MANHATTAN"], "violations": [5, 8, 3]}
        )
        fig = borough_bar_chart(df)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_kpi_gauge(self):
        fig = kpi_gauge(1.8, "Defect Density", target=2.0)
        assert fig is not None

    def test_contract_gantt(self):
        df = pd.DataFrame(
            {
                "contract_id": ["C1", "C2"],
                "start_date": ["2024-01-01", "2024-06-01"],
                "end_date": ["2025-06-30", "2025-01-31"],
                "status": ["in_progress", "complete"],
            }
        )
        fig = contract_gantt(df)
        assert fig is not None

    def test_priority_heatmap(self):
        df = pd.DataFrame(
            {
                "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN"],
                "status": ["Pending", "Complete", "Pending"],
                "violations": [5, 3, 8],
            }
        )
        fig = priority_heatmap(df)
        assert fig is not None

    def test_trend_line(self):
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame({"dt": dates, "val": range(30)})
        fig = trend_line(df, "dt", "val")
        assert fig is not None

    def test_status_donut(self):
        df = pd.DataFrame(
            {"status": ["Pending Repair", "Complete", "Pending Repair", "Complete", "Complete"]}
        )
        fig = status_donut(df)
        assert fig is not None

    def test_save_chart_html(self, tmp_path):
        fig = kpi_gauge(5.0, "Test", target=10.0)
        path = str(tmp_path / "chart.html")
        result = save_chart(fig, path)
        assert result == path
        assert "plotly" in open(path, encoding="utf-8").read().lower()

    def test_hypothesis_test_results(self):
        group_names = ["Borough A", "Borough B", "Borough C"]
        p_values = [0.001, 0.05, 0.2]
        effect_sizes = [0.8, 0.5, 0.2]
        fig = hypothesis_test_results(group_names, p_values, effect_sizes)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_waterfall_chart(self):
        categories = ["Initial", "Factor A", "Factor B", "Final"]
        values = [100, 50, -30, 120]
        fig = waterfall_chart(categories, values)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_correlation_heatmap(self):
        df = pd.DataFrame(
            {
                "metric1": [1, 2, 3, 4, 5],
                "metric2": [2, 4, 6, 8, 10],
                "metric3": [5, 4, 3, 2, 1],
            }
        )
        fig = correlation_heatmap(df)
        assert fig is not None
        assert hasattr(fig, "to_html")

    def test_correlation_heatmap_with_selection(self):
        df = pd.DataFrame(
            {
                "metric1": [1, 2, 3, 4, 5],
                "metric2": [2, 4, 6, 8, 10],
                "metric3": [5, 4, 3, 2, 1],
                "text_col": ["a", "b", "c", "d", "e"],
            }
        )
        fig = correlation_heatmap(df, numeric_cols=["metric1", "metric2"])
        assert fig is not None

    def test_inspector_performance_boxplot(self):
        df = pd.DataFrame(
            {
                "inspector": ["A", "A", "B", "B", "C"],
                "score": [80, 85, 70, 75, 90],
            }
        )
        fig = inspector_performance_boxplot(df)
        assert fig is not None
        assert hasattr(fig, "to_html")
