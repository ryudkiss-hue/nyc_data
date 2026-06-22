"""KPIEngine: Compute KPIs with validation and metadata."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class KPIResult:
    """Result of KPI computation with metadata.

    Attributes:
        kpi_name: KPI identifier
        dataset_key: Dataset identifier
        value: Computed KPI value
        unit: Unit of measurement (count, percent, days, etc.)
        timestamp: When KPI was computed
        freshness_days: Data freshness (days since last update)
        sample_size: Number of records used in computation
        metadata: Additional context (target, status, etc.)
    """

    kpi_name: str
    dataset_key: str
    value: float | int | str | None
    unit: str
    timestamp: str
    freshness_days: int | None = None
    sample_size: int | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.kpi_name}={self.value} {self.unit} (n={self.sample_size})"


class KPIEngine:
    """Compute and validate KPIs from datasets.

    Provides centralized KPI calculation with:
    - Schema validation before computation
    - Type-safe result objects
    - Metadata tracking (freshness, sample size)
    - Error handling and logging

    Usage:
        engine = KPIEngine(registry, schema_registry)
        result = engine.compute(
            dataset_key="inspection",
            kpi_name="inspections_scheduled_week",
            data=df,
        )
        print(result.value, result.unit)
    """

    def __init__(
        self,
        registry: dict[str, Any],
        schema_registry: Any | None = None,
    ):
        """Initialize KPI engine.

        Args:
            registry: DATASET_REGISTRY configuration
            schema_registry: Optional SchemaRegistry for validation
        """
        self.registry = registry
        self.schema_registry = schema_registry
        self.datasets = registry.get("datasets", {})
        self.computed_kpis = {}

    def compute(
        self,
        dataset_key: str,
        kpi_name: str,
        data: pd.DataFrame | None = None,
        filters: dict[str, Any] | None = None,
    ) -> KPIResult:
        """Compute KPI from dataset.

        Args:
            dataset_key: Dataset identifier (e.g., "inspection")
            kpi_name: KPI identifier (e.g., "inspections_scheduled_week")
            data: Optional DataFrame (if None, raises error)
            filters: Optional filter dictionary

        Returns:
            KPIResult with computed value and metadata

        Raises:
            ValueError: If dataset or KPI not found
            KeyError: If required columns missing
        """
        if dataset_key not in self.datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")

        dataset = self.datasets[dataset_key]

        if kpi_name not in dataset.get("kpis", []):
            raise ValueError(
                f"KPI '{kpi_name}' not configured for dataset '{dataset_key}'"
            )

        if data is None:
            raise ValueError("DataFrame required for KPI computation")

        # Validate schema if enabled
        if self.schema_registry:
            validation = self.schema_registry.validate(dataset_key, data)
            if not validation.is_valid:
                raise ValueError(
                    f"Schema validation failed: {validation.errors}"
                )

        # Dispatch to KPI-specific calculation
        method_name = f"_compute_{kpi_name}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            result = method(data, dataset_key)
        else:
            logger.warning(
                f"No implementation for KPI: {kpi_name}, returning placeholder"
            )
            result = KPIResult(
                kpi_name=kpi_name,
                dataset_key=dataset_key,
                value=None,
                unit="unknown",
                timestamp=datetime.now().isoformat(),
                metadata={"status": "not_implemented"},
            )

        # Cache result
        self.computed_kpis[f"{dataset_key}:{kpi_name}"] = result
        return result

    # ========================================================================
    # Inspection KPIs
    # ========================================================================

    def _compute_inspections_scheduled_week(
        self, df: pd.DataFrame, dataset_key: str
    ) -> KPIResult:
        """Inspections scheduled this week."""
        try:
            count = len(df)
            return KPIResult(
                kpi_name="inspections_scheduled_week",
                dataset_key=dataset_key,
                value=count,
                unit="inspections",
                timestamp=datetime.now().isoformat(),
                sample_size=count,
                metadata={"target": 500, "status": "active"},
            )
        except Exception as e:
            logger.error(f"Error computing inspections_scheduled_week: {e}")
            return self._error_result(
                "inspections_scheduled_week", dataset_key, str(e)
            )

    def _compute_inspection_completion_rate(
        self, df: pd.DataFrame, dataset_key: str
    ) -> KPIResult:
        """Inspection completion rate."""
        try:
            if "status" not in df.columns:
                raise KeyError("Column 'status' not found")

            completed = (df["status"] == "COMPLETED").sum()
            total = len(df)
            rate = (completed / total * 100) if total > 0 else 0

            return KPIResult(
                kpi_name="inspection_completion_rate",
                dataset_key=dataset_key,
                value=round(rate, 2),
                unit="percent",
                timestamp=datetime.now().isoformat(),
                sample_size=total,
                metadata={"target": 95, "status": "active"},
            )
        except Exception as e:
            logger.error(f"Error computing inspection_completion_rate: {e}")
            return self._error_result(
                "inspection_completion_rate", dataset_key, str(e)
            )

    def _compute_avg_violations_per_inspection(
        self, df: pd.DataFrame, dataset_key: str
    ) -> KPIResult:
        """Average violations per inspection."""
        try:
            if "violation_count" not in df.columns:
                raise KeyError("Column 'violation_count' not found")

            avg_violations = df["violation_count"].mean()

            return KPIResult(
                kpi_name="avg_violations_per_inspection",
                dataset_key=dataset_key,
                value=round(avg_violations, 2),
                unit="violations/inspection",
                timestamp=datetime.now().isoformat(),
                sample_size=len(df),
                metadata={"target": 2.5, "status": "active"},
            )
        except Exception as e:
            logger.error(
                f"Error computing avg_violations_per_inspection: {e}"
            )
            return self._error_result(
                "avg_violations_per_inspection", dataset_key, str(e)
            )

    # ========================================================================
    # Violation KPIs
    # ========================================================================

    def _compute_violations_open_count(
        self, df: pd.DataFrame, dataset_key: str
    ) -> KPIResult:
        """Count of open violations."""
        try:
            if "status" not in df.columns:
                raise KeyError("Column 'status' not found")

            open_count = (df["status"] == "OPEN").sum()

            return KPIResult(
                kpi_name="violations_open_count",
                dataset_key=dataset_key,
                value=open_count,
                unit="violations",
                timestamp=datetime.now().isoformat(),
                sample_size=len(df),
                metadata={"status": "active"},
            )
        except Exception as e:
            logger.error(f"Error computing violations_open_count: {e}")
            return self._error_result(
                "violations_open_count", dataset_key, str(e)
            )

    def _compute_violation_resolution_time(
        self, df: pd.DataFrame, dataset_key: str
    ) -> KPIResult:
        """Average violation resolution time in days."""
        try:
            if "resolution_time_days" not in df.columns:
                raise KeyError("Column 'resolution_time_days' not found")

            avg_time = df["resolution_time_days"].mean()

            return KPIResult(
                kpi_name="violation_resolution_time",
                dataset_key=dataset_key,
                value=round(avg_time, 1),
                unit="days",
                timestamp=datetime.now().isoformat(),
                sample_size=len(df),
                metadata={"target": 30, "status": "active"},
            )
        except Exception as e:
            logger.error(f"Error computing violation_resolution_time: {e}")
            return self._error_result(
                "violation_resolution_time", dataset_key, str(e)
            )

    # ========================================================================
    # Accessibility KPIs
    # ========================================================================

    def _compute_ramp_completion_by_borough(
        self, df: pd.DataFrame, dataset_key: str
    ) -> KPIResult:
        """Ramp completion rate by borough."""
        try:
            if "status" not in df.columns:
                raise KeyError("Column 'status' not found")

            completed = (df["status"] == "COMPLETED").sum()
            total = len(df)
            rate = (completed / total * 100) if total > 0 else 0

            return KPIResult(
                kpi_name="ramp_completion_by_borough",
                dataset_key=dataset_key,
                value=round(rate, 2),
                unit="percent",
                timestamp=datetime.now().isoformat(),
                sample_size=total,
                metadata={"target": 80, "status": "active"},
            )
        except Exception as e:
            logger.error(f"Error computing ramp_completion_by_borough: {e}")
            return self._error_result(
                "ramp_completion_by_borough", dataset_key, str(e)
            )

    # ========================================================================
    # Helper methods
    # ========================================================================

    def _error_result(
        self, kpi_name: str, dataset_key: str, error_msg: str
    ) -> KPIResult:
        """Create error result for failed KPI computation."""
        return KPIResult(
            kpi_name=kpi_name,
            dataset_key=dataset_key,
            value=None,
            unit="error",
            timestamp=datetime.now().isoformat(),
            metadata={"error": error_msg, "status": "failed"},
        )

    def get_cached_kpi(
        self, dataset_key: str, kpi_name: str
    ) -> KPIResult | None:
        """Retrieve cached KPI result.

        Args:
            dataset_key: Dataset identifier
            kpi_name: KPI identifier

        Returns:
            KPIResult if cached, None otherwise
        """
        key = f"{dataset_key}:{kpi_name}"
        return self.computed_kpis.get(key)
