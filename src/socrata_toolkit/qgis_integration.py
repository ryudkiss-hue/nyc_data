"""QGIS Project File Generator for DOT Sidewalk Toolkit.

Generate .qgs project files pre-configured with PostGIS layers
and styled by priority/status for the DOT sidewalk team.

Example::

    from socrata_toolkit.qgis_integration import generate_qgis_project

    generate_qgis_project("postgresql://user:pass@localhost/db",
                           layers=["inspections", "permits"],
                           output="sidewalk_project.qgs")
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


def generate_qgis_project(
    dsn: str,
    layers: list[str],
    output: str = "sidewalk_project.qgs",
    geom_col: str = "geom",
    srid: int = 4326,
    title: str = "DOT Sidewalk Inspection Project",
) -> str:
    """Generate a QGIS project file with PostGIS layers.

    Args:
        dsn: PostgreSQL connection string.
        layers: Table names to add as layers.
        output: Output .qgs file path.
        geom_col: Geometry column name.
        srid: Spatial reference ID.
        title: Project title.
    """
    parsed = urlparse(dsn)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    dbname = (parsed.path or "").lstrip("/")
    username = parsed.username or "postgres"
    password = parsed.password or ""

    root = ET.Element("qgis", version="3.34", projectname=title)
    ET.SubElement(root, "title").text = title

    # Project CRS
    proj_crs = ET.SubElement(root, "projectCrs")
    srs = ET.SubElement(proj_crs, "spatialrefsys")
    ET.SubElement(srs, "authid").text = f"EPSG:{srid}"

    # Layer tree
    layer_tree = ET.SubElement(root, "layer-tree-group")

    # Map layers
    project_layers = ET.SubElement(root, "projectlayers")

    for i, table in enumerate(layers):
        layer_id = f"{table}_{i:04d}"

        # Layer tree entry
        tree_layer = ET.SubElement(layer_tree, "layer-tree-layer", id=layer_id, name=table, checked="Qt::Checked")

        # Map layer
        ml = ET.SubElement(project_layers, "maplayer", type="vector", geometry="Point")
        ET.SubElement(ml, "id").text = layer_id
        ET.SubElement(ml, "layername").text = table
        ET.SubElement(ml, "datasource").text = (
            f"dbname='{dbname}' host={host} port={port} "
            f"user='{username}' password='{password}' "
            f"sslmode=prefer key='id' srid={srid} type=Point "
            f"table=\"public\".\"{table}\" ({geom_col})"
        )
        ET.SubElement(ml, "provider").text = "postgres"
        srs_elem = ET.SubElement(ml, "srs")
        srs_inner = ET.SubElement(srs_elem, "spatialrefsys")
        ET.SubElement(srs_inner, "authid").text = f"EPSG:{srid}"

    p = Path(output)
    p.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    tree.write(str(p), encoding="unicode", xml_declaration=True)
    return str(p)
