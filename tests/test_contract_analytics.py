import pandas as pd

from socrata_toolkit.engineering import (
    analyze_contract_progress,
    budget_analysis,
    compare_contracts,
    productivity_metrics,
    schedule_variance,
)


def _sample_contracts():
    return pd.DataFrame(
        {
            "contract_id": ["C1", "C1", "C2", "C2"],
            "planned_sqft": [1000, 1000, 500, 500],
            "actual_sqft": [800, 200, 500, 0],
            "start_date": ["2024-01-01", "2024-01-01", "2024-06-01", "2024-06-01"],
            "end_date": ["2025-12-31", "2025-12-31", "2025-06-30", "2025-06-30"],
            "status": ["in_progress", "in_progress", "complete", "complete"],
            "planned_spend": [50000, 50000, 25000, 25000],
            "actual_spend": [45000, 15000, 25000, 5000],
            "earned_value": [40000, 10000, 25000, 5000],
            "linear_feet": [400, 100, 250, 0],
            "days_worked": [50, 20, 30, 10],
        }
    )


def test_analyze_contract_progress():
    df = _sample_contracts()
    results = analyze_contract_progress(df)
    assert len(results) == 2  # C1 and C2
    c1 = [r for r in results if r.contract_id == "C1"][0]
    assert c1.pct_complete == 50.0  # 1000/2000
    assert c1.velocity_sqft_per_day > 0


def test_budget_analysis():
    df = _sample_contracts()
    result = budget_analysis(df)
    assert result.total_planned == 150000.0
    assert result.total_actual == 90000.0
    assert result.variance == -60000.0  # under budget
    assert result.cost_performance_index > 0
    assert result.remaining_budget == 60000.0


def test_productivity_metrics():
    df = _sample_contracts()
    result = productivity_metrics(df)
    assert result.total_sqft_installed == 1500.0
    assert result.total_linear_feet == 750.0
    assert result.sqft_per_day > 0
    assert result.cost_per_sqft > 0
    assert result.crew_efficiency > 0


def test_compare_contracts():
    df = _sample_contracts()
    result = compare_contracts(df)
    assert len(result) == 2
    assert "cost_per_sqft" in result.columns
    assert "sqft_per_day" in result.columns


def test_schedule_variance():
    df = pd.DataFrame(
        {
            "contract_id": ["C1", "C2"],
            "planned_end_date": ["2025-06-01", "2025-03-01"],
            "actual_end_date": ["2025-07-15", "2025-02-15"],
        }
    )
    result = schedule_variance(df)
    assert "_schedule_variance_days" in result.columns
    assert result.loc[0, "_schedule_variance_days"] == 44  # 44 days late
    assert result.loc[1, "_schedule_variance_days"] == -14  # 14 days early
