#!/usr/bin/env python
"""
Bootstrap historical data cache from Socrata.
Runs once to populate DuckDB with initial 30-day snapshot.

Usage:
  python bootstrap_cache.py

Result:
  - Creates DuckDB file at data/local_db/nyc_sim_cache.duckdb
  - Populates raw/ schema with 30 days of data from all 24 datasets
  - Runs spaCy classification on text fields
  - Materializes analytics views
  - Ready for daily incremental refresh
"""

import sys
import os
sys.path.insert(0, 'src')

import duckdb
import logging
from datetime import datetime, timedelta
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from socrata_toolkit.core.client import SocrataClient, SocrataConfig

# Optional: Classification can be added later
try:
    from socrata_toolkit.analysis.nlp_classifier import TextClassifierPipeline
    HAS_CLASSIFIER = True
except ImportError:
    HAS_CLASSIFIER = False
    logger.info("Note: NLP classifier not available - will skip classification")

# All 24 datasets
DATASETS = {
    # Inspection & Violations
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "dismissals": "p4u2-3jgx",
    "correspondences": "bheb-sjfi",
    "reinspection": "gx72-kirf",
    "tree_damage": "j6v2-6uxq",
    "curb_metal_protruding": "i2y3-sx2e",

    # Ramp & Accessibility
    "ramp_locations": "ufzp-rrqu",
    "ramp_complaints": "jagj-gttd",
    "ramp_progress": "e7gc-ub6z",

    # Permits & Construction
    "street_permits": "tqtj-sjs8",
    "weekly_construction": "r528-jcks",
    "capital_blocks": "jvk9-k4re",
    "capital_intersections": "97nd-ff3i",
    "street_construction_inspections": "ydkf-mpxb",
    "street_closures_block": "i6b5-j7bu",
    "permit_stipulations": "gsgx-6efw",
    "street_resurfacing_schedule": "xnfm-u3k5",
    "street_resurfacing_inhouse": "ffaf-8mrv",

    # Context & Overlays
    "step_streets": "u9au-h79y",
    "sidewalk_planimetric": "vfx9-tbb6",
    "pedestrian_demand": "fwpa-qxaf",
    "mappluto": "64uk-42ks",
    "complaints_311": "erm2-nwe9",
}

# Datasets requiring classification
CLASSIFICATION_DATASETS = {
    "violations": "violations",
    "inspection": "violations",
    "tree_damage": "tree_damage",
    "complaints_311": "complaints",
    "curb_metal_protruding": "violations",
}

def setup_database(db_path):
    """Create DuckDB file and schema."""
    logger.info(f"[SETUP] Creating DuckDB at {db_path}")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = duckdb.connect(db_path)

    # Create schemas
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
    conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    logger.info("[SETUP] Schemas created: raw, staging, analytics")
    return conn

def fetch_dataset(client, dataset_name, fourfour, days_back=30):
    """Fetch recent data from Socrata."""
    try:
        logger.info(f"[FETCH] {dataset_name}...")

        # For dated datasets, fetch last N days
        date_field = get_date_field(dataset_name)
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()

        if date_field:
            where = f"{date_field} >= '{cutoff_date}T00:00:00'"
        else:
            where = None

        df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            fourfour,
            where=where,
            max_rows=50000
        )

        logger.info(f"  ✓ {len(df)} rows fetched")
        return df

    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return None

def get_date_field(dataset_name):
    """Identify date field for incremental fetch.
    Only fields verified to work with SOQL date filtering are listed.
    Datasets not listed are fetched without a date filter (up to max_rows).
    Field names verified against live API 2026-06-11.
    """
    date_fields = {
        "violations":                      "vissuedate",
        "inspection":                      "inspectiondate",
        "dismissals":                      "violation_issue_date",
        "complaints_311":                  "created_date",
        "ramp_complaints":                 "complaint_date",
        "street_permits":                  "permitissuedate",
        "street_construction_inspections": "inspectiondate",
        "street_closures_block":           "work_start_date",
        "street_resurfacing_schedule":     "date",
        "correspondences":                 "date_received",
        "curb_metal_protruding":           "insp",
        "tree_damage":                     "inspect_date",
    }
    return date_fields.get(dataset_name)

def land_in_raw(conn, dataset_name, df):
    """Store dataframe in raw schema."""
    table_name = f"raw.{dataset_name}"

    # Register and create table
    conn.register(f"{dataset_name}_temp", df)
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {dataset_name}_temp")

    logger.info(f"  → Landed in {table_name}")

def classify_and_stage(conn, dataset_name, df):
    """Classify and store in staging schema."""
    if dataset_name not in CLASSIFICATION_DATASETS:
        return False  # No classification needed

    if not HAS_CLASSIFIER:
        # Skip classification if not available
        logger.info(f"[STAGE] {dataset_name} (no classification)")
        staging_table = f"staging.{dataset_name}"
        conn.register(f"{dataset_name}_staged", df)
        conn.execute(f"DROP TABLE IF EXISTS {staging_table}")
        conn.execute(f"CREATE TABLE {staging_table} AS SELECT * FROM {dataset_name}_staged")
        return True

    try:
        logger.info(f"[CLASSIFY] {dataset_name}...")
        pipeline = TextClassifierPipeline()

        classifier_type = CLASSIFICATION_DATASETS[dataset_name]

        if classifier_type == "violations":
            classified_df = pipeline.classify_violations_dataframe(df)
        elif classifier_type == "complaints":
            classified_df = pipeline.classify_complaints_dataframe(df)
        elif classifier_type == "tree_damage":
            classified_df = df
        else:
            classified_df = df

        # Store in staging
        staging_table = f"staging.{dataset_name}"
        conn.register(f"{dataset_name}_classified", classified_df)
        conn.execute(f"DROP TABLE IF EXISTS {staging_table}")
        conn.execute(f"CREATE TABLE {staging_table} AS SELECT * FROM {dataset_name}_classified")

        logger.info(f"  ✓ Classified and staged")
        return True

    except Exception as e:
        logger.error(f"  ✗ Classification error: {e}")
        return False

def materialize_analytics(conn):
    """Create analytics views."""
    logger.info("[ANALYTICS] Materializing views...")

    try:
        # Violations by borough — uses actual SODA2 field names (verified 2026-06-11)
        conn.execute("""
        CREATE OR REPLACE VIEW analytics.violations_by_borough AS
        SELECT
          cb                                                      AS borough,
          COUNT(*)                                                AS violation_count,
          COUNT(DISTINCT onstname)                                AS affected_streets,
          DATE_TRUNC('month', TRY_CAST(vissuedate AS TIMESTAMP)) AS month
        FROM raw.violations
        WHERE vissuedate IS NOT NULL
        GROUP BY cb, DATE_TRUNC('month', TRY_CAST(vissuedate AS TIMESTAMP))
        ORDER BY month DESC, violation_count DESC
        """)

        # Inspection summary
        conn.execute("""
        CREATE OR REPLACE VIEW analytics.inspection_summary AS
        SELECT
          COUNT(*)                                                    AS total_inspections,
          COUNT(DISTINCT damageid)                                    AS unique_damages,
          COUNT(CASE WHEN noviolationfound = 'Y' THEN 1 END)         AS clean_inspections,
          DATE_TRUNC('month', TRY_CAST(inspectiondate AS TIMESTAMP)) AS month
        FROM raw.inspection
        WHERE inspectiondate IS NOT NULL
        GROUP BY DATE_TRUNC('month', TRY_CAST(inspectiondate AS TIMESTAMP))
        ORDER BY month DESC
        """)

        # Ramp progress — construc_2 holds construction status (truncated Shapefile name)
        conn.execute("""
        CREATE OR REPLACE VIEW analytics.ramp_progress_summary AS
        SELECT
          borough,
          COUNT(*)                                              AS total_ramps,
          COUNT(CASE WHEN construc_2 = 'Completed' THEN 1 END) AS completed_ramps,
          ROUND(
            100.0 * COUNT(CASE WHEN construc_2 = 'Completed' THEN 1 END)
            / NULLIF(COUNT(*), 0), 1
          )                                                     AS completion_pct
        FROM raw.ramp_progress
        WHERE borough IS NOT NULL
        GROUP BY borough
        ORDER BY completion_pct DESC
        """)

        # Permits by status — uses actual SODA2 field names
        conn.execute("""
        CREATE OR REPLACE VIEW analytics.permits_by_status AS
        SELECT
          permitstatusshortdesc   AS permit_status,
          COUNT(*)                AS permit_count,
          COUNT(DISTINCT permitteename) AS permittee_count
        FROM raw.street_permits
        GROUP BY permitstatusshortdesc
        ORDER BY permit_count DESC
        """)

        logger.info("  ✓ Analytics views created")

    except Exception as e:
        logger.error(f"  ✗ View creation error: {e}")

def main():
    """Run bootstrap process."""
    logger.info("=" * 70)
    logger.info("BOOTSTRAP: Historical Data Cache")
    logger.info("=" * 70)

    # Setup
    db_path = "data/local_db/nyc_sim_cache.duckdb"
    conn = setup_database(db_path)
    client = SocrataClient(SocrataConfig())

    # Fetch and land all datasets
    logger.info(f"\n[INGEST] Fetching {len(DATASETS)} datasets...")

    successful = 0
    failed = 0

    existing_tables = {
        row[1] for row in conn.execute(
            "SELECT schema_name, table_name FROM duckdb_tables() WHERE schema_name = 'raw'"
        ).fetchall()
    }

    for dataset_name, fourfour in sorted(DATASETS.items()):
        if dataset_name in existing_tables:
            logger.info(f"[SKIP] {dataset_name} (already loaded)")
            successful += 1
            continue

        df = fetch_dataset(client, dataset_name, fourfour, days_back=30)

        if df is not None and len(df) > 0 and len(df.columns) > 0:
            land_in_raw(conn, dataset_name, df)
            classify_and_stage(conn, dataset_name, df)
            successful += 1
        else:
            failed += 1
            logger.warning(f"  ⚠ {dataset_name}: no data or empty schema")

    # Materialize views
    materialize_analytics(conn)

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info(f"BOOTSTRAP COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Successful: {successful}/{len(DATASETS)}")
    logger.info(f"Failed: {failed}/{len(DATASETS)}")
    logger.info(f"Database: {db_path}")
    logger.info(f"\nReady for daily refresh via: daily_refresh.py")
    logger.info(f"Query cache via: analytics views")
    logger.info("=" * 70)

    conn.close()

if __name__ == "__main__":
    main()
