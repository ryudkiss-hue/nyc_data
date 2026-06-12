"""
Test suite for hardcoded business logic module.

Validates that all hardcoded rules, classifications, and thresholds work correctly.
"""

import pytest

from app.report_generator.hardcoded_logic import (
    DISTRIBUTION_TYPES,
    MORANS_I_CLASSIFICATIONS,
    RISK_ASSESSMENT_MATRIX,
    classify_distribution,
    classify_morans_i,
    get_distribution_config,
    get_morans_i_config,
    get_outlier_config,
    get_risk_config,
    get_risk_level,
)


class TestMoransIClassification:
    """Test Moran's I classification logic."""

    def test_strong_clustering(self):
        """Test STRONG_CLUSTERING classification (I > 0.5)."""
        assert classify_morans_i(0.75) == "STRONG_CLUSTERING"
        assert classify_morans_i(0.95) == "STRONG_CLUSTERING"
        assert classify_morans_i(0.50) == "STRONG_CLUSTERING"

    def test_moderate_clustering(self):
        """Test MODERATE_CLUSTERING classification (0.2 < I ≤ 0.5)."""
        assert classify_morans_i(0.35) == "MODERATE_CLUSTERING"
        assert classify_morans_i(0.25) == "MODERATE_CLUSTERING"
        assert classify_morans_i(0.45) == "MODERATE_CLUSTERING"

    def test_random_distribution(self):
        """Test RANDOM_DISTRIBUTION classification (-0.2 ≤ I ≤ 0.2)."""
        assert classify_morans_i(0.0) == "RANDOM_DISTRIBUTION"
        assert classify_morans_i(0.1) == "RANDOM_DISTRIBUTION"
        assert classify_morans_i(-0.15) == "RANDOM_DISTRIBUTION"

    def test_spatial_dispersion(self):
        """Test SPATIAL_DISPERSION classification (I < -0.2)."""
        assert classify_morans_i(-0.5) == "SPATIAL_DISPERSION"
        assert classify_morans_i(-0.9) == "SPATIAL_DISPERSION"

    def test_boundary_cases(self):
        """Test boundary values."""
        # At boundaries
        assert classify_morans_i(0.2) in ["MODERATE_CLUSTERING", "RANDOM_DISTRIBUTION"]
        assert classify_morans_i(-0.2) in ["SPATIAL_DISPERSION", "RANDOM_DISTRIBUTION"]


class TestDistributionClassification:
    """Test distribution type classification."""

    def test_normal_distribution(self):
        """Test NORMAL classification (|skewness| < 0.5)."""
        assert classify_distribution(0.0, 3.0) == "NORMAL"
        assert classify_distribution(0.3, 3.0) == "NORMAL"
        assert classify_distribution(-0.4, 3.0) == "NORMAL"

    def test_right_skewed_distribution(self):
        """Test RIGHT_SKEWED classification (skewness > 0.5)."""
        assert classify_distribution(0.7, 3.0) == "RIGHT_SKEWED"
        assert classify_distribution(1.5, 3.0) == "RIGHT_SKEWED"

    def test_left_skewed_distribution(self):
        """Test LEFT_SKEWED classification (skewness < -0.5)."""
        assert classify_distribution(-0.7, 3.0) == "LEFT_SKEWED"
        assert classify_distribution(-1.5, 3.0) == "LEFT_SKEWED"

    def test_bimodal_distribution(self):
        """Test BIMODAL classification (bimodality_index > 0.555)."""
        assert classify_distribution(0.3, 3.0, bimodality_index=0.6) == "BIMODAL"
        assert classify_distribution(1.0, 3.0, bimodality_index=0.8) == "BIMODAL"

    def test_bimodal_overrides_skewness(self):
        """Test that bimodality detection overrides skewness."""
        # Even right-skewed, if bimodal flag is high, should be BIMODAL
        result = classify_distribution(1.0, 3.0, bimodality_index=0.6)
        assert result == "BIMODAL"


class TestRiskClassification:
    """Test risk level classification."""

    def test_critical_risk(self):
        """Test CRITICAL risk (prob_breach > 0.75)."""
        # prob_meets_sla < 0.25 means breach probability > 0.75
        assert get_risk_level(0.20) == "CRITICAL"
        assert get_risk_level(0.10) == "CRITICAL"

    def test_high_risk(self):
        """Test HIGH risk (0.50 < prob_breach ≤ 0.75)."""
        assert get_risk_level(0.35) == "HIGH"
        assert get_risk_level(0.45) == "HIGH"

    def test_medium_risk(self):
        """Test MEDIUM risk (0.25 < prob_breach ≤ 0.50)."""
        assert get_risk_level(0.60) == "MEDIUM"
        assert get_risk_level(0.70) == "MEDIUM"

    def test_low_risk(self):
        """Test LOW risk (prob_breach ≤ 0.25)."""
        assert get_risk_level(0.80) == "LOW"
        assert get_risk_level(0.95) == "LOW"


class TestConfigRetrieval:
    """Test configuration dictionary retrieval."""

    def test_morans_i_config_strong_clustering(self):
        """Test retrieval of STRONG_CLUSTERING config."""
        config = get_morans_i_config("STRONG_CLUSTERING")
        assert "range" in config
        assert "meaning" in config
        assert "action_steps" in config
        assert isinstance(config["action_steps"], list)
        assert len(config["action_steps"]) > 0

    def test_morans_i_config_all_types(self):
        """Test all Moran's I config types."""
        for classification_type in MORANS_I_CLASSIFICATIONS.keys():
            config = get_morans_i_config(classification_type)
            assert config is not None
            assert "range" in config
            assert "meaning" in config

    def test_distribution_config_all_types(self):
        """Test all distribution config types."""
        for dist_type in DISTRIBUTION_TYPES.keys():
            config = get_distribution_config(dist_type)
            assert config is not None
            assert "characteristics" in config
            assert "meaning" in config

    def test_outlier_config(self):
        """Test outlier config retrieval."""
        high_config = get_outlier_config("HIGH_OUTLIER")
        low_config = get_outlier_config("LOW_OUTLIER")

        assert high_config["meaning"] == "Anomalously high violation rates"
        assert low_config["meaning"] == "Anomalously low violation rates (best practices)"

    def test_risk_config_all_levels(self):
        """Test all risk config levels."""
        for risk_level in RISK_ASSESSMENT_MATRIX.keys():
            config = get_risk_config(risk_level)
            assert config is not None
            assert "probability_range" in config
            assert "meaning" in config


class TestConfigConsistency:
    """Test that all configurations are complete and consistent."""

    def test_morans_i_all_have_action_steps(self):
        """Test all Moran's I classifications have action steps."""
        for classification, config in MORANS_I_CLASSIFICATIONS.items():
            assert "action_steps" in config
            assert isinstance(config["action_steps"], list)
            assert len(config["action_steps"]) >= 3

    def test_distribution_types_have_test_recommendation(self):
        """Test all distribution types have test recommendations."""
        for dist_type, config in DISTRIBUTION_TYPES.items():
            assert "test_recommendation" in config

    def test_risk_matrix_has_decision(self):
        """Test all risk levels have decision guidance."""
        for risk_level, config in RISK_ASSESSMENT_MATRIX.items():
            assert "decision" in config
            assert "probability_range" in config

    def test_no_overlapping_morans_i_ranges(self):
        """Test that Moran's I classification ranges don't overlap."""
        ranges = []
        for classification, config in MORANS_I_CLASSIFICATIONS.items():
            range_min, range_max = config["range"]
            ranges.append((range_min, range_max, classification))

        # Sort by minimum
        ranges.sort(key=lambda x: x[0])

        # Check no overlaps (each max should be <= next min)
        for i in range(len(ranges) - 1):
            current_max = ranges[i][1]
            next_min = ranges[i + 1][0]
            assert current_max <= next_min, f"Overlap: {ranges[i]} vs {ranges[i + 1]}"

    def test_risk_matrix_probability_ranges_complete(self):
        """Test that risk matrix covers 0-1 probability range."""
        all_ranges = []
        for risk_level, config in RISK_ASSESSMENT_MATRIX.items():
            prob_min, prob_max = config["probability_range"]
            all_ranges.append((prob_min, prob_max))

        # Sort
        all_ranges.sort()

        # Should cover 0.0 to 1.0
        assert all_ranges[0][0] == 0.0
        assert all_ranges[-1][1] == 1.0
