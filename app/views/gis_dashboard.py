"""GIS & Spatial Analysis dashboard for NYC DOT SIM Program."""

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.data_loader import (
    DATASET_REGISTRY,
    LAT_CANDIDATES,
    LON_CANDIDATES,
    demo_mode_enabled,
    fetch_dataset,
    pick_column,
)

try:
    import folium
    from streamlit_folium import st_folium  # type: ignore[import]
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

NYC_BOUNDS = {"lat_min": 40.477, "lat_max": 40.917, "lon_min": -74.259, "lon_max": -73.700}
BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]


def _normalize_inspection(df: pd.DataFrame) -> pd.DataFrame:
    """Map Socrata inspection columns to standard view column names."""
    if df.empty:
        return df
    df = df.copy()
    lat_col = pick_column(df, LAT_CANDIDATES)
    lon_col = pick_column(df, LON_CANDIDATES)
    if lat_col and lat_col != "latitude":
        df = df.rename(columns={lat_col: "latitude"})
    if lon_col and lon_col != "longitude":
        df = df.rename(columns={lon_col: "longitude"})
    for src, dst in [
        ("streetname", "street_name"),
        ("onstreet", "street_name"),
        ("boro", "borough"),
    ]:
        if src in df.columns and dst not in df.columns:
            df = df.rename(columns={src: dst})
    for col in ("latitude", "longitude"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _normalize_permits(df: pd.DataFrame) -> pd.DataFrame:
    """Map Socrata street_permits columns to standard view column names."""
    if df.empty:
        return df
    df = df.copy()
    lat_col = pick_column(df, LAT_CANDIDATES)
    lon_col = pick_column(df, LON_CANDIDATES)
    if lat_col and lat_col != "latitude":
        df = df.rename(columns={lat_col: "latitude"})
    if lon_col and lon_col != "longitude":
        df = df.rename(columns={lon_col: "longitude"})
    for src, dst in [
        ("boro", "borough"),
        ("permittee_s_borough", "borough"),
        ("jobtype", "permit_type"),
        ("worktype", "permit_type"),
        ("permittee_s_name", "applicant"),
        ("applicantname", "applicant"),
        ("startdate", "start_date"),
        ("expirationdate", "end_date"),
        ("jobno", "permit_id"),
    ]:
        if src in df.columns and dst not in df.columns:
            df = df.rename(columns={src: dst})
    for col in ("latitude", "longitude"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=86_400, show_spinner="Loading inspection data from Socrata…")
def _load_inspections(limit: int = 25_000) -> pd.DataFrame:
    df = fetch_dataset("inspection", limit=limit)
    return _normalize_inspection(df)


@st.cache_data(ttl=86_400, show_spinner="Loading permit data from Socrata…")
def _load_permits(limit: int = 25_000) -> pd.DataFrame:
    df = fetch_dataset("street_permits", limit=limit)
    return _normalize_permits(df)


@st.cache_data(ttl=86_400, show_spinner="Loading HIQA street construction inspections…")
def _load_street_construction_inspections(limit: int = 15_000) -> pd.DataFrame:
    try:
        df = fetch_dataset("street_construction_inspections", limit=limit)
        if "inspectiondate" in df.columns:
            df["inspectiondate"] = pd.to_datetime(df["inspectiondate"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86_400, show_spinner="Loading capital reconstruction intersections…")
def _load_capital_intersections(limit: int = 10_000) -> pd.DataFrame:
    try:
        df = fetch_dataset("capital_intersections", limit=limit)
        for col in ("designstar", "construc_2"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def _flag_in_bounds(df: pd.DataFrame) -> pd.DataFrame:
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return df
    mask = (
        df["latitude"].between(NYC_BOUNDS["lat_min"], NYC_BOUNDS["lat_max"])
        & df["longitude"].between(NYC_BOUNDS["lon_min"], NYC_BOUNDS["lon_max"])
    )
    return df[mask].copy()


def _detect_spatial_conflicts(inspections: pd.DataFrame, permits: pd.DataFrame) -> pd.DataFrame:
    if inspections.empty or permits.empty:
        return pd.DataFrame()

    # Join on block_id if present, otherwise fall back to borough-level match
    insp = inspections.copy()
    perm = permits.copy()

    if "block_id" in insp.columns and "block_id" in perm.columns:
        join_col = "block_id"
    elif "_bbl" in insp.columns and "_bbl" in perm.columns:
        join_col = "_bbl"
    elif "borough" in insp.columns and "borough" in perm.columns:
        join_col = "borough"
    else:
        return pd.DataFrame()

    common = set(insp[join_col].dropna()) & set(perm[join_col].dropna())
    if not common:
        return pd.DataFrame()

    insp_sub = insp[insp[join_col].isin(common)].copy()
    perm_sub = perm[perm[join_col].isin(common)].copy()

    today = pd.Timestamp.today()
    conflicts = []
    for _, permit in perm_sub.iterrows():
        bid = permit[join_col]
        matching = insp_sub[insp_sub[join_col] == bid]
        for _, insp_row in matching.iterrows():
            insp_date = insp_row.get("inspection_date") or insp_row.get("inspectiondate")
            days_gap = 999
            if insp_date:
                try:
                    days_gap = abs((today - pd.Timestamp(insp_date)).days)
                except Exception:
                    pass
            if days_gap <= 30:
                severity = "HIGH"
            elif days_gap <= 90:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            conflicts.append({
                join_col: bid,
                "borough": insp_row.get("borough", permit.get("borough", "")),
                "permit_type": permit.get("permit_type", permit.get("worktype", "")),
                "applicant": permit.get("applicant", ""),
                "severity": severity,
                "inspection_date": insp_date,
                "permit_start": permit.get("start_date", ""),
                "permit_end": permit.get("end_date", ""),
            })

    if not conflicts:
        return pd.DataFrame()
    df = pd.DataFrame(conflicts)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    df["_sort"] = df["severity"].map(order)
    return df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)


def _render_folium_map(df: pd.DataFrame, color_col: str = "condition_score") -> None:
    if not HAS_FOLIUM:
        st.info("Install folium and streamlit-folium for interactive maps: `pip install folium streamlit-folium`")
        return

    df_valid = _flag_in_bounds(df).dropna(subset=["latitude", "longitude"])
    if df_valid.empty:
        st.warning("No points within NYC bounds.")
        return

    center_lat = df_valid["latitude"].mean()
    center_lon = df_valid["longitude"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB positron")

    for _, row in df_valid.iterrows():
        val = row.get(color_col, 50)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 50
        r = int(min(255, max(0, (100 - val) * 2.55)))
        g = int(min(255, max(0, val * 2.55)))
        color = f"#{r:02x}{g:02x}40"

        popup_lines = [f"<b>{row.get('block_id', row.get('streetname', ''))}</b>"]
        for col in ("borough", "defect_type", "condition_score", "result", "status"):
            if col in row and pd.notna(row[col]):
                popup_lines.append(f"{col}: {row[col]}")
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup("<br>".join(popup_lines), max_width=200),
        ).add_to(m)

    st_folium(m, width=900, height=550, returned_objects=[])


def _render_plotly_map(df: pd.DataFrame, title: str = "Inspection Locations") -> None:
    if not HAS_PLOTLY:
        st.info("Install plotly for interactive charts.")
        return
    df_valid = _flag_in_bounds(df).dropna(subset=["latitude", "longitude"])
    if df_valid.empty:
        st.warning("No points within NYC bounds.")
        return

    color_col = next((c for c in ("condition_score", "result", "status") if c in df_valid.columns), None)
    hover_cols = [c for c in ("borough", "defect_type", "result", "status", "street_name") if c in df_valid.columns]

    fig = px.scatter_mapbox(
        df_valid,
        lat="latitude",
        lon="longitude",
        color=color_col,
        color_continuous_scale="RdYlGn" if color_col == "condition_score" else None,
        hover_data=hover_cols,
        zoom=10,
        title=title,
        height=550,
    )
    fig.update_layout(mapbox_style="carto-positron", margin={"r": 0, "t": 40, "l": 0, "b": 0})
    st.plotly_chart(fig, use_container_width=True)


def render_gis_page() -> None:
    st.header("🗺️ GIS & Spatial Analysis")
    st.caption("Conflict detection, hotspot mapping, and spatial reporting for sidewalk inspection data.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📍 Inspection Map",
        "⚠️ Conflict Detection",
        "🔥 Hotspot Analysis",
        "📊 Spatial Reports",
        "🚧 HIQA & Capital Projects",
    ])

    with tab1:
        _render_inspection_map_tab()
    with tab2:
        _render_conflict_detection_tab()
    with tab3:
        _render_hotspot_tab()
    with tab4:
        _render_spatial_reports_tab()
    with tab5:
        _render_hiqa_capital_tab()


def _get_inspection_df(key_prefix: str) -> pd.DataFrame:
    """Load inspections from Socrata or user-uploaded CSV."""
    source = st.radio(
        "Data source",
        ["Socrata (live)", "Upload CSV"],
        horizontal=True,
        key=f"{key_prefix}_src",
    )
    if source == "Socrata (live)":
        limit = st.number_input("Row limit", 1_000, 100_000, 25_000, step=5_000, key=f"{key_prefix}_lim")
        with st.spinner("Loading from Socrata…"):
            df = _load_inspections(int(limit))
        if demo_mode_enabled():
            st.caption("⚠️ Running in demo mode — configure SOCRATA_APP_TOKEN in Settings for live data.")
        return df
    else:
        up = st.file_uploader(
            "Upload inspection CSV (must include latitude and longitude columns)",
            type="csv",
            key=f"{key_prefix}_upload",
        )
        if up is None:
            st.info("Upload a CSV to continue.")
            return pd.DataFrame()
        df = pd.read_csv(up)
        return _normalize_inspection(df)


def _render_inspection_map_tab() -> None:
    st.subheader("Inspection Locations")
    df = _get_inspection_df("gis_insp")
    if df.empty:
        return

    if "latitude" not in df.columns or "longitude" not in df.columns:
        st.error("Data must contain latitude and longitude columns.")
        st.write("Columns found:", list(df.columns))
        return

    st.caption(f"Loaded {len(df):,} inspection records")

    col1, col2, col3 = st.columns(3)
    with col1:
        if "borough" in df.columns:
            boros = sorted(df["borough"].dropna().unique().tolist())
            borough_filter = st.multiselect("Borough", boros, default=boros, key="gis_boro")
        else:
            borough_filter = []
    with col2:
        if "condition_score" in df.columns:
            score_range = st.slider("Condition Score", 0, 100, (0, 100), key="gis_score")
        else:
            score_range = (0, 100)
    with col3:
        if "defect_type" in df.columns:
            defect_filter = st.multiselect(
                "Defect Type", sorted(df["defect_type"].dropna().unique()), key="gis_defect"
            )
        else:
            defect_filter = []

    mask = pd.Series([True] * len(df))
    if borough_filter and "borough" in df.columns:
        mask &= df["borough"].isin(borough_filter)
    if "condition_score" in df.columns:
        mask &= df["condition_score"].between(*score_range)
    if defect_filter and "defect_type" in df.columns:
        mask &= df["defect_type"].isin(defect_filter)
    df_filtered = df[mask].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Locations", f"{len(df_filtered):,}")
    if "condition_score" in df_filtered.columns and not df_filtered.empty:
        c2.metric("Avg Condition Score", f"{df_filtered['condition_score'].mean():.1f}")
        critical = (df_filtered["condition_score"] < 30).sum()
        c3.metric("Critical (<30)", f"{critical:,}", delta=f"-{critical}", delta_color="inverse")

    map_engine = st.radio("Map engine", ["Plotly (recommended)", "Folium (interactive)"], horizontal=True, key="gis_engine")
    if map_engine.startswith("Plotly"):
        _render_plotly_map(df_filtered)
    else:
        _render_folium_map(df_filtered)

    with st.expander("Data Table"):
        st.dataframe(df_filtered, use_container_width=True, height=300)
        st.download_button(
            "Download filtered CSV",
            df_filtered.to_csv(index=False).encode(),
            "inspections_filtered.csv",
            "text/csv",
        )


def _render_conflict_detection_tab() -> None:
    st.subheader("⚠️ Conflict Detection")
    st.caption("Identify inspection locations that overlap with active permits or capital projects.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Inspection Data**")
        df_insp = _get_inspection_df("conf_insp")

    with col2:
        st.markdown("**Permits / Contracts**")
        perm_src = st.radio("Source", ["Socrata (live)", "Upload CSV"], horizontal=True, key="conf_perm_src")
        if perm_src == "Socrata (live)":
            perm_limit = st.number_input("Row limit", 1_000, 50_000, 15_000, step=5_000, key="conf_perm_lim")
            with st.spinner("Loading permits from Socrata…"):
                df_perm = _load_permits(int(perm_limit))
        else:
            up2 = st.file_uploader("Upload permits CSV", type="csv", key="conf_perm_up")
            df_perm = _normalize_permits(pd.read_csv(up2)) if up2 else pd.DataFrame()

    if df_insp.empty or df_perm.empty:
        st.info("Load both datasets to detect conflicts.")
        return

    conflicts = _detect_spatial_conflicts(df_insp, df_perm)

    if conflicts.empty:
        st.success("✅ No spatial conflicts detected between the loaded datasets.")
        return

    high = (conflicts["severity"] == "HIGH").sum()
    med = (conflicts["severity"] == "MEDIUM").sum()
    low = (conflicts["severity"] == "LOW").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Conflicts", len(conflicts))
    c2.metric("🔴 High", high, delta=f"+{high}" if high else None, delta_color="inverse")
    c3.metric("🟡 Medium", med)
    c4.metric("🟢 Low", low)

    severity_colors = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    display = conflicts.copy()
    display["severity"] = display["severity"].map(lambda s: f"{severity_colors.get(s, '')} {s}")
    st.dataframe(display, use_container_width=True, height=400)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        conflicts.to_excel(writer, sheet_name="Conflicts", index=False)
        df_insp.to_excel(writer, sheet_name="Inspections", index=False)
        df_perm.to_excel(writer, sheet_name="Permits", index=False)
    buf.seek(0)
    st.download_button(
        "📥 Export Conflict Report (Excel)",
        buf.getvalue(),
        f"conflict_report_{date.today()}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_hotspot_tab() -> None:
    st.subheader("🔥 Hotspot Analysis")
    st.caption("Identify geographic clusters of high-severity defects to prioritize patrol areas.")

    df = _get_inspection_df("hot_insp")
    if df.empty or "latitude" not in df.columns:
        return

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider(
            "Critical condition threshold (show locations below this score)", 10, 60, 35, key="hot_thresh"
        )
    with col2:
        if "borough" in df.columns:
            boros = sorted(df["borough"].dropna().unique().tolist())
            borough_sel = st.multiselect("Filter Borough", boros, default=boros, key="hot_boro")
        else:
            borough_sel = []

    mask = pd.Series([True] * len(df))
    if borough_sel and "borough" in df.columns:
        mask &= df["borough"].isin(borough_sel)
    if "condition_score" in df.columns:
        mask &= df["condition_score"] <= threshold

    df_critical = _flag_in_bounds(df[mask].copy()).dropna(subset=["latitude", "longitude"])

    st.markdown(f"**{len(df_critical):,} critical locations** (score ≤ {threshold})")

    if not HAS_PLOTLY:
        if not df_critical.empty:
            st.dataframe(df_critical[["latitude", "longitude", "borough"]].head(50))
        return

    if df_critical.empty:
        st.info("No critical locations with current filter settings.")
        return

    score_col = df_critical.get("condition_score") if "condition_score" in df_critical.columns else None
    z_vals = (100 - df_critical["condition_score"]) if score_col is not None else pd.Series([50] * len(df_critical))

    fig = go.Figure(go.Densitymapbox(
        lat=df_critical["latitude"],
        lon=df_critical["longitude"],
        z=z_vals,
        radius=20,
        colorscale="YlOrRd",
        showscale=True,
        colorbar_title="Severity",
    ))
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=10,
        mapbox_center={"lat": df_critical["latitude"].mean(), "lon": df_critical["longitude"].mean()},
        margin={"r": 0, "t": 10, "l": 0, "b": 0},
        height=520,
    )
    st.plotly_chart(fig, use_container_width=True)

    if "borough" in df_critical.columns:
        st.markdown("**Critical Locations by Borough**")
        agg_cols: dict = {"latitude": "count"}
        if "condition_score" in df_critical.columns:
            agg_cols["condition_score"] = "mean"
        borough_counts = df_critical.groupby("borough").agg(agg_cols).reset_index()
        borough_counts = borough_counts.rename(columns={"latitude": "count"})
        if "condition_score" in borough_counts.columns:
            borough_counts["condition_score"] = borough_counts["condition_score"].round(1)
        st.dataframe(borough_counts.sort_values("count", ascending=False), use_container_width=True, hide_index=True)


def _render_spatial_reports_tab() -> None:
    st.subheader("📊 Spatial Reports")
    df = _get_inspection_df("srep_insp")
    if df.empty:
        return

    date_range = st.date_input(
        "Date Range",
        value=(date.today() - timedelta(days=365), date.today()),
        key="srep_dates",
    )
    date_col = next(
        (c for c in df.columns if any(d in c.lower() for d in ("date", "created", "open"))), None
    )
    if len(date_range) == 2 and date_col:
        start, end = date_range
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df[df[date_col].between(str(start), str(end))]

    if df.empty:
        st.warning("No data in selected date range.")
        return

    if HAS_PLOTLY and "borough" in df.columns:
        col1, col2 = st.columns(2)
        with col1:
            boro_counts = df.groupby("borough").size().reset_index(name="count")
            fig = px.bar(boro_counts, x="borough", y="count", color="borough", title="Inspections by Borough")
            fig.update_layout(showlegend=False, height=320)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if "condition_score" in df.columns:
                boro_scores = df.groupby("borough")["condition_score"].mean().reset_index()
                fig2 = px.bar(
                    boro_scores, x="borough", y="condition_score",
                    color="condition_score", color_continuous_scale="RdYlGn",
                    title="Average Condition Score by Borough", range_color=[0, 100],
                )
                fig2.update_layout(showlegend=False, height=320)
                st.plotly_chart(fig2, use_container_width=True)

        if "defect_type" in df.columns:
            defect_counts = (
                df.groupby("defect_type").size().reset_index(name="count").sort_values("count", ascending=False)
            )
            fig3 = px.bar(defect_counts, x="defect_type", y="count", title="Defect Type Distribution")
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    if st.button("📥 Export Spatial Report (Excel)"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="All Inspections", index=False)
            if "borough" in df.columns:
                agg: dict = {"borough": "count"}
                if "condition_score" in df.columns:
                    agg["condition_score"] = "mean"
                summary = df.groupby("borough").agg(agg).rename(columns={"borough": "total_locations"}).reset_index()
                summary.to_excel(writer, sheet_name="Borough Summary", index=False)
        buf.seek(0)
        st.download_button(
            "Download Report",
            buf.getvalue(),
            f"spatial_report_{date.today()}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _render_hiqa_capital_tab() -> None:
    st.subheader("🚧 HIQA Street Construction Inspections & Capital Projects")
    st.caption(
        "Highway Inspection & Quality Assurance (HIQA) inspections of permit compliance on city streets. "
        "Capital Reconstruction Projects — intersection-level spatial data."
    )

    sub_hiqa, sub_cap = st.tabs(["🔍 HIQA Inspections", "🏗️ Capital Intersections"])

    with sub_hiqa:
        hiqa_limit = st.number_input("Row limit", 1_000, 50_000, 10_000, step=1_000, key="hiqa_lim")
        df_hiqa = _load_street_construction_inspections(int(hiqa_limit))
        if df_hiqa.empty:
            st.info("No HIQA data loaded. Configure SOCRATA_APP_TOKEN in Settings.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total inspections", f"{len(df_hiqa):,}")
            if "inspectionresulttype" in df_hiqa.columns:
                vio = df_hiqa["inspectionresulttype"].str.upper().str.contains("FAIL|VIOL|NOV", na=False).sum()
                c2.metric("Violations / NOV", int(vio))
            if "novnumber" in df_hiqa.columns:
                c3.metric("NOV numbers issued", int(df_hiqa["novnumber"].notna().sum()))

            if "inspectiontype" in df_hiqa.columns:
                type_filter = st.multiselect(
                    "Inspection type",
                    df_hiqa["inspectiontype"].dropna().unique().tolist(),
                    key="hiqa_type",
                )
                if type_filter:
                    df_hiqa = df_hiqa[df_hiqa["inspectiontype"].isin(type_filter)]

            show_cols = [c for c in (
                "inspectiondate", "permitnumber", "permitteename", "onstreetname",
                "fromstreetname", "tostreetname", "inspectiontype", "inspectionresulttype",
                "novnumber", "novcodedescription", "defectivecuts",
            ) if c in df_hiqa.columns]
            st.dataframe(df_hiqa[show_cols] if show_cols else df_hiqa,
                         use_container_width=True, hide_index=True)
            st.download_button("⬇ Export (CSV)", df_hiqa.to_csv(index=False).encode(),
                               "hiqa_inspections.csv", mime="text/csv")

            if HAS_PLOTLY and "inspectionresulttype" in df_hiqa.columns:
                result_counts = df_hiqa["inspectionresulttype"].value_counts().head(10).reset_index()
                result_counts.columns = ["result", "count"]
                fig = px.bar(result_counts, x="count", y="result", orientation="h",
                             title="HIQA inspection results (top 10)")
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)

    with sub_cap:
        cap_limit = st.number_input("Row limit", 500, 20_000, 5_000, step=500, key="cap_lim")
        df_cap = _load_capital_intersections(int(cap_limit))
        if df_cap.empty:
            st.info("No capital intersection data loaded. Configure SOCRATA_APP_TOKEN in Settings.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total projects", f"{len(df_cap):,}")
            if "projectsta" in df_cap.columns:
                active = df_cap["projectsta"].str.upper().str.contains("ACTIVE|CONSTRUCT|DESIGN", na=False).sum()
                c2.metric("Active/In progress", int(active))
            if "projectcost" in df_cap.columns:
                df_cap["projectcost"] = pd.to_numeric(df_cap["projectcost"], errors="coerce")
                c3.metric("Total project cost", f"${df_cap['projectcost'].sum():,.0f}")

            if "boroughnam" in df_cap.columns:
                boro_sel = st.multiselect("Borough filter", df_cap["boroughnam"].dropna().unique().tolist(), key="cap_boro")
                if boro_sel:
                    df_cap = df_cap[df_cap["boroughnam"].isin(boro_sel)]

            show_cols = [c for c in (
                "projtitle", "boroughnam", "onstreetname", "fromstreet", "tostreetna",
                "projectsta", "designstar", "construc_2", "projectcost", "leadagency",
            ) if c in df_cap.columns]
            st.dataframe(df_cap[show_cols] if show_cols else df_cap,
                         use_container_width=True, hide_index=True)
            st.download_button("⬇ Export (CSV)", df_cap.to_csv(index=False).encode(),
                               "capital_intersections.csv", mime="text/csv")

            if HAS_PLOTLY and "projectsta" in df_cap.columns:
                status_counts = df_cap["projectsta"].value_counts().reset_index()
                status_counts.columns = ["status", "count"]
                fig = px.pie(status_counts, names="status", values="count",
                             title="Capital projects by status", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
