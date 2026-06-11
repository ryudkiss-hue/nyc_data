"""Data ingestion layer for MotherDuck (motherduck-load-data).

Provides the InspectionDataLoader class for creating and populating raw data tables
in MotherDuck. Handles schema creation and bulk loading of inspection, spatial,
timeseries, and violations data.

Key responsibilities:
- Create raw schema and table definitions
- Load pandas DataFrames into raw tables using DuckDB
- Support inspection, spatial, timeseries, and violations datasets
- Track data load timestamps for all records
"""
import logging
from typing import Optional

import pandas as pd

from socrata_toolkit.motherduck.connector import MotherDuckConnection

logger = logging.getLogger(__name__)


class InspectionDataLoader:
    """Data loader for NYC DOT inspection and violations data.

    Manages creation of raw data tables and bulk loading of inspection, spatial,
    timeseries, and violations datasets into MotherDuck or local DuckDB.

    Attributes:
        conn: MotherDuckConnection instance for executing queries
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize the data loader.

        Args:
            connection: MotherDuckConnection instance (MotherDuck cloud or local DuckDB)

        Example:
            conn = MotherDuckConnection(token="your_token")
            loader = InspectionDataLoader(conn)
            loader.create_raw_schema()
        """
        self.conn = connection

    def create_raw_schema(self) -> None:
        """Create raw schema and all raw table definitions.

        Creates the 'raw' schema if it doesn't exist, then creates four tables:
        - raw.inspection_raw: 398K rows expected
        - raw.spatial_raw: 50K rows expected
        - raw.timeseries_raw: 450 rows expected
        - raw.violations_raw: 312K rows expected

        Raises:
            RuntimeError: If connection is not active or schema creation fails
        """
        self.conn.create_schema("raw")
        self._create_inspection_raw()
        self._create_spatial_raw()
        self._create_timeseries_raw()
        self._create_violations_raw()
        logger.info("Raw schema and all tables created successfully")

    def _create_inspection_raw(self) -> None:
        """Create raw.inspection_raw table.

        Schema:
            objectid INT: Unique inspection identifier
            created_date TIMESTAMP: When the inspection was created
            violation_type VARCHAR: Type of violation (e.g., "Structural", "Accessibility")
            violation_code VARCHAR: Code for the violation type
            severity VARCHAR: Severity level (High, Medium, Low)
            borough VARCHAR: NYC borough code (MN, BX, BK, QN, SI)
            block INT: Tax lot block number
            lot INT: Tax lot lot number
            location_latitude DOUBLE: Latitude coordinate
            location_longitude DOUBLE: Longitude coordinate
            open_violation BOOLEAN: Whether violation is currently open
            inspector_id VARCHAR: ID of inspector
            community_board VARCHAR: Community board designation
            data_load_timestamp TIMESTAMP: When this row was loaded
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS raw.inspection_raw (
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
            data_load_timestamp TIMESTAMP
        )
        """
        self.conn.execute(create_sql)
        logger.debug("Created raw.inspection_raw table")

    def _create_spatial_raw(self) -> None:
        """Create raw.spatial_raw table.

        Schema:
            location_id VARCHAR: Unique location identifier
            borough VARCHAR: NYC borough code (MN, BX, BK, QN, SI)
            block INT: Tax lot block number
            lot INT: Tax lot lot number
            latitude DOUBLE: Latitude coordinate
            longitude DOUBLE: Longitude coordinate
            the_geom GEOMETRY: GIS geometry object (point/polygon)
            community_board VARCHAR: Community board designation
            inspection_count INT: Number of inspections at this location
            last_inspection_date DATE: Date of most recent inspection
            data_load_timestamp TIMESTAMP: When this row was loaded
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS raw.spatial_raw (
            location_id VARCHAR,
            borough VARCHAR,
            block INT,
            lot INT,
            latitude DOUBLE,
            longitude DOUBLE,
            the_geom GEOMETRY,
            community_board VARCHAR,
            inspection_count INT,
            last_inspection_date DATE,
            data_load_timestamp TIMESTAMP
        )
        """
        self.conn.execute(create_sql)
        logger.debug("Created raw.spatial_raw table")

    def _create_timeseries_raw(self) -> None:
        """Create raw.timeseries_raw table.

        Schema:
            date DATE: Date of the record
            borough VARCHAR: NYC borough code (MN, BX, BK, QN, SI)
            violation_count INT: Total violations on this date
            open_violations INT: Count of open violations
            closed_violations INT: Count of closed violations
            avg_severity_score DOUBLE: Average severity (0-5 scale)
            data_load_timestamp TIMESTAMP: When this row was loaded
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS raw.timeseries_raw (
            date DATE,
            borough VARCHAR,
            violation_count INT,
            open_violations INT,
            closed_violations INT,
            avg_severity_score DOUBLE,
            data_load_timestamp TIMESTAMP
        )
        """
        self.conn.execute(create_sql)
        logger.debug("Created raw.timeseries_raw table")

    def _create_violations_raw(self) -> None:
        """Create raw.violations_raw table.

        Schema:
            violation_id INT: Unique violation identifier
            inspection_id INT: Related inspection identifier
            violation_type VARCHAR: Type of violation
            violation_code VARCHAR: Code for the violation type
            violation_date DATE: Date violation was recorded
            status VARCHAR: Current status (Open, Closed, etc.)
            borough VARCHAR: NYC borough code (MN, BX, BK, QN, SI)
            data_load_timestamp TIMESTAMP: When this row was loaded
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS raw.violations_raw (
            violation_id INT,
            inspection_id INT,
            violation_type VARCHAR,
            violation_code VARCHAR,
            violation_date DATE,
            status VARCHAR,
            borough VARCHAR,
            data_load_timestamp TIMESTAMP
        )
        """
        self.conn.execute(create_sql)
        logger.debug("Created raw.violations_raw table")

    def load_inspection_data(self, df: pd.DataFrame) -> None:
        """Load inspection data into raw.inspection_raw.

        Args:
            df: pandas DataFrame with inspection data. Expected columns:
                objectid, created_date, violation_type, violation_code, severity,
                borough, block, lot, location_latitude, location_longitude,
                open_violation, inspector_id, community_board, data_load_timestamp

        Raises:
            RuntimeError: If connection is not active or insert fails

        Example:
            df = pd.DataFrame({
                'objectid': [1, 2, 3],
                'created_date': pd.to_datetime(['2026-01-01', '2026-01-02', '2026-01-03']),
                ...
            })
            loader.load_inspection_data(df)
        """
        try:
            self.conn.conn.from_df(df).insert_into("raw.inspection_raw")
            logger.info(f"Loaded {len(df)} rows into raw.inspection_raw")
        except Exception as e:
            logger.error(f"Failed to load inspection data: {e}")
            raise

    def load_spatial_data(self, df: pd.DataFrame) -> None:
        """Load spatial data into raw.spatial_raw.

        Args:
            df: pandas DataFrame with spatial data. Expected columns:
                location_id, borough, block, lot, latitude, longitude,
                the_geom, community_board, inspection_count,
                last_inspection_date, data_load_timestamp

        Raises:
            RuntimeError: If connection is not active or insert fails

        Example:
            df = pd.DataFrame({
                'location_id': ['LOC1', 'LOC2'],
                'borough': ['MN', 'BK'],
                ...
            })
            loader.load_spatial_data(df)
        """
        try:
            self.conn.conn.from_df(df).insert_into("raw.spatial_raw")
            logger.info(f"Loaded {len(df)} rows into raw.spatial_raw")
        except Exception as e:
            logger.error(f"Failed to load spatial data: {e}")
            raise

    def load_timeseries_data(self, df: pd.DataFrame) -> None:
        """Load timeseries data into raw.timeseries_raw.

        Args:
            df: pandas DataFrame with timeseries data. Expected columns:
                date, borough, violation_count, open_violations,
                closed_violations, avg_severity_score, data_load_timestamp

        Raises:
            RuntimeError: If connection is not active or insert fails

        Example:
            df = pd.DataFrame({
                'date': pd.to_datetime(['2026-01-01', '2026-01-02']),
                'borough': ['MN', 'BK'],
                ...
            })
            loader.load_timeseries_data(df)
        """
        try:
            self.conn.conn.from_df(df).insert_into("raw.timeseries_raw")
            logger.info(f"Loaded {len(df)} rows into raw.timeseries_raw")
        except Exception as e:
            logger.error(f"Failed to load timeseries data: {e}")
            raise

    def load_violations_data(self, df: pd.DataFrame) -> None:
        """Load violations data into raw.violations_raw.

        Args:
            df: pandas DataFrame with violations data. Expected columns:
                violation_id, inspection_id, violation_type, violation_code,
                violation_date, status, borough, data_load_timestamp

        Raises:
            RuntimeError: If connection is not active or insert fails

        Example:
            df = pd.DataFrame({
                'violation_id': [1001, 1002],
                'inspection_id': [1, 2],
                ...
            })
            loader.load_violations_data(df)
        """
        try:
            self.conn.conn.from_df(df).insert_into("raw.violations_raw")
            logger.info(f"Loaded {len(df)} rows into raw.violations_raw")
        except Exception as e:
            logger.error(f"Failed to load violations data: {e}")
            raise
