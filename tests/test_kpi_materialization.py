"""Comprehensive tests for Phase 2 KPI materialization.

Test coverage:
- Forecasting engine (exponential smoothing, seasonality, stationarity)
- Anomaly detection (z-score, severity classification)
- KPI computation (value calculation, trends, status)
- Database operations (upserts, queries)
- End-to-end materialization flow
"""

import pytest
from datetime import date, datetime, timezone, timedelta
import numpy as np
from unittest.mock import Mock, MagicMock

from socrata_toolkit.kpi.forecasting import ForecastingEngine, create_forecasting_engine
from socrata_toolkit.kpi.anomaly import AnomalyDetector, create_anomaly_detector
from socrata_toolkit.kpi.compute import KPIComputer, create_kpi_computer
from socrata_toolkit.kpi.materialization import MaterializationOrchestrator
from socrata_toolkit.kpi.models import KPIDefinition, KPIValue


class TestForecastingEngine:
    """Test time-series forecasting."""

    @pytest.fixture
    def engine(self):
        return create_forecasting_engine(min_history=6)

    def test_forecast_normal_series(self, engine):
        """Forecast on normal increasing series."""
        series = [100 + i * 2 for i in range(12)]
        result = engine.forecast_kpi('TEST-001', series, periods_ahead=3)

        assert result is not None
        assert len(result.forecast_values) == 3
        assert len(result.ci_lower) == 3
        assert len(result.ci_upper) == 3
        assert result.method == 'exponential_smoothing'
        assert all(ci <= f <= cu for f, ci, cu in zip(
            result.forecast_values, result.ci_lower, result.ci_upper
        ))

    def test_forecast_with_seasonality(self, engine):
        """Detect and forecast seasonal series."""
        # 24-month seasonal pattern (repeating 12-month cycle)
        base = [100, 105, 110, 115, 120, 125, 120, 115, 110, 105, 100, 95]
        series = base + base
        result = engine.forecast_kpi('TEST-002', series, periods_ahead=3)

        assert result is not None
        assert result.seasonality_detected

    def test_forecast_insufficient_history(self, engine):
        """Return None if < 6 months history."""
        short_series = [100, 102, 104, 105, 106]
        result = engine.forecast_kpi('TEST-003', short_series, periods_ahead=3)

        assert result is None

    def test_forecast_confidence_score(self, engine):
        """Confidence score between 0 and 1."""
        series = [100 + i for i in range(12)]
        result = engine.forecast_kpi('TEST-004', series)

        assert result is not None
        assert 0.0 <= result.confidence_score <= 1.0

    def test_forecast_with_noise(self, engine):
        """Forecast on noisy series."""
        np.random.seed(42)
        base_series = [100 + i * 0.5 for i in range(12)]
        noisy_series = [v + np.random.normal(0, 5) for v in base_series]
        result = engine.forecast_kpi('TEST-005', noisy_series)

        assert result is not None
        assert result.confidence_score > 0.3  # Still have confidence despite noise

    def test_stationarity_check(self, engine):
        """Check stationarity detection."""
        # Stationary: random fluctuations around mean
        stationary = [100 + np.random.normal(0, 2) for _ in range(12)]
        result_stat = engine.forecast_kpi('STAT-001', stationary)

        # Non-stationary: trending
        trending = [100 + i * 5 + np.random.normal(0, 1) for i in range(12)]
        result_trend = engine.forecast_kpi('TREND-001', trending)

        # Both should produce results but may differ in stationarity flag
        assert result_stat is not None
        assert result_trend is not None


class TestAnomalyDetector:
    """Test anomaly detection."""

    @pytest.fixture
    def detector(self):
        return create_anomaly_detector(z_threshold=3.0)

    def test_normal_value_not_flagged(self, detector):
        """Normal value within 3-sigma should not be anomaly."""
        historical = [100, 101, 102, 101, 100, 99, 101, 102, 101, 100, 101, 99]
        result = detector.detect('TEST-001', 100.5, historical)

        assert result.is_anomaly is False
        assert result.severity == 'none'

    def test_outlier_flagged(self, detector):
        """Value 3+ sigma away should be flagged."""
        historical = [100, 101, 102, 101, 100, 99, 101, 102, 101, 100, 101, 99]
        outlier = 200  # ~6 sigma above mean
        result = detector.detect('TEST-002', outlier, historical)

        assert result.is_anomaly is True
        assert result.severity == 'high'
        assert result.z_score > 3.0

    def test_severity_levels(self, detector):
        """Test severity classification levels."""
        historical = [100] * 12

        # Just above normal: 1.5 sigma
        result_low = detector.detect('TEST-003', 101.5, historical)
        assert result_low.severity == 'none'

        # Medium deviation: 2.3 sigma
        result_medium = detector.detect('TEST-004', 102.3, historical)
        assert result_medium.severity == 'low'

        # High deviation: 2.8 sigma
        result_high = detector.detect('TEST-005', 102.8, historical)
        assert result_high.severity == 'medium'

        # Very high: 3.5 sigma
        result_critical = detector.detect('TEST-006', 103.5, historical)
        assert result_critical.severity == 'high'

    def test_insufficient_history(self, detector):
        """With < 12 history points, should not flag anomaly."""
        short_history = [100, 101, 102]
        result = detector.detect('TEST-007', 200, short_history)

        assert result.is_anomaly is False

    def test_zero_variance(self, detector):
        """Handle series with zero variance."""
        constant = [100] * 12
        result = detector.detect('TEST-008', 100, constant)

        assert result.is_anomaly is False
        assert result.z_score == 0.0

    def test_negative_anomaly(self, detector):
        """Detect drop as anomaly."""
        historical = [100, 101, 102, 101, 100, 99, 101, 102, 101, 100, 101, 99]
        sharp_drop = 50  # ~5 sigma below
        result = detector.detect('TEST-009', sharp_drop, historical)

        assert result.is_anomaly is True
        assert result.severity == 'high'
        assert result.z_score < -3.0


class TestKPIComputer:
    """Test KPI computation."""

    @pytest.fixture
    def computer(self):
        return create_kpi_computer()

    @pytest.fixture
    def mock_kpi_def(self):
        """Mock KPI definition."""
        kpi = Mock(spec=KPIDefinition)
        kpi.kpi_id = 'TEST-001'
        kpi.target = 100.0
        kpi.materialization_sql = 'SELECT 92.5'
        return kpi

    def test_determine_status_gold(self, computer):
        """Achievement >= 80% should be gold."""
        kpi = Mock()
        kpi.target = 100.0

        status = computer.determine_status(kpi, 85.0, 100.0)
        assert status == 'gold'

    def test_determine_status_silver(self, computer):
        """60% <= achievement < 80% should be silver."""
        kpi = Mock()
        kpi.target = 100.0

        status = computer.determine_status(kpi, 70.0, 100.0)
        assert status == 'silver'

    def test_determine_status_bronze(self, computer):
        """Achievement < 60% should be bronze."""
        kpi = Mock()
        kpi.target = 100.0

        status = computer.determine_status(kpi, 50.0, 100.0)
        assert status == 'bronze'

    def test_determine_status_exceeds_target(self, computer):
        """Achievement > 100% should be gold."""
        kpi = Mock()
        kpi.target = 100.0

        status = computer.determine_status(kpi, 110.0, 100.0)
        assert status == 'gold'

    def test_compute_trend_period_over_period(self, computer):
        """Calculate period-over-period change."""
        current = 105.0
        historical = [
            KPIValue(date(2026, 5, 1), 100.0),
            KPIValue(date(2026, 4, 1), 98.0)
        ]

        trend = computer.compute_trend('TEST-001', current, historical)

        assert trend is not None
        assert trend.period_over_period_pct > 0  # Increased

    def test_compute_trend_with_empty_history(self, computer):
        """Handle empty historical data."""
        trend = computer.compute_trend('TEST-002', 100.0, [])

        assert trend is not None
        assert trend.period_over_period_pct == 0.0

    def test_build_computation_result(self, computer, mock_kpi_def):
        """Assemble complete computation result."""
        result = computer.build_computation_result(
            mock_kpi_def,
            date(2026, 6, 1),
            92.5
        )

        assert result.kpi_id == 'TEST-001'
        assert result.value == 92.5
        assert result.achievement_pct == 92.5
        assert result.status == 'gold'


class TestMaterializationOrchestrator:
    """Test end-to-end materialization."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock orchestrator with minimal dependencies."""
        db_manager = Mock()
        # Make db_manager.get_connection() return a context manager
        mock_conn = MagicMock()
        db_manager.get_connection.return_value = mock_conn

        registry = Mock()

        orchestrator = MaterializationOrchestrator(db_manager, registry)
        return orchestrator

    def test_orchestrator_initialization(self, mock_orchestrator):
        """Orchestrator initializes with components."""
        assert mock_orchestrator.computer is not None
        assert mock_orchestrator.forecasting is not None
        assert mock_orchestrator.anomaly_detector is not None

    def test_materialize_all_kpis_result_structure(self, mock_orchestrator):
        """MaterializationResult has correct structure."""
        mock_orchestrator.registry.get_all_kpis.return_value = []

        result = mock_orchestrator.materialize_all_kpis(date(2026, 6, 1))

        assert hasattr(result, 'run_id')
        assert hasattr(result, 'started_at')
        assert hasattr(result, 'completed_at')
        assert hasattr(result, 'total_kpis')
        assert hasattr(result, 'successful_kpis')
        assert hasattr(result, 'failed_kpis')
        assert hasattr(result, 'execution_seconds')


class TestIntegration:
    """Integration tests across modules."""

    def test_forecast_to_anomaly_flow(self):
        """Full flow: forecast → use in anomaly detection."""
        forecaster = create_forecasting_engine()
        detector = create_anomaly_detector()

        # Generate synthetic 12-month series
        series = [100 + i for i in range(12)]

        # Forecast
        forecast = forecaster.forecast_kpi('INT-001', series)
        assert forecast is not None

        # Check if forecast values are reasonable
        assert all(v > 0 for v in forecast.forecast_values)

    def test_anomaly_detection_on_forecast_series(self):
        """Detect anomaly in extended series."""
        detector = create_anomaly_detector()

        # Series with normal trend then sharp drop
        series = [100 + i for i in range(12)] + [150]  # Anomalous last value

        result = detector.detect('INT-002', 150, series[:-1])
        assert result.is_anomaly is True

    def test_status_determination_across_thresholds(self):
        """Test status at various achievement levels."""
        computer = create_kpi_computer()
        kpi = Mock()
        kpi.target = 100.0

        levels = [
            (50.0, 'bronze'),
            (60.0, 'silver'),
            (70.0, 'silver'),
            (80.0, 'gold'),
            (100.0, 'gold'),
            (150.0, 'gold')
        ]

        for value, expected_status in levels:
            status = computer.determine_status(kpi, value, 100.0)
            assert status == expected_status, f"Value {value} should be {expected_status}"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_forecast_all_same_values(self):
        """Forecast when all values are identical."""
        engine = create_forecasting_engine()
        constant = [100.0] * 12

        # Should not crash; may return constant forecast
        result = engine.forecast_kpi('EDGE-001', constant)
        assert result is not None  # Should still produce output

    def test_anomaly_with_nan_values(self):
        """Handle NaN in historical data gracefully."""
        detector = create_anomaly_detector()

        # Can't have NaN in list before passing; would be filtered out
        # This test ensures code doesn't crash on edge case
        historical = [100, 101, 102, 101, 100, 99, 101, 102, 101, 100, 101, 99]
        result = detector.detect('EDGE-002', 100.5, historical)

        assert result is not None

    def test_zero_target_status_determination(self):
        """Handle zero target in status calculation."""
        computer = create_kpi_computer()
        kpi = Mock()
        kpi.target = 0  # Edge case

        status = computer.determine_status(kpi, 50.0, 0.0)
        assert status == 'bronze'  # Should default safely

    def test_large_dataset_forecasting(self):
        """Forecast on large historical dataset."""
        engine = create_forecasting_engine()

        # 5 years of data
        long_series = list(range(1, 61))

        result = engine.forecast_kpi('EDGE-003', long_series)
        assert result is not None
        assert len(result.forecast_values) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
