#!/usr/bin/env python3
"""
Phase 3C-3: Ingestion Progress Monitor
Reads execution.json and watermarks.json, prints dataset status, rows, and elapsed time.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def load_execution_log(log_file: str = 'pipeline/logs/execution.json') -> Dict:
    """Load execution log from file."""
    try:
        with open(log_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def load_watermarks(watermarks_file: str = 'pipeline/state/watermarks.json') -> Dict:
    """Load watermark file for incremental tracking."""
    try:
        with open(watermarks_file) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def calculate_elapsed_time(started_at: str, ended_at: str = None) -> str:
    """Calculate elapsed time between two ISO timestamps."""
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at) if ended_at else datetime.now()
        elapsed = (end - start).total_seconds()
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except (ValueError, TypeError):
        return "N/A"


def print_stage_summary(execution_log: Dict) -> None:
    """Print summary of all pipeline stages."""
    print("\n" + "=" * 80)
    print("PIPELINE STAGES SUMMARY")
    print("=" * 80)

    stages = execution_log.get('stages', {})
    for stage_name, stage_info in stages.items():
        status = stage_info.get('status', 'unknown').upper()
        timestamp = stage_info.get('timestamp', 'N/A')
        load_time = stage_info.get('load_time_seconds', 0)

        status_icon = "[OK]" if status == "SUCCESS" else "[FAIL]" if status == "FAILED" else "[--]"
        print(f"{status_icon} {stage_name:30s} | {status:8s} | {load_time:.1f}s | {timestamp}")


def print_dataset_summary(execution_log: Dict) -> None:
    """Print summary of all ingested datasets."""
    print("\n" + "=" * 80)
    print("DATASET INGESTION SUMMARY")
    print("=" * 80)
    print(f"{'Dataset Name':<40} | {'Status':<10} | {'Rows':<15} | Source")
    print("-" * 80)

    datasets = execution_log.get('datasets', {})
    total_rows = 0
    loaded_count = 0

    for dataset_name, dataset_info in sorted(datasets.items()):
        status = dataset_info.get('status', 'unknown')
        rows = dataset_info.get('rows', 0)
        source = dataset_info.get('source', 'unknown')

        status_icon = "[OK]" if status == "loaded" else "[FAIL]"
        print(f"{dataset_name:<40} | {status:<10} | {rows:<15,d} | {source}")

        if status == "loaded":
            loaded_count += 1
            total_rows += rows

    print("-" * 80)
    print(f"TOTAL: {loaded_count} loaded datasets | {total_rows:,} total rows")


def print_progress_report(execution_log: Dict, watermarks: Dict) -> None:
    """Print detailed progress report."""
    print("\n" + "=" * 80)
    print("INGESTION PROGRESS REPORT")
    print("=" * 80)

    started_at = execution_log.get('started_at', 'N/A')
    completed_at = execution_log.get('completed_at')
    status = execution_log.get('status', 'running').upper()

    elapsed = calculate_elapsed_time(started_at, completed_at)
    print(f"Pipeline Status: {status}")
    print(f"Started At:      {started_at}")
    print(f"Completed At:    {completed_at or 'IN PROGRESS'}")
    print(f"Elapsed Time:    {elapsed}")
    print(f"Pipeline Version: {execution_log.get('pipeline_version', 'N/A')}")

    datasets = execution_log.get('datasets', {})
    print(f"\nDatasets: {len(datasets)} total")
    print(f"  - Loaded: {sum(1 for d in datasets.values() if d.get('status') == 'loaded')}")
    print(f"  - Failed: {sum(1 for d in datasets.values() if d.get('status') == 'failed')}")

    total_rows = sum(d.get('rows', 0) for d in datasets.values() if d.get('status') == 'loaded')
    print(f"  - Total Rows: {total_rows:,}")

    # Check for problematic datasets
    failed_datasets = [name for name, info in datasets.items() if info.get('status') == 'failed']
    if failed_datasets:
        print(f"\nFailed Datasets ({len(failed_datasets)}):")
        for name in failed_datasets[:10]:  # Show first 10
            error = datasets[name].get('error', 'Unknown error')
            print(f"  - {name}: {error}")


def main() -> int:
    """Main entry point."""
    execution_log = load_execution_log()
    watermarks = load_watermarks()

    if not execution_log:
        print("ERROR: No execution log found. Pipeline may not have started.")
        return 1

    print_progress_report(execution_log, watermarks)
    print_stage_summary(execution_log)
    print_dataset_summary(execution_log)

    print("\n" + "=" * 80)

    status = execution_log.get('status', 'unknown')
    if status == 'success':
        print("INGESTION COMPLETED SUCCESSFULLY")
        return 0
    elif status == 'failed':
        print("INGESTION FAILED - CHECK LOGS FOR DETAILS")
        return 1
    else:
        print("INGESTION IN PROGRESS OR STATUS UNKNOWN")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
