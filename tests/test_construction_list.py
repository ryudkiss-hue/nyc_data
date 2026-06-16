import pytest

import pandas as pd

from socrata_toolkit.engineering import (
    classify_scope,
    compute_priority_score,
    detect_construction_conflicts,
    export_construction_list,
    flag_ada_locations,
    prioritize_construction_list,
    summarize_construction_list,
)


def _sample_inspections():
    return pd.DataFrame(
        {
            "location_id": ["L1", "L2", "L3", "L4"],
            "borough": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
            "address": ["123 Main St", "456 Oak Ave", "789 Elm Blvd", "321 Pine Rd"],
            "description": [
                "Sidewalk cracked",
                "ADA ramp needed",
                "Tree pit repair",
                "Curb replacement",
            ],
            "severity_rating": [8, 5, 3, 9],
            "pedestrian_volume": [8000, 2000, 500, 6000],
            "issued_date": ["2020-01-01", "2023-06-15", "2024-11-01", "2019-03-20"],
            "ada_flag": [False, True, False, False],
            "smart_spine": [True, False, False, True],
            "complaint_count": [5, 1, 0, 8],
            "estimated_sqft": [200, 50, 100, 300],
            "status": ["Pending Repair", "Pending Repair", "Complete", "Pending Repair"],
        }
    )


def test_compute_priority_score():
    row = pd.Series(
        {
            "severity_rating": 8,
            "pedestrian_volume": 5000,
            "issued_date": "2020-01-01",
            "ada_flag": True,
            "smart_spine": True,
            "complaint_count": 5,
        }
    )
    score = compute_priority_score(row)
    assert 0 <= score <= 1
    assert score > 0.3  # high severity + old + ADA + spine


def test_prioritize_construction_list():
    df = _sample_inspections()
    result = prioritize_construction_list(df)
    assert "_priority_score" in result.columns
    assert len(result) == 4
    # First row should be highest priority
    assert result.iloc[0]["_priority_score"] >= result.iloc[-1]["_priority_score"]


def test_detect_construction_conflicts():
    construction = _sample_inspections()
    permits = pd.DataFrame({"location_id": ["L1", "L3", "L99"]})
    result = detect_construction_conflicts(construction, permits)
    assert result.total_items == 4
    assert result.conflict_count == 2  # L1 and L3
    assert len(result.clean) == 2
    assert len(result.conflicts) == 2


def test_detect_construction_conflicts_no_overlap():
    construction = _sample_inspections()
    permits = pd.DataFrame({"location_id": ["X1", "X2"]})
    result = detect_construction_conflicts(construction, permits)
    assert result.conflict_count == 0
    assert len(result.clean) == 4


def test_classify_scope():
    df = _sample_inspections()
    result = classify_scope(df)
    assert "_scope" in result.columns
    assert result.loc[1, "_scope"] == "pedestrian_ramp"  # "ADA ramp needed" matches ramp first
    assert result.loc[2, "_scope"] == "tree_pit"  # "Tree pit repair"
    assert result.loc[3, "_scope"] == "curb_replacement"  # "Curb replacement"


def test_flag_ada_locations():
    df = _sample_inspections()
    df = classify_scope(df)
    result = flag_ada_locations(df)
    assert "_ada_required" in result.columns
    assert bool(result.loc[1, "_ada_required"]) is True  # ADA ramp


def test_summarize_construction_list():
    df = _sample_inspections()
    df = prioritize_construction_list(df)
    df = classify_scope(df)
    df = flag_ada_locations(df)
    summary = summarize_construction_list(df)
    assert summary.total_locations == 4
    assert summary.total_estimated_sqft == 650.0
    assert len(summary.by_borough) > 0


def test_export_construction_list_csv(tmp_path):
    df = _sample_inspections()
    path = str(tmp_path / "list.csv")
    result = export_construction_list(df, path)
    assert result == path
    loaded = pd.read_csv(path)
    assert len(loaded) == 4


def test_export_construction_list_json(tmp_path):
    df = _sample_inspections()
    path = str(tmp_path / "list.json")
    export_construction_list(df, path)
    loaded = pd.read_json(path)
    assert len(loaded) == 4
