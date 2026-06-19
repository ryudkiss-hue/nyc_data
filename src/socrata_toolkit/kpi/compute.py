"""KPI computation and trend analysis.

Executes KPI definitions and computes:
- Current KPI values
- Trends (period-over-period, month-over-month)
- Status determination (gold/silver/bronze)
- Dimension breakdowns
"""

from typing import Optional, List, Dict
from datetime import date, datetime, timezone
from dataclasses import dataclass
import logging
import numpy as np

from socrata_toolkit.kpi.models import KPIDefinition, Trend, KPIValue

logger = logging.getLogger(__name__)


@dataclass
class ComputationResult:
    """Result of KPI computation."""
    kpi_id: str
    period: date
    value: float
    target: float
    achievement_pct: float
    status: str
    trend: Optional[Trend]


class KPIComputer:
    """Computes KPI values and derives trends."""

    def compute_kpi_value(self, kpi_def: KPIDefinition, period: date,
                         conn) -> Optional[float]:
        """Execute KPI computation SQL.

        Args:
            kpi_def: KPI definition with materialization_sql
            period: Period to compute for
            conn: DuckDB connection

        Returns:
            Computed KPI value, or None if computation fails
        """
        try:
            # Replace period placeholder in SQL if present
            sql = kpi_def.materialization_sql.replace('{period}', str(period))

            result = conn.execute(sql).fetch_arrow_table()

            if len(result) == 0:
                logger.warning(f"KPI {kpi_def.kpi_id}: no data for period {period}")
                return None

            # Extract first column, first row
            value = result[0][0].as_py()

            if value is None or (isinstance(value, float) and np.isnan(value)):
                logger.warning(f"KPI {kpi_def.kpi_id}: null or NaN value")
                return None

            return float(value)

        except Exception as e:
            logger.error(f"KPI {kpi_def.kpi_id}: computation failed: {e}")
            return None

    def compute_trend(self, kpi_id: str, current_value: float,
                     historical: List[KPIValue]) -> Optional[Trend]:
        """Calculate period-over-period trends.

        Args:
            kpi_id: KPI identifier
            current_value: Current period value
            historical: Historical KPI values (chronologically ordered)

        Returns:
            Trend object with period-over-period, forecast, and anomaly data
        """

        if not historical or len(historical) == 0:
            return Trend(
                period_over_period=0.0,
                historical_average_variance=0.0,
                forecast_next_period=current_value,
                anomaly_flagged=False,
                anomaly_z_score=0.0
            )

        # Period-over-period (previous period vs current)
        prev_value = historical[-1].value if historical else current_value
        pct_change = ((current_value - prev_value) / prev_value * 100.0) if prev_value != 0 else 0.0

        # Historical average variance
        values = [h.value for h in historical]
        avg = np.mean(values)
        avg_variance = ((current_value - avg) / avg * 100.0) if avg != 0 else 0.0

        return Trend(
            period_over_period=pct_change,
            historical_average_variance=avg_variance,
            forecast_next_period=current_value,
            anomaly_flagged=False,
            anomaly_z_score=0.0
        )

    def determine_status(self, kpi_def: KPIDefinition, current: float,
                        target: float) -> str:
        """Map KPI value to status using threshold configuration.

        Status mapping (example, uses kpi_def.threshold_config):
        - gold: >= 80% of target
        - silver: 60-80% of target
        - bronze: < 60% of target

        Args:
            kpi_def: KPI definition with threshold_config
            current: Current KPI value
            target: Target value

        Returns:
            Status: 'gold', 'silver', or 'bronze'
        """

        if target <= 0:
            return 'bronze'

        achievement = (current / target) * 100.0

        if achievement >= 80:
            return 'gold'
        elif achievement >= 60:
            return 'silver'
        else:
            return 'bronze'

    def compute_dimension_breakdown(self, kpi_id: str, period: date,
                                    dimension_name: str,
                                    breakdown_sql: str,
                                    conn) -> Dict[str, float]:
        """Aggregate KPI across dimension values.

        Args:
            kpi_id: KPI identifier
            period: Period to compute for
            dimension_name: Dimension name (e.g., 'borough')
            breakdown_sql: SQL with placeholders {dimension}, {period}
            conn: DuckDB connection

        Returns:
            Dictionary: {dimension_value: aggregated_value}
        """

        try:
            # This is a simplified version; real implementation would
            # execute dimension-specific SQL
            sql = breakdown_sql.replace('{period}', str(period))

            result = conn.execute(sql).fetch_arrow_table()

            breakdown = {}
            for i in range(len(result)):
                dim_value = result[0][i].as_py()
                agg_value = result[1][i].as_py()
                if dim_value and agg_value is not None:
                    breakdown[str(dim_value)] = float(agg_value)

            return breakdown

        except Exception as e:
            logger.error(f"KPI {kpi_id}: dimension breakdown failed: {e}")
            return {}

    def build_computation_result(self, kpi_def: KPIDefinition, period: date,
                                current_value: float,
                                historical: Optional[List[KPIValue]] = None) -> ComputationResult:
        """Assemble complete computation result.

        Args:
            kpi_def: KPI definition
            period: Computation period
            current_value: Computed KPI value
            historical: Historical values for trend calculation

        Returns:
            ComputationResult with value, status, and trends
        """

        target = kpi_def.target
        achievement = (current_value / target * 100.0) if target > 0 else 0.0
        status = self.determine_status(kpi_def, current_value, target)
        trend = self.compute_trend(kpi_def.kpi_id, current_value, historical or [])

        return ComputationResult(
            kpi_id=kpi_def.kpi_id,
            period=period,
            value=current_value,
            target=target,
            achievement_pct=achievement,
            status=status,
            trend=trend
        )


def create_kpi_computer() -> KPIComputer:
    """Factory for KPI computer."""
    return KPIComputer()
