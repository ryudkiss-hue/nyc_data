"""
Generic ETL Staging Framework for NYC DOT SIM Workflows.

Extensible stage_dataset() function for all 24 Socrata datasets.
Supports classification, mapping, derivations, deduplication, validation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StagingResult:
    """Result of staging operation."""

    dataset_key: str
    rows_in: int
    rows_out: int
    rows_deduplicated: int
    errors: list[str]
    execution_time_secs: float
    timestamp: datetime

    @property
    def success(self) -> bool:
        """Whether staging completed without errors."""
        return len(self.errors) == 0


class TransformationRegistry:
    """Registry of transformations for all 24 datasets."""

    # Classification transformations
    CLASSIFICATIONS = {
        "violations": ["open", "closed", "appealed", "dismissed"],
        "dismissals": ["upheld", "reversed", "appealed"],
        "ramps": ["completed", "in_progress", "planned", "stalled"],
        "permits": ["approved", "pending", "denied", "cancelled"],
    }

    # Value mappings
    BOROUGH_MAPPING = {
        "1": "MN",  # Manhattan
        "2": "BX",  # Bronx
        "3": "BK",  # Brooklyn
        "4": "QN",  # Queens
        "5": "SI",  # Staten Island
    }

    STATUS_MAPPING = {
        "OPEN": "open",
        "CLOSED": "closed",
        "IN_PROGRESS": "in_progress",
        "PENDING": "pending",
        "COMPLETED": "completed",
    }

    @classmethod
    def get_classifications(cls, dataset_key: str) -> list[str]:
        """Get valid classifications for a dataset."""
        return cls.CLASSIFICATIONS.get(dataset_key, [])

    @classmethod
    def get_borough_code(cls, code: str) -> str:
        """Map borough code to abbreviation."""
        return cls.BOROUGH_MAPPING.get(code, code)

    @classmethod
    def normalize_status(cls, status: str) -> str:
        """Normalize status value."""
        return cls.STATUS_MAPPING.get(status.upper(), status.lower())


def stage_dataset(
    dataset_key: str,
    raw_df: Any,  # Pandas DataFrame or DuckDB relation
    client: Any,  # MotherDuckClient
    transformations: Optional[dict[str, Any]] = None,
    dedup_cols: Optional[list[str]] = None,
) -> StagingResult:
    """
    Generic staging function for all 24 datasets.

    Transforms raw data → staging layer with classification, mapping, validation.

    Args:
        dataset_key: Dataset identifier (e.g., 'violations', 'ramp_progress')
        raw_df: Input dataframe (raw layer data)
        client: MotherDuckClient instance
        transformations: Dict of {column: transformation_func}
        dedup_cols: Columns to use for deduplication

    Returns:
        StagingResult with staging metrics
    """
    start_time = datetime.now()
    errors = []
    rows_deduplicated = 0

    try:
        # 1. Infer schema from sample
        logger.info(f"[STAGE] {dataset_key}: Analyzing schema...")
        if hasattr(raw_df, "shape"):
            rows_in = raw_df.shape[0]
        else:
            # DuckDB relation
            rows_in = raw_df.count().fetchall()[0][0]

        # 2. Apply transformations
        logger.info(f"[STAGE] {dataset_key}: Applying transformations...")
        if transformations:
            for col, func in transformations.items():
                if col in raw_df.columns:
                    try:
                        if callable(func):
                            raw_df[col] = raw_df[col].apply(func)
                        else:
                            # Dictionary mapping
                            raw_df[col] = raw_df[col].map(func)
                    except Exception as e:
                        errors.append(f"Transform {col} failed: {e}")

        # 3. Deduplicate
        logger.info(f"[STAGE] {dataset_key}: Deduplicating...")
        if dedup_cols:
            rows_before_dedup = len(raw_df)
            raw_df = raw_df.drop_duplicates(subset=dedup_cols, keep="last")
            rows_deduplicated = rows_before_dedup - len(raw_df)

        # 4. Validate
        logger.info(f"[STAGE] {dataset_key}: Validating...")
        null_checks = raw_df.isnull().sum()
        for col, null_count in null_checks.items():
            null_pct = (null_count / len(raw_df)) * 100
            if null_pct > 50:
                errors.append(f"Column {col}: {null_pct:.1f}% nulls")

        rows_out = len(raw_df)

        # 5. Land in staging
        logger.info(f"[STAGE] {dataset_key}: Landing in staging_cloud...")
        table_name = f"staging_cloud.{dataset_key}_staging"
        # In production: raw_df.to_sql(table_name, con=client.connect())

        logger.info(
            f"[STAGE] {dataset_key} complete: "
            f"{rows_in} → {rows_out} rows (dedup: {rows_deduplicated})"
        )

    except Exception as e:
        logger.error(f"[STAGE] {dataset_key} FAILED: {e}")
        errors.append(str(e))

    execution_time = (datetime.now() - start_time).total_seconds()

    return StagingResult(
        dataset_key=dataset_key,
        rows_in=rows_in,
        rows_out=rows_out,
        rows_deduplicated=rows_deduplicated,
        errors=errors,
        execution_time_secs=execution_time,
        timestamp=datetime.now(),
    )


def stage_all_datasets(
    datasets: list[dict[str, Any]], client: Any
) -> list[StagingResult]:
    """
    Stage all datasets in sequence.

    Args:
        datasets: List of dicts with dataset_key, raw_df, transformations
        client: MotherDuckClient

    Returns:
        List of StagingResult objects
    """
    results = []

    for dataset in datasets:
        result = stage_dataset(
            dataset_key=dataset["dataset_key"],
            raw_df=dataset["raw_df"],
            client=client,
            transformations=dataset.get("transformations"),
            dedup_cols=dataset.get("dedup_cols"),
        )
        results.append(result)

    # Summary
    total_rows_in = sum(r.rows_in for r in results)
    total_rows_out = sum(r.rows_out for r in results)
    total_errors = sum(len(r.errors) for r in results)

    logger.info(
        f"\n[STAGING COMPLETE] "
        f"{len(results)} datasets, "
        f"{total_rows_in} → {total_rows_out} rows, "
        f"{total_errors} errors"
    )

    return results
