"""Serving views for Dash callbacks (motherduck-share-data).

Creates 6 optimized views in app_queries schema for dashboard integration:

1. app_queries.v_phase_b_results - Spatial clustering with significance
2. app_queries.v_phase_c_results - Distribution stats with concentration
3. app_queries.v_phase_d_results - Geographic anomalies
4. app_queries.v_phase_e_decomposition - Time series decomposition
5. app_queries.v_phase_f_bootstrap_ci - SLA confidence with risk level
6. app_queries.v_kpi_dashboard - 18 KPIs × 5 boroughs with categories

All views are idempotent (CREATE OR REPLACE) and include computed columns
for display in Dash without post-processing.
"""
import logging

from socrata_toolkit.motherduck.connector import MotherDuckConnection

logger = logging.getLogger(__name__)

class ServingViewsBuilder:
    """Builds serving views for Dash callbacks from analytics tables.

    Creates 6 optimized views in app_queries schema:
    - Filtered columns for dashboard display
    - Computed columns (significance, concentration_percent, risk_level, metric_category)
    - Proper ordering for Dash callbacks
    - Idempotent (CREATE OR REPLACE)

    Attributes:
        conn: MotherDuckConnection instance for executing queries
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize the serving views builder.

        Args:
            connection: MotherDuckConnection instance (MotherDuck cloud or local DuckDB)

        Example:
            conn = MotherDuckConnection(token="your_token")
            builder = ServingViewsBuilder(conn)
            builder.create_all_views()
        """
        self.conn = connection

    def create_all_views(self) -> None:
        """Create all 6 serving views in app_queries schema.

        Creates the 'app_queries' schema if it doesn't exist, then creates:
        - v_phase_b_results (5 rows)
        - v_phase_c_results (5 rows)
        - v_phase_d_results (~25 rows)
        - v_phase_e_decomposition (~450 rows)
        - v_phase_f_bootstrap_ci (5 rows)
        - v_kpi_dashboard (90 rows)

        All views are idempotent and include computed columns for display.

        Raises:
            RuntimeError: If connection is not active or view creation fails
        """
        self.conn.create_schema("app_queries")
        self._create_v_phase_b_results()
        self._create_v_phase_c_results()
        self._create_v_phase_d_results()
        self._create_v_phase_e_decomposition()
        self._create_v_phase_f_bootstrap_ci()
        self._create_v_kpi_dashboard()
        logger.info("All 6 serving views created successfully in app_queries schema")

    def _create_v_phase_b_results(self) -> None:
        """Create app_queries.v_phase_b_results view.

        Spatial clustering results with computed significance column.
        Purpose: Dash callback for Phase B chart + statistics

        Schema (5 rows - one per borough):
        - borough: MN, BK, BX, QN, SI
        - morans_i_value: Spatial clustering index
        - classification: STRONG_CLUSTERING|MODERATE_CLUSTERING|RANDOM_DISTRIBUTION|SPATIAL_DISPERSION
        - location_count: Number of locations in borough
        - p_value: Statistical significance
        - significance: COMPUTED - 'Significant' if p_value < 0.05, else 'Not Significant'
        - analytics_timestamp: When calculated
        """
        create_sql = """
        CREATE OR REPLACE VIEW app_queries.v_phase_b_results AS
        SELECT
            borough,
            morans_i_value,
            classification,
            location_count,
            p_value,
            CASE WHEN p_value < 0.05 THEN 'Significant' ELSE 'Not Significant' END AS significance,
            analytics_timestamp
        FROM analytics.phase_b_spatial_clusters
        ORDER BY borough
        """
        self.conn.execute(create_sql)
        logger.debug("Created view: app_queries.v_phase_b_results")

    def _create_v_phase_c_results(self) -> None:
        """Create app_queries.v_phase_c_results view.

        Distribution statistics with computed concentration_percent column.
        Purpose: Dash callback for Phase C histogram

        Schema (5 rows - one per borough):
        - borough: MN, BK, BX, QN, SI
        - record_count: Number of records
        - mean_val: Mean violation count
        - median_val: Median violation count
        - std_val: Standard deviation
        - skewness: Skewness coefficient
        - distribution_type: NORMAL|RIGHT_SKEWED|LEFT_SKEWED|BIMODAL
        - concentration_percent: COMPUTED - 100 * (1 - (mean - min) / (max - min))
        - analytics_timestamp: When calculated
        """
        create_sql = """
        CREATE OR REPLACE VIEW app_queries.v_phase_c_results AS
        SELECT
            borough,
            record_count,
            mean_val,
            median_val,
            std_val,
            skewness,
            distribution_type,
            ROUND(100.0 * (1.0 - (mean_val - min_val) / NULLIF(max_val - min_val, 0)), 1) AS concentration_percent,
            analytics_timestamp
        FROM analytics.phase_c_distributions
        ORDER BY borough
        """
        self.conn.execute(create_sql)
        logger.debug("Created view: app_queries.v_phase_c_results")

    def _create_v_phase_d_results(self) -> None:
        """Create app_queries.v_phase_d_results view.

        Geographic anomalies with all location data for mapping.
        Purpose: Dash callback for Phase D geographic map

        Schema (~25 rows - outliers across all boroughs):
        - location_id: Location identifier
        - borough: MN, BK, BX, QN, SI
        - latitude: Latitude coordinate
        - longitude: Longitude coordinate
        - inspection_count: Number of inspections at location
        - z_score_violations: Z-score of violation count
        - outlier_class: HIGH_OUTLIER|LOW_OUTLIER|NORMAL
        - priority_rank: ROW_NUMBER by magnitude within borough
        - analytics_timestamp: When calculated
        """
        create_sql = """
        CREATE OR REPLACE VIEW app_queries.v_phase_d_results AS
        SELECT
            location_id,
            borough,
            latitude,
            longitude,
            inspection_count,
            z_score_violations,
            outlier_class,
            priority_rank,
            analytics_timestamp
        FROM analytics.phase_d_anomalies
        ORDER BY borough, priority_rank
        """
        self.conn.execute(create_sql)
        logger.debug("Created view: app_queries.v_phase_d_results")

    def _create_v_phase_e_decomposition(self) -> None:
        """Create app_queries.v_phase_e_decomposition view.

        Time series decomposition for 4-panel visualization.
        Purpose: Dash callback for Phase E time series

        Schema (~450 rows - daily data across 5 boroughs × ~90 days):
        - date: Date of observation
        - borough: MN, BK, BX, QN, SI
        - violation_count: Daily violation count
        - trend_value: 7-day moving average
        - seasonal_value: Seasonal component
        - residual_value: Unexplained variance
        - forecast_next_period: Predicted violations for next day
        - analytics_timestamp: When calculated
        """
        create_sql = """
        CREATE OR REPLACE VIEW app_queries.v_phase_e_decomposition AS
        SELECT
            date,
            borough,
            violation_count,
            trend_value,
            seasonal_value,
            residual_value,
            forecast_next_period,
            analytics_timestamp
        FROM analytics.phase_e_decomposition
        ORDER BY date DESC, borough
        """
        self.conn.execute(create_sql)
        logger.debug("Created view: app_queries.v_phase_e_decomposition")

    def _create_v_phase_f_bootstrap_ci(self) -> None:
        """Create app_queries.v_phase_f_bootstrap_ci view.

        Bootstrap confidence intervals with computed risk_level column.
        Purpose: Dash callback for Phase F SLA gauge

        Schema (5 rows - one per borough):
        - borough: MN, BK, BX, QN, SI
        - point_estimate: Sample proportion (0-1 scale)
        - ci_lower_95: Lower 95% confidence interval
        - ci_upper_95: Upper 95% confidence interval
        - interval_width: Width of confidence interval
        - prob_meets_sla: Probability of meeting SLA (0-1 scale)
        - risk_level: COMPUTED - 'HIGH'|'MEDIUM'|'LOW'|'CRITICAL' based on prob_meets_sla
        - analytics_timestamp: When calculated
        """
        create_sql = """
        CREATE OR REPLACE VIEW app_queries.v_phase_f_bootstrap_ci AS
        SELECT
            borough,
            point_estimate,
            ci_lower_95,
            ci_upper_95,
            interval_width,
            prob_meets_sla,
            CASE
                WHEN prob_meets_sla >= 0.90 THEN 'HIGH'
                WHEN prob_meets_sla >= 0.75 THEN 'MEDIUM'
                WHEN prob_meets_sla >= 0.50 THEN 'LOW'
                ELSE 'CRITICAL'
            END AS risk_level,
            analytics_timestamp
        FROM analytics.phase_f_bootstrap_ci
        ORDER BY borough
        """
        self.conn.execute(create_sql)
        logger.debug("Created view: app_queries.v_phase_f_bootstrap_ci")

    def _create_v_kpi_dashboard(self) -> None:
        """Create app_queries.v_kpi_dashboard view.

        KPI metrics with computed metric_category column for categorization.
        Purpose: Populate all 18 KPI cards on dashboard

        Schema (90 rows - 18 KPIs × 5 boroughs):
        - kpi_name: Name of KPI metric
        - borough: MN, BK, BX, QN, SI
        - kpi_value: Calculated value
        - metric_category: COMPUTED - Category name based on kpi_name
        - analytics_timestamp: When calculated

        KPI Categories:
        - phase_b_clustering_strength, phase_b_confidence, phase_b_resource_gap (3)
        - phase_c_concentration_index, phase_c_segmentation_potential, phase_c_type_certainty, phase_c_distribution_balance (4)
        - phase_d_outlier_concentration, phase_d_adoption_rate, phase_d_priority_score (3)
        - phase_e_trend_direction, phase_e_seasonality_strength, phase_e_resource_gap, phase_e_forecast_confidence (4)
        - phase_f_sla_probability, phase_f_risk_score, phase_f_ci_coverage, phase_f_investment_justification (4)
        Total: 18 KPIs × 5 boroughs = 90 rows
        """
        create_sql = """
        CREATE OR REPLACE VIEW app_queries.v_kpi_dashboard AS
        SELECT
            kpi_name,
            borough,
            kpi_value,
            CASE
                WHEN kpi_name = 'phase_b_clustering_strength' THEN 'Clustering Score (0-100)'
                WHEN kpi_name = 'phase_b_confidence' THEN 'Confidence'
                WHEN kpi_name = 'phase_b_resource_gap' THEN 'Resource Gap'
                WHEN kpi_name = 'phase_c_concentration_index' THEN 'Concentration (%)'
                WHEN kpi_name = 'phase_c_segmentation_potential' THEN 'Segmentation'
                WHEN kpi_name = 'phase_c_type_certainty' THEN 'Type Certainty'
                WHEN kpi_name = 'phase_c_distribution_balance' THEN 'Distribution Balance'
                WHEN kpi_name = 'phase_d_outlier_concentration' THEN 'Outlier Count'
                WHEN kpi_name = 'phase_d_adoption_rate' THEN 'Adoption Rate'
                WHEN kpi_name = 'phase_d_priority_score' THEN 'Priority Score'
                WHEN kpi_name = 'phase_e_trend_direction' THEN 'Trend Direction'
                WHEN kpi_name = 'phase_e_seasonality_strength' THEN 'Seasonality'
                WHEN kpi_name = 'phase_e_resource_gap' THEN 'Resource Gap'
                WHEN kpi_name = 'phase_e_forecast_confidence' THEN 'Forecast Confidence'
                WHEN kpi_name = 'phase_f_sla_probability' THEN 'SLA Probability (%)'
                WHEN kpi_name = 'phase_f_risk_score' THEN 'Risk Score'
                WHEN kpi_name = 'phase_f_ci_coverage' THEN 'CI Coverage'
                WHEN kpi_name = 'phase_f_investment_justification' THEN 'Investment Justification'
                ELSE 'Unknown'
            END AS metric_category,
            analytics_timestamp
        FROM analytics.kpi_metrics
        ORDER BY borough, kpi_name
        """
        self.conn.execute(create_sql)
        logger.debug("Created view: app_queries.v_kpi_dashboard")
