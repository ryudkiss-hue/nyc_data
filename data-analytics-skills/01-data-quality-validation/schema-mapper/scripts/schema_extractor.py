#!/usr/bin/env python3
"""
schema_extractor.py — Extract column metadata from NYC DOT Socrata datasets.

Connects to the Socrata metadata API to retrieve column names, data types,
descriptions, and sample values. Outputs a data dictionary CSV.

Usage:
    python schema_extractor.py --key inspection
    python schema_extractor.py --key violations --output violations_schema.csv
    python schema_extractor.py --all --output all_schemas.csv
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, "src")

DATASET_KEYS = {
    "inspection": ("data.cityofnewyork.us", "dntt-gqwq", "SIM Inspection Records"),
    "violations": ("data.cityofnewyork.us", "6kbp-uz6m", "SIM Violation Notices"),
    "ramp_progress": ("data.cityofnewyork.us", "e7gc-ub6z", "Curb Ramp Progress"),
    "dismissals": ("data.cityofnewyork.us", "p4u2-3jgx", "SIM Dismissals"),
    "ramp_complaints": ("data.cityofnewyork.us", "jagj-gttd", "Ramp Complaints"),
    "street_permits": ("data.cityofnewyork.us", "tqtj-sjs8", "Street Opening Permits"),
    "tree_damage": ("data.cityofnewyork.us", "j6v2-6uxq", "Tree Damage Inspections"),
    "built": ("data.cityofnewyork.us", "ugc8-s3f6", "SIM Built Records"),
}

DTYPE_NOTES = {
    "text": "String. Check for mixed-case boroughs and trailing spaces.",
    "number": "Numeric. Check for nulls encoded as -1 or 9999.",
    "calendar_date": "ISO 8601 datetime string from Socrata. Cast to DATE for DuckDB comparisons.",
    "point": "GeoJSON point. Extract lat/lon with ST_Y(geom)/ST_X(geom) in DuckDB spatial.",
    "polygon": "GeoJSON polygon.",
    "multipolygon": "GeoJSON multipolygon.",
    "checkbox": "Boolean (true/false string). Cast to BOOLEAN in DuckDB.",
    "url": "URL string.",
}


def extract_schema(key: str, sample_rows: int = 3) -> list[dict]:
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    domain, fourfour, name = DATASET_KEYS[key]
    client = SocrataClient(SocrataConfig())

    print(f"Fetching metadata for {key} ({fourfour})...", flush=True)
    meta = client.get_metadata(domain, fourfour)
    columns = meta.column_dict() if hasattr(meta, "column_dict") else []

    # Fetch sample rows for value examples
    try:
        df = client.fetch_dataframe(domain, fourfour, max_rows=sample_rows)
        sample_values = {col: df[col].dropna().head(3).tolist() for col in df.columns if col in df}
    except Exception:
        sample_values = {}

    rows = []
    for col in columns:
        field = col.get("fieldName", "")
        dtype = col.get("dataTypeName", "")
        samples = sample_values.get(field, [])
        rows.append(
            {
                "dataset_key": key,
                "fourfour": fourfour,
                "dataset_name": name,
                "field_name": field,
                "display_name": col.get("name", field),
                "data_type": dtype,
                "nullable": "yes",  # Socrata columns are always nullable
                "description": col.get("description", ""),
                "sample_values": " | ".join(str(s) for s in samples[:3]),
                "dtype_notes": DTYPE_NOTES.get(dtype, ""),
            }
        )
    return rows


def print_table(rows: list[dict]) -> None:
    print(f"\n{'Field':<35} {'Type':<18} {'Sample Values'}")
    print("-" * 90)
    for r in rows:
        samples = (
            r["sample_values"][:40] + "..." if len(r["sample_values"]) > 40 else r["sample_values"]
        )
        print(f"{r['field_name']:<35} {r['data_type']:<18} {samples}")


def main():
    parser = argparse.ArgumentParser(description="Extract NYC DOT Socrata schema metadata")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--key", choices=list(DATASET_KEYS), help="Dataset key")
    group.add_argument("--all", action="store_true", help="Extract all registered datasets")
    parser.add_argument("--output", help="Save CSV data dictionary to this path")
    parser.add_argument("--sample-rows", type=int, default=3, help="Rows to sample for examples")
    args = parser.parse_args()

    keys = list(DATASET_KEYS) if args.all else [args.key]
    all_rows = []
    for key in keys:
        try:
            rows = extract_schema(key, args.sample_rows)
            all_rows.extend(rows)
            print_table(rows)
        except Exception as e:
            print(f"WARNING: Could not extract schema for {key}: {e}", file=sys.stderr)

    if args.output and all_rows:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\nData dictionary saved to {args.output} ({len(all_rows)} columns)")


if __name__ == "__main__":
    main()
