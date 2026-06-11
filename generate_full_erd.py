#!/usr/bin/env python
"""
Generate detailed ERD for all 24 NYC DOT datasets.
Fetches schema from Socrata and builds entity-relationship diagram.
"""

import sys
sys.path.insert(0, 'src')

import json
from datetime import datetime
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

# All 24 datasets
DATASETS = {
    # Inspection & Violations
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "dismissals": "p4u2-3jgx",
    "correspondences": "bheb-sjfi",
    "reinspection": "gx72-kirf",
    "tree_damage": "j6v2-6uxq",
    "curb_metal_protruding": "i2y3-sx2e",

    # Ramp & Accessibility
    "ramp_locations": "ufzp-rrqu",
    "ramp_complaints": "jagj-gttd",
    "ramp_progress": "e7gc-ub6z",

    # Permits & Construction
    "street_permits": "tqtj-sjs8",
    "weekly_construction": "r528-jcks",
    "capital_blocks": "jvk9-k4re",
    "capital_intersections": "97nd-ff3i",
    "street_construction_inspections": "ydkf-mpxb",
    "street_closures_block": "i6b5-j7bu",
    "permit_stipulations": "gsgx-6efw",
    "street_resurfacing_schedule": "xnfm-u3k5",
    "street_resurfacing_inhouse": "ffaf-8mrv",

    # Context & Overlays
    "step_streets": "u9au-h79y",
    "sidewalk_planimetric": "vfx9-tbb6",
    "pedestrian_demand": "fwpa-qxaf",
    "mappluto": "64uk-42ks",
    "complaints_311": "erm2-nwe9",
}

def infer_relationships(all_metadata):
    """Infer relationships between datasets based on column names."""
    relationships = []

    # Common key patterns
    key_patterns = {
        'id': ['objectid', 'unique_id', 'record_id', 'id'],
        'location': ['the_geom', 'geometry', 'location', 'lat', 'lon', 'latitude', 'longitude'],
        'date': ['date', 'created_date', 'updated_date', 'closed_date', 'completion_date'],
        'borough': ['borough', 'borough_code', 'boro'],
        'address': ['address', 'street_address', 'location_address'],
    }

    # Build column index
    columns_by_dataset = {}
    for ds_name, metadata in all_metadata.items():
        columns_by_dataset[ds_name] = {
            col['name'].lower(): col for col in metadata.get('columns', [])
        }

    # Find relationships
    for ds1_name in all_metadata.keys():
        for col in all_metadata[ds1_name].get('columns', []):
            col_name = col['name'].lower()

            # Look for foreign key patterns
            for ds2_name in all_metadata.keys():
                if ds1_name == ds2_name:
                    continue

                if col_name in columns_by_dataset.get(ds2_name, {}):
                    # Found potential FK
                    relationships.append({
                        'from_table': ds1_name,
                        'from_column': col['name'],
                        'to_table': ds2_name,
                        'to_column': col['name'],
                        'type': 'FK'
                    })

    return relationships

def generate_erd_text(all_metadata, relationships):
    """Generate text-based ERD."""
    lines = []
    lines.append("=" * 100)
    lines.append("ENTITY RELATIONSHIP DIAGRAM - NYC DOT DATASETS")
    lines.append("=" * 100)

    # Entity definitions
    lines.append("\n## ENTITIES (24 Datasets)\n")

    for ds_name in sorted(all_metadata.keys()):
        metadata = all_metadata[ds_name]
        columns = metadata.get('columns', [])

        lines.append(f"\n### {ds_name.upper()}")
        lines.append(f"Fourfour: {metadata['fourfour']}")
        lines.append(f"Rows: {metadata.get('row_count', 'N/A'):,}")
        lines.append(f"Columns: {len(columns)}")
        lines.append("")

        # Identify potential key columns
        key_patterns = ['id', 'objectid', 'unique_id', 'record_id']
        location_patterns = ['the_geom', 'geometry', 'location']
        date_patterns = ['date', 'created_date', 'updated_date', 'closed_date']

        lines.append("Columns:")
        for col in sorted(columns, key=lambda c: c['name']):
            col_name = col['name']
            col_type = col.get('dataTypeName', 'Unknown')

            # Mark special columns
            markers = []
            if any(p in col_name.lower() for p in key_patterns):
                markers.append("[PK]")
            if any(p in col_name.lower() for p in location_patterns):
                markers.append("[GEO]")
            if any(p in col_name.lower() for p in date_patterns):
                markers.append("[DATE]")

            marker_str = " ".join(markers) if markers else ""
            lines.append(f"  • {col_name:40s} {col_type:20s} {marker_str}")

    return "\n".join(lines)

def generate_erd_mermaid(all_metadata, relationships):
    """Generate Mermaid diagram syntax."""
    lines = ["erDiagram"]

    for ds_name in sorted(all_metadata.keys()):
        metadata = all_metadata[ds_name]
        row_count = metadata.get('row_count', 0)
        lines.append(f'    {ds_name.upper()} {{')

        columns = metadata.get('columns', [])
        for col in sorted(columns[:10], key=lambda c: c['name']):  # Limit to 10 cols for readability
            col_type = col.get('dataTypeName', 'text')
            lines.append(f'        {col["name"]} {col_type}')

        if len(columns) > 10:
            lines.append(f'        ... ({len(columns) - 10} more columns)')

        lines.append(f'    }}')

    # Add relationships
    for rel in relationships[:20]:  # Limit relationships for readability
        lines.append(f'    {rel["from_table"].upper()} ||--o{{ {rel["to_table"].upper()} : "{rel["from_column"]}"')

    return "\n".join(lines)

def generate_dataset_summary(all_metadata):
    """Generate summary statistics."""
    lines = []
    lines.append("\n" + "=" * 100)
    lines.append("DATASET SUMMARY")
    lines.append("=" * 100)

    total_rows = 0
    total_columns = 0
    total_datasets = len(all_metadata)

    column_type_counts = {}

    for metadata in all_metadata.values():
        total_rows += metadata.get('row_count', 0)
        total_columns += len(metadata.get('columns', []))

        for col in metadata.get('columns', []):
            col_type = col.get('dataTypeName', 'Unknown')
            column_type_counts[col_type] = column_type_counts.get(col_type, 0) + 1

    lines.append(f"\nTotal Datasets: {total_datasets}")
    lines.append(f"Total Rows: {total_rows:,}")
    lines.append(f"Total Columns: {total_columns}")
    lines.append(f"Avg Rows/Dataset: {total_rows // total_datasets:,}")
    lines.append(f"Avg Columns/Dataset: {total_columns // total_datasets}")

    lines.append("\nColumn Types:")
    for col_type in sorted(column_type_counts.keys(), key=lambda x: column_type_counts[x], reverse=True):
        lines.append(f"  • {col_type:30s} {column_type_counts[col_type]:3d} columns")

    return "\n".join(lines)

def main():
    print("=" * 100)
    print("GENERATING COMPLETE ERD FOR ALL 24 DATASETS")
    print("=" * 100)

    client = SocrataClient(SocrataConfig())
    all_metadata = {}

    print(f"\n[FETCHING] Schema for {len(DATASETS)} datasets...")

    for ds_name, fourfour in sorted(DATASETS.items()):
        try:
            metadata = client.get_metadata("data.cityofnewyork.us", fourfour)

            all_metadata[ds_name] = {
                'fourfour': fourfour,
                'name': metadata.name,
                'row_count': metadata.row_count,
                'columns': metadata.columns,
            }

            print(f"  [OK] {ds_name:35s} {metadata.row_count or 0:>10,} rows {len(metadata.columns):>3} cols")
        except Exception as e:
            print(f"  [ERROR] {ds_name:35s} {str(e)[:40]}")

    print(f"\n[ANALYSIS] Found {len(all_metadata)} datasets")

    # Infer relationships
    relationships = infer_relationships(all_metadata)
    print(f"[ANALYSIS] Inferred {len(relationships)} relationships")

    # Generate ERD outputs
    print("\n[GENERATING] Text-based ERD...")
    erd_text = generate_erd_text(all_metadata, relationships)

    print("[GENERATING] Mermaid diagram...")
    erd_mermaid = generate_erd_mermaid(all_metadata, relationships)

    print("[GENERATING] Summary statistics...")
    summary = generate_dataset_summary(all_metadata)

    # Save outputs
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_datasets": len(all_metadata),
        "total_relationships": len(relationships),
        "summary": summary,
        "erd_text": erd_text,
        "erd_mermaid": erd_mermaid,
        "detailed_schemas": all_metadata,
    }

    with open("complete_erd.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    # Also save text version
    with open("complete_erd.txt", "w") as f:
        f.write(erd_text)
        f.write("\n\n")
        f.write(summary)

    # Save Mermaid diagram
    with open("complete_erd.mmd", "w") as f:
        f.write(erd_mermaid)

    print("\n" + "=" * 100)
    print("FILES SAVED:")
    print("  • complete_erd.json — Full data (for processing)")
    print("  • complete_erd.txt — Human-readable ERD")
    print("  • complete_erd.mmd — Mermaid diagram (for rendering)")
    print("=" * 100)

    # Print summary
    print(summary)

    return output

if __name__ == "__main__":
    main()
