"""KPI materialization orchestrator.

Coordinates the full pipeline:
1. Load KPI definitions from registry
2. Compute KPI values from staging data
3. Generate forecasts
4. Detect anomalies
5. Calculate trends
6. Persist to analytics schema
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from socrata_toolkit.kpi.anomaly import AnomalyDetector, create_anomaly_detector
from socrata_toolkit.kpi.compute import KPIComputer, create_kpi_computer
from socrata_toolkit.kpi.database import (
    get_kpi_time_series,
    initialize_analytics_schema,
    upsert_anomaly,
    upsert_forecast,
    upsert_kpi_latest,
    upsert_kpi_time_series,
)
from socrata_toolkit.kpi.forecasting import ForecastingEngine, create_forecasting_engine
from socrata_toolkit.kpi.registry import KPIRegistry

logger = logging.getLogger(__name__)


@dataclass
class MaterializationResult:
    """Outcome of a materialization run."""
    run_id: str
    started_at: datetime
    completed_at: datetime
    total_kpis: int
    successful_kpis: int
    failed_kpis: List[str]
    execution_seconds: float

    def success_rate(self) -> float:
        """Percentage of KPIs computed successfully."""
        return (self.successful_kpis / self.total_kpis * 100.0) if self.total_kpis > 0 else 0.0


class MaterializationOrchestrator:
    """Orchestrates KPI materialization pipeline."""

    def __init__(self, duckdb_manager, registry: KPIRegistry):
        """Initialize orchestrator.

        Args:
            duckdb_manager: DuckDB connection manager
            registry: KPI registry with all KPI definitions
        """
        self.db = duckdb_manager
        self.registry = registry
        self.computer = create_kpi_computer()
        self.forecasting = create_forecasting_engine()
        self.anomaly_detector = create_anomaly_detector()

    def materialize_all_kpis(self, period: date) -> MaterializationResult:
        """Execute full materialization pipeline for all KPIs.

        Args:
            period: Period to materialize (e.g., date(2026, 6, 1))

        Returns:
            MaterializationResult with execution status
        """

        run_id = str(uuid.uuid4())[:8]
        started = datetime.now(timezone.utc)

        logger.info(f"Materialization run {run_id} started for period {period}")

        # Initialize schema if needed
        with self.db.get_connection() as conn:
            initialize_analytics_schema(conn)

        # Materialize each KPI
        successful = 0
        failed = []

        for kpi in self.registry.get_all_kpis():
            try:
                self._materialize_kpi(kpi, period)
                successful += 1
            except Exception as e:
                logger.error(f"Failed to materialize KPI {kpi.kpi_id}: {e}")
                failed.append(kpi.kpi_id)

        completed = datetime.now(timezone.utc)
        elapsed = (completed - started).total_seconds()

        result = MaterializationResult(
            run_id=run_id,
            started_at=started,
            completed_at=completed,
            total_kpis=len(self.registry.get_all_kpis()),
            successful_kpis=successful,
            failed_kpis=failed,
            execution_seconds=elapsed
        )

        logger.info(f"Materialization run {run_id} complete: "
                   f"{successful}/{result.total_kpis} KPIs materialized in {elapsed:.1f}s")

        return result

    def _materialize_kpi(self, kpi, period: date):
        """Materialize single KPI for a period.

        Steps:
        1. Compute current value
        2. Fetch historical data
        3. Generate forecast
        4. Detect anomaly
        5. Upsert to analytics tables
        """

        with self.db.get_connection() as conn:
            # 1. Compute KPI value
            current_value = self.computer.compute_kpi_value(kpi, period, conn)
            if current_value is None:
                logger.warning(f"KPI {kpi.kpi_id}: no value computed for {period}")
                return

            # 2. Fetch historical data
            historical = get_kpi_time_series(conn, kpi.kpi_id, months_back=12)
            historical_values = [h['value'] for h in historical]

            # 3. Generate forecast
            forecast_result = None
            if historical_values:
                forecast_result = self.forecasting.forecast_kpi(
                    kpi.kpi_id, historical_values, periods_ahead=3
                )

            # 4. Detect anomaly
            anomaly_result = self.anomaly_detector.detect(
                kpi.kpi_id, current_value, historical_values
            )

            # 5. Upsert to analytics tables
            upsert_kpi_time_series(
                conn, kpi.kpi_id, period, borough=None,
                current_value=current_value, target=kpi.target
            )

            if forecast_result:
                upsert_forecast(
                    conn, kpi.kpi_id, period,
                    forecast_value=forecast_result.forecast_values[0],
                    ci_lower=forecast_result.ci_lower[0],
                    ci_upper=forecast_result.ci_upper[0],
                    confidence=forecast_result.confidence_score,
                    method=forecast_result.method
                )

            upsert_anomaly(
                conn, kpi.kpi_id, period,
                observed=anomaly_result.observed_value,
                expected=anomaly_result.expected_value,
                z_score=anomaly_result.z_score,
                is_anomaly=anomaly_result.is_anomaly,
                severity=anomaly_result.severity
            )

            # Determine status
            status = self.computer.determine_status(kpi, current_value, kpi.target)

            upsert_kpi_latest(
                conn, kpi.kpi_id, period,
                current=current_value, target=kpi.target, status=status
            )

            logger.debug(f"KPI {kpi.kpi_id}: materialized for {period} = {current_value:.2f}")


def create_orchestrator(duckdb_manager, registry: KPIRegistry) -> MaterializationOrchestrator:
    """Factory for materialization orchestrator."""
    return MaterializationOrchestrator(duckdb_manager, registry)
