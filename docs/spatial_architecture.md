# Spatial Architecture & PostGIS Integration

## Overview

The NYC DOT Sidewalk Toolkit uses **PostGIS** (PostgreSQL's spatial extension) as the geographic data foundation. This document describes the spatial data model, indexing strategy, and query patterns for sidewalk infrastructure analysis.

## Coordinate Systems

### Primary: WGS84 (SRID 4326)
- **Standard**: World Geodetic System 1984
- **Coverage**: Global, suitable for web mapping and GIS interoperability
- **NYC Center**: 40.7128°N, 74.0060°W
- **Bounds**: 40.4774°N to 40.9155°N, 74.2557°W to 73.7004°W
- **Usage**: All PostGIS tables, JSON APIs, map visualization

### Secondary: NAD83 NY Long Island (SRID 2263)
- **Standard**: North American Datum 1983, NY State Plane Coordinate System
- **Units**: Feet (US survey feet)
- **Usage**: Legacy NYC GIS data, City Planning Department references
- **Conversion**: `ST_Transform(geometry, 2263)` for NAD83

## Data Model

### Core Tables

#### `sidewalk_segments` (LineString)
Primary table for sidewalk infrastructure.

```sql
CREATE TABLE sidewalk_segments (
    segment_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(LINESTRING, 4326) NOT NULL,
    
    -- Computed: length in meters
    length_meters FLOAT GENERATED AS (ST_Length(geography(geometry)))
    
    -- Classification
    material_type VARCHAR(50),  -- asphalt, concrete, brick, stone, other
    condition_score FLOAT (0-100),  -- 0=poor, 100=excellent
    defects INT,
    
    -- Geographic hierarchy
    borough VARCHAR(50),
    block_id VARCHAR(50) REFERENCES blocks(block_id),
    district VARCHAR(50),
    council_district VARCHAR(50),
    
    -- Inspection metadata
    last_inspection TIMESTAMP,
    inspection_count INT
);
```

**Spatial Indexes:**
- `GiST` index on `geometry` (primary spatial index)
- `BRIN` index on `(last_inspection, geometry)` (time-series queries)
- `B-Tree` indexes on material_type, condition_score, borough

**Example Queries:**
```sql
-- Find segments within 50m of a point (NYC center)
SELECT segment_id, material_type, condition_score
FROM sidewalk_segments
WHERE ST_DWithin(
    geometry::geography,
    ST_GeomFromText('POINT(-74.0060 40.7128)', 4326)::geography,
    50
)
ORDER BY ST_Distance(geometry::geography, ...) ASC;

-- Segments in polygon (borough boundary)
SELECT segment_id, length_meters, condition_score
FROM sidewalk_segments
WHERE ST_Intersects(geometry, ST_GeomFromText('POLYGON(...))', 4326));

-- Aggregate length by material type
SELECT material_type,
       COUNT(*) as segment_count,
       SUM(length_meters) as total_length,
       AVG(condition_score) as avg_condition
FROM sidewalk_segments
GROUP BY material_type;
```

#### `blocks` (Polygon)
City blocks as geographic boundaries.

```sql
CREATE TABLE blocks (
    block_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    
    -- Computed: area in square meters
    area_square_meters FLOAT GENERATED AS (ST_Area(geography(geometry)))
    
    -- Geographic hierarchy
    borough VARCHAR(50),
    district VARCHAR(50),
    
    -- Coverage metrics
    total_segments INT,
    segments_with_data INT,
    coverage_percentage FLOAT
);
```

**Spatial Indexes:**
- `GiST` index on `geometry`

#### `inspections` (Point)
Point-based inspection records with timestamps.

```sql
CREATE TABLE inspections (
    inspection_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    
    segment_id VARCHAR(50) REFERENCES sidewalk_segments(segment_id),
    inspector_id VARCHAR(50),
    inspection_timestamp TIMESTAMP NOT NULL,
    
    -- Defect information
    defect_type VARCHAR(100),  -- pothole, crack, heave, etc.
    severity VARCHAR(20),  -- low, medium, high, critical
    condition_score INT (0-100),
    
    -- Field data
    gps_accuracy_meters FLOAT,
    photo_url TEXT
);
```

**Spatial Indexes:**
- `GiST` index on `geometry`
- `B-Tree` index on `inspection_timestamp`
- `B-Tree` index on `segment_id`

#### `material_zones` (MultiPolygon)
Aggregated areas of uniform material type.

```sql
CREATE TABLE material_zones (
    zone_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    
    material_type VARCHAR(50),
    area_square_meters FLOAT GENERATED AS (ST_Area(geography(geometry))),
    average_condition FLOAT,
    segment_count INT
);
```

#### `hotspots` (Point + Polygon)
Problem areas identified through spatial analysis.

```sql
CREATE TABLE hotspots (
    hotspot_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(POINT, 4326),  -- centroid
    affected_area_geom GEOMETRY(POLYGON, 4326),  -- buffer zone
    
    severity VARCHAR(20),  -- low, medium, high, critical
    density FLOAT,  -- segments or defects per unit area
    segment_count INT,
    detected_timestamp TIMESTAMP
);
```

## Indexing Strategy

### GiST (Generalized Search Tree)
**Best for:** Exact spatial operations (contains, intersects, distance)
```sql
CREATE INDEX idx_sidewalk_segments_geom 
    ON sidewalk_segments USING GIST(geometry)
    WITH (FILLFACTOR=70);
```

- Default spatial index type in PostGIS
- Excellent for range queries and nearest-neighbor
- Good for mixed query workloads

### BRIN (Block Range Index)
**Best for:** Time-series spatial data
```sql
CREATE INDEX idx_sidewalk_segments_brin 
    ON sidewalk_segments USING BRIN(last_inspection, geometry);
```

- More efficient for large tables (lower overhead)
- Good for sequential/temporal data
- Ideal for inspection timestamp + location queries

### B-Tree Indexes
**Best for:** Filtering and sorting
```sql
CREATE INDEX idx_sidewalk_segments_borough 
    ON sidewalk_segments(borough);

CREATE INDEX idx_sidewalk_segments_condition 
    ON sidewalk_segments(condition_score);
```

## Materialized Views for Performance

### By Borough Statistics
```sql
CREATE MATERIALIZED VIEW mv_segments_by_borough AS
SELECT borough,
       COUNT(*) as segment_count,
       SUM(length_meters) as total_length_meters,
       AVG(condition_score) as average_condition,
       COUNT(CASE WHEN last_inspection IS NOT NULL THEN 1 END) as inspected_count,
       ST_Union(geometry) as union_geometry
FROM sidewalk_segments
GROUP BY borough;
```

Refresh: Daily or after bulk inspections
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_segments_by_borough;
```

### Coverage by Block
```sql
CREATE MATERIALIZED VIEW mv_block_coverage AS
SELECT b.block_id, b.borough, b.geometry,
       COUNT(ss.segment_id) as segments_with_data,
       ROUND(100.0 * COUNT(ss.segment_id)::FLOAT / 
           NULLIF(b.total_segments, 0), 2) as coverage_percentage
FROM blocks b
LEFT JOIN sidewalk_segments ss ON ST_Intersects(b.geometry, ss.geometry)
GROUP BY b.block_id, b.geometry, b.borough;
```

## Spatial Functions

### Distance Queries
```python
# Find segments within distance of point
def find_nearby_segments(point: Point, distance_meters: float):
    results = query.find_nearby_segments(point, distance_meters)
    # Returns: segment_id, distance, material_type, condition_score, borough
```

**SQL Equivalent:**
```sql
SELECT segment_id, 
       ST_Distance(geometry::geography, point::geography) as distance_m,
       material_type, condition_score
FROM sidewalk_segments
WHERE ST_DWithin(geometry::geography, point::geography, ?)
ORDER BY distance_m;
```

### Intersection Queries
```python
# Find segments in polygon (e.g., block boundaries)
def find_segments_in_polygon(polygon: Polygon):
    results = query.find_segments_in_polygon(polygon)
    # Returns: list of segment IDs
```

**SQL Equivalent:**
```sql
SELECT segment_id
FROM sidewalk_segments
WHERE ST_Intersects(geometry, polygon);
```

### Aggregation Queries
```python
# Material distribution by borough
def material_distribution_stats(borough: str):
    results = query.segments_by_material()
```

**SQL Equivalent:**
```sql
SELECT material_type,
       COUNT(*) as count,
       SUM(length_meters) as total_length,
       AVG(condition_score) as avg_condition
FROM sidewalk_segments
WHERE borough = ?
GROUP BY material_type;
```

## Performance Tuning

### Query Optimization
1. **Use Geography type for distances > ~100km:**
   ```sql
   -- Accurate distance calculations
   ST_Distance(geometry::geography, other_geom::geography)
   ```

2. **Use GiST indexes for spatial operations:**
   ```sql
   -- Uses index for <= 500m queries
   WHERE ST_DWithin(geometry::geography, point::geography, 500)
   ```

3. **Cluster tables by geometry:**
   ```sql
   CLUSTER sidewalk_segments USING idx_sidewalk_segments_geom;
   ```

4. **Analyze frequently:**
   ```sql
   ANALYZE sidewalk_segments;
   ```

### Query Performance Targets
- **Proximity search (50m radius)**: < 100ms
- **Block intersection**: < 200ms
- **Borough aggregation**: < 500ms
- **City-wide aggregation**: < 1000ms

### Explain Plans
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) FROM sidewalk_segments
WHERE ST_DWithin(geometry::geography, 
                 ST_GeomFromText('POINT(...)'), 
                 50);
```

## Integration with Python

### Using Shapely + psycopg
```python
from shapely.geometry import Point, LineString
import psycopg

# Create geometry
point = Point(-74.0060, 40.7128)
line = LineString([(-74.01, 40.71), (-74.00, 40.72)])

# Store in database
segment = SpatialSegment(
    segment_id="seg001",
    geometry=SpatialGeometry(line, SRID_WGS84),
    material_type="asphalt",
    condition_score=75.0,
    borough="Manhattan"
)

db.insert_segment(segment)  # Saves to PostGIS

# Query nearby segments
results = query.find_nearby_segments(point, 50)
```

## Common Patterns

### Pattern 1: Proximity Analysis
Find all segments within service area of fire station:
```python
station_location = Point(-74.0060, 40.7128)
nearby = query.find_nearby_segments(station_location, 500)  # 500m
for segment in nearby:
    print(f"{segment.segment_id}: {segment.distance_meters:.1f}m away")
```

### Pattern 2: Material Distribution Mapping
Show which materials are where:
```python
materials = query.find_material_zones("asphalt", borough="Manhattan")
for zone in materials:
    print(f"{zone.district}: {zone.total_length_meters:.0f}m of asphalt")
```

### Pattern 3: Hotspot Detection
Find problem areas:
```python
hotspots = analyzer.detect_hotspots(
    coordinates=segment_coords,
    values=condition_scores,
    threshold=60.0  # Areas with avg condition < 60
)
for hotspot in hotspots:
    print(f"Problem area at {hotspot.centroid_x}, {hotspot.centroid_y}")
    print(f"  Severity: {hotspot.severity}")
    print(f"  Affected segments: {hotspot.segment_count}")
```

### Pattern 4: Time-Series Spatial
Show inspection trend by location:
```python
recent_inspections = query.db.get_connection()
query.execute("""
    SELECT segment_id, condition_score, last_inspection
    FROM sidewalk_segments
    WHERE ST_Intersects(geometry, block_polygon)
    AND last_inspection > NOW() - INTERVAL '30 days'
    ORDER BY last_inspection DESC
""")
```

## Migration Path

1. **Setup PostGIS:**
   ```bash
   psql -d sidewalk_db -c "CREATE EXTENSION postgis;"
   ```

2. **Run migration:**
   ```bash
   psql -d sidewalk_db -f sql/010_postgis_schema.sql
   ```

3. **Import existing data:**
   ```python
   from socrata_toolkit.spatial_database import SpatialDatabaseConnection
   
   db = SpatialDatabaseConnection(
       host="localhost",
       port=5432,
       database="sidewalk_db",
       user="postgres",
       password="..."
   )
   
   # Import segments from existing data
   for segment_data in old_segments:
       segment = create_spatial_segment(segment_data)
       db.insert_segment(segment)
   ```

4. **Verify spatial integrity:**
   ```sql
   SELECT COUNT(*) FROM sidewalk_segments 
   WHERE NOT ST_IsValid(geometry);  -- Should be 0
   ```

## Troubleshooting

### Issue: Queries running slow
**Solution:**
1. Check indexes exist: `\d sidewalk_segments`
2. Analyze table: `ANALYZE sidewalk_segments;`
3. Check explain plan: `EXPLAIN (ANALYZE) SELECT ...`

### Issue: Invalid geometries
**Solution:**
```sql
-- Find invalid geometries
SELECT segment_id FROM sidewalk_segments 
WHERE NOT ST_IsValid(geometry);

-- Fix with ST_MakeValid
UPDATE sidewalk_segments 
SET geometry = ST_MakeValid(geometry) 
WHERE NOT ST_IsValid(geometry);
```

### Issue: Coordinate system mismatch
**Solution:**
```sql
-- Check SRID
SELECT DISTINCT ST_SRID(geometry) FROM sidewalk_segments;

-- Transform if needed
UPDATE sidewalk_segments 
SET geometry = ST_Transform(geometry, 4326)
WHERE ST_SRID(geometry) != 4326;
```

## Resources

- **PostGIS Documentation:** https://postgis.net/docs/
- **Shapely Documentation:** https://shapely.readthedocs.io/
- **NYC Geographic Data:** https://opendata.cityofnewyork.us/
- **QGIS Documentation:** https://qgis.org/docs/

## Further Reading

- [NYC Coordinate Systems Guide](https://www1.nyc.gov/site/planning/index.page)
- [PostGIS Performance Tips](https://postgis.net/docs/performance-tips.html)
- [Spatial Indexing Strategies](https://en.wikipedia.org/wiki/Spatial_index)
