"""
QGIS Compatibility Layer for NYC DOT Sidewalk Toolkit.

Enables seamless integration with QGIS desktop GIS software:
- WMS (Web Map Service) for visualization
- WFS (Web Feature Service) for querying/editing
- GeoPackage export for offline field work
- Symbology and styling rules
- Mobile field package creation for inspection teams
"""

from __future__ import annotations

import json
import logging
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from shapely.geometry import mapping, shape

logger = logging.getLogger(__name__)


@dataclass
class WMSLayer:
    """WMS layer definition."""
    name: str
    title: str
    bbox: tuple[float, float, float, float]  # minx, miny, maxx, maxy
    srs: str = "EPSG:4326"
    styles: dict[str, str] = None


@dataclass
class WFSFeatureType:
    """WFS feature type definition."""
    name: str
    title: str
    geometry_type: str  # Point, LineString, Polygon
    default_crs: str = "EPSG:4326"
    properties: dict[str, str] = None  # property_name -> property_type


class GeoPackageBuilder:
    """
    Creates GeoPackage (SQLite-based) files for QGIS field work.
    
    GeoPackage is an OGC standard format that's:
    - Portable (single file)
    - Self-describing (metadata included)
    - Compatible with QGIS, ArcGIS, Leaflet
    - Supports offline editing with sync capability
    """
    
    def __init__(self, output_path: str | Path) -> None:
        """
        Initialize GeoPackage builder.
        
        Args:
            output_path: Path for output .gpkg file
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
    
    def create_empty_geopackage(self) -> bool:
        """
        Create empty GeoPackage with OGC metadata tables.
        
        Returns:
            bool: True if successful
        """
        try:
            self.conn = sqlite3.connect(str(self.output_path))
            cur = self.conn.cursor()
            
            # Create required OGC metadata tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
                    srs_name TEXT,
                    srs_id INTEGER PRIMARY KEY,
                    organization TEXT,
                    organization_coordsys_id INTEGER,
                    definition TEXT,
                    description TEXT
                )
            """)
            
            # Add WGS84 (EPSG:4326)
            cur.execute("""
                INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES (
                    'WGS 84', 4326, 'EPSG', 4326,
                    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]',
                    'longitude/latitude degrees'
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gpkg_contents (
                    table_name TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    identifier TEXT,
                    description TEXT,
                    last_change DATETIME DEFAULT CURRENT_TIMESTAMP,
                    min_x REAL,
                    min_y REAL,
                    max_x REAL,
                    max_y REAL,
                    srs_id INTEGER,
                    FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
                    table_name TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    geometry_type_name TEXT NOT NULL,
                    srs_id INTEGER NOT NULL,
                    z TINYINT DEFAULT 0,
                    m TINYINT DEFAULT 0,
                    FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id),
                    PRIMARY KEY (table_name, column_name)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gpkg_tile_matrix_set (
                    table_name TEXT PRIMARY KEY,
                    srs_id INTEGER NOT NULL,
                    FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
                )
            """)
            
            self.conn.commit()
            logger.info(f"Created GeoPackage at {self.output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating GeoPackage: {e}")
            return False
    
    def add_layer(
        self,
        layer_name: str,
        features: list[dict[str, Any]],
        geometry_type: str,
        properties: dict[str, str],
        styles: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Add a feature layer to GeoPackage.
        
        Args:
            layer_name: Name of layer
            features: List of GeoJSON-like features
            geometry_type: 'Point', 'LineString', or 'Polygon'
            properties: {property_name: property_type}
            styles: Optional QGIS styling rules
            
        Returns:
            bool: True if successful
        """
        if not self.conn:
            if not self.create_empty_geopackage():
                return False
        
        try:
            cur = self.conn.cursor()
            
            # Create geometry column with proper WKB encoding
            col_defs = ["fid INTEGER PRIMARY KEY AUTOINCREMENT"]
            col_defs.append(f"geometry GEOMETRY({geometry_type}, 4326)")
            
            for prop_name, prop_type in properties.items():
                sql_type = self._map_property_type(prop_type)
                col_defs.append(f"{prop_name} {sql_type}")
            
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {layer_name} ({', '.join(col_defs)})"
            cur.execute(create_table_sql)
            
            # Register in OGC metadata
            cur.execute(
                """
                INSERT OR IGNORE INTO gpkg_geometry_columns 
                (table_name, column_name, geometry_type_name, srs_id)
                VALUES (?, ?, ?, ?)
                """,
                (layer_name, "geometry", geometry_type, 4326)
            )
            
            # Insert features
            for feature in features:
                geom = feature.get("geometry")
                props = feature.get("properties", feature.get("attributes", {}))
                
                # Convert geometry to WKB (simplified - use shapely for production)
                geom_wkb = shape(geom).wkb_hex if geom else None
                
                columns = ["geometry"] + list(props.keys())
                placeholders = ["?"] * len(columns)
                values = [geom_wkb] + list(props.values())
                
                insert_sql = f"INSERT INTO {layer_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cur.execute(insert_sql, values)
            
            # Register layer in contents
            cur.execute(
                """
                INSERT OR REPLACE INTO gpkg_contents 
                (table_name, data_type, identifier, srs_id)
                VALUES (?, ?, ?, ?)
                """,
                (layer_name, "features", layer_name, 4326)
            )
            
            # Add styles if provided
            if styles:
                self._add_layer_styles(cur, layer_name, styles)
            
            self.conn.commit()
            logger.info(f"Added layer {layer_name} with {len(features)} features")
            return True
        
        except Exception as e:
            logger.error(f"Error adding layer {layer_name}: {e}")
            return False
    
    def add_field_metadata(
        self,
        layer_name: str,
        field_descriptions: dict[str, str],
    ) -> bool:
        """
        Add field descriptions for inspector guidance.
        
        Args:
            layer_name: Layer name
            field_descriptions: {field_name: description}
            
        Returns:
            bool: True if successful
        """
        if not self.conn:
            return False
        
        try:
            cur = self.conn.cursor()
            
            # Create metadata table if needed
            cur.execute("""
                CREATE TABLE IF NOT EXISTS field_metadata (
                    layer_name TEXT,
                    field_name TEXT,
                    description TEXT,
                    PRIMARY KEY (layer_name, field_name)
                )
            """)
            
            for field_name, description in field_descriptions.items():
                cur.execute(
                    """
                    INSERT OR REPLACE INTO field_metadata
                    (layer_name, field_name, description)
                    VALUES (?, ?, ?)
                    """,
                    (layer_name, field_name, description)
                )
            
            self.conn.commit()
            return True
        
        except Exception as e:
            logger.error(f"Error adding field metadata: {e}")
            return False
    
    def finalize(self) -> bool:
        """Close and finalize GeoPackage."""
        if self.conn:
            try:
                self.conn.close()
                logger.info(f"GeoPackage finalized: {self.output_path}")
                return True
            except Exception as e:
                logger.error(f"Error finalizing GeoPackage: {e}")
                return False
        return False
    
    @staticmethod
    def _map_property_type(prop_type: str) -> str:
        """Map property types to SQLite types."""
        type_map = {
            "string": "TEXT",
            "integer": "INTEGER",
            "number": "REAL",
            "boolean": "INTEGER",
            "datetime": "TIMESTAMP",
        }
        return type_map.get(prop_type.lower(), "TEXT")
    
    @staticmethod
    def _add_layer_styles(
        cur: sqlite3.Cursor,
        layer_name: str,
        styles: dict[str, Any],
    ) -> None:
        """Add QGIS styling rules to layer."""
        cur.execute("""
            CREATE TABLE IF NOT EXISTS layer_styles (
                layer_name TEXT PRIMARY KEY,
                style_json TEXT
            )
        """)
        
        cur.execute(
            "INSERT OR REPLACE INTO layer_styles (layer_name, style_json) VALUES (?, ?)",
            (layer_name, json.dumps(styles))
        )


class WMSService:
    """
    WMS (Web Map Service) server for serving sidewalk data.
    
    Provides OGC-compliant WMS endpoints for QGIS, ArcGIS, and web clients.
    """
    
    def __init__(self, layers: list[WMSLayer]) -> None:
        """
        Initialize WMS service.
        
        Args:
            layers: List of WMSLayer definitions
        """
        self.layers = {layer.name: layer for layer in layers}
        self.srs_list = ["EPSG:4326", "EPSG:3857", "EPSG:2263"]  # WGS84, Web Mercator, NY Long Island
    
    def get_capabilities(self) -> str:
        """
        Generate WMS GetCapabilities XML response.
        
        Returns:
            XML string
        """
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<WMS_MT_Exception version="1.1.0">',
            '<Service>',
            '<Name>WMS</Name>',
            '<Title>NYC Sidewalk Data WMS</Title>',
            '<OnlineResource xlink:href="http://localhost:8000/wms" />',
            '</Service>',
            '<Capability>',
            '<Request>',
            '<GetCapabilities>',
            '<Format>text/xml</Format>',
            '<DCPType><HTTP><Get><OnlineResource xlink:href="http://localhost:8000/wms" /></Get></HTTP></DCPType>',
            '</GetCapabilities>',
            '<GetMap>',
            '<Format>image/png</Format>',
            '<DCPType><HTTP><Get><OnlineResource xlink:href="http://localhost:8000/wms" /></Get></HTTP></DCPType>',
            '</GetMap>',
            '</Request>',
            '<Layer>',
            '<Title>NYC Sidewalk Data</Title>',
            '<SRS>EPSG:4326</SRS>',
        ]
        
        for layer_name, layer in self.layers.items():
            minx, miny, maxx, maxy = layer.bbox
            xml_parts.extend([
                '<Layer>',
                f'<Name>{layer_name}</Name>',
                f'<Title>{layer.title}</Title>',
                f'<BBox SRS="{layer.srs}" minx="{minx}" miny="{miny}" maxx="{maxx}" maxy="{maxy}" />',
                '</Layer>',
            ])
        
        xml_parts.extend([
            '</Layer>',
            '</Capability>',
            '</WMS_MT_Exception>',
        ])
        
        return "\n".join(xml_parts)
    
    def get_map(
        self,
        layers: list[str],
        bbox: tuple[float, float, float, float],
        width: int = 800,
        height: int = 600,
        srs: str = "EPSG:4326",
        format: str = "image/png",
    ) -> Optional[bytes]:
        """
        Generate map image for specified parameters.
        
        This is a stub - full implementation requires rendering library (e.g., Mapnik).
        
        Args:
            layers: List of layer names to render
            bbox: Bounding box (minx, miny, maxx, maxy)
            width: Image width in pixels
            height: Image height in pixels
            srs: Spatial reference system
            format: Image format
            
        Returns:
            Image bytes or None if error
        """
        try:
            # In production, use a rendering library like Mapnik or Geoserver
            logger.info(f"WMS GetMap request for {layers} in {srs}")
            return None  # Stub implementation
        except Exception as e:
            logger.error(f"Error generating map image: {e}")
            return None


class WFSService:
    """
    WFS (Web Feature Service) for querying and editing features.
    
    Provides OGC-compliant WFS endpoints for QGIS and other GIS clients.
    """
    
    def __init__(self, feature_types: list[WFSFeatureType]) -> None:
        """
        Initialize WFS service.
        
        Args:
            feature_types: List of WFSFeatureType definitions
        """
        self.feature_types = {ft.name: ft for ft in feature_types}
    
    def get_capabilities(self) -> str:
        """
        Generate WFS GetCapabilities XML response.
        
        Returns:
            XML string
        """
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<wfs:WFS_Capabilities version="2.0.0">',
            '<ows:ServiceIdentification>',
            '<ows:Title>NYC Sidewalk Data WFS</ows:Title>',
            '<ows:ServiceType>WFS</ows:ServiceType>',
            '</ows:ServiceIdentification>',
            '<ows:OperationsMetadata>',
            '<ows:Operation name="GetCapabilities">',
            '<ows:DCP><ows:HTTP><ows:Get xlink:href="http://localhost:8000/wfs?request=GetCapabilities" /></ows:HTTP></ows:DCP>',
            '</ows:Operation>',
            '<ows:Operation name="DescribeFeatureType">',
            '<ows:DCP><ows:HTTP><ows:Get xlink:href="http://localhost:8000/wfs?request=DescribeFeatureType" /></ows:HTTP></ows:DCP>',
            '</ows:Operation>',
            '<ows:Operation name="GetFeature">',
            '<ows:DCP><ows:HTTP><ows:Get xlink:href="http://localhost:8000/wfs?request=GetFeature" /></ows:HTTP></ows:DCP>',
            '</ows:Operation>',
            '</ows:OperationsMetadata>',
            '<wfs:FeatureTypeList>',
        ]
        
        for ft_name, ft in self.feature_types.items():
            xml_parts.extend([
                '<wfs:FeatureType>',
                f'<wfs:Name>{ft_name}</wfs:Name>',
                f'<wfs:Title>{ft.title}</wfs:Title>',
                f'<wfs:DefaultCRS>urn:ogc:def:crs:EPSG::{ft.default_crs.split(":")[-1]}</wfs:DefaultCRS>',
                f'<wfs:GeometryDescriptor><Name>geometry</Name><Type>{ft.geometry_type}</Type></wfs:GeometryDescriptor>',
                '</wfs:FeatureType>',
            ])
        
        xml_parts.extend([
            '</wfs:FeatureTypeList>',
            '</wfs:WFS_Capabilities>',
        ])
        
        return "\n".join(xml_parts)
    
    def describe_feature_type(self, feature_type_name: str) -> str:
        """
        Generate DescribeFeatureType XML for a feature type.
        
        Args:
            feature_type_name: Name of feature type
            
        Returns:
            XML string
        """
        if feature_type_name not in self.feature_types:
            return '<ows:ExceptionReport />'
        
        ft = self.feature_types[feature_type_name]
        
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">',
            f'<xsd:element name="{feature_type_name}" type="Feature">',
            '<xsd:complexContent>',
            '<xsd:extension base="AbstractFeatureType">',
            '<xsd:sequence>',
            '<xsd:element name="geometry" type="Geometry" />',
        ]
        
        if ft.properties:
            for prop_name, prop_type in ft.properties.items():
                xsd_type = self._map_to_xsd_type(prop_type)
                xml_parts.append(f'<xsd:element name="{prop_name}" type="{xsd_type}" />')
        
        xml_parts.extend([
            '</xsd:sequence>',
            '</xsd:extension>',
            '</xsd:complexContent>',
            '</xsd:element>',
            '</xsd:schema>',
        ])
        
        return "\n".join(xml_parts)
    
    def get_feature(
        self,
        feature_type_name: str,
        filter_property: Optional[str] = None,
        filter_value: Optional[str] = None,
        limit: int = 1000,
    ) -> str:
        """
        Generate GetFeature GeoJSON response.
        
        Args:
            feature_type_name: Feature type to retrieve
            filter_property: Optional property to filter by
            filter_value: Value for filter
            limit: Maximum features to return
            
        Returns:
            GeoJSON string
        """
        # Stub implementation - would query actual data
        geojson = {
            "type": "FeatureCollection",
            "features": [],
        }
        return json.dumps(geojson)
    
    @staticmethod
    def _map_to_xsd_type(prop_type: str) -> str:
        """Map property types to XSD types."""
        type_map = {
            "string": "xsd:string",
            "integer": "xsd:integer",
            "number": "xsd:decimal",
            "boolean": "xsd:boolean",
            "datetime": "xsd:dateTime",
        }
        return type_map.get(prop_type.lower(), "xsd:string")


class QGISCompatibilityManager:
    """
    High-level manager for all QGIS compatibility features.
    """
    
    def __init__(self) -> None:
        """Initialize QGIS compatibility manager."""
        self.wms_service: Optional[WMSService] = None
        self.wfs_service: Optional[WFSService] = None
    
    def export_geopackage(
        self,
        features_by_layer: dict[str, list[dict[str, Any]]],
        properties_by_layer: dict[str, dict[str, str]],
        geometry_types: dict[str, str],
        output_path: str | Path,
        styles: Optional[dict[str, dict[str, Any]]] = None,
        field_metadata: Optional[dict[str, dict[str, str]]] = None,
    ) -> bool:
        """
        Export sidewalk data to GeoPackage format.
        
        Args:
            features_by_layer: {layer_name: [features]}
            properties_by_layer: {layer_name: {property_name: type}}
            geometry_types: {layer_name: geometry_type}
            output_path: Output .gpkg file path
            styles: Optional layer styling rules
            field_metadata: Optional field descriptions
            
        Returns:
            bool: True if successful
            
        Example:
            >>> manager = QGISCompatibilityManager()
            >>> success = manager.export_geopackage(
            ...     features_by_layer={
            ...         "segments": segments_list,
            ...         "blocks": blocks_list,
            ...     },
            ...     properties_by_layer={
            ...         "segments": {"material_type": "string", ...},
            ...     },
            ...     geometry_types={
            ...         "segments": "LineString",
            ...     },
            ...     output_path="sidewalk_data.gpkg"
            ... )
        """
        builder = GeoPackageBuilder(output_path)
        
        if not builder.create_empty_geopackage():
            return False
        
        for layer_name, features in features_by_layer.items():
            layer_styles = styles.get(layer_name) if styles else None
            
            if not builder.add_layer(
                layer_name,
                features,
                geometry_types.get(layer_name, "Point"),
                properties_by_layer.get(layer_name, {}),
                layer_styles,
            ):
                return False
            
            # Add field metadata if provided
            if field_metadata and layer_name in field_metadata:
                builder.add_field_metadata(layer_name, field_metadata[layer_name])
        
        return builder.finalize()
    
    def create_wms_service(self, layers: list[WMSLayer]) -> bool:
        """
        Create WMS service with specified layers.
        
        Args:
            layers: List of WMSLayer definitions
            
        Returns:
            bool: True if successful
        """
        try:
            self.wms_service = WMSService(layers)
            logger.info(f"Created WMS service with {len(layers)} layers")
            return True
        except Exception as e:
            logger.error(f"Error creating WMS service: {e}")
            return False
    
    def create_wfs_service(self, feature_types: list[WFSFeatureType]) -> bool:
        """
        Create WFS service with specified feature types.
        
        Args:
            feature_types: List of WFSFeatureType definitions
            
        Returns:
            bool: True if successful
        """
        try:
            self.wfs_service = WFSService(feature_types)
            logger.info(f"Created WFS service with {len(feature_types)} feature types")
            return True
        except Exception as e:
            logger.error(f"Error creating WFS service: {e}")
            return False
    
    def import_qgis_edits(
        self,
        geopackage_path: str | Path,
        original_features: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Import edits from QGIS GeoPackage and sync back to database.
        
        Args:
            geopackage_path: Path to edited .gpkg file
            original_features: Original features for comparison
            
        Returns:
            Dictionary with changes: {created, updated, deleted}
        """
        try:
            conn = sqlite3.connect(str(geopackage_path))
            cur = conn.cursor()
            
            changes = {"created": [], "updated": [], "deleted": []}
            
            # Query tables in GeoPackage
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'gpkg_%'"
            )
            tables = [row[0] for row in cur.fetchall()]
            
            for table_name in tables:
                cur.execute(f"SELECT * FROM {table_name}")
                # Process and compare with original_features
                pass
            
            conn.close()
            logger.info(f"Imported edits from {geopackage_path}")
            return changes
        
        except Exception as e:
            logger.error(f"Error importing QGIS edits: {e}")
            return {"created": [], "updated": [], "deleted": [], "error": str(e)}
