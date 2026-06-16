"""
Optimized parallel data fetching for remaining 23 datasets
Strategy: Group by size class, fetch in parallel with retry logic
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
import time

def fetch_dataset(client, domain, key, fourfour, cache_dir, max_retries=3):
    """Fetch single dataset with retry logic"""
    for attempt in range(max_retries):
        try:
            df = client.fetch_dataframe(domain, fourfour)
            row_count = len(df)
            cache_file = cache_dir / f"{key}.parquet"
            df.to_parquet(cache_file, compression='snappy', index=False)
            return {
                'key': key,
                'fourfour': fourfour,
                'rows': row_count,
                'status': 'SUCCESS',
                'attempt': attempt + 1
            }
        except Exception as e:
            if attempt == max_retries - 1:
                return {
                    'key': key,
                    'fourfour': fourfour,
                    'error': str(e)[:60],
                    'status': 'FAILED',
                    'attempts': max_retries
                }
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

# Already cached
cached = {p.stem for p in Path('data/cache').glob('*.parquet')}

# All 26 datasets
all_datasets = {
    'inspection': 'dntt-gqwq',
    'violations': '6kbp-uz6m',
    'built': 'ugc8-s3f6',
    'lot_info': 'i642-2fxq',
    'reinspection': 'gx72-kirf',
    'tree_damage': 'j6v2-6uxq',
    'dismissals': 'p4u2-3jgx',
    'correspondences': 'bheb-sjfi',
    'curb_metal_protruding': 'i2y3-sx2e',
    'ramp_locations': 'ufzp-rrqu',
    'ramp_complaints': 'jagj-gttd',
    'ramp_progress': 'e7gc-ub6z',
    'street_permits': 'tqtj-sjs8',
    'weekly_construction': 'r528-jcks',
    'capital_blocks': 'jvk9-k4re',
    'capital_intersections': '97nd-ff3i',
    'street_construction_inspections': 'ydkf-mpxb',
    'street_closures_block': 'i6b5-j7bu',
    'permit_stipulations': 'gsgx-6efw',
    'street_resurfacing_schedule': 'xnfm-u3k5',
    'street_resurfacing_inhouse': 'ffaf-8mrv',
    'step_streets': 'u9au-h79y',
    'sidewalk_planimetric': 'vfx9-tbb6',
    'pedestrian_demand': 'fwpa-qxaf',
    'mappluto': '64uk-42ks',
    'complaints_311': 'erm2-nwe9',
}

# Groupby size (estimated)
small = {k: v for k, v in all_datasets.items() if k in ['step_streets', 'ramp_complaints', 'weekly_construction', 'capital_intersections', 'street_closures_block', 'permit_stipulations', 'curb_metal_protruding', 'correspondences', 'reinspection']}
medium = {k: v for k, v in all_datasets.items() if k in ['tree_damage', 'dismissals', 'ramp_locations', 'ramp_progress', 'built', 'sidewalk_planimetric', 'pedestrian_demand', 'street_resurfacing_schedule', 'street_resurfacing_inhouse']}
large = {k: v for k, v in all_datasets.items() if k in ['lot_info', 'street_permits', 'street_construction_inspections', 'mappluto', 'complaints_311']}

remaining = {k: v for k, v in all_datasets.items() if k not in cached}

print("\n" + "=" * 70)
print("OPTIMIZED PARALLEL FETCH — ALL 26 DATASETS")
print("=" * 70)
print(f"\nAlready cached: {len(cached)}")
print(f"Remaining: {len(remaining)}\n")
print(f"Small datasets ({len([k for k in small if k in remaining])}):")
for k in small:
    if k in remaining:
        print(f"  {k}")

print(f"\nMedium datasets ({len([k for k in medium if k in remaining])}):")
for k in medium:
    if k in remaining:
        print(f"  {k}")

print(f"\nLarge datasets ({len([k for k in large if k in remaining])}):")
for k in large:
    if k in remaining:
        print(f"  {k}")

client = SocrataClient(SocrataConfig())
cache_dir = Path('data/cache')
cache_dir.mkdir(parents=True, exist_ok=True)
domain = 'data.cityofnewyork.us'

all_results = {}
start_time = time.time()

# Fetch small + medium in parallel (lower timeout risk)
batch_1 = {**{k: v for k, v in small.items() if k in remaining}, 
           **{k: v for k, v in medium.items() if k in remaining}}

print(f"\n[BATCH 1] Small + Medium ({len(batch_1)} datasets) — Parallel fetch:")
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(fetch_dataset, client, domain, k, v, cache_dir): k 
        for k, v in batch_1.items()
    }
    
    for future in as_completed(futures):
        result = future.result()
        if result:
            all_results[result['key']] = result
            status = "✓" if result['status'] == 'SUCCESS' else "✗"
            rows = f"{result['rows']:,}" if 'rows' in result else result.get('error', '')
            print(f"  {status} {result['key']:30s} {rows}")

# Fetch large sequentially (higher timeout tolerance needed)
batch_2 = {k: v for k, v in large.items() if k in remaining}

print(f"\n[BATCH 2] Large datasets ({len(batch_2)} datasets) — Sequential fetch (retry strategy):")
for key, fourfour in batch_2.items():
    result = fetch_dataset(client, domain, key, fourfour, cache_dir, max_retries=3)
    if result:
        all_results[result['key']] = result
        status = "✓" if result['status'] == 'SUCCESS' else "✗"
        rows = f"{result['rows']:,}" if 'rows' in result else result.get('error', '')
        print(f"  {status} {result['key']:30s} {rows}")

# Summary
success = sum(1 for r in all_results.values() if r.get('status') == 'SUCCESS')
total_new_rows = sum(r.get('rows', 0) for r in all_results.values())
total_cached = len(list(Path('data/cache').glob('*.parquet')))
elapsed = time.time() - start_time

print("\n" + "=" * 70)
print(f"✓ New datasets fetched: {success}/{len(remaining)}")
print(f"✓ Total cached: {total_cached}/26")
print(f"✓ New rows: {total_new_rows:,}")
print(f"⏱️  Elapsed: {elapsed:.1f}s")
print("=" * 70 + "\n")

# Save results
report_path = Path('.claude/analysis/parallel_fetch_report.json')
with open(report_path, 'w') as f:
    json.dump({
        'optimization': 'parallel_batch_fetch',
        'timestamp': datetime.now().isoformat(),
        'batch_1_count': len(batch_1),
        'batch_2_count': len(batch_2),
        'total_fetched': success,
        'total_rows': total_new_rows,
        'total_cached': total_cached,
        'elapsed_seconds': elapsed,
        'results': all_results
    }, f, indent=2)

print(f"Report: {report_path}")

