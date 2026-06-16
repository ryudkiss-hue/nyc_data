#!/bin/bash
set -a && source .env && set +a

echo ""
echo "========================================================================"
echo "NYC DOT LIVE DATA PIPELINE ORCHESTRATOR"
echo "========================================================================"
echo ""

# Load env and set git config for commits
git config user.email noreply@anthropic.com
git config user.name Claude

# Phase 2: Data Ingestion (already running in background or execute here)
echo "✓ Phase 2: Data ingestion (running or completed)"
echo ""

# Wait for cache to be populated
echo "Waiting for cached datasets..."
while [ ! -d "data/cache" ] || [ $(ls -1 data/cache/*.parquet 2>/dev/null | wc -l) -lt 26 ]; do
    echo "  $(date +%H:%M:%S) — $(ls -1 data/cache/*.parquet 2>/dev/null | wc -l)/26 datasets cached"
    sleep 10
done

echo "✓ Phase 2 Complete: All 26 datasets cached"
echo ""

# Phase 3: DuckDB Population
echo "Running Phase 3: DuckDB Population..."
python3 /home/user/nyc_data/.claude/analysis/phase3_duckdb_load.py

if [ ! -f "data/local_db/nyc_mission_control.duckdb" ]; then
    echo "✗ Phase 3 failed: DuckDB not created"
    exit 1
fi

echo "✓ Phase 3 Complete"
echo ""

# Phases 4-6: Quality, Analysis, Reporting
echo "Running Phases 4-6: Quality Assessment, Analysis, and Reporting..."
python3 /home/user/nyc_data/.claude/analysis/phases_4_5_6.py

echo ""
echo "========================================================================"
echo "✅ FULL PIPELINE COMPLETE"
echo "========================================================================"
echo ""
echo "Generated reports:"
ls -lh data/reports/**/* .claude/analysis/*.json 2>/dev/null | grep -E "json|xlsx|html"
echo ""

