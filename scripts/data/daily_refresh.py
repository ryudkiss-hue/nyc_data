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

# Datasets to refresh — (date_field, fourfour).
# date_field is the actual SODA2 API field name; None means no date filter.
# Field names verified against live API and MotherDuck schema 2026-06-11.
REFRESH_DATASETS = {
    "violations":                     ("vissuedate",           "6kbp-uz6m"),
    "inspection":                     ("inspectiondate",       "dntt-gqwq"),
    "dismissals":                     ("violation_issue_date", "p4u2-3jgx"),
    "complaints_311":                 ("created_date",         "erm2-nwe9"),
    "ramp_progress":                  (None,                   "e7gc-ub6z"),
    "ramp_complaints":                ("complaint_date",       "jagj-gttd"),
    "street_permits":                 ("permitissuedate",      "tqtj-sjs8"),
    "street_construction_inspections":("inspectiondate",       "ydkf-mpxb"),
    "street_closures_block":          ("work_start_date",      "i6b5-j7bu"),
    "street_resurfacing_schedule":    ("date",                 "xnfm-u3k5"),
    "correspondences":                ("date_received",        "bheb-sjfi"),
    "curb_metal_protruding":          ("insp",                 "i2y3-sx2e"),
    "tree_damage":                    ("inspect_date",         "j6v2-6uxq"),
}

CLASSIFICATION_DATASETS = {
    "violations": "violations",
    "inspection": "violations",
    "complaints_311": "complaints",
    "tree_damage": "tree_damage",
}

# Archive date fields — actual SODA2 column names (verified 2026-06-11).
ARCHIVE_DATE_FIELDS = {
    "violations":                      "vissuedate",
    "inspection":                      "inspectiondate",
    "dismissals":                      "violation_issue_date",
    "complaints_311":                  "created_date",
    "street_construction_inspections": "inspectiondate",
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

    total_new = 0
    successful = 0

    for dataset_name, (date_field, fourfour) in REFRESH_DATASETS.items():
        try:
            logger.info(f"[REFRESH] {dataset_name}...")

            # Use ISO 8601 timestamp format required by Socrata SOQL.
            where = f"{date_field} >= '{yesterday}T00:00:00'" if date_field else None
            df = client.fetch_dataframe(
                "data.cityofnewyork.us",
                fourfour,
                where=where,
                max_rows=10000
            )

            if df is None or len(df) == 0 or len(df.columns) == 0:
                logger.info(f"  (no new records)")
                continue

            logger.info(f"  {len(df)} new records")
            total_new += len(df)

            # Upsert into raw schema.  If the table doesn't exist yet (e.g.
            # bootstrap timed out for this dataset), create it.  Use BY NAME
            # so column-count mismatches (Socrata omits null cols) are safe.
            raw_table = f"raw.{dataset_name}"
            conn.register(f"{dataset_name}_new", df)
            exists = conn.execute(
                "SELECT COUNT(*) FROM duckdb_tables() "
                f"WHERE schema_name='raw' AND table_name='{dataset_name}'"
            ).fetchone()[0]
            if exists:
                conn.execute(
                    f"INSERT INTO {raw_table} BY NAME "
                    f"SELECT * FROM {dataset_name}_new"
                )
            else:
                conn.execute(
                    f"CREATE TABLE {raw_table} AS "
                    f"SELECT * FROM {dataset_name}_new"
                )
                logger.info(f"  (created new table {raw_table})")

            successful += 1  # raw insert succeeded

            # spaCy classification (best-effort — failure doesn't roll back insert)
            if dataset_name in CLASSIFICATION_DATASETS:
                try:
                    classifier_type = CLASSIFICATION_DATASETS[dataset_name]

                    if classifier_type == "violations":
                        classified_df = pipeline.classify_violations_dataframe(df)
                    elif classifier_type == "complaints":
                        classified_df = pipeline.classify_complaints_dataframe(df)
                    else:
                        classified_df = df

                    staging_table = f"staging.{dataset_name}"
                    conn.register(f"{dataset_name}_classified", classified_df)
                    s_exists = conn.execute(
                        "SELECT COUNT(*) FROM duckdb_tables() "
                        f"WHERE schema_name='staging' AND table_name='{dataset_name}'"
                    ).fetchone()[0]
                    if s_exists:
                        conn.execute(
                            f"INSERT INTO {staging_table} BY NAME "
                            f"SELECT * FROM {dataset_name}_classified"
                        )
                    else:
                        conn.execute(
                            f"CREATE TABLE {staging_table} AS "
                            f"SELECT * FROM {dataset_name}_classified"
                        )
                except Exception as cls_err:
                    logger.warning(f"  ⚠ Classification skipped: {cls_err}")

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")

    # Refresh analytics views with correct SODA2 column names
    logger.info("\n[VIEWS] Refreshing analytics...")

    try:
        conn.execute("""
        CREATE OR REPLACE VIEW analytics.violations_by_borough AS
        SELECT
          cb                                                          AS borough,
          COUNT(*)                                                    AS violation_count,
          COUNT(DISTINCT onstname)                                    AS affected_streets,
          DATE_TRUNC('month', TRY_CAST(vissuedate AS TIMESTAMP))     AS month
        FROM raw.violations
        WHERE vissuedate IS NOT NULL
        GROUP BY cb, DATE_TRUNC('month', TRY_CAST(vissuedate AS TIMESTAMP))
        ORDER BY month DESC, violation_count DESC
        """)

        conn.execute("""
        CREATE OR REPLACE VIEW analytics.inspection_summary AS
        SELECT
          COUNT(*)                                                        AS total_inspections,
          COUNT(DISTINCT damageid)                                        AS unique_damages,
          COUNT(CASE WHEN noviolationfound = 'Y' THEN 1 END)             AS clean_inspections,
          DATE_TRUNC('month', TRY_CAST(inspectiondate AS TIMESTAMP))     AS month
        FROM raw.inspection
        WHERE inspectiondate IS NOT NULL
        GROUP BY DATE_TRUNC('month', TRY_CAST(inspectiondate AS TIMESTAMP))
        ORDER BY month DESC
        """)

        conn.execute("""
        CREATE OR REPLACE VIEW analytics.ramp_progress_summary AS
        SELECT
          borough,
          COUNT(*)                                                AS total_ramps,
          COUNT(CASE WHEN construc_2 = 'Completed' THEN 1 END)   AS completed_ramps,
          ROUND(
            100.0 * COUNT(CASE WHEN construc_2 = 'Completed' THEN 1 END)
            / NULLIF(COUNT(*), 0), 1
          )                                                       AS completion_pct
        FROM raw.ramp_progress
        WHERE borough IS NOT NULL
        GROUP BY borough
        ORDER BY completion_pct DESC
        """)

        logger.info("  ✓ Views refreshed")

    except Exception as e:
        logger.warning(f"  ⚠ View refresh error: {e}")

    # Archive records older than 30 days to Parquet
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
    SELECT
        (SELECT COUNT(*) FROM raw.violations)    +
        (SELECT COUNT(*) FROM raw.inspection)    +
        (SELECT COUNT(*) FROM raw.dismissals)    +
        (SELECT COUNT(*) FROM raw.complaints_311)
        AS total
    """).fetchone()[0]

    logger.info(f"  Total records (4 core tables): {raw_count:,}")

    logger.info("\n" + "=" * 70)
    logger.info("DAILY REFRESH COMPLETE")
    logger.info("=" * 70)
    logger.info(f"New records fetched:   {total_new:,}")
    logger.info(f"Datasets updated:      {successful}/{len(REFRESH_DATASETS)}")
    logger.info(f"Cache size:            {db_size_mb:.1f} MB")
    logger.info(f"Next refresh:          Tomorrow {datetime.now().strftime('%H:%M')} UTC")
    logger.info("=" * 70)

    conn.close()


def archive_old_data(conn, days_old=30):
    """Export records older than N days to Parquet for cloud upload."""
    cutoff_date = (datetime.now() - timedelta(days=days_old)).date()
    logger.info(f"  Cutoff: records older than {cutoff_date}")

    for dataset_name, date_field in ARCHIVE_DATE_FIELDS.items():
        try:
            count = conn.execute(f"""
                SELECT COUNT(*) FROM raw.{dataset_name}
                WHERE TRY_CAST({date_field} AS DATE) < DATE '{cutoff_date}'
            """).fetchone()[0]

            if count == 0:
                continue

            logger.info(f"  {dataset_name}: {count:,} records to archive")

            parquet_dir = (
                f"data/parquet_archive/{datetime.now().year}/"
                f"{datetime.now().strftime('%m-%B')}"
            )
            os.makedirs(parquet_dir, exist_ok=True)
            parquet_file = (
                f"{parquet_dir}/{dataset_name}_{datetime.now().date()}.parquet"
            )

            conn.execute(f"""
                COPY (
                    SELECT * FROM raw.{dataset_name}
                    WHERE TRY_CAST({date_field} AS DATE) < DATE '{cutoff_date}'
                ) TO '{parquet_file}' (FORMAT PARQUET)
            """)
            logger.info(f"    → Exported to {parquet_file}")

        except Exception as e:
            logger.warning(f"  ⚠ Archive error for {dataset_name}: {e}")


if __name__ == "__main__":
    daily_refresh()
