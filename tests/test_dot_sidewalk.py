import pandas as pd

from socrata_toolkit.engineering.dot_sidewalk import compute_sidewalk_kpis


def test_compute_sidewalk_kpis():
    df = pd.DataFrame({
        "violations": [10, 15],
        "curb_miles": [2, 3],
        "built_linear_feet": [1000, 500],
        "days": [10, 5],
        "actual_spend": [100, 200],
        "planned_spend": [90, 210],
        "first_pass": [8, 10],
        "total_inspections": [10, 15],
        "rework_spend": [5, 10],
    })
    kpi = compute_sidewalk_kpis(df)
    assert kpi.defect_density > 0
    assert 0 <= kpi.first_pass_yield <= 1
