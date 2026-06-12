"""Tests for quality.integration module - Pipeline integration and decorators."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd

from socrata_toolkit.quality.integration import (
    QualityFramework,
    QualityIntegration,
    QualityPipeline,
    create_quality_pipeline,
    get_quality_integration,
    run_all_quality_checks,
    set_quality_integration,
)

class TestQualityIntegrationInitialization:
    """Tests for QualityIntegration initialization."""

    def test_quality_integration_default_init(self):
        """Test QualityIntegration with default parameters."""
        integration = QualityIntegration()
        assert integration is not None
        assert integration.validator is not None
        assert integration.default_suite is None
        assert integration.tracker is not None
        assert integration.anomaly_detector is not None
        assert integration.rules_engine is not None

    def test_quality_integration_with_custom_suite(self):
        """Test QualityIntegration with custom suite."""
        mock_suite = MagicMock()
        integration = QualityIntegration(default_suite=mock_suite)
        assert integration.default_suite is mock_suite

    def test_quality_integration_with_custom_tracker(self):
        """Test QualityIntegration with custom tracker."""
        mock_tracker = MagicMock()
        integration = QualityIntegration(tracker=mock_tracker)
        assert integration.tracker is mock_tracker

    def test_quality_integration_with_custom_anomaly_detector(self):
        """Test QualityIntegration with custom anomaly detector."""
        mock_detector = MagicMock()
        integration = QualityIntegration(anomaly_detector=mock_detector)
        assert integration.anomaly_detector is mock_detector

    def test_quality_integration_with_custom_rules_engine(self):
        """Test QualityIntegration with custom rules engine."""
        mock_engine = MagicMock()
        integration = QualityIntegration(rules_engine=mock_engine)
        assert integration.rules_engine is mock_engine

    def test_quality_integration_with_all_custom_components(self):
        """Test QualityIntegration with all custom components."""
        mock_suite = MagicMock()
        mock_tracker = MagicMock()
        mock_detector = MagicMock()
        mock_engine = MagicMock()

        integration = QualityIntegration(
            default_suite=mock_suite,
            tracker=mock_tracker,
            anomaly_detector=mock_detector,
            rules_engine=mock_engine,
        )

        assert integration.default_suite is mock_suite
        assert integration.tracker is mock_tracker
        assert integration.anomaly_detector is mock_detector
        assert integration.rules_engine is mock_engine

class TestQualityFramework:
    """Tests for QualityFramework class."""

    def test_quality_framework_initialization(self):
        """Test QualityFramework initialization."""
        framework = QualityFramework()
        assert framework is not None

    def test_quality_framework_initialize(self):
        """Test initialize method."""
        framework = QualityFramework()
        framework.initialize()

    def test_quality_framework_run_quality_checks(self):
        """Test run_quality_checks method."""
        framework = QualityFramework()
        df = pd.DataFrame({"col": [1, 2, 3]})
        result = framework.run_quality_checks(df)
        assert isinstance(result, dict)

class TestQualityPipeline:
    """Tests for QualityPipeline class."""

    def test_quality_pipeline_initialization(self):
        """Test QualityPipeline initialization."""
        pipeline = QualityPipeline()
        assert pipeline is not None
        assert pipeline._checks == []

    def test_quality_pipeline_add_check(self):
        """Test add_check method."""
        pipeline = QualityPipeline()

        def dummy_check(data):
            return True

        pipeline.add_check("check1", dummy_check)
        assert len(pipeline._checks) == 1

    def test_quality_pipeline_execute(self):
        """Test execute method."""
        pipeline = QualityPipeline()

        def dummy_check(data):
            return True

        pipeline.add_check("check1", dummy_check)
        df = pd.DataFrame({"col": [1, 2, 3]})
        result = pipeline.execute(df)
        assert isinstance(result, dict)

class TestCreateQualityPipeline:
    """Tests for create_quality_pipeline function."""

    def test_create_quality_pipeline_returns_instance(self):
        """Test create_quality_pipeline returns QualityPipeline."""
        pipeline = create_quality_pipeline()
        assert isinstance(pipeline, QualityPipeline)

class TestRunAllQualityChecks:
    """Tests for run_all_quality_checks function."""

    def test_run_all_quality_checks_with_data(self):
        """Test run_all_quality_checks with data."""
        df = pd.DataFrame({"col": [1, 2, 3]})
        result = run_all_quality_checks(df)
        assert isinstance(result, dict)

class TestGlobalIntegrationManagement:
    """Tests for global integration management functions."""

    def test_get_quality_integration_creates_instance(self):
        """Test get_quality_integration creates instance."""
        import socrata_toolkit.quality.integration as integration_module
        integration_module._global_integration = None

        integration = get_quality_integration()
        assert isinstance(integration, QualityIntegration)

    def test_set_quality_integration(self):
        """Test set_quality_integration."""
        custom_integration = QualityIntegration()
        set_quality_integration(custom_integration)
        retrieved = get_quality_integration()
        assert retrieved is custom_integration
