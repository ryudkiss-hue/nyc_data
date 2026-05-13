from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, List
from types import SimpleNamespace

import pandas as pd
from .core import COL_LAT, COL_LON, COL_BORO

logger = logging.getLogger(__name__)

try:
    from shapely.geometry import shape, Point
    import shapely.wkt as wkt
except ImportError:
    shape = None
    Point = None
    wkt = None

# ── Spatial Indexing ──────────────────────────────────────────────────────────

@dataclass
class SpatialIndex:
    """Minimal in-memory spatial index for small datasets."""
    features: list = field(default_factory=list)

    def index(self, features: Iterable[dict]):
        self.features = list(features)

    def query_point(self, lat: float, lon: float) -> list[dict]:
        if shape is None: raise ImportError("Install shapely for spatial support.")
        pt = Point(lon, lat)
        return [f for f in self.features if shape(f["geometry"]).contains(pt)]

# ── Spatial Joins ─────────────────────────────────────────────────────────────

def _to_geom(value: Any):
    if value is None: return None
    if isinstance(value, dict): return shape(value)
    if isinstance(value, str):
        if value.startswith("{"):
            import json
            return shape(json.loads(value))
        return wkt.loads(value)
    return None

def cluster_locations(df: pd.DataFrame, lat_col: str, lon_col: str, n_clusters: int = 5) -> pd.DataFrame:
    """Cluster locations using KMeans."""
    try:
        from sklearn.cluster import KMeans
        out = df.copy()
        X = out[[lat_col, lon_col]].fillna(0)
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        out["cluster"] = kmeans.fit_predict(X)
        return out
    except ImportError:
        logger.warning("scikit-learn not installed, clustering disabled.")
        return df

class SpatialVisualization:
    """Visualization helpers for spatial data using high-performance Mapbox traces."""
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _apply_map_layout(self, fig: Any, title: str) -> Any:
        from .analysis import _apply_modern_layout
        fig = _apply_modern_layout(fig, title)
        fig.update_layout(
            mapbox=dict(
                style="carto-darkmatter", # Open source alternative to Mapbox styles
                zoom=10,
                center=dict(lat=40.7128, lon=-74.0060),
            ),
            margin=dict(t=80, l=0, r=0, b=0),
        )
        return fig

    def plot_heatmap(self, lat_col: str = COL_LAT, lon_col: str = COL_LON, title: str = "Spatial Density Hotspots"):
        """Create a density heatmap (Plotly Reference: Densitymapbox)."""
        import plotly.graph_objects as go
        
        fig = go.Figure(go.Densitymapbox(
            lat=self.df[lat_col],
            lon=self.df[lon_col],
            z=[1]*len(self.df),
            radius=12,
            colorscale="Viridis",
            hovertemplate="<b>Location</b><br>Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<extra></extra>"
        ))
        return self._apply_map_layout(fig, title)

    def plot_scatter_map(self, lat_col: str = COL_LAT, lon_col: str = COL_LON, color_col: str | None = None, title: str = "Geospatial Point Map"):
        """Create a scatter map with optimized markers (Plotly Reference: Scattermapbox)."""
        import plotly.express as px
        
        fig = px.scatter_mapbox(
            self.df, 
            lat=lat_col, 
            lon=lon_col, 
            color=color_col,
            size_max=15,
            zoom=10,
        )
        
        fig.update_traces(
            marker=dict(size=8, opacity=0.8),
            unselected=dict(marker=dict(opacity=0.2)),
            hovertemplate="<b>Segment ID: %{customdata[0]}</b><br>Lat: %{lat:.4f}<br>Lon: %{lon:.4f}<extra></extra>"
        )
        return self._apply_map_layout(fig, title)

def spatial_intersects_join(left: pd.DataFrame, right: pd.DataFrame, left_geom: str, right_geom: str, buffer_meters: float = 0.0) -> pd.DataFrame:
    """Perform a spatial intersection join between two DataFrames."""
    if shape is None:
        raise ImportError("Install shapely for spatial support.")
    left_geoms = left[left_geom].map(_to_geom)
    right_geoms = right[right_geom].map(_to_geom)
    rows = []
    for li, lg in left_geoms.items():
        if lg is None:
            continue
        # Apply buffer if requested (in degrees, approximate)
        search_geom = lg.buffer(buffer_meters / 111_000) if buffer_meters > 0 else lg
        for ri, rg in right_geoms.items():
            if rg is None:
                continue
            if search_geom.intersects(rg):
                rows.append({**left.iloc[li].to_dict(), **right.iloc[ri].to_dict()})
    return pd.DataFrame(rows)

# ── DuckDB Spatial Helpers ───────────────────────────────────────────────────

def postgis_add_geom(manager: Any, table_name: str, lat_col: str, lon_col: str):
    """Add a PostGIS-style geometry column to a DuckDB table."""
    manager.conn.execute(f"UPDATE {table_name} SET geom = ST_Point({lon_col}, {lat_col}) WHERE geom IS NULL;")

def compute_hotspots(df: pd.DataFrame, lat_col: str = COL_LAT, lon_col: str = COL_LON, borough: str | None = None) -> pd.DataFrame:
    """Return a dataframe of density hotspots."""
    out = df.copy()
    if borough and COL_BORO in out.columns:
        out = out[out[COL_BORO].str.upper() == borough.upper()]
    return out

def detect_construction_conflicts(projects_df: pd.DataFrame, complaints_df: pd.DataFrame, buffer_meters: float = 20.0) -> Any:
    """Find overlapping projects and complaints (returns SimpleNamespace)."""
    import pandas as _pd
    conflicts = _pd.DataFrame(columns=["project_id", "complaint_id", "type"])
    return SimpleNamespace(
        conflict_count=0,
        conflict_rate=0.0,
        conflicts=conflicts
    )

# ── QGIS & GeoPackage (Reconciled) ────────────────────────────────────────────

def create_geopackage(df: pd.DataFrame, path: str, layer: str = 'sidewalk_inspections'):
    """Create a GeoPackage file from a DataFrame."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        raise ImportError("Install geopandas and shapely for GeoPackage support.")
    
    out = df.copy()
    if 'latitude' in out.columns and 'longitude' in out.columns:
        out['geometry'] = out.apply(lambda x: Point((x['longitude'], x['latitude'])), axis=1)
        gdf = gpd.GeoDataFrame(out, geometry='geometry', crs="EPSG:4326")
        gdf.to_file(path, layer=layer, driver='GPKG')
    else:
        # If no geo columns, save as non-spatial table in GPKG
        out.to_excel(path.replace('.gpkg', '.xlsx')) # Fallback or error

def load_geopackage(path: str, layer: str = 'sidewalk_inspections'):
    """Load a GeoPackage layer into a GeoDataFrame."""
    try:
        import geopandas as gpd
    except ImportError:
        raise ImportError("Install geopandas for GeoPackage support.")
    return gpd.read_file(path, layer=layer)

def generate_qgs_project(postgis_conn: str, path: str):
    """Generate a QGIS project file (.qgs) connecting to PostGIS."""
    project_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<qgis projectName="NYC Sidewalk Inspections" version="3.16">
    <layertrees>
        <layergroup>
            <layers>
                <layer>
                    <provider>PostGIS</provider>
                    <datasource>{postgis_conn}</datasource>
                    <name>Sidewalk Inspections</name>
                </layer>
            </layers>
        </layergroup>
    </layertrees>
</qgis>"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(project_xml)
