"""
Analytics-to-Dashboard Bridge for NYC DOT SIM Workflows.

Connects Phase 3A KPI calculations to Phase 2A Dash visualizations.
Handles data flow: DuckDB cache → KPI calculation → Dashboard display.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class AnalyticsBridge:
    """
    Bridges analytics layer to dashboard visualizations.

    Responsibilities:
    - Fetch KPIs from analytics_cloud schema
    - Transform KPIs to chart-ready format
    - Handle real-time updates
    - Cache results for performance
    """

    def __init__(self, client: Any):
        """Initialize analytics bridge with database client."""
        self.client = client
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid."""
        if key not in self._cache:
            return False
        cached_time, _ = self._cache[key]
        return (datetime.now() - cached_time).total_seconds() < self._cache_ttl

    def _get_cached(self, key: str) -> Any:
        """Get value from cache if valid."""
        if self._is_cache_valid(key):
            return self._cache[key][1]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Store value in cache with timestamp."""
        self._cache[key] = (datetime.now(), value)

    def get_violation_kpis(self) -> dict[str, Any]:
        """
        Fetch violation KPIs for dashboard display (cached for 5 min).

        Returns:
            Dict with violation metrics ready for visualization
        """
        # Check cache first
        cache_key = 'violation_kpis'
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug("Returning cached violation KPIs")
            return cached

        try:
            sql = """
                SELECT
                    kpi_name,
                    kpi_value,
                    dimensions,
                    computed_at
                FROM analytics_cloud.violations_kpis
                ORDER BY computed_at DESC
                LIMIT 100
            """
            results = self.client.query(sql) if hasattr(self.client, 'query') else []

            response = {
                'kpis': results,
                'timestamp': datetime.now().isoformat(),
                'source': 'analytics_cloud.violations_kpis',
                'cached': False
            }
            self._set_cache(cache_key, response)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch violation KPIs: {e}")
            return {'kpis': [], 'error': str(e), 'cached': False}

    def get_ramp_kpis(self) -> dict[str, Any]:
        """
        Fetch ramp completion KPIs with confidence intervals (cached).

        Returns:
            Dict with ramp metrics + confidence intervals
        """
        cache_key = 'ramp_kpis'
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            sql = """
                SELECT
                    kpi_name,
                    kpi_value,
                    confidence_interval,
                    reliability,
                    computed_at
                FROM analytics_cloud.ramps_kpis
                WHERE kpi_name = 'completion_rate'
                ORDER BY computed_at DESC
                LIMIT 1
            """
            result = self.client.query(sql) if hasattr(self.client, 'query') else None

            response = {
                'completion_rate': result[0] if result else None,
                'timestamp': datetime.now().isoformat(),
                'source': 'analytics_cloud.ramps_kpis',
                'cached': False
            }
            self._set_cache(cache_key, response)
            return response
        except Exception as e:
            logger.error(f"Failed to fetch ramp KPIs: {e}")
            return {'completion_rate': None, 'error': str(e), 'cached': False}

    def get_quality_kpis(self) -> dict[str, Any]:
        """
        Fetch data quality metrics (completeness, validity, composite score).

        Returns:
            Dict with quality metrics
        """
        try:
            sql = """
                SELECT
                    kpi_name,
                    kpi_value
                FROM analytics_cloud.quality_kpis
                WHERE kpi_name IN (
                    'completeness_score',
                    'uniqueness_score',
                    'composite_quality_score'
                )
            """
            results = self.client.query(sql) if hasattr(self.client, 'query') else []

            metrics = {r[0]: r[1] for r in results} if results else {}

            return {
                'metrics': metrics,
                'timestamp': datetime.now().isoformat(),
                'source': 'analytics_cloud.quality_kpis'
            }
        except Exception as e:
            logger.error(f"Failed to fetch quality KPIs: {e}")
            return {'metrics': {}, 'error': str(e)}

    def get_spatial_coverage(self) -> dict[str, Any]:
        """
        Fetch geographic coverage and hotspot data.

        Returns:
            Dict with spatial metrics by borough
        """
        try:
            sql = """
                SELECT
                    dimensions->>'borough' AS borough,
                    SUM(kpi_value) AS records
                FROM analytics_cloud.spatial_kpis
                WHERE kpi_name = 'records_by_borough'
                GROUP BY borough
                ORDER BY records DESC
            """
            results = self.client.query(sql) if hasattr(self.client, 'query') else []

            coverage = {r[0]: r[1] for r in results} if results else {}

            return {
                'borough_distribution': coverage,
                'timestamp': datetime.now().isoformat(),
                'source': 'analytics_cloud.spatial_kpis'
            }
        except Exception as e:
            logger.error(f"Failed to fetch spatial coverage: {e}")
            return {'borough_distribution': {}, 'error': str(e)}

    def materialize_dashboard_data(self) -> dict[str, Any]:
        """
        Materialize all analytics for dashboard in single call.

        Combines all KPI categories into one dashboard data structure.

        Returns:
            Complete dashboard data dict
        """
        logger.info("Materializing dashboard analytics data...")

        return {
            'violations': self.get_violation_kpis(),
            'ramps': self.get_ramp_kpis(),
            'quality': self.get_quality_kpis(),
            'spatial': self.get_spatial_coverage(),
            'timestamp': datetime.now().isoformat(),
            'version': '1.0'
        }

    def register_dash_callbacks(self, app: Any) -> None:
        """
        Register Dash callbacks to connect analytics to visualizations.

        Args:
            app: Dash application instance
        """
        from dash import Input, Output, callback

        @callback(
            Output('violation-metrics', 'children'),
            Input('refresh-interval', 'n_intervals')
        )
        def update_violation_metrics(n):
            """Update violation KPI display."""
            data = self.get_violation_kpis()
            return f"{len(data.get('kpis', []))} violation KPIs"

        @callback(
            Output('ramp-completion', 'children'),
            Input('refresh-interval', 'n_intervals')
        )
        def update_ramp_metrics(n):
            """Update ramp completion KPI display."""
            data = self.get_ramp_kpis()
            rate = data.get('completion_rate')
            return f"Completion Rate: {rate}" if rate else "Loading..."

        @callback(
            Output('quality-score', 'children'),
            Input('refresh-interval', 'n_intervals')
        )
        def update_quality_metrics(n):
            """Update data quality score display."""
            data = self.get_quality_kpis()
            score = data.get('metrics', {}).get('composite_quality_score')
            return f"Quality: {score}/100" if score else "Loading..."

        logger.info("Dash callbacks registered for analytics")
