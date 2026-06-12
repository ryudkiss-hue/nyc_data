"""Generate synthetic Excel fixtures for analyst workflow tests."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent

def write_fixtures() -> None:
    inspections = pd.DataFrame(
        {
            "location_id": ["L001", "L002", "L003"],
            "borough": ["MANHATTAN", "BROOKLYN", "QUEENS"],
            "severity": [4, 2, 5],
            "pedestrian_volume": [100, 50, 200],
            "age_days": [30, 10, 90],
            "ada_flag": [1, 0, 1],
            "complaint_count": [2, 0, 5],
        }
    )
    contracts = pd.DataFrame(
        {
            "contract_id": ["C-100", "C-200"],
            "borough": ["MANHATTAN", "BROOKLYN"],
            "planned_sqft": [1000, 800],
            "actual_sqft": [600, 400],
            "planned_spend": [50000, 40000],
            "actual_spend": [30000, 25000],
            "status": ["in_progress", "in_progress"],
            "violations": [5, 3],
            "curb_miles": [1.0, 0.8],
            "built_linear_feet": [200, 150],
            "days": [10, 8],
        }
    )
    permits = pd.DataFrame({"location_id": ["L002"]})
    inspections.to_excel(ROOT / "inspections.xlsx", index=False)
    contracts.to_excel(ROOT / "contracts.xlsx", index=False)
    permits.to_excel(ROOT / "permits.xlsx", index=False)

if __name__ == "__main__":
    write_fixtures()
