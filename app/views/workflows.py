"""Analyst workflow views (QA, spatial, contract, productivity, ingest)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.analytics import ProductivityROI
from app.data_loader import (
    DATASET_REGISTRY,
    NYC_CRS,
    dataframe_to_map_df,
    gdf_to_map_df,
    ingestion_summary,
    token_status,
)


def render_roi_header(roi: ProductivityROI | None) -> None:
    token = token_status()
    st.markdown("### Productivity ROI")
    if token.get("demo_mode"):
        st.caption("Demo mode — synthetic data (set SOCRATA_APP_TOKEN for live Socrata).")
    if roi is None:
        st.info("Load datasets to compute productivity ROI.")
        return
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Manual joins eliminated", f"{roi.joins_automated:,}", help="Automated cross-dataset joins")
    c2.metric("Discrepancies flagged", f"{roi.actionable_discrepancies:,}", help="Owner, 311, spatial flags")
    c3.metric("Lots validated", f"{roi.lots_validated:,}", help="BBL ledger rows")
    c4.metric("Spatial conflicts", f"{roi.spatial_conflicts_checked:,}", help="Schedule ∩ permit overlaps")
    c5.metric("Est. hours reclaimed", f"{roi.hours_reclaimed:.1f} h", help="Engineering time-savings model")


def view_qa(results: dict) -> None:
    st.subheader("QA/QC & Inventory Ledger")
    st.caption("Lot Info ⨝ MapPLUTO on BBL; stale 311 complaints > 30 days.")
    ledger = results["ledger"]
    stale = results["stale_311"]
    if ledger.empty:
        st.warning("Lot Info empty or failed to load. Check ingestion matrix or token.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Lots in ledger", len(ledger))
    c2.metric("Owner discrepancies", int(ledger.get("owner_discrepancy", pd.Series(dtype=bool)).sum()))
    c3.metric("Stale 311 complaints", len(stale))
    show = ledger.copy()
    if "owner_discrepancy" in show.columns:
        show = show[show["owner_discrepancy"] | show.get("missing_or_corrupt", False)]
    st.dataframe(show.head(500), use_container_width=True, hide_index=True)
    if not show.empty:
        st.download_button("Export QA ledger (CSV)", show.to_csv(index=False).encode("utf-8"), "qa_ledger.csv")
    if not stale.empty:
        st.markdown("**Unaddressed 311 (>30 days)**")
        st.dataframe(stale.head(200), use_container_width=True, hide_index=True)


def _conflicts_map_df(conflicts: pd.DataFrame) -> pd.DataFrame:
    if conflicts.empty or "note" in conflicts.columns:
        return pd.DataFrame(columns=["lat", "lon", "layer"])
    mapped = dataframe_to_map_df(conflicts, layer="conflict")
    if not mapped.empty:
        return mapped
    if "geometry" in conflicts.columns and conflicts["geometry"].notna().any():
        try:
            import geopandas as gpd

            gdf = gpd.GeoDataFrame(conflicts.copy(), geometry=conflicts["geometry"], crs=NYC_CRS)
            return gdf_to_map_df(gdf, layer="conflict")
        except Exception:
            pass
    return mapped


def view_spatial(results: dict, map_layers: dict[str, pd.DataFrame]) -> None:
    st.subheader("Spatial Conflict Detection")
    conflicts = results["conflicts"]
    if conflicts.empty:
        st.success("No spatial intersections in loaded layers.") if "note" not in conflicts.columns else st.warning(
            str(conflicts["note"].iloc[0])
        )
    else:
        st.metric("Active spatial conflicts", len(conflicts))
    map_points: list[pd.DataFrame] = []
    for key, label in (("inspection", "SMD Inspection"), ("street_permits", "Street Permits")):
        layer_df = map_layers.get(key, pd.DataFrame())
        if not layer_df.empty:
            layer_df = layer_df.copy()
            layer_df["layer"] = label
            map_points.append(layer_df)
    conflict_pts = _conflicts_map_df(conflicts)
    if not conflict_pts.empty:
        conflict_pts = conflict_pts.copy()
        conflict_pts["layer"] = "Conflict"
        map_points.append(conflict_pts)
    if map_points:
        combined = pd.concat(map_points, ignore_index=True)
        st.map(combined, latitude="lat", longitude="lon", color="layer", size=20)
    if not conflicts.empty and "note" not in conflicts.columns:
        display_cols = [c for c in ("conflict_id", "conflict_type", "_bbl") if c in conflicts.columns]
        extra = [c for c in conflicts.columns if c not in display_cols][:8]
        table = conflicts[display_cols + extra].head(300)
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button("Export conflicts (CSV)", table.to_csv(index=False).encode("utf-8"), "spatial_conflicts.csv")


def view_contract(results: dict) -> None:
    st.subheader("Contract & Dispatch Clearance")
    cleared, parks = results["cleared"], results["parks_routing"]
    c1, c2 = st.columns(2)
    c1.metric("Contracts cleared", len(cleared))
    c2.metric("Parks routing tags", len(parks))
    if not cleared.empty:
        st.dataframe(cleared.head(300), use_container_width=True, hide_index=True)
        st.download_button("DOT dispatch list (CSV)", cleared.to_csv(index=False).encode("utf-8"), "dispatch.csv")
    if not parks.empty:
        st.dataframe(parks.head(200), use_container_width=True, hide_index=True)
        st.download_button("Parks routing (CSV)", parks.to_csv(index=False).encode("utf-8"), "parks_routing.csv")


def view_productivity(results: dict) -> None:
    st.subheader("Productivity & ADA Progress")
    prod = results["productivity"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Sidewalk feet repaired (est.)", f"{prod['feet_repaired']:,.0f}")
    c2.metric("Ramp installations", prod["ramp_installs"])
    c3.metric("High-demand corridors", prod["high_demand_corridors"])
    idx = prod.get("ramp_demand_index")
    if isinstance(idx, pd.DataFrame) and not idx.empty:
        st.scatter_chart(idx, x="lon", y="lat", color="source")
    else:
        st.info("Load ramp progress and pedestrian demand for spatial index.")


def view_ingest(frames: dict[str, pd.DataFrame]) -> None:
    st.subheader("Dataset Ingestion Matrix")
    summary = ingestion_summary(frames)
    st.dataframe(summary, use_container_width=True, hide_index=True)
    failed = summary[summary["error"].astype(str).str.len() > 0] if "error" in summary.columns else pd.DataFrame()
    if not failed.empty:
        st.error(f"{len(failed)} dataset(s) failed — see error column.")
    key = st.selectbox("Preview dataset", list(DATASET_REGISTRY.keys()))
    df = frames.get(key, pd.DataFrame())
    if not df.empty and "_error" in df.columns:
        st.error(str(df["_error"].iloc[0]))
    elif not df.empty:
        st.dataframe(df.head(100), use_container_width=True, hide_index=True)
