import pytest

from socrata_toolkit.core.answer_engine.prebuilt_answer_engine import PreBuiltAnswerEngine
from socrata_toolkit.core.routing.claude_semantic_router import ClaudeSemanticRouter
from socrata_toolkit.core.routing.hybrid_router import HybridRouter
from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter


def test_hybrid_router_agreement(sample_kpi_registry):
    """Test ensemble when both strategies agree"""
    prog_router = ProgrammaticRouter(sample_kpi_registry)

    embeddings = {
        "KPI-089": [0.1, 0.2, 0.3] * 512,
        "KPI-045": [0.15, 0.25, 0.35] * 512
    }
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)

    hybrid = HybridRouter(prog_router, claude_router, threshold=0.70)
    result = hybrid.match("violations fixed by borough")

    assert result.question_id == "KPI-089"
    assert result.confidence > 0.5

def test_hybrid_router_disagreement(sample_kpi_registry):
    """Test ensemble when strategies might disagree"""
    prog_router = ProgrammaticRouter(sample_kpi_registry)

    embeddings = {
        "KPI-089": [0.1, 0.2, 0.3] * 512,
        "KPI-045": [0.9, 0.9, 0.9] * 512
    }
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)

    hybrid = HybridRouter(prog_router, claude_router, threshold=0.70)
    result = hybrid.match("violations fixed by borough")

    # With clear signal, should still match
    assert result.question_id is not None

def test_prebuilt_answer_lookup(sample_kpi_registry):
    """Test retrieving pre-built answer for matched KPI"""
    engine = PreBuiltAnswerEngine(sample_kpi_registry)

    answer = engine.get_answer("KPI-089")

    assert answer.kpi_id == "KPI-089"
    assert answer.kpi_name == "Violations Fixed by Borough & Month"
    assert len(answer.datasets) >= 1
    assert "borough" in answer.sql_pattern.lower()

def test_prebuilt_answer_not_found():
    """Test behavior when KPI not in registry"""
    engine = PreBuiltAnswerEngine({})

    answer = engine.get_answer("NONEXISTENT")

    assert answer is None

def test_prebuilt_answer_contains_all_fields(sample_kpi_registry):
    """Test answer has all required fields"""
    engine = PreBuiltAnswerEngine(sample_kpi_registry)
    answer = engine.get_answer("KPI-089")

    assert answer.kpi_id is not None
    assert answer.kpi_name is not None
    assert answer.summary is not None
    assert answer.sql_pattern is not None
    assert answer.visualizations is not None
    assert isinstance(answer.related_kpis, list)

def test_full_tier1_flow(sample_kpi_registry):
    """Test complete Tier 1 flow: question -> router -> answer"""
    prog_router = ProgrammaticRouter(sample_kpi_registry)
    embeddings = {k: [0.1] * 1536 for k in sample_kpi_registry.keys()}
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)
    hybrid = HybridRouter(prog_router, claude_router)
    answer_engine = PreBuiltAnswerEngine(sample_kpi_registry)

    question = "How many violations were fixed by borough?"
    match_result = hybrid.match(question)
    assert match_result.question_id is not None

    answer = answer_engine.get_answer(match_result.question_id)
    assert answer is not None
    assert answer.kpi_name == "Violations Fixed by Borough & Month"
    assert len(answer.datasets) > 0
