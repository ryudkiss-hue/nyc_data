import pytest
from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter
from socrata_toolkit.core.routing.models import MatchResult

def test_programmatic_router_bm25_exact_match(sample_kpi_registry):
    """Test BM25 matches exact question"""
    router = ProgrammaticRouter(sample_kpi_registry)

    question = "violations fixed by borough"
    result = router.match(question)

    assert result.question_id == "KPI-089"
    assert result.confidence > 0.7
    assert "bm25" in result.strategy.lower() or "bm25" in result.source.lower()

def test_programmatic_router_jaccard_overlap(sample_kpi_registry):
    """Test Jaccard coefficient for token overlap"""
    router = ProgrammaticRouter(sample_kpi_registry)

    question = "how many violations were fixed in boroughs"
    result = router.match(question)

    assert result.question_id == "KPI-089"
    assert result.confidence > 0.6

def test_programmatic_router_no_match(sample_kpi_registry):
    """Test behavior when question doesn't match any KPI"""
    router = ProgrammaticRouter(sample_kpi_registry)

    question = "xyz abc 123 qwerty"
    result = router.match(question)

    assert result.question_id is None
    assert result.confidence < 0.3
