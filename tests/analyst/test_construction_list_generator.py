"""Tests for ConstructionListGenerator."""

import pandas as pd

from socrata_toolkit.analyst.construction_list_generator import (
    REPAIR_COST_BY_SCOPE,
    ConstructionListConfig,
    ConstructionListGenerator,
)

SAMPLE_PHASE_D = pd.DataFrame(
    {
        "location_id": ["LOC001", "LOC002", "LOC003"],
        "borough": ["MN", "BX", "BK"],
        "latitude": [40.75, 40.83, 40.65],
        "longitude": [-74.00, -73.92, -73.95],
        "inspection_count": [15, 22, 8],
        "z_score_violations": [3.2, 4.1, 2.8],
        "outlier_class": ["high", "critical", "moderate"],
        "priority_rank": [1, 2, 3],
    }
)


def test_from_phase_d_returns_dataframe():
    gen = ConstructionListGenerator()
    result = gen.build_from_phase_d(SAMPLE_PHASE_D)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert "estimated_cost" in result.columns
    assert "scope_category" in result.columns
    assert "timeline_weeks" in result.columns
    assert "priority_rank" in result.columns


def test_cost_constants_present():
    assert "sidewalk_repair" in REPAIR_COST_BY_SCOPE
    assert REPAIR_COST_BY_SCOPE["pedestrian_ramp"]["typical"] == 4500


def test_excel_bytes_returned(tmp_path):
    gen = ConstructionListGenerator()
    df = gen.build_from_phase_d(SAMPLE_PHASE_D)
    out = tmp_path / "test_list.xlsx"
    gen.export_to_excel(df, str(out))
    assert out.exists()
    assert out.stat().st_size > 0


def test_config_borough_filter():
    gen = ConstructionListGenerator(config=ConstructionListConfig(borough_filter="MN"))
    result = gen.build_from_phase_d(SAMPLE_PHASE_D)
    assert all(result["borough"] == "MN")
    assert len(result) == 1


def test_critical_outliers_assigned_ada_scope():
    gen = ConstructionListGenerator()
    result = gen.build_from_phase_d(SAMPLE_PHASE_D)
    critical = result[result["outlier_class"] == "critical"]
    assert critical["scope_category"].iloc[0] == "ada_compliance"
