#!/usr/bin/env python3
"""Local-only nightly refresh — no MotherDuck, no cloud compute limit.

Runs the full end-to-end pipeline against ./nyc_dot_analytics.duckdb (cwd = repo
root), the same local file run_pipeline.py's MotherDuckBridge falls back to when
MOTHERDUCK_TOKEN is unset. MOTHERDUCK_TOKEN is force-removed from the child env so
every stage — including the geo/Metric builders — uses the local DuckDB file.

Stages (stop on first failure):
  1. run_pipeline.py            ingest -> staging -> analytics -> SQL Metrics -> 4 gates
  2. geo/conform.py             borough/NTA/BBL/segment/date stamping
  3. geo/split_layers.py        spatial length/area metrics
  4. metric/build_metrics.py          Metric catalog + by-borough
  5. metric/build_metrics_advanced.py advanced Metrics

Exit 0 only if every stage succeeds; otherwise 1.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STAGES = [
    ("pipeline", ["pipeline/run_pipeline.py"]),
    ("ingest:ct66_daily", ["pipeline/ingest_ct66_daily.py"]),  # 20.5M counts -> daily aggregate
    ("geo:conform", ["pipeline/geo/conform.py"]),
    ("geo:split_layers", ["pipeline/geo/split_layers.py"]),
    ("metric:build_metrics", ["pipeline/metric/build_metrics.py"]),
    ("metric:build_metrics_advanced", ["pipeline/metric/build_metrics_advanced.py"]),
    ("analytics:phase_b_f", ["pipeline/analytics/build_phase_analytics.py"]),  # real Moran's I, anomalies, decomp, bootstrap CIs
    ("serving:app_views", ["pipeline/serving/build_app_views.py"]),  # real app_queries.* from serving (no synthetic)
    ("compact", ["pipeline/compact_local.py"]),  # reclaim space, drop scratch schemas
    ("publish:serving", ["pipeline/publish_serving.py"]),  # push small serving layer -> MotherDuck
]


def main() -> int:
    env = dict(os.environ)
    env.pop("MOTHERDUCK_TOKEN", None)  # run_pipeline reads env directly
    env["NYC_FORCE_LOCAL"] = "1"  # geo/Metric builders re-load .env, so force local explicitly
    env["NYC_INCREMENTAL"] = "1"  # skip datasets whose Socrata last_updated is unchanged

    db = ROOT / "nyc_dot_analytics.duckdb"
    print(f"Local-only run -> {db}\n")

    failed = []
    for name, script in STAGES:
        print(f"\n{'=' * 70}\nLOCAL STAGE: {name}\n{'=' * 70}", flush=True)
        rc = subprocess.run([sys.executable, *script], cwd=ROOT, env=env).returncode
        if rc != 0:
            print(f"FAILED: {name} (exit {rc})", flush=True)
            failed.append(name)
            break

    print(f"\n{'=' * 70}")
    if failed:
        print(f"LOCAL PIPELINE FAILED at: {', '.join(failed)}")
        return 1
    print(f"LOCAL PIPELINE SUCCESS — all stages complete -> {db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
