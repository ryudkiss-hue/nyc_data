"""SchemaRegistry: Central schema validation layer."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of schema validation.

    Attributes:
        is_valid: Whether validation passed
        dataset_key: Dataset identifier
        errors: List of validation errors
        warnings: List of validation warnings
        columns_expected: Expected columns from registry
        columns_present: Actual columns in DataFrame
    """

    is_valid: bool
    dataset_key: str
    errors: list[str]
    warnings: list[str]
    columns_expected: list[str]
    columns_present: list[str]

    def __str__(self) -> str:
        """String representation."""
        status = "✓ VALID" if self.is_valid else "✗ INVALID"
        msg = f"{status} | Dataset: {self.dataset_key}"
        if self.errors:
            msg += f" | Errors: {len(self.errors)}"
        if self.warnings:
            msg += f" | Warnings: {len(self.warnings)}"
        return msg


class SchemaRegistry:
    """Central registry for dataset schemas with validation.

    Maintains schemas for all datasets and provides:
    - Column validation (existence, type matching)
    - Required field checking
    - Data quality validation
    - Type coercion

    Usage:
        registry = SchemaRegistry(dataset_registry)
        result = registry.validate("inspection", df)
        if not result.is_valid:
            print("Errors:", result.errors)
    """

    def __init__(self, dataset_registry: dict[str, Any]):
        """Initialize schema registry.

        Args:
            dataset_registry: DATASET_REGISTRY configuration
        """
        self.registry = dataset_registry
        self.datasets = dataset_registry.get("datasets", {})
        self.validation_cache = {}

    def validate(
        self, dataset_key: str, df: pd.DataFrame
    ) -> ValidationResult:
        """Validate DataFrame against dataset schema.

        Args:
            dataset_key: Dataset identifier
            df: DataFrame to validate

        Returns:
            ValidationResult with validation status and details

        Raises:
            ValueError: If dataset not found
        """
        if dataset_key not in self.datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")

        dataset_config = self.datasets[dataset_key]
        columns_config = dataset_config.get("columns", [])

        errors = []
        warnings = []

        # Extract expected columns
        columns_expected = [col["name"] for col in columns_config]
        columns_present = df.columns.tolist() if not df.empty else []

        # Check for required columns
        required_columns = [
            col["name"]
            for col in columns_config
            if col.get("required", False)
        ]

        for col_name in required_columns:
            if col_name not in columns_present:
                errors.append(
                    f"Required column '{col_name}' not found. "
                    f"Available: {columns_present}"
                )

        # Check for nulls in required columns
        if not df.empty:
            for col in required_columns:
                if col in df.columns:
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        warnings.append(
                            f"Required column '{col}' has {null_count} nulls"
                        )

        # Type checking (best effort)
        self._validate_types(
            df, columns_config, columns_present, errors, warnings
        )

        # Build result
        result = ValidationResult(
            is_valid=len(errors) == 0,
            dataset_key=dataset_key,
            errors=errors,
            warnings=warnings,
            columns_expected=columns_expected,
            columns_present=columns_present,
        )

        # Cache result
        cache_key = f"{dataset_key}:{id(df)}"
        self.validation_cache[cache_key] = result

        if errors:
            logger.error(
                f"Validation failed for {dataset_key}: {errors}"
            )
        elif warnings:
            logger.warning(
                f"Validation warnings for {dataset_key}: {warnings}"
            )
        else:
            logger.debug(f"Validation passed for {dataset_key}")

        return result

    def _validate_types(
        self,
        df: pd.DataFrame,
        columns_config: list[dict[str, Any]],
        columns_present: list[str],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Validate column types.

        Args:
            df: DataFrame to validate
            columns_config: Column configurations from schema
            columns_present: Actual columns in DataFrame
            errors: List to append errors to
            warnings: List to append warnings to
        """
        type_map = {
            "integer": ["int64", "int32", "int"],
            "float": ["float64", "float32", "float"],
            "string": ["object", "string", "str"],
            "datetime": ["datetime64", "datetime"],
            "boolean": ["bool", "boolean"],
            "geometry": ["object"],  # GeoDataFrame geometry
        }

        for col_config in columns_config:
            col_name = col_config["name"]
            expected_type = col_config.get("type", "unknown")

            if col_name not in columns_present:
                continue

            actual_type = str(df[col_name].dtype)

            # Check if type matches (permissive matching)
            expected_types = type_map.get(expected_type, [])
            if expected_types and actual_type not in expected_types:
                warnings.append(
                    f"Column '{col_name}' type mismatch: "
                    f"expected {expected_type}, got {actual_type}"
                )

    def get_schema(self, dataset_key: str) -> list[dict[str, Any]]:
        """Get schema for dataset.

        Args:
            dataset_key: Dataset identifier

        Returns:
            List of column configurations

        Raises:
            ValueError: If dataset not found
        """
        if dataset_key not in self.datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")

        return self.datasets[dataset_key].get("columns", [])

    def get_required_columns(self, dataset_key: str) -> list[str]:
        """Get list of required columns for dataset.

        Args:
            dataset_key: Dataset identifier

        Returns:
            List of required column names
        """
        schema = self.get_schema(dataset_key)
        return [col["name"] for col in schema if col.get("required", False)]

    def clear_cache(self) -> None:
        """Clear validation cache."""
        self.validation_cache.clear()
        logger.info("Cleared schema registry validation cache")
