#!/usr/bin/env python3
"""
Load all 26 NYC datasets into Google BigQuery.

Loads Parquet files from GCS or local cache into BigQuery dataset with
automatic table creation, schema inference, and partition setup for large tables.

Usage:
    # Load from GCS (recommended for large files):
    python load_to_bigquery.py \
      --project your-gcp-project \
      --dataset nyc_datasets \
      --bucket your-gcs-bucket

    # Load from local cache:
    python load_to_bigquery.py \
      --project your-gcp-project \
      --dataset nyc_datasets \
      --source local

    # Load specific datasets only:
    python load_to_bigquery.py \
      --project your-gcp-project \
      --dataset nyc_datasets \
      --datasets inspection violations ramp_progress

    # Dry run (show what would be loaded):
    python load_to_bigquery.py \
      --project your-gcp-project \
      --dataset nyc_datasets \
      --dry-run

Setup:
    1. Create GCS bucket: gsutil mb gs://your-bucket-name
    2. Upload data: python sync_to_gcs.py --bucket your-bucket-name
    3. Create BQ dataset: bq mk nyc_datasets
    4. Run this script
"""

import os
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from google.cloud import bigquery
    from google.cloud import storage
except ImportError:
    print("ERROR: google-cloud-bigquery not installed.")
    print("Install with: pip install google-cloud-bigquery google-cloud-storage")
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

def load_to_bigquery(
    bq_client: bigquery.Client,
    project_id: str,
    dataset_id: str,
    table_key: str,
    gcs_path: str = None,
    local_path: Path = None,
    dry_run: bool = False
) -> dict:
    """Load a single Parquet file to BigQuery."""
    try:
        start = time.time()
        table_id = f"{project_id}.{dataset_id}.{table_key}"

        # Determine source
        if gcs_path:
            source_uri = gcs_path
            source_type = "GCS"
        elif local_path and local_path.exists():
            source_uri = str(local_path)
            source_type = "local"
        else:
            return {
                'table': table_key,
                'status': 'SKIP',
                'reason': 'file_not_found',
                'elapsed': 0
            }

        if dry_run:
            elapsed = time.time() - start
            return {
                'table': table_key,
                'status': 'DRY_RUN',
                'table_id': table_id,
                'source': source_uri,
                'source_type': source_type,
                'elapsed': elapsed
            }

        # Configure load job
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            skip_leading_rows=0,
            autodetect=True,  # Auto-detect schema from Parquet
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Replace if exists
        )

        # For very large tables, consider partitioning by date
        # (Inspect schema after load to determine if date_column exists)

        # Load job
        load_job = bq_client.load_table_from_uri(
            source_uri,
            table_id,
            job_config=job_config
        )

        load_job.result()  # Wait for job to complete

        elapsed = time.time() - start
        dest_table = bq_client.get_table(table_id)

        return {
            'table': table_key,
            'status': 'SUCCESS',
            'table_id': table_id,
            'rows': dest_table.num_rows,
            'size_bytes': dest_table.num_bytes,
            'elapsed': elapsed,
            'throughput_rows_per_sec': dest_table.num_rows / elapsed if elapsed > 0 else 0
        }

    except Exception as e:
        elapsed = time.time() - start
        return {
            'table': table_key,
            'status': 'ERROR',
            'error': str(e)[:100],
            'elapsed': elapsed
        }

def main():
    parser = argparse.ArgumentParser(
        description='Load NYC datasets to Google BigQuery'
    )
    parser.add_argument(
        '--project',
        required=True,
        help='GCP project ID'
    )
    parser.add_argument(
        '--dataset',
        required=True,
        help='BigQuery dataset ID (will be created if not exists)'
    )
    parser.add_argument(
        '--bucket',
        help='GCS bucket name (for loading from GCS). If not provided, loads from local cache.'
    )
    parser.add_argument(
        '--source',
        choices=['gcs', 'local'],
        default='gcs',
        help='Data source: gcs (from GCS bucket) or local (from cache dir)'
    )
    parser.add_argument(
        '--datasets',
        nargs='+',
        help='Specific datasets to load (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be loaded without actually loading'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel load workers (default: 4)'
    )
    parser.add_argument(
        '--cache-dir',
        default='data/cache',
        help='Path to local cache (for --source local)'
    )

    args = parser.parse_args()

    # Determine which datasets to load
    if args.datasets:
        datasets_to_load = {k: v for k, v in DATASET_REGISTRY.items() if k in args.datasets}
    else:
        datasets_to_load = DATASET_REGISTRY

    # Validate source
    if args.source == 'gcs' and not args.bucket:
        print("ERROR: --bucket required when --source gcs")
        sys.exit(1)

    cache_dir = Path(args.cache_dir)
    available_files = {f.stem: f for f in cache_dir.glob('*.parquet')}

    print("=" * 80)
    print("Load to Google BigQuery")
    print("=" * 80)
    print(f"\nProject: {args.project}")
    print(f"Dataset: {args.dataset}")
    if args.bucket:
        print(f"Source: GCS (gs://{args.bucket}/nyc-datasets/)")
    else:
        print(f"Source: Local cache ({cache_dir})")
    print(f"Datasets to load: {len(datasets_to_load)}")
    print(f"Parallel workers: {args.workers}")
    print(f"Dry-run: {args.dry_run}")

    # Authenticate with BigQuery
    if not args.dry_run:
        bq_client = bigquery.Client(project=args.project)
        print(f"\n✓ Authenticated with BigQuery")

        # Create dataset if not exists
        try:
            dataset = bq_client.get_dataset(f"{args.project}.{args.dataset}")
            print(f"✓ Dataset exists: {args.dataset}")
        except:
            dataset = bigquery.Dataset(f"{args.project}.{args.dataset}")
            dataset.location = "US"
            dataset = bq_client.create_dataset(dataset)
            print(f"✓ Created dataset: {args.dataset}")

    print("\n" + "=" * 80)
    print("Loading to BigQuery...")
    print("=" * 80 + "\n")

    results = []

    # Use ThreadPoolExecutor for parallel loads
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}

        for dataset_key in datasets_to_load:
            # Determine source path
            if args.source == 'gcs' or args.bucket:
                gcs_path = f"gs://{args.bucket}/nyc-datasets/{dataset_key}.parquet" if args.bucket else None
                local_path = None
            else:
                gcs_path = None
                local_path = available_files.get(dataset_key)

            if not gcs_path and not local_path:
                results.append({
                    'table': dataset_key,
                    'status': 'NOT_FOUND',
                    'elapsed': 0
                })
                continue

            future = executor.submit(
                load_to_bigquery,
                bq_client if not args.dry_run else None,
                args.project,
                args.dataset,
                dataset_key,
                gcs_path=gcs_path,
                local_path=local_path,
                dry_run=args.dry_run
            )
            futures[future] = dataset_key

        # Collect results
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            table = result['table']
            status = result['status']

            if status == 'SUCCESS':
                size_mb = result['size_bytes'] / (1024**2) if result.get('size_bytes') else 0
                print(
                    f"✓ {table:40s} {result['rows']:>10,} rows "
                    f"{size_mb:>8.1f}MB {result['elapsed']:>6.1f}s"
                )
            elif status == 'DRY_RUN':
                print(
                    f"📋 {table:40s} {result['source_type']:>6s} "
                    f"→ {result['table_id']}"
                )
            elif status == 'NOT_FOUND':
                print(f"⏭️  {table:40s} NOT FOUND (skipped)")
            elif status == 'SKIP':
                print(f"⏭️  {table:40s} SKIPPED ({result.get('reason', 'unknown')})")
            else:
                print(
                    f"❌ {table:40s} ERROR: {result.get('error', 'unknown')}"
                )

    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    success = sum(1 for r in results if r['status'] == 'SUCCESS')
    dry_run = sum(1 for r in results if r['status'] == 'DRY_RUN')
    not_found = sum(1 for r in results if r['status'] == 'NOT_FOUND')
    errors = sum(1 for r in results if r['status'] == 'ERROR')

    print(f"\n✓ Successfully loaded: {success}")
    print(f"📋 Dry-run (would load): {dry_run}")
    print(f"⏭️  Not found: {not_found}")
    print(f"❌ Errors: {errors}")

    total_rows = sum(r.get('rows', 0) for r in results if r['status'] == 'SUCCESS')
    total_time = sum(r.get('elapsed', 0) for r in results)

    if total_rows > 0:
        print(f"\nTotal rows loaded: {total_rows:,}")
        if total_time > 0:
            print(f"Total time: {total_time:.1f}s")
            print(f"Throughput: {total_rows/total_time:.0f} rows/sec")

    print("\n" + "=" * 80)
    print("Query your data in BigQuery:")
    print(f"  bq query --use_legacy_sql=false 'SELECT * FROM `{args.project}.{args.dataset}.inspection` LIMIT 10'")
    print("\nOr via Python:")
    print(f"  from google.cloud import bigquery")
    print(f"  client = bigquery.Client(project='{args.project}')")
    print(f"  df = client.query('SELECT COUNT(*) FROM `{args.project}.{args.dataset}.complaints_311`').to_dataframe()")

    print("\n" + "=" * 80)

    return 0 if errors == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
