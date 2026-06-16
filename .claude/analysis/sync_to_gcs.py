#!/usr/bin/env python3
"""
Sync NYC datasets to Google Cloud Storage (GCS).

Fast parallel upload of all 26 Parquet files from local cache to GCS bucket.
Enables shared access, backup, and direct querying from GCS via BigQuery/DuckDB.

Usage:
    # First-time setup:
    gcloud auth login
    gsutil mb gs://your-bucket-name

    # Then sync:
    python sync_to_gcs.py --bucket your-bucket-name

    # Watch progress:
    python sync_to_gcs.py --bucket your-bucket-name --watch 5

    # Dry run (show what would upload):
    python sync_to_gcs.py --bucket your-bucket-name --dry-run

    # Specific datasets only:
    python sync_to_gcs.py --bucket your-bucket-name --datasets inspection violations ramp_progress
"""

import os
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from google.cloud import storage
except ImportError:
    print("ERROR: google-cloud-storage not installed.")
    print("Install with: pip install google-cloud-storage")
    sys.exit(1)

# Registry of all 26 NYC datasets
DATASET_REGISTRY = {
    'inspection': 'dntt-gqwq',
    'violations': '6kbp-uz6m',
    'built': 'ugc8-s3f6',
    'lot_info': 'i642-2fxq',
    'reinspection': 'gx72-kirf',
    'correspondences': 'bheb-sjfi',
    'tree_damage': 'j6v2-6uxq',
    'dismissals': 'p4u2-3jgx',
    'curb_metal_protruding': 'i2y3-sx2e',
    'ramp_progress': 'e7gc-ub6z',
    'ramp_complaints': 'jagj-gttd',
    'ramp_locations': 'ufzp-rrqu',
    'street_permits': 'tqtj-sjs8',
    'street_construction_inspections': 'ydkf-mpxb',
    'capital_intersections': '97nd-ff3i',
    'street_closures_block': 'i6b5-j7bu',
    'permit_stipulations': 'gsgx-6efw',
    'street_resurfacing_schedule': 'xnfm-u3k5',
    'street_resurfacing_inhouse': 'ffaf-8mrv',
    'weekly_construction': 'r528-jcks',
    'capital_blocks': 'jvk9-k4re',
    'complaints_311': 'erm2-nwe9',
    'pedestrian_demand': 'fwpa-qxaf',
    'mappluto': '64uk-42ks',
    'sidewalk_planimetric': 'vfx9-tbb6',
    'step_streets': 'u9au-h79y',
}

def get_gcs_client() -> storage.Client:
    """Get authenticated GCS client."""
    try:
        return storage.Client()
    except Exception as e:
        print(f"ERROR: Failed to authenticate with GCS: {e}")
        print("\nTo authenticate:")
        print("  1. gcloud auth login")
        print("  2. gcloud auth application-default login")
        sys.exit(1)

def upload_to_gcs(
    client: storage.Client,
    bucket_name: str,
    dataset_key: str,
    parquet_path: Path,
    dry_run: bool = False
) -> dict:
    """Upload single Parquet file to GCS."""
    try:
        if not parquet_path.exists():
            return {
                'dataset': dataset_key,
                'status': 'SKIP',
                'reason': 'file_not_found',
                'elapsed': 0
            }

        file_size_mb = parquet_path.stat().st_size / (1024**2)
        start = time.time()

        if dry_run:
            elapsed = time.time() - start
            gcs_path = f"gs://{bucket_name}/nyc-datasets/{dataset_key}.parquet"
            return {
                'dataset': dataset_key,
                'status': 'DRY_RUN',
                'gcs_path': gcs_path,
                'size_mb': file_size_mb,
                'elapsed': elapsed
            }

        # Upload to GCS
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"nyc-datasets/{dataset_key}.parquet")
        blob.upload_from_filename(str(parquet_path))

        elapsed = time.time() - start
        gcs_path = f"gs://{bucket_name}/nyc-datasets/{dataset_key}.parquet"

        return {
            'dataset': dataset_key,
            'status': 'SUCCESS',
            'gcs_path': gcs_path,
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
        description='Upload NYC datasets to Google Cloud Storage'
    )
    parser.add_argument(
        '--bucket',
        required=True,
        help='GCS bucket name (e.g., your-bucket-name)'
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
    available_files = {f.stem: f for f in cache_dir.glob('*.parquet')}

    print("=" * 80)
    print("Google Cloud Storage Upload")
    print("=" * 80)
    print(f"\nBucket: gs://{args.bucket}/nyc-datasets/")
    print(f"Parquet files available: {len(available_files)}/26")
    print(f"Datasets to upload: {len(datasets_to_upload)}")
    print(f"Parallel workers: {args.workers}")
    print(f"Dry-run: {args.dry_run}")

    # Authenticate with GCS
    if not args.dry_run:
        client = get_gcs_client()
        print(f"✓ Authenticated with GCS")

    print("\n" + "=" * 80)
    print("Uploading to GCS...")
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
                upload_to_gcs,
                client if not args.dry_run else None,
                args.bucket,
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
                    f"✓ {dataset:40s} {result['size_mb']:>8.1f}MB "
                    f"{result['elapsed']:>6.1f}s ({result['throughput_mb_per_sec']:.1f} MB/s)"
                )
            elif status == 'DRY_RUN':
                print(
                    f"📋 {dataset:40s} {result['size_mb']:>8.1f}MB "
                    f"→ {result['gcs_path']}"
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
    print("Query your data in GCS:")
    print(f"  gcloud storage ls gs://{args.bucket}/nyc-datasets/")
    print("\nOr query via BigQuery (next step):")
    print(f"  python load_to_bigquery.py --bucket {args.bucket}")

    print("\n" + "=" * 80)

    return 0 if errors == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
