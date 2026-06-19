#!/usr/bin/env python3
"""
Generate staging schema SQL dynamically from config.
Issue #5: Use actual primary keys from socrata_datasets.json instead of hardcoded columns.
"""

import json
from pathlib import Path


def generate_staging_schema() -> str:
    """Generate complete staging schema SQL from config primary keys."""
    config_path = Path('pipeline/config/socrata_datasets.json')

    with open(config_path) as f:
        config = json.load(f)

    all_datasets = []
    all_datasets.extend(config.get('cached_datasets', []))
    all_datasets.extend(config.get('socrata_remaining', []))

    sql_lines = [
        "-- ============================================================================",
        "-- Phase 1B: Staging Schema - Deduplication & Type Casting (Auto-generated)",
        "-- ============================================================================",
        "-- Generated from pipeline/config/socrata_datasets.json",
        "-- Uses actual primary_key from config for each dataset",
        "-- ============================================================================",
        "",
        "CREATE SCHEMA IF NOT EXISTS staging;",
        "",
    ]

    for dataset in all_datasets:
        dataset_name = dataset['name']
        primary_key = dataset['primary_key']

        # Use QUALIFY pattern (DuckDB native) for cleaner deduplication
        sql = f"""CREATE OR REPLACE TABLE staging.{dataset_name} AS
SELECT * FROM raw.{dataset_name}
QUALIFY ROW_NUMBER() OVER (PARTITION BY {primary_key} ORDER BY 1 DESC) = 1;
"""
        sql_lines.append(sql)

    return "\n".join(sql_lines)


if __name__ == "__main__":
    sql = generate_staging_schema()
    output_path = Path('pipeline/sql/02_staging_schema.sql')

    with open(output_path, 'w') as f:
        f.write(sql)

    with open('pipeline/config/socrata_datasets.json') as f:
        config = json.load(f)
    total = config['metadata'].get('total_datasets', 0)

    print(f"[OK] Generated staging schema with all {total} datasets")
    print(f"[OK] Written to {output_path}")
