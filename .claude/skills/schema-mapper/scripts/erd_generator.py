#!/usr/bin/env python3
"""
erd_generator.py — Generate a Mermaid ERD for NYC DOT SIM dataset relationships.

Outputs a .mmd file containing a Mermaid erDiagram block that can be rendered
in GitHub Markdown, Notion, or mermaid.live.

Usage:
    python erd_generator.py --output erd.mmd
    python erd_generator.py --datasets inspection violations dismissals --output sim_erd.mmd
    python erd_generator.py --include-overlays --output full_erd.mmd
"""

import argparse
from pathlib import Path

# Entity definitions: field name, type, key indicator (PK/FK/-)
ENTITIES = {
    "inspection": [
        ("objectid", "NUMBER", "PK"),
        ("borough", "TEXT", "-"),
        ("status", "TEXT", "-"),
        ("inspection_date", "DATE", "-"),
        ("house_number", "TEXT", "-"),
        ("street_name", "TEXT", "-"),
        ("latitude", "NUMBER", "-"),
        ("longitude", "NUMBER", "-"),
        ("the_geom", "POINT", "-"),
    ],
    "violations": [
        ("objectid", "NUMBER", "PK"),
        ("inspection_objectid", "NUMBER", "FK"),
        ("borough", "TEXT", "-"),
        ("status", "TEXT", "-"),
        ("created_date", "DATE", "-"),
        ("violation_type", "TEXT", "-"),
        ("house_number", "TEXT", "-"),
        ("street_name", "TEXT", "-"),
    ],
    "dismissals": [
        ("objectid", "NUMBER", "PK"),
        ("violation_objectid", "NUMBER", "FK"),
        ("borough", "TEXT", "-"),
        ("created_date", "DATE", "-"),
        ("dismiss_reason", "TEXT", "-"),
    ],
    "ramp_progress": [
        ("objectid", "NUMBER", "PK"),
        ("borough", "TEXT", "-"),
        ("status", "TEXT", "-"),
        ("inspection_date", "DATE", "-"),
        ("completion_date", "DATE", "-"),
        ("latitude", "NUMBER", "-"),
        ("longitude", "NUMBER", "-"),
        ("the_geom", "POINT", "-"),
    ],
    "ramp_complaints": [
        ("unique_key", "TEXT", "PK"),
        ("borough", "TEXT", "-"),
        ("created_date", "DATE", "-"),
        ("status", "TEXT", "-"),
        ("latitude", "NUMBER", "-"),
        ("longitude", "NUMBER", "-"),
    ],
    "street_permits": [
        ("permit_si_no", "TEXT", "PK"),
        ("borough", "TEXT", "-"),
        ("work_type", "TEXT", "-"),
        ("startdate", "DATE", "-"),
        ("enddate", "DATE", "-"),
        ("latitude", "NUMBER", "-"),
        ("longitude", "NUMBER", "-"),
        ("the_geom", "POINT", "-"),
    ],
    "tree_damage": [
        ("objectid", "NUMBER", "PK"),
        ("inspection_objectid", "NUMBER", "FK"),
        ("borough", "TEXT", "-"),
        ("created_date", "DATE", "-"),
    ],
}

# Overlay / context datasets (optional)
OVERLAY_ENTITIES = {
    "sidewalk_planimetric": [
        ("objectid", "NUMBER", "PK"),
        ("borough", "TEXT", "-"),
        ("the_geom", "POLYGON", "-"),
    ],
    "pedestrian_demand": [
        ("objectid", "NUMBER", "PK"),
        ("borough", "TEXT", "-"),
        ("demand_score", "NUMBER", "-"),
        ("the_geom", "POLYGON", "-"),
    ],
    "mappluto": [
        ("objectid", "NUMBER", "PK"),
        ("bbl", "TEXT", "PK"),
        ("borough", "TEXT", "-"),
        ("the_geom", "MULTIPOLYGON", "-"),
    ],
}

# Relationships: (entity_a, cardinality, entity_b, label)
# Mermaid cardinality: ||--|| one-to-one, ||--o{ one-to-many, }o--o{ many-to-many
RELATIONSHIPS = [
    ("inspection", "||--o{", "violations", "generates"),
    ("violations", "||--o{", "dismissals", "resolved by"),
    ("inspection", "||--o{", "tree_damage", "flags"),
    ("inspection", "}o--o{", "street_permits", "conflicts near"),
    ("ramp_complaints", "}o--o{", "ramp_progress", "tracked in"),
]

OVERLAY_RELATIONSHIPS = [
    ("inspection", "}o--o{", "sidewalk_planimetric", "located on"),
    ("inspection", "}o--o{", "pedestrian_demand", "demand context"),
    ("street_permits", "}o--o{", "mappluto", "lot context"),
]


def render_entity(name: str, fields: list[tuple]) -> list[str]:
    lines = [f"    {name} {{"]
    for field_name, dtype, key in fields:
        key_str = f" {key}" if key != "-" else ""
        lines.append(f"        {dtype} {field_name}{key_str}")
    lines.append("    }")
    return lines


def generate_mermaid(datasets: list[str], include_overlays: bool) -> str:
    lines = ["erDiagram"]
    active_entities = {k: v for k, v in ENTITIES.items() if k in datasets}
    if include_overlays:
        active_entities.update(OVERLAY_ENTITIES)

    for name, fields in active_entities.items():
        lines.extend(render_entity(name, fields))
        lines.append("")

    for entity_a, cardinality, entity_b, label in RELATIONSHIPS:
        if entity_a in active_entities and entity_b in active_entities:
            lines.append(f'    {entity_a} {cardinality} {entity_b} : "{label}"')

    if include_overlays:
        for entity_a, cardinality, entity_b, label in OVERLAY_RELATIONSHIPS:
            if entity_a in active_entities and entity_b in active_entities:
                lines.append(f'    {entity_a} {cardinality} {entity_b} : "{label}"')

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Mermaid ERD for NYC DOT SIM datasets")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=list(ENTITIES),
        default=list(ENTITIES),
        help="Datasets to include (default: all core SIM)",
    )
    parser.add_argument(
        "--include-overlays", action="store_true", help="Include overlay/context datasets"
    )
    parser.add_argument("--output", default="erd.mmd", help="Output .mmd file path")
    args = parser.parse_args()

    diagram = generate_mermaid(args.datasets, args.include_overlays)

    output_path = Path(args.output)
    output_path.write_text(diagram)
    print(f"ERD written to {output_path}")
    print(
        f"Entities: {len(args.datasets)}  |  Overlays: {'yes' if args.include_overlays else 'no'}"
    )
    print("\nPreview (first 20 lines):")
    for line in diagram.split("\n")[:20]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
