#!/usr/bin/env python
"""Verify Socrata dataset schemas and test joins."""

import sys

sys.path.insert(0, '/c/Users/ryudk/nyc_data/src')

import json

from socrata_toolkit.core.client import SocrataClient, SocrataConfig

config = SocrataConfig()
client = SocrataClient(config)
domain = "data.cityofnewyork.us"

results = {}

# 1. VIOLATIONS - critical defect type columns
print("\n" + "="*70)
print("1. VIOLATIONS (6kbp-uz6m)")
print("="*70)
try:
    meta = client.get_metadata(domain, "6kbp-uz6m")
    print("Total rows: ~398K")
    print(f"Columns: {len(meta.column_dict())}")

    cols = meta.column_dict()
    col_names = [c['name'] for c in cols]
    print(f"\nAll columns:\n  {', '.join(col_names)}")

    # Fetch small sample
    df = client.fetch_dataframe(domain, "6kbp-uz6m", max_rows=5)
    print(f"\nSample data ({len(df)} rows):")
    print(df[['ViolationID', 'BBLID', 'BROKEN', 'TRIP_HAZ', 'UNDERMINED']].to_string())

    results['violations'] = {
        'columns': col_names,
        'sample_count': len(df),
        'has_block_lot': 'Block' in col_names and 'Lot' in col_names,
        'has_bblid': 'BBLID' in col_names,
        'defect_columns': ['BROKEN', 'TRIP_HAZ', 'UNDERMINED', 'SLOPE', 'PATCHWORK', 'HARDWARE', 'SW_MISSING', 'OTHER_DEF', 'CB', 'FLAG', 'INTEGRITY'],
    }
except Exception as e:
    print(f"ERROR: {e}")
    results['violations'] = {'error': str(e)}

# 2. DISMISSALS
print("\n" + "="*70)
print("2. DISMISSALS (p4u2-3jgx)")
print("="*70)
try:
    meta = client.get_metadata(domain, "p4u2-3jgx")
    cols = meta.column_dict()
    col_names = [c['name'] for c in cols]
    print(f"Columns: {len(cols)}")
    print(f"\nKey columns:\n  {', '.join([c for c in col_names if any(k in c.lower() for k in ['block', 'lot', 'bbl', 'violation'])])}")

    df = client.fetch_dataframe(domain, "p4u2-3jgx", max_rows=5)
    print(f"\nSample data ({len(df)} rows):")
    print(df[['Block', 'Lot', 'BBL', 'Violation#']].to_string())

    results['dismissals'] = {
        'columns': col_names,
        'sample_count': len(df),
        'join_keys': ['Block', 'Lot', 'BBL', 'Violation#'] if all(k in col_names for k in ['Block', 'Lot', 'BBL', 'Violation#']) else 'MISSING',
    }
except Exception as e:
    print(f"ERROR: {e}")
    results['dismissals'] = {'error': str(e)}

# 3. LOT_INFO
print("\n" + "="*70)
print("3. LOT_INFO (i642-2fxq)")
print("="*70)
try:
    meta = client.get_metadata(domain, "i642-2fxq")
    cols = meta.column_dict()
    col_names = [c['name'] for c in cols]
    print(f"Columns: {len(cols)}: {col_names}")

    df = client.fetch_dataframe(domain, "i642-2fxq", max_rows=5)
    print(f"\nSample data ({len(df)} rows):")
    print(df.to_string())

    results['lot_info'] = {
        'columns': col_names,
        'sample_count': len(df),
    }
except Exception as e:
    print(f"ERROR: {e}")
    results['lot_info'] = {'error': str(e)}

# 4. CORRESPONDENCES
print("\n" + "="*70)
print("4. CORRESPONDENCES (bheb-sjfi)")
print("="*70)
try:
    meta = client.get_metadata(domain, "bheb-sjfi")
    cols = meta.column_dict()
    col_names = [c['name'] for c in cols]
    print(f"Columns: {len(cols)}")
    print(f"\nKey columns:\n  {', '.join([c for c in col_names if any(k in c.lower() for k in ['block', 'lot', 'bbl', 'violation'])])}")

    df = client.fetch_dataframe(domain, "bheb-sjfi", max_rows=5)
    print(f"\nSample data ({len(df)} rows):")
    print(df[['Block', 'Lot', 'BBL', 'Violation']].to_string() if all(k in df.columns for k in ['Block', 'Lot', 'BBL', 'Violation']) else str(df))

    results['correspondences'] = {
        'columns': col_names,
        'sample_count': len(df),
    }
except Exception as e:
    print(f"ERROR: {e}")
    results['correspondences'] = {'error': str(e)}

# 5. MAPPLUTO
print("\n" + "="*70)
print("5. MAPPLUTO (64uk-42ks)")
print("="*70)
try:
    meta = client.get_metadata(domain, "64uk-42ks")
    cols = meta.column_dict()
    col_names = [c['name'] for c in cols]
    print(f"Columns: {len(cols)}")

    # Check for ownership columns
    owner_cols = [c for c in col_names if any(k in c.lower() for k in ['owner', 'bbl', 'assess'])]
    print(f"\nOwnership/Assessment columns:\n  {', '.join(owner_cols)}")

    df = client.fetch_dataframe(domain, "64uk-42ks", max_rows=3)
    print(f"\nSample data ({len(df)} rows):")
    sample_cols = ['BBL', 'ownertype', 'ownername', 'assesstot'] if all(c in df.columns for c in ['BBL', 'ownertype', 'ownername', 'assesstot']) else df.columns[:5]
    print(df[sample_cols].to_string())

    results['mappluto'] = {
        'columns': col_names,
        'sample_count': len(df),
        'has_bbl': 'BBL' in col_names,
        'has_ownership': 'ownertype' in col_names and 'ownername' in col_names,
    }
except Exception as e:
    print(f"ERROR: {e}")
    results['mappluto'] = {'error': str(e)}

# Save summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(json.dumps(results, indent=2, default=str))
