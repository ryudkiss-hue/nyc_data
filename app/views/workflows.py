"""Analyst workflow views (QA, spatial, contract, productivity, quality, ingest)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.analytics import (
    DatasetProfile,
    ProductivityROI,
    compare_datasets,
    profile_dataset,
    quality_summary,
)
from app.data_loader import (
    DATASET_REGISTRY,
    NYC_CRS,
    dataframe_to_map_df,
    gdf_to_map_df,
    ingestion_summary,
    token_status,
)

_URGENCY_COLORS = {"critical": "🔴", "urgent": "🟠", "normal": "🟡", "ok": "🟢"}


# ---------------------------------------------------------------------------
# ROI Header
# ---------------------------------------------------------------------------

def render_roi_header(roi: ProductivityROI | None) -> None:
    token = token_status()
    st.markdown("### 📊 Productivity ROI — Live Telemetry")
    if token.get("demo_mode"):
        st.caption("⚠️ Demo mode — synthetic data (set SOCRATA_APP_TOKEN for live Socrata).")
    if roi is None:
        st.info("Load datasets to compute productivity ROI.")
        return

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(
        "Joins automated",
        f"{roi.joins_automated:,}",
        help="Cross-dataset BBL/spatial joins eliminating manual lookups",
    )
    c2.metric(
        "Discrepancies flagged",
        f"{roi.actionable_discrepancies:,}",
        help="Owner, 311-stale, spatial conflict flags",
    )
    c3.metric(
        "Lots validated",
        f"{roi.lots_validated:,}",
        help="BBL ledger rows cross-checked against MapPLUTO",
    )
    c4.metric(
        "Spatial conflicts",
        f"{roi.spatial_conflicts_checked:,}",
        delta=f"-{roi.spatial_conflicts_checked} manual" if roi.spatial_conflicts_checked else None,
        delta_color="normal",
        help="Schedule ∩ permit + schedule ∩ capital block overlaps",
    )
    c5.metric(
        "Hours reclaimed",
        f"{roi.hours_reclaimed:.1f} h",
        help="Engineering time-savings model: lots×3min + conflicts×15min + contracts×5min",
    )
    c6.metric(
        "Quality flags",
        f"{roi.quality_flags:,}",
        help="Total data quality issues detected across all workflows",
    )


# ---------------------------------------------------------------------------
# QA / QC Ledger
# ---------------------------------------------------------------------------

def view_qa(results: dict) -> None:
    st.subheader("🔍 QA/QC & Inventory Ledger")
    st.caption("Lot Info ⨝ MapPLUTO on BBL · owner-mismatch & stale 311 complaint detection")

    ledger = results["ledger"]
    stale = results["stale_311"]

    if ledger.empty:
        st.warning("Lot Info empty or failed to load. Check the ingestion matrix or your Socrata token.")
        st.info("**Fix:** Set `SOCRATA_APP_TOKEN` in `.env`, or enable demo mode from the sidebar.")
        return

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lots in ledger", f"{len(ledger):,}")
    owner_flag_count = int(ledger.get("owner_discrepancy", pd.Series(dtype=bool)).sum())
    c2.metric(
        "Owner discrepancies",
        f"{owner_flag_count:,}",
        delta=f"{owner_flag_count} need review" if owner_flag_count else "None",
        delta_color="inverse",
    )
    missing_count = int(ledger.get("missing_or_corrupt", pd.Series(dtype=bool)).sum())
    c3.metric("Missing/corrupt rows", f"{missing_count:,}", delta_color="inverse")
    c4.metric("Stale 311 complaints", f"{len(stale):,}", delta_color="inverse")

    # Ledger table
    show = ledger.copy()
    internal_cols = [c for c in show.columns if c.startswith("_")]

    tab_all, tab_issues, tab_stale = st.tabs(
        [f"All Lots ({len(show):,})", f"Issues ({owner_flag_count + missing_count:,})", f"Stale 311 ({len(stale):,})"]
    )

    with tab_all:
        disp = show.drop(columns=internal_cols, errors="ignore").head(500)
        st.dataframe(disp, use_container_width=True, hide_index=True)
        if not show.empty:
            csv = show.to_csv(index=False).encode("utf-8")
            st.download_button("⬇ Export full ledger (CSV)", csv, "qa_ledger.csv", mime="text/csv")

    with tab_issues:
        if owner_flag_count + missing_count == 0:
            st.success("✅ No discrepancies or missing data detected!")
        else:
            mask = pd.Series([False] * len(show), index=show.index)
            if "owner_discrepancy" in show.columns:
                mask = mask | show["owner_discrepancy"]
            if "missing_or_corrupt" in show.columns:
                mask = mask | show["missing_or_corrupt"]
            issues_df = show[mask].drop(columns=internal_cols, errors="ignore").head(500)
            if "_quality_severity" in show.columns:
                issues_df = show[mask].copy()
                issues_df["severity"] = issues_df.get("_quality_severity", "info").map(
                    lambda x: _URGENCY_COLORS.get(x, "🔵")
                )
            st.dataframe(issues_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇ Export issues (CSV)",
                issues_df.to_csv(index=False).encode("utf-8"),
                "qa_issues.csv",
                mime="text/csv",
            )

    with tab_stale:
        if stale.empty:
            st.success("✅ No stale 311 complaints (> 30 days unaddressed).")
        else:
            stale_disp = stale.drop(columns=[c for c in stale.columns if c.startswith("_")], errors="ignore").head(300)
            if "_days_open" in stale.columns:
                stale_disp["days_open"] = stale["_days_open"]
            st.dataframe(stale_disp, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇ Export stale 311 (CSV)",
                stale_disp.to_csv(index=False).encode("utf-8"),
                "stale_311.csv",
                mime="text/csv",
            )


# ---------------------------------------------------------------------------
# Spatial Conflict Detection
# ---------------------------------------------------------------------------

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
    st.subheader("🗺️ Spatial Conflict Detection")
    st.caption(
        "Geospatial intersection: weekly construction schedule vs street permits vs capital reconstruction blocks"
    )

    conflicts = results["conflicts"]
    has_note = not conflicts.empty and "note" in conflicts.columns

    if has_note:
        st.warning(str(conflicts["note"].iloc[0]))
    elif conflicts.empty:
        st.success("✅ No active spatial intersections detected in the loaded layers.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Active spatial conflicts", len(conflicts))
        if "conflict_type" in conflicts.columns:
            by_type = conflicts["conflict_type"].value_counts()
            c2.metric(
                "Weekly vs. permit",
                int(by_type.get("weekly_vs_permit", 0)),
            )
            c3.metric(
                "Weekly vs. capital",
                int(by_type.get("weekly_vs_capital", 0)),
            )

    # Map visualization
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
        conflict_pts["layer"] = "⚠️ Conflict"
        map_points.append(conflict_pts)

    if map_points:
        combined = pd.concat(map_points, ignore_index=True)
        st.map(combined, latitude="lat", longitude="lon", color="layer", size=20)
        st.caption(f"Showing {len(combined):,} points · {len([x for x in map_points if not x.empty])} layers")
    else:
        st.info("No geospatial layers loaded. Select 'Spatial' workflow and reload datasets.")

    if not conflicts.empty and not has_note:
        display_cols = [c for c in ("conflict_id", "conflict_type", "conflict_severity", "_bbl", "detected_at") if c in conflicts.columns]
        extra = [c for c in conflicts.columns if c not in display_cols and not c.startswith("_")][:6]
        table = conflicts[display_cols + extra].head(300)
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Export conflicts (CSV)",
            table.to_csv(index=False).encode("utf-8"),
            "spatial_conflicts.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
# Contract & Dispatch Clearance
# ---------------------------------------------------------------------------

def view_contract(results: dict) -> None:
    st.subheader("📋 Contract & Dispatch Clearance")
    st.caption("Violations past grace period → DOT dispatch queue · Tree-damage BBL → Parks routing")

    cleared = results["cleared"]
    parks = results["parks_routing"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Contracts cleared", f"{len(cleared):,}")
    c2.metric("Parks routing tags", f"{len(parks):,}")
    if not cleared.empty and "_clearance_urgency" in cleared.columns:
        critical = int((cleared["_clearance_urgency"] == "critical").sum())
        c3.metric("Critical (>365 days)", f"{critical:,}", delta_color="inverse")

    tab_cleared, tab_parks = st.tabs(
        [f"DOT Dispatch ({len(cleared):,})", f"Parks Routing ({len(parks):,})"]
    )

    with tab_cleared:
        if cleared.empty:
            st.info("No contracts past grace period — or violations dataset not loaded.")
        else:
            disp = cleared.copy()
            if "_clearance_urgency" in disp.columns:
                disp["urgency"] = disp["_clearance_urgency"].map(lambda x: _URGENCY_COLORS.get(x, "🔵"))
            show_cols = [c for c in disp.columns if not c.startswith("_")]
            st.dataframe(disp[show_cols].head(300), use_container_width=True, hide_index=True)
            st.download_button(
                "⬇ DOT dispatch list (CSV)",
                cleared.to_csv(index=False).encode("utf-8"),
                "dispatch.csv",
                mime="text/csv",
            )

    with tab_parks:
        if parks.empty:
            st.info("No Parks Department routing tags generated.")
        else:
            show_cols = [c for c in parks.columns if not c.startswith("_")]
            st.dataframe(parks[show_cols].head(200), use_container_width=True, hide_index=True)
            st.download_button(
                "⬇ Parks routing (CSV)",
                parks.to_csv(index=False).encode("utf-8"),
                "parks_routing.csv",
                mime="text/csv",
            )


# ---------------------------------------------------------------------------
# Productivity & ADA Progress
# ---------------------------------------------------------------------------

def view_productivity(results: dict) -> None:
    st.subheader("🚶 Productivity & ADA Ramp Progress")
    st.caption("Sidewalk linear feet repaired · ramp program completion · high-demand corridor overlay")

    prod = results["productivity"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sidewalk feet repaired", f"{prod['feet_repaired']:,.0f} ft")
    c2.metric("Ramp installations completed", f"{prod['ramp_installs']:,}")
    c3.metric("Ramps pending", f"{prod.get('ramp_pending', 0):,}")
    completion = prod.get("completion_rate_pct", 0.0)
    c4.metric("Completion rate", f"{completion:.1f}%")

    if completion > 0:
        st.progress(
            completion / 100.0,
            text=f"Ramp program: {completion:.1f}% complete",
        )

    st.metric("High-demand corridors identified", f"{prod['high_demand_corridors']:,}")

    idx = prod.get("ramp_demand_index")
    if isinstance(idx, pd.DataFrame) and not idx.empty:
        st.caption("Ramp install locations vs. pedestrian demand corridors:")
        st.scatter_chart(idx, x="lon", y="lat", color="source", height=400)
    else:
        st.info(
            "Load **ramp_progress** and **pedestrian_demand** datasets for the demand×supply spatial index."
        )


# ---------------------------------------------------------------------------
# Data Quality View
# ---------------------------------------------------------------------------

def view_quality(results: dict, frames: dict) -> None:
    st.subheader("🩺 Data Quality Dashboard")
    st.caption("Automated column profiling, null analysis, and schema health scores")

    profiles = results.get("profiles", {})

    if not profiles:
        st.info("No dataset profiles available. Load workflow datasets first.")
        return

    # Summary table
    st.markdown("#### Quality Scorecard")
    summary_df = quality_summary(profiles)
    if not summary_df.empty:
        # Color-code quality score column
        def _score_color(score: float) -> str:
            if score >= 80:
                return "🟢"
            if score >= 60:
                return "🟡"
            return "🔴"

        summary_df["grade"] = summary_df["quality_score"].map(_score_color)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Export quality scorecard (CSV)",
            summary_df.to_csv(index=False).encode("utf-8"),
            "quality_scorecard.csv",
            mime="text/csv",
        )

        # Store SLA compliance report in session state for sidebar SLA monitor
        sla_details = []
        for _, row in summary_df.iterrows():
            score = row["quality_score"]
            status = "✅ Passing" if score >= 90 else ("⚠️ At Risk" if score >= 70 else "🔴 Critical")
            sla_details.append({
                "dataset": row["dataset"],
                "target": "90%",
                "actual": f"{score:.1f}%",
                "gap": f"{score - 90:+.1f}%",
                "status": status,
                "severity": "none" if score >= 90 else ("low" if score >= 70 else "critical"),
            })

        st.session_state["sla_compliance_report"] = {
            "overall_compliance_pct": summary_df["quality_score"].mean(),
            "breach_count": len(summary_df[summary_df["quality_score"] < 90]),
            "total_slas": len(summary_df),
            "sla_details": sla_details,
        }

    # Per-dataset column profiles
    st.markdown("#### Column Profiles")
    selected_key = st.selectbox("Select dataset to profile", list(profiles.keys()))
    if selected_key and selected_key in profiles:
        prof = profiles[selected_key]
        st.markdown(
            f"**{selected_key}** — {prof.row_count:,} rows · {prof.col_count} cols · "
            f"Quality score: **{prof.quality_score:.0f}/100** · "
            f"Null rate: {prof.overall_null_pct:.1f}% · "
            f"Dup rate: {prof.duplicate_row_pct:.1f}%"
        )

        col_rows = []
        for cp in prof.columns:
            col_rows.append({
                "column": cp.name,
                "type": cp.dtype,
                "null_%": cp.null_pct,
                "cardinality": cp.cardinality,
                "min": cp.min_val,
                "max": cp.max_val,
                "samples": " | ".join(cp.sample_values),
                "score": round(cp.quality_score(), 1),
            })
        if col_rows:
            cols_df = pd.DataFrame(col_rows)
            st.dataframe(cols_df, use_container_width=True, hide_index=True)

    # Dataset comparison
    if len(profiles) >= 2:
        st.markdown("#### Dataset Comparison")
        keys = list(profiles.keys())
        col_a, col_b = st.columns(2)
        ds_a = col_a.selectbox("Dataset A", keys, index=0, key="cmp_a")
        ds_b = col_b.selectbox("Dataset B", keys, index=min(1, len(keys) - 1), key="cmp_b")
        if ds_a and ds_b and ds_a != ds_b:
            df_a = frames.get(ds_a, pd.DataFrame())
            df_b = frames.get(ds_b, pd.DataFrame())
            if not df_a.empty and not df_b.empty:
                cmp_df = compare_datasets(df_a, df_b, ds_a, ds_b)
                st.dataframe(cmp_df, use_container_width=True, hide_index=True)
                shared = len(cmp_df[cmp_df["shared"] == "✓"])
                join_cands = len(cmp_df[cmp_df["join_candidate"] == "🔑"])
                st.caption(
                    f"Shared columns: **{shared}** · Join key candidates: **{join_cands}** · "
                    f"Only in {ds_a}: {len(cmp_df[cmp_df[f'in_{ds_b}'] == '—'])} · "
                    f"Only in {ds_b}: {len(cmp_df[cmp_df[f'in_{ds_a}'] == '—'])}"
                )


# ---------------------------------------------------------------------------
# Ingestion Matrix
# ---------------------------------------------------------------------------

def view_ingest(frames: dict[str, pd.DataFrame]) -> None:
    st.subheader("📥 Dataset Ingestion Matrix")
    st.caption("Live row counts, BBL coverage, and error status for all registered datasets")

    summary = ingestion_summary(frames)

    # Color failed rows
    failed = (
        summary[summary["error"].astype(str).str.len() > 0]
        if "error" in summary.columns
        else pd.DataFrame()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Total datasets", len(summary))
    c2.metric("Loaded successfully", len(summary) - len(failed))
    c3.metric("Failed / empty", len(failed), delta_color="inverse")

    st.dataframe(summary, use_container_width=True, hide_index=True)

    if not failed.empty:
        st.error(
            f"⚠️ {len(failed)} dataset(s) failed to load — see the **error** column above. "
            "Check your `SOCRATA_APP_TOKEN` or try demo mode."
        )

    st.divider()
    key = st.selectbox(
        "Preview raw dataset",
        list(DATASET_REGISTRY.keys()),
        help="Inspect the first 100 rows of any registered dataset",
    )
    df = frames.get(key, pd.DataFrame())
    if not df.empty and "_error" in df.columns:
        st.error(f"Ingestion error: {df['_error'].iloc[0]}")
        st.info(f"**Dataset:** {DATASET_REGISTRY[key]['label']} — Fourfour: `{DATASET_REGISTRY[key]['fourfour']}`")
    elif not df.empty:
        st.caption(f"{len(df):,} rows · {len(df.columns)} columns · Key: `{key}`")
        show_cols = [c for c in df.columns if not c.startswith("_")]
        st.dataframe(df[show_cols].head(100), use_container_width=True, hide_index=True)
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"⬇ Download {key}.csv",
            csv_data,
            f"{key}.csv",
            mime="text/csv",
        )
    else:
        st.warning(f"Dataset `{key}` not loaded. Run a workflow that includes this dataset.")
