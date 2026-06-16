"""Borough-level Analysis for DOT Sidewalk Inspection & Management.

Provides tools to analyze sidewalk repair needs, contract performance, and
infrastructure conditions across NYC's five boroughs.

Key capabilities:
- Borough-level aggregation of inspections, complaints, and work orders
- Cross-borough comparison dashboards
- Hotspot identification (high-density repair clusters)
- Borough equity scoring (repair backlog relative to need)
- Community Board-level drill-down

Example::

    from socrata_toolkit.engineering.borough_analysis import (
        borough_summary,
        identify_hotspots,
        equity_analysis,
    )

    summary = borough_summary(inspections_df)
    hotspots = identify_hotspots(inspections_df, threshold=10)
    equity = equity_analysis(inspections_df, population_df)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np  # type: ignore[import]
import pandas as pd  # type: ignore[import]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOROUGHS = ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]

#: Approximate sidewalk miles per borough (DOT reference data, rounded).
BOROUGH_SIDEWALK_MILES: dict[str, float] = {
    "MANHATTAN": 1580.0,
    "BRONX": 1200.0,
    "BROOKLYN": 2100.0,
    "QUEENS": 2400.0,
    "STATEN ISLAND": 900.0,
}

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class BoroughMetrics:
    """Aggregated metrics for a single borough."""
    borough: str
    total_inspections: int
    total_violations: int
    total_complaints: int
    avg_severity: float
    pct_ada: float
    repair_backlog: int
    estimated_sqft: float
    contracts_active: int

@dataclass
class HotspotCluster:
    """A geographic cluster of repair-needing locations."""
    cluster_id: int
    borough: str
    center_lat: float | None
    center_lon: float | None
    location_count: int
    avg_severity: float
    total_sqft: float
    community_board: str | None

@dataclass
class EquityScore:
    """Borough equity scoring -- how fairly repair resources are distributed."""
    borough: str
    need_index: float      # normalized repair need (0-1)
    resource_index: float  # normalized resource allocation (0-1)
    equity_gap: float      # need - resource (positive = underserved)
    backlog_per_mile: float

# ---------------------------------------------------------------------------
# Borough Summary
# ---------------------------------------------------------------------------

def borough_summary(
    df: pd.DataFrame,
    borough_col: str = "borough",
    violations_col: str = "violations",
    complaints_col: str = "complaint_count",
    severity_col: str = "severity_rating",
    ada_col: str = "ada_flag",
    sqft_col: str = "estimated_sqft",
    contract_col: str = "contract_id",
    status_col: str = "status",
) -> list[BoroughMetrics]:
    """Compute summary metrics for each borough.

    Args:
        df: Inspection/work order DataFrame with a borough column.

    Returns:
        List of BoroughMetrics, one per borough found in the data.
    """
    if borough_col not in df.columns:
        return []

    results = []
    for borough, group in df.groupby(borough_col):
        violations = int(group[violations_col].fillna(0).sum()) if violations_col in group.columns else 0
        complaints = int(group[complaints_col].fillna(0).sum()) if complaints_col in group.columns else 0
        avg_sev = float(group[severity_col].fillna(0).mean()) if severity_col in group.columns else 0.0
        pct_ada = float(group[ada_col].fillna(False).mean() * 100) if ada_col in group.columns else 0.0
        backlog = int((group[status_col] == "Pending Repair").sum()) if status_col in group.columns else 0
        sqft = float(group[sqft_col].fillna(0).sum()) if sqft_col in group.columns else 0.0
        active = int(group[contract_col].nunique()) if contract_col in group.columns else 0

        results.append(BoroughMetrics(
            borough=str(borough),
            total_inspections=len(group),
            total_violations=violations,
            total_complaints=complaints,
            avg_severity=round(avg_sev, 2),
            pct_ada=round(pct_ada, 2),
            repair_backlog=backlog,
            estimated_sqft=round(sqft, 2),
            contracts_active=active,
        ))

    return results

def borough_comparison_table(
    df: pd.DataFrame,
    borough_col: str = "borough",
    **kwargs: str,
) -> pd.DataFrame:
    """Generate a comparison table across all boroughs.

    Returns a DataFrame with one row per borough and standard metric columns.
    Suitable for direct display or charting.
    """
    metrics = borough_summary(df, borough_col=borough_col, **kwargs)
    if not metrics:
        return pd.DataFrame()
    return pd.DataFrame([m.__dict__ for m in metrics]).sort_values("borough").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Hotspot Identification
# ---------------------------------------------------------------------------

def identify_hotspots(
    df: pd.DataFrame,
    location_col: str = "location_id",
    borough_col: str = "borough",
    severity_col: str = "severity_rating",
    sqft_col: str = "estimated_sqft",
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    cb_col: str = "community_board",
    threshold: int = 5,
) -> list[HotspotCluster]:
    """Identify hotspot clusters -- locations with multiple repair needs.

    Groups by ``location_col`` and flags clusters where the count of
    records meets or exceeds the ``threshold``.

    For true geographic clustering (DBSCAN, etc.) on coordinate data,
    consider extending this with scikit-learn.

    Args:
        df: Inspection data.
        threshold: Minimum records at a location to qualify as a hotspot.

    Returns:
        List of HotspotCluster, sorted by location_count descending.
    """
    if location_col not in df.columns:
        return []

    agg_cols = {location_col: "count"}
    rename = {"count": "location_count"}

    group_cols = [location_col]
    if borough_col in df.columns:
        group_cols.append(borough_col)

    grouped = df.groupby(group_cols).agg(
        location_count=(location_col, "count"),
        avg_severity=(severity_col, "mean") if severity_col in df.columns else (location_col, "count"),
        total_sqft=(sqft_col, "sum") if sqft_col in df.columns else (location_col, "count"),
    ).reset_index()

    hotspots = grouped[grouped["location_count"] >= threshold].sort_values(
        "location_count", ascending=False
    ).reset_index(drop=True)

    results = []
    for i, row in hotspots.iterrows():
        # Get center coordinates from original data
        loc_data = df[df[location_col] == row[location_col]]
        center_lat = float(loc_data[lat_col].mean()) if lat_col in loc_data.columns else None
        center_lon = float(loc_data[lon_col].mean()) if lon_col in loc_data.columns else None
        cb = str(loc_data[cb_col].mode().iloc[0]) if cb_col in loc_data.columns and not loc_data[cb_col].mode().empty else None

        results.append(HotspotCluster(
            cluster_id=i,
            borough=str(row.get(borough_col, "unknown")),
            center_lat=round(center_lat, 6) if center_lat and not np.isnan(center_lat) else None,
            center_lon=round(center_lon, 6) if center_lon and not np.isnan(center_lon) else None,
            location_count=int(row["location_count"]),
            avg_severity=round(float(row.get("avg_severity", 0)), 2),
            total_sqft=round(float(row.get("total_sqft", 0)), 2),
            community_board=cb,
        ))

    return results

# ---------------------------------------------------------------------------
# Equity Analysis
# ---------------------------------------------------------------------------

from ..governance.equity import EquityScorer


def equity_analysis(
    inspections_df: pd.DataFrame,
    resource_df: pd.DataFrame | None = None,
    borough_col: str = "borough",
    status_col: str = "status",
    spend_col: str = "actual_spend",
) -> list[EquityScore]:
    """
    Elite Borough Equity Analysis.
    Integrates socio-economic weighting as mandated by NYC SDM 4th Ed.
    """
    if borough_col not in inspections_df.columns:
        return []

    resource = resource_df if resource_df is not None else inspections_df
    scorer = EquityScorer()

    results = []
    total_weighted_needs = []
    total_spends = []

    for borough in BOROUGHS:
        boro_data = inspections_df[inspections_df[borough_col].str.upper() == borough]
        if boro_data.empty:
            continue

        # Calculate weighted need using the Mandate's EquityScorer
        total_weighted_need = 0.0
        for _, row in boro_data.iterrows():
            # Base need is 1.0 for a pending repair
            is_pending = row.get(status_col) == "Pending Repair"
            base_need = 1.0 if is_pending else 0.1
            impact = scorer.calculate_impact(row, base_need)
            total_weighted_need += impact.score_weighted

        total_weighted_needs.append(total_weighted_need)

        boro_resource = resource[resource[borough_col].str.upper() == borough] if borough_col in resource.columns else pd.DataFrame()
        spend = float(boro_resource[spend_col].fillna(0).sum()) if spend_col in boro_resource.columns else 0.0
        total_spends.append(spend)

        results.append({
            "borough": borough,
            "raw_need": total_weighted_need,
            "raw_resource": spend,
        })

    # Normalize
    max_need = max(total_weighted_needs) if total_weighted_needs else 1.0
    max_resource = max(total_spends) if total_spends else 1.0

    final_results = []
    for r in results:
        borough = r["borough"]
        need_idx = r["raw_need"] / max_need if max_need > 0 else 0.0
        res_idx = r["raw_resource"] / max_resource if max_resource > 0 else 0.0

        miles = BOROUGH_SIDEWALK_MILES.get(borough, 1.0)
        weighted_need_per_mile = r["raw_need"] / miles

        final_results.append(EquityScore(
            borough=borough,
            need_index=round(float(need_idx), 2),
            resource_index=round(float(res_idx), 2),
            equity_gap=round(float(need_idx - res_idx), 4),
            backlog_per_mile=round(float(weighted_need_per_mile), 4),
        ))

    return sorted(final_results, key=lambda e: e.equity_gap, reverse=True)
