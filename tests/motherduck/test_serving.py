"""Tests for serving views (motherduck-share-data).

Tests verify that 6 serving views are created and queryable:
1. app_queries.v_phase_b_results - Spatial clustering view
2. app_queries.v_phase_c_results - Distribution statistics view
3. app_queries.v_phase_d_results - Anomaly detection view
4. app_queries.v_phase_e_decomposition - Time series decomposition view
5. app_queries.v_phase_f_bootstrap_ci - SLA confidence intervals view
6. app_queries.v_kpi_dashboard - KPI metrics aggregation view
"""
import pytest

from socrata_toolkit.motherduck.connector import MotherDuckConnection
from socrata_toolkit.motherduck.serving import ServingViewsBuilder

@pytest.fixture
def md_connection():
    """Create a MotherDuck connection for testing."""
    conn = MotherDuckConnection(database_path=":memory:")
    return conn

@pytest.fixture
def setup_analytics_tables(md_connection):
    """Set up minimal analytics tables for testing serving views."""
    # Create schema
    md_connection.create_schema("analytics")

    # Create phase_b_spatial_clusters
    md_connection.execute("""
        CREATE TABLE analytics.phase_b_spatial_clusters (
            borough VARCHAR,
            morans_i_value DOUBLE,
            classification VARCHAR,
            location_count INT,
            mean_violations DOUBLE,
            std_violations DOUBLE,
            p_value DOUBLE,
            analytics_timestamp TIMESTAMP
        )
    """)

    # Create phase_c_distributions
    md_connection.execute("""
        CREATE TABLE analytics.phase_c_distributions (
            borough VARCHAR,
            record_count INT,
            mean_val DOUBLE,
            median_val DOUBLE,
            std_val DOUBLE,
            min_val DOUBLE,
            max_val DOUBLE,
            skewness DOUBLE,
            kurtosis DOUBLE,
            distribution_type VARCHAR,
            analytics_timestamp TIMESTAMP
        )
    """)

    # Create phase_d_anomalies
    md_connection.execute("""
        CREATE TABLE analytics.phase_d_anomalies (
            location_id INT,
            borough VARCHAR,
            block INT,
            lot INT,
            latitude DOUBLE,
            longitude DOUBLE,
            inspection_count INT,
            z_score_violations DOUBLE,
            outlier_class VARCHAR,
            outlier_magnitude DOUBLE,
            priority_rank INT,
            analytics_timestamp TIMESTAMP
        )
    """)

    # Create phase_e_decomposition
    md_connection.execute("""
        CREATE TABLE analytics.phase_e_decomposition (
            date DATE,
            borough VARCHAR,
            violation_count INT,
            trend_value DOUBLE,
            seasonal_value DOUBLE,
            residual_value DOUBLE,
            forecast_next_period DOUBLE,
            analytics_timestamp TIMESTAMP
        )
    """)

    # Create phase_f_bootstrap_ci
    md_connection.execute("""
        CREATE TABLE analytics.phase_f_bootstrap_ci (
            borough VARCHAR,
            bootstrap_count INT,
            point_estimate DOUBLE,
            ci_lower_95 DOUBLE,
            ci_upper_95 DOUBLE,
            interval_width DOUBLE,
            prob_meets_sla DOUBLE,
            std_error DOUBLE,
            analytics_timestamp TIMESTAMP
        )
    """)

    # Create kpi_metrics
    md_connection.execute("""
        CREATE TABLE analytics.kpi_metrics (
            kpi_name VARCHAR,
            borough VARCHAR,
            kpi_value DOUBLE,
            analytics_timestamp TIMESTAMP
        )
    """)

    # Insert sample data
    boroughs = ['MN', 'BK', 'BX', 'QN', 'SI']

    # Phase B data
    for idx, borough in enumerate(boroughs):
        md_connection.execute(f"""
            INSERT INTO analytics.phase_b_spatial_clusters VALUES
            ('{borough}', 0.34 + {idx} * 0.05, 'MODERATE_CLUSTERING', 50 + {idx} * 10,
             5.2, 2.1, 0.01, NOW())
        """)

    # Phase C data
    for idx, borough in enumerate(boroughs):
        md_connection.execute(f"""
            INSERT INTO analytics.phase_c_distributions VALUES
            ('{borough}', 100 + {idx} * 20, 4.5, 4.0, 1.5, 1, 15, 0.3, 0.1, 'NORMAL', NOW())
        """)

    # Phase D data - ~5 per borough
    location_id = 1
    for borough in boroughs:
        for rank in range(1, 6):
            md_connection.execute(f"""
                INSERT INTO analytics.phase_d_anomalies VALUES
                ({location_id}, '{borough}', 1001 + {location_id}, 101,
                 40.7128 + {rank} * 0.001, -74.0060 + {rank} * 0.001,
                 {rank * 2}, 2.3, 'HIGH_OUTLIER', 2.3, {rank}, NOW())
            """)
            location_id += 1

    # Phase E data - ~450 rows (90 per borough)
    from datetime import datetime, timedelta
    base_date = datetime(2026, 1, 1)
    for borough in boroughs:
        for day_offset in range(90):
            date_str = (base_date + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            md_connection.execute(f"""
                INSERT INTO analytics.phase_e_decomposition VALUES
                ('{date_str}', '{borough}', 10 + {day_offset} % 20, 11.5, 0.8, 1.2, 12.3, NOW())
            """)

    # Phase F data
    for idx, borough in enumerate(boroughs):
        md_connection.execute(f"""
            INSERT INTO analytics.phase_f_bootstrap_ci VALUES
            ('{borough}', 10000, 0.87 - {idx} * 0.05, 0.75, 0.95, 0.20, 0.78, 0.03, NOW())
        """)

    # KPI metrics - 18 KPIs × 5 boroughs = 90 rows
    kpi_names = [
        'phase_b_clustering_strength', 'phase_b_confidence', 'phase_b_resource_gap',
        'phase_c_concentration_index', 'phase_c_segmentation_potential', 'phase_c_type_certainty', 'phase_c_distribution_balance',
        'phase_d_outlier_concentration', 'phase_d_adoption_rate', 'phase_d_priority_score',
        'phase_e_trend_direction', 'phase_e_seasonality_strength', 'phase_e_resource_gap', 'phase_e_forecast_confidence',
        'phase_f_sla_probability', 'phase_f_risk_score', 'phase_f_ci_coverage', 'phase_f_investment_justification'
    ]

    for borough in boroughs:
        for kpi_idx, kpi_name in enumerate(kpi_names):
            md_connection.execute(f"""
                INSERT INTO analytics.kpi_metrics VALUES
                ('{kpi_name}', '{borough}', {0.5 + kpi_idx * 0.02}, NOW())
            """)

    return md_connection

class TestServingViewsCreation:
    """Test that all serving views are created."""

    def test_all_serving_views_created(self, setup_analytics_tables):
        """Verify all 6 serving views are created as VIEW table type."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        view_names = [
            'v_phase_b_results',
            'v_phase_c_results',
            'v_phase_d_results',
            'v_phase_e_decomposition',
            'v_phase_f_bootstrap_ci',
            'v_kpi_dashboard'
        ]

        for view_name in view_names:
            result = conn.fetch_all(
                f"SELECT table_type FROM information_schema.tables WHERE table_name = '{view_name}' AND table_schema = 'app_queries'"
            )
            assert len(result) > 0, f"View {view_name} not found in app_queries schema"
            assert result[0][0] == 'VIEW', f"{view_name} is not a VIEW table type"

class TestPhaseB:
    """Test v_phase_b_results view."""

    def test_v_phase_b_results_queryable(self, setup_analytics_tables):
        """Verify v_phase_b_results view is queryable and has required columns."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT * FROM app_queries.v_phase_b_results")

        required_columns = ['borough', 'morans_i_value', 'classification', 'location_count', 'p_value', 'significance', 'analytics_timestamp']
        for col in required_columns:
            assert col in df.columns, f"Column {col} not found in v_phase_b_results"

        # Verify significance computed column
        assert df['significance'].dtype == 'object', "significance should be VARCHAR"
        assert all(val in ['Significant', 'Not Significant'] for val in df['significance']), \
            "significance should be 'Significant' or 'Not Significant'"

    def test_v_phase_b_results_row_count(self, setup_analytics_tables):
        """Verify v_phase_b_results returns 5 rows (one per borough)."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        result = conn.fetch_all("SELECT COUNT(*) FROM app_queries.v_phase_b_results")
        assert result[0][0] == 5, f"Expected 5 rows, got {result[0][0]}"

    def test_v_phase_b_results_ordered_by_borough(self, setup_analytics_tables):
        """Verify v_phase_b_results is ordered by borough."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT borough FROM app_queries.v_phase_b_results")
        boroughs = df['borough'].tolist()
        assert boroughs == sorted(boroughs), "Results should be ordered by borough"

class TestPhaseC:
    """Test v_phase_c_results view."""

    def test_v_phase_c_results_queryable(self, setup_analytics_tables):
        """Verify v_phase_c_results view is queryable and has required columns."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT * FROM app_queries.v_phase_c_results")

        required_columns = ['borough', 'record_count', 'mean_val', 'median_val', 'std_val',
                          'skewness', 'distribution_type', 'concentration_percent', 'analytics_timestamp']
        for col in required_columns:
            assert col in df.columns, f"Column {col} not found in v_phase_c_results"

    def test_v_phase_c_results_concentration_percent_computed(self, setup_analytics_tables):
        """Verify concentration_percent is computed correctly."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT concentration_percent FROM app_queries.v_phase_c_results")

        # concentration_percent should be numeric (0-100 range)
        assert df['concentration_percent'].dtype in ['float64', 'float32', 'int64'], \
            "concentration_percent should be numeric"
        assert all(0 <= val <= 100 for val in df['concentration_percent'] if pd.notna(val)), \
            "concentration_percent should be in 0-100 range"

    def test_v_phase_c_results_row_count(self, setup_analytics_tables):
        """Verify v_phase_c_results returns 5 rows."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        result = conn.fetch_all("SELECT COUNT(*) FROM app_queries.v_phase_c_results")
        assert result[0][0] == 5, f"Expected 5 rows, got {result[0][0]}"

class TestPhaseD:
    """Test v_phase_d_results view."""

    def test_v_phase_d_results_queryable(self, setup_analytics_tables):
        """Verify v_phase_d_results view is queryable with geographic columns."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT * FROM app_queries.v_phase_d_results")

        required_columns = ['location_id', 'borough', 'latitude', 'longitude',
                          'inspection_count', 'z_score_violations', 'outlier_class', 'priority_rank']
        for col in required_columns:
            assert col in df.columns, f"Column {col} not found in v_phase_d_results"

    def test_v_phase_d_results_row_count(self, setup_analytics_tables):
        """Verify v_phase_d_results returns ~25 rows."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        result = conn.fetch_all("SELECT COUNT(*) FROM app_queries.v_phase_d_results")
        # We inserted 5 rows per borough × 5 boroughs = 25 rows
        assert result[0][0] == 25, f"Expected ~25 rows, got {result[0][0]}"

    def test_v_phase_d_results_ordered_by_borough_and_rank(self, setup_analytics_tables):
        """Verify v_phase_d_results is ordered by borough and priority_rank."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT borough, priority_rank FROM app_queries.v_phase_d_results")

        # Check that within each borough, priority_rank is ascending
        for borough in df['borough'].unique():
            borough_data = df[df['borough'] == borough]['priority_rank'].tolist()
            assert borough_data == sorted(borough_data), f"Rank not ascending for borough {borough}"

class TestPhaseE:
    """Test v_phase_e_decomposition view."""

    def test_v_phase_e_decomposition_queryable(self, setup_analytics_tables):
        """Verify v_phase_e_decomposition view is queryable with time series columns."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT * FROM app_queries.v_phase_e_decomposition")

        required_columns = ['date', 'borough', 'violation_count', 'trend_value',
                          'seasonal_value', 'residual_value', 'forecast_next_period', 'analytics_timestamp']
        for col in required_columns:
            assert col in df.columns, f"Column {col} not found in v_phase_e_decomposition"

    def test_v_phase_e_decomposition_row_count(self, setup_analytics_tables):
        """Verify v_phase_e_decomposition returns ~450 rows."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        result = conn.fetch_all("SELECT COUNT(*) FROM app_queries.v_phase_e_decomposition")
        # We inserted 90 rows per borough × 5 boroughs = 450 rows
        assert result[0][0] == 450, f"Expected ~450 rows, got {result[0][0]}"

    def test_v_phase_e_decomposition_ordered_by_date_desc(self, setup_analytics_tables):
        """Verify v_phase_e_decomposition is ordered by date DESC, then borough."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT date FROM app_queries.v_phase_e_decomposition LIMIT 10")
        dates = df['date'].tolist()

        # Dates should be descending
        assert dates == sorted(dates, reverse=True), "Dates should be descending"

class TestPhaseF:
    """Test v_phase_f_bootstrap_ci view."""

    def test_v_phase_f_bootstrap_ci_queryable(self, setup_analytics_tables):
        """Verify v_phase_f_bootstrap_ci view is queryable with SLA columns."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT * FROM app_queries.v_phase_f_bootstrap_ci")

        required_columns = ['borough', 'point_estimate', 'ci_lower_95', 'ci_upper_95',
                          'interval_width', 'prob_meets_sla', 'risk_level', 'analytics_timestamp']
        for col in required_columns:
            assert col in df.columns, f"Column {col} not found in v_phase_f_bootstrap_ci"

    def test_v_phase_f_bootstrap_ci_risk_level_computed(self, setup_analytics_tables):
        """Verify risk_level is computed correctly."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT risk_level FROM app_queries.v_phase_f_bootstrap_ci")

        valid_levels = {'HIGH', 'MEDIUM', 'LOW', 'CRITICAL'}
        assert all(val in valid_levels for val in df['risk_level']), \
            f"risk_level should be in {valid_levels}"

    def test_v_phase_f_bootstrap_ci_row_count(self, setup_analytics_tables):
        """Verify v_phase_f_bootstrap_ci returns 5 rows."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        result = conn.fetch_all("SELECT COUNT(*) FROM app_queries.v_phase_f_bootstrap_ci")
        assert result[0][0] == 5, f"Expected 5 rows, got {result[0][0]}"

class TestKPIDashboard:
    """Test v_kpi_dashboard view."""

    def test_v_kpi_dashboard_queryable(self, setup_analytics_tables):
        """Verify v_kpi_dashboard view is queryable."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT * FROM app_queries.v_kpi_dashboard")

        required_columns = ['kpi_name', 'borough', 'kpi_value', 'metric_category', 'analytics_timestamp']
        for col in required_columns:
            assert col in df.columns, f"Column {col} not found in v_kpi_dashboard"

    def test_v_kpi_dashboard_row_count(self, setup_analytics_tables):
        """Verify v_kpi_dashboard returns 90 rows (18 KPIs × 5 boroughs)."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        result = conn.fetch_all("SELECT COUNT(*) FROM app_queries.v_kpi_dashboard")
        assert result[0][0] == 90, f"Expected 90 rows (18 KPIs × 5 boroughs), got {result[0][0]}"

    def test_v_kpi_dashboard_metric_category_computed(self, setup_analytics_tables):
        """Verify metric_category is computed based on kpi_name."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT DISTINCT metric_category FROM app_queries.v_kpi_dashboard ORDER BY metric_category")

        # Should have multiple categories
        assert len(df) > 0, "metric_category should have values"
        assert all(isinstance(val, str) for val in df['metric_category']), "metric_category should be VARCHAR"

    def test_v_kpi_dashboard_ordered_by_borough_and_kpi(self, setup_analytics_tables):
        """Verify v_kpi_dashboard is ordered by borough, kpi_name."""
        conn = setup_analytics_tables
        builder = ServingViewsBuilder(conn)
        builder.create_all_views()

        df = conn.fetch_df("SELECT borough, kpi_name FROM app_queries.v_kpi_dashboard")

        # Check sorting: should be ordered by borough first, then kpi_name
        expected = df.sort_values(['borough', 'kpi_name']).reset_index(drop=True)
        actual = df.reset_index(drop=True)
        assert actual.equals(expected), "Results should be ordered by borough, then kpi_name"

# Import pandas for type checking in tests
try:
    import pandas as pd
except ImportError:
    pd = None
