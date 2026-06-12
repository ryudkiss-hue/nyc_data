"""
Test suite for report generators.

Validates that all 5 report generators produce valid output with correct structure.
"""

import pytest
from app.report_generator import (
    generate_phase_b_report,
    generate_phase_c_report,
    generate_phase_d_report,
    generate_phase_e_report,
    generate_phase_f_report,
)

# ============================================================================
# PHASE B REPORTER TESTS
# ============================================================================

class TestPhaseBReporter:
    """Test Phase B (Spatial Clustering) report generation."""

    @pytest.fixture
    def valid_phase_b_data(self):
        """Provide valid Phase B data."""
        return {
            'morans_i_value': 0.342,
            'p_value': 0.0234,
            'location_count': 5823,
            'violation_count': 18234,
            'borough_list': ['Manhattan', 'Brooklyn', 'Bronx', 'Queens', 'Staten Island'],
            'concentration_pct': 65.0,
            'area_pct': 20.0,
            'time_period': '24 months',
            'dataset_name': 'Sidewalk Inspection Data',
            'geography_scope': 'New York City',
        }

    def test_phase_b_basic_generation(self, valid_phase_b_data):
        """Test Phase B report generates without error."""
        report = generate_phase_b_report(valid_phase_b_data)
        assert isinstance(report, str)
        assert len(report) > 500  # Should be 750+ words

    def test_phase_b_contains_required_sections(self, valid_phase_b_data):
        """Test Phase B report contains required narrative sections."""
        report = generate_phase_b_report(valid_phase_b_data)

        # SCR framework sections
        assert 'HOOK' in report or 'map shows where' in report
        assert 'SITUATION' in report or 'DATA LAYER' in report
        assert 'COMPLICATION' in report or 'Moran' in report
        assert 'RESOLUTION' in report or 'Resource Allocation' in report

    def test_phase_b_contains_dynamic_values(self, valid_phase_b_data):
        """Test Phase B report contains injected dynamic values."""
        report = generate_phase_b_report(valid_phase_b_data)

        # Check specific values are present
        assert '0.342' in report
        assert '5823' in report or '5,823' in report
        assert '65.0' in report or '65' in report
        assert 'MODERATE_CLUSTERING' in report or 'clustering' in report

    def test_phase_b_classification_applied(self, valid_phase_b_data):
        """Test that classification is correctly determined."""
        # Test moderate clustering (0.2 < I <= 0.5)
        data = {**valid_phase_b_data, 'morans_i_value': 0.35}
        report = generate_phase_b_report(data)
        assert 'MODERATE_CLUSTERING' in report

        # Test strong clustering (I > 0.5)
        data = {**valid_phase_b_data, 'morans_i_value': 0.75}
        report = generate_phase_b_report(data)
        assert 'STRONG_CLUSTERING' in report

    def test_phase_b_missing_required_field_raises_error(self):
        """Test that missing required field raises error."""
        incomplete_data = {
            'morans_i_value': 0.342,
            'p_value': 0.0234,
            # Missing location_count and other required fields
        }
        with pytest.raises(ValueError):
            generate_phase_b_report(incomplete_data)

# ============================================================================
# PHASE C REPORTER TESTS
# ============================================================================

class TestPhaseCReporter:
    """Test Phase C (Distribution Analysis) report generation."""

    @pytest.fixture
    def valid_phase_c_data(self):
        """Provide valid Phase C data."""
        return {
            'record_count': 450,
            'valid_count': 445,
            'validity_percentage': 98.9,
            'mean_value': 15.3,
            'median_value': 12.5,
            'std_dev': 8.7,
            'min_value': 0.0,
            'max_value': 95.5,
            'skewness': 0.75,
            'kurtosis': 4.2,
            'concentration_pct': 67.5,
            'dataset_name': 'Violation Distribution',
            'geography_scope': 'New York City',
        }

    def test_phase_c_basic_generation(self, valid_phase_c_data):
        """Test Phase C report generates without error."""
        report = generate_phase_c_report(valid_phase_c_data)
        assert isinstance(report, str)
        assert len(report) > 500

    def test_phase_c_contains_required_sections(self, valid_phase_c_data):
        """Test Phase C report contains BAB framework."""
        report = generate_phase_c_report(valid_phase_c_data)

        assert 'BEFORE' in report or 'Distribution' in report
        assert 'AFTER' in report or 'Future' in report
        assert 'BRIDGE' in report or 'Implementation' in report

    def test_phase_c_distribution_classification(self, valid_phase_c_data):
        """Test distribution type is correctly classified."""
        # Right-skewed
        data = {**valid_phase_c_data, 'skewness': 0.85}
        report = generate_phase_c_report(data)
        assert 'RIGHT_SKEWED' in report or 'right' in report.lower()

        # Normal
        data = {**valid_phase_c_data, 'skewness': 0.2}
        report = generate_phase_c_report(data)
        assert 'NORMAL' in report or 'normal' in report.lower()

    def test_phase_c_contains_dynamic_values(self, valid_phase_c_data):
        """Test Phase C report contains injected values."""
        report = generate_phase_c_report(valid_phase_c_data)

        assert '450' in report
        assert '15.3' in report or '15' in report
        assert '98.9' in report or '99' in report
        assert '67.5' in report or '67' in report

# ============================================================================
# PHASE D REPORTER TESTS
# ============================================================================

class TestPhaseDReporter:
    """Test Phase D (Anomaly Detection) report generation."""

    @pytest.fixture
    def valid_phase_d_data(self):
        """Provide valid Phase D data."""
        return {
            'location_count': 5823,
            'outlier_count': 28,
            'outlier_percentage': 0.48,
            'high_outlier_count': 18,
            'low_outlier_count': 10,
            'outlier_threshold': 2.5,
            'high_outlier_mean_z': 3.2,
            'low_outlier_mean_z': -2.8,
            'dataset_name': 'Location Violations',
            'geography_scope': 'New York City',
            'high_outliers_list': [
                {'location_id': 'LOC_001', 'violation_count': 95, 'z_score': 3.5},
                {'location_id': 'LOC_002', 'violation_count': 88, 'z_score': 3.2},
            ],
            'low_outliers_list': [
                {'location_id': 'LOC_100', 'violation_count': 0, 'z_score': -3.0},
                {'location_id': 'LOC_101', 'violation_count': 1, 'z_score': -2.8},
            ],
        }

    def test_phase_d_basic_generation(self, valid_phase_d_data):
        """Test Phase D report generates without error."""
        report = generate_phase_d_report(valid_phase_d_data)
        assert isinstance(report, str)
        assert len(report) > 500

    def test_phase_d_hero_journey_structure(self, valid_phase_d_data):
        """Test Phase D contains Hero's Journey structure."""
        report = generate_phase_d_report(valid_phase_d_data)

        # Hero's Journey acts
        assert 'CALL TO ADVENTURE' in report or 'Discovery' in report
        assert 'CROSSING THE THRESHOLD' in report or 'Investigation' in report
        assert 'ORDEAL' in report or 'Challenge' in report
        assert 'RETURN WITH ELIXIR' in report or 'Solution' in report

    def test_phase_d_contains_dynamic_values(self, valid_phase_d_data):
        """Test Phase D contains injected values."""
        report = generate_phase_d_report(valid_phase_d_data)

        assert '5823' in report or '5,823' in report
        assert '28' in report
        assert '18' in report
        assert '10' in report

# ============================================================================
# PHASE E REPORTER TESTS
# ============================================================================

class TestPhaseEReporter:
    """Test Phase E (Seasonal Decomposition) report generation."""

    @pytest.fixture
    def valid_phase_e_data(self):
        """Provide valid Phase E data."""
        return {
            'trend_slope': 0.05,
            'seasonal_amplitude_pct': 40.0,
            'forecast_accuracy': 0.85,
            'data_point_count': 450,
            'lookback_months': 24,
            'dataset_name': 'Time Series Violations',
            'geography_scope': 'New York City',
            'model_fit': 0.87,
            'forecast_ci_pct': 12.0,
        }

    def test_phase_e_basic_generation(self, valid_phase_e_data):
        """Test Phase E report generates without error."""
        report = generate_phase_e_report(valid_phase_e_data)
        assert isinstance(report, str)
        assert len(report) > 500

    def test_phase_e_problem_solution_proof_structure(self, valid_phase_e_data):
        """Test Phase E contains Problem-Solution-Proof structure."""
        report = generate_phase_e_report(valid_phase_e_data)

        assert 'PROBLEM' in report or 'Waste' in report
        assert 'SOLUTION' in report or 'Resource Allocation' in report
        assert 'PROOF' in report or 'ROI' in report or 'Validation' in report

    def test_phase_e_seasonal_content(self, valid_phase_e_data):
        """Test Phase E discusses seasons."""
        report = generate_phase_e_report(valid_phase_e_data)

        assert 'Winter' in report or 'winter' in report
        assert 'Summer' in report or 'summer' in report
        assert '40.0' in report or '40' in report  # amplitude

# ============================================================================
# PHASE F REPORTER TESTS
# ============================================================================

class TestPhaseFReporter:
    """Test Phase F (SLA Forecasting) report generation."""

    @pytest.fixture
    def valid_phase_f_data(self):
        """Provide valid Phase F data."""
        return {
            'point_estimate': 78.5,
            'sla_target': 90.0,
            'ci_lower': 72.3,
            'ci_upper': 84.7,
            'prob_meets_sla': 25.0,
            'completion_velocity': 0.5,
            'dataset_name': 'SLA Tracking',
            'geography_scope': 'New York City',
        }

    def test_phase_f_basic_generation(self, valid_phase_f_data):
        """Test Phase F report generates without error."""
        report = generate_phase_f_report(valid_phase_f_data)
        assert isinstance(report, str)
        assert len(report) > 500

    def test_phase_f_decision_consequence_action(self, valid_phase_f_data):
        """Test Phase F contains Decision-Consequence-Action structure."""
        report = generate_phase_f_report(valid_phase_f_data)

        assert 'DECISION' in report or 'STAKES' in report or 'HIGH' in report
        assert 'CONSEQUENCE' in report or 'PATH A' in report or 'PATH B' in report
        assert 'ACTION' in report or 'RECOMMENDED' in report

    def test_phase_f_risk_classification(self, valid_phase_f_data):
        """Test Phase F classifies risk correctly."""
        # High risk (25% success = 75% breach)
        data = {**valid_phase_f_data, 'prob_meets_sla': 25.0}
        report = generate_phase_f_report(data)
        assert 'HIGH' in report or 'CRITICAL' in report

        # Low risk (95% success = 5% breach)
        data = {**valid_phase_f_data, 'prob_meets_sla': 95.0}
        report = generate_phase_f_report(data)
        assert 'LOW' in report or 'OPTIONAL' in report

    def test_phase_f_contains_dynamic_values(self, valid_phase_f_data):
        """Test Phase F contains injected values."""
        report = generate_phase_f_report(valid_phase_f_data)

        assert '78.5' in report or '78' in report
        assert '90.0' in report or '90' in report
        assert '25.0' in report or '25' in report

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestReportIntegration:
    """Test all reporters work together consistently."""

    def test_all_reports_generate(self):
        """Test that all 5 reports can be generated without errors."""
        phase_b_data = {
            'morans_i_value': 0.342,
            'p_value': 0.0234,
            'location_count': 5823,
            'violation_count': 18234,
            'borough_list': ['Manhattan', 'Brooklyn'],
            'concentration_pct': 65.0,
            'area_pct': 20.0,
            'time_period': '24 months',
            'dataset_name': 'Test Dataset',
            'geography_scope': 'NYC',
        }

        phase_c_data = {
            'record_count': 450,
            'valid_count': 445,
            'validity_percentage': 98.9,
            'mean_value': 15.3,
            'median_value': 12.5,
            'std_dev': 8.7,
            'min_value': 0.0,
            'max_value': 95.5,
            'skewness': 0.75,
            'kurtosis': 4.2,
            'concentration_pct': 67.5,
            'dataset_name': 'Test Dataset',
            'geography_scope': 'NYC',
        }

        phase_d_data = {
            'location_count': 5823,
            'outlier_count': 28,
            'outlier_percentage': 0.48,
            'high_outlier_count': 18,
            'low_outlier_count': 10,
            'outlier_threshold': 2.5,
            'high_outlier_mean_z': 3.2,
            'low_outlier_mean_z': -2.8,
            'dataset_name': 'Test Dataset',
            'geography_scope': 'NYC',
            'high_outliers_list': [],
            'low_outliers_list': [],
        }

        phase_e_data = {
            'trend_slope': 0.05,
            'seasonal_amplitude_pct': 40.0,
            'forecast_accuracy': 0.85,
            'data_point_count': 450,
            'dataset_name': 'Test Dataset',
            'geography_scope': 'NYC',
        }

        phase_f_data = {
            'point_estimate': 78.5,
            'sla_target': 90.0,
            'ci_lower': 72.3,
            'ci_upper': 84.7,
            'prob_meets_sla': 25.0,
            'completion_velocity': 0.5,
            'dataset_name': 'Test Dataset',
            'geography_scope': 'NYC',
        }

        # Generate all 5 reports
        reports = [
            generate_phase_b_report(phase_b_data),
            generate_phase_c_report(phase_c_data),
            generate_phase_d_report(phase_d_data),
            generate_phase_e_report(phase_e_data),
            generate_phase_f_report(phase_f_data),
        ]

        # All should be non-empty strings
        for i, report in enumerate(reports, 1):
            assert isinstance(report, str), f"Phase {i} report is not a string"
            assert len(report) > 100, f"Phase {i} report is too short"

    def test_all_reports_no_hardcoded_test_placeholders(self):
        """Test that no test/placeholder values remain in reports."""
        phase_b_data = {
            'morans_i_value': 0.342,
            'p_value': 0.0234,
            'location_count': 5823,
            'violation_count': 18234,
            'borough_list': ['Manhattan'],
            'concentration_pct': 65.0,
            'area_pct': 20.0,
            'time_period': '24 months',
            'dataset_name': 'Test',
            'geography_scope': 'NYC',
        }

        report = generate_phase_b_report(phase_b_data)

        # Should not have remaining placeholders
        assert '{' not in report or 'http' in report  # Allow URLs with {braces}
        assert '}' not in report or 'http' in report
