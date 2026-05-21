"""Manhattan Mission Control — Streamlit entry."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.analytics import ProductivityROI, run_all_workflows
from app.data_loader import (
    CACHE_TTL_SECONDS,
    DATASET_REGISTRY,
    NYC_CRS,
    WORKFLOW_DATASETS,
    dataframe_to_map_df,
    demo_mode_enabled,
    fetch_datasets_for_keys,
    gdf_to_map_df,
    ingestion_summary,
    keys_for_workflow,
    load_manhattan_map_layers,
    token_status,
)

st.set_page_config(
    page_title="Manhattan Mission Control",
    page_icon="🚧",
    layout="wide",
    initial_sidebar_state="expanded",
)

WORKFLOW_VIEWS = {
    "QA/QC & Inventory Ledger": "qa",
    "Spatial Conflict Detection": "spatial",
    "Contract & Dispatch Clearance": "contract",
    "Productivity & ADA Progress": "productivity",
}


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading workflow datasets…")
def _load_workflow_frames(workflow_key: str, limit: int) -> dict[str, pd.DataFrame]:
    keys = keys_for_workflow(workflow_key)
    return fetch_datasets_for_keys(keys, limit=limit)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading full ingestion matrix…")
def _load_all_frames(limit: int) -> dict[str, pd.DataFrame]:
    return fetch_datasets_for_keys(tuple(DATASET_REGISTRY.keys()), limit=limit)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading Manhattan map layers…")
def _load_map_layers(limit: int) -> dict[str, pd.DataFrame]:
    return load_manhattan_map_layers(limit=limit)


@st.cache_data(ttl=600, show_spinner="Running analyst workflows…")
def _run_workflows(frames: dict[str, pd.DataFrame]) -> dict:
    return run_all_workflows(frames)


def _render_productivity_header(roi: ProductivityROI | None, token: dict) -> None:
    st.markdown("### Productivity ROI")
    if token.get("demo_mode"):
        st.caption("Demo mode — synthetic data (set SOCRATA_APP_TOKEN for live Socrata).")
    if roi is None:
        st.info("Load datasets to compute live productivity ROI from analyst workflows.")
        c1, c2, c3, c4, c5 = st.columns(5)
        for col, label in zip(
            (c1, c2, c3, c4, c5),
            (
                "Manual joins eliminated",
                "Discrepancies flagged",
                "Lots validated",
                "Spatial conflicts",
                "Est. hours reclaimed",
            ),
            strict=True,
        ):
            col.metric(label, "—")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Manual joins eliminated", f"{roi.joins_automated:,}")
        c2.metric("Discrepancies flagged", f"{roi.actionable_discrepancies:,}")
        c3.metric("Lots validated", f"{roi.lots_validated:,}")
        c4.metric("Spatial conflicts", f"{roi.spatial_conflicts_checked:,}")
        c5.metric("Est. hours reclaimed", f"{roi.hours_reclaimed:.1f} h")
    auth_bits = []
    if token["configured"]:
        auth_bits.append("app token")
    if token.get("key_pair"):
        auth_bits.append("API key pair")
    auth = ", ".join(auth_bits) if auth_bits else "demo / public tier"
    st.caption(
        f"Socrata: {auth} ({token['masked']}) · {token['datasets']} datasets · CRS {NYC_CRS}"
    )


def _view_qa(results: dict) -> None:
    st.subheader("QA/QC & Inventory Ledger")
    st.caption("Lot Info (`i642-2fxq`) ⨝ MapPLUTO (`6fi9-q3ta`) on BBL; stale 311 (`erm2-nwe9`) > 30 days.")
    ledger = results["ledger"]
    stale = results["stale_311"]
    if ledger.empty:
        st.warning("Lot Info dataset empty or failed to load.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Lots in ledger", len(ledger))
    c2.metric("Owner discrepancies", int(ledger.get("owner_discrepancy", pd.Series(dtype=bool)).sum()))
    c3.metric("Stale 311 complaints", len(stale))
    show = ledger.copy()
    if "owner_discrepancy" in show.columns:
        show = show[show["owner_discrepancy"] | show.get("missing_or_corrupt", False)]
    st.dataframe(show.head(500), use_container_width=True, hide_index=True)
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


def _view_spatial(results: dict, map_layers: dict[str, pd.DataFrame]) -> None:
    st.subheader("Spatial Conflict Detection Engine")
    st.caption(
        "Weekly schedule (`r528-jcks`) ∩ permits (`tqtj-sjs8`) and capital blocks (`jvk9-k4re`) in EPSG:2263. "
        "Map shows Manhattan-filtered inspection (`dntt-gqwq`) and permits (`tqtj-sjs8`)."
    )
    conflicts = results["conflicts"]
    if conflicts.empty:
        if "note" in conflicts.columns:
            st.warning(str(conflicts["note"].iloc[0]))
        else:
            st.success("No spatial intersections detected in cached layers (or geopandas unavailable).")
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
        st.markdown("**Manhattan activity & conflicts**")
        st.map(combined, latitude="lat", longitude="lon", color="layer", size=20)
        st.caption(f"{len(combined):,} mapped points across {combined['layer'].nunique()} layers")
    else:
        st.info("No lat/lon or geometry available for map layers.")

    if not conflicts.empty and "note" not in conflicts.columns:
        display_cols = [c for c in ("conflict_id", "conflict_type", "_bbl") if c in conflicts.columns]
        extra = [c for c in conflicts.columns if c not in display_cols][:8]
        table = conflicts[display_cols + extra].head(300)
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button(
            label="Download Active Conflicts Report (CSV)",
            data=table.to_csv(index=False).encode("utf-8"),
            file_name="spatial_conflicts_report.csv",
            mime="text/csv",
        )


def _view_contract(results: dict) -> None:
    st.subheader("Contract & Dispatch Clearance Tracker")
    st.caption("Violations (`6kbp-uz6m`) grace period elapsed; Parks routing via tree damage (`j6v2-6uxq`).")
    cleared = results["cleared"]
    parks = results["parks_routing"]
    c1, c2 = st.columns(2)
    c1.metric("Contracts cleared (post-grace)", len(cleared))
    c2.metric("Parks coordination tags", len(parks))
    if not cleared.empty:
        st.dataframe(cleared.head(300), use_container_width=True, hide_index=True)
        st.download_button(
            label="Download DOT Dispatch List (CSV)",
            data=cleared.to_csv(index=False).encode("utf-8"),
            file_name="sim_cleared_dispatch.csv",
            mime="text/csv",
        )
    if not parks.empty:
        st.markdown("**Parks Department routing**")
        st.dataframe(parks.head(200), use_container_width=True, hide_index=True)
        st.download_button(
            label="Download Parks Coordination List (CSV)",
            data=parks.to_csv(index=False).encode("utf-8"),
            file_name="parks_tree_damage_routing.csv",
            mime="text/csv",
        )


def _view_productivity(results: dict) -> None:
    st.subheader("Active Productivity & ADA Progress Dashboard")
    st.caption("Built (`ugc8-s3f6`) vs ramp progress (`e7gc-ub6z`) on pedestrian demand (`fwpa-qxaf`).")
    prod = results["productivity"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Sidewalk feet repaired (est.)", f"{prod['feet_repaired']:,.0f}")
    c2.metric("Ramp installations", prod["ramp_installs"])
    c3.metric("High-demand corridors", prod["high_demand_corridors"])
    idx = prod.get("ramp_demand_index")
    if isinstance(idx, pd.DataFrame) and not idx.empty:
        st.scatter_chart(idx, x="lon", y="lat", color="source")
    else:
        st.info("Load ramp + demand datasets with lat/lon for spatial index chart.")


def _view_ingest(frames: dict[str, pd.DataFrame]) -> None:
    st.subheader("Dataset Ingestion Matrix")
    st.dataframe(ingestion_summary(frames), use_container_width=True, hide_index=True)
    key = st.selectbox("Preview dataset", list(DATASET_REGISTRY.keys()))
    df = frames.get(key, pd.DataFrame())
    if not df.empty and "_error" in df.columns:
        st.error(str(df["_error"].iloc[0]))
    else:
        st.dataframe(df.head(100), use_container_width=True, hide_index=True)


def main() -> None:
    st.title("Manhattan Mission Control")
    st.markdown(
        "NYC DOT Sidewalk Inspection & Management (SIM) — unified Socrata ingestion, "
        "spatial cross-reference, and analyst workflow automation."
    )

    show_ingest = False
    with st.sidebar:
        st.header("Workflows")
        view_label = st.radio("Analyst view", list(WORKFLOW_VIEWS.keys()), index=0)
        view_key = WORKFLOW_VIEWS[view_label]
        st.divider()
        st.header("Data load")
        row_limit = st.slider("Max rows per dataset", 1_000, 50_000, 10_000, step=1_000)
        if demo_mode_enabled():
            st.info("Demo mode active — no live API calls. Set SOCRATA_APP_TOKEN to go live.")
        refresh = st.button("Refresh cache", type="primary")
        if refresh:
            st.cache_data.clear()
        st.caption(f"Loads {len(WORKFLOW_DATASETS.get(view_key, ()))} datasets for this view (not all 16).")
        with st.expander("Ingestion matrix", expanded=False):
            show_ingest = st.button("Open ingestion utilities")

    token = token_status()
    roi: ProductivityROI | None = None
    results: dict | None = None
    frames: dict[str, pd.DataFrame] = {}
    map_layers: dict[str, pd.DataFrame] = {}

    try:
        if show_ingest:
            frames = _load_all_frames(row_limit)
        else:
            frames = _load_workflow_frames(view_key, row_limit)
        if view_key == "spatial":
            map_layers = _load_map_layers(min(row_limit, 25_000))
        results = _run_workflows(frames)
        roi = results["roi"]
    except ImportError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Socrata ingestion failed: {exc}")
        st.info("Set SOCRATA_APP_TOKEN in .env, enable demo mode, or run: pip install -e \".[mission]\"")
        st.stop()

    with st.container():
        _render_productivity_header(roi, token)

    if show_ingest:
        _view_ingest(frames)
    elif view_key == "qa":
        _view_qa(results)
    elif view_key == "spatial":
        _view_spatial(results, map_layers)
    elif view_key == "contract":
        _view_contract(results)
    elif view_key == "productivity":
        _view_productivity(results)

    if roi is not None:
        with st.expander("ROI calculation detail"):
            st.json(roi.as_dict())
            st.markdown(
                "**Formula:** `(lots × 3 min) + (spatial conflicts × 15 min) + (contracts cleared × 5 min)` → hours"
            )


if __name__ == "__main__":
    main()
