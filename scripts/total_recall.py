"""
TOTAL RECALL: Full-Scale Socrata Ingestion Script.
Ingests every single record for all 26 datasets into the local DuckDB store.
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from app.data_loader import DATASET_REGISTRY
from src.socrata_toolkit.pipeline.sync import sync_dataset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_REPO_ROOT / "outputs" / "total_recall.log")
    ]
)
logger = logging.getLogger("total_recall")

# Map of dataset keys to their authoritative timestamp column for incremental sync
# Corrected field names based on Socrata metadata probes
UPDATED_COL_MAP = {
    "inspection": "inspectiondate",
    "violations": "entrydate",
    "built": "dot_contstruct_date",
    "reinspection": "actualreinspectdate",
    "tree_damage": "inspect_date",
    "dismissals": "inspection_date",
    "correspondences": "date_received",
    "ramp_complaints": "complaint_date",
    "ramp_progress": "construction_end_date",
    "street_permits": "modifiedon",
    "capital_blocks": "designstartdate",
    "capital_intersections": "designstartdate",
    "street_construction_inspections": "inspectiondate",
    "street_closures_block": "work_start_date",
    "permit_stipulations": "createdon",
    "street_resurfacing_schedule": "date",
    "street_resurfacing_inhouse": "location_actual_paving_start_date",
    "mappluto": "appdate",
    "complaints_311": "created_date",
    "curb_metal_protruding": "rec_d_2", # Heuristic based on common Socrata patterns
}

DB_PATH = str(_REPO_ROOT / "data" / "local_db" / "nyc_mission_control.duckdb")
TOKEN = os.getenv("SOCRATA_APP_TOKEN", "").strip()

def run_total_recall():
    logger.info("Starting TOTAL RECALL — Full scale municipal data ingestion.")
    logger.info(f"Target Database: {DB_PATH}")

    if not TOKEN:
        logger.warning("No SOCRATA_APP_TOKEN found. Ingestion will be slow and subject to heavy rate limits.")

    total_rows = 0
    success_count = 0

    for key, meta in DATASET_REGISTRY.items():
        fourfour = meta["fourfour"]
        label = meta["label"]
        updated_col = UPDATED_COL_MAP.get(key, "created_at") # Fallback to a common Socrata name

        logger.info(f"--- Syncing {key} ({label}) [{fourfour}] ---")
        try:
            # sync_dataset handles pagination (unlimited) and incremental logic
            rows_synced = sync_dataset(
                domain="data.cityofnewyork.us",
                fourfour=fourfour,
                db_path=DB_PATH,
                table_name=key,
                updated_col=updated_col,
                token=TOKEN
            )
            logger.info(f"Successfully synced {rows_synced:,} rows for {key}.")
            total_rows += rows_synced
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to sync {key}: {e}")

    logger.info("====================================================")
    logger.info("TOTAL RECALL COMPLETE.")
    logger.info(f"Datasets processed: {success_count}/{len(DATASET_REGISTRY)}")
    logger.info(f"Total new rows ingested: {total_rows:,}")
    logger.info("====================================================")

if __name__ == "__main__":
    run_total_recall()
