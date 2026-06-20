import pytest
from socrata_toolkit.core.routing.models import MatchResult, AnswerResult, ExpansionResult

def test_match_result_dataclass():
    result = MatchResult(
        question_id="KPI-089",
        confidence=0.82,
        strategy="ensemble",
        source="programmatic+claude",
        alternatives=["KPI-045", "KPI-067"]
    )
    assert result.question_id == "KPI-089"
    assert result.confidence == 0.82
    assert len(result.alternatives) == 2

def test_answer_result_dataclass():
    answer = AnswerResult(
        kpi_id="KPI-089",
        kpi_name="Violations Fixed by Borough & Month",
        summary="Monthly count of violations marked fixed",
        datasets=[{"key": "violations", "fourfour": "6kbp-uz6m"}],
        sql_pattern="SELECT borough, COUNT(*) FROM violations WHERE status='FIXED'",
        visualizations=["monthly_fix_rate", "heatmap"],
        confidence=0.82,
        source="hybrid_router"
    )
    assert answer.kpi_id == "KPI-089"
    assert len(answer.datasets) == 1

def test_expansion_result_dataclass():
    expansion = ExpansionResult(
        synthesis="Violations spiked 45% in June...",
        suggested_questions=[
            {"question": "What causes structural damage?", "related_kpi": "KPI-045"}
        ],
        query_results_summary="45% increase in June vs May"
    )
    assert "spiked" in expansion.synthesis
    assert len(expansion.suggested_questions) == 1
