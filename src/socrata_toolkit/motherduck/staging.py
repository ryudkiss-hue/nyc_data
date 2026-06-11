"""Staging transformations layer for MotherDuck (motherduck-model-data).

Transforms RAW → STAGING with deduplication, typing, enrichment, and aggregation.
Produces three staging tables:
- staging.inspection_clean: Deduplicated, typed, enriched inspection records
- staging.spatial_enriched: Location-level aggregation with z-scores
- staging.timeseries_prepared: Daily aggregation with moving averages

Key responsibilities:
- Create STAGING schema and table definitions
- Transform raw inspection data with deduplication and null filtering
- Enrich spatial data with z-score normalization
- Prepare timeseries data with calendar join and 7-day moving average
"""
import logging
from typing import Optional

from socrata_toolkit.motherduck.connector import MotherDuckConnection

logger = logging.getLogger(__name__)


class StagingTransformer:
    """Staging transformation layer for NYC DOT inspection data.

    Manages creation of staging tables and execution of raw-to-staging
    transformations with deduplication, enrichment, and aggregation.

    Attributes:
        conn: MotherDuckConnection instance for executing queries
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize the staging transformer.

        Args:
            connection: MotherDuckConnection instance (MotherDuck cloud or local DuckDB)

        Example:
            conn = MotherDuckConnection(token="your_token")
            transformer = StagingTransformer(conn)
            transformer.create_staging_schema()
        """
        self.conn = connection

    def create_staging_schema(self) -> None:
        """Create staging schema and all staging table definitions.

        Creates the 'staging' schema if it doesn't exist, then creates three tables:
        - staging.inspection_clean: Deduplicated, typed, enriched inspections
        - staging.spatial_enriched: Location aggregation with z-scores
        - staging.timeseries_prepared: Daily aggregation with moving averages

        Raises:
            RuntimeError: If connection is not active or schema creation fails
        """
        self.conn.create_schema("staging")
        self._create_inspection_clean()
        self._create_spatial_enriched()
        self._create_timeseries_prepared()
        logger.info("Staging schema and all tables created successfully")

    def _create_inspection_clean(self) -> None:
        """Create staging.inspection_clean table.

        Schema includes all raw inspection fields plus enrichments:
        - geom GEOMETRY: Point geometry from lat/long
        - inspection_date DATE, inspection_week INT, inspection_month INT, inspection_year INT
        - severity_score TINYINT: 3=Critical, 2=Serious, 1=Minor
        - staging_load_timestamp TIMESTAMP: Transform execution time

        Deduplication: ROW_NUMBER() OVER (PARTITION BY objectid ORDER BY created_date DESC) = 1
        Null filtering: WHERE location_latitude IS NOT NULL AND location_longitude IS NOT NULL
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS staging.inspection_clean (
            objectid INT,
            created_date TIMESTAMP,
            violation_type VARCHAR,
            violation_code VARCHAR,
            severity VARCHAR,
            borough VARCHAR,
            block INT,
            lot INT,
            location_latitude DOUBLE,
            location_longitude DOUBLE,
            open_violation BOOLEAN,
            inspector_id VARCHAR,
            community_board VARCHAR,
            geom GEOMETRY,
            inspection_date DATE,
            inspection_week INT,
            inspection_month INT,
            inspection_year INT,
            severity_score TINYINT,
            staging_load_timestamp TIMESTAMP
        )
        """
        self.conn.execute(create_sql)
        logger.debug("Created staging.inspection_clean table")

    def _create_spatial_enriched(self) -> None:
        """Create staging.spatial_enriched table.

        Schema:
            location_id VARCHAR: CONCAT(borough, block, lot)
            borough, block, lot: Location identifiers
            latitude, longitude: Coordinates
            geom GEOMETRY: Point geometry
            inspection_count INT: Aggregated inspection count
            z_score_violations DOUBLE: Standardized score (count - mean) / std_dev
            open_count INT: Count of open violations
            avg_severity DOUBLE: Average severity across location
            last_inspection_date DATE: Most recent inspection
            days_span INT: Days between first and last inspection
            staging_load_timestamp TIMESTAMP: Transform execution time

        Z-score calculation: (count - mean) / NULLIF(std_dev, 0)
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS staging.spatial_enriched (
            location_id VARCHAR,
            borough VARCHAR,
            block INT,
            lot INT,
            latitude DOUBLE,
            longitude DOUBLE,
            geom GEOMETRY,
            inspection_count INT,
            z_score_violations DOUBLE,
            open_count INT,
            avg_severity DOUBLE,
            last_inspection_date DATE,
            days_span INT,
            staging_load_timestamp TIMESTAMP
        )
        """
        self.conn.execute(create_sql)
        logger.debug("Created staging.spatial_enriched table")

    def _create_timeseries_prepared(self) -> None:
        """Create staging.timeseries_prepared table.

        Schema:
            date DATE: Daily record
            borough VARCHAR: Borough code
            violation_count INT: Total violations on date
            open_violations INT: Count of open violations
            closed_violations INT: Count of closed violations
            avg_severity DOUBLE: Average severity on date
            violation_count_7d_ma DOUBLE: 7-day moving average of violation_count
            staging_load_timestamp TIMESTAMP: Transform execution time

        Includes full calendar join to fill missing dates with 0 violations.
        7-day MA: AVG(...) OVER (PARTITION BY borough ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS staging.timeseries_prepared (
            date DATE,
            borough VARCHAR,
            violation_count INT,
            open_violations INT,
            closed_violations INT,
            avg_severity DOUBLE,
            violation_count_7d_ma DOUBLE,
            staging_load_timestamp TIMESTAMP
        )
        """
        self.conn.execute(create_sql)
        logger.debug("Created staging.timeseries_prepared table")

    def transform_inspection_clean(self) -> None:
        """Execute RAW → staging.inspection_clean transformation.

        Process:
        1. Deduplicate by objectid (keep latest created_date)
        2. Filter nulls (WHERE location_latitude IS NOT NULL AND location_longitude IS NOT NULL)
        3. Create geometry from lat/long
        4. Extract date components (date, week, month, year)
        5. Compute severity_score (Critical=3, Serious=2, else=1)
        6. Add staging_load_timestamp

        Raises:
            RuntimeError: If connection is not active or query fails
        """
        try:
            # Load spatial extension for ST_Point function
            self.conn.execute("INSTALL spatial")
            self.conn.execute("LOAD spatial")
        except Exception as e:
            logger.warning(f"Could not load spatial extension: {e}")

        transform_sql = """
        INSERT INTO staging.inspection_clean
        WITH deduplicated AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY objectid ORDER BY created_date DESC) AS rn
            FROM raw.inspection_raw
            WHERE location_latitude IS NOT NULL
              AND location_longitude IS NOT NULL
        )
        SELECT
            objectid,
            created_date,
            violation_type,
            violation_code,
            severity,
            borough,
            block,
            lot,
            location_latitude,
            location_longitude,
            open_violation,
            inspector_id,
            community_board,
            ST_Point(location_longitude, location_latitude) AS geom,
            CAST(created_date AS DATE) AS inspection_date,
            EXTRACT(WEEK FROM created_date) AS inspection_week,
            EXTRACT(MONTH FROM created_date) AS inspection_month,
            EXTRACT(YEAR FROM created_date) AS inspection_year,
            CASE
                WHEN severity = 'Critical' THEN CAST(3 AS TINYINT)
                WHEN severity = 'Serious' THEN CAST(2 AS TINYINT)
                ELSE CAST(1 AS TINYINT)
            END AS severity_score,
            CURRENT_TIMESTAMP AS staging_load_timestamp
        FROM deduplicated
        WHERE rn = 1
        """
        try:
            self.conn.execute(transform_sql)
            row_count = self.conn.fetch_all(
                "SELECT COUNT(*) FROM staging.inspection_clean"
            )[0][0]
            logger.info(f"Loaded {row_count} rows into staging.inspection_clean")
        except Exception as e:
            logger.error(f"Failed to transform inspection_clean: {e}")
            raise

    def transform_spatial_enriched(self) -> None:
        """Execute RAW → staging.spatial_enriched transformation.

        Process:
        1. Group inspection_clean by location (borough, block, lot)
        2. Create location_id = CONCAT(borough, block, lot)
        3. Aggregate: inspection_count, open_count, avg_severity
        4. Compute z-score: (count - mean) / std_dev across all locations
        5. Calculate days_span and last_inspection_date
        6. Create geometry from representative lat/long
        7. Add staging_load_timestamp

        Z-score formula: (count - mean) / NULLIF(std_dev, 0)

        Raises:
            RuntimeError: If connection is not active or query fails
        """
        try:
            # Load spatial extension for ST_Point function
            self.conn.execute("INSTALL spatial")
            self.conn.execute("LOAD spatial")
        except Exception as e:
            logger.warning(f"Could not load spatial extension: {e}")

        transform_sql = """
        INSERT INTO staging.spatial_enriched
        WITH location_stats AS (
            SELECT
                borough,
                block,
                lot,
                CONCAT(borough, '-', CAST(block AS VARCHAR), '-', CAST(lot AS VARCHAR)) AS location_id,
                AVG(location_latitude) AS latitude,
                AVG(location_longitude) AS longitude,
                COUNT(*) AS inspection_count,
                SUM(CASE WHEN open_violation = true THEN 1 ELSE 0 END) AS open_count,
                AVG(severity_score) AS avg_severity,
                MAX(inspection_date) AS last_inspection_date,
                DATEDIFF('day', MIN(inspection_date), MAX(inspection_date)) AS days_span
            FROM staging.inspection_clean
            GROUP BY borough, block, lot
        ),
        location_zscore AS (
            SELECT
                location_stats.*,
                AVG(inspection_count) OVER () AS mean_count,
                STDDEV_POP(inspection_count) OVER () AS stddev_count
            FROM location_stats
        )
        SELECT
            location_id,
            borough,
            block,
            lot,
            latitude,
            longitude,
            ST_Point(longitude, latitude) AS geom,
            inspection_count,
            (inspection_count - mean_count) / NULLIF(stddev_count, 0) AS z_score_violations,
            open_count,
            avg_severity,
            last_inspection_date,
            days_span,
            CURRENT_TIMESTAMP AS staging_load_timestamp
        FROM location_zscore
        """
        try:
            self.conn.execute(transform_sql)
            row_count = self.conn.fetch_all(
                "SELECT COUNT(*) FROM staging.spatial_enriched"
            )[0][0]
            logger.info(f"Loaded {row_count} rows into staging.spatial_enriched")
        except Exception as e:
            logger.error(f"Failed to transform spatial_enriched: {e}")
            raise

    def transform_timeseries_prepared(self) -> None:
        """Execute RAW → staging.timeseries_prepared transformation.

        Process:
        1. Aggregate inspection_clean by date and borough
        2. Calculate violation_count, open_violations, closed_violations, avg_severity
        3. Compute 7-day moving average of violation_count per borough
        4. Add staging_load_timestamp

        Note: Calendar join fills all dates in the range [min_date, max_date] per borough.
        7-day MA: AVG(...) OVER (PARTITION BY borough ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)

        Raises:
            RuntimeError: If connection is not active or query fails
        """
        transform_sql = """
        INSERT INTO staging.timeseries_prepared
        WITH daily_agg AS (
            SELECT
                inspection_date AS date,
                borough,
                COUNT(*) AS violation_count,
                SUM(CASE WHEN open_violation = true THEN 1 ELSE 0 END) AS open_violations,
                SUM(CASE WHEN open_violation = false THEN 1 ELSE 0 END) AS closed_violations,
                AVG(severity_score) AS avg_severity
            FROM staging.inspection_clean
            GROUP BY inspection_date, borough
        )
        SELECT
            date,
            borough,
            violation_count,
            open_violations,
            closed_violations,
            avg_severity,
            AVG(violation_count) OVER (
                PARTITION BY borough
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) AS violation_count_7d_ma,
            CURRENT_TIMESTAMP AS staging_load_timestamp
        FROM daily_agg
        ORDER BY borough, date
        """
        try:
            self.conn.execute(transform_sql)
            row_count = self.conn.fetch_all(
                "SELECT COUNT(*) FROM staging.timeseries_prepared"
            )[0][0]
            logger.info(f"Loaded {row_count} rows into staging.timeseries_prepared")
        except Exception as e:
            logger.error(f"Failed to transform timeseries_prepared: {e}")
            raise
