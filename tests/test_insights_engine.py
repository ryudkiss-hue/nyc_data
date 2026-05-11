import pandas as pd
import pytest

from socrata_toolkit.analysis.insights import (
    InsightsReport,
    generate_insights,
    smart_recommendations,
)


def _sample_data():
    return pd.DataFrame({
        "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
        "status": ["Pending Repair", "Complete", "Pending Repair", "Pending Repair", "Complete"],
        "severity_rating": [8, 3, 9, 2, 5],
        "violations": [5, 1, 10, 0, 3],
        "complaint_count": [3, 0, 7, 1, 2],
        "estimated_sqft": [200, 50, 500, 30, 100],
        "inspection_date": ["2024-01-15", "2024-03-20", "2024-02-10", "2024-06-01", "2024-04-15"],
    })


def test_generate_insights_basic():
    df = _sample_data()
    report = generate_insights(df)
    assert isinstance(report, InsightsReport)
    assert report.data_health in ("good", "fair", "poor")
    assert len(report.summary) > 0
    assert report.key_metrics.get("Row Count") == 5


def test_generate_insights_has_quality_metrics():
    df = _sample_data()
    report = generate_insights(df)
    assert "Quality Score" in report.key_metrics
    assert "Completeness" in report.key_metrics


def test_generate_insights_borough_analysis():
    df = _sample_data()
    report = generate_insights(df, borough_col="borough")
    assert len(report.borough_insights) > 0
    assert "MANHATTAN" in report.borough_insights


def test_generate_insights_with_missing_data():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["a", None, None],
        "value": [10, None, 30],
    })
    report = generate_insights(df)
    # Should detect missing data
    quality_insights = [i for i in report.insights if i.category == "quality"]
    assert len(quality_insights) > 0


def test_generate_insights_with_outliers():
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100, 2, 3, 4, 5]})
    report = generate_insights(df)
    anomaly_insights = [i for i in report.insights if i.category == "anomaly"]
    assert len(anomaly_insights) >= 1


def test_generate_insights_status_analysis():
    df = _sample_data()
    report = generate_insights(df, status_col="status")
    status_insights = [i for i in report.insights if i.category == "operational"]
    assert len(status_insights) >= 1


def test_generate_insights_trend():
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    df = pd.DataFrame({"date": dates, "severity_rating": range(30), "borough": ["MANHATTAN"] * 30})
    report = generate_insights(df, date_col="date")
    trend_insights = [i for i in report.insights if i.category == "trend"]
    assert len(trend_insights) >= 1


def test_smart_recommendations():
    df = _sample_data()
    recs = smart_recommendations(df)
    assert isinstance(recs, list)
    for r in recs:
        assert r.priority in ("critical", "high", "medium", "low")
        assert len(r.text) > 0


def test_insights_to_markdown():
    df = _sample_data()
    report = generate_insights(df)
    md = report.to_markdown()
    assert "# Data Insights Report" in md
    assert "Summary" in md
    assert "Key Metrics" in md


def test_high_severity_borough_recommendation():
    df = pd.DataFrame({
        "borough": ["BRONX"] * 10,
        "severity_rating": [9] * 10,
        "status": ["Pending Repair"] * 10,
    })
    report = generate_insights(df, borough_col="borough", severity_col="severity_rating")
    high_recs = [r for r in report.recommendations if r.priority in ("critical", "high")]
    assert len(high_recs) >= 1
