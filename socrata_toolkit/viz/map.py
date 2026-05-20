"""GIS Map View Generator for DOT Sidewalk Toolkit.

Generate interactive maps from DataFrames with lat/lon columns.
Maps are exported as standalone HTML files viewable in any browser.

Uses folium (Leaflet.js) for interactive maps. Falls back to a
simple HTML table if folium is not installed.

Example::

    from socrata_toolkit.viz.map import create_map, cluster_map

    html = create_map(df, lat_col="latitude", lon_col="longitude",
                      color_col="priority", popup_cols=["address", "status"])
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# NYC center coordinates
NYC_CENTER = (40.7128, -74.0060)

PRIORITY_COLORS = {
    "critical": "red", "high": "orange", "medium": "yellow",
    "low": "green", "none": "gray",
}

STATUS_COLORS = {
    "Pending Repair": "red", "In Progress": "orange",
    "Complete": "green", "City-Initiated": "blue",
}

BOROUGH_COLORS = {
    "MANHATTAN": "blue", "BRONX": "purple", "BROOKLYN": "red",
    "QUEENS": "green", "STATEN ISLAND": "orange",
}


def create_map(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    color_col: Optional[str] = None,
    color_map: Optional[Dict[str, str]] = None,
    popup_cols: Optional[List[str]] = None,
    title: str = "DOT Sidewalk Map",
    center: Optional[tuple] = None,
    zoom: int = 11,
) -> str:
    """Create an interactive map with markers.

    Returns HTML string. Save to file with Path(path).write_text(html).
    """
    try:
        import folium
    except ImportError:
        return _fallback_map(df, lat_col, lon_col, popup_cols, title)

    tmp = df.copy()
    tmp[lat_col] = pd.to_numeric(tmp[lat_col], errors="coerce")
    tmp[lon_col] = pd.to_numeric(tmp[lon_col], errors="coerce")
    tmp = tmp.dropna(subset=[lat_col, lon_col])

    map_center = center or (tmp[lat_col].mean(), tmp[lon_col].mean()) if not tmp.empty else NYC_CENTER
    m = folium.Map(location=map_center, zoom_start=zoom, tiles="cartodbpositron")

    cmap = color_map or PRIORITY_COLORS
    popup_columns = popup_cols or [c for c in df.columns if c not in (lat_col, lon_col)][:5]

    for _, row in tmp.iterrows():
        color = "blue"
        if color_col and color_col in row:
            color = cmap.get(str(row[color_col]), "blue")

        popup_html = "<br>".join(f"<b>{c}</b>: {row.get(c, '')}" for c in popup_columns if c in row)
        folium.CircleMarker(
            location=(row[lat_col], row[lon_col]),
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m._repr_html_()


def cluster_map(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    popup_cols: Optional[List[str]] = None,
    title: str = "DOT Sidewalk Clusters",
) -> str:
    """Create a map with marker clustering for hotspot visualization."""
    try:
        import folium
        from folium.plugins import MarkerCluster
    except ImportError:
        return _fallback_map(df, lat_col, lon_col, popup_cols, title)

    tmp = df.copy()
    tmp[lat_col] = pd.to_numeric(tmp[lat_col], errors="coerce")
    tmp[lon_col] = pd.to_numeric(tmp[lon_col], errors="coerce")
    tmp = tmp.dropna(subset=[lat_col, lon_col])

    map_center = (tmp[lat_col].mean(), tmp[lon_col].mean()) if not tmp.empty else NYC_CENTER
    m = folium.Map(location=map_center, zoom_start=11, tiles="cartodbpositron")
    cluster = MarkerCluster().add_to(m)

    popup_columns = popup_cols or [c for c in df.columns if c not in (lat_col, lon_col)][:5]

    for _, row in tmp.iterrows():
        popup_html = "<br>".join(f"<b>{c}</b>: {row.get(c, '')}" for c in popup_columns if c in row)
        folium.Marker(
            location=(row[lat_col], row[lon_col]),
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(cluster)

    return m._repr_html_()


def save_map(html: str, path: str) -> str:
    """Save map HTML to a file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return str(p)


def _fallback_map(df, lat_col, lon_col, popup_cols, title) -> str:
    """Generate a simple HTML page when folium is not available."""
    rows_html = ""
    cols = popup_cols or list(df.columns)[:8]
    for _, row in df.head(100).iterrows():
        cells = "".join(f"<td>{row.get(c, '')}</td>" for c in cols)
        rows_html += f"<tr>{cells}</tr>"
    headers = "".join(f"<th>{c}</th>" for c in cols)
    return f"""<!DOCTYPE html><html><head><title>{title}</title>
<style>body{{font-family:sans-serif}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:6px}}th{{background:#003366;color:white}}</style>
</head><body><h1>{title}</h1><p>Install folium for interactive maps: pip install folium</p>
<table><tr>{headers}</tr>{rows_html}</table></body></html>"""
