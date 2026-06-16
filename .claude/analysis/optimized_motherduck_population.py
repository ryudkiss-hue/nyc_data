#!/usr/bin/env python3
"""
Optimized MotherDuck population strategy for 26 NYC datasets.

This script implements parallel, storage-efficient population of MotherDuck
from locally-cached Parquet files.

Approach:
1. Use DuckDB's native Parquet scanning (zero-copy, memory-efficient)
2. Create external MotherDuck tables pointing to Parquet files
3. Parallel workers for speed (4 concurrent uploads)
4. No data duplication in memory

Usage:
    python optimized_motherduck_population.py

    OR for specific datasets:
    python optimized_motherduck_population.py --datasets inspection violations ramp_progress

    OR dry-run (no uploads):
    python optimized_motherduck_population.py --dry-run
"""

import os
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb not installed. Install with: pip install duckdb")
    sys.exit(1)

# Registry of all 26 NYC datasets with fourfour codes
DATASET_REGISTRY = {
    # Core SIM Data (Inspection & Violations)
    'inspection': 'dntt-gqwq',
    'violations': '6kbp-uz6m',
    'built': 'ugc8-s3f6',
    'lot_info': 'i642-2fxq',
    'reinspection': 'gx72-kirf',
    'correspondences': 'bheb-sjfi',
    'tree_damage': 'j6v2-6uxq',
    'dismissals': 'p4u2-3jgx',
    'curb_metal_protruding': 'i2y3-sx2e',

    # Accessibility (Ramps)
    'ramp_progress': 'e7gc-ub6z',
    'ramp_complaints': 'jagj-gttd',
    'ramp_locations': 'ufzp-rrqu',

    # Coordination (Permits & Construction)
    'street_permits': 'tqtj-sjs8',
    'street_construction_inspections': 'ydkf-mpxb',
    'capital_intersections': '97nd-ff3i',
    'street_closures_block': 'i6b5-j7bu',
    'permit_stipulations': 'gsgx-6efw',
    'street_resurfacing_schedule': 'xnfm-u3k5',
    'street_resurfacing_inhouse': 'ffaf-8mrv',
    'weekly_construction': 'r528-jcks',
    'capital_blocks': 'jvk9-k4re',

    # Context Layers (Overlays)
    'complaints_311': 'erm2-nwe9',
    'pedestrian_demand': 'fwpa-qxaf',
    'mappluto': '64uk-42ks',
    'sidewalk_planimetric': 'vfx9-tbb6',
    'step_streets': 'u9au-h79y',
}

def get_motherduck_token() -> str:
    """Get MotherDuck token from environment or prompt user."""
    token = os.getenv('MOTHERDUCK_TOKEN')
    if not token:
        print("\n⚠️  MOTHERDUCK_TOKEN not set in environment.")
        print("   To get a token, visit: https://console.motherduck.com/")
        token = input("   Enter your MotherDuck token (or press Enter to skip): ").strip()
    return token

def connect_motherduck(token: str = None) -> duckdb.DuckDBPyConnection:
    """Connect to MotherDuck with token."""
    if not token:
        token = get_motherduck_token()

    if not token:
        print("Skipping MotherDuck (no token provided)")
        return None

    try:
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        # Test connection
        conn.execute("SELECT 1")
        print("✓ MotherDuck connection successful")
        return conn
    except Exception as e:
        print(f"❌ MotherDuck connection failed: {e}")
        return None

def upload_parquet_to_motherduck(
    md_conn,
    dataset_key: str,
    parquet_path: Path,
    dry_run: bool = False
) -> dict:
    """
    Upload a single Parquet file to MotherDuck.

    Strategy:
    1. Create an external table pointing to the local Parquet file
    2. Insert into MotherDuck table via CTAS
    3. Minimal memory footprint (streaming inserts)
    """
    try:
        start = time.time()

        if not parquet_path.exists():
            return {
                'dataset': dataset_key,
                'status': 'SKIP',
                'reason': 'file_not_found',
                'elapsed': 0
            }

        file_size_mb = parquet_path.stat().st_size / (1024**2)

        # Read Parquet to get row count and schema
        local_df = duckdb.from_parquet(str(parquet_path))
        row_count = len(local_df)

        if dry_run:
            elapsed = time.time() - start
            return {
                'dataset': dataset_key,
                'status': 'DRY_RUN',
                'rows': row_count,
                'size_mb': file_size_mb,
                'elapsed': elapsed
            }

        if not md_conn:
            return {
                'dataset': dataset_key,
                'status': 'SKIP',
                'reason': 'no_motherduck_connection',
                'elapsed': 0
            }

        # Drop existing table if it exists
        try:
            md_conn.execute(f"DROP TABLE IF EXISTS {dataset_key}")
        except:
            pass

        # Create table in MotherDuck from local Parquet
        # Using CREATE TABLE AS SELECT for streaming inserts
        sql = f"""
        CREATE TABLE {dataset_key} AS
        SELECT * FROM read_parquet('{parquet_path}')
        """

        md_conn.execute(sql)

        elapsed = time.time() - start
        return {
            'dataset': dataset_key,
            'status': 'SUCCESS',
            'rows': row_count,
            'size_mb': file_size_mb,
            'elapsed': elapsed,
            'throughput_mb_per_sec': file_size_mb / elapsed if elapsed > 0 else 0
        }

    except Exception as e:
        elapsed = time.time() - start
        return {
            'dataset': dataset_key,
            'status': 'ERROR',
            'error': str(e)[:100],
            'elapsed': elapsed
        }

def main():
    parser = argparse.ArgumentParser(
        description='Populate MotherDuck with 26 NYC datasets from local Parquet cache'
    )
    parser.add_argument(
        '--datasets',
        nargs='+',
        help='Specific datasets to upload (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be uploaded without actually uploading'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel upload workers (default: 4)'
    )
    parser.add_argument(
        '--cache-dir',
        default='data/cache',
        help='Path to cached Parquet files (default: data/cache)'
    )

    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)

    # Determine which datasets to upload
    if args.datasets:
        datasets_to_upload = {k: v for k, v in DATASET_REGISTRY.items() if k in args.datasets}
    else:
        datasets_to_upload = DATASET_REGISTRY

    # Check which Parquet files exist
    available_files = {
        f.stem: f for f in cache_dir.glob('*.parquet')
    }

    print("=" * 80)
    print("Optimized MotherDuck Population Strategy")
    print("=" * 80)
    print(f"\nCache directory: {cache_dir}")
    print(f"Parquet files available: {len(available_files)}/26")
    print(f"Datasets to process: {len(datasets_to_upload)}")
    print(f"Parallel workers: {args.workers}")
    print(f"Dry-run: {args.dry_run}")

    # Connect to MotherDuck
    if args.dry_run:
        md_conn = None
        print("\n[DRY RUN] No MotherDuck connection needed")
    else:
        token = get_motherduck_token()
        md_conn = connect_motherduck(token) if token else None

    print("\n" + "=" * 80)
    print("Uploading Parquet files...")
    print("=" * 80 + "\n")

    results = []

    # Use ThreadPoolExecutor for parallel uploads
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}

        for dataset_key in datasets_to_upload:
            parquet_path = available_files.get(dataset_key)

            if not parquet_path:
                results.append({
                    'dataset': dataset_key,
                    'status': 'NOT_CACHED',
                    'elapsed': 0
                })
                continue

            future = executor.submit(
                upload_parquet_to_motherduck,
                md_conn,
                dataset_key,
                parquet_path,
                args.dry_run
            )
            futures[future] = dataset_key

        # Collect results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            dataset = result['dataset']
            status = result['status']

            if status == 'SUCCESS':
                print(
                    f"✓ {dataset:40s} {result['rows']:>10,} rows "
                    f"{result['size_mb']:>8.1f}MB {result['elapsed']:>6.1f}s "
                    f"({result['throughput_mb_per_sec']:.1f} MB/s)"
                )
            elif status == 'DRY_RUN':
                print(
                    f"📋 {dataset:40s} {result['rows']:>10,} rows "
                    f"{result['size_mb']:>8.1f}MB (would upload)"
                )
            elif status == 'NOT_CACHED':
                print(f"⏭️  {dataset:40s} NOT YET CACHED (skipped)")
            elif status == 'SKIP':
                print(f"⏭️  {dataset:40s} SKIPPED ({result.get('reason', 'unknown')})")
            else:
                print(
                    f"❌ {dataset:40s} ERROR: {result.get('error', 'unknown')}"
                )

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    success = sum(1 for r in results if r['status'] == 'SUCCESS')
    dry_run = sum(1 for r in results if r['status'] == 'DRY_RUN')
    not_cached = sum(1 for r in results if r['status'] == 'NOT_CACHED')
    errors = sum(1 for r in results if r['status'] == 'ERROR')

    print(f"\n✓ Successful uploads: {success}")
    print(f"📋 Dry-run (would upload): {dry_run}")
    print(f"⏭️  Not yet cached: {not_cached}")
    print(f"❌ Errors: {errors}")

    total_time = sum(r.get('elapsed', 0) for r in results)
    total_mb = sum(r.get('size_mb', 0) for r in results if r['status'] in ('SUCCESS', 'DRY_RUN'))

    if total_time > 0:
        print(f"\nTotal time: {total_time:.1f}s")
        print(f"Total data: {total_mb:.1f}MB")
        print(f"Throughput: {total_mb/total_time:.1f} MB/s")

    print("\n" + "=" * 80)

    if md_conn:
        md_conn.close()

    return 0 if errors == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
