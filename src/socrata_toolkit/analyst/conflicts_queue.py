"""Build analyst conflict review queue spreadsheet."""

from __future__ import annotations

import pandas as pd


def build_conflicts_review(
    conflicts_df: pd.DataFrame,
    *,
    location_col: str = "location_id",
) -> pd.DataFrame:
    """Return a review queue with standard analyst columns."""
    if conflicts_df.empty:
        return pd.DataFrame(
            columns=["location", "conflict_type", "reference_id", "recommended_action"]
        )

    rows = []
    for _, row in conflicts_df.iterrows():
        loc = str(row.get(location_col, row.get("location", "unknown")))
        ref = str(row.get("permit_id", row.get("permit_number", row.get("reference_id", ""))))
        rows.append(
            {
                "location": loc,
                "conflict_type": "active_permit_overlap",
                "reference_id": ref or loc,
                "recommended_action": "Coordinate with permit holder before scheduling work",
            }
        )
    return pd.DataFrame(rows)
