"""
Schema Drift Logging Utility.
Tracks and logs instances where municipal data schemas evolve or deviate from expected baselines.
"""

import os
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = _REPO_ROOT / "data" / "logs"
DRIFT_CSV = LOG_DIR / "schema_drift.csv"
DRIFT_MD = _REPO_ROOT / "docs" / "SCHEMA_DRIFT.md"

logger = logging.getLogger(__name__)

def _ensure_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not DRIFT_CSV.exists():
        with open(DRIFT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_utc", "dataset_key", "event_type", "column_name", "details"])

def log_drift(dataset_key: str, event_type: str, column_name: str, details: str = ""):
    """Logs a schema drift event to both CSV and Markdown."""
    _ensure_logs()
    now = datetime.now(timezone.utc).isoformat()
    
    # Log to CSV
    try:
        with open(DRIFT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([now, dataset_key, event_type, column_name, details])
    except Exception as e:
        logger.error("Failed to write to drift CSV: %s", e)

    # Log to Markdown
    try:
        header_exists = DRIFT_MD.exists()
        with open(DRIFT_MD, "a", encoding="utf-8") as f:
            if not header_exists:
                f.write("# 📋 Municipal Schema Drift Registry\n\n")
                f.write("This log tracks all instances of schema evolution, column additions, and data type shifts detected by the toolkit.\n\n")
                f.write("| Timestamp (UTC) | Dataset | Event | Column | Details |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            f.write(f"| {now} | `{dataset_key}` | **{event_type}** | `{column_name}` | {details} |\n")
    except Exception as e:
        logger.error("Failed to write to drift MD: %s", e)

def log_column_added(dataset_key: str, column_name: str):
    """Convenience helper for new column detection."""
    log_drift(dataset_key, "COLUMN_ADDED", column_name, "Automatically added to DuckDB table via schema evolution.")