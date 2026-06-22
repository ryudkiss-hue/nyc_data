import pytest

from socrata_toolkit.core.answer_engine.claude_expansion_engine import ClaudeExpansionEngine
from socrata_toolkit.core.answer_engine.prebuilt_answer_engine import PreBuiltAnswerEngine
from socrata_toolkit.core.feedback.feedback_collector import FeedbackCollector
from socrata_toolkit.core.routing.claude_semantic_router import ClaudeSemanticRouter
from socrata_toolkit.core.routing.hybrid_router import HybridRouter
from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter
from socrata_toolkit.core.suggestion.npl_suggester import NPLSuggester


@pytest.fixture
def full_system(sample_kpi_registry, sample_research_questions):
    """Initialize full system components"""
    prog_router = ProgrammaticRouter(sample_kpi_registry)
    embeddings = {k: [0.1] * 1536 for k in sample_kpi_registry.keys()}
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)
    hybrid = HybridRouter(prog_router, claude_router)
    answer_engine = PreBuiltAnswerEngine(sample_kpi_registry)
    expansion_engine = ClaudeExpansionEngine()
    suggester = NPLSuggester(sample_research_questions)
    feedback_collector = FeedbackCollector()

    return {
        'hybrid': hybrid,
        'answer_engine': answer_engine,
        'expansion_engine': expansion_engine,
        'suggester': suggester,
        'feedback_collector': feedback_collector
    }

def test_full_tier1_pipeline(full_system):
    """Test complete Tier 1 pipeline"""
    question = "How many violations were fixed by borough?"

    # Route question
    match_result = full_system['hybrid'].match(question)
    assert match_result.question_id == "KPI-089"
    assert match_result.confidence > 0.5

    # Get pre-built answer
    answer = full_system['answer_engine'].get_answer(match_result.question_id)
    assert answer is not None
    assert "Violations Fixed" in answer.kpi_name
    assert len(answer.datasets) > 0
    assert len(answer.sql_pattern) > 0

def test_full_tier2_pipeline(full_system):
    """Test complete Tier 1 + Tier 2 pipeline"""
    question = "Why are violations spiking?"

    # Tier 1: Route and get answer
    match_result = full_system['hybrid'].match(question)
    answer = full_system['answer_engine'].get_answer(match_result.question_id)
    assert answer is not None

    # Tier 2: Expand with Claude
    mock_results = {"count": 120, "trend": "increasing"}
    expansion = full_system['expansion_engine'].expand(
        question,
        answer.kpi_name,
        mock_results
    )
    assert expansion.synthesis is not None
    assert len(expansion.synthesis) > 10

    # Get suggestions
    suggestions = full_system['suggester'].suggest_next_questions(expansion.synthesis)
    assert isinstance(suggestions, list)

def test_feedback_collection(full_system):
    """Test feedback collection"""
    collector = full_system['feedback_collector']

    # Mark helpful
    collector.mark_helpful("test question", "KPI-089")
    feedback = collector.get_feedback()
    assert len(feedback) == 1
    assert feedback[0]['helpful']

    # Mark wrong
    collector.mark_wrong("another question", "KPI-045", "KPI-089")
    feedback = collector.get_feedback()
    assert len(feedback) == 2
    assert not feedback[1]['helpful']
    assert feedback[1]['corrected_kpi_id'] == "KPI-089"

    # Check threshold
    assert not collector.should_retrain()  # Only 2 feedback items

def test_end_to_end_question_answering(full_system):
    """End-to-end test of question answering"""
    questions = [
        "violations fixed by borough",
        "structural damage trends",
        "what's happening with violations"
    ]

    for q in questions:
        # Route
        match = full_system['hybrid'].match(q)
        assert match.question_id is not None, f"Failed to route: {q}"

        # Get answer
        answer = full_system['answer_engine'].get_answer(match.question_id)
        assert answer is not None

        # Record feedback
        full_system['feedback_collector'].mark_helpful(q, match.question_id)

    # Check accumulated feedback
    feedback = full_system['feedback_collector'].get_feedback()
    assert len(feedback) == 3
    assert all(f['helpful'] for f in feedback)
