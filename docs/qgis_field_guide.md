# QGIS Field Guide for Sidewalk Inspectors

## Overview

QGIS is the desktop GIS software used by field inspection teams. This guide covers:
- Creating offline field packages
- Conducting inspections with QGIS
- Syncing data back to the server
- Managing GeoPackage files

## Field Package Creation

### Generate Field Package for Area

```python
from socrata_toolkit.mobile_gis import FieldPackageBuilder

# Create package for specific area
builder = FieldPackageBuilder(
    inspector_id="inspector_john_123",
    area_of_interest={
        "minx": -74.01,
        "miny": 40.71,
        "maxx": -74.00,
        "maxy": 40.72
    }
)

# Get segments and blocks for area
segments = query.find_segments_in_polygon(aoi_polygon)
blocks = query.find_blocks_in_polygon(aoi_polygon)

# Create package
package_path = builder.create_package(
    segments=segments,
    blocks=blocks,
    output_dir="./field_packages"
)

print(f"Field package created: {package_path}")
# Output: field_packages/sidewalk_inspection_inspector_john_123_20260510_143000.gpkg
```

### What's in a Field Package

The GeoPackage contains:
- **segments layer**: All sidewalk segments in area with attributes
- **blocks layer**: Block boundaries for reference
- **field_metadata table**: Help text for each field
- **symbology**: Pre-configured styling rules for visualization

### Advanced: Direct GeoPackageBuilder API

For custom GeoPackage creation, you can use the lower-level `GeoPackageBuilder` API directly. This provides fine-grained control over layers and metadata.

```python
from socrata_toolkit.qgis_compatibility import GeoPackageBuilder

# Initialize builder
builder = GeoPackageBuilder("custom_inspection.gpkg")
builder.create_empty_geopackage()

# Add custom layers with specific properties and styling
builder.add_layer(
    layer_name="segments",
    features=segment_features,
    geometry_type="LineString",
    properties={
        "segment_id": "string",
        "material_type": "string",
        "condition_score": "number",
        "defects": "integer",
        "last_inspection": "datetime"
    },
    styles={
        "type": "simple",
        "symbols": [{
            "type": "line",
            "color": [0, 0, 0, 255],
            "width": 1.5
        }]
    }
)

# Add field help text for inspectors
builder.add_field_metadata(
    "segments",
    {
        "condition_score": "Rate overall condition 0-100",
        "material_type": "Predominant surface material",
        "defects": "Number of defects observed"
    }
)

# Finalize the GeoPackage
builder.finalize()
```

For complete API documentation, see [`docs/geospatial.md#geopackage-builder-api`](geospatial.md#geopackage-builder-api).

## Opening in QGIS

### Step 1: Launch QGIS
```bash
qgis ~/field_packages/sidewalk_inspection_inspector_john_123_20260510_143000.gpkg
```

### Step 2: Enable Offline Editing
1. Go to `Plugins` → `Offline Editing` → `Create an Offline Project`
2. Select all layers
3. Offline editing is now active - you can edit without internet

### Step 3: Configure Layer Styles
- Segments are color-coded by condition score
- Hover over a segment to see details
- Right-click for field form

## Conducting Inspections

### Recording Segment Condition

1. Click on a sidewalk segment to open the attribute form
2. Fill in fields:
   - **condition_score** (0-100): Rate overall condition
   - **material_type**: Confirm or correct material
   - **defects**: Number of defects observed
   - **notes**: Any observations

3. Click "Save"

### Adding Photos

1. In the attribute form, click "Add Photo"
2. Take photo with device camera
3. Photo automatically geotagged with GPS location
4. Photo link saved in GeoPackage

### Recording GPS Location

During inspection:
1. Enable GPS (usually on by default in QGIS mobile)
2. Position tracking shows current location on map
3. Current accuracy shown (usually 5-10 meters)

## Field Session Workflow

### Start Session

```python
from socrata_toolkit.mobile_gis import FieldSession
from datetime import datetime

session = FieldSession(
    session_id="session_20260510_001",
    inspector_id="inspector_john_123",
    area_name="Chelsea Block A",
    geopackage_path="sidewalk_inspection_20260510_143000.gpkg"
)

print(f"Session started at {session.start_time}")
```

### Record Inspection Data

```python
# After inspecting segment SEG001
location = session.add_location(
    segment_id="SEG001",
    latitude=40.7128,
    longitude=-74.0060,
    gps_accuracy=5.0,
    defects=["pothole", "heave"],
    notes="3-inch pothole at corner, surface heave adjacent"
)

# Add photo
session.add_photo(
    segment_id="SEG001",
    file_path="photo_seg001_001.jpg",
    latitude=40.7128,
    longitude=-74.0060,
    caption="Pothole at intersection"
)

print(f"Recorded {len(session.locations)} locations")
```

### End Session

```python
# End of day
inspection = session.end_session()

print(f"Session summary:")
print(f"  Locations: {inspection.location_count}")
print(f"  Photos: {inspection.photo_count}")
print(f"  Segments inspected: {inspection.segments_inspected}")
print(f"  Duration: {(inspection.end_time - inspection.start_time).seconds / 3600:.1f} hours")

# Export for syncing
session.export_session_data("session_20260510_001.json")
```

## Syncing Data Back

### Sync When Connected to Internet

```python
from socrata_toolkit.mobile_gis import FieldDataSync

sync = FieldDataSync(server_url="https://api.sidewalk-toolkit.nyc.gov")

# Load exported session data
with open("session_20260510_001.json") as f:
    session_data = json.load(f)

# Sync to server
result = sync.sync_session_data(session_data)

print(f"Sync result:")
print(f"  Synced: {result['synced_count']}")
print(f"  Conflicts: {result['conflict_count']}")

# Sync photos
photo_paths = [
    "photo_seg001_001.jpg",
    "photo_seg002_001.jpg",
]
sync.sync_photos("session_20260510_001", photo_paths)
```

## Common QGIS Tasks

### Task 1: Find Segments by Condition

1. Open Attribute Table: Right-click segments layer → Open Attribute Table
2. Filter: Click Filter icon, enter: `condition_score < 50`
3. Results show all poor-condition segments

### Task 2: Draw Inspection Area

1. Create new layer: Layer → Create Layer → New Shapefile Layer
2. Set geometry type: Polygon
3. Use digitize tool to draw area of interest
4. Use Select by Polygon tool to select all segments in drawn area

### Task 3: Measure Distances

1. Vector → Measure Tool
2. Click points to measure distances
3. Or use: Vector → Geometry Tools → Distance to Nearest Hub

### Task 4: Create Map for Print

1. Project → New Print Layout
2. Add map frame, legend, scale
3. File → Export as PDF
4. Print at field office before heading out

## Offline-Online Sync

### Before Going Offline

1. Create offline project (as described above)
2. Download all needed imagery
3. Test that all layers load correctly
4. Verify GPS works

### While Offline

- All edits saved locally in GeoPackage
- Photos stored on device
- GPS locations continuously recorded
- No internet needed

### After Returning Online

```python
# QGIS Offline Editing plugin handles sync
# Or manually sync via Python:

from socrata_toolkit.mobile_gis import FieldDataSync

sync = FieldDataSync(server_url="https://api.sidewalk-toolkit.nyc.gov")

# Check what's pending
pending = sync.get_sync_status()
print(f"Pending syncs: {pending}")

# Sync all changes
result = sync.sync_session_data(session_data)
```

## WMS/WFS Services

### Add WMS Background (Satellite Imagery)

1. Layer → Add Layer → Add WMS/WMTS Layer
2. URL: `http://localhost:8000/wms`
3. Click "Connect"
4. Select layers (e.g., "NYC Satellite Imagery")
5. Click "Add"

### Query WFS Service

1. Layer → Add Layer → Add WFS Layer
2. URL: `http://localhost:8000/wfs`
3. Click "Connect"
4. Select feature type (e.g., "sidewalk_segments")
5. Click "Download"

## Troubleshooting

### Issue: "Layer failed to load"
**Solution:** Check file path and ensure GeoPackage is not open in another application

### Issue: "GPS not working"
**Solution:**
1. Check GPS is enabled on device
2. Verify location permission granted to QGIS
3. Wait 30 seconds for GPS fix
4. Try moving outdoors for better signal

### Issue: "Edits won't save"
**Solution:**
1. Check layer is in edit mode (toggle Edit icon)
2. Ensure offline editing is enabled
3. Try saving manually: Ctrl+S

### Issue: "Photos not attached"
**Solution:**
1. Check photo file exists in current directory
2. Use relative paths: `photo_seg001.jpg` (not `/home/user/photo_seg001.jpg`)
3. Verify JPEG format (some old phones use HEIC)

## Best Practices

### Before Starting
- [ ] Charge device fully
- [ ] Test GPS accuracy
- [ ] Download area and verify all segments visible
- [ ] Check camera battery
- [ ] Bring printed map as backup

### During Inspection
- [ ] Use consistent defect type naming
- [ ] Take photos from multiple angles
- [ ] Note unusual features in comments
- [ ] Record GPS location at start and end of session

### After Inspection
- [ ] Complete all attribute fields
- [ ] Review photos match descriptions
- [ ] Sync data as soon as internet available
- [ ] Report any technical issues

## Performance Tips

### Reduce File Size
- Remove unnecessary background layers
- Reduce resolution of satellite imagery
- Save as GeoPackage (more efficient than Shapefile)

### Speed Up QGIS
- Disable unnecessary plugins
- Set map canvas to 512MB cache
- Use vector tiles instead of raster if available

### Phone/Tablet Tips
- Close other apps to free memory
- Disable WiFi scanning if not needed
- Use USB-C for faster data transfer

## Field Resources

Keep these nearby during fieldwork:
- Printed street map showing segment IDs
- Defect type reference guide
- Contact list for supervisors
- Offline copy of these instructions (PDF or hardcopy)

## Getting Help

- **Technical issues**: Contact GIS coordinator
- **Field questions**: Call supervisor
- **Data sync problems**: Check logs in `~/.qgis3/plugins/offlinesync.log`

## See Also

- [QGIS Documentation](https://qgis.org/docs/)
- [Offline Editing Plugin](https://plugins.qgis.org/plugins/offline_editing_plugin/)
- [Spatial Architecture Guide](spatial_architecture.md)
- [Data Quality Standards](../docs/quality_sla.md)
