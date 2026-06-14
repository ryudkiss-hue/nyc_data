#!/usr/bin/env python
"""
Daily cache refresh from Socrata.
Runs at 6 AM UTC via APScheduler to fetch new data and update DuckDB.

Usage:
  # One-time run
  python daily_refresh.py

  # Scheduled (in APScheduler)
  scheduler.add_job(daily_refresh, 'cron', hour=6, minute=0, timezone='UTC')
"""

import sys
import os
sys.path.insert(0, 'src')

import duckdb
import pandas as pd
import logging
from datetime import datetime, timedelta

from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.analysis.nlp_classifier import TextClassifierPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Datasets to refresh: (actual_date_field_in_api, fourfour)
# date fields verified against live API schema 2026-06-14
REFRESH_DATASETS = {
    "violations": ("vissuedate", "6kbp-uz6m"),
    "inspection": ("inspectiondate", "dntt-gqwq"),
    "dismissals": ("violation_issue_date", "p4u2-3jgx"),
    "complaints_311": ("created_date", "erm2-nwe9"),
    "ramp_progress": (None, "e7gc-ub6z"),       # no filterable date field; fetch latest
    "ramp_complaints": ("complaint_date", "jagj-gttd"),
    "street_permits": ("permitissuedate", "tqtj-sjs8"),
    "street_construction_inspections": ("inspectiondate", "ydkf-mpxb"),
    "street_closures_block": ("work_start_date", "i6b5-j7bu"),
    "street_resurfacing_schedule": ("date", "xnfm-u3k5"),
    "correspondences": ("date_received", "bheb-sjfi"),
    "curb_metal_protruding": ("insp", "i2y3-sx2e"),
    "tree_damage": ("inspect_date", "j6v2-6uxq"),
}

CLASSIFICATION_DATASETS = {
    "violations": "violations",
    "inspection": "violations",
    "complaints_311": "complaints",
    "tree_damage": "tree_damage",
}

def align_df_to_table(conn, df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Add missing columns (as None) and drop extras so df matches table schema."""
    table_cols = [
        r[0] for r in conn.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_schema='{table.split('.')[0]}' AND table_name='{table.split('.')[1]}'"
        ).fetchall()
    ]
    for col in table_cols:
        if col not in df.columns:
            df[col] = None
    return df[[c for c in table_cols if c in df.columns]]


def daily_refresh():
    """Fetch new records and update cache."""
    logger.info("=" * 70)
    logger.info("DAILY REFRESH")
    logger.info("=" * 70)

    db_path = "data/local_db/nyc_sim_cache.duckdb"
    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        logger.info("Run bootstrap_cache.py first")
        return

    conn = duckdb.connect(db_path)
    client = SocrataClient(SocrataConfig())
    pipeline = TextClassifierPipeline()

    yesterday = (datetime.now() - timedelta(days=1)).date()

    total_new = 0
    successful = 0

    for dataset_name, (date_field, fourfour) in REFRESH_DATASETS.items():
        try:
            logger.info(f"[REFRESH] {dataset_name}...")

            if date_field is not None:
                where = f"{date_field} >= '{yesterday}T00:00:00.000'"
            else:
                where = None

            df = client.fetch_dataframe(
                "data.cityofnewyork.us",
                fourfour,
                where=where,
                max_rows=10000
            )

            if len(df) == 0:
                logger.info(f"  (no new records)")
                successful += 1
                continue

            logger.info(f"  {len(df)} new records")
            total_new += len(df)

            # Append into raw schema (no PK constraints — append-only for daily increments)
            raw_table = f"raw.{dataset_name}"
            df = align_df_to_table(conn, df, raw_table)
            conn.register(f"{dataset_name}_new", df)
            conn.execute(f"INSERT INTO {raw_table} SELECT * FROM {dataset_name}_new")

            # Classify if applicable
            if dataset_name in CLASSIFICATION_DATASETS:
                classifier_type = CLASSIFICATION_DATASETS[dataset_name]

                try:
                    if classifier_type == "violations":
                        classified_df = pipeline.classify_violations_dataframe(df)
                    elif classifier_type == "complaints":
                        classified_df = pipeline.classify_complaints_dataframe(df)
                    else:
                        classified_df = df

                    staging_table = f"staging.{dataset_name}"
                    conn.register(f"{dataset_name}_classified", classified_df)
                    try:
                        conn.execute(f"INSERT INTO {staging_table} SELECT * FROM {dataset_name}_classified")
                    except Exception:
                        conn.execute(f"CREATE TABLE IF NOT EXISTS {staging_table} AS SELECT * FROM {dataset_name}_classified")
                except Exception as e:
                    logger.warning(f"  ⚠ Classification skipped: {e}")

            successful += 1

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")

    # Refresh materialized views (CREATE OR REPLACE avoids INSERT OR REPLACE PK issue)
    logger.info("\n[VIEWS] Refreshing analytics...")

    try:
        conn.execute("""
        CREATE OR REPLACE VIEW analytics.violations_by_borough AS
        SELECT
          cb AS borough,
          COUNT(*) AS violation_count,
          COUNT(DISTINCT onstname) AS affected_streets,
          DATE_TRUNC('month', TRY_CAST(vissuedate AS TIMESTAMP)) AS month
        FROM raw.violations
        WHERE vissuedate IS NOT NULL
        GROUP BY cb, DATE_TRUNC('month', TRY_CAST(vissuedate AS TIMESTAMP))
        """)

        conn.execute("""
        CREATE OR REPLACE VIEW analytics.ramp_progress_summary AS
        SELECT
          borough,
          COUNT(*) AS total_ramps,
          SUM(CASE WHEN constructi = 'Completed' THEN 1 ELSE 0 END) AS completed_ramps,
          ROUND(100.0 * SUM(CASE WHEN constructi = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completion_pct
        FROM raw.ramp_progress
        GROUP BY borough
        """)

        logger.info("  ✓ Views updated")

    except Exception as e:
        logger.warning(f"  ⚠ View update error: {e}")

    # Cleanup old data (archive to Parquet)
    logger.info("\n[ARCHIVE] Checking for data to archive...")

    try:
        archive_old_data(conn, days_old=30)
    except Exception as e:
        logger.warning(f"  ⚠ Archive error: {e}")

    # Health check
    logger.info("\n[HEALTH] Cache status...")

    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    logger.info(f"  Database size: {db_size_mb:.1f} MB")

    raw_count = conn.execute("""
    SELECT SUM(cnt) FROM (
        SELECT COUNT(*) AS cnt FROM raw.violations
        UNION ALL SELECT COUNT(*) FROM raw.inspection
        UNION ALL SELECT COUNT(*) FROM raw.dismissals
        UNION ALL SELECT COUNT(*) FROM raw.complaints_311
    )
    """).fetchone()[0]

    logger.info(f"  Total records in cache: {raw_count:,}")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("DAILY REFRESH COMPLETE")
    logger.info("=" * 70)
    logger.info(f"New records: {total_new:,}")
    logger.info(f"Datasets updated: {successful}/{len(REFRESH_DATASETS)}")
    logger.info(f"Cache size: {db_size_mb:.1f} MB")
    logger.info(f"Next refresh: Tomorrow {datetime.now().time().strftime('%H:%M')} UTC")
    logger.info("=" * 70)

    conn.close()

def archive_old_data(conn, days_old=30):
    """Archive data older than N days to local Parquet (MotherDuck upload is TODO)."""
    cutoff_date = (datetime.now() - timedelta(days=days_old)).date()

    # Use actual column names as verified from live schema
    archive_datasets = [
        ("violations", "vissuedate"),
        ("inspection", "inspectiondate"),
        ("dismissals", "violation_issue_date"),
        ("complaints_311", "created_date"),
        ("street_construction_inspections", "inspectiondate"),
    ]

    logger.info(f"  Archiving records older than {cutoff_date}...")

    for dataset_name, date_field in archive_datasets:
        try:
            count = conn.execute(f"""
            SELECT COUNT(*) FROM raw.{dataset_name}
            WHERE TRY_CAST({date_field} AS TIMESTAMP) < TIMESTAMP '{cutoff_date}'
            """).fetchone()[0]

            if count == 0:
                continue

            logger.info(f"  {dataset_name}: {count} records to archive")

            parquet_dir = f"data/parquet_archive/{datetime.now().year}/{datetime.now().strftime('%m-%B')}"
            os.makedirs(parquet_dir, exist_ok=True)

            parquet_file = f"{parquet_dir}/{dataset_name}_{datetime.now().date()}.parquet"

            conn.execute(f"""
            COPY (
                SELECT * FROM raw.{dataset_name}
                WHERE TRY_CAST({date_field} AS TIMESTAMP) < TIMESTAMP '{cutoff_date}'
            ) TO '{parquet_file}' (FORMAT PARQUET)
            """)

            logger.info(f"    → Exported to {parquet_file}")

            # TODO: upload_to_motherduck(parquet_file, f"md:raw.{dataset_name}")

        except Exception as e:
            logger.warning(f"  ⚠ Archive error for {dataset_name}: {e}")

if __name__ == "__main__":
    daily_refresh()
