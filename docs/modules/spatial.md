# `socrata_toolkit.spatial` — Spatial Analysis

**File:** `socrata_toolkit/spatial.py` | **Pillar:** Spatial  
**Dependencies:** `pandas`, `shapely` (optional), `scikit-learn` (optional for clustering)

---

> [!NOTE]
> `shapely` is optional. Install with `pip install ".[geo]"`. Functions that require it will raise `ImportError` gracefully if unavailable.

---

## `SpatialIndex`
Minimal in-memory spatial index for point-in-polygon queries.

```python
from socrata_toolkit.spatial import SpatialIndex

idx = SpatialIndex()
idx.index(geojson_feature_collection["features"])

# Find features containing point (lat, lon)
matches = idx.query_point(40.7128, -74.0060)
```

| Method | Description |
|--------|-------------|
| `index(features)` | Load GeoJSON features into the index |
| `query_point(lat, lon)` | Return all features whose geometry contains the point |

Requires `shapely`.

---

## `cluster_locations(df, lat_col, lon_col, n_clusters=5) → pd.DataFrame`
KMeans clustering of geographic points. Adds a `cluster` integer column.

```python
from socrata_toolkit import cluster_locations

clustered = cluster_locations(df, lat_col="latitude", lon_col="longitude", n_clusters=8)
print(clustered["cluster"].value_counts())
```

Requires `scikit-learn`. Falls back gracefully (returns `df` unchanged) if not installed.

---

## `spatial_intersects_join(left, right, left_geom, right_geom, buffer_meters=0.0) → pd.DataFrame`
Spatial intersection join between two DataFrames. Supports WKT strings, GeoJSON dicts, or Shapely objects in the geometry columns.

```python
from socrata_toolkit import spatial_intersects_join

joined = spatial_intersects_join(
    left=projects_df,
    right=complaints_df,
    left_geom="project_geometry",
    right_geom="complaint_location",
    buffer_meters=50.0   # expand project geometry by 50m before intersect
)
```

- `left_geom` / `right_geom`: Column names containing geometry (GeoJSON dict, WKT string, or Shapely object)
- `buffer_meters`: Optional expansion of left geometry (approximate — uses degree conversion 1° ≈ 111km)
- Returns a flat DataFrame merging both rows for each intersection

Requires `shapely`.

---

## `detect_construction_conflicts(projects_df, complaints_df, buffer_meters=20.0) → SimpleNamespace`
Find overlapping construction projects and 311 complaints within a spatial buffer.

```python
from socrata_toolkit import detect_construction_conflicts

result = detect_construction_conflicts(
    projects_df=projects,
    complaints_df=complaints,
    buffer_meters=20.0
)
print(result.conflict_count)
print(result.conflict_rate)   # fraction of projects with conflicts
result.conflicts              # DataFrame with (project_id, complaint_id, type)
```

Returns: `{conflict_count, conflict_rate, conflicts: pd.DataFrame}`

---

## `compute_hotspots(df, lat_col, lon_col, borough=None) → pd.DataFrame`
Filter a DataFrame to a specific borough for hotspot analysis.

```python
from socrata_toolkit.spatial import compute_hotspots

bk_hotspots = compute_hotspots(df, lat_col="latitude", lon_col="longitude",
                                borough="BROOKLYN")
```

---

## `postgis_add_geom(manager, table_name, lat_col, lon_col)`
Add a PostGIS-compatible geometry point column to a DuckDB table using the spatial extension.

```python
from socrata_toolkit.spatial import postgis_add_geom
from socrata_toolkit.core import DuckDBManager

mgr = DuckDBManager("nyc.db")
postgis_add_geom(mgr, "complaints", lat_col="latitude", lon_col="longitude")
```

Executes: `UPDATE {table} SET geom = ST_Point(lon, lat) WHERE geom IS NULL`

---

## `SpatialVisualization`
Placeholder class for future Folium/Plotly Express mapping helpers.

```python
viz = SpatialVisualization(df)
viz.plot_heatmap("latitude", "longitude")  # stub — extend as needed
```
