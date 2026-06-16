"""Tests for Advanced Analytics Skills."""

from __future__ import annotations
import pytest


import numpy as np
import pandas as pd
import pytest

from socrata_toolkit.analytics.advanced import Segmentation, TimeSeriesForecasting


@pytest.fixture
def time_series_df():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    # Linear trend + noise
    values = np.linspace(10, 110, 100) + np.random.normal(0, 2, 100)
    return pd.DataFrame({"date": dates, "value": values})


class TestTimeSeriesForecasting:
    def test_forecasting_execution(self, time_series_df):
        skill = TimeSeriesForecasting()
        result = skill.run(df=time_series_df, date_col="date", value_col="value", periods=10)

        assert result.success is True
        assert "forecast" in result.data
        assert len(result.data["forecast"]) == 10
        assert "metrics" in result.data
        assert "rmse" in result.data["metrics"]


class TestSegmentation:
    def test_segmentation_execution(self):
        df = pd.DataFrame({"feature1": [1, 1, 5, 5, 10, 10], "feature2": [1, 2, 5, 6, 10, 11]})
        skill = Segmentation()
        result = skill.run(df=df, n_clusters=3)

        assert result.success is True
        assert "clusters" in result.data
        assert len(result.data["clusters"]) == 6
        assert len(set(result.data["clusters"])) == 3
