#!/usr/bin/env python3
"""
Real-time dataset cache monitoring dashboard.

Tracks which of the 26 NYC datasets are cached locally and remotely,
with file sizes, row counts, and freshness status.

Works in terminal (Linux/Mac) and PowerShell (Windows).

Usage:
    python dataset_cache_monitor.py

    Or watch live:
    python dataset_cache_monitor.py --watch 5  (updates every 5 seconds)
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

# Dataset registry: {key: fourfour_code}
REGISTRY = {
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

def format_size(bytes_val):
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}TB"

def get_row_count(parquet_path):
    """Get row count from Parquet file (fast)."""
    try:
        import duckdb
        result = duckdb.execute(f"SELECT COUNT(*) as count FROM read_parquet('{parquet_path}')").fetchall()
        return result[0][0] if result else 0
    except:
        return None

def get_motherduck_status():
    """Check MotherDuck connection status."""
    try:
        import duckdb
        token = os.getenv('MOTHERDUCK_TOKEN')
        if not token:
            return 'NO_TOKEN'
        conn = duckdb.connect(f'md:?motherduck_token={token}')
        conn.execute("SELECT 1")
        conn.close()
        return 'CONNECTED'
    except Exception as e:
        if 'token' in str(e).lower():
            return 'INVALID_TOKEN'
        return 'DISCONNECTED'

def get_duckdb_status():
    """Check local DuckDB status."""
    try:
        import duckdb
        db_path = Path('data/local_db/nyc_mission_control.duckdb')
        if not db_path.exists():
            return 'NOT_CREATED'
        conn = duckdb.connect(str(db_path))
        result = conn.execute("SELECT COUNT(*) FROM information_schema.tables").fetchall()
        table_count = result[0][0] if result else 0
        conn.close()
        return f'OK ({table_count} tables)'
    except Exception as e:
        return f'ERROR: {str(e)[:30]}'

def print_status_table(cache_dir='data/cache', show_row_counts=False):
    """Print status table of all datasets."""
    cache_path = Path(cache_dir)
    cached_files = {f.stem: f for f in cache_path.glob('*.parquet')}

    # Sort by status (cached first) then by name
    sorted_keys = sorted(
        REGISTRY.keys(),
        key=lambda k: (k not in cached_files, k)
    )

    print("\n" + "=" * 120)
    print(f"{'Dataset':<40} {'Status':<12} {'Size':>12} {'Rows':>15} {'Modified':>20}")
    print("=" * 120)

    cached_count = 0
    total_size = 0

    for key in sorted_keys:
        parquet_file = cached_files.get(key)

        if parquet_file:
            cached_count += 1
            size = parquet_file.stat().st_size
            total_size += size
            size_str = format_size(size)

            # Get modification time
            mtime = parquet_file.stat().st_mtime
            mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

            # Get row count (optional, can be slow for large files)
            if show_row_counts:
                row_count = get_row_count(str(parquet_file))
                rows_str = f"{row_count:,}" if row_count is not None else "?"
            else:
                rows_str = "-"

            status = "✓ CACHED"
        else:
            size_str = "-"
            rows_str = "-"
            mtime_str = "-"
            status = "⏳ PENDING"

        print(f"{key:<40} {status:<12} {size_str:>12} {rows_str:>15} {mtime_str:>20}")

    print("=" * 120)
    print(f"\nSummary: {cached_count}/26 datasets cached ({total_size / (1024**2):.1f}MB)")
    print(f"Missing: {26 - cached_count}")

    return cached_count

def print_storage_summary(cache_dir='data/cache'):
    """Print storage summary."""
    cache_path = Path(cache_dir)
    total_size = 0
    file_count = 0

    for f in cache_path.glob('*.parquet'):
        total_size += f.stat().st_size
        file_count += 1

    print(f"\nStorage Summary:")
    print(f"  Cached files: {file_count}")
    print(f"  Total size: {format_size(total_size)}")

    # Estimate full corpus size (based on Socrata row counts)
    estimated_full = {
        'inspection': 398_000 * 200,      # ~80MB estimate
        'violations': 312_000 * 150,      # ~47MB estimate
        'complaints_311': 21_300_000 * 100,  # ~2.1GB estimate
        'street_permits': 3_600_000 * 150,   # ~540MB estimate
        'street_construction_inspections': 11_500_000 * 100,  # ~1.15GB estimate
        'mappluto': 858_000 * 300,        # ~257MB estimate
    }
    estimated_total = sum(estimated_full.values()) / (1024**2)  # Convert to MB

    print(f"  Estimated full corpus: {format_size(estimated_total * 1024**2)}")

def print_system_status(cache_dir='data/cache'):
    """Print system status summary."""
    print("\n" + "=" * 120)
    print("System Status")
    print("=" * 120)

    print(f"\nLocal DuckDB: {get_duckdb_status()}")
    print(f"MotherDuck:   {get_motherduck_status()}")

    cache_path = Path(cache_dir)
    if cache_path.exists():
        total_size = sum(f.stat().st_size for f in cache_path.glob('*.parquet'))
        print(f"Cache directory: {cache_path.absolute()}")
        print(f"  Size: {format_size(total_size)}")

    print(f"\nEnvironment:")
    print(f"  SOCRATA_APP_TOKEN: {'***set***' if os.getenv('SOCRATA_APP_TOKEN') else 'NOT SET'}")
    print(f"  MOTHERDUCK_TOKEN: {'***set***' if os.getenv('MOTHERDUCK_TOKEN') else 'NOT SET'}")

def main():
    parser = argparse.ArgumentParser(
        description='Real-time dataset cache monitoring dashboard'
    )
    parser.add_argument(
        '--watch',
        type=int,
        help='Watch mode: refresh every N seconds'
    )
    parser.add_argument(
        '--row-counts',
        action='store_true',
        help='Show row counts (slower, scans Parquet metadata)'
    )
    parser.add_argument(
        '--cache-dir',
        default='data/cache',
        help='Path to cache directory (default: data/cache)'
    )

    args = parser.parse_args()

    if args.watch:
        try:
            iteration = 0
            while True:
                # Clear screen (works on most terminals)
                os.system('clear' if os.name == 'posix' else 'cls')

                print(f"\n📊 Dataset Cache Monitor (updated every {args.watch}s)")
                print(f"   Iteration {iteration + 1} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                cached_count = print_status_table(args.cache_dir, args.row_counts)
                print_storage_summary(args.cache_dir)
                print_system_status(args.cache_dir)

                if cached_count == 26:
                    print("\n✅ All 26 datasets cached! Ready for analysis.")
                    break

                print(f"\nNext update in {args.watch}s (Press Ctrl+C to stop)...")
                iteration += 1
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n\nMonitor stopped.")
    else:
        print(f"\n📊 Dataset Cache Monitor")
        print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        cached_count = print_status_table(args.cache_dir, args.row_counts)
        print_storage_summary(args.cache_dir)
        print_system_status(args.cache_dir)

        if cached_count == 26:
            print("\n✅ All 26 datasets cached! Ready for analysis.")
        else:
            print(f"\n⏳ Waiting for remaining {26 - cached_count} datasets...")
            print(f"\nTo watch progress live, run:")
            print(f"  python .claude/analysis/dataset_cache_monitor.py --watch 5")

if __name__ == '__main__':
    main()
