import pytest

@pytest.fixture
def sample_kpi_registry():
    """Sample KPI registry for testing"""
    return {
        "KPI-089": {
            "kpi_id": "KPI-089",
            "kpi_name": "Violations Fixed by Borough & Month",
            "summary": "Monthly count of violations marked fixed",
            "datasets": [
                {"key": "violations", "fourfour": "6kbp-uz6m", "role": "primary"},
                {"key": "dismissals", "fourfour": "p4u2-3jgx", "role": "supporting"}
            ],
            "sql_pattern": "SELECT borough, DATE_TRUNC('month', fixed_date) AS month, COUNT(*) AS fixed_count FROM violations WHERE status='FIXED' GROUP BY borough, month",
            "visualization_metadata": ["monthly_fix_rate_chart", "violations_heatmap"],
            "related_kpis": ["KPI-045", "KPI-067"]
        },
        "KPI-045": {
            "kpi_id": "KPI-045",
            "kpi_name": "Structural Damage by Borough & Cause",
            "summary": "Classification of structural damage",
            "datasets": [{"key": "violations", "fourfour": "6kbp-uz6m", "role": "primary"}],
            "sql_pattern": "SELECT borough, damage_cause, COUNT(*) FROM violations WHERE damage_type='structural' GROUP BY borough, damage_cause",
            "visualization_metadata": ["damage_breakdown_chart"],
            "related_kpis": ["KPI-089"]
        }
    }

@pytest.fixture
def sample_research_questions():
    """Sample research questions for NLP suggestion testing"""
    return [
        {
            "question_id": "Q1",
            "text": "Why are violations spiking in Manhattan?",
            "related_kpi": "KPI-089"
        },
        {
            "question_id": "Q2",
            "text": "What is causing the structural damage spike?",
            "related_kpi": "KPI-045"
        }
    ]
