"""NYC DOT SIM Construction List Generator — upload-driven analyst view."""

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.data_loader import (
    DATE_CANDIDATES,
    LAT_CANDIDATES,
    LON_CANDIDATES,
    demo_mode_enabled,
    fetch_dataset,
    pick_column,
)
from socrata_toolkit.core.utils import BOROUGH_LIST

try:
    import plotly.express as px

    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False

_BOROUGHS = sorted(BOROUGH_LIST)  # alphabetical order preserved from original

_INSPECTION_COLUMNS = {
    "block_id",
    "borough",
    "address",
    "condition_score",
    "defect_type",
    "inspection_date",
    "area_sqft",
    "priority_score",
    "status",
}

_CONTRACT_COLUMNS = {
    "contract_id",
    "block_id",
    "borough",
    "start_date",
    "end_date",
    "status",
    "contractor",
}

_SCHEDULE_COLUMNS = {
    "block_id",
    "borough",
    "planned_start",
    "planned_end",
    "priority_score",
}

# ---------------------------------------------------------------------------
# Socrata data loader
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86_400, show_spinner="Loading inspection data from Socrata…")
def _load_inspection_from_socrata(limit: int = 25_000) -> pd.DataFrame:
    """Load and normalize the SMD inspection dataset for the construction list view."""
    df = fetch_dataset("inspection", limit=limit)
    if df.empty:
        return df
    df = df.copy()
    lat_col = pick_column(df, LAT_CANDIDATES)
    lon_col = pick_column(df, LON_CANDIDATES)
    date_col = pick_column(df, DATE_CANDIDATES)
    renames: dict[str, str] = {}
    if lat_col and lat_col != "latitude":
        renames[lat_col] = "latitude"
    if lon_col and lon_col != "longitude":
        renames[lon_col] = "longitude"
    if date_col and date_col != "inspection_date":
        renames[date_col] = "inspection_date"
    for src, dst in [("boro", "borough"), ("streetname", "address"), ("onstreet", "address")]:
        if src in df.columns and dst not in df.columns:
            renames[src] = dst
    if renames:
        df = df.rename(columns=renames)
    if "block_id" not in df.columns:
        id_col = next(
            (c for c in df.columns if any(k in c.lower() for k in ("streetfaceid", "blockid", "inspectionid"))),
            None,
        )
        df["block_id"] = df[id_col].astype(str) if id_col else df.index.astype(str)
    for col in ("condition_score", "area_sqft"):
        if col not in df.columns:
            df[col] = None
    if "defect_type" not in df.columns:
        result_col = next((c for c in df.columns if "result" in c.lower()), None)
        df["defect_type"] = df[result_col] if result_col else "Unknown"
    if "status" not in df.columns:
        df["status"] = "Active"
    if "priority_score" not in df.columns:
        df["priority_score"] = 0.0
    return df

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _validate_columns(df: pd.DataFrame, required: set[str], label: str) -> list[str]:
    missing = required - set(df.columns)
    return [f"**{label}** is missing columns: {', '.join(sorted(missing))}"] if missing else []

def _compute_priority(
    df: pd.DataFrame,
    w_condition: float,
    w_area: float,
    w_age: float,
) -> pd.DataFrame:
    out = df.copy()

    scores = out["condition_score"].fillna(50).clip(0, 100)
    condition_norm = (100 - scores) / 100.0

    area_vals = out["area_sqft"].fillna(0).clip(lower=0)
    area_max = area_vals.max()
    area_norm = area_vals / area_max if area_max > 0 else pd.Series(0.0, index=out.index)

    try:
        inspection_dates = pd.to_datetime(out["inspection_date"], errors="coerce")
        today_ts = pd.Timestamp(date.today())
        age_days = (today_ts - inspection_dates).dt.days.fillna(0).clip(lower=0)
        age_max = age_days.max()
        age_norm = age_days / age_max if age_max > 0 else pd.Series(0.0, index=out.index)
    except Exception:
        age_norm = pd.Series(0.0, index=out.index)

    total_weight = w_condition + w_area + w_age
    if total_weight == 0:
        total_weight = 1.0

    out["priority_score"] = (
        (w_condition * condition_norm + w_area * area_norm + w_age * age_norm) / total_weight
    ).round(4)

    return out.sort_values("priority_score", ascending=False).reset_index(drop=True)

def _detect_conflicts(inspections: pd.DataFrame, contracts: pd.DataFrame) -> pd.DataFrame:
    merged = inspections[["block_id", "address", "borough"]].drop_duplicates("block_id").merge(
        contracts[["contract_id", "block_id", "borough", "start_date", "end_date", "contractor", "status"]],
        on="block_id",
        how="inner",
    )

    if merged.empty:
        return pd.DataFrame()

    try:
        insp_dates = pd.to_datetime(
            inspections.set_index("block_id")["inspection_date"], errors="coerce"
        )
        merged["inspection_date"] = merged["block_id"].map(insp_dates)
        merged["start_date"] = pd.to_datetime(merged["start_date"], errors="coerce")
        merged["end_date"] = pd.to_datetime(merged["end_date"], errors="coerce")
    except Exception:
        pass

    today_ts = pd.Timestamp(date.today())

    def _severity(row: pd.Series) -> str:
        try:
            s = row["start_date"]
            e = row["end_date"]
            if pd.isna(s) or pd.isna(e):
                return "UNKNOWN"
            # Contract window overlaps with today → active conflict
            if s <= today_ts <= e:
                return "HIGH"
            # Contract starts or ends within 90 days → adjacent/imminent
            days_to_start = (s - today_ts).days
            days_since_end = (today_ts - e).days
            if 0 <= days_to_start <= 90 or 0 <= days_since_end <= 90:
                return "MEDIUM"
            return "LOW"
        except Exception:
            return "UNKNOWN"

    merged["severity"] = merged.apply(_severity, axis=1)
    merged = merged.sort_values(
        "severity",
        key=lambda col: col.map({"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}),
    )
    return merged.reset_index(drop=True)

# ---------------------------------------------------------------------------
# Excel export helper
# ---------------------------------------------------------------------------

def _to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buf.getvalue()

# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def _render_construction_list_tab() -> None:
    st.subheader("Construction List Generator")
    st.caption(
        "Upload an inspection export or load from session, apply filters and priority weights, "
        "then generate and export a ranked construction list."
    )

    uploaded = st.file_uploader(
        "Upload inspection CSV",
        type=["csv"],
        key="insp_upload",
        help="Required columns: block_id, borough, address, condition_score, defect_type, "
        "inspection_date, area_sqft, priority_score, status",
    )

    df: pd.DataFrame | None = None
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
        except Exception as exc:
            st.error(f"Could not parse uploaded file: {exc}")
            return
    elif st.session_state.get("construction_inspection_df") is not None:
        df = st.session_state["construction_inspection_df"]
    else:
        with st.expander("No data loaded — load from Socrata or upload a file", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                soc_limit = st.number_input("Row limit", 1_000, 100_000, 25_000, step=5_000, key="ci_soc_lim")
                if st.button("Load from Socrata (SMD Inspection)", key="load_socrata_insp"):
                    loaded = _load_inspection_from_socrata(int(soc_limit))
                    if loaded.empty:
                        st.warning("No data returned. Check SOCRATA_APP_TOKEN in Settings.")
                    else:
                        st.session_state["construction_inspection_df"] = loaded
                        if demo_mode_enabled():
                            st.info("Running in demo mode — configure SOCRATA_APP_TOKEN for live data.")
                        st.rerun()
            with c2:
                st.caption(
                    "Or upload a CSV with columns: block_id, borough, address, "
                    "condition_score, defect_type, inspection_date, area_sqft, priority_score, status"
                )
            return

    if df is None or df.empty:
        st.warning("Loaded DataFrame is empty.")
        return

    errors = _validate_columns(df, _INSPECTION_COLUMNS, "Inspection data")
    if errors:
        for e in errors:
            st.error(e)
        st.caption("Columns found: " + ", ".join(df.columns.tolist()))
        return

    st.caption(f"Loaded {len(df):,} inspection records · {df['block_id'].nunique():,} unique blocks")

    # ---- Filters ----
    with st.expander("Filters", expanded=True):
        fc1, fc2 = st.columns(2)
        with fc1:
            boroughs_in_data = sorted(df["borough"].dropna().unique().tolist())
            selected_boroughs = st.multiselect(
                "Borough",
                options=boroughs_in_data,
                default=boroughs_in_data,
                key="filter_borough",
            )
            score_range = st.slider(
                "Condition Score range",
                min_value=0,
                max_value=100,
                value=(0, 100),
                key="filter_score",
            )
        with fc2:
            defect_types = sorted(df["defect_type"].dropna().unique().tolist())
            selected_defects = st.multiselect(
                "Defect Type",
                options=defect_types,
                default=defect_types,
                key="filter_defect",
            )
            statuses_in_data = sorted(df["status"].dropna().unique().tolist())
            selected_statuses = st.multiselect(
                "Status",
                options=statuses_in_data,
                default=statuses_in_data,
                key="filter_status",
            )

    mask = (
        df["borough"].isin(selected_boroughs)
        & df["condition_score"].between(score_range[0], score_range[1])
        & df["defect_type"].isin(selected_defects)
        & df["status"].isin(selected_statuses)
    )
    filtered_df = df[mask].copy()

    if filtered_df.empty:
        st.warning("No records match the current filters.")
        return

    # ---- Priority weights ----
    with st.expander("Priority Weights", expanded=True):
        wc1, wc2, wc3 = st.columns(3)
        w_condition = wc1.slider("Condition Weight", 0.0, 1.0, 0.5, step=0.05, key="w_cond")
        w_area = wc2.slider("Area Weight", 0.0, 1.0, 0.3, step=0.05, key="w_area")
        w_age = wc3.slider("Age Weight", 0.0, 1.0, 0.2, step=0.05, key="w_age")
        total = w_condition + w_area + w_age
        if total == 0:
            st.error("At least one weight must be greater than 0.")
        else:
            st.caption(
                f"Weights sum: **{total:.2f}** — "
                f"normalized condition={w_condition/total:.2f}, "
                f"area={w_area/total:.2f}, "
                f"age={w_age/total:.2f}"
            )

    if st.button("Generate Construction List", type="primary", key="gen_list"):
        if total == 0:
            st.error("Adjust weights before generating.")
        else:
            result = _compute_priority(filtered_df, w_condition, w_area, w_age)
            st.session_state["generated_construction_list"] = result

    result_df: pd.DataFrame | None = st.session_state.get("generated_construction_list")

    if result_df is not None and not result_df.empty:
        st.divider()
        st.markdown("#### Generated Construction List")

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Total Locations", f"{len(result_df):,}")
        sc2.metric("Avg Condition Score", f"{result_df['condition_score'].mean():.1f}")
        sc3.metric("Boroughs Covered", result_df["borough"].nunique())

        st.markdown("**By Borough**")
        borough_counts = (
            result_df.groupby("borough")
            .agg(locations=("block_id", "count"), avg_score=("condition_score", "mean"))
            .reset_index()
            .rename(columns={"avg_score": "avg_condition_score"})
            .sort_values("locations", ascending=False)
        )
        borough_counts["avg_condition_score"] = borough_counts["avg_condition_score"].round(1)
        st.dataframe(borough_counts, use_container_width=True, hide_index=True)

        st.dataframe(result_df, use_container_width=True, hide_index=True)

        try:
            excel_bytes = _to_excel_bytes(result_df, sheet_name="Construction List")
            st.download_button(
                "Export to Excel",
                data=excel_bytes,
                file_name="construction_list.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_construction_excel",
            )
        except ImportError:
            st.warning("openpyxl not installed — install it to enable Excel export.")
            csv_bytes = result_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Export to CSV (fallback)",
                data=csv_bytes,
                file_name="construction_list.csv",
                mime="text/csv",
                key="dl_construction_csv",
            )

def _render_conflict_detection_tab() -> None:
    st.subheader("Conflict Detection")
    st.caption(
        "Upload a construction list and a contracts/permits export. "
        "Records sharing a block_id with overlapping or adjacent date windows are flagged."
    )

    col_insp, col_contr = st.columns(2)
    with col_insp:
        insp_file = st.file_uploader(
            "Construction list CSV",
            type=["csv"],
            key="conflict_insp_upload",
            help="Must contain block_id, borough, address, inspection_date",
        )
    with col_contr:
        contr_file = st.file_uploader(
            "Contracts / permits CSV",
            type=["csv"],
            key="conflict_contr_upload",
            help="Must contain contract_id, block_id, borough, start_date, end_date, status, contractor",
        )

    insp_df: pd.DataFrame | None = None
    contr_df: pd.DataFrame | None = None

    if insp_file is not None:
        try:
            insp_df = pd.read_csv(insp_file)
        except Exception as exc:
            st.error(f"Could not parse construction list: {exc}")
            return
    elif st.session_state.get("generated_construction_list") is not None:
        insp_df = st.session_state["generated_construction_list"]
        st.info("Using construction list generated in Tab 1.")

    if contr_file is not None:
        try:
            contr_df = pd.read_csv(contr_file)
        except Exception as exc:
            st.error(f"Could not parse contracts file: {exc}")
            return

    if insp_df is None or contr_df is None:
        st.info(
            "Upload both files above, or generate a construction list in Tab 1 "
            "and upload a contracts file here."
        )
        return

    if insp_df is None or insp_df.empty:
        st.warning("Construction list is empty.")
        return
    if contr_df is None or contr_df.empty:
        st.warning("Contracts/permits file is empty.")
        return

    insp_errors = _validate_columns(insp_df, {"block_id", "borough", "address"}, "Construction list")
    contr_errors = _validate_columns(contr_df, _CONTRACT_COLUMNS, "Contracts/permits")
    all_errors = insp_errors + contr_errors
    if all_errors:
        for e in all_errors:
            st.error(e)
        return

    conflicts = _detect_conflicts(insp_df, contr_df)

    st.divider()
    if conflicts.empty:
        st.success("No block-level conflicts detected between the construction list and contracts.")
        return

    high = int((conflicts["severity"] == "HIGH").sum())
    medium = int((conflicts["severity"] == "MEDIUM").sum())
    low = int((conflicts["severity"] == "LOW").sum())

    cc1, cc2, cc3, cc4 = st.columns(4)
    cc1.metric("Total Conflicts", len(conflicts))
    cc2.metric("HIGH", high, delta=str(high) if high else None, delta_color="inverse")
    cc3.metric("MEDIUM", medium)
    cc4.metric("LOW", low)

    severity_filter = st.multiselect(
        "Filter by severity",
        options=["HIGH", "MEDIUM", "LOW", "UNKNOWN"],
        default=["HIGH", "MEDIUM", "LOW", "UNKNOWN"],
        key="conflict_severity_filter",
    )
    display_conflicts = conflicts[conflicts["severity"].isin(severity_filter)]

    st.dataframe(display_conflicts, use_container_width=True, hide_index=True)

    try:
        excel_bytes = _to_excel_bytes(display_conflicts, sheet_name="Conflicts")
        st.download_button(
            "Export Conflicts to Excel",
            data=excel_bytes,
            file_name="conflict_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_conflicts_excel",
        )
    except ImportError:
        st.warning("openpyxl not installed — falling back to CSV export.")
        csv_bytes = display_conflicts.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Export Conflicts to CSV",
            data=csv_bytes,
            file_name="conflict_report.csv",
            mime="text/csv",
            key="dl_conflicts_csv",
        )

def _render_schedule_tab() -> None:
    st.subheader("Schedule View")
    st.caption(
        "Gantt-style timeline of planned construction. "
        "Upload a schedule CSV or use the construction list from Tab 1."
    )

    if not _PLOTLY_AVAILABLE:
        st.warning(
            "plotly is not installed. Install it with `pip install plotly` to view the Gantt chart. "
            "The table view is still available below."
        )

    sched_file = st.file_uploader(
        "Schedule CSV (columns: block_id, borough, address, condition_score, priority_score, planned_start, planned_end)",
        type=["csv"],
        key="schedule_upload",
    )

    sched_df: pd.DataFrame | None = None

    if sched_file is not None:
        try:
            sched_df = pd.read_csv(sched_file)
        except Exception as exc:
            st.error(f"Could not parse schedule file: {exc}")
            return
    elif st.session_state.get("schedule_df") is not None:
        sched_df = st.session_state["schedule_df"]
    elif st.session_state.get("generated_construction_list") is not None:
        base = st.session_state["generated_construction_list"].copy()
        if "planned_start" not in base.columns or "planned_end" not in base.columns:
            today = pd.Timestamp(date.today())
            base["planned_start"] = [
                today + timedelta(days=i * 14) for i in range(len(base))
            ]
            base["planned_end"] = base["planned_start"] + timedelta(days=30)
        sched_df = base
        st.info("Using construction list from Tab 1 with auto-assigned placeholder dates.")

    if sched_df is None or sched_df.empty:
        st.info(
            "No schedule data loaded. Upload a CSV or generate a construction list in Tab 1 "
            "to populate the schedule view."
        )
        return

    errors = _validate_columns(sched_df, _SCHEDULE_COLUMNS, "Schedule")
    if errors:
        for e in errors:
            st.error(e)
        st.caption("Columns found: " + ", ".join(sched_df.columns.tolist()))
        return

    try:
        sched_df = sched_df.copy()
        sched_df["planned_start"] = pd.to_datetime(sched_df["planned_start"], errors="coerce")
        sched_df["planned_end"] = pd.to_datetime(sched_df["planned_end"], errors="coerce")
    except Exception as exc:
        st.error(f"Could not parse date columns: {exc}")
        return

    invalid_dates = sched_df["planned_start"].isna() | sched_df["planned_end"].isna()
    if invalid_dates.any():
        st.warning(
            f"{invalid_dates.sum()} row(s) have unparseable dates and will be excluded from the chart."
        )
        sched_df = sched_df[~invalid_dates]

    if sched_df.empty:
        st.warning("No rows with valid date ranges remain after filtering.")
        return

    if _PLOTLY_AVAILABLE:
        hover_extras: dict[str, str | bool] = {
            "priority_score": True,
            "planned_start": "|%Y-%m-%d",
            "planned_end": "|%Y-%m-%d",
        }
        if "condition_score" in sched_df.columns:
            hover_extras["condition_score"] = True
        if "address" in sched_df.columns:
            hover_extras["address"] = True

        gantt_label = sched_df["block_id"].astype(str)
        if "address" in sched_df.columns:
            gantt_label = sched_df["block_id"].astype(str) + " · " + sched_df["address"].fillna("")

        sched_df = sched_df.copy()
        sched_df["_label"] = gantt_label

        sort_col = "priority_score" if "priority_score" in sched_df.columns else "planned_start"
        sched_df = sched_df.sort_values(sort_col, ascending=False)

        fig = px.timeline(
            sched_df,
            x_start="planned_start",
            x_end="planned_end",
            y="_label",
            color="borough",
            title="Planned Construction Schedule",
            labels={"_label": "Block / Address", "borough": "Borough"},
            hover_data=hover_extras,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(
            yaxis_title="Block / Address",
            xaxis_title="Timeline",
            legend_title_text="Borough",
            height=max(400, len(sched_df) * 28 + 120),
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Install plotly to view the Gantt chart. Showing table view only.")

    with st.expander("Schedule table", expanded=not _PLOTLY_AVAILABLE):
        display_cols = [c for c in sched_df.columns if not c.startswith("_")]
        st.dataframe(sched_df[display_cols], use_container_width=True, hide_index=True)

    st.caption(
        f"{len(sched_df):,} blocks scheduled · "
        f"earliest start: {sched_df['planned_start'].min().date()} · "
        f"latest end: {sched_df['planned_end'].max().date()}"
    )

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_construction_page() -> None:
    st.markdown("## Construction List Generator")
    st.caption(
        "NYC DOT SIM · Project Analyst tools for construction list generation, "
        "GIS conflict identification, and schedule visualization."
    )

    tab_list, tab_conflicts, tab_schedule = st.tabs(
        ["Construction List Generator", "Conflict Detection", "Schedule View"]
    )

    with tab_list:
        _render_construction_list_tab()

    with tab_conflicts:
        _render_conflict_detection_tab()

    with tab_schedule:
        _render_schedule_tab()
