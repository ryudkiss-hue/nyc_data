"""Schema Management for MotherDuck Cloud Databases."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SchemaManager:
    """
    Manages database schemas for raw, staging, and analytics layers.

    Detects schema changes, tracks column history, and validates type compatibility.
    """

    # Standard schemas for each layer
    RAW_SCHEMA = {
        "source_fourfour": "VARCHAR",
        "dataset_key": "VARCHAR",
        "raw_data": "JSON",
        "fetched_at": "TIMESTAMP",
        "hash": "VARCHAR",
    }

    STAGING_SCHEMA = {
        "id": "VARCHAR",
        "dataset_key": "VARCHAR",
        "classification": "VARCHAR",
        "staged_at": "TIMESTAMP",
        "data": "JSON",
        "row_hash": "VARCHAR",
    }

    ANALYTICS_SCHEMA = {
        "id": "VARCHAR",
        "dataset_key": "VARCHAR",
        "kpi_name": "VARCHAR",
        "kpi_value": "DOUBLE",
        "computed_at": "TIMESTAMP",
        "dimensions": "JSON",
    }

    def __init__(self, client):
        """
        Initialize schema manager.

        Args:
            client: MotherDuckClient instance
        """
        self.client = client
        self._cached_schemas = {}

    def get_raw_schema(self) -> dict[str, str]:
        """Get schema for raw data layer."""
        return self.RAW_SCHEMA.copy()

    def get_staging_schema(self) -> dict[str, str]:
        """Get schema for staging layer."""
        return self.STAGING_SCHEMA.copy()

    def get_analytics_schema(self) -> dict[str, str]:
        """Get schema for analytics layer."""
        return self.ANALYTICS_SCHEMA.copy()

    def detect_schema_drift(
        self, database: str, table: str, expected_schema: dict[str, str]
    ) -> dict[str, list[str]]:
        """
        Detect schema changes vs expected.

        Args:
            database: Database name
            table: Table name
            expected_schema: Expected column definitions

        Returns:
            Dictionary with added_columns, removed_columns, type_changes
        """
        sql = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='{database}' AND table_name='{table}'
        """
        try:
            results = self.client.query(sql)
            actual_schema = {row[0]: row[1] for row in results}

            added = list(set(actual_schema.keys()) - set(expected_schema.keys()))
            removed = list(set(expected_schema.keys()) - set(actual_schema.keys()))
            type_changes = [
                col
                for col in expected_schema
                if col in actual_schema
                and actual_schema[col] != expected_schema[col]
            ]

            return {
                "added_columns": added,
                "removed_columns": removed,
                "type_changes": type_changes,
            }
        except Exception as e:
            logger.error(f"Failed to detect schema drift: {e}")
            return {
                "added_columns": [],
                "removed_columns": [],
                "type_changes": [],
            }

    def validate_schema(
        self, database: str, table: str, expected_schema: dict[str, str]
    ) -> bool:
        """
        Validate table schema against expected.

        Args:
            database: Database name
            table: Table name
            expected_schema: Expected schema

        Returns:
            True if schema is compatible
        """
        drift = self.detect_schema_drift(database, table, expected_schema)
        is_compatible = (
            not drift["added_columns"]
            and not drift["removed_columns"]
            and not drift["type_changes"]
        )

        if not is_compatible:
            logger.warning(f"Schema mismatch in {database}.{table}: {drift}")

        return is_compatible
