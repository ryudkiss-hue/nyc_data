import pandas as pd

from socrata_toolkit.engineering import (
    borough_comparison_table,
    borough_summary,
    equity_analysis,
    identify_hotspots,
)


def _sample_data():
    return pd.DataFrame(
        {
            "location_id": ["L1", "L1", "L2", "L3", "L3", "L3", "L4", "L5"],
            "borough": [
                "MANHATTAN",
                "MANHATTAN",
                "BROOKLYN",
                "QUEENS",
                "QUEENS",
                "QUEENS",
                "BRONX",
                "STATEN ISLAND",
            ],
            "violations": [3, 2, 5, 1, 2, 3, 4, 1],
            "complaint_count": [2, 1, 3, 0, 1, 2, 5, 0],
            "severity_rating": [7, 6, 8, 3, 4, 5, 9, 2],
            "ada_flag": [True, False, True, False, False, True, True, False],
            "estimated_sqft": [100, 50, 200, 30, 40, 50, 300, 20],
            "contract_id": ["C1", "C1", "C2", "C3", "C3", "C3", "C4", "C5"],
            "status": [
                "Pending Repair",
                "Pending Repair",
                "Complete",
                "Pending Repair",
                "Pending Repair",
                "Pending Repair",
                "Pending Repair",
                "Complete",
            ],
            "actual_spend": [5000, 3000, 10000, 1000, 2000, 3000, 15000, 500],
            "latitude": [40.75, 40.75, 40.68, 40.72, 40.72, 40.72, 40.85, 40.58],
            "longitude": [-73.99, -73.99, -73.96, -73.79, -73.79, -73.79, -73.87, -74.15],
        }
    )


def test_borough_summary():
    df = _sample_data()
    results = borough_summary(df)
    assert len(results) == 5  # 5 boroughs in data
    manhattan = [m for m in results if m.borough == "MANHATTAN"][0]
    assert manhattan.total_inspections == 2
    assert manhattan.total_violations == 5
    assert manhattan.repair_backlog == 2


def test_borough_comparison_table():
    df = _sample_data()
    table = borough_comparison_table(df)
    assert isinstance(table, pd.DataFrame)
    assert "borough" in table.columns
    assert len(table) == 5


def test_identify_hotspots():
    df = _sample_data()
    hotspots = identify_hotspots(df, threshold=2)
    assert len(hotspots) >= 1
    # QUEENS L3 has 3 records, should be a hotspot
    queens_hotspots = [h for h in hotspots if h.borough == "QUEENS"]
    assert len(queens_hotspots) >= 1
    assert queens_hotspots[0].location_count >= 2


def test_identify_hotspots_high_threshold():
    df = _sample_data()
    hotspots = identify_hotspots(df, threshold=100)
    assert len(hotspots) == 0


def test_equity_analysis():
    df = _sample_data()
    results = equity_analysis(df)
    assert len(results) == 5  # One per NYC borough
    # Check structure
    for r in results:
        assert 0 <= r.need_index <= 1
        assert 0 <= r.resource_index <= 1
        assert r.borough in ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]
