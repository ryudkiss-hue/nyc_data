"""
SIM analyst workflows and Productivity ROI telemetry.

Maps four operational views to cross-dataset logic on the ingestion matrix.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from typing import Any

import pandas as pd

from app.data_loader import (
    BBL_CANDIDATES,
    DATE_CANDIDATES,
    GRACE_CANDIDATES,
    OWNER_CANDIDATES,
    df_to_gdf,
    normalize_bbl,
    pick_column,
)

try:
    import geopandas as gpd
except ImportError:
    gpd = None  # type: ignore


@dataclass
class ProductivityROI:
    """Telemetry for manual-step elimination and time reclaimed."""

    joins_automated: int
    actionable_discrepancies: int
    lots_validated: int
    spatial_conflicts_checked: int
    contracts_cleared: int
    hours_reclaimed: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "joins_automated": self.joins_automated,
            "actionable_discrepancies": self.actionable_discrepancies,
            "lots_validated": self.lots_validated,
            "spatial_conflicts_checked": self.spatial_conflicts_checked,
            "contracts_cleared": self.contracts_cleared,
            "hours_reclaimed": round(self.hours_reclaimed, 2),
        }


def _utc_today() -> pd.Timestamp:
    return pd.Timestamp.now(tz=timezone.utc).normalize().tz_localize(None)


def compute_productivity_roi(
    *,
    lots_validated: int,
    spatial_conflicts_checked: int,
    contracts_cleared: int,
    joins_automated: int,
    actionable_discrepancies: int,
) -> ProductivityROI:
    """
    Time-savings matrix (engineering baselines):
      lots * 3 min + conflicts * 15 min + contracts * 5 min
    """
    minutes = (lots_validated * 3) + (spatial_conflicts_checked * 15) + (contracts_cleared * 5)
    return ProductivityROI(
        joins_automated=joins_automated,
        actionable_discrepancies=actionable_discrepancies,
        lots_validated=lots_validated,
        spatial_conflicts_checked=spatial_conflicts_checked,
        contracts_cleared=contracts_cleared,
        hours_reclaimed=minutes / 60.0,
    )


def qa_qc_inventory_ledger(
    lot_info: pd.DataFrame,
    mappluto: pd.DataFrame,
    complaints_311: pd.DataFrame,
    *,
    stale_days: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """
    Join lot info + MapPLUTO on BBL; flag owner mismatches and stale 311 complaints.
    Returns (ledger, stale_311, join_count).
    """
    joins = 0
    if lot_info.empty:
        return pd.DataFrame(), pd.DataFrame(), joins

    lot = lot_info.copy()
    if "_bbl" not in lot.columns:
        bbl_col = pick_column(lot, BBL_CANDIDATES)
        if bbl_col:
            lot["_bbl"] = normalize_bbl(lot[bbl_col])

    pluto = mappluto.copy() if not mappluto.empty else pd.DataFrame()
    if not pluto.empty and "_bbl" not in pluto.columns:
        bbl_col = pick_column(pluto, BBL_CANDIDATES)
        if bbl_col:
            pluto["_bbl"] = normalize_bbl(pluto[bbl_col])

    if not pluto.empty and "_bbl" in lot.columns and "_bbl" in pluto.columns:
        pluto_owner = pick_column(pluto, OWNER_CANDIDATES) or pick_column(pluto, ("ownername", "ownertype"))
        lot_owner = pick_column(lot, OWNER_CANDIDATES)
        keep_cols = ["_bbl"] + ([pluto_owner] if pluto_owner else [])
        merged = lot.merge(pluto[keep_cols].drop_duplicates("_bbl"), on="_bbl", how="left", suffixes=("", "_pluto"))
        joins += 1
    else:
        merged = lot.copy()

    if lot_owner := pick_column(merged, OWNER_CANDIDATES):
        pluto_owner_col = f"{lot_owner}_pluto" if f"{lot_owner}_pluto" in merged.columns else pick_column(merged, ("ownername", "ownertype"))
        if pluto_owner_col:
            merged["owner_discrepancy"] = (
                merged[lot_owner].astype(str).str.lower().str.strip()
                != merged[pluto_owner_col].astype(str).str.lower().str.strip()
            ) & merged[lot_owner].notna() & merged[pluto_owner_col].notna()
        else:
            merged["owner_discrepancy"] = False
    else:
        merged["owner_discrepancy"] = False

    missing_mask = merged.isna().any(axis=1)
    merged["missing_or_corrupt"] = missing_mask

    stale = pd.DataFrame()
    if not complaints_311.empty:
        c = complaints_311.copy()
        date_col = pick_column(c, DATE_CANDIDATES)
        if date_col:
            c["_opened"] = pd.to_datetime(c[date_col], errors="coerce")
            cutoff = _utc_today() - pd.Timedelta(days=stale_days)
            stale = c[c["_opened"].notna() & (c["_opened"] <= cutoff)].copy()
            if "_bbl" not in stale.columns:
                bbl_col = pick_column(stale, BBL_CANDIDATES)
                if bbl_col:
                    stale["_bbl"] = normalize_bbl(stale[bbl_col])

    return merged, stale, joins


def spatial_conflict_detection(
    weekly_construction: pd.DataFrame,
    street_permits: pd.DataFrame,
    capital_blocks: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """
    Spatial overlaps: weekly schedule vs permits and vs capital reconstruction blocks.
    Returns conflict table and count of spatial join operations performed.
    """
    if gpd is None:
        return pd.DataFrame({"note": ["geopandas not installed — pip install -e \".[mission]\""]}), 0

    joins = 0
    weekly_gdf = df_to_gdf(weekly_construction) if not weekly_construction.empty else None
    permits_gdf = df_to_gdf(street_permits) if not street_permits.empty else None
    capital_gdf = df_to_gdf(capital_blocks) if not capital_blocks.empty else None

    if weekly_gdf is None or weekly_gdf.empty:
        return pd.DataFrame(), joins

    conflicts: list[pd.DataFrame] = []

    if permits_gdf is not None and not permits_gdf.empty:
        try:
            joined = gpd.sjoin(weekly_gdf, permits_gdf, how="inner", predicate="intersects")
            if not joined.empty:
                joined["conflict_type"] = "weekly_vs_permit"
                conflicts.append(joined)
                joins += 1
        except Exception:
            pass

    if capital_gdf is not None and not capital_gdf.empty:
        try:
            joined = gpd.sjoin(weekly_gdf, capital_gdf, how="inner", predicate="intersects")
            if not joined.empty:
                joined["conflict_type"] = "weekly_vs_capital"
                conflicts.append(joined)
                joins += 1
        except Exception:
            pass

    if not conflicts:
        return pd.DataFrame(), joins
    out = pd.concat(conflicts, ignore_index=True)
    out["conflict_id"] = range(1, len(out) + 1)
    return out, joins


def contract_dispatch_clearance(
    violations: pd.DataFrame,
    tree_damage: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """
    Violations past grace period (city-contract clearance) + Parks routing from tree damage.
    """
    joins = 0
    cleared = pd.DataFrame()
    parks_routing = pd.DataFrame()

    if not violations.empty:
        v = violations.copy()
        grace_col = pick_column(v, GRACE_CANDIDATES)
        if grace_col:
            v["_grace"] = pd.to_datetime(v[grace_col], errors="coerce")
            today = _utc_today()
            v["days_past_grace"] = (today - v["_grace"]).dt.days
            cleared = v[v["days_past_grace"].notna() & (v["days_past_grace"] >= 0)].copy()
            if "_bbl" not in cleared.columns:
                bbl_col = pick_column(cleared, BBL_CANDIDATES)
                if bbl_col:
                    cleared["_bbl"] = normalize_bbl(cleared[bbl_col])

    if not tree_damage.empty and not cleared.empty:
        t = tree_damage.copy()
        if "_bbl" not in t.columns:
            bbl_col = pick_column(t, BBL_CANDIDATES)
            if bbl_col:
                t["_bbl"] = normalize_bbl(t[bbl_col])
        tree_bbls = set(t["_bbl"].dropna().astype(str))
        cleared = cleared.copy()
        cleared["route_parks_coordination"] = cleared["_bbl"].astype(str).isin(tree_bbls)
        parks_routing = cleared[cleared["route_parks_coordination"]].copy()
        joins += 1
    elif not tree_damage.empty:
        t = tree_damage.copy()
        if "_bbl" not in t.columns:
            bbl_col = pick_column(t, BBL_CANDIDATES)
            if bbl_col:
                t["_bbl"] = normalize_bbl(t[bbl_col])
        parks_routing = t.copy()
        parks_routing["route_parks_coordination"] = True

    return cleared, parks_routing, joins


def productivity_ada_dashboard(
    built: pd.DataFrame,
    ramp_progress: pd.DataFrame,
    pedestrian_demand: pd.DataFrame,
) -> dict[str, Any]:
    """Sidewalk feet repaired, ramp installs, demand corridor overlay stats."""
    result: dict[str, Any] = {
        "feet_repaired": 0.0,
        "ramp_installs": 0,
        "high_demand_corridors": 0,
        "ramp_demand_index": pd.DataFrame(),
    }

    if not built.empty:
        length_col = pick_column(built, ("feet", "length", "sqft", "linear_feet", "sidewalk_feet", "repaired_feet"))
        if length_col:
            result["feet_repaired"] = float(pd.to_numeric(built[length_col], errors="coerce").fillna(0).sum())
        else:
            result["feet_repaired"] = float(len(built))

    if not ramp_progress.empty:
        status_col = pick_column(ramp_progress, ("status", "install_status", "completed"))
        if status_col:
            done = ramp_progress[status_col].astype(str).str.contains("complete|install|done", case=False, na=False)
            result["ramp_installs"] = int(done.sum())
        else:
            result["ramp_installs"] = len(ramp_progress)

    if not pedestrian_demand.empty and not ramp_progress.empty:
        demand = pedestrian_demand.copy()
        ramps = ramp_progress.copy()
        d_col = pick_column(demand, ("demand", "pedestrian_demand", "score", "index"))
        if d_col:
            threshold = demand[d_col].quantile(0.75) if demand[d_col].notna().any() else 0
            result["high_demand_corridors"] = int((demand[d_col] >= threshold).sum())
        lat_d = pick_column(demand, ("latitude", "lat"))
        lon_d = pick_column(demand, ("longitude", "lon", "lng"))
        lat_r = pick_column(ramps, ("latitude", "lat"))
        lon_r = pick_column(ramps, ("longitude", "lon", "lng"))
        if lat_d and lon_d and lat_r and lon_r:
            ddf = demand[[lat_d, lon_d]].dropna()
            rdf = ramps[[lat_r, lon_r]].dropna()
            ddf.columns = ["lat", "lon"]
            rdf.columns = ["lat", "lon"]
            ddf["source"] = "demand"
            rdf["source"] = "ramp"
            result["ramp_demand_index"] = pd.concat([ddf, rdf], ignore_index=True)

    return result


def run_all_workflows(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Execute four views and aggregate ROI inputs."""
    ledger, stale_311, qa_joins = qa_qc_inventory_ledger(
        frames.get("lot_info", pd.DataFrame()),
        frames.get("mappluto", pd.DataFrame()),
        frames.get("complaints_311", pd.DataFrame()),
    )
    conflicts, spatial_joins = spatial_conflict_detection(
        frames.get("weekly_construction", pd.DataFrame()),
        frames.get("street_permits", pd.DataFrame()),
        frames.get("capital_blocks", pd.DataFrame()),
    )
    cleared, parks, contract_joins = contract_dispatch_clearance(
        frames.get("violations", pd.DataFrame()),
        frames.get("tree_damage", pd.DataFrame()),
    )
    productivity = productivity_ada_dashboard(
        frames.get("built", pd.DataFrame()),
        frames.get("ramp_progress", pd.DataFrame()),
        frames.get("pedestrian_demand", pd.DataFrame()),
    )

    lots_validated = int(len(ledger)) if not ledger.empty else 0
    owner_flags = int(ledger["owner_discrepancy"].sum()) if "owner_discrepancy" in ledger.columns else 0
    missing_flags = int(ledger["missing_or_corrupt"].sum()) if "missing_or_corrupt" in ledger.columns else 0
    spatial_count = len(conflicts) if not conflicts.empty else 0
    contracts_count = len(cleared) if not cleared.empty else 0
    joins_total = qa_joins + spatial_joins + contract_joins
    discrepancies = owner_flags + missing_flags + len(stale_311) + spatial_count

    roi = compute_productivity_roi(
        lots_validated=lots_validated,
        spatial_conflicts_checked=spatial_count,
        contracts_cleared=contracts_count,
        joins_automated=joins_total,
        actionable_discrepancies=discrepancies,
    )

    return {
        "ledger": ledger,
        "stale_311": stale_311,
        "conflicts": conflicts,
        "cleared": cleared,
        "parks_routing": parks,
        "productivity": productivity,
        "roi": roi,
    }
