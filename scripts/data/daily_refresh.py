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
import logging
from datetime import datetime, timedelta

from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.analysis.nlp_classifier import TextClassifierPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Datasets to refresh (high-volume)
REFRESH_DATASETS = {
    "violations": ("violation_issue_date", "6kbp-uz6m"),
    "inspection": ("inspection_date", "dntt-gqwq"),
    "dismissals": ("violation_issue_date", "p4u2-3jgx"),
    "complaints_311": ("created_date", "erm2-nwe9"),
    "ramp_progress": ("startdate", "e7gc-ub6z"),
    "ramp_complaints": ("date_received", "jagj-gttd"),
    "street_permits": ("issued_date", "tqtj-sjs8"),
    "street_construction_inspections": ("inspection_date", "ydkf-mpxb"),
    "street_closures_block": ("closure_date", "i6b5-j7bu"),
    "street_resurfacing_schedule": ("scheduled_start", "xnfm-u3k5"),
    "correspondences": ("date_received", "bheb-sjfi"),
    "curb_metal_protruding": ("insp", "i2y3-sx2e"),
    "tree_damage": ("report_date", "j6v2-6uxq"),
}

CLASSIFICATION_DATASETS = {
    "violations": "violations",
    "inspection": "violations",
    "complaints_311": "complaints",
    "tree_damage": "tree_damage",
}

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
    today = datetime.now().date()

    total_new = 0
    successful = 0

    for dataset_name, (date_field, fourfour) in REFRESH_DATASETS.items():
        try:
            logger.info(f"[REFRESH] {dataset_name}...")

            # Fetch new records (since yesterday)
            where = f"{date_field} >= '{yesterday}'"
            df = client.fetch_dataframe(
                "data.cityofnewyork.us",
                fourfour,
                where=where,
                max_rows=10000
            )

            if len(df) == 0:
                logger.info(f"  (no new records)")
                continue

            logger.info(f"  {len(df)} new records")
            total_new += len(df)

            # Upsert into raw schema
            raw_table = f"raw.{dataset_name}"
            conn.register(f"{dataset_name}_new", df)
            conn.execute(f"""
            INSERT OR REPLACE INTO {raw_table}
            SELECT * FROM {dataset_name}_new
            """)

            # Classify if applicable
            if dataset_name in CLASSIFICATION_DATASETS:
                classifier_type = CLASSIFICATION_DATASETS[dataset_name]

                if classifier_type == "violations":
                    classified_df = pipeline.classify_violations_dataframe(df)
                elif classifier_type == "complaints":
                    classified_df = pipeline.classify_complaints_dataframe(df)
                elif classifier_type == "tree_damage":
                    classified_df = df  # Simplified for now
                else:
                    classified_df = df

                # Upsert into staging
                staging_table = f"staging.{dataset_name}"
                conn.register(f"{dataset_name}_classified", classified_df)
                conn.execute(f"""
                INSERT OR REPLACE INTO {staging_table}
                SELECT * FROM {dataset_name}_classified
                """)

            successful += 1

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")

    # Refresh materialized views
    logger.info("\n[VIEWS] Refreshing analytics...")

    try:
        # Violations summary
        conn.execute("""
        INSERT OR REPLACE INTO analytics.violations_by_borough
        SELECT
          Borough,
          COUNT(*) as violation_count,
          COUNT(DISTINCT site_street_address) as affected_addresses,
          DATE_TRUNC('month', violation_issue_date) as month
        FROM raw.violations
        WHERE violation_issue_date >= DATE '2024-01-01'
        GROUP BY Borough, DATE_TRUNC('month', violation_issue_date)
        """)

        # Ramp progress summary
        conn.execute("""
        INSERT OR REPLACE INTO analytics.ramp_progress_summary
        SELECT
          Borough,
          COUNT(*) as total_ramps,
          SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_ramps,
          ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) as completion_pct,
          AVG(CAST(percent_complete AS FLOAT)) as avg_progress
        FROM raw.ramp_progress
        GROUP BY Borough
        """)

        logger.info("  ✓ Views updated")

    except Exception as e:
        logger.warning(f"  ⚠ View update error: {e}")

    # Cleanup old data (archive to cloud)
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
    SELECT COUNT(*) as total FROM (
        SELECT COUNT(*) FROM raw.violations
        UNION ALL SELECT COUNT(*) FROM raw.inspection
        UNION ALL SELECT COUNT(*) FROM raw.dismissals
        UNION ALL SELECT COUNT(*) FROM raw.complaints_311
    )
    """).fetchone()[0]

    logger.info(f"  Total records in cache: {raw_count:,}")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info(f"DAILY REFRESH COMPLETE")
    logger.info("=" * 70)
    logger.info(f"New records: {total_new:,}")
    logger.info(f"Datasets updated: {successful}/{len(REFRESH_DATASETS)}")
    logger.info(f"Cache size: {db_size_mb:.1f} MB")
    logger.info(f"Next refresh: Tomorrow {datetime.now().time().strftime('%H:%M')} UTC")
    logger.info("=" * 70)

    conn.close()

def archive_old_data(conn, days_old=30):
    """Archive data older than N days to MotherDuck."""
    cutoff_date = (datetime.now() - timedelta(days=days_old)).date()

    # Datasets with date fields suitable for archival
    archive_datasets = [
        ("violations", "violation_issue_date"),
        ("inspection", "inspection_date"),
        ("dismissals", "violation_issue_date"),
        ("complaints_311", "created_date"),
        ("street_construction_inspections", "inspection_date"),
    ]

    logger.info(f"  Archiving records older than {cutoff_date}...")

    for dataset_name, date_field in archive_datasets:
        try:
            # Count records to archive
            count = conn.execute(f"""
            SELECT COUNT(*) FROM raw.{dataset_name}
            WHERE {date_field} < '{cutoff_date}'
            """).fetchone()[0]

            if count == 0:
                continue

            logger.info(f"  {dataset_name}: {count} records to archive")

            # Export to Parquet (for cloud upload)
            parquet_dir = f"data/parquet_archive/{datetime.now().year}/{datetime.now().strftime('%m-%B')}"
            os.makedirs(parquet_dir, exist_ok=True)

            parquet_file = f"{parquet_dir}/{dataset_name}_{datetime.now().date()}.parquet"

            conn.execute(f"""
            COPY (
                SELECT * FROM raw.{dataset_name}
                WHERE {date_field} < '{cutoff_date}'
            ) TO '{parquet_file}' (FORMAT PARQUET)
            """)

            logger.info(f"    → Exported to {parquet_file}")

            # TODO: Upload to MotherDuck
            # upload_to_motherduck(parquet_file, f"md:raw.{dataset_name}")

            # Delete from local cache (optional - keep if space available)
            # conn.execute(f"""
            # DELETE FROM raw.{dataset_name}
            # WHERE {date_field} < '{cutoff_date}'
            # """)

        except Exception as e:
            logger.warning(f"  ⚠ Archive error for {dataset_name}: {e}")

if __name__ == "__main__":
    daily_refresh()
