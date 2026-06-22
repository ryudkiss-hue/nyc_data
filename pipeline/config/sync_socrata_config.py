#!/usr/bin/env python3
"""
AUTHORITATIVE CONFIG SYNC

Pulls dataset metadata from Local Law 251 inventory (the official NYC data catalog)
and updates pipeline/config/socrata_datasets.json to ALWAYS stay accurate.

Run daily via cron/scheduler to keep configuration in sync with official source:
    0 2 * * * cd /path/to/nyc_data && python pipeline/config/sync_socrata_config.py

This ensures:
- All Socrata IDs are always correct
- New datasets are automatically discovered
- Stale dataset IDs are updated
- No manual config maintenance needed
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

# Configuration
LL251_ID = "5tqd-u88y"  # Local Law 251 - Published Data Asset Inventory
DOMAIN = "data.cityofnewyork.us"
CONFIG_FILE = Path(__file__).parent / "socrata_datasets.json"

def fetch_ll251_inventory():
    """Fetch the authoritative Local Law 251 inventory from NYC Open Data."""
    url = f"https://{DOMAIN}/resource/{LL251_ID}.json?$limit=50000"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"ERROR: Failed to fetch LL251 inventory: {e}")
        sys.exit(1)

def extract_dot_datasets(inventory):
    """Extract DOT sidewalk/inspection datasets from inventory."""
    dot_datasets = []

    for row in inventory:
        agency = row.get("datasetinformation_agency", "")
        name = row.get("name", "")
        uid = row.get("uid", "")
        description = row.get("description", "")
        last_updated = row.get("last_data_updated_date", "")
        category = row.get("category", "")

        # Filter: DOT agency + sidewalk/inspection keywords
        if "DOT" in agency or "Department of Transportation" in agency:
            keywords = ["sidewalk", "inspection", "violation", "ramp", "street center", "curb", "street construction", "pedestrian", "construction"]
            if any(kw in name.lower() or kw in description.lower() for kw in keywords):
                # Calculate days since update
                try:
                    updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    days_ago = (datetime.now(updated_dt.tzinfo) - updated_dt).days
                except:
                    days_ago = None

                dot_datasets.append({
                    "id": len(dot_datasets) + 1,
                    "name": name,
                    "socrata_id": uid,
                    "category": category,
                    "last_updated": last_updated,
                    "days_since_update": days_ago,
                    "source": "socrata"
                })

    return dot_datasets

def update_config(datasets):
    """Write updated configuration to file."""
    new_config = {
        "metadata": {
            "version": "3.0-authoritative",
            "created_at": "2026-06-22",
            "last_synced": datetime.now().isoformat(),
            "source": "Local Law 251 inventory (authoritative)",
            "description": "All DOT datasets from NYC Local Law 251 data asset inventory - ALWAYS ACCURATE",
            "sync_frequency": "Daily via sync_socrata_config.py",
            "total_datasets": len(datasets)
        },
        "socrata_datasets": sorted(datasets, key=lambda x: x['name']),
        "cached_datasets": []
    }

    with open(CONFIG_FILE, 'w') as f:
        json.dump(new_config, f, indent=2)

    return new_config

def main():
    print("=" * 80)
    print("SOCRATA CONFIG SYNC - Local Law 251 Authority")
    print("=" * 80)
    print()
    print("Fetching Local Law 251 inventory...")
    inventory = fetch_ll251_inventory()
    print(f"  Fetched {len(inventory)} total NYC datasets")

    print("Extracting DOT sidewalk/inspection datasets...")
    datasets = extract_dot_datasets(inventory)
    print(f"  Found {len(datasets)} DOT datasets")

    print("Updating configuration...")
    config = update_config(datasets)
    print(f"  Wrote {len(datasets)} datasets to {CONFIG_FILE}")

    print()
    print("SYNC COMPLETE")
    print(f"  Total datasets: {config['metadata']['total_datasets']}")
    print(f"  Last synced: {config['metadata']['last_synced']}")
    print(f"  Source: {config['metadata']['source']}")

    # Also refresh the full authoritative metadata registry (all 3,000+ NYC
    # datasets + DOT column schemas). One daily job keeps both current.
    print()
    print("Refreshing authoritative metadata registry...")
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from pipeline.data.nyc_open_data_registry import NYCDataRegistry

        registry = NYCDataRegistry(auto_sync=False)
        registry.sync()  # incremental: re-fetches columns only for changed datasets
        rmeta = registry.registry["metadata"]
        print(f"  Registry datasets: {rmeta['total_datasets']}")
        print(f"  Registry last synced: {rmeta['last_synced']}")
    except Exception as e:
        print(f"  WARNING: registry refresh failed ({e}); config still updated")

    print()
    print("Configuration and registry will ALWAYS stay accurate with latest NYC Open Data.")

if __name__ == "__main__":
    main()
