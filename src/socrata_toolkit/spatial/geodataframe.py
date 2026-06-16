"""
GeoPandas integration for Socrata datasets.

Converts the_geom WKT/GeoJSON columns from Socrata API responses into
GeoDataFrames for spatial analysis, joins, and export.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    from shapely.geometry import shape as shapely_shape
    from shapely.wkt import loads as load_wkt

    HAS_GEOPANDAS = True
except ImportError:
    gpd = None  # type: ignore[assignment]
    shapely_shape = None
    load_wkt = None
    HAS_GEOPANDAS = False

def _parse_geom_value(val: Any):
    """Parse a single the_geom value — WKT string, GeoJSON dict, or JSON string."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        # Try WKT (POINT(...), MULTIPOLYGON(...), etc.)
        if any(
            val.upper().startswith(t)
            for t in ("POINT", "LINESTRING", "POLYGON", "MULTI", "GEOMETRYCOLLECTION")
        ):
            try:
                return load_wkt(val)
            except Exception:
                pass
        # Try JSON-encoded GeoJSON
        try:
            obj = json.loads(val)
            if isinstance(obj, dict) and "type" in obj and "coordinates" in obj:
                return shapely_shape(obj)
        except Exception:
            pass
        return None
    if isinstance(val, dict) and "type" in val and "coordinates" in val:
        try:
            return shapely_shape(val)
        except Exception:
            return None
    return None

def geodataframe_from_socrata(
    df: pd.DataFrame,
    geom_col: str = "the_geom",
    crs: str = "EPSG:4326",
    drop_null_geom: bool = True,
) -> gpd.GeoDataFrame:
    """Convert a Socrata DataFrame with a geometry column to a GeoDataFrame.

    Args:
        df: DataFrame from fetch_dataset(), expected to contain geom_col.
        geom_col: Name of the geometry column (default: 'the_geom').
        crs: Coordinate reference system (default WGS84 EPSG:4326).
        drop_null_geom: Whether to drop rows with unparseable geometry.

    Returns:
        GeoDataFrame with parsed geometry.

    Raises:
        ImportError: if geopandas or shapely are not installed.
        KeyError: if geom_col is not in df.columns.
    """
    if not HAS_GEOPANDAS:
        raise ImportError(
            "geopandas and shapely are required. "
            "Install with: pip install geopandas shapely"
        )
    if geom_col not in df.columns:
        raise KeyError(f"Column '{geom_col}' not found. Available: {list(df.columns)}")

    df = df.copy()
    geoms = df[geom_col].map(_parse_geom_value)
    null_count = geoms.isna().sum()
    if null_count:
        logger.debug("geodataframe_from_socrata: %d rows had unparseable geometry", null_count)

    gdf = gpd.GeoDataFrame(df, geometry=geoms, crs=crs)
    if drop_null_geom:
        gdf = gdf[gdf.geometry.notna()].reset_index(drop=True)
    return gdf

def spatial_join_socrata(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    left_geom_col: str = "the_geom",
    right_geom_col: str = "the_geom",
    how: str = "inner",
    predicate: str = "intersects",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """Spatial join between two Socrata DataFrames via GeoPandas.

    Args:
        left_df, right_df: DataFrames from fetch_dataset().
        left_geom_col, right_geom_col: geometry column names.
        how: join type ('inner', 'left', 'right').
        predicate: spatial predicate ('intersects', 'within', 'contains').
        crs: coordinate reference system.

    Returns:
        Joined GeoDataFrame.
    """
    if not HAS_GEOPANDAS:
        raise ImportError("geopandas is required for spatial joins.")

    left_gdf = geodataframe_from_socrata(left_df, geom_col=left_geom_col, crs=crs)
    right_gdf = geodataframe_from_socrata(right_df, geom_col=right_geom_col, crs=crs)
    return gpd.sjoin(left_gdf, right_gdf, how=how, predicate=predicate)

def detect_conflicts_geopandas(
    inspections: pd.DataFrame,
    permits: pd.DataFrame,
    *,
    buffer_meters: float = 50.0,
    insp_geom_col: str = "the_geom",
    perm_geom_col: str = "the_geom",
) -> gpd.GeoDataFrame:
    """Find inspection locations that spatially overlap active permit areas.

    Reprojects to EPSG:2263 (NY State Plane, feet) for metric buffering,
    then back to WGS84 for output.

    Args:
        inspections: Inspection DataFrame with geometry.
        permits: Permits DataFrame with geometry.
        buffer_meters: Buffer radius in meters around each inspection point.
        insp_geom_col, perm_geom_col: geometry column names.

    Returns:
        GeoDataFrame of conflicting pairs.
    """
    if not HAS_GEOPANDAS:
        raise ImportError("geopandas is required.")

    insp_gdf = geodataframe_from_socrata(inspections, geom_col=insp_geom_col)
    perm_gdf = geodataframe_from_socrata(permits, geom_col=perm_geom_col)

    # Project to metric CRS for buffering
    insp_proj = insp_gdf.to_crs("EPSG:2263")
    # Buffer in feet (1 meter ≈ 3.28084 feet)
    buffer_ft = buffer_meters * 3.28084
    insp_proj["geometry"] = insp_proj.geometry.buffer(buffer_ft)

    perm_proj = perm_gdf.to_crs("EPSG:2263")
    conflicts = gpd.sjoin(insp_proj, perm_proj, how="inner", predicate="intersects")
    return conflicts.to_crs("EPSG:4326")

def to_geojson(gdf: gpd.GeoDataFrame) -> str:
    """Serialize a GeoDataFrame to a GeoJSON string."""
    if not HAS_GEOPANDAS:
        raise ImportError("geopandas is required.")
    return gdf.to_json()

def to_wkt_column(gdf: gpd.GeoDataFrame, geom_col: str = "geometry") -> pd.Series:
    """Return a WKT string Series from the GeoDataFrame geometry column."""
    if not HAS_GEOPANDAS:
        raise ImportError("geopandas is required.")
    return gdf[geom_col].apply(lambda g: g.wkt if g is not None else None)

def spatial_stats(gdf) -> dict:
    """Compute summary spatial statistics for a GeoDataFrame.

    Args:
        gdf: A GeoDataFrame to summarise.

    Returns:
        Dict with total_features, geometry_types, bounds, crs, and
        optionally total_area_sq_deg when Polygon geometries are present.

    Raises:
        ImportError: if geopandas is not installed.
    """
    if not HAS_GEOPANDAS:
        raise ImportError("geopandas required")
    stats: dict = {
        "total_features": len(gdf),
        "geometry_types": gdf.geometry.geom_type.value_counts().to_dict(),
        "bounds": gdf.total_bounds.tolist(),  # [minx, miny, maxx, maxy]
        "crs": str(gdf.crs),
    }
    if any(gdf.geometry.geom_type == "Polygon"):
        polys = gdf[gdf.geometry.geom_type == "Polygon"]
        stats["total_area_sq_deg"] = float(polys.geometry.area.sum())
    return stats
