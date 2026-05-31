"""GIS & Spatial Analysis dashboard for NYC DOT SIM Program."""

from __future__ import annotations

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

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

try:
    from shapely.geometry import Point  # type: ignore[import]
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

NYC_BOUNDS = {"lat_min": 40.477, "lat_max": 40.917, "lon_min": -74.259, "lon_max": -73.700}
BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
BOROUGH_CENTERS = {
    "Manhattan":    (40.7831, -73.9712),
    "Brooklyn":     (40.6782, -73.9442),
    "Queens":       (40.7282, -73.7949),
    "Bronx":        (40.8448, -73.8648),
    "Staten Island": (40.5795, -74.1502),
}


def _demo_inspections(n: int = 200) -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(42)
    boros = rng.choice(BOROUGHS, n)
    base_lats = [BOROUGH_CENTERS[b][0] for b in boros]
    base_lons = [BOROUGH_CENTERS[b][1] for b in boros]
    return pd.DataFrame({
        "block_id": [f"B{i:05d}" for i in range(n)],
        "borough": boros,
        "latitude": rng.normal(base_lats, 0.015),
        "longitude": rng.normal(base_lons, 0.015),
        "condition_score": rng.integers(10, 100, n),
        "defect_type": rng.choice(["Raised Flag", "Sunken Flag", "Missing Flag", "Cracked Flag", "Tree Damage"], n),
        "area_sqft": rng.integers(20, 500, n),
        "priority_score": rng.uniform(0, 100, n).round(1),
        "inspection_date": pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D"),
        "contract_id": rng.choice(["C-2025-001", "C-2025-002", "C-2025-003", None], n),
    })


def _demo_permits(n: int = 40) -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(7)
    boros = rng.choice(BOROUGHS, n)
    starts = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 300, n), unit="D")
    return pd.DataFrame({
        "permit_id": [f"P{i:04d}" for i in range(n)],
        "block_id": [f"B{i:05d}" for i in rng.integers(0, 200, n)],
        "borough": boros,
        "permit_type": rng.choice(["Street Opening", "Utility Work", "Building Construction", "DOT Capital"], n),
        "applicant": rng.choice(["ConEd", "National Grid", "Verizon", "DEP", "DDC"], n),
        "start_date": starts,
        "end_date": starts + pd.to_timedelta(rng.integers(30, 365, n), unit="D"),
        "latitude": [BOROUGH_CENTERS[b][0] + rng.normal(0, 0.015) for b in boros],
        "longitude": [BOROUGH_CENTERS[b][1] + rng.normal(0, 0.015) for b in boros],
    })


def _flag_in_bounds(df: pd.DataFrame) -> pd.DataFrame:
    mask = (
        df["latitude"].between(NYC_BOUNDS["lat_min"], NYC_BOUNDS["lat_max"])
        & df["longitude"].between(NYC_BOUNDS["lon_min"], NYC_BOUNDS["lon_max"])
    )
    return df[mask].copy()


def _detect_spatial_conflicts(inspections: pd.DataFrame, permits: pd.DataFrame) -> pd.DataFrame:
    if inspections.empty or permits.empty:
        return pd.DataFrame()
    common_blocks = set(inspections["block_id"]) & set(permits["block_id"])
    if not common_blocks:
        return pd.DataFrame()

    conflicts = []
    insp_by_block = inspections[inspections["block_id"].isin(common_blocks)].set_index("block_id")
    perm_by_block = permits[permits["block_id"].isin(common_blocks)]

    today = pd.Timestamp.today()
    for _, permit in perm_by_block.iterrows():
        bid = permit["block_id"]
        if bid not in insp_by_block.index:
            continue
        insp_rows = insp_by_block.loc[[bid]]
        for _, insp in insp_rows.iterrows():
            days_gap = abs((today - pd.Timestamp(insp.get("inspection_date", today))).days)
            if days_gap <= 30:
                severity = "HIGH"
            elif days_gap <= 90:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            conflicts.append({
                "block_id": bid,
                "borough": insp.get("borough", ""),
                "permit_id": permit.get("permit_id", ""),
                "permit_type": permit.get("permit_type", ""),
                "applicant": permit.get("applicant", ""),
                "condition_score": insp.get("condition_score", ""),
                "severity": severity,
                "inspection_date": insp.get("inspection_date", ""),
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

    df_valid = _flag_in_bounds(df)
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

        popup_lines = [f"<b>{row.get('block_id', '')}</b>"]
        for col in ("borough", "defect_type", "condition_score", "area_sqft", "priority_score"):
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
    df_valid = _flag_in_bounds(df)
    if df_valid.empty:
        st.warning("No points within NYC bounds.")
        return

    color_col = "condition_score" if "condition_score" in df_valid.columns else None
    hover_cols = [c for c in ("block_id", "borough", "defect_type", "area_sqft", "priority_score") if c in df_valid.columns]

    fig = px.scatter_mapbox(
        df_valid,
        lat="latitude",
        lon="longitude",
        color=color_col,
        color_continuous_scale="RdYlGn",
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

    tab1, tab2, tab3, tab4 = st.tabs([
        "📍 Inspection Map",
        "⚠️ Conflict Detection",
        "🔥 Hotspot Analysis",
        "📊 Spatial Reports",
    ])

    with tab1:
        _render_inspection_map_tab()
    with tab2:
        _render_conflict_detection_tab()
    with tab3:
        _render_hotspot_tab()
    with tab4:
        _render_spatial_reports_tab()


def _render_inspection_map_tab() -> None:
    st.subheader("Inspection Locations")

    use_demo = st.checkbox("Use demo data", value=True, key="gis_demo")
    if use_demo:
        df = _demo_inspections()
        st.caption(f"Demo dataset: {len(df):,} inspection records")
    else:
        uploaded = st.file_uploader("Upload inspections CSV (must have latitude, longitude columns)", type="csv", key="gis_upload")
        if uploaded is None:
            st.info("Upload a CSV to begin, or enable demo data above.")
            return
        df = pd.read_csv(uploaded)

    required = {"latitude", "longitude"}
    if not required.issubset(df.columns):
        st.error(f"Missing required columns: {required - set(df.columns)}")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        borough_filter = st.multiselect("Borough", BOROUGHS, default=BOROUGHS, key="gis_boro")
    with col2:
        if "condition_score" in df.columns:
            score_range = st.slider("Condition Score", 0, 100, (0, 100), key="gis_score")
        else:
            score_range = (0, 100)
    with col3:
        if "defect_type" in df.columns:
            defect_filter = st.multiselect("Defect Type", sorted(df["defect_type"].dropna().unique()), key="gis_defect")
        else:
            defect_filter = []

    mask = pd.Series([True] * len(df))
    if "borough" in df.columns and borough_filter:
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
    if "area_sqft" in df_filtered.columns and not df_filtered.empty:
        c4.metric("Total Area (sqft)", f"{df_filtered['area_sqft'].sum():,.0f}")

    map_engine = st.radio("Map engine", ["Plotly (recommended)", "Folium (interactive)"], horizontal=True, key="gis_engine")

    if map_engine.startswith("Plotly"):
        _render_plotly_map(df_filtered)
    else:
        _render_folium_map(df_filtered)

    with st.expander("Data Table"):
        st.dataframe(df_filtered, use_container_width=True, height=300)
        csv = df_filtered.to_csv(index=False).encode()
        st.download_button("Download filtered CSV", csv, "inspections_filtered.csv", "text/csv")


def _render_conflict_detection_tab() -> None:
    st.subheader("⚠️ Conflict Detection")
    st.caption("Identify inspection locations that overlap with active permits or capital projects.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Inspection Data**")
        use_demo_insp = st.checkbox("Demo inspections", value=True, key="conf_demo_insp")
        if use_demo_insp:
            df_insp = _demo_inspections()
        else:
            up = st.file_uploader("Upload inspections CSV", type="csv", key="conf_insp_up")
            df_insp = pd.read_csv(up) if up else pd.DataFrame()

    with col2:
        st.markdown("**Permits / Contracts**")
        use_demo_perm = st.checkbox("Demo permits", value=True, key="conf_demo_perm")
        if use_demo_perm:
            df_perm = _demo_permits()
        else:
            up2 = st.file_uploader("Upload permits CSV", type="csv", key="conf_perm_up")
            df_perm = pd.read_csv(up2) if up2 else pd.DataFrame()

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

    use_demo = st.checkbox("Use demo data", value=True, key="hot_demo")
    df = _demo_inspections(400) if use_demo else pd.DataFrame()

    if not use_demo:
        up = st.file_uploader("Upload CSV with latitude, longitude, condition_score", type="csv", key="hot_up")
        if up:
            df = pd.read_csv(up)

    if df.empty or "latitude" not in df.columns:
        st.info("Load data to generate hotspot analysis.")
        return

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider("Critical condition threshold (show locations below this score)", 10, 60, 35, key="hot_thresh")
    with col2:
        borough_sel = st.multiselect("Filter Borough", BOROUGHS, default=BOROUGHS, key="hot_boro")

    mask = pd.Series([True] * len(df))
    if "borough" in df.columns and borough_sel:
        mask &= df["borough"].isin(borough_sel)
    if "condition_score" in df.columns:
        mask &= df["condition_score"] <= threshold

    df_critical = _flag_in_bounds(df[mask].copy())

    st.markdown(f"**{len(df_critical):,} critical locations** (score ≤ {threshold})")

    if not HAS_PLOTLY:
        st.info("Install plotly for hotspot visualization.")
        if not df_critical.empty:
            st.dataframe(df_critical[["block_id", "borough", "latitude", "longitude", "condition_score"]].head(50))
        return

    if df_critical.empty:
        st.info("No critical locations with current filter settings.")
        return

    fig = go.Figure(go.Densitymapbox(
        lat=df_critical["latitude"],
        lon=df_critical["longitude"],
        z=100 - df_critical.get("condition_score", pd.Series([50] * len(df_critical))),
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
        borough_counts = df_critical.groupby("borough").agg(
            count=("block_id", "count"),
            avg_score=("condition_score", "mean"),
            total_sqft=("area_sqft", "sum"),
        ).reset_index().sort_values("count", ascending=False)
        st.dataframe(borough_counts, use_container_width=True, hide_index=True)


def _render_spatial_reports_tab() -> None:
    st.subheader("📊 Spatial Reports")

    use_demo = st.checkbox("Use demo data", value=True, key="srep_demo")
    df = _demo_inspections(300) if use_demo else pd.DataFrame()

    if not use_demo:
        up = st.file_uploader("Upload inspections CSV", type="csv", key="srep_up")
        if up:
            df = pd.read_csv(up)

    if df.empty:
        st.info("Load data to generate reports.")
        return

    date_range = st.date_input(
        "Date Range",
        value=(date.today() - timedelta(days=365), date.today()),
        key="srep_dates",
    )
    if len(date_range) == 2:
        start, end = date_range
        if "inspection_date" in df.columns:
            df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")
            df = df[df["inspection_date"].between(str(start), str(end))]

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
                fig2 = px.bar(boro_scores, x="borough", y="condition_score",
                              color="condition_score", color_continuous_scale="RdYlGn",
                              title="Average Condition Score by Borough", range_color=[0, 100])
                fig2.update_layout(showlegend=False, height=320)
                st.plotly_chart(fig2, use_container_width=True)

        if "defect_type" in df.columns:
            defect_counts = df.groupby("defect_type").size().reset_index(name="count").sort_values("count", ascending=False)
            fig3 = px.bar(defect_counts, x="defect_type", y="count", title="Defect Type Distribution")
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    st.markdown("**Generate Full Spatial Report**")
    if st.button("📥 Export Spatial Report (Excel)"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="All Inspections", index=False)
            if "borough" in df.columns:
                summary = df.groupby("borough").agg(
                    total_locations=("block_id", "count"),
                    avg_condition_score=("condition_score", "mean"),
                    total_sqft=("area_sqft", "sum"),
                    critical_locations=("condition_score", lambda x: (x < 35).sum()),
                ).round(1).reset_index()
                summary.to_excel(writer, sheet_name="Borough Summary", index=False)
            if "defect_type" in df.columns:
                defect_summary = df.groupby(["borough", "defect_type"]).size().reset_index(name="count")
                defect_summary.to_excel(writer, sheet_name="Defect Breakdown", index=False)
        buf.seek(0)
        st.download_button(
            "Download Report",
            buf.getvalue(),
            f"spatial_report_{date.today()}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
