import pandas as pd
import pytest

try:
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from socrata_toolkit.analysis import (
    borough_bar_chart,
    contract_gantt,
    kpi_gauge,
    priority_heatmap,
    save_chart,
    status_donut,
    trend_line,
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
        assert "plotly" in open(path).read().lower()
