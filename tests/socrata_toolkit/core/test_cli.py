import pytest
from socrata_toolkit.core.cli_nlquery import run_nl_query

@pytest.fixture
def sample_kpi_registry():
    """Sample KPI registry"""
    return {
        "KPI-089": {
            "kpi_id": "KPI-089",
            "kpi_name": "Violations Fixed by Borough & Month",
            "summary": "Monthly count of violations marked fixed",
            "datasets": [{"key": "violations", "fourfour": "6kbp-uz6m"}],
            "sql_pattern": "SELECT * FROM violations",
            "visualization_metadata": ["chart1"],
            "related_kpis": ["KPI-045"]
        }
    }

@pytest.fixture
def sample_research_questions():
    """Sample research questions"""
    return [
        {
            "question_id": "Q1",
            "text": "Why are violations increasing?",
            "related_kpi": "KPI-089"
        }
    ]

def test_cli_tier1_basic(sample_kpi_registry):
    """Test CLI Tier 1 basic routing"""
    result = run_nl_query(
        question="violations fixed by borough",
        kpi_registry=sample_kpi_registry,
        expand=False
    )

    assert 'matched_kpi' in result
    assert result['matched_kpi'] == 'KPI-089'
    assert 'datasets' in result
    assert 'sql_pattern' in result

def test_cli_tier1_no_match(sample_kpi_registry):
    """Test CLI when no KPI matches"""
    result = run_nl_query(
        question="xyz abc 123 qwerty",
        kpi_registry=sample_kpi_registry,
        expand=False
    )

    assert result['matched_kpi'] is None
    assert result['confidence'] == 0.0
    assert 'error' in result

def test_cli_tier2_expansion(sample_kpi_registry, sample_research_questions):
    """Test CLI Tier 2 expansion"""
    embeddings = {"KPI-089": [0.1] * 1536}

    result = run_nl_query(
        question="Why are violations spiking?",
        kpi_registry=sample_kpi_registry,
        research_questions=sample_research_questions,
        embeddings_cache=embeddings,
        expand=True
    )

    assert 'tier_2_expansion' in result
    assert 'claude_synthesis' in result['tier_2_expansion']
    assert 'suggested_questions' in result['tier_2_expansion']

def test_cli_feedback_helpful(sample_kpi_registry):
    """Test marking feedback as helpful"""
    result = run_nl_query(
        question="violations fixed",
        kpi_registry=sample_kpi_registry,
        mark_helpful=True
    )

    assert result.get('feedback_recorded') == True

def test_cli_feedback_wrong(sample_kpi_registry):
    """Test marking feedback as wrong"""
    result = run_nl_query(
        question="violations fixed",
        kpi_registry=sample_kpi_registry,
        mark_wrong=True,
        corrected_kpi_id="KPI-045"
    )

    assert result.get('feedback_recorded') == True
