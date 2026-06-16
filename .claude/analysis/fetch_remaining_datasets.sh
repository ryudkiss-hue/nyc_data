#!/bin/bash
# Fetch remaining 6 NYC datasets with clear progress tracking
# Works in bash, zsh, PowerShell (via WSL or git bash)

set -e

CACHE_DIR="data/cache"
PYTHONPATH="src:."

# Create cache directory
mkdir -p "$CACHE_DIR"

# Remaining 6 datasets
declare -A DATASETS=(
    [street_permits]="tqtj-sjs8"
    [street_construction_inspections]="ydkf-mpxb"
    [complaints_311]="erm2-nwe9"
    [mappluto]="64uk-42ks"
    [capital_blocks]="jvk9-k4re"
    [permit_stipulations]="gsgx-6efw"
)

echo "=================================================="
echo "Fetching Remaining 6 NYC Datasets"
echo "=================================================="
echo ""

CACHED=0
MISSING=0

for dataset in "${!DATASETS[@]}"; do
    fourfour="${DATASETS[$dataset]}"
    parquet_file="$CACHE_DIR/$dataset.parquet"

    if [ -f "$parquet_file" ]; then
        size=$(ls -lh "$parquet_file" | awk '{print $5}')
        echo "✓ $dataset - Already cached ($size)"
        CACHED=$((CACHED + 1))
    else
        echo ""
        echo "⬇️  Fetching $dataset ($fourfour)..."

        python3 << EOFETCH
import os
import sys
sys.path.insert(0, 'src')

from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from pathlib import Path
import time

config = SocrataConfig()
client = SocrataClient(config)
cache_dir = Path("$CACHE_DIR")

dataset = "$dataset"
fourfour = "$fourfour"
parquet_file = cache_dir / f"{dataset}.parquet"

try:
    start = time.time()
    print(f"   Connecting to Socrata API...")

    df = client.fetch_dataframe('data.cityofnewyork.us', fourfour, max_rows=None)

    if df.empty:
        print(f"   ⚠️  No data returned (empty dataset)")
        sys.exit(0)

    elapsed = time.time() - start

    df.to_parquet(str(parquet_file))
    size_mb = parquet_file.stat().st_size / (1024**2)

    print(f"   ✓ Success: {len(df):,} rows, {size_mb:.1f}MB ({elapsed:.1f}s)")

except Exception as e:
    error = str(e)
    if '403' in error:
        print(f"   🚫 API Error 403 (permissions issue)")
    elif 'empty' in error.lower() or '0 rows' in error.lower():
        print(f"   ⚠️  Empty dataset")
    else:
        print(f"   ❌ Error: {error[:100]}")
    sys.exit(1)

EOFETCH

        if [ $? -eq 0 ]; then
            CACHED=$((CACHED + 1))
        else
            MISSING=$((MISSING + 1))
        fi

        sleep 2
    fi
done

echo ""
echo "=================================================="
echo "Summary"
echo "=================================================="
TOTAL=$((CACHED + MISSING))
echo "Cached: $CACHED/6 remaining datasets"
echo "Failed: $MISSING/6"
echo ""

# Show final cache status
CACHE_COUNT=$(ls -1 "$CACHE_DIR"/*.parquet 2>/dev/null | wc -l)
echo "Total cached: $CACHE_COUNT/26 datasets"

if [ $CACHE_COUNT -eq 26 ]; then
    echo ""
    echo "✅ All 26 datasets cached!"
    echo ""
    echo "Next steps:"
    echo "  1. Load all 26 into DuckDB:"
    echo "     python .claude/analysis/complete_26_dataset_pipeline.py"
    echo ""
    echo "  2. Populate MotherDuck (optional, faster analytics):"
    echo "     python .claude/analysis/optimized_motherduck_population.py"
else
    echo ""
    echo "⏳ Still waiting for $((26 - CACHE_COUNT)) datasets..."
fi
