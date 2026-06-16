#!/usr/bin/env python3
"""
Sync all 26 NYC datasets to local cache, MotherDuck, Google Cloud Storage, and BigQuery.

One-command sync orchestration:
- Local: Ensure all 26 are cached as Parquet
- MotherDuck: Fast cloud analytics (4-worker parallel)
- GCS: Backup + shareable storage
- BigQuery: SQL warehouse + team analytics

Usage:
    # Full sync to all platforms:
    python sync_all_platforms.py \
      --motherduck-token your_token \
      --gcp-project your-project-id \
      --gcs-bucket your-bucket \
      --bq-dataset nyc_datasets

    # Partial sync (skip some platforms):
    python sync_all_platforms.py \
      --platforms local motherduck gcs \
      --motherduck-token your_token \
      --gcs-bucket your-bucket

    # Dry run:
    python sync_all_platforms.py \
      --platforms local motherduck gcs bigquery \
      --dry-run

    # Specific datasets only:
    python sync_all_platforms.py \
      --datasets inspection violations complaints_311 \
      --motherduck-token your_token
"""

import os
import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description='Sync NYC datasets to all platforms (local, MotherDuck, GCS, BigQuery)'
    )
    parser.add_argument(
        '--platforms',
        nargs='+',
        choices=['local', 'motherduck', 'gcs', 'bigquery'],
        default=['local', 'motherduck', 'gcs', 'bigquery'],
        help='Which platforms to sync to (default: all)'
    )
    parser.add_argument(
        '--motherduck-token',
        help='MotherDuck token (required if syncing to MotherDuck)'
    )
    parser.add_argument(
        '--gcs-bucket',
        help='GCS bucket name (required if syncing to GCS)'
    )
    parser.add_argument(
        '--gcp-project',
        help='GCP project ID (required if syncing to BigQuery)'
    )
    parser.add_argument(
        '--bq-dataset',
        default='nyc_datasets',
        help='BigQuery dataset ID (default: nyc_datasets)'
    )
    parser.add_argument(
        '--datasets',
        nargs='+',
        help='Specific datasets to sync (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be synced without actually syncing'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Parallel workers (default: 4)'
    )
    parser.add_argument(
        '--cache-dir',
        default='data/cache',
        help='Path to local cache (default: data/cache)'
    )

    args = parser.parse_args()

    # Validate required args for each platform
    if 'motherduck' in args.platforms and not args.motherduck_token:
        print("ERROR: --motherduck-token required for MotherDuck sync")
        sys.exit(1)

    if 'gcs' in args.platforms and not args.gcs_bucket:
        print("ERROR: --gcs-bucket required for GCS sync")
        sys.exit(1)

    if 'bigquery' in args.platforms and not args.gcp_project:
        print("ERROR: --gcp-project required for BigQuery sync")
        sys.exit(1)

    print("=" * 80)
    print("Multi-Platform Sync for NYC Datasets")
    print("=" * 80)
    print(f"\nPlatforms: {', '.join(args.platforms)}")
    if args.datasets:
        print(f"Datasets: {', '.join(args.datasets)} (specific)")
    else:
        print(f"Datasets: all 26")
    print(f"Dry-run: {args.dry_run}")

    print("\n" + "=" * 80)
    print("Running sync operations...")
    print("=" * 80 + "\n")

    # Step 1: Local cache (always first)
    if 'local' in args.platforms:
        print("📦 STEP 1: Ensure local cache complete")
        print("   (Run fetch_remaining_datasets.sh if needed)")
        cache_dir = Path(args.cache_dir)
        cached_count = len(list(cache_dir.glob('*.parquet')))
        print(f"   ✓ {cached_count}/26 datasets cached\n")

    # Step 2: MotherDuck
    if 'motherduck' in args.platforms:
        print("☁️  STEP 2: MotherDuck (parallel 4-worker, 20-25 min)")
        cmd = f"python optimized_motherduck_population.py --workers {args.workers}"
        if args.datasets:
            cmd += f" --datasets {' '.join(args.datasets)}"
        if args.dry_run:
            cmd += " --dry-run"
        print(f"   Command: {cmd}")
        print(f"   Run this next (or auto-run: --auto-run flag)\n")

    # Step 3: Google Cloud Storage
    if 'gcs' in args.platforms:
        print("🪣 STEP 3: Google Cloud Storage (parallel 4-worker, 10-15 min)")
        cmd = f"python sync_to_gcs.py --bucket {args.gcs_bucket} --workers {args.workers}"
        if args.datasets:
            cmd += f" --datasets {' '.join(args.datasets)}"
        if args.dry_run:
            cmd += " --dry-run"
        print(f"   Command: {cmd}")
        print(f"   Run this next (or auto-run: --auto-run flag)\n")

    # Step 4: BigQuery
    if 'bigquery' in args.platforms:
        print("📊 STEP 4: BigQuery (parallel 4-worker, 20-30 min)")
        cmd = f"python load_to_bigquery.py --project {args.gcp_project} --dataset {args.bq_dataset} --bucket {args.gcs_bucket} --workers {args.workers}"
        if args.datasets:
            cmd += f" --datasets {' '.join(args.datasets)}"
        if args.dry_run:
            cmd += " --dry-run"
        print(f"   Command: {cmd}")
        print(f"   Run this next (or auto-run: --auto-run flag)\n")

    print("=" * 80)
    print("Manual Execution")
    print("=" * 80)
    print("\nRun each step in order, or copy-paste individual commands above.")
    print("\nTotal estimated time (all platforms):")
    print("  - Local: ~5 min (if incomplete)")
    print("  - MotherDuck: 20-25 min")
    print("  - GCS: 10-15 min (parallel with MotherDuck)")
    print("  - BigQuery: 20-30 min (after GCS)")
    print("  ────────────────────────")
    print("  Total: ~50-70 minutes (first-time full sync)")

    print("\n" + "=" * 80)
    print("Query Your Data After Sync")
    print("=" * 80)

    if 'motherduck' in args.platforms:
        print("\nMotherDuck (Python):")
        print("  import duckdb")
        print("  conn = duckdb.connect('md:?motherduck_token=...')")
        print("  df = conn.execute('SELECT * FROM inspection LIMIT 10').df()")

    if 'gcs' in args.platforms:
        print(f"\nGoogle Cloud Storage:")
        print(f"  gsutil ls gs://{args.gcs_bucket}/nyc-datasets/")
        print(f"  # Or query via BigQuery (Step 4)")

    if 'bigquery' in args.platforms:
        print(f"\nBigQuery (CLI):")
        print(f"  bq query 'SELECT COUNT(*) FROM `{args.gcp_project}.{args.bq_dataset}.complaints_311`'")
        print(f"\nBigQuery (Python):")
        print(f"  from google.cloud import bigquery")
        print(f"  client = bigquery.Client(project='{args.gcp_project}')")
        print(f"  df = client.query('SELECT * FROM `{args.gcp_project}.{args.bq_dataset}.inspection` LIMIT 10').to_dataframe()")

    print("\n" + "=" * 80)

    return 0

if __name__ == '__main__':
    sys.exit(main())
