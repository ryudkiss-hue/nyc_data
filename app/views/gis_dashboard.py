"""GIS & Spatial Analysis dashboard for NYC DOT SIM Program."""

from __future__ import annotations

import io
import json
import math
import os
import tempfile
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
from socrata_toolkit.core.utils import BOROUGH_LIST

try:
    import folium
    from folium import plugins as folium_plugins
    from streamlit_folium import st_folium  # type: ignore[import]
    HAS_FOLIUM = True
except ImportError:
    folium_plugins = None
    HAS_FOLIUM = False

try:
    import plotly.express as px
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import geopandas as gpd

    HAS_GEOPANDAS = True
except ImportError:
    gpd = None
    HAS_GEOPANDAS = False

try:
    import pydeck as pdk

    HAS_PYDECK = True
except ImportError:
    pdk = None
    HAS_PYDECK = False

try:
    import numpy as np
    from sklearn.cluster import DBSCAN

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from scipy.spatial import KDTree
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

NYC_BOUNDS = {"lat_min": 40.477, "lat_max": 40.917, "lon_min": -74.259, "lon_max": -73.700}
BOROUGHS = BOROUGH_LIST


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Cached data loaders
# ---------------------------------------------------------------------------

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


@st.cache_data(ttl=86_400, show_spinner="Loading permit stipulations…")
def _load_permit_stipulations(limit: int = 10_000) -> pd.DataFrame:
    try:
        return fetch_dataset("permit_stipulations", limit=limit)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86_400, show_spinner="Loading street closures (block level)…")
def _load_street_closures(limit: int = 10_000) -> pd.DataFrame:
    try:
        df = fetch_dataset("street_closures_block", limit=limit)
        lat_col = pick_column(df, LAT_CANDIDATES)
        lon_col = pick_column(df, LON_CANDIDATES)
        if lat_col and lat_col != "latitude":
            df = df.rename(columns={lat_col: "latitude"})
        if lon_col and lon_col != "longitude":
            df = df.rename(columns={lon_col: "longitude"})
        for col in ("latitude", "longitude"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86_400, show_spinner="Loading step streets…")
def _load_step_streets(limit: int = 5_000) -> pd.DataFrame:
    try:
        df = fetch_dataset("u9au-h79y", limit=limit)
        lat_col = pick_column(df, LAT_CANDIDATES)
        lon_col = pick_column(df, LON_CANDIDATES)
        if lat_col and lat_col != "latitude":
            df = df.rename(columns={lat_col: "latitude"})
        if lon_col and lon_col != "longitude":
            df = df.rename(columns={lon_col: "longitude"})
        for col in ("latitude", "longitude"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _flag_in_bounds(df: pd.DataFrame) -> pd.DataFrame:
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return df
    mask = (
        df["latitude"].between(NYC_BOUNDS["lat_min"], NYC_BOUNDS["lat_max"])
        & df["longitude"].between(NYC_BOUNDS["lon_min"], NYC_BOUNDS["lon_max"])
    )
    return df[mask].copy()


def _df_to_geojson(df: pd.DataFrame) -> str:
    """Build a simple Point FeatureCollection from latitude/longitude columns."""
    features = []
    for _, row in df.iterrows():
        if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            feat = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": row.drop(["latitude", "longitude"]).to_dict(),
            }
            features.append(feat)
    return json.dumps({"type": "FeatureCollection", "features": features})


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two WGS84 points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_neighbor_route(coords: list[tuple]) -> list[int]:
    """Greedy nearest-neighbour TSP heuristic.

    Args:
        coords: List of (lat, lon) tuples.

    Returns:
        Ordered list of indices representing the visit sequence.
    """
    n = len(coords)
    if n == 0:
        return []
    unvisited = set(range(1, n))
    route = [0]
    current = 0
    while unvisited:
        nearest = min(
            unvisited,
            key=lambda j: _haversine_km(coords[current][0], coords[current][1],
                                        coords[j][0], coords[j][1]),
        )
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest
    return route


# ---------------------------------------------------------------------------
# Conflict detection (attribute-based fallback)
# ---------------------------------------------------------------------------

def _detect_spatial_conflicts(inspections: pd.DataFrame, permits: pd.DataFrame) -> pd.DataFrame:
    if inspections.empty or permits.empty:
        return pd.DataFrame()

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
                "insp_lat": insp_row.get("latitude"),
                "insp_lon": insp_row.get("longitude"),
                "perm_lat": permit.get("latitude"),
                "perm_lon": permit.get("longitude"),
            })

    if not conflicts:
        return pd.DataFrame()
    df = pd.DataFrame(conflicts)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    df["_sort"] = df["severity"].map(order)
    return df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)


# EPSG:2263 = NY State Plane (Long Island), feet. Used for metric distance ops.
NY_STATE_PLANE = "EPSG:2263"
M_TO_FT = 3.280839895


def _detect_conflicts_geopandas(
    inspections: pd.DataFrame,
    permits: pd.DataFrame,
    radius_m: float,
) -> pd.DataFrame:
    """Flag permits within ``radius_m`` of an inspection using GeoPandas (Items 13, 14).

    Reprojects both datasets to EPSG:2263 (NY State Plane, feet) and uses
    ``gpd.sjoin_nearest`` with ``max_distance`` to replace the manual haversine
    point-distance approximation. Returns one row per inspection∩permit match,
    sorted by distance.

    Args:
        inspections: Inspection DataFrame with latitude/longitude columns.
        permits: Permit DataFrame with latitude/longitude columns.
        radius_m: Buffer radius in meters (conflict threshold).

    Returns:
        DataFrame of conflict pairs with a ``dist_m`` distance column, or an
        empty DataFrame if GeoPandas is unavailable or no coordinates exist.
    """
    if not HAS_GEOPANDAS:
        return pd.DataFrame()

    insp = inspections.dropna(subset=["latitude", "longitude"]).copy()
    perm = permits.dropna(subset=["latitude", "longitude"]).copy()
    if insp.empty or perm.empty:
        return pd.DataFrame()

    insp_keep = [c for c in ("borough", "street_name", "block_id", "condition_score",
                             "inspection_date", "inspectiondate") if c in insp.columns]
    perm_keep = [c for c in ("permit_id", "permit_type", "applicant", "start_date",
                             "end_date") if c in perm.columns]

    insp_gdf = gpd.GeoDataFrame(
        insp[insp_keep + ["latitude", "longitude"]],
        geometry=gpd.points_from_xy(insp["longitude"], insp["latitude"]),
        crs="EPSG:4326",
    ).to_crs(NY_STATE_PLANE)
    perm_gdf = gpd.GeoDataFrame(
        perm[perm_keep + ["latitude", "longitude"]].rename(
            columns={"latitude": "perm_lat", "longitude": "perm_lon"}
        ),
        geometry=gpd.points_from_xy(perm["longitude"], perm["latitude"]),
        crs="EPSG:4326",
    ).to_crs(NY_STATE_PLANE)

    # Distance threshold expressed in feet (the unit of EPSG:2263)
    max_distance_ft = radius_m * M_TO_FT

    joined = gpd.sjoin_nearest(
        insp_gdf,
        perm_gdf,
        how="left",
        max_distance=max_distance_ft,
        distance_col="dist_ft",
    )
    # Keep only inspections that actually matched a permit within range
    joined = joined[joined["index_right"].notna()].copy()
    if joined.empty:
        return pd.DataFrame()

    joined["dist_m"] = joined["dist_ft"] / M_TO_FT

    def _severity(d: float) -> str:
        if d <= radius_m / 3:
            return "HIGH"
        if d <= 2 * radius_m / 3:
            return "MEDIUM"
        return "LOW"

    joined["severity"] = joined["dist_m"].map(_severity)

    out_cols = [
        c for c in (
            "borough", "street_name", "block_id", "condition_score",
            "permit_id", "permit_type", "applicant", "severity", "dist_m",
            "inspection_date", "start_date", "end_date",
            "latitude", "longitude", "perm_lat", "perm_lon",
        )
        if c in joined.columns
    ]
    result = joined[out_cols].rename(
        columns={"latitude": "insp_lat", "longitude": "insp_lon"}
    )
    result["dist_m"] = result["dist_m"].round(1)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    result = result.sort_values(
        ["severity", "dist_m"], key=lambda s: s.map(order) if s.name == "severity" else s
    )
    return result.reset_index(drop=True)


def _base_folium_map(center_lat: float, center_lon: float, zoom_start: int = 11) -> folium.Map:
    """Create a CartoDB-positron Folium map with MiniMap, Fullscreen, and Draw controls.

    Shared by every Folium map in this dashboard so government-report basemaps
    are consistent and every map gets an overview inset, a fullscreen toggle,
    and an ad-hoc study-area drawing tool (Items 9, 10, 11).
    """
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="CartoDB positron",
    )
    # Item 9 — overview inset
    folium_plugins.MiniMap(toggle_display=True, position="bottomright").add_to(m)
    # Item 11 — fullscreen button
    folium_plugins.Fullscreen(position="topleft").add_to(m)
    # Item 10 — ad-hoc polygon / circle / rectangle study-area selection (exportable)
    folium_plugins.Draw(
        export=True,
        position="topleft",
        draw_options={"polyline": False, "marker": False, "circlemarker": False},
    ).add_to(m)
    return m


def _render_folium_map(
    df: pd.DataFrame,
    color_col: str = "condition_score",
    permits: pd.DataFrame | None = None,
) -> None:
    """Interactive Folium inspection map.

    Uses FastMarkerCluster for inspection points (Item 7) to stay responsive on
    10k+ points, adds a HeatMap density overlay (Item 8), a MiniMap/Fullscreen/
    Draw control set (Items 9-11), optional permit and violation FeatureGroups
    toggled via LayerControl (Item 12), and the CartoDB-positron basemap.
    """
    if not HAS_FOLIUM:
        st.info(
            "Install folium and streamlit-folium for interactive maps: "
            "`pip install folium streamlit-folium`"
        )
        return

    df_valid = _flag_in_bounds(df).dropna(subset=["latitude", "longitude"])
    if df_valid.empty:
        st.warning("No points within NYC bounds.")
        return

    center_lat = df_valid["latitude"].mean()
    center_lon = df_valid["longitude"].mean()
    m = _base_folium_map(center_lat, center_lon)

    # --- Inspections layer (FastMarkerCluster — Item 7) ---
    insp_group = folium.FeatureGroup(name="Inspections", show=True)
    insp_coords = df_valid[["latitude", "longitude"]].to_numpy().tolist()
    folium_plugins.FastMarkerCluster(data=insp_coords).add_to(insp_group)
    insp_group.add_to(m)

    # --- Inspection density heatmap (Item 8) ---
    heat_group = folium.FeatureGroup(name="Inspection Density (heatmap)", show=False)
    if color_col in df_valid.columns:
        # Weight by severity (worse condition = higher weight) when available
        weights = df_valid[color_col].apply(
            lambda v: max(0.0, (100 - float(v)) / 100.0) if pd.notna(v) else 0.5
        )
        heat_data = [
            [lat, lon, w]
            for lat, lon, w in zip(
                df_valid["latitude"], df_valid["longitude"], weights
            )
        ]
    else:
        heat_data = insp_coords
    folium_plugins.HeatMap(heat_data, radius=20, blur=15, max_zoom=13).add_to(heat_group)
    heat_group.add_to(m)

    # --- Optional permits layer (Item 12 — toggle via LayerControl) ---
    if permits is not None and not permits.empty:
        perm_valid = _flag_in_bounds(permits).dropna(subset=["latitude", "longitude"])
        if not perm_valid.empty:
            perm_group = folium.FeatureGroup(name="Permits", show=False)
            for _, prow in perm_valid.iterrows():
                popup_lines = [f"<b>{prow.get('permit_id', prow.get('permit_type', 'Permit'))}</b>"]
                for col in ("borough", "permit_type", "applicant", "start_date", "end_date"):
                    if col in prow and pd.notna(prow[col]):
                        popup_lines.append(f"{col}: {prow[col]}")
                folium.CircleMarker(
                    location=[prow["latitude"], prow["longitude"]],
                    radius=4,
                    color="#1f77b4",
                    fill=True,
                    fill_opacity=0.7,
                    popup=folium.Popup("<br>".join(popup_lines), max_width=220),
                ).add_to(perm_group)
            perm_group.add_to(m)

    # --- Optional violations layer (subset of inspections flagged as violations) ---
    if "result" in df_valid.columns or "status" in df_valid.columns:
        flag_col = "result" if "result" in df_valid.columns else "status"
        viol = df_valid[
            df_valid[flag_col].astype(str).str.upper().str.contains(
                "FAIL|VIOL|NOV|DEFECT", na=False
            )
        ]
        if not viol.empty:
            viol_group = folium.FeatureGroup(name="Violations", show=False)
            for _, vrow in viol.iterrows():
                folium.CircleMarker(
                    location=[vrow["latitude"], vrow["longitude"]],
                    radius=5,
                    color="#d62728",
                    fill=True,
                    fill_opacity=0.8,
                    popup=folium.Popup(str(vrow.get(flag_col, "")), max_width=200),
                ).add_to(viol_group)
            viol_group.add_to(m)

    # Item 12 — layer toggle control
    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width=900, height=550, returned_objects=[])


def _render_folium_heatmap(df: pd.DataFrame) -> None:
    """Interactive Folium HeatMap density overlay for critical locations (Item 8)."""
    if not HAS_FOLIUM:
        st.info("Install folium and streamlit-folium for the interactive heatmap.")
        return

    df_valid = _flag_in_bounds(df).dropna(subset=["latitude", "longitude"])
    if df_valid.empty:
        st.warning("No points within NYC bounds.")
        return

    m = _base_folium_map(df_valid["latitude"].mean(), df_valid["longitude"].mean(), zoom_start=10)

    if "condition_score" in df_valid.columns:
        weights = df_valid["condition_score"].apply(
            lambda v: max(0.0, (100 - float(v)) / 100.0) if pd.notna(v) else 0.5
        )
        heat_data = [
            [lat, lon, w]
            for lat, lon, w in zip(
                df_valid["latitude"], df_valid["longitude"], weights
            )
        ]
    else:
        heat_data = df_valid[["latitude", "longitude"]].to_numpy().tolist()

    heat_group = folium.FeatureGroup(name="Inspection Density (heatmap)", show=True)
    folium_plugins.HeatMap(heat_data, radius=20, blur=15, max_zoom=13).add_to(heat_group)
    heat_group.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width=900, height=540, returned_objects=[])


def _render_plotly_map(df: pd.DataFrame, title: str = "Inspection Locations") -> None:
    if not HAS_PLOTLY:
        st.info("Install plotly for interactive charts.")
        return
    df_valid = _flag_in_bounds(df).dropna(subset=["latitude", "longitude"])
    if df_valid.empty:
        st.warning("No points within NYC bounds.")
        return

    color_col = next(
        (c for c in ("condition_score", "result", "status") if c in df_valid.columns), None
    )
    hover_cols = [
        c for c in ("borough", "defect_type", "result", "status", "street_name")
        if c in df_valid.columns
    ]

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


def _render_pydeck_map(df: pd.DataFrame, title: str = "Inspection Locations") -> None:
    """Render a high-performance deck.gl scatter map via pydeck.

    Suitable for large datasets (>10k points) where Plotly/Folium are slow.
    Requires pydeck: pip install pydeck

    When condition_score is present the ScatterplotLayer radius is scaled
    proportional to (100 - score) so worse locations appear larger —
    effectively a 3-D severity view (Item 36).
    """
    if not HAS_PYDECK:
        st.info("Install pydeck for GPU-accelerated maps: `pip install pydeck`")
        return
    df_valid = _flag_in_bounds(df).dropna(subset=["latitude", "longitude"])
    if df_valid.empty:
        st.warning("No points within NYC bounds.")
        return

    def _score_color(score):
        try:
            s = float(score)
        except (TypeError, ValueError):
            s = 50
        r = int(min(255, max(0, (100 - s) * 2.55)))
        g = int(min(255, max(0, s * 2.55)))
        return [r, g, 60, 180]

    df_valid = df_valid.copy()
    score_col = "condition_score" if "condition_score" in df_valid.columns else None
    if score_col:
        df_valid["_color"] = df_valid[score_col].apply(_score_color)
        # Item 36: radius proportional to severity (worse = bigger)
        df_valid["_radius"] = df_valid[score_col].apply(
            lambda s: max(30, int((100 - float(s)) * 1.5)) if pd.notna(s) else 60
        )
        st.caption("3D view: marker size reflects condition severity (larger = worse)")
    else:
        df_valid["_color"] = [[80, 140, 220, 180]] * len(df_valid)
        df_valid["_radius"] = 60

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_valid,
        get_position=["longitude", "latitude"],
        get_color="_color",
        get_radius="_radius",
        pickable=True,
        auto_highlight=True,
    )
    view = pdk.ViewState(
        latitude=df_valid["latitude"].mean(),
        longitude=df_valid["longitude"].mean(),
        zoom=11,
        pitch=0,
    )
    tooltip_fields = {
        c: f"{{{c}}}"
        for c in ("borough", "defect_type", "condition_score", "result", "status")
        if c in df_valid.columns
    }
    tooltip_html = "<br>".join(f"<b>{k}:</b> {v}" for k, v in tooltip_fields.items())
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip={"html": tooltip_html},
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    )
    st.pydeck_chart(deck)
    st.caption(f"{len(df_valid):,} points rendered · {title}")


# ---------------------------------------------------------------------------
# Item 20 — Block-level aggregation
# ---------------------------------------------------------------------------

def _render_block_aggregation(df: pd.DataFrame) -> None:
    """Aggregated bar chart by borough or block_id (Item 20)."""
    st.subheader("📦 Block Aggregation")
    if df.empty:
        st.info("No data to aggregate.")
        return

    group_col = "block_id" if "block_id" in df.columns else "borough" if "borough" in df.columns else None
    if group_col is None:
        st.info("No borough or block_id column found for aggregation.")
        return

    agg: dict = {group_col: "count"}
    if "condition_score" in df.columns:
        agg["condition_score"] = "mean"

    agg_df = df.groupby(group_col).agg(agg).rename(columns={group_col: "record_count"}).reset_index()
    agg_df = agg_df.rename(columns={"record_count": "count"})

    if not HAS_PLOTLY:
        st.dataframe(agg_df, use_container_width=True)
        return

    fig = px.bar(
        agg_df,
        x=group_col,
        y="count",
        color="condition_score" if "condition_score" in agg_df.columns else None,
        color_continuous_scale="RdYlGn",
        title=f"Inspection Count by {group_col.replace('_', ' ').title()}",
        labels={"count": "Record Count"},
        height=420,
    )
    if "condition_score" in agg_df.columns:
        fig.update_layout(coloraxis_colorbar_title="Avg Score")
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

    if "condition_score" in agg_df.columns:
        fig2 = px.bar(
            agg_df,
            x=group_col,
            y="condition_score",
            color="condition_score",
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            title=f"Average Condition Score by {group_col.replace('_', ' ').title()}",
            labels={"condition_score": "Avg Condition Score"},
            height=380,
        )
        fig2.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(agg_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Item 23 / Item 41 — Spatial export buttons
# ---------------------------------------------------------------------------

def _export_spatial_buttons(df: pd.DataFrame, key_prefix: str) -> None:
    """GeoJSON, GeoPackage, and CSV download buttons for spatial data (Items 23, 41)."""
    st.markdown("**Export spatial data**")
    col_geo, col_gpkg, col_csv = st.columns(3)

    with col_geo:
        if "the_geom" in df.columns:
            try:
                from socrata_toolkit.spatial.geodataframe import (
                    HAS_GEOPANDAS,
                    geodataframe_from_socrata,
                    to_geojson,
                )
                if HAS_GEOPANDAS:
                    with st.spinner("Building GeoJSON…"):
                        gdf = geodataframe_from_socrata(df)
                        geojson_str = to_geojson(gdf)
                    st.download_button(
                        "Export GeoJSON",
                        geojson_str.encode(),
                        f"{key_prefix}_export.geojson",
                        "application/geo+json",
                        key=f"{key_prefix}_geojson",
                    )
                else:
                    st.info("Install geopandas for GeoJSON export.")
            except Exception as err:
                st.warning(f"GeoJSON export failed: {err}")
        elif "latitude" in df.columns and "longitude" in df.columns:
            geojson_str = _df_to_geojson(df)
            st.download_button(
                "Export GeoJSON",
                geojson_str.encode(),
                f"{key_prefix}_export.geojson",
                "application/geo+json",
                key=f"{key_prefix}_geojson",
            )
        else:
            st.info("No geometry columns available for GeoJSON export.")

    with col_gpkg:
        # Item 41 — GeoPackage export
        if "the_geom" in df.columns:
            try:
                from socrata_toolkit.spatial.geodataframe import (
                    HAS_GEOPANDAS,
                    geodataframe_from_socrata,
                )
                if HAS_GEOPANDAS:
                    if st.button("Export GeoPackage (.gpkg)", key=f"{key_prefix}_gpkg_btn"):
                        with st.spinner("Building GeoPackage…"):
                            gdf = geodataframe_from_socrata(df)
                            with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
                                tmp_path = tmp.name
                            gdf.to_file(tmp_path, driver="GPKG")
                            with open(tmp_path, "rb") as fh:
                                gpkg_bytes = fh.read()
                            os.unlink(tmp_path)
                        st.download_button(
                            "Download GeoPackage",
                            gpkg_bytes,
                            f"{key_prefix}_export.gpkg",
                            "application/octet-stream",
                            key=f"{key_prefix}_gpkg_dl",
                        )
                else:
                    st.info("Install geopandas for GeoPackage export.")
            except Exception as err:
                st.warning(f"GeoPackage export failed: {err}")
        else:
            st.caption("GeoPackage requires the_geom column.")

    with col_csv:
        st.download_button(
            "Export CSV",
            df.to_csv(index=False).encode(),
            f"{key_prefix}_export.csv",
            "text/csv",
            key=f"{key_prefix}_csv",
        )


# ---------------------------------------------------------------------------
# Item 27 — Spatial time-lapse
# ---------------------------------------------------------------------------

def _render_time_lapse(df: pd.DataFrame) -> None:
    """Animated bar chart showing inspection count by month (Item 27)."""
    date_col = next(
        (c for c in df.columns if any(d in c.lower() for d in ("date", "created", "open"))),
        None,
    )
    if date_col is None:
        st.info("No date column detected for time-lapse.")
        return

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    if df.empty:
        st.info("No valid dates found for time-lapse.")
        return

    df["_ym"] = df[date_col].dt.to_period("M").astype(str)
    months = sorted(df["_ym"].unique().tolist())
    if len(months) < 2:
        st.info("Fewer than 2 months of data — time-lapse not available.")
        return

    start_idx, end_idx = st.select_slider(
        "Month range",
        options=list(range(len(months))),
        value=(0, len(months) - 1),
        format_func=lambda i: months[i],
        key="timelapse_slider",
    )
    selected_months = months[start_idx: end_idx + 1]
    df_sel = df[df["_ym"].isin(selected_months)]

    if not HAS_PLOTLY:
        st.dataframe(df_sel.groupby("_ym").size().reset_index(name="count"), use_container_width=True)
        return

    group_col = "borough" if "borough" in df_sel.columns else None
    if group_col:
        agg = df_sel.groupby(["_ym", group_col]).size().reset_index(name="count")
        fig = px.bar(
            agg,
            x=group_col,
            y="count",
            animation_frame="_ym",
            color=group_col,
            title="Inspection Count per Month by Borough",
            height=420,
        )
    else:
        agg = df_sel.groupby("_ym").size().reset_index(name="count")
        fig = px.bar(
            agg,
            x="_ym",
            y="count",
            animation_frame="_ym",
            title="Inspection Count per Month",
            height=420,
        )
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Item 28 — Route optimiser
# ---------------------------------------------------------------------------

def _render_route_optimizer(df: pd.DataFrame) -> None:
    """Nearest-neighbour TSP route optimiser (Item 28)."""
    if "latitude" not in df.columns or "longitude" not in df.columns:
        st.info("Latitude/longitude columns required for route optimisation.")
        return

    borough_opts = ["All boroughs"]
    if "borough" in df.columns:
        borough_opts += sorted(df["borough"].dropna().unique().tolist())
    boro_sel = st.selectbox("Borough filter", borough_opts, key="route_boro")
    if boro_sel != "All boroughs" and "borough" in df.columns:
        df_r = df[df["borough"] == boro_sel].copy()
    else:
        df_r = df.copy()

    df_r = _flag_in_bounds(df_r).dropna(subset=["latitude", "longitude"])
    if df_r.empty:
        st.info("No valid locations for selected filter.")
        return

    df_r = df_r.head(50)
    st.caption(f"Optimising route across {len(df_r)} locations (capped at 50).")

    coords = list(zip(df_r["latitude"].tolist(), df_r["longitude"].tolist()))
    route_idx = _nearest_neighbor_route(coords)

    ordered = df_r.iloc[route_idx].reset_index(drop=True)
    ordered.index = ordered.index + 1  # 1-based stop number

    # Compute total distance
    total_km = 0.0
    for i in range(len(route_idx) - 1):
        c1 = coords[route_idx[i]]
        c2 = coords[route_idx[i + 1]]
        total_km += _haversine_km(c1[0], c1[1], c2[0], c2[1])

    st.metric("Estimated total route distance", f"{total_km:.2f} km")

    display_cols = [c for c in ("borough", "street_name", "block_id", "condition_score",
                                "latitude", "longitude") if c in ordered.columns]
    st.dataframe(ordered[display_cols] if display_cols else ordered,
                 use_container_width=True, height=300)

    st.download_button(
        "Export route as CSV",
        ordered.to_csv(index=True).encode(),
        "optimised_route.csv",
        "text/csv",
        key="route_csv",
    )


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def render_gis_page() -> None:
    st.header("🗺️ GIS & Spatial Analysis")
    st.caption("Conflict detection, hotspot mapping, and spatial reporting for sidewalk inspection data.")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📍 Inspection Map",
        "⚠️ Conflict Detection",
        "🔥 Hotspot Analysis",
        "📊 Spatial Reports",
        "🚧 HIQA & Capital Projects",
        "📋 Stipulations & Closures",
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
    with tab6:
        _render_stipulations_tab()


def _get_inspection_df(key_prefix: str) -> pd.DataFrame:
    """Load inspections from Socrata or user-uploaded CSV."""
    source = st.radio(
        "Data source",
        ["Socrata (live)", "Upload CSV"],
        horizontal=True,
        key=f"{key_prefix}_src",
    )
    if source == "Socrata (live)":
        limit = st.number_input("Row limit", 1_000, 100_000, 25_000, step=5_000,
                                key=f"{key_prefix}_lim")
        with st.spinner("Loading from Socrata…"):
            df = _load_inspections(int(limit))
        if demo_mode_enabled():
            st.caption(
                "⚠️ Running in demo mode — configure SOCRATA_APP_TOKEN in Settings for live data."
            )
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

    # Map subtabs — main map + block aggregation (Item 20) + time-lapse (Item 27)
    map_subtab, agg_subtab, timelapse_subtab = st.tabs([
        "🗺️ Map View", "📦 Block Aggregation", "⏱️ Time-lapse"
    ])

    with map_subtab:
        engine_opts = ["Plotly (recommended)", "Folium (interactive)"]
        if HAS_PYDECK:
            engine_opts.append("pydeck (GPU / large datasets)")
        map_engine = st.radio("Map engine", engine_opts, horizontal=True, key="gis_engine")
        if map_engine.startswith("Plotly"):
            _render_plotly_map(df_filtered)
        elif map_engine.startswith("Folium"):
            _render_folium_map(df_filtered)
        else:
            _render_pydeck_map(df_filtered)

        with st.expander("Data Table"):
            st.dataframe(df_filtered, use_container_width=True, height=300)

        # Item 37 — Spatial Statistics
        if "the_geom" in df_filtered.columns:
            with st.expander("📐 Spatial Statistics"):
                try:
                    from socrata_toolkit.spatial.geodataframe import (
                        HAS_GEOPANDAS,
                        geodataframe_from_socrata,
                        spatial_stats,
                    )
                    if HAS_GEOPANDAS:
                        with st.spinner("Computing spatial statistics…"):
                            gdf = geodataframe_from_socrata(df_filtered)
                            stats = spatial_stats(gdf)
                        st.json(stats)
                    else:
                        st.info("Install geopandas for spatial statistics.")
                except Exception as err:
                    st.warning(f"Spatial statistics failed: {err}")

        # Item 28 — Route optimiser
        with st.expander("🗺️ Inspector Route Optimizer"):
            _render_route_optimizer(df_filtered)

    with agg_subtab:
        _render_block_aggregation(df_filtered)

    with timelapse_subtab:
        with st.expander("⏱️ Time-lapse", expanded=True):
            _render_time_lapse(df_filtered)

    # Export buttons at bottom of tab (Item 23 / 41)
    st.markdown("---")
    _export_spatial_buttons(df_filtered, "insp_map")


def _render_conflict_detection_tab() -> None:
    st.subheader("⚠️ Conflict Detection")
    st.caption("Identify inspection locations that overlap with active permits or capital projects.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Inspection Data**")
        df_insp = _get_inspection_df("conf_insp")

    with col2:
        st.markdown("**Permits / Contracts**")
        perm_src = st.radio("Source", ["Socrata (live)", "Upload CSV"],
                            horizontal=True, key="conf_perm_src")
        if perm_src == "Socrata (live)":
            perm_limit = st.number_input("Row limit", 1_000, 50_000, 15_000, step=5_000,
                                         key="conf_perm_lim")
            with st.spinner("Loading permits from Socrata…"):
                df_perm = _load_permits(int(perm_limit))
        else:
            up2 = st.file_uploader("Upload permits CSV", type="csv", key="conf_perm_up")
            df_perm = _normalize_permits(pd.read_csv(up2)) if up2 else pd.DataFrame()

    if df_insp.empty or df_perm.empty:
        st.info("Load both datasets to detect conflicts.")
        return

    # Item 13 / 14 — buffer-based spatial conflict detection via GeoPandas
    has_coords = (
        "latitude" in df_insp.columns and "longitude" in df_insp.columns
        and "latitude" in df_perm.columns and "longitude" in df_perm.columns
    )
    used_geopandas = False
    if HAS_GEOPANDAS and has_coords:
        radius_m = st.slider(
            "Conflict buffer radius (meters) — flag permits within this distance of an inspection",
            min_value=50, max_value=500, value=150, step=10, key="conf_radius",
        )
        with st.spinner(f"Buffering inspections by {radius_m} m and running GeoPandas sjoin_nearest…"):
            conflicts = _detect_conflicts_geopandas(df_insp, df_perm, float(radius_m))
        if conflicts.empty:
            # Fall back to the attribute-based join when no spatial matches found
            conflicts = _detect_spatial_conflicts(df_insp, df_perm)
        else:
            used_geopandas = True
            st.caption(
                f"GeoPandas sjoin_nearest (EPSG:2263, ≤{radius_m} m buffer): "
                f"{len(conflicts):,} inspection∩permit conflict pairs."
            )
    else:
        if not HAS_GEOPANDAS:
            st.caption("Install geopandas for buffer-based spatial conflict detection. Using attribute join.")
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

    # Item 12 — interactive conflict map: inspections + permits toggled via LayerControl
    if used_geopandas and HAS_FOLIUM:
        with st.expander("🗺️ Conflict Map (inspections + permits)", expanded=False):
            st.caption(
                "Inspections clustered (FastMarkerCluster); toggle the Permits and "
                "Inspection Density layers via the control top-right. Use the Draw tools "
                "to mark an ad-hoc study area."
            )
            _render_folium_map(df_insp, permits=df_perm)


def _render_hotspot_tab() -> None:
    st.subheader("🔥 Hotspot Analysis")
    st.caption("Identify geographic clusters of high-severity defects to prioritize patrol areas.")

    df = _get_inspection_df("hot_insp")
    if df.empty or "latitude" not in df.columns:
        return

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider(
            "Critical condition threshold (show locations below this score)", 10, 60, 35,
            key="hot_thresh"
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

    engine_opts = ["Plotly density"]
    if HAS_FOLIUM:
        engine_opts.append("Folium heatmap (interactive)")
    heat_engine = st.radio("Hotspot engine", engine_opts, horizontal=True, key="hot_engine")

    if heat_engine.startswith("Folium"):
        _render_folium_heatmap(df_critical)
    else:
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
        st.dataframe(
            borough_counts.sort_values("count", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    # Item 21 — DBSCAN cluster analysis
    with st.expander("🔍 DBSCAN Cluster Analysis"):
        if not HAS_SKLEARN:
            st.info(
                "Install scikit-learn for DBSCAN clustering: `pip install scikit-learn`"
            )
        else:
            _render_dbscan_clusters(df_critical)


def _render_dbscan_clusters(df: pd.DataFrame) -> None:
    """DBSCAN hotspot clustering overlay (Item 21)."""
    if df.empty or "latitude" not in df.columns or "longitude" not in df.columns:
        st.info("No valid coordinates for clustering.")
        return

    coords = df[["latitude", "longitude"]].to_numpy()
    with st.spinner("Running DBSCAN clustering…"):
        db = DBSCAN(eps=0.005, min_samples=5).fit(coords)
    labels = db.labels_

    df_c = df.copy()
    df_c["cluster"] = labels.astype(str)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())
    col1, col2 = st.columns(2)
    col1.metric("Clusters found", n_clusters)
    col2.metric("Noise points", n_noise)

    if n_clusters == 0:
        st.info("No clusters found with current density threshold (eps=0.005, min_samples=5).")
        return

    if HAS_PLOTLY:
        # Map noise points (-1) as grey; clusters get distinct colours
        fig = px.scatter_mapbox(
            df_c,
            lat="latitude",
            lon="longitude",
            color="cluster",
            color_discrete_map={"-1": "#aaaaaa"},
            hover_data=[c for c in ("borough", "condition_score") if c in df_c.columns],
            zoom=10,
            title="DBSCAN Clusters",
            height=500,
        )
        fig.update_layout(
            mapbox_style="carto-positron",
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Top 5 clusters by size
    cluster_sizes = (
        df_c[df_c["cluster"] != "-1"]
        .groupby("cluster")
        .size()
        .reset_index(name="size")
        .sort_values("size", ascending=False)
        .head(5)
    )
    st.markdown("**Top 5 clusters by size**")
    st.dataframe(cluster_sizes, use_container_width=True, hide_index=True)


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
            fig = px.bar(boro_counts, x="borough", y="count", color="borough",
                         title="Inspections by Borough")
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
                df.groupby("defect_type").size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
            )
            fig3 = px.bar(defect_counts, x="defect_type", y="count",
                          title="Defect Type Distribution")
            st.plotly_chart(fig3, use_container_width=True)

    # Item 38 — Coordinate converter
    with st.expander("🔄 Coordinate Converter"):
        _render_coordinate_converter()

    st.markdown("---")
    if st.button("📥 Export Spatial Report (Excel)"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="All Inspections", index=False)
            if "borough" in df.columns:
                agg: dict = {"borough": "count"}
                if "condition_score" in df.columns:
                    agg["condition_score"] = "mean"
                summary = (
                    df.groupby("borough")
                    .agg(agg)
                    .rename(columns={"borough": "total_locations"})
                    .reset_index()
                )
                summary.to_excel(writer, sheet_name="Borough Summary", index=False)
        buf.seek(0)
        st.download_button(
            "Download Report",
            buf.getvalue(),
            f"spatial_report_{date.today()}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _render_coordinate_converter() -> None:
    """WGS84 → NY State Plane + Web Mercator coordinate converter (Item 38)."""
    st.markdown("Convert WGS84 (lat/lon) to projected coordinate systems.")
    lat_in = st.number_input("Latitude (WGS84)", value=40.7128, format="%.6f", key="coord_lat")
    lon_in = st.number_input("Longitude (WGS84)", value=-74.0060, format="%.6f", key="coord_lon")

    if st.button("Convert", key="coord_convert"):
        if HAS_PYPROJ:
            try:
                t_sp = Transformer.from_crs("EPSG:4326", "EPSG:2263", always_xy=True)
                sp_x, sp_y = t_sp.transform(lon_in, lat_in)
                t_merc = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
                merc_x, merc_y = t_merc.transform(lon_in, lat_in)
            except Exception as err:
                st.error(f"Projection failed: {err}")
                return
        else:
            # Manual approximations
            # NY State Plane (EPSG:2263) — simplified linear approx near NYC
            sp_x = (lon_in + 74.0) * 308_042.0
            sp_y = (lat_in - 40.5) * 363_660.0
            # Web Mercator (EPSG:3857)
            merc_x = lon_in * 20037508.34 / 180.0
            merc_y = (
                math.log(math.tan((90 + lat_in) * math.pi / 360.0)) / (math.pi / 180.0)
            ) * 20037508.34 / 180.0
            st.caption("pyproj not installed — using manual approximations (less accurate).")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**NY State Plane (EPSG:2263) — feet**")
            st.code(f"Easting:  {sp_x:,.2f} ft\nNorthing: {sp_y:,.2f} ft")
        with col2:
            st.markdown("**Web Mercator (EPSG:3857) — metres**")
            st.code(f"X: {merc_x:,.2f} m\nY: {merc_y:,.2f} m")


def _render_hiqa_capital_tab() -> None:
    st.subheader("🚧 HIQA Street Construction Inspections & Capital Projects")
    st.caption(
        "Highway Inspection & Quality Assurance (HIQA) inspections of permit compliance on city "
        "streets. Capital Reconstruction Projects — intersection-level spatial data."
    )

    sub_hiqa, sub_cap = st.tabs(["🔍 HIQA Inspections", "🏗️ Capital Intersections"])

    with sub_hiqa:
        hiqa_limit = st.number_input("Row limit", 1_000, 50_000, 10_000, step=1_000,
                                     key="hiqa_lim")
        df_hiqa = _load_street_construction_inspections(int(hiqa_limit))
        if df_hiqa.empty:
            st.info("No HIQA data loaded. Configure SOCRATA_APP_TOKEN in Settings.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total inspections", f"{len(df_hiqa):,}")
            if "inspectionresulttype" in df_hiqa.columns:
                vio = (
                    df_hiqa["inspectionresulttype"]
                    .str.upper()
                    .str.contains("FAIL|VIOL|NOV", na=False)
                    .sum()
                )
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
            st.dataframe(
                df_hiqa[show_cols] if show_cols else df_hiqa,
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "⬇ Export (CSV)", df_hiqa.to_csv(index=False).encode(),
                "hiqa_inspections.csv", mime="text/csv"
            )

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
                active = (
                    df_cap["projectsta"]
                    .str.upper()
                    .str.contains("ACTIVE|CONSTRUCT|DESIGN", na=False)
                    .sum()
                )
                c2.metric("Active/In progress", int(active))
            if "projectcost" in df_cap.columns:
                df_cap["projectcost"] = pd.to_numeric(df_cap["projectcost"], errors="coerce")
                c3.metric("Total project cost", f"${df_cap['projectcost'].sum():,.0f}")

            if "boroughnam" in df_cap.columns:
                boro_sel = st.multiselect(
                    "Borough filter", df_cap["boroughnam"].dropna().unique().tolist(),
                    key="cap_boro"
                )
                if boro_sel:
                    df_cap = df_cap[df_cap["boroughnam"].isin(boro_sel)]

            show_cols = [c for c in (
                "projtitle", "boroughnam", "onstreetname", "fromstreet", "tostreetna",
                "projectsta", "designstar", "construc_2", "projectcost", "leadagency",
            ) if c in df_cap.columns]
            st.dataframe(
                df_cap[show_cols] if show_cols else df_cap,
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "⬇ Export (CSV)", df_cap.to_csv(index=False).encode(),
                "capital_intersections.csv", mime="text/csv"
            )

            if HAS_PLOTLY and "projectsta" in df_cap.columns:
                status_counts = df_cap["projectsta"].value_counts().reset_index()
                status_counts.columns = ["status", "count"]
                fig = px.pie(status_counts, names="status", values="count",
                             title="Capital projects by status", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)

            # Item 33 — Capital project impact radius overlay
            _render_capital_impact_radius(df_cap)

    # Item 40 — PostGIS connection settings
    with st.expander("🗄️ PostGIS Connection"):
        _render_postgis_settings()


def _render_capital_impact_radius(df_cap: pd.DataFrame) -> None:
    """Proportional-marker overlay for capital project impact radius (Item 33)."""
    if not HAS_PLOTLY:
        return

    lat_col = pick_column(df_cap, LAT_CANDIDATES) if not df_cap.empty else None
    lon_col = pick_column(df_cap, LON_CANDIDATES) if not df_cap.empty else None
    # After normalisation the column may already be named "latitude"/"longitude"
    lat_col = lat_col or ("latitude" if "latitude" in df_cap.columns else None)
    lon_col = lon_col or ("longitude" if "longitude" in df_cap.columns else None)
    if lat_col is None or lon_col is None:
        return

    df_pts = df_cap.dropna(subset=[lat_col, lon_col]).copy()
    if df_pts.empty:
        return

    st.markdown("**Capital Project Impact Radius**")
    radius_m = st.number_input(
        "Impact radius (meters)", min_value=10, max_value=2000, value=200, step=10,
        key="cap_impact_radius"
    )

    # Scale marker size 5–40 proportional to radius (capped for readability)
    marker_size = max(5, min(40, int(radius_m / 10)))

    hover_col = next((c for c in ("projtitle", "onstreetname") if c in df_pts.columns), None)
    fig = px.scatter_mapbox(
        df_pts,
        lat=lat_col,
        lon=lon_col,
        size=[marker_size] * len(df_pts),
        hover_name=hover_col,
        hover_data=[c for c in ("projectsta", "projectcost") if c in df_pts.columns],
        color_discrete_sequence=["#e05c00"],
        zoom=10,
        title=f"Capital Projects — Impact radius {radius_m} m",
        height=480,
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Each marker represents one capital intersection. Marker size reflects the "
               f"{radius_m} m impact radius (larger radius → bigger marker).")


def _render_postgis_settings() -> None:
    """PostGIS connection form (Item 40)."""
    try:
        from app.services.postgis import PostGISConfig, PostGISService
        HAS_POSTGIS_SERVICE = True
    except ImportError:
        HAS_POSTGIS_SERVICE = False

    with st.form("postgis_form"):
        st.markdown("Configure a PostGIS connection to query spatial tables directly.")
        host = st.text_input("Host", value="localhost", key="pg_host")
        port = st.number_input("Port", min_value=1, max_value=65535, value=5432, key="pg_port")
        dbname = st.text_input("Database", value="nyc_dot", key="pg_db")
        user = st.text_input("User", value="postgres", key="pg_user")
        password = st.text_input("Password", type="password", key="pg_pass")
        col_test, col_list = st.columns(2)
        test_btn = col_test.form_submit_button("Test Connection")
        list_btn = col_list.form_submit_button("List Spatial Tables")

    if test_btn or list_btn:
        if not HAS_POSTGIS_SERVICE:
            st.warning(
                "PostGIS service not available. "
                "Ensure `app/services/postgis.py` is present and psycopg2 is installed."
            )
            return
        try:
            cfg = PostGISConfig(
                host=host, port=int(port), dbname=dbname, user=user, password=password
            )
            svc = PostGISService(cfg)
            if test_btn:
                ok = svc.test_connection()
                if ok:
                    st.success("✅ Connected successfully.")
                else:
                    st.error("❌ Connection failed.")
            if list_btn:
                tables = svc.list_spatial_tables()
                if tables:
                    st.dataframe(pd.DataFrame({"spatial_tables": tables}),
                                 use_container_width=True)
                else:
                    st.info("No spatial tables found.")
        except Exception as err:
            st.error(f"Connection error: {err}")


# ---------------------------------------------------------------------------
# Item 34 / 35 — Stipulations & Closures tab
# ---------------------------------------------------------------------------

def _render_stipulations_tab() -> None:
    """Permit stipulations, street closures, and step streets (Items 34, 35)."""
    st.subheader("📋 Stipulations & Closures")
    st.caption(
        "Permit stipulations, street closures at block level, and step streets from Socrata."
    )

    row_limit = st.number_input("Row limit (per dataset)", 500, 25_000, 5_000, step=500,
                                key="stip_limit")

    # --- Stipulations ---
    with st.spinner("Loading permit stipulations…"):
        df_stip = _load_permit_stipulations(int(row_limit))

    # --- Closures ---
    with st.spinner("Loading street closures…"):
        df_close = _load_street_closures(int(row_limit))

    c1, c2 = st.columns(2)
    c1.metric("Total stipulations", f"{len(df_stip):,}")
    c2.metric("Total closures", f"{len(df_close):,}")

    stip_tab, close_tab, step_tab = st.tabs([
        "📄 Stipulations", "🚧 Closures Map", "🪜 Step Streets"
    ])

    with stip_tab:
        if df_stip.empty:
            st.info("No stipulation data. Configure SOCRATA_APP_TOKEN in Settings.")
        else:
            st.dataframe(df_stip, use_container_width=True, height=380)
            st.download_button(
                "⬇ Download Stipulations (CSV)",
                df_stip.to_csv(index=False).encode(),
                "permit_stipulations.csv",
                "text/csv",
                key="stip_dl",
            )

    with close_tab:
        if df_close.empty:
            st.info("No closure data loaded.")
        else:
            if HAS_PLOTLY and "latitude" in df_close.columns and "longitude" in df_close.columns:
                df_map = _flag_in_bounds(df_close).dropna(subset=["latitude", "longitude"])
                if not df_map.empty:
                    hover_cols = [
                        c for c in ("borough", "streetname", "fromstreet", "tostreet",
                                    "closuretype", "startdate", "enddate")
                        if c in df_map.columns
                    ]
                    fig = px.scatter_mapbox(
                        df_map,
                        lat="latitude",
                        lon="longitude",
                        hover_data=hover_cols,
                        color_discrete_sequence=["#d62728"],
                        zoom=10,
                        title="Street Closures",
                        height=500,
                    )
                    fig.update_layout(
                        mapbox_style="carto-positron",
                        margin={"r": 0, "t": 40, "l": 0, "b": 0},
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No geocoded closures within NYC bounds.")
            else:
                st.info("Plotly or lat/lon columns required for closure map.")

            st.dataframe(df_close, use_container_width=True, height=300)
            st.download_button(
                "⬇ Download Closures (CSV)",
                df_close.to_csv(index=False).encode(),
                "street_closures.csv",
                "text/csv",
                key="close_dl",
            )

    with step_tab:
        _render_step_streets(int(row_limit))


def _render_step_streets(limit: int) -> None:
    """Step streets dataset view (Item 35) — fourfour u9au-h79y."""
    st.markdown("**Step Streets** — NYC DOT dataset `u9au-h79y`")
    with st.spinner("Loading step streets…"):
        df_ss = _load_step_streets(limit)

    if df_ss.empty:
        st.info("No step streets data. Configure SOCRATA_APP_TOKEN in Settings.")
        return

    # Count by borough
    if "borough" in df_ss.columns:
        boro_counts = df_ss["borough"].value_counts().reset_index()
        boro_counts.columns = ["borough", "count"]
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("**Count by Borough**")
            st.dataframe(boro_counts, use_container_width=True, hide_index=True)
        with c2:
            if HAS_PLOTLY:
                fig = px.bar(boro_counts, x="borough", y="count", color="borough",
                             title="Step Streets by Borough", height=300)
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.metric("Total step streets", len(df_ss))

    # Map if coordinates available
    if "latitude" in df_ss.columns and "longitude" in df_ss.columns and HAS_PLOTLY:
        df_map = _flag_in_bounds(df_ss).dropna(subset=["latitude", "longitude"])
        if not df_map.empty:
            hover_cols = [
                c for c in ("borough", "streetname", "from_street", "to_street")
                if c in df_map.columns
            ]
            fig = px.scatter_mapbox(
                df_map,
                lat="latitude",
                lon="longitude",
                color="borough" if "borough" in df_map.columns else None,
                hover_data=hover_cols,
                zoom=10,
                title="Step Streets Locations",
                height=480,
            )
            fig.update_layout(
                mapbox_style="carto-positron",
                margin={"r": 0, "t": 40, "l": 0, "b": 0},
            )
            st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_ss, use_container_width=True, height=300)
    st.download_button(
        "⬇ Download Step Streets (CSV)",
        df_ss.to_csv(index=False).encode(),
        "step_streets.csv",
        "text/csv",
        key="step_dl",
    )
