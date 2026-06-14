import pandas as pd

from socrata_toolkit.analysis import (
    InsightsReport,
    generate_insights,
    smart_recommendations,
)


def _sample_data():
    return pd.DataFrame(
        {
            "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
            "status": [
                "Pending Repair",
                "Complete",
                "Pending Repair",
                "Pending Repair",
                "Complete",
            ],
            "severity_rating": [8, 3, 9, 2, 5],
            "violations": [5, 1, 10, 0, 3],
            "complaint_count": [3, 0, 7, 1, 2],
            "estimated_sqft": [200, 50, 500, 30, 100],
            "inspection_date": [
                "2024-01-15",
                "2024-03-20",
                "2024-02-10",
                "2024-06-01",
                "2024-04-15",
            ],
        }
    )

def test_generate_insights_basic():
    df = _sample_data()
    report = generate_insights(df)
    assert isinstance(report, InsightsReport)
    # Engine reports operational health as a categorical status string.
    assert report.data_health in ("optimal", "unstable", "critical")
    assert len(report.summary) > 0
    assert report.key_metrics.get("Rows") == 5

def test_generate_insights_has_quality_metrics():
    df = _sample_data()
    report = generate_insights(df)
    assert "Quality" in report.key_metrics
    # Quality is reported as an "<score>/100" string.
    assert report.key_metrics["Quality"].endswith("/100")

def test_generate_insights_borough_analysis():
    df = _sample_data()
    report = generate_insights(df, borough_col="borough")
    # Borough column is categorical with <10 levels, so it is eligible for
    # chi-square association analysis; the report should still be well-formed.
    assert isinstance(report, InsightsReport)
    assert report.key_metrics.get("Rows") == 5

def test_generate_insights_with_missing_data():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["a", None, None],
            "value": [10, None, 30],
        }
    )
    report = generate_insights(df)
    # Missing data lowers the quality score below the 100/100 ceiling.
    score = int(report.key_metrics["Quality"].split("/")[0])
    assert score < 100

def test_generate_insights_with_outliers():
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 100, 2, 3, 4, 5]})
    report = generate_insights(df)
    # A strong outlier produces severe skewness, surfaced as a distribution insight.
    distribution_insights = [i for i in report.insights if i.category == "distribution"]
    assert len(distribution_insights) >= 1

def test_generate_insights_status_analysis():
    df = _sample_data()
    report = generate_insights(df, status_col="status")
    assert isinstance(report, InsightsReport)
    assert isinstance(report.insights, list)

def test_generate_insights_trend():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "severity_rating": range(30),
            "borough": ["MANHATTAN"] * 30,
        }
    )
    report = generate_insights(df, date_col="date")
    assert isinstance(report, InsightsReport)
    assert report.key_metrics.get("Rows") == 30

def test_smart_recommendations():
    df = pd.DataFrame({"surface_rating": [3, 4, 2, 3, 5] * 4})
    report = generate_insights(df)
    recs = smart_recommendations(report)
    assert isinstance(recs, list)
    for text in recs:
        assert isinstance(text, str)
        assert len(text) > 0

def test_insights_to_markdown():
    df = _sample_data()
    report = generate_insights(df)
    md = report.to_markdown()
    assert "Data Insights Report" in md
    assert "Key Metrics" in md
    assert "Recommendations" in md

def test_high_severity_borough_recommendation():
    # Low surface ratings trigger an NYSDOT high-priority engineering insight,
    # flipping data_health to "unstable".
    df = pd.DataFrame({"surface_rating": [3] * 10})
    report = generate_insights(df)
    assert report.data_health == "unstable"
    high_insights = [i for i in report.insights if i.priority == "high"]
    assert len(high_insights) >= 1
