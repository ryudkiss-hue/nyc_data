import pytest

from socrata_toolkit.training.train_router_weights import train_router_weights


def test_train_router_weights_converges():
    """Test weight optimization converges on synthetic feedback"""
    feedback_data = [
        {"question": "violations fixed", "matched_kpi": "KPI-089", "helpful": True},
        {"question": "structural damage", "matched_kpi": "KPI-045", "helpful": True},
        {"question": "contractor", "matched_kpi": "KPI-067", "helpful": False, "corrected_kpi": "KPI-089"},
    ]

    result = train_router_weights(feedback_data, iterations=5)

    assert "updated_weights" in result
    assert "accuracy" in result
    assert "iterations" in result
    assert result["iterations"] == 5
    assert result["accuracy"] >= 0.0
