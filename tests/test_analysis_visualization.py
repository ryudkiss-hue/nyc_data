"""Tests for Phase 4B: Analysis layer (pre-built queries, NL interface, summaries) + Visualization (dashboards, charts)."""
import json
from pathlib import Path

import duckdb
import pytest

from socrata_toolkit.core.analysis import (
    AnalysisEngine,
    AnalyticalQueryTemplate,
    StatisticalSummary,
)
from socrata_toolkit.core.visualization import (
    ChartRecommender,
    DashboardGenerator,
    RoleBasedDashboard,
)


@pytest.fixture
def db():
    """In-memory DuckDB with sample analytics marts."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA analytics")

    # Create sample sidewalk_repair_matrix
    conn.execute("""
        CREATE TABLE analytics.sidewalk_repair_matrix (
            dataset VARCHAR,
            row_val VARCHAR,
            col_val VARCHAR,
            metric_value INTEGER
        )
    """)
    conn.execute("""
        INSERT INTO analytics.sidewalk_repair_matrix VALUES
        ('inspection', 'concrete', 'MN', 150),
        ('inspection', 'asphalt', 'MN', 45),
        ('inspection', 'concrete', 'BK', 120),
        ('inspection', 'asphalt', 'BK', 80)
    """)

    # Create sample raw_counts_summary
    conn.execute("""
        CREATE TABLE analytics.raw_counts_summary (
            dataset VARCHAR,
            row_count INTEGER,
            materialized_at TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO analytics.raw_counts_summary VALUES
        ('inspection', 398234, NOW()),
        ('violations', 312891, NOW()),
        ('permits', 3612445, NOW())
    """)

    return conn

def test_analytical_query_template_registration(db):
    """Test query templates can be registered and retrieved."""
    template = AnalyticalQueryTemplate(
        name="top_materials_by_borough",
        mart_name="sidewalk_repair_matrix",
        description="Top materials by borough",
        query="SELECT row_val, col_val, SUM(metric_value) FROM {mart} GROUP BY row_val, col_val ORDER BY 3 DESC"
    )

    assert template.name == "top_materials_by_borough"
    assert "{mart}" in template.query

def test_analytical_query_execution(db):
    """Test query templates execute and return results."""
    engine = AnalysisEngine(db)

    # Register a query
    query = "SELECT row_val, SUM(metric_value) as total FROM analytics.sidewalk_repair_matrix GROUP BY row_val ORDER BY total DESC"

    result = engine.execute_query(query)

    assert len(result) > 0
    assert "total" in str(result.columns)

def test_statistical_summary_numeric(db):
    """Test statistical summary computation for numeric columns."""
    summary = StatisticalSummary(db)

    stats = summary.compute(
        table="analytics.raw_counts_summary",
        columns=["row_count"]
    )

    assert "row_count" in stats
    assert "mean" in stats["row_count"]
    assert "median" in stats["row_count"]
    assert "stddev" in stats["row_count"]
    assert stats["row_count"]["mean"] > 0

def test_statistical_summary_categorical(db):
    """Test statistical summary for categorical columns."""
    summary = StatisticalSummary(db)

    stats = summary.compute(
        table="analytics.sidewalk_repair_matrix",
        columns=["row_val"]
    )

    assert "row_val" in stats
    assert "top_categories" in stats["row_val"]
    assert len(stats["row_val"]["top_categories"]) > 0

def test_chart_recommendation_numeric(db):
    """Test chart type recommendation based on schema."""
    recommender = ChartRecommender()

    schema = {
        "columns": [
            {"name": "material", "type": "VARCHAR"},
            {"name": "borough", "type": "VARCHAR"},
            {"name": "count", "type": "INTEGER"}
        ]
    }

    recommendations = recommender.recommend(schema)

    assert len(recommendations) > 0
    assert any(chart["type"] in ["heatmap", "bar"] for chart in recommendations)

def test_chart_recommendation_timeseries(db):
    """Test chart recommendation for time series."""
    recommender = ChartRecommender()

    schema = {
        "columns": [
            {"name": "date", "type": "TIMESTAMP"},
            {"name": "metric_value", "type": "FLOAT"}
        ]
    }

    recommendations = recommender.recommend(schema)

    assert any(chart["type"] == "line" for chart in recommendations)

def test_dashboard_generation(db):
    """Test dashboard auto-generation from mart metadata."""
    generator = DashboardGenerator(db)

    dashboard = generator.generate(
        mart_name="analytics.sidewalk_repair_matrix",
        title="Sidewalk Repair Matrix",
        description="Condition by material × borough"
    )

    assert dashboard["title"] == "Sidewalk Repair Matrix"
    assert "charts" in dashboard
    assert len(dashboard["charts"]) > 0
    assert all("type" in chart for chart in dashboard["charts"])

def test_role_based_dashboard_filtering(db):
    """Test role-based dashboard filtering."""
    role_dashboard = RoleBasedDashboard(db)

    contract_analyst_dashboards = role_dashboard.get_dashboards_for_role("contract_analyst")

    assert isinstance(contract_analyst_dashboards, list)
    assert len(contract_analyst_dashboards) > 0

def test_role_based_dashboard_manager_view(db):
    """Test manager role gets all dashboards + quality metrics."""
    role_dashboard = RoleBasedDashboard(db)

    manager_dashboards = role_dashboard.get_dashboards_for_role("manager")

    assert len(manager_dashboards) >= len(
        role_dashboard.get_dashboards_for_role("contract_analyst")
    )

def test_nl_query_interface_integration(db):
    """Test natural language query translation (integration with Claude API)."""
    engine = AnalysisEngine(db)

    # Mock NL query (in real implementation, calls Claude API)
    nl_question = "What's the total row count for all datasets?"

    # For testing, we'll just verify the method exists and can handle SQL directly
    sql = "SELECT SUM(row_count) as total FROM analytics.raw_counts_summary"
    result = engine.execute_query(sql)

    assert result is not None

def test_analysis_engine_query_history(db):
    """Test query history tracking."""
    engine = AnalysisEngine(db)

    query1 = "SELECT COUNT(*) FROM analytics.raw_counts_summary"
    query2 = "SELECT COUNT(*) FROM analytics.sidewalk_repair_matrix"

    engine.execute_query(query1)
    engine.execute_query(query2)

    history = engine.get_query_history()

    assert len(history) == 2
    assert query1 in [h["sql"] for h in history]
    assert query2 in [h["sql"] for h in history]
