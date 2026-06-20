import pytest
import json
from socrata_toolkit.training.evaluate_router import evaluate_router

def test_evaluate_router_basic():
    """Test router accuracy evaluation on sample variants"""
    kpi_registry = {
        "KPI-089": {"kpi_id": "KPI-089", "kpi_name": "Violations Fixed"},
        "KPI-045": {"kpi_id": "KPI-045", "kpi_name": "Structural Damage"}
    }
    
    variants = [
        {"kpi_id": "KPI-089", "question_variant": "violations fixed"},
        {"kpi_id": "KPI-089", "question_variant": "how many fixed"},
        {"kpi_id": "KPI-045", "question_variant": "structural damage"},
    ]
    
    result = evaluate_router(kpi_registry, variants)
    
    assert "accuracy" in result
    assert "confusion_matrix" in result
    assert result["accuracy"] >= 0.0
    assert result["accuracy"] <= 1.0
    assert result["correct"] >= 0
    assert result["total"] == 3
