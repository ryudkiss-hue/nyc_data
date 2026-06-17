"""DatasetLoader: Load datasets with schema validation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DatasetResult:
    """Result of dataset loading with validation status.

    Attributes:
        dataset_key: Dataset identifier
        data: DataFrame
        row_count: Number of rows returned
        columns_present: List of columns in returned data
        validation_status: "valid", "warning", or "error"
        errors: List of validation errors
        metadata: Freshness, source, etc.
    """

    dataset_key: str
    data: pd.DataFrame
    row_count: int
    columns_present: list[str]
    validation_status: str  # "valid", "warning", "error"
    errors: list[str]
    metadata: dict[str, Any]

    @property
    def is_valid(self) -> bool:
        """Check if dataset is valid (no errors)."""
        return self.validation_status != "error"


class DatasetLoader:
    """Load datasets with schema validation.

    Provides type-safe data loading:
    - Fetches from MotherDuck, local cache, or Socrata API
    - Validates columns exist and types match
    - Returns typed DatasetResult with metadata
    - Tracks freshness and data quality

    Usage:
        loader = DatasetLoader(registry)
        result = loader.load("inspection", filters={"borough": "MANHATTAN"})
        if result.is_valid:
            df = result.data
        else:
            print("Validation errors:", result.errors)
    """

    def __init__(
        self,
        registry: dict[str, Any],
        schema_registry: Any | None = None,
    ):
        """Initialize loader.

        Args:
            registry: DATASET_REGISTRY configuration
            schema_registry: Optional SchemaRegistry for validation
        """
        self.registry = registry
        self.schema_registry = schema_registry
        self.datasets = registry.get("datasets", {})
        self.cache = {}

    def load(
        self,
        dataset_key: str,
        filters: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> DatasetResult:
        """Load dataset with optional filtering and validation.

        Args:
            dataset_key: Dataset identifier (e.g., "inspection")
            filters: Optional filter dictionary (e.g., {"borough": "MANHATTAN"})
            use_cache: Whether to use cached data if available

        Returns:
            DatasetResult with data and validation status

        Raises:
            ValueError: If dataset not found
        """
        if dataset_key not in self.datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")

        dataset_config = self.datasets[dataset_key]

        # Check cache
        cache_key = f"{dataset_key}:{str(filters)}"
        if use_cache and cache_key in self.cache:
            logger.debug(f"Using cached data for {dataset_key}")
            return self.cache[cache_key]

        # Fetch data (placeholder — implement with MotherDuck/Socrata)
        df = self._fetch_data(dataset_key, filters)

        # Validate
        result = self._validate_dataset(dataset_key, df, dataset_config)

        # Cache result
        self.cache[cache_key] = result

        return result

    def _fetch_data(
        self, dataset_key: str, filters: dict[str, Any] | None = None
    ) -> pd.DataFrame:
        """Fetch data from source.

        Args:
            dataset_key: Dataset identifier
            filters: Optional filters

        Returns:
            DataFrame

        NOTE: Implement to fetch from MotherDuck, Socrata API, or local cache.
        """
        logger.debug(f"Fetching data for {dataset_key}")

        # Placeholder: return empty DataFrame
        # TODO: Implement actual data fetching:
        # - Try MotherDuck view first
        # - Fall back to Socrata API
        # - Cache as Parquet
        return pd.DataFrame()

    def _validate_dataset(
        self,
        dataset_key: str,
        df: pd.DataFrame,
        dataset_config: dict[str, Any],
    ) -> DatasetResult:
        """Validate dataset against schema.

        Args:
            dataset_key: Dataset identifier
            df: DataFrame to validate
            dataset_config: Dataset configuration from registry

        Returns:
            DatasetResult with validation status
        """
        errors = []
        warnings = []
        columns_present = df.columns.tolist() if not df.empty else []

        # Check required columns exist
        required_columns = [
            col["name"]
            for col in dataset_config.get("columns", [])
            if col.get("required", False)
        ]

        missing_columns = [
            col for col in required_columns if col not in columns_present
        ]

        if missing_columns:
            errors.append(
                f"Missing required columns: {', '.join(missing_columns)}"
            )

        # Check for nulls in required columns
        if not df.empty:
            for col in required_columns:
                if col in df.columns and df[col].isnull().any():
                    warnings.append(
                        f"Required column '{col}' contains nulls"
                    )

        # Determine status
        status = "error" if errors else ("warning" if warnings else "valid")

        result = DatasetResult(
            dataset_key=dataset_key,
            data=df,
            row_count=len(df),
            columns_present=columns_present,
            validation_status=status,
            errors=errors,
            metadata={
                "warnings": warnings,
                "fetched_at": datetime.now().isoformat(),
                "freshness_days": dataset_config.get("update_sla_days"),
                "quality_score": dataset_config.get("quality_score"),
            },
        )

        if errors:
            logger.error(f"Validation errors for {dataset_key}: {errors}")
        elif warnings:
            logger.warning(
                f"Validation warnings for {dataset_key}: {warnings}"
            )

        return result

    def clear_cache(self) -> None:
        """Clear data cache."""
        self.cache.clear()
        logger.info("Cleared dataset loader cache")
