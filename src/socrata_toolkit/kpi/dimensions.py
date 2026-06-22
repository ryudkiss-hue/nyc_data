"""Dimension breakdown aggregation for KPI analysis.

Breaks down KPI values across dimensions (borough, contractor, material_type)
and computes contribution %, ranking, and status per dimension value.
"""

import logging
from datetime import date
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class DimensionBreakdown:
    """Aggregates KPI values across dimension values."""

    @staticmethod
    def aggregate_by_dimension(kpi_id: str, period: date, dimension_name: str,
                               dimension_values: Dict[str, float],
                               target: float) -> Dict[str, dict]:
        """Aggregate KPI across dimension values with contribution and ranking.

        Args:
            kpi_id: KPI identifier
            period: Analysis period
            dimension_name: Dimension name (e.g., 'borough', 'contractor')
            dimension_values: {value: kpi_metric} e.g., {'MN': 95.3, 'BK': 87.2}
            target: Overall KPI target for status determination

        Returns:
            {dimension_value: {metric_value, contribution_pct, rank, status}}
        """

        if not dimension_values:
            return {}

        # Calculate total and contribution percentages
        total = sum(dimension_values.values())
        result = {}

        for value, metric in dimension_values.items():
            contribution = (metric / total * 100.0) if total > 0 else 0.0
            achievement = (metric / target * 100.0) if target > 0 else 0.0
            status = DimensionBreakdown._determine_status(achievement)

            result[str(value)] = {
                'metric_value': metric,
                'contribution_pct': contribution,
                'status': status,
                'achievement_pct': achievement
            }

        # Add ranking (sort by metric_value, descending)
        sorted_values = sorted(result.items(), key=lambda x: x[1]['metric_value'], reverse=True)
        for rank, (value, data) in enumerate(sorted_values, 1):
            result[value]['rank'] = rank

        logger.debug(f"KPI {kpi_id}/{dimension_name}: {len(result)} values aggregated")
        return result

    @staticmethod
    def _determine_status(achievement_pct: float) -> str:
        """Map achievement % to status."""
        if achievement_pct >= 80:
            return 'gold'
        elif achievement_pct >= 60:
            return 'silver'
        else:
            return 'bronze'

    @staticmethod
    def get_top_dimensions(aggregated: Dict[str, dict], top_n: int = 10) -> List[str]:
        """Get top N dimension values by contribution."""
        sorted_dims = sorted(
            aggregated.items(),
            key=lambda x: x[1].get('contribution_pct', 0),
            reverse=True
        )
        return [dim for dim, _ in sorted_dims[:top_n]]

    @staticmethod
    def compute_disparity_index(aggregated: Dict[str, dict]) -> float:
        """Compute disparity across dimension values (coefficient of variation)."""
        if not aggregated or len(aggregated) < 2:
            return 0.0

        values = [data['metric_value'] for data in aggregated.values()]
        mean = np.mean(values)
        stdev = np.std(values)

        return (stdev / mean) if mean > 0 else 0.0


def create_dimension_breakdown() -> DimensionBreakdown:
    """Factory for dimension breakdown aggregator."""
    return DimensionBreakdown()
