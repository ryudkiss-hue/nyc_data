import pandas as pd
import pytest

try:
    import matplotlib

    matplotlib.use("Agg")
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from socrata_toolkit.analysis import (
    bar_chart,
    box_plot,
    correlation_heatmap,
    histogram,
    quality_dashboard,
    time_series_chart,
)

@pytest.mark.skipif(not HAS_MPL, reason="matplotlib not installed")
class TestVisualization:
    def test_histogram_returns_base64(self):
        df = pd.DataFrame({"val": range(50)})
        result = histogram(df, "val")
        assert result.chart_type == "histogram"
        assert result.base64_png is not None
        assert len(result.base64_png) > 100

    def test_histogram_saves_to_file(self, tmp_path):
        df = pd.DataFrame({"val": range(50)})
        path = str(tmp_path / "hist.png")
        result = histogram(df, "val", path=path)
        assert result.path == path

    def test_bar_chart(self):
        df = pd.DataFrame({"cat": ["a", "b", "a", "c", "b", "a"]})
        result = bar_chart(df, "cat")
        assert result.chart_type == "bar_chart"
        assert result.base64_png is not None

    def test_bar_chart_horizontal(self):
        df = pd.DataFrame({"cat": ["a", "b", "c"] * 10})
        result = bar_chart(df, "cat", horizontal=True)
        assert result.base64_png is not None

    def test_correlation_heatmap(self):
        df = pd.DataFrame({"x": range(20), "y": range(20), "z": [i * -1 for i in range(20)]})
        result = correlation_heatmap(df)
        assert result.chart_type == "heatmap"
        assert result.base64_png is not None

    def test_time_series_chart(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        df = pd.DataFrame({"dt": dates, "val": range(60)})
        result = time_series_chart(df, "dt", "val")
        assert result.chart_type == "time_series"
        assert result.base64_png is not None

    def test_box_plot(self):
        df = pd.DataFrame({"a": range(30), "b": [x**2 for x in range(30)]})
        result = box_plot(df, ["a", "b"])
        assert result.chart_type == "box_plot"
        assert result.base64_png is not None

    def test_quality_dashboard(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, "x"], "c": [10, 20, 30]})
        dash = quality_dashboard(df)
        assert dash.completeness_score < 100
        assert dash.missing_cells > 0
        assert dash.missing_chart.chart_type == "quality_missing"
