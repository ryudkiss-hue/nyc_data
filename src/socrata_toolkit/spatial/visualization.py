"""
Web-Based Spatial Visualization for Sidewalk Data.

Provides interactive maps using Folium/Leaflet with:
- Condition score visualization (color-coded)
- Material distribution mapping
- Hotspot heatmaps
- Inspector annotations
- Comparison maps (before/after, different datasets)
- Export to HTML/GeoJSON
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import folium  # type: ignore[import]
    from folium import plugins  # type: ignore[import]
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

try:
    import geopandas as gpd  # type: ignore[import]

    HAS_GEOPANDAS = True
except ImportError:
    gpd = None  # type: ignore[assignment]
    HAS_GEOPANDAS = False

logger = logging.getLogger(__name__)

# NYC bounds and default center
NYC_CENTER = (40.7128, -74.0060)
NYC_BOUNDS = [[40.4774, -74.2557], [40.9155, -73.7004]]

@dataclass
class MapStyle:
    """Map styling configuration."""
    color_scheme: str = "viridis"  # viridis, plasma, inferno, cool, warm
    min_color: str = "#d73027"  # Red for poor condition
    max_color: str = "#1a9850"  # Green for good condition
    neutral_color: str = "#fee090"  # Yellow for neutral
    line_weight: int = 2
    line_opacity: float = 0.8
    popup_width: int = 300

class SpatialVisualization:
    """
    High-level manager for spatial data visualization.

    Creates interactive maps from sidewalk data using Folium.
    """

    def __init__(self) -> None:
        """Initialize visualization engine."""
        if not HAS_FOLIUM:
            logger.warning("Folium not installed - visualization features disabled")
        self.maps: dict[str, Any] = {}

    def create_condition_map(
        self,
        features: list[dict[str, Any]],
        title: str = "Sidewalk Condition Map",
        style: MapStyle | None = None,
    ) -> Any | None:
        """
        Create interactive map colored by condition score.

        Args:
            features: List of GeoJSON-like features with condition_score property
            title: Map title
            style: MapStyle configuration

        Returns:
            Folium Map object or None if error

        Example:
            >>> features = [
            ...     {
            ...         "geometry": {"type": "LineString", "coordinates": [...]},
            ...         "properties": {"condition_score": 75, "material": "concrete"}
            ...     }
            ... ]
            >>> map_obj = viz.create_condition_map(features)
            >>> map_obj.save("condition_map.html")
        """
        if not HAS_FOLIUM:
            return None

        try:
            style = style or MapStyle()

            # Create base map with accessibility metadata
            m = folium.Map(
                location=NYC_CENTER,
                zoom_start=12,
                tiles='OpenStreetMap',
                control_scale=True
            )

            # Add accessibility container for Screen Readers
            acc_summary = f"Interactive Map: {title}. Visualizing sidewalk conditions across NYC using color-coded segments."
            acc_html = f'<div id="map-accessibility" role="region" aria-label="{acc_summary}" style="position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); border: 0;">{acc_summary}</div>'
            m.get_root().html.add_child(folium.Element(acc_html))

            # Add segments colored by condition
            for feature in features:
                # ... (feature processing) ...

                properties = feature.get("properties", {})

                condition_score = properties.get("condition_score", 50)
                segment_id = properties.get("segment_id", "unknown")

                # Color based on condition (0=red, 100=green)
                color = self._score_to_color(condition_score, style)

                # Handle different geometry types
                geom = feature.get("geometry", {})
                geom_type = geom.get("type")
                coords = geom.get("coordinates", [])

                if geom_type == "LineString" and coords:
                    # Swap coordinates from [lon, lat] to [lat, lon] for Folium
                    latlng_coords = [[c[1], c[0]] for c in coords]

                    folium.PolyLine(
                        locations=latlng_coords,
                        color=color,
                        weight=style.line_weight,
                        opacity=style.line_opacity,
                        popup=self._create_popup(segment_id, properties),
                    ).add_to(m)

                elif geom_type == "Point" and coords:
                    lat, lon = coords[1], coords[0]
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=5,
                        color=color,
                        fill=True,
                        fillColor=color,
                        popup=self._create_popup(segment_id, properties),
                    ).add_to(m)

            # Add legend
            self._add_condition_legend(m, style)

            # Add title
            title_html = f'<div style="position: fixed; top: 10px; left: 50px; width: 300px; height: 60px; background-color: white; border:2px solid grey; z-index:9999; font-size:16px; padding: 10px">{title}</div>'
            m.get_root().html.add_child(folium.Element(title_html))

            logger.info(f"Created condition map with {len(features)} features")
            return m

        except Exception as e:
            logger.error(f"Error creating condition map: {e}")
            return None

    def create_material_map(
        self,
        features: list[dict[str, Any]],
        title: str = "Material Distribution Map",
        style: MapStyle | None = None,
    ) -> Any | None:
        """
        Create map showing material type distribution.

        Args:
            features: GeoJSON features with material_type property
            title: Map title
            style: MapStyle configuration

        Returns:
            Folium Map object or None
        """
        if not HAS_FOLIUM:
            return None

        try:
            m = folium.Map(
                location=NYC_CENTER,
                zoom_start=12,
                tiles='OpenStreetMap'
            )

            material_colors = {
                "asphalt": "#8b7355",  # Brown
                "concrete": "#d3d3d3",  # Light gray
                "brick": "#a0522d",  # Brown
                "stone": "#696969",  # Dark gray
                "other": "#cccccc",  # Gray
            }

            for feature in features:
                geometry = feature.get("geometry", {})
                properties = feature.get("properties", {})

                material = properties.get("material_type", "other").lower()
                segment_id = properties.get("segment_id", "unknown")
                color = material_colors.get(material, "#cccccc")

                coords = geometry.get("coordinates", [])
                geom_type = geometry.get("type")

                if geom_type == "LineString" and coords:
                    latlng_coords = [[c[1], c[0]] for c in coords]

                    folium.PolyLine(
                        locations=latlng_coords,
                        color=color,
                        weight=3,
                        opacity=0.8,
                        popup=f"{segment_id}<br>Material: {material}",
                    ).add_to(m)

            # Add legend
            legend_html = '''
            <div style="position: fixed; bottom: 50px; right: 50px; width: 200px;
                        background-color: white; border:2px solid grey; z-index:9999;
                        font-size:14px; padding: 10px">
                <p style="margin: 0; font-weight: bold;">Material Type</p>
                <p><i style="background:#8b7355"></i> Asphalt</p>
                <p><i style="background:#d3d3d3"></i> Concrete</p>
                <p><i style="background:#a0522d"></i> Brick</p>
                <p><i style="background:#696969"></i> Stone</p>
                <p><i style="background:#cccccc"></i> Other</p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))

            logger.info(f"Created material map with {len(features)} features")
            return m

        except Exception as e:
            logger.error(f"Error creating material map: {e}")
            return None

    def create_hotspot_map(
        self,
        hotspots: list[dict[str, Any]],
        segments: list[dict[str, Any]] | None = None,
        title: str = "Problem Area Hotspots",
    ) -> Any | None:
        """
        Create heatmap showing problem concentration areas.

        Args:
            hotspots: List of hotspot data {centroid_x, centroid_y, density, severity}
            segments: Optional segment data to show underlying distribution
            title: Map title

        Returns:
            Folium Map object or None
        """
        if not HAS_FOLIUM:
            return None

        try:
            m = folium.Map(
                location=NYC_CENTER,
                zoom_start=12,
                tiles='CartoDB positron'
            )

            # Add hotspot markers
            severity_colors = {
                "critical": "#d73027",  # Dark red
                "high": "#fc8d59",  # Orange red
                "medium": "#fee090",  # Yellow
                "low": "#e0f3f8",  # Light blue
            }

            for hotspot in hotspots:
                severity = hotspot.get("severity", "medium")
                density = hotspot.get("density", 0)
                segment_count = hotspot.get("segment_count", 0)

                color = severity_colors.get(severity, "#fee090")

                lat = hotspot.get("centroid_y")
                lon = hotspot.get("centroid_x")

                if lat is not None and lon is not None:
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=10 + (density / 10),
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.7,
                        weight=2,
                        popup=f"Severity: {severity}<br>Density: {density:.2f}<br>Segments: {segment_count}",
                    ).add_to(m)

            # Add underlying segments if provided
            if segments:
                for segment in segments:
                    geom = segment.get("geometry", {})
                    props = segment.get("properties", {})
                    condition = props.get("condition_score", 50)

                    coords = geom.get("coordinates", [])
                    if geom.get("type") == "LineString" and coords:
                        latlng = [[c[1], c[0]] for c in coords]
                        folium.PolyLine(
                            locations=latlng,
                            color="#999999",
                            weight=1,
                            opacity=0.3,
                        ).add_to(m)

            # Add legend
            legend_html = '''
            <div style="position: fixed; bottom: 50px; right: 50px; width: 150px;
                        background-color: white; border:2px solid grey; z-index:9999;
                        font-size:14px; padding: 10px">
                <p style="margin: 0; font-weight: bold;">Severity</p>
                <p><i style="background:#d73027"></i> Critical</p>
                <p><i style="background:#fc8d59"></i> High</p>
                <p><i style="background:#fee090"></i> Medium</p>
                <p><i style="background:#e0f3f8"></i> Low</p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))

            logger.info(f"Created hotspot map with {len(hotspots)} hotspots")
            return m

        except Exception as e:
            logger.error(f"Error creating hotspot map: {e}")
            return None

    def create_comparison_map(
        self,
        features_before: list[dict[str, Any]],
        features_after: list[dict[str, Any]],
        title: str = "Before/After Comparison",
    ) -> Any | None:
        """
        Create side-by-side comparison map using Folium's HeatMap.

        Args:
            features_before: Features from earlier dataset
            features_after: Features from later dataset
            title: Map title

        Returns:
            Folium Map object or None
        """
        if not HAS_FOLIUM:
            return None

        try:
            m = folium.Map(
                location=NYC_CENTER,
                zoom_start=12,
                tiles='OpenStreetMap',
            )

            # Create two layer groups
            before_group = folium.FeatureGroup(name='Before', show=True)
            after_group = folium.FeatureGroup(name='After', show=True)

            # Add before features
            for feature in features_before:
                geom = feature.get("geometry", {})
                props = feature.get("properties", {})

                coords = geom.get("coordinates", [])
                if geom.get("type") == "LineString" and coords:
                    latlng = [[c[1], c[0]] for c in coords]
                    folium.PolyLine(
                        locations=latlng,
                        color="#3388ff",  # Blue for before
                        weight=2,
                        opacity=0.7,
                    ).add_to(before_group)

            # Add after features
            for feature in features_after:
                geom = feature.get("geometry", {})
                props = feature.get("properties", {})

                coords = geom.get("coordinates", [])
                if geom.get("type") == "LineString" and coords:
                    latlng = [[c[1], c[0]] for c in coords]
                    folium.PolyLine(
                        locations=latlng,
                        color="#ff3333",  # Red for after
                        weight=2,
                        opacity=0.7,
                    ).add_to(after_group)

            before_group.add_to(m)
            after_group.add_to(m)

            # Add layer control
            folium.LayerControl().add_to(m)

            logger.info(f"Created comparison map with {len(features_before)} before, {len(features_after)} after features")
            return m

        except Exception as e:
            logger.error(f"Error creating comparison map: {e}")
            return None

    def export_map_html(
        self,
        map_obj: Any,
        output_path: str | Path,
    ) -> bool:
        """
        Export map to HTML file.

        Args:
            map_obj: Folium Map object
            output_path: Output HTML file path

        Returns:
            bool: True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            map_obj.save(str(output_path))
            logger.info(f"Exported map to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting map: {e}")
            return False

    def export_map_geojson(
        self,
        features: list[dict[str, Any]],
        output_path: str | Path,
    ) -> bool:
        """
        Export features to GeoJSON file.

        Args:
            features: List of features
            output_path: Output GeoJSON file path

        Returns:
            bool: True if successful
        """
        try:
            geojson = {
                "type": "FeatureCollection",
                "features": features,
            }

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(geojson, f, indent=2)

            logger.info(f"Exported GeoJSON to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting GeoJSON: {e}")
            return False

    @staticmethod
    def _score_to_color(score: float, style: MapStyle) -> str:
        """
        Convert condition score (0-100) to color.

        Args:
            score: Condition score 0-100
            style: MapStyle configuration

        Returns:
            Hex color code
        """
        # Map score to 0-1 range
        normalized = score / 100.0

        if normalized < 0.33:
            # Red to Yellow (0-33)
            ratio = normalized / 0.33
            return style.min_color  # Fully red
        elif normalized < 0.67:
            # Yellow (33-67)
            return style.neutral_color
        else:
            # Yellow to Green (67-100)
            return style.max_color

    @staticmethod
    def _create_popup(segment_id: str, properties: dict[str, Any]) -> str:
        """Create HTML popup for feature."""
        html = f"<b>Segment: {segment_id}</b><br>"

        for key, value in properties.items():
            if key not in {"geometry", "segment_id"}:
                if isinstance(value, float):
                    html += f"{key}: {value:.2f}<br>"
                else:
                    html += f"{key}: {value}<br>"

        return html

    @staticmethod
    def _add_condition_legend(m: Any, style: MapStyle) -> None:
        """Add condition score legend to map."""
        legend_html = f'''
        <div style="position: fixed; bottom: 50px; right: 50px; width: 250px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:14px; padding: 10px">
            <p style="margin: 0; font-weight: bold;">Condition Score</p>
            <p><i style="background:{style.min_color}; width: 20px; height: 20px; float: left; margin-right: 8px;"></i>Poor (0-33)</p>
            <p><i style="background:{style.neutral_color}; width: 20px; height: 20px; float: left; margin-right: 8px;"></i>Fair (34-66)</p>
            <p><i style="background:{style.max_color}; width: 20px; height: 20px; float: left; margin-right: 8px;"></i>Good (67-100)</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

class MapExporter:
    """Helper for exporting maps in various formats."""

    @staticmethod
    def to_html(map_obj: Any, path: str | Path) -> bool:
        """Export Folium map to HTML."""
        try:
            map_obj.save(str(path))
            return True
        except Exception as e:
            logger.error(f"Error exporting to HTML: {e}")
            return False

    @staticmethod
    def to_geojson(features: list[dict[str, Any]], path: str | Path) -> bool:
        """Export features to GeoJSON."""
        try:
            geojson = {
                "type": "FeatureCollection",
                "features": features,
            }

            with open(path, 'w') as f:
                json.dump(geojson, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error exporting to GeoJSON: {e}")
            return False

    @staticmethod
    def to_kml(features: list[dict[str, Any]], path: str | Path) -> bool:
        """
        Export features to KML (for Google Earth compatibility).

        This is a simplified implementation.
        """
        try:
            kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>Sidewalk Data</name>
'''

            kml_features = []
            for feature in features:
                geom = feature.get("geometry", {})
                props = feature.get("properties", {})

                coords = geom.get("coordinates", [])
                if geom.get("type") == "LineString" and coords:
                    # Convert to KML LineString
                    coord_str = " ".join([f"{c[0]},{c[1]},0" for c in coords])

                    kml_feature = f'''
  <Placemark>
    <name>{props.get("segment_id", "unknown")}</name>
    <LineString>
      <coordinates>{coord_str}</coordinates>
    </LineString>
  </Placemark>
'''
                    kml_features.append(kml_feature)

            kml_footer = '''
</Document>
</kml>'''

            kml_content = kml_header + "".join(kml_features) + kml_footer

            with open(path, 'w') as f:
                f.write(kml_content)

            return True
        except Exception as e:
            logger.error(f"Error exporting to KML: {e}")
            return False

def export_conflicts_geojson(conflicts_gdf, path: str | Path) -> bool:
    """Write a conflicts GeoDataFrame to GeoJSON with severity properties.

    Reprojects to WGS84 (the GeoJSON standard CRS) when needed and serialises
    all attribute columns — including any ``conflict_score``/``dist`` severity
    fields produced by the conflict engine — as feature properties.

    Args:
        conflicts_gdf: GeoDataFrame of conflicts (e.g. from ``detect_conflicts``
            then ``spatial_conflict_score``).
        path: Output ``.geojson`` file path.

    Returns:
        bool: ``True`` on success, ``False`` if geopandas is missing, the input
        is empty/invalid, or the write fails.
    """
    if not HAS_GEOPANDAS:
        logger.warning("export_conflicts_geojson: geopandas not installed")
        return False
    if conflicts_gdf is None or len(conflicts_gdf) == 0:
        logger.warning("export_conflicts_geojson: no conflicts to export")
        return False

    try:
        gdf = conflicts_gdf
        if gdf.crs is not None and str(gdf.crs).upper() not in (
            "EPSG:4326",
            "WGS84",
        ):
            gdf = gdf.to_crs("EPSG:4326")

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(str(out_path), driver="GeoJSON")
        logger.info("Exported %d conflicts to %s", len(gdf), out_path)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Error exporting conflicts GeoJSON: %s", e)
        return False
