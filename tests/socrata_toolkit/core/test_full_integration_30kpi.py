import pytest
import json
from pathlib import Path
from socrata_toolkit.core.cli_nlquery import run_nl_query

@pytest.fixture
def full_kpi_registry():
    """Load full 30-KPI registry"""
    path = Path("config/kpi_registry_full.json")
    if not path.exists():
        pytest.skip("Full registry not found")
    with open(path) as f:
        return json.load(f)

@pytest.fixture
def full_research_questions():
    """Load all research questions"""
    path = Path("config/research_questions.json")
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)

def test_tier1_with_full_registry(full_kpi_registry):
    """Test Tier 1 routing works with 30 KPIs"""
    result = run_nl_query(
        question="violations fixed by borough",
        kpi_registry=full_kpi_registry,
        expand=False
    )
    
    assert result is not None
    assert 'matched_kpi' in result

def test_tier2_with_full_registry(full_kpi_registry, full_research_questions):
    """Test Tier 2 expansion works with full dataset"""
    result = run_nl_query(
        question="Why are violations spiking?",
        kpi_registry=full_kpi_registry,
        research_questions=full_research_questions,
        embeddings_cache={},
        expand=True
    )
    
    assert result is not None

def test_feedback_collection_with_full_registry(full_kpi_registry):
    """Test feedback recording works with full registry"""
    result = run_nl_query(
        question="violations fixed",
        kpi_registry=full_kpi_registry,
        mark_helpful=True
    )
    
    assert result.get('feedback_recorded') == True
