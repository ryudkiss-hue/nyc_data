import pytest

import pandas as pd

from socrata_toolkit.analysis import (
    classify_all_distributions,
    classify_distribution,
    correlation_analysis,
    detect_all_outliers,
    detect_outliers_iqr,
    detect_outliers_zscore,
    flag_anomalies,
    time_series_summary,
)

# -- Outlier Detection -------------------------------------------------------

def test_detect_outliers_iqr_basic():
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100]})
    r = detect_outliers_iqr(df, "val")
    assert r.column == "val"
    assert r.method == "iqr"
    assert r.outlier_count >= 1
    assert 100 in [df.loc[i, "val"] for i in r.outlier_indices]

def test_detect_outliers_zscore_basic():
    df = pd.DataFrame({"val": [10, 10, 10, 10, 10, 10, 10, 10, 10, 500]})
    r = detect_outliers_zscore(df, "val", threshold=2.0)
    assert r.outlier_count >= 1

def test_detect_outliers_zscore_zero_std():
    df = pd.DataFrame({"val": [5, 5, 5, 5]})
    r = detect_outliers_zscore(df, "val")
    assert r.outlier_count == 0

def test_detect_all_outliers():
    df = pd.DataFrame({"a": [1, 2, 3, 100], "b": [10, 20, 30, 40], "c": ["x", "y", "z", "w"]})
    reports = detect_all_outliers(df, method="iqr")
    # Should only process numeric columns a and b
    assert len(reports) == 2
    cols = {r.column for r in reports}
    assert cols == {"a", "b"}

# -- Correlation Analysis ----------------------------------------------------

def test_correlation_analysis_basic():
    df = pd.DataFrame({"x": range(20), "y": range(20), "z": [i * -1 for i in range(20)]})
    result = correlation_analysis(df, threshold=0.5)
    assert len(result.pairs) >= 1
    # x and y are perfectly correlated
    xy = [p for p in result.pairs if set([p["column_a"], p["column_b"]]) == {"x", "y"}]
    assert len(xy) == 1
    assert xy[0]["correlation"] > 0.99

def test_correlation_analysis_no_numeric():
    df = pd.DataFrame({"a": ["x", "y"], "b": ["m", "n"]})
    result = correlation_analysis(df)
    assert result.pairs == []

# -- Time Series Summary -----------------------------------------------------

def test_time_series_summary_increasing():
    dates = pd.date_range("2024-01-01", periods=50, freq="D")
    df = pd.DataFrame({"dt": dates, "val": range(50)})
    s = time_series_summary(df, "dt", "val")
    assert s.trend_direction == "increasing"
    assert s.trend_slope > 0
    assert s.count == 50

def test_time_series_summary_empty():
    df = pd.DataFrame({"dt": [], "val": []})
    s = time_series_summary(df, "dt", "val")
    assert s.count == 0
    assert s.trend_direction == "flat"

# -- Distribution Classification ---------------------------------------------

def test_classify_distribution_normal():
    rng = pd.array([float(x) for x in range(-50, 51)])
    df = pd.DataFrame({"v": rng})
    d = classify_distribution(df, "v")
    assert d.classification in ("normal", "uniform")
    assert d.sample_size == 101

def test_classify_distribution_sparse():
    df = pd.DataFrame({"v": [1, 2]})
    d = classify_distribution(df, "v")
    assert d.classification == "sparse"

def test_classify_all_distributions():
    df = pd.DataFrame({"a": range(20), "b": [x**2 for x in range(20)], "c": ["t"] * 20})
    results = classify_all_distributions(df)
    assert len(results) == 2  # only numeric columns

# -- Anomaly Flagging --------------------------------------------------------

def test_flag_anomalies():
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 500]})
    flagged, report = flag_anomalies(df)
    assert "_anomaly" in flagged.columns
    assert report.flagged_rows >= 1
    assert report.total_rows == 6
