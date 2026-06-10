
import pandas as pd
import pytest

from app.services.analytics_service import (
    digital_twin_pre_screen,
    perform_causal_what_if_simulation,
    update_predictive_simulation_intervention,
)


def test_causal_what_if_simulation():
    # Mocking manager and data
    manager = None
    historical_df = pd.DataFrame({"attr": [1, 2], "val": [3, 4]})
    result = perform_causal_what_if_simulation(manager, historical_df, 1000.0, "test_strategy")
    assert result["success"] is True
    assert "simulated_outcomes" in result

def test_update_predictive_simulation_intervention():
    result = update_predictive_simulation_intervention("int_001", 0.5)
    assert result["success"] is True
    assert result["intervention_updated"] == "int_001"

def test_digital_twin_pre_screen():
    historical_df = pd.DataFrame({"performance": [0.8, 0.9]})
    result = digital_twin_pre_screen("contractor_001", historical_df)
    assert result["success"] is True
    assert "pre_screen_result" in result
