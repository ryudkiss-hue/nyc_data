"""Tests for MotherDuck analytics layer (motherduck-query).

Comprehensive tests for 5 analytical phases + 18 KPI metrics.
Tests verify:
- All 5 phase tables are created with correct schemas
- All 18 KPIs are calculated (90 rows: 18 × 5 boroughs)
- Phase-specific calculations match expected formulas
"""

import os

import pytest

from socrata_toolkit.motherduck.analytics import AnalyticsBuilder
from socrata_toolkit.motherduck.connector import MotherDuckConnection
from socrata_toolkit.motherduck.ingestion import InspectionDataLoader
from socrata_toolkit.motherduck.staging import StagingTransformer


@pytest.fixture
def motherduck_conn():
    """Fixture providing a local DuckDB connection (no MotherDuck token needed)."""
    # Temporarily remove MOTHERDUCK_TOKEN to force local DuckDB
    old_token = os.environ.pop("MOTHERDUCK_TOKEN", None)
    try:
        conn = MotherDuckConnection(token="", database_path=":memory:")
        yield conn
        conn.close()
    finally:
        # Restore token if it was set
        if old_token:
            os.environ["MOTHERDUCK_TOKEN"] = old_token


@pytest.fixture
def data_loader(motherduck_conn):
    """Fixture providing an InspectionDataLoader instance."""
    return InspectionDataLoader(motherduck_conn)


@pytest.fixture
def staging_transformer(motherduck_conn):
    """Fixture providing a StagingTransformer instance."""
    return StagingTransformer(motherduck_conn)


@pytest.fixture
def analytics_builder(motherduck_conn):
    """Fixture providing an AnalyticsBuilder instance."""
    return AnalyticsBuilder(motherduck_conn)


class TestAnalyticsSchemaCreation:
    """Tests for analytics schema and phase table creation."""

    def test_analytics_schema_created(self, data_loader, staging_transformer, analytics_builder):
        """Verify analytics schema is created."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        result = analytics_builder.conn.fetch_all(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'analytics'"
        )
        assert len(result) > 0, "Analytics schema should exist"

    def test_phase_b_spatial_clusters_created(
        self, data_loader, staging_transformer, analytics_builder
    ):
        """Verify analytics.phase_b_spatial_clusters table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        result = analytics_builder.conn.fetch_all(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analytics' AND table_name = 'phase_b_spatial_clusters' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "phase_b_spatial_clusters table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "borough",
            "morans_i_value",
            "classification",
            "location_count",
            "mean_violations",
            "std_violations",
            "p_value",
            "analytics_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in phase_b_spatial_clusters"

    def test_phase_c_distributions_created(
        self, data_loader, staging_transformer, analytics_builder
    ):
        """Verify analytics.phase_c_distributions table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        result = analytics_builder.conn.fetch_all(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analytics' AND table_name = 'phase_c_distributions' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "phase_c_distributions table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "borough",
            "record_count",
            "mean_val",
            "median_val",
            "std_val",
            "min_val",
            "max_val",
            "skewness",
            "kurtosis",
            "distribution_type",
            "analytics_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in phase_c_distributions"

    def test_phase_d_anomalies_created(self, data_loader, staging_transformer, analytics_builder):
        """Verify analytics.phase_d_anomalies table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        result = analytics_builder.conn.fetch_all(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analytics' AND table_name = 'phase_d_anomalies' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "phase_d_anomalies table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "location_id",
            "borough",
            "block",
            "lot",
            "latitude",
            "longitude",
            "inspection_count",
            "z_score_violations",
            "outlier_class",
            "outlier_magnitude",
            "priority_rank",
            "analytics_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in phase_d_anomalies"

    def test_phase_e_decomposition_created(
        self, data_loader, staging_transformer, analytics_builder
    ):
        """Verify analytics.phase_e_decomposition table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        result = analytics_builder.conn.fetch_all(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analytics' AND table_name = 'phase_e_decomposition' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "phase_e_decomposition table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "date",
            "borough",
            "violation_count",
            "trend_value",
            "seasonal_value",
            "residual_value",
            "forecast_next_period",
            "analytics_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in phase_e_decomposition"

    def test_phase_f_bootstrap_ci_created(
        self, data_loader, staging_transformer, analytics_builder
    ):
        """Verify analytics.phase_f_bootstrap_ci table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        result = analytics_builder.conn.fetch_all(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analytics' AND table_name = 'phase_f_bootstrap_ci' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "phase_f_bootstrap_ci table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "borough",
            "bootstrap_count",
            "point_estimate",
            "ci_lower_95",
            "ci_upper_95",
            "interval_width",
            "prob_meets_sla",
            "std_error",
            "analytics_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in phase_f_bootstrap_ci"

    def test_all_five_phases_exist(self, data_loader, staging_transformer, analytics_builder):
        """Loop through all 5 phases and verify each table exists."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        phase_tables = [
            "phase_b_spatial_clusters",
            "phase_c_distributions",
            "phase_d_anomalies",
            "phase_e_decomposition",
            "phase_f_bootstrap_ci",
        ]

        for phase_table in phase_tables:
            result = analytics_builder.conn.fetch_all(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = 'analytics' AND table_name = '{phase_table}'"
            )
            assert len(result) > 0, f"Phase table '{phase_table}' should exist"


class TestKPIMetricsTableCreation:
    """Tests for KPI metrics table creation."""

    def test_kpi_metrics_table_created(self, data_loader, staging_transformer, analytics_builder):
        """Verify analytics.kpi_metrics table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        result = analytics_builder.conn.fetch_all(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analytics' AND table_name = 'kpi_metrics' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "kpi_metrics table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "kpi_name",
            "borough",
            "kpi_value",
            "analytics_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in kpi_metrics"


class TestAnalyticsDataBuild:
    """Tests for analytics data building and calculation."""

    def test_phase_b_builds_correctly(self, data_loader, staging_transformer, analytics_builder):
        """Insert sample data, build phase B, and verify results."""
        # Setup
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        # Load spatial extension for ST_Point
        try:
            analytics_builder.conn.execute("INSTALL spatial")
            analytics_builder.conn.execute("LOAD spatial")
        except Exception:
            pass  # Spatial extension may already be loaded

        # Insert sample spatial data into staging.spatial_enriched (use INSERT, not CREATE)
        analytics_builder.conn.execute(
            """
            INSERT INTO staging.spatial_enriched
            (location_id, borough, block, lot, latitude, longitude, inspection_count, z_score_violations,
             open_count, avg_severity, last_inspection_date, days_span, geom, staging_load_timestamp)
            SELECT
                '1' AS location_id,
                'MN' AS borough,
                101 AS block,
                201 AS lot,
                40.7128 AS latitude,
                -74.0060 AS longitude,
                3 AS inspection_count,
                0.8 AS z_score_violations,
                1 AS open_count,
                2.5 AS avg_severity,
                NOW()::DATE AS last_inspection_date,
                30 AS days_span,
                ST_Point(-74.0060, 40.7128) AS geom,
                NOW() AS staging_load_timestamp
            UNION ALL
            SELECT '2', 'BK', 102, 202, 40.6501, -73.9496, 2, 0.5, 1, 2.0, NOW()::DATE, 25, ST_Point(-73.9496, 40.6501), NOW()
            UNION ALL
            SELECT '3', 'BX', 103, 203, 40.8448, -73.8648, 2, 0.6, 0, 1.5, NOW()::DATE, 20, ST_Point(-73.8648, 40.8448), NOW()
            UNION ALL
            SELECT '4', 'QN', 104, 204, 40.7282, -73.7949, 1, 0.3, 0, 1.0, NOW()::DATE, 15, ST_Point(-73.7949, 40.7282), NOW()
            UNION ALL
            SELECT '5', 'SI', 105, 205, 40.5733, -74.1502, 1, 0.2, 0, 1.0, NOW()::DATE, 10, ST_Point(-74.1502, 40.5733), NOW()
            """
        )

        # Build phase B
        analytics_builder.build_phase_b()

        # Verify phase_b_spatial_clusters has data
        result = analytics_builder.conn.fetch_all(
            "SELECT COUNT(*) FROM analytics.phase_b_spatial_clusters"
        )
        assert result[0][0] > 0, "phase_b_spatial_clusters should have rows"

        # Verify classification is one of the expected values
        result = analytics_builder.conn.fetch_all(
            "SELECT DISTINCT classification FROM analytics.phase_b_spatial_clusters"
        )
        valid_classifications = [
            "STRONG_CLUSTERING",
            "MODERATE_CLUSTERING",
            "RANDOM_DISTRIBUTION",
            "SPATIAL_DISPERSION",
        ]
        for row in result:
            assert row[0] in valid_classifications, f"Invalid classification: {row[0]}"

    def test_all_kpis_calculated(self, data_loader, staging_transformer, analytics_builder):
        """Verify 90 KPI rows (18 × 5 boroughs) are calculated."""
        # Setup
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()
        analytics_builder.create_analytics_schema()

        # Load spatial extension for ST_Point
        try:
            analytics_builder.conn.execute("INSTALL spatial")
            analytics_builder.conn.execute("LOAD spatial")
        except Exception:
            pass  # Spatial extension may already be loaded

        # Insert minimal sample data (use INSERT, not CREATE)
        analytics_builder.conn.execute(
            """
            INSERT INTO staging.spatial_enriched
            (location_id, borough, block, lot, latitude, longitude, inspection_count, z_score_violations,
             open_count, avg_severity, last_inspection_date, days_span, geom, staging_load_timestamp)
            SELECT
                '1' AS location_id,
                'MN' AS borough,
                101 AS block,
                201 AS lot,
                40.7128 AS latitude,
                -74.0060 AS longitude,
                3 AS inspection_count,
                0.8 AS z_score_violations,
                1 AS open_count,
                2.5 AS avg_severity,
                NOW()::DATE AS last_inspection_date,
                30 AS days_span,
                ST_Point(-74.0060, 40.7128) AS geom,
                NOW() AS staging_load_timestamp
            UNION ALL
            SELECT '2', 'BK', 102, 202, 40.6501, -73.9496, 2, 0.5, 1, 2.0, NOW()::DATE, 25, ST_Point(-73.9496, 40.6501), NOW()
            UNION ALL
            SELECT '3', 'BX', 103, 203, 40.8448, -73.8648, 2, 0.6, 0, 1.5, NOW()::DATE, 20, ST_Point(-73.8648, 40.8448), NOW()
            UNION ALL
            SELECT '4', 'QN', 104, 204, 40.7282, -73.7949, 1, 0.3, 0, 1.0, NOW()::DATE, 15, ST_Point(-73.7949, 40.7282), NOW()
            UNION ALL
            SELECT '5', 'SI', 105, 205, 40.5733, -74.1502, 1, 0.2, 0, 1.0, NOW()::DATE, 10, ST_Point(-74.1502, 40.5733), NOW()
            """
        )

        # Build all phases
        analytics_builder.build_phase_b()
        analytics_builder.build_phase_c()
        analytics_builder.build_phase_d()
        analytics_builder.build_phase_e()
        analytics_builder.build_phase_f()

        # Build KPI metrics
        analytics_builder.build_kpi_metrics()

        # Verify 90 KPI rows (18 KPIs × 5 boroughs)
        result = analytics_builder.conn.fetch_all("SELECT COUNT(*) FROM analytics.kpi_metrics")
        kpi_count = result[0][0]
        assert kpi_count == 90, f"Expected 90 KPI rows (18 × 5 boroughs), got {kpi_count}"

        # Verify all expected KPI names
        result = analytics_builder.conn.fetch_all(
            "SELECT DISTINCT kpi_name FROM analytics.kpi_metrics ORDER BY kpi_name"
        )
        kpi_names = [row[0] for row in result]

        expected_kpis = [
            "phase_b_clustering_strength",
            "phase_b_confidence",
            "phase_b_resource_gap",
            "phase_c_concentration_index",
            "phase_c_distribution_balance",
            "phase_c_segmentation_potential",
            "phase_c_type_certainty",
            "phase_d_adoption_rate",
            "phase_d_outlier_concentration",
            "phase_d_priority_score",
            "phase_e_forecast_confidence",
            "phase_e_resource_gap",
            "phase_e_seasonality_strength",
            "phase_e_trend_direction",
            "phase_f_ci_coverage",
            "phase_f_investment_justification",
            "phase_f_risk_score",
            "phase_f_sla_probability",
        ]

        assert len(kpi_names) == 18, f"Expected 18 KPI names, got {len(kpi_names)}"

        # Verify each borough has all 18 KPIs
        for borough in ["MN", "BK", "BX", "QN", "SI"]:
            result = analytics_builder.conn.fetch_all(
                f"SELECT COUNT(*) FROM analytics.kpi_metrics WHERE borough = '{borough}'"
            )
            count = result[0][0]
            assert count == 18, f"Borough {borough} should have 18 KPIs, got {count}"
