# ArcGIS Integration Guide

## Overview

The NYC DOT Socrata Toolkit integrates seamlessly with ArcGIS Online and ArcGIS Enterprise for:
- Querying authoritative NYC reference data (streets, districts, zones)
- Publishing sidewalk data as feature services
- Synchronizing data with city-wide GIS systems
- Accessing symbology and styling from ArcGIS

## Authentication

### Setup Credentials

```python
from socrata_toolkit.arcgis_integration import ArcGISConnector, ArcGISCredential

# Create credentials for NYC ArcGIS Online
credential = ArcGISCredential(
    username="your_username",
    password="your_password",
    organization_url="https://nyc.maps.arcgisonline.com"
)

# Initialize connector
connector = ArcGISConnector(credential)

# Authenticate
if connector.authenticate():
    print("Connected to ArcGIS")
else:
    print("Authentication failed")
```

### Token Management

Tokens expire after 60 minutes by default. The connector automatically:
- Refreshes tokens when needed
- Tracks expiration time
- Validates before each request

```python
# Check token status
if connector.token_expires:
    time_until_expiry = connector.token_expires - datetime.utcnow()
    print(f"Token expires in {time_until_expiry.seconds} seconds")
```

## Querying Feature Services

### Query NYC Reference Data

```python
# Query NYC street centerlines from authoritative source
streets = connector.query_feature_service(
    service_url="https://services.arcgisonline.com/ArcGIS/rest/services/NYC_Streets/FeatureServer",
    layer_id=0,
    where_clause="borough='Manhattan'",
    return_geometry=True,
    out_sr=4326,
    limit=10000
)

print(f"Retrieved {len(streets)} streets")
for street in streets:
    print(f"  {street['properties']['name']}")
```

### Get Service Metadata

```python
# Inspect feature service structure
metadata = connector.get_service_metadata(
    service_url="https://services.arcgisonline.com/ArcGIS/rest/services/NYC_Districts/FeatureServer",
    layer_id=0
)

print(f"Service: {metadata.name}")
print(f"Type: {metadata.geometry_type}")
print(f"Fields: {list(metadata.fields.keys())}")
print(f"Records: {metadata.record_count}")
```

## Importing Data from ArcGIS

### Import Feature Service

```python
# Import council districts from ArcGIS
result = connector.import_feature_service(
    service_url="https://services.arcgisonline.com/ArcGIS/rest/services/NYC_CouncilDistricts/FeatureServer",
    layer_id=0,
    geometry_filter=aoi_polygon  # Optional: filter to area of interest
)

features = result['features']
metadata = result['metadata']

print(f"Imported {result['count']} districts")

# Store in local PostGIS
for feature in features:
    geom = feature['geometry']
    props = feature['properties']
    
    block = SpatialBlock(
        block_id=props['OBJECTID'],
        geometry=SpatialGeometry(shape(geom), SRID_WGS84),
        borough=props.get('BOROUGH'),
        district=props.get('DISTRICT')
    )
    db.insert_block(block)
```

### Filter by Geometry

```python
# Import only features in specific area
manhattan_bounds = Polygon([
    (-74.0270, 40.7067),
    (-73.9270, 40.7067),
    (-73.9270, 40.8167),
    (-74.0270, 40.8167),
    (-74.0270, 40.7067)
])

result = connector.import_feature_service(
    service_url="...",
    geometry_filter=manhattan_bounds
)
```

## Exporting to ArcGIS

### Publish Sidewalk Data as Feature Service

```python
# Prepare sidewalk segments for export
features = []
for segment in all_segments:
    feature = {
        "geometry": mapping(segment.geometry.geometry),
        "properties": {
            "segment_id": segment.segment_id,
            "material_type": segment.material_type,
            "condition_score": segment.condition_score,
            "borough": segment.borough,
            "last_inspection": segment.last_inspection.isoformat() if segment.last_inspection else None,
        }
    }
    features.append(feature)

# Export to ArcGIS feature service
result = connector.export_to_arcgis(
    features=features,
    target_service_url="https://services.arcgisonline.com/ArcGIS/rest/services/DOT_Sidewalks/FeatureServer",
    target_layer_id=0,
    mode="append"  # or "replace"
)

print(f"Exported {result['success_count']}/{result['total']} features")
if result['failed_count'] > 0:
    print(f"Failed: {result['failed_count']}")
```

## Synchronizing Data

### One-Way Sync (Export)

```python
# Regular sync to keep ArcGIS updated
from datetime import datetime, timedelta

def sync_updated_segments():
    # Get segments updated since last sync
    last_sync = datetime.utcnow() - timedelta(hours=24)
    updated = query.get_segments_modified_since(last_sync)
    
    # Convert to GeoJSON features
    features = [segment_to_geojson(s) for s in updated]
    
    # Sync to ArcGIS
    result = connector.sync_layer(
        local_features=features,
        service_url="...",
        sync_mode="append"
    )
    
    return result

result = sync_updated_segments()
print(f"Synced {result['success_count']} segments")
```

### Two-Way Sync (Update)

```python
# Replace entire layer (for full dataset updates)
all_segments = query.get_all_segments()
features = [segment_to_geojson(s) for s in all_segments]

result = connector.sync_layer(
    local_features=features,
    service_url="...",
    sync_mode="replace"  # Delete all, add new
)

print(f"Replaced {result['total']} segments in ArcGIS")
```

## Accessing Authoritative Reference Data

### NYC Street Centerlines

```python
# Get authoritative street network
streets = connector.get_authoritative_data(
    dataset_name="streets",
    bounds={
        "xmin": -74.01,
        "ymin": 40.71,
        "xmax": -74.00,
        "ymax": 40.72
    }
)

print(f"Retrieved {len(streets)} streets")
```

### City Blocks/Lots

```python
# Get block boundaries
blocks = connector.get_authoritative_data(
    dataset_name="blocks"
)
```

### Council Districts

```python
# Get political district boundaries
districts = connector.get_authoritative_data(
    dataset_name="districts"
)

for district in districts:
    print(f"District {district['properties']['number']}")
```

## Publishing Maps

### Create Web Map

```python
# Create web map with sidewalk condition layer
map_data = {
    "baseMap": {
        "baseMapLayers": [
            {
                "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer",
                "layerType": "ArcGISTiledMapServiceLayer",
                "visibility": True,
                "opacity": 1
            }
        ]
    },
    "operationalLayers": [
        {
            "url": "https://services.arcgisonline.com/ArcGIS/rest/services/DOT_Sidewalks/FeatureServer/0",
            "title": "Sidewalk Condition",
            "opacity": 0.8,
            "visibility": True
        }
    ],
    "version": "3.24"
}

# Publish to ArcGIS Online
success = connector.publish_map(
    map_data=map_data,
    map_title="NYC DOT Sidewalk Condition Map",
    map_description="Real-time sidewalk condition assessment"
)

if success:
    print("Map published to ArcGIS Online")
```

## Error Handling

### Handle Network Errors

```python
try:
    result = connector.import_feature_service(service_url)
except requests.exceptions.ConnectionError:
    print("Cannot connect to ArcGIS")
    # Fallback to cached data
    result = load_cached_data()
except requests.exceptions.Timeout:
    print("ArcGIS request timed out")
    # Retry with longer timeout
    result = connector.import_feature_service(service_url, timeout=120)
```

### Handle Authentication Errors

```python
if not connector.authenticate():
    print("Invalid credentials")
    # Check token validity
    if connector.token:
        print(f"Token valid until {connector.token_expires}")
    else:
        print("No token available - authentication failed")
```

## Performance Tips

### Pagination for Large Datasets

```python
# Query in chunks to manage memory
page_size = 1000
all_features = []

for page in range(0, total_count, page_size):
    features = connector.query_feature_service(
        service_url=...,
        limit=page_size,
        # Note: ArcGIS uses resultOffset for pagination
    )
    all_features.extend(features)
    print(f"Retrieved {len(all_features)}/{total_count}")
```

### Batch Operations

```python
# Export in batches to avoid timeouts
batch_size = 5000

for i in range(0, len(all_segments), batch_size):
    batch = all_segments[i:i+batch_size]
    features = [segment_to_geojson(s) for s in batch]
    
    result = connector.export_to_arcgis(
        features=features,
        target_service_url=...,
        mode="append"
    )
    
    print(f"Exported batch {i//batch_size + 1}")
```

## Integration with Spatial Workflow

```python
from socrata_toolkit.arcgis_integration import ArcGISConnector, ArcGISCredential
from socrata_toolkit.spatial_queries import SpatialQuery
from socrata_toolkit.spatial_visualization import SpatialVisualization

# Setup
credential = ArcGISCredential(username="...", password="...", organization_url="...")
connector = ArcGISConnector(credential)
query = SpatialQuery(db_connection)
viz = SpatialVisualization()

# 1. Import reference data from ArcGIS
blocks = connector.import_feature_service("NYC_Blocks_FeatureServer")

# 2. Local analysis
hotspots = analyzer.detect_hotspots(segment_coords, condition_scores)

# 3. Visualize locally
map_obj = viz.create_hotspot_map(hotspots)

# 4. Export results to ArcGIS
hotspot_features = [hotspot_to_feature(h) for h in hotspots]
connector.export_to_arcgis(hotspot_features, "DOT_Hotspots_FeatureServer")

# 5. Publish map
success = connector.publish_map(map_data, "Sidewalk Hotspots")
```

## Health Check

```python
# Verify ArcGIS connectivity
if connector.health_check():
    print("ArcGIS service is accessible")
    print(f"Organization: {connector.credential.organization_url}")
else:
    print("Cannot reach ArcGIS service")
```

## Troubleshooting

### Issue: "Invalid token" error
**Solution:** Re-authenticate
```python
connector.token = None
connector.authenticate()
```

### Issue: "Layer not found" error
**Solution:** Verify layer ID
```python
metadata = connector.get_service_metadata(service_url, layer_id=0)
print(f"Available layers: {metadata.layer_count}")
```

### Issue: Export timeout
**Solution:** Use smaller batches
```python
# Instead of exporting all at once
result = connector.export_to_arcgis(features_batch, ..., mode="append")
```

## References

- ArcGIS REST API: https://resources.arcgis.com/en/help/arcgis-rest-api/
- ArcGIS Online: https://www.arcgis.com/home/
- Feature Services: https://developers.arcgis.com/rest/services-reference/feature-service/
