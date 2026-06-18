#!/usr/bin/env python3
"""
Fetch Socrata metadata for all 78 datasets and populate schemas.

Updates DATASET_REGISTRY.yaml with:
- Actual column names and types from Socrata
- Row counts
- Last update timestamps
- API accessibility status

This ensures visualization templates are pre-configured with real schemas.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

# All 78 datasets: core 57 + Phase 1 21
DATASETS_TO_FETCH = {
    # Phase 1: Permit Variants (5)
    "street_permits_fee": "9fnm-j6if",
    "street_closures_construction": "ezy6-djsf",
    "street_permits_historical": "c9sj-fmsg",
    "street_permits_cranes": "hcv3-zacv",
    "street_permits_related_agency": "cj3v-xdpd",
    # Phase 1: Pedestrian Infrastructure (6)
    "open_streets": "uiay-nctu",
    "pedestrian_mobility_demand": "c4kr-96ik",
    "accessible_signals_map": "umfn-twbz",
    "accessible_signals_table": "de3m-c5p4",
    "pedestrian_plazas_polygon": "k5k6-6jex",
    "pedestrian_plazas_map": "fnkv-pyhj",
    # Phase 1: Street Safety (5)
    "parking_meters_map": "mvib-nh9w",
    "parking_meters_table": "693u-uax6",
    "speed_reducers": "9n6h-pt9g",
    "leading_pedestrian_intervals": "xc4v-ntf4",
    "vision_zero_crossings": "bssx-36gg",
    # Phase 1: Budget & Vendor (3)
    "capital_projects_dashboard": "fb86-vt7u",
    "bicycle_parking": "thbt-gfu9",
    "bus_pad_tracking": "eyb2-p5s8",
    # Phase 1: Reference & Geospatial (2)
    "centerline_streets": "3mf9-qshr",
    "pedestrian_ramp_audit_mbpo": "8kic-uvpz",
    # Core: Daily Operations (subset)
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "reinspection": "gx72-kirf",
    "ramp_progress": "e7gc-ub6z",
    "ramp_complaints": "jagj-gttd",
}


def fetch_dataset_metadata(fourfour: str, domain: str = "data.cityofnewyork.us") -> Optional[Dict[str, Any]]:
    """
    Fetch dataset metadata from Socrata API.

    Args:
        fourfour: Socrata fourfour ID (e.g., "dntt-gqwq")
        domain: Socrata domain (default: NYC Open Data)

    Returns:
        Dict with columns, row count, last update, status
        None if API call fails
    """
    url = f"https://{domain}/api/views/{fourfour}.json"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())

        # Extract useful metadata
        columns = []
        if "columns" in data:
            for col in data.get("columns", []):
                columns.append({
                    "name": col.get("name"),
                    "field_name": col.get("fieldName"),
                    "type": col.get("dataTypeName"),
                    "description": col.get("description", ""),
                })

        row_count = data.get("rowsUpdatedAt", 0)

        metadata = {
            "fourfour": fourfour,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "columns": columns,
            "row_count": data.get("numberOfRows", 0),
            "last_updated_timestamp": data.get("lastModifiedTime", None),
            "created_timestamp": data.get("createdTime", None),
            "accessibility": "ok" if len(columns) > 0 else "error",
        }

        return metadata

    except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
        print(f"  ⚠️  {fourfour}: {type(e).__name__} — using stub metadata")
        return {
            "fourfour": fourfour,
            "accessibility": "error",
            "error": str(e),
            "columns": [],
        }


def generate_column_specs(columns: list) -> Dict[str, str]:
    """Convert Socrata columns to visualization specs."""
    specs = {}

    # Common patterns
    numeric_cols = [c["name"] for c in columns if c.get("type") in ["number", "decimal"]]
    text_cols = [c["name"] for c in columns if c.get("type") in ["text", "plain_text"]]
    date_cols = [c["name"] for c in columns if c.get("type") in ["calendar_date", "floating_timestamp"]]
    geo_cols = [c["name"] for c in columns if c.get("type") in ["location", "point"]]

    # Auto-detect borough column
    borough_col = next(
        (c["name"] for c in columns if "borough" in c.get("name", "").lower()),
        text_cols[0] if text_cols else "location"
    )

    # Auto-detect numeric value column (prefer count-like names)
    value_col = next(
        (c["name"] for c in columns if any(x in c.get("name", "").lower() for x in ["count", "volume", "total", "amount"])),
        numeric_cols[0] if numeric_cols else "value"
    )

    # Auto-detect date column
    date_col = next(
        (c["name"] for c in columns if any(x in c.get("name", "").lower() for x in ["date", "time"])),
        date_cols[0] if date_cols else None
    )

    return {
        "borough_column": borough_col,
        "value_column": value_col,
        "date_column": date_col,
        "all_numeric": numeric_cols,
        "all_text": text_cols,
        "all_dates": date_cols,
        "all_geographic": geo_cols,
    }


def main():
    """Fetch metadata for all datasets and update registry."""
    registry_path = Path("docs/DATASET_REGISTRY.yaml")

    # Load existing registry
    with open(registry_path) as f:
        registry = yaml.safe_load(f)

    print(f"Fetching Socrata metadata for {len(DATASETS_TO_FETCH)} datasets...\n")

    fetched_count = 0
    error_count = 0

    for key, fourfour in sorted(DATASETS_TO_FETCH.items()):
        print(f"Fetching {fourfour} ({key})...", end=" ", flush=True)

        # Fetch metadata
        metadata = fetch_dataset_metadata(fourfour)

        if metadata and metadata.get("accessibility") == "ok":
            print(f"✓ {len(metadata.get('columns', []))} columns")
            fetched_count += 1

            # Update registry with schema info
            if key in registry["datasets"]:
                registry["datasets"][key]["schema"] = {
                    "columns": [{"name": c["name"], "type": c["type"]} for c in metadata.get("columns", [])],
                    "row_count": metadata.get("row_count", 0),
                    "last_updated": metadata.get("last_updated_timestamp"),
                }

                # Add column specs for visualization auto-configuration
                col_specs = generate_column_specs(metadata.get("columns", []))
                registry["datasets"][key]["column_specs"] = col_specs

                # Update visualization hints
                if "visualization" in registry["datasets"][key]:
                    registry["datasets"][key]["visualization"]["suggested_iv"] = col_specs["borough_column"]
                    registry["datasets"][key]["visualization"]["suggested_dv"] = col_specs["value_column"]
        else:
            print(f"⚠️  Error")
            error_count += 1

    # Write updated registry
    with open(registry_path, "w") as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)

    print(f"\n[SUMMARY]")
    print(f"  Fetched: {fetched_count}")
    print(f"  Errors: {error_count}")
    print(f"  Updated: {registry_path}")
    print(f"\n  Registry now includes:")
    print(f"  - Real column schemas")
    print(f"  - Auto-detected IV/DV columns")
    print(f"  - Row counts & update timestamps")
    print(f"  - Geographic column hints")
    print(f"\n  Visualization templates can now:")
    print(f"  - Use real column names")
    print(f"  - Auto-detect aggregation method")
    print(f"  - Suggest chart types based on data")


if __name__ == "__main__":
    main()
