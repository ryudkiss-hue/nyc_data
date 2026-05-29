"""Spatial analytics tab for Manhattan Mission Control."""

from __future__ import annotations

import logging

import pandas as pd

try:
    import folium
    _HAS_FOLIUM = True
except ImportError:
    folium = None  # type: ignore[assignment]
    _HAS_FOLIUM = False
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

log = logging.getLogger(__name__)

BOROUGH_COORDS: dict[str, list[float]] = {
    "MANHATTAN": [40.7831, -73.9712],
    "BROOKLYN": [40.6782, -73.9442],
    "QUEENS": [40.7282, -73.7949],
    "BRONX": [40.8448, -73.8648],
    "STATEN ISLAND": [40.5795, -74.1502],
}
NYC_CENTER = [40.7128, -74.0060]

_LAT_COLS = ("latitude", "lat", "y", "ycoord", "y_coordinate")
_LON_COLS = ("longitude", "lon", "lng", "x", "xcoord", "x_coordinate")


def _pick(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in low:
            return low[c]
    return None


def _to_numeric_coords(df: pd.DataFrame) -> pd.DataFrame:
    lat_col = _pick(df, _LAT_COLS)
    lon_col = _pick(df, _LON_COLS)
    if lat_col and lon_col:
        df = df.copy()
        df["_lat"] = pd.to_numeric(df[lat_col], errors="coerce")
        df["_lon"] = pd.to_numeric(df[lon_col], errors="coerce")
        df = df.dropna(subset=["_lat", "_lon"])
        df = df[(df["_lat"].between(40.4, 40.95)) & (df["_lon"].between(-74.3, -73.6))]
    return df


def _borough_from_location(loc_str: str) -> str:
    loc_upper = str(loc_str).upper()
    for b in BOROUGH_COORDS:
        if b in loc_upper:
            return b
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _borough_bar(df: pd.DataFrame, label: str) -> go.Figure | None:
    """Bar chart of record counts by borough."""
    borough_col = _pick(df, ("borough", "boro", "borough_name"))
    if not borough_col:
        return None
    counts = (
        df[borough_col]
        .str.upper()
        .value_counts()
        .reset_index()
    )
    counts.columns = ["Borough", "Count"]
    fig = go.Figure(go.Bar(
        x=counts["Borough"],
        y=counts["Count"],
        marker_color="#3B82F6",
        hovertemplate="%{x}: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Borough",
        yaxis_title="Records",
    )
    return fig


def _density_heatmap(df: pd.DataFrame, label: str) -> go.Figure | None:
    """KDE-style density scatter using lat/lon."""
    df2 = _to_numeric_coords(df)
    if "_lat" not in df2.columns or df2.empty:
        return None
    sample = df2.sample(min(len(df2), 2000), random_state=42)
    fig = go.Figure(go.Scattermapbox(
        lat=sample["_lat"],
        lon=sample["_lon"],
        mode="markers",
        marker=dict(size=5, color="#3B82F6", opacity=0.5),
        hovertemplate="(%{lat:.4f}, %{lon:.4f})<extra></extra>",
        name=label,
    ))
    fig.update_layout(
        mapbox=dict(style="carto-darkmatter", center=dict(lat=40.71, lon=-74.0), zoom=10),
        height=420,
        margin=dict(l=0, r=0, t=0, b=0),
        template="plotly_dark",
    )
    return fig


def _folium_bubble_map(
    df: pd.DataFrame,
    location_col: str,
    count_col: str,
    label: str,
) -> str:
    """Folium bubble map grouped by location text → borough geocode."""
    m = folium.Map(location=NYC_CENTER, zoom_start=10, tiles="CartoDB dark_matter")
    for _, row in df.iterrows():
        borough = _borough_from_location(str(row[location_col]))
        base = BOROUGH_COORDS.get(borough, NYC_CENTER)
        h = hash(str(row[location_col]))
        lat = base[0] + (h % 200 - 100) / 8000
        lon = base[1] + ((h >> 8) % 200 - 100) / 8000
        radius = min(max(int(row[count_col]) * 2, 5), 25)
        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            popup=folium.Popup(
                f"<b>{row[location_col]}</b><br>{label}: {row[count_col]:,}",
                max_width=240,
            ),
            tooltip=f"{row[location_col]} ({row[count_col]:,})",
            color="#3B82F6",
            fill=True,
            fill_color="#3B82F6",
            fill_opacity=0.65,
        ).add_to(m)
    return m._repr_html_()


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def _detect_spatial_conflicts(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    label_a: str,
    label_b: str,
) -> pd.DataFrame:
    """Naive overlap detector: match on borough and week for text-location datasets."""
    borough_col_a = _pick(df_a, ("borough", "boro"))
    borough_col_b = _pick(df_b, ("borough", "boro"))
    if not (borough_col_a and borough_col_b):
        return pd.DataFrame()

    agg_a = df_a[borough_col_a].str.upper().value_counts().rename("count_a")
    agg_b = df_b[borough_col_b].str.upper().value_counts().rename("count_b")
    merged = pd.concat([agg_a, agg_b], axis=1).dropna()
    if merged.empty:
        return pd.DataFrame()
    merged["potential_conflict"] = (merged["count_a"] > 0) & (merged["count_b"] > 0)
    merged = merged[merged["potential_conflict"]].reset_index()
    merged.columns = ["Borough", f"{label_a} records", f"{label_b} records", "Conflict"]
    return merged[["Borough", f"{label_a} records", f"{label_b} records"]]


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_spatial_tab(loaded_frames: dict[str, pd.DataFrame]) -> None:
    """Render the Spatial Analytics tab."""
    st.markdown("### 🗺️ Spatial Analytics")
    st.caption(
        "Geospatial distribution, density hotspots, and construction conflict detection "
        "across all loaded NYC datasets."
    )

    if not loaded_frames:
        st.info(
            "No datasets loaded yet. Load data from the Home tab or run the Apex Pipeline "
            "to populate spatial views.",
            icon="🗺️",
        )
        return

    # Filter to datasets with useful location data
    geo_datasets: dict[str, pd.DataFrame] = {}
    text_location_datasets: dict[str, pd.DataFrame] = {}
    for key, df in loaded_frames.items():
        if df.empty:
            continue
        if _pick(df, _LAT_COLS) and _pick(df, _LON_COLS):
            geo_datasets[key] = df
        elif _pick(df, ("work_location", "borough", "location", "address")):
            text_location_datasets[key] = df

    # ── Summary metrics ────────────────────────────────────────────────────
    total_points = sum(
        len(_to_numeric_coords(df)) for df in geo_datasets.values()
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Geo-referenced datasets", len(geo_datasets))
    c2.metric("Total spatial records", f"{total_points:,}")
    c3.metric("Text-location datasets", len(text_location_datasets))
    st.divider()

    # ── Borough distribution ───────────────────────────────────────────────
    st.subheader("Borough Distribution")
    borough_tabs = st.tabs(list(loaded_frames.keys())[:6])
    for tab, (key, df) in zip(borough_tabs, list(loaded_frames.items())[:6], strict=False):
        with tab:
            fig = _borough_bar(df, key)
            if fig:
                st.plotly_chart(fig, width="stretch")
            else:
                st.caption(f"No borough column detected in `{key}`.")

    # ── Point density map ──────────────────────────────────────────────────
    if geo_datasets:
        st.divider()
        st.subheader("Point Density Map")
        selected_geo = st.selectbox(
            "Dataset", list(geo_datasets.keys()), key="spatial_geo_select"
        )
        df_geo = geo_datasets[selected_geo]
        fig_map = _density_heatmap(df_geo, selected_geo)
        if fig_map:
            st.plotly_chart(fig_map, width="stretch")
            df_coords = _to_numeric_coords(df_geo)
            st.caption(
                f"{len(df_coords):,} geocoded records plotted "
                f"(sampled to 2,000 for rendering speed)."
            )

    # ── Text-location bubble map ──────────────────────────────────────────
    if text_location_datasets:
        st.divider()
        st.subheader("Location Density Bubbles")
        selected_text = st.selectbox(
            "Dataset", list(text_location_datasets.keys()), key="spatial_text_select"
        )
        df_text = text_location_datasets[selected_text]
        loc_col = _pick(df_text, ("work_location", "location", "address", "borough")) or ""
        if loc_col:
            counts = (
                df_text[loc_col]
                .value_counts()
                .reset_index()
                .head(30)
            )
            counts.columns = ["Location", "Count"]
            if _HAS_FOLIUM:
                html = _folium_bubble_map(counts, "Location", "Count", selected_text)
                components.html(html, height=460)
            else:
                st.caption("Install `folium` for interactive bubble maps.")
                st.dataframe(counts, width="stretch", hide_index=True)

    # ── Conflict detection ────────────────────────────────────────────────
    keys = list(loaded_frames.keys())
    if len(keys) >= 2:
        st.divider()
        st.subheader("🚧 Spatial Conflict Detection")
        st.caption(
            "Detects datasets with overlapping borough+date footprints — "
            "potential scheduling conflicts."
        )
        col_a, col_b = st.columns(2)
        ds_a = col_a.selectbox("Dataset A", keys, index=0, key="conflict_a")
        ds_b = col_b.selectbox("Dataset B", keys, index=min(1, len(keys) - 1), key="conflict_b")
        if ds_a != ds_b:
            conflicts = _detect_spatial_conflicts(
                loaded_frames[ds_a], loaded_frames[ds_b], ds_a, ds_b
            )
            if conflicts.empty:
                st.success("No shared boroughs detected between selected datasets.")
            else:
                st.warning(
                    f"⚠️  {len(conflicts)} borough(s) have records in both datasets — "
                    "potential scheduling overlap.",
                    icon="⚠️",
                )
                st.dataframe(conflicts, width="stretch", hide_index=True)

    # ── Coordinate export ─────────────────────────────────────────────────
    if geo_datasets:
        st.divider()
        st.subheader("📥 Export Geocoded Data")
        export_ds = st.selectbox(
            "Dataset to export", list(geo_datasets.keys()), key="spatial_export_select"
        )
        df_export = _to_numeric_coords(geo_datasets[export_ds])
        if not df_export.empty:
            csv = df_export.to_csv(index=False)
            st.download_button(
                "Download geocoded CSV",
                csv,
                file_name=f"mmc_{export_ds}_geocoded.csv",
                mime="text/csv",
                width="stretch",
            )
