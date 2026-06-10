# Spatial Analytics Guide

## Overview

The spatial analytics module provides advanced geographic analysis capabilities for sidewalk infrastructure:
- Network routing and service area analysis
- Hotspot detection and clustering
- Spatial interpolation
- Anomaly detection

## Network Analysis

### Building Street Networks

```python
from socrata_toolkit.spatial_analytics import NetworkAnalysis

network = NetworkAnalysis()

streets = [
    {
        "id": "st1",
        "coordinates": [[-74.01, 40.71], [-74.00, 40.71]],
        "length": 150,
    },
    # ... more streets
]

stats = network.build_network(streets)
print(f"Network: {stats['nodes']} nodes, {stats['edges']} edges")
```

### Finding Shortest Routes

```python
# Find efficient inspection route between two segments
path = network.find_shortest_route(
    start_node_id="st1_start",
    end_node_id="st3_end"
)

print(f"Route: {path}")
# Output: ['st1_start', 'st2_start', 'st2_end', 'st3_start', 'st3_end']
```

### Service Area Analysis

```python
# Find all segments reachable within 500m walk distance
reachable = network.compute_service_areas(
    center_x=-74.0060,
    center_y=40.7128,
    walk_distance_meters=500
)

print(f"Reachable segments: {len(reachable)}")
```

## Hotspot Detection

### Kernel Density Estimation

```python
from socrata_toolkit.spatial_analytics import HotspotAnalysis

analyzer = HotspotAnalysis()

# Analyze condition score distribution
points = [(-74.006, 40.713), (-74.007, 40.714), (-74.008, 40.715)]
condition_scores = [45, 38, 42]

density_result = analyzer.kernel_density(
    points=points,
    values=condition_scores,
    bandwidth=0.01,
    grid_size=50
)

print(f"Highest density: {density_result['max_density']:.2f}")
print(f"Density grid: {len(density_result['density_grid'])} cells")
```

### Clustering Analysis

```python
# Identify groups of similar-condition segments
clusters = analyzer.cluster_segments(
    coordinates=segment_coords,
    values=condition_scores,
    segment_ids=segment_ids,
    method="dbscan",  # or "kmeans"
    eps=0.01,  # Max distance between points in cluster
    min_samples=5
)

for cluster in clusters:
    print(f"Cluster {cluster.cluster_id}:")
    print(f"  Size: {cluster.size} segments")
    print(f"  Center: ({cluster.centroid_x}, {cluster.centroid_y})")
    print(f"  Avg condition: {cluster.average_value:.1f}")
```

### Detecting Problem Areas (Hotspots)

```python
# Automatically find areas needing urgent attention
hotspots = analyzer.detect_hotspots(
    coordinates=segment_coords,
    values=condition_scores,
    threshold=60.0,  # Areas with avg condition < 60
    radius_degrees=0.01  # ~1km
)

for hotspot in hotspots:
    print(f"Hotspot at ({hotspot.centroid_x}, {hotspot.centroid_y})")
    print(f"  Severity: {hotspot.severity}")
    print(f"  Density: {hotspot.density:.2f} segments/km²")
    print(f"  Affected segments: {hotspot.segment_count}")
```

## Spatial Interpolation

### Inverse Distance Weighting (IDW)

```python
from socrata_toolkit.spatial_analytics import InterpolationAnalysis

interpolator = InterpolationAnalysis()

# Estimate condition scores at unsampled locations
known_points = [
    (-74.006, 40.713),  # Known survey points
    (-74.007, 40.714),
    (-74.008, 40.715),
]
known_values = [80, 65, 45]  # Observed condition scores

# Estimate condition at new location
query_points = [(-74.0065, 40.7135)]

estimated = interpolator.inverse_distance_weighted(
    known_points=known_points,
    known_values=known_values,
    query_points=query_points,
    power=2.0  # IDW power parameter
)

print(f"Estimated condition: {estimated[0]:.1f}")
```

## Anomaly Detection

### Statistical Outliers

```python
from socrata_toolkit.spatial_analytics import SpatialAnomalyDetector

detector = SpatialAnomalyDetector()

# Find unusual condition scores using z-score
outlier_indices = detector.detect_outliers(
    coordinates=segment_coords,
    values=condition_scores,
    method="zscore",
    threshold=2.5  # 2.5 standard deviations
)

for idx in outlier_indices:
    print(f"Outlier: {segment_ids[idx]} with score {condition_scores[idx]}")
```

### Spatial Outliers (Local Outlier Factor)

```python
# Find segments with unusual values compared to neighbors
spatial_outliers = detector.detect_spatial_outliers(
    coordinates=segment_coords,
    values=condition_scores,
    k=5,  # Compare to 5 nearest neighbors
    std_threshold=2.0
)

for idx in spatial_outliers:
    print(f"Spatial outlier: {segment_ids[idx]}")
    print(f"  Value differs significantly from neighbors")
```

## Use Cases

### Use Case 1: Prioritize Maintenance Routes

```python
# Find worst areas and route inspectors efficiently
hotspots = analyzer.detect_hotspots(coords, scores, threshold=50)

# Sort by severity
urgent_hotspots = sorted(
    hotspots,
    key=lambda h: h.severity,
    reverse=True
)

# Route between hotspots
route = network.find_shortest_route(
    start=urgent_hotspots[0].centroid,
    end=urgent_hotspots[-1].centroid
)

print(f"Optimized inspection route: {route}")
```

### Use Case 2: Material Distribution Analysis

```python
# Understand where different materials are
asphalt_segments = query.find_material_zones("asphalt", borough="Manhattan")

for zone in asphalt_segments:
    # Interpolate condition where unsampled
    if zone.avg_condition is None:
        estimated_condition = interpolator.inverse_distance_weighted(
            known_segments,
            known_conditions,
            [zone.centroid]
        )
        print(f"Estimated condition for zone: {estimated_condition[0]:.1f}")
```

### Use Case 3: Coverage Gap Analysis

```python
# Find areas with no inspection data
all_blocks = query.get_all_blocks(borough="Brooklyn")

for block in all_blocks:
    segments = query.find_segments_in_polygon(block.geometry)
    
    if len(segments) == 0:
        print(f"Coverage gap: Block {block.block_id} has no data")
    elif all(s.last_inspection is None for s in segments):
        print(f"Data gap: Block {block.block_id} never inspected")
```

## Performance Considerations

### Large Dataset Handling

For city-wide analysis with millions of points:

```python
# Process in geographic tiles to manage memory
tiles = create_grid_tiles(nyc_bounds, tile_size=0.01)  # 1km tiles

for tile in tiles:
    tile_segments = query.find_segments_in_polygon(tile)
    tile_hotspots = analyzer.detect_hotspots(
        tile_segments.coords,
        tile_segments.values
    )
    # Process and store results incrementally
```

### Caching Results

```python
# Cache hotspot analysis results
hotspots_cache = {}

def get_hotspots(borough, force_refresh=False):
    if borough in hotspots_cache and not force_refresh:
        return hotspots_cache[borough]
    
    hotspots = analyzer.detect_hotspots(
        borough_coords[borough],
        borough_conditions[borough]
    )
    hotspots_cache[borough] = hotspots
    return hotspots
```

## Integration with Metrics

```python
from socrata_toolkit.spatial_metrics import SpatialMetricsCollector

collector = SpatialMetricsCollector()

# Get official metrics
coverage = collector.calculate_coverage_by_borough()
sla_compliance = collector.calculate_sla_compliance(sla_def)

# Enhance with analytics
for metric in coverage:
    hotspots = analyzer.detect_hotspots(
        metric.borough_coords,
        metric.borough_conditions
    )
    metric.hotspot_count = len(hotspots)
    metric.critical_area = [h for h in hotspots if h.severity == "critical"]
```

## References

- Kernel Density Estimation: https://en.wikipedia.org/wiki/Kernel_density_estimation
- Clustering (DBSCAN, KMeans): https://scikit-learn.org/stable/modules/clustering.html
- Spatial Interpolation: https://en.wikipedia.org/wiki/Spatial_interpolation
- Network Analysis: https://en.wikipedia.org/wiki/Network_analysis
