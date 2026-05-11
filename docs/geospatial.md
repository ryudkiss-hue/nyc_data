# Geospatial Analytics

## Core Features

- Spatial intersects join via `socrata spatial-join`
- WKT/GeoJSON parsing support
- Conflict rate and overlap count outputs
- DOT dashboard spatial conflict workflow in Streamlit

## GeoPackage Builder API

The `GeoPackageBuilder` class provides a comprehensive API for creating and managing GeoPackage files compatible with QGIS.

### Methods

#### `create_empty_geopackage() → bool`
Initialize an empty GeoPackage file.

**Returns**: `True` if initialization successful, `False` otherwise

```python
builder = GeoPackageBuilder("output.gpkg")
if builder.create_empty_geopackage():
    print("GeoPackage initialized")
```

#### `add_layer(layer_name, features, geometry_type, properties, styles=None) → None`
Add a layer to the GeoPackage with features and properties.

**Parameters**:
- `layer_name` (str): Name of the layer
- `features` (List[Dict]): List of feature dictionaries with geometry and properties
- `geometry_type` (str): Type of geometry (Point, LineString, Polygon, MultiLineString, etc.)
- `properties` (Dict[str, str]): Dictionary mapping property names to data types (string, number, datetime, etc.)
- `styles` (Optional[Dict]): QGIS style definition for layer visualization

```python
builder.add_layer(
    layer_name="segments",
    features=segment_features,
    geometry_type="LineString",
    properties={
        "segment_id": "string",
        "material_type": "string",
        "condition_score": "number",
        "last_inspection": "datetime"
    },
    styles={"type": "simple", "color": [0, 0, 0, 255]}
)
```

#### `add_field_metadata(layer_name, metadata) → None`
Add descriptive metadata for fields in a layer (field help text, definitions, etc.).

**Parameters**:
- `layer_name` (str): Name of the layer to add metadata to
- `metadata` (Dict[str, str]): Dictionary mapping field names to descriptions

```python
builder.add_field_metadata(
    "segments",
    {
        "condition_score": "Rate overall condition 0-100",
        "material_type": "What is the predominant material?",
        "defects": "Number of defects observed"
    }
)
```

#### `finalize() → bool`
Finalize and write the GeoPackage file to disk.

**Returns**: `True` if finalization successful, `False` otherwise

```python
if builder.finalize():
    print(f"GeoPackage saved successfully")
```

### Workflow Example

```python
from socrata_toolkit.qgis_compatibility import GeoPackageBuilder

# Initialize builder
builder = GeoPackageBuilder("sidewalk_inspection.gpkg")
builder.create_empty_geopackage()

# Add segments layer
builder.add_layer(
    layer_name="segments",
    features=segments_data,
    geometry_type="LineString",
    properties={
        "segment_id": "string",
        "material_type": "string",
        "condition_score": "number",
        "defects": "integer"
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

# Add field help text
builder.add_field_metadata(
    "segments",
    {
        "condition_score": "Rate condition 0-100",
        "material_type": "Predominant surface material",
        "defects": "Count of observed defects"
    }
)

# Add reference layer
builder.add_layer(
    layer_name="blocks",
    features=blocks_data,
    geometry_type="Polygon",
    properties={
        "block_id": "string",
        "borough": "string"
    }
)

# Finalize and save
builder.finalize()
```

## Mobile Field Packages

See [`docs/qgis_field_guide.md`](qgis_field_guide.md) for creating and using offline field inspection packages with GeoPackages.
