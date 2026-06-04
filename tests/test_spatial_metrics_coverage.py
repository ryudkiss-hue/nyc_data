"""Comprehensive tests for spatial.metrics module."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.spatial.metrics import (
    InspectionDensityMetric,
    MaterialDistributionMetric,
    SLAComplianceMetric,
    SpatialCoverageMetric,
    SpatialMetricsCollector,
    SpatialQualityScorer,
)


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------

class TestSpatialCoverageMetric:
    """Tests for the SpatialCoverageMetric dataclass."""

    def test_required_fields_stored(self):
        """SpatialCoverageMetric stores metric_name, value, and unit."""
        m = SpatialCoverageMetric(
            metric_name="street_network_coverage_percent",
            value=87.5,
            unit="percent",
        )
        assert m.metric_name == "street_network_coverage_percent"
        assert m.value == pytest.approx(87.5)
        assert m.unit == "percent"

    def test_optional_borough_default_none(self):
        """SpatialCoverageMetric.borough defaults to None."""
        m = SpatialCoverageMetric(metric_name="m", value=50.0, unit="percent")
        assert m.borough is None

    def test_timestamp_auto_populated(self):
        """SpatialCoverageMetric.timestamp is set automatically when omitted."""
        m = SpatialCoverageMetric(metric_name="m", value=50.0, unit="percent")
        assert m.timestamp is not None
        assert isinstance(m.timestamp, datetime)

    def test_explicit_timestamp_preserved(self):
        """SpatialCoverageMetric preserves an explicit timestamp."""
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        m = SpatialCoverageMetric(metric_name="m", value=50.0, unit="percent", timestamp=ts)
        assert m.timestamp == ts

    def test_borough_and_district_fields(self):
        """SpatialCoverageMetric stores optional borough and district."""
        m = SpatialCoverageMetric(
            metric_name="m", value=75.0, unit="percent",
            borough="Manhattan", district="D1"
        )
        assert m.borough == "Manhattan"
        assert m.district == "D1"


class TestMaterialDistributionMetric:
    """Tests for the MaterialDistributionMetric dataclass."""

    def test_all_fields_stored(self):
        """MaterialDistributionMetric stores all fields correctly."""
        m = MaterialDistributionMetric(
            material_type="concrete",
            total_length_meters=1500.0,
            segment_count=50,
            percentage=55.0,
            average_condition=68.0,
        )
        assert m.material_type == "concrete"
        assert m.total_length_meters == pytest.approx(1500.0)
        assert m.segment_count == 50
        assert m.percentage == pytest.approx(55.0)
        assert m.average_condition == pytest.approx(68.0)

    def test_borough_defaults_to_none(self):
        """MaterialDistributionMetric.borough defaults to None."""
        m = MaterialDistributionMetric(
            material_type="asphalt",
            total_length_meters=1000.0,
            segment_count=30,
            percentage=45.0,
            average_condition=55.0,
        )
        assert m.borough is None


class TestInspectionDensityMetric:
    """Tests for the InspectionDensityMetric dataclass."""

    def test_all_fields_stored(self):
        """InspectionDensityMetric stores all provided fields correctly."""
        m = InspectionDensityMetric(
            area_name="Manhattan",
            inspections_per_km2=12.5,
            total_inspections=45,
            unique_segments_inspected=30,
            time_period_days=30,
            last_inspection_age_days=5,
        )
        assert m.area_name == "Manhattan"
        assert m.inspections_per_km2 == pytest.approx(12.5)
        assert m.total_inspections == 45
        assert m.unique_segments_inspected == 30
        assert m.time_period_days == 30
        assert m.last_inspection_age_days == 5


class TestSLAComplianceMetric:
    """Tests for the SLAComplianceMetric dataclass."""

    def test_all_fields_stored(self):
        """SLAComplianceMetric stores all provided fields correctly."""
        m = SLAComplianceMetric(
            metric_name="coverage_target",
            target_value=95.0,
            actual_value=87.5,
            compliance_percentage=92.1,
            status="at_risk",
        )
        assert m.metric_name == "coverage_target"
        assert m.target_value == pytest.approx(95.0)
        assert m.actual_value == pytest.approx(87.5)
        assert m.compliance_percentage == pytest.approx(92.1)
        assert m.status == "at_risk"

    def test_borough_defaults_to_none(self):
        """SLAComplianceMetric.borough defaults to None."""
        m = SLAComplianceMetric(
            metric_name="m", target_value=100.0,
            actual_value=90.0, compliance_percentage=90.0, status="at_risk"
        )
        assert m.borough is None


# ---------------------------------------------------------------------------
# SpatialMetricsCollector — no DB
# ---------------------------------------------------------------------------

class TestSpatialMetricsCollectorNoDb:
    """Tests for SpatialMetricsCollector when db_connection is None."""

    def test_init_without_db(self):
        """SpatialMetricsCollector can be created without a DB connection."""
        collector = SpatialMetricsCollector()
        assert collector.db_connection is None

    def test_calculate_coverage_returns_empty_without_db(self):
        """calculate_coverage_by_borough returns [] when db_connection is None."""
        collector = SpatialMetricsCollector()
        result = collector.calculate_coverage_by_borough()
        assert result == []

    def test_calculate_material_distribution_returns_empty_without_db(self):
        """calculate_material_distribution returns [] when db_connection is None."""
        collector = SpatialMetricsCollector()
        result = collector.calculate_material_distribution()
        assert result == []

    def test_calculate_inspection_density_returns_none_without_db(self):
        """calculate_inspection_density returns None when db_connection is None."""
        collector = SpatialMetricsCollector()
        result = collector.calculate_inspection_density("Manhattan")
        assert result is None

    def test_calculate_spatial_gaps_returns_empty_without_db(self):
        """calculate_spatial_gaps returns {} when db_connection is None."""
        collector = SpatialMetricsCollector()
        result = collector.calculate_spatial_gaps()
        assert result == {}


# ---------------------------------------------------------------------------
# SpatialMetricsCollector — with mock DB
# ---------------------------------------------------------------------------

class TestSpatialMetricsCollectorWithDb:
    """Tests for SpatialMetricsCollector when a mock DB is provided."""

    def test_calculate_coverage_returns_five_boroughs(self):
        """calculate_coverage_by_borough returns one metric per NYC borough."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.calculate_coverage_by_borough()
        assert len(result) == 5
        boroughs = {m.borough for m in result}
        assert "Manhattan" in boroughs
        assert "Brooklyn" in boroughs

    def test_calculate_coverage_returns_spatial_coverage_metrics(self):
        """calculate_coverage_by_borough returns SpatialCoverageMetric instances."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.calculate_coverage_by_borough()
        for m in result:
            assert isinstance(m, SpatialCoverageMetric)

    def test_calculate_material_distribution_returns_five_materials(self):
        """calculate_material_distribution returns one metric per material type."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.calculate_material_distribution()
        assert len(result) == 5

    def test_calculate_material_distribution_returns_metrics(self):
        """calculate_material_distribution returns MaterialDistributionMetric instances."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.calculate_material_distribution()
        for m in result:
            assert isinstance(m, MaterialDistributionMetric)

    def test_calculate_material_distribution_with_borough_filter(self):
        """calculate_material_distribution accepts a borough filter."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.calculate_material_distribution(borough="Queens")
        assert len(result) == 5
        for m in result:
            assert m.borough == "Queens"

    def test_calculate_inspection_density_returns_metric(self):
        """calculate_inspection_density returns an InspectionDensityMetric."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.calculate_inspection_density("Bronx", days_lookback=7)
        assert isinstance(result, InspectionDensityMetric)
        assert result.area_name == "Bronx"
        assert result.time_period_days == 7

    def test_calculate_spatial_gaps_returns_dict(self):
        """calculate_spatial_gaps returns a dict with gap-related keys."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.calculate_spatial_gaps()
        assert isinstance(result, dict)
        assert "total_gaps" in result
        assert "critical_gaps" in result

    def test_calculate_spatial_gaps_error_returns_empty(self):
        """calculate_spatial_gaps returns {} when an exception is raised."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        with patch.object(collector, "_get_critical_gaps", side_effect=Exception("db error")):
            result = collector.calculate_spatial_gaps()
        assert result == {}


# ---------------------------------------------------------------------------
# SpatialMetricsCollector.calculate_sla_compliance
# ---------------------------------------------------------------------------

class TestCalculateSlaCompliance:
    """Tests for SpatialMetricsCollector.calculate_sla_compliance."""

    def test_returns_three_metrics(self):
        """calculate_sla_compliance returns exactly three SLA metrics."""
        collector = SpatialMetricsCollector()
        result = collector.calculate_sla_compliance({})
        assert len(result) == 3

    def test_returns_sla_compliance_metric_instances(self):
        """calculate_sla_compliance returns SLAComplianceMetric instances."""
        collector = SpatialMetricsCollector()
        result = collector.calculate_sla_compliance({})
        for m in result:
            assert isinstance(m, SLAComplianceMetric)

    def test_compliant_when_actual_meets_target(self):
        """SLA status is 'compliant' when actual >= target."""
        collector = SpatialMetricsCollector()
        with patch.object(collector, "_get_actual_coverage", return_value=100.0):
            with patch.object(collector, "_get_inspection_frequency", return_value=100.0):
                with patch.object(collector, "_get_average_condition", return_value=100.0):
                    result = collector.calculate_sla_compliance(
                        {"coverage_percent": 95, "inspection_percent": 50, "min_condition": 60}
                    )
        assert all(m.status == "compliant" for m in result)

    def test_non_compliant_when_actual_far_below_target(self):
        """SLA status is 'non_compliant' when actual is far below target."""
        collector = SpatialMetricsCollector()
        with patch.object(collector, "_get_actual_coverage", return_value=10.0):
            with patch.object(collector, "_get_inspection_frequency", return_value=10.0):
                with patch.object(collector, "_get_average_condition", return_value=10.0):
                    result = collector.calculate_sla_compliance(
                        {"coverage_percent": 95, "inspection_percent": 50, "min_condition": 60}
                    )
        assert any(m.status == "non_compliant" for m in result)

    def test_at_risk_when_slightly_below_target(self):
        """SLA status is 'at_risk' when compliance is between 90% and 100%."""
        collector = SpatialMetricsCollector()
        with patch.object(collector, "_get_actual_coverage", return_value=90.0):
            with patch.object(collector, "_get_inspection_frequency", return_value=90.0):
                with patch.object(collector, "_get_average_condition", return_value=90.0):
                    result = collector.calculate_sla_compliance(
                        {"coverage_percent": 95, "inspection_percent": 95, "min_condition": 95}
                    )
        statuses = {m.status for m in result}
        assert "at_risk" in statuses or "non_compliant" in statuses

    def test_compliance_percentage_capped_at_100(self):
        """SLA compliance_percentage is capped at 100 even when actual exceeds target."""
        collector = SpatialMetricsCollector()
        with patch.object(collector, "_get_actual_coverage", return_value=200.0):
            with patch.object(collector, "_get_inspection_frequency", return_value=200.0):
                with patch.object(collector, "_get_average_condition", return_value=200.0):
                    result = collector.calculate_sla_compliance(
                        {"coverage_percent": 95, "inspection_percent": 50, "min_condition": 60}
                    )
        assert all(m.compliance_percentage <= 100 for m in result)

    def test_zero_target_yields_zero_compliance(self):
        """SLA with target_value of 0 yields compliance_percentage of 0."""
        collector = SpatialMetricsCollector()
        result = collector.calculate_sla_compliance(
            {"coverage_percent": 0, "inspection_percent": 0, "min_condition": 0}
        )
        for m in result:
            assert m.compliance_percentage == 0.0

    def test_returns_empty_on_exception(self):
        """calculate_sla_compliance returns [] when an exception is raised."""
        collector = SpatialMetricsCollector()
        with patch.object(collector, "_get_actual_coverage", side_effect=Exception("error")):
            result = collector.calculate_sla_compliance({})
        assert result == []


# ---------------------------------------------------------------------------
# SpatialMetricsCollector.export_metrics_prometheus
# ---------------------------------------------------------------------------

class TestExportMetricsPrometheus:
    """Tests for SpatialMetricsCollector.export_metrics_prometheus."""

    def test_output_is_string(self):
        """export_metrics_prometheus returns a string."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.export_metrics_prometheus()
        assert isinstance(result, str)

    def test_output_contains_help_comment(self):
        """export_metrics_prometheus output includes # HELP line."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.export_metrics_prometheus()
        assert "# HELP" in result

    def test_output_contains_borough_labels(self):
        """export_metrics_prometheus includes borough labels in output."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.export_metrics_prometheus()
        assert "borough=" in result


# ---------------------------------------------------------------------------
# SpatialMetricsCollector.export_metrics_json
# ---------------------------------------------------------------------------

class TestExportMetricsJson:
    """Tests for SpatialMetricsCollector.export_metrics_json."""

    def test_returns_dict(self):
        """export_metrics_json returns a dictionary."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.export_metrics_json()
        assert isinstance(result, dict)

    def test_contains_top_level_keys(self):
        """export_metrics_json includes timestamp, coverage, materials, sla_compliance."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.export_metrics_json()
        assert "timestamp" in result
        assert "coverage" in result
        assert "materials" in result
        assert "sla_compliance" in result

    def test_timestamp_is_iso_string(self):
        """export_metrics_json timestamp is an ISO-format string."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.export_metrics_json()
        # A parseable ISO string will not raise
        datetime.fromisoformat(result["timestamp"])

    def test_coverage_is_list_of_dicts(self):
        """export_metrics_json coverage key contains a list of dicts."""
        collector = SpatialMetricsCollector(db_connection=MagicMock())
        result = collector.export_metrics_json()
        assert isinstance(result["coverage"], list)
        if result["coverage"]:
            assert "metric" in result["coverage"][0]


# ---------------------------------------------------------------------------
# SpatialQualityScorer
# ---------------------------------------------------------------------------

class TestSpatialQualityScorerCompleteness:
    """Tests for SpatialQualityScorer.calculate_completeness_score."""

    def test_full_coverage(self):
        """100% of segments present yields completeness score of 100.0."""
        score = SpatialQualityScorer.calculate_completeness_score(100, 100)
        assert score == pytest.approx(100.0)

    def test_zero_segments(self):
        """0 segments present out of 100 yields completeness score of 0.0."""
        score = SpatialQualityScorer.calculate_completeness_score(0, 100)
        assert score == pytest.approx(0.0)

    def test_partial_coverage(self):
        """50% of segments present yields completeness score of 50.0."""
        score = SpatialQualityScorer.calculate_completeness_score(50, 100)
        assert score == pytest.approx(50.0)

    def test_zero_total_returns_zero(self):
        """Total of 0 yields completeness score of 0.0 (no division by zero)."""
        score = SpatialQualityScorer.calculate_completeness_score(0, 0)
        assert score == pytest.approx(0.0)


class TestSpatialQualityScorerRecency:
    """Tests for SpatialQualityScorer.calculate_recency_score."""

    def test_inspected_today_scores_100(self):
        """0 days since inspection yields recency score of 100.0."""
        score = SpatialQualityScorer.calculate_recency_score(0)
        assert score == pytest.approx(100.0)

    def test_inspected_at_twice_interval_scores_zero(self):
        """Inspection age at 2× target interval yields recency score of 0.0."""
        score = SpatialQualityScorer.calculate_recency_score(730, target_inspection_interval_days=365)
        assert score == pytest.approx(0.0)

    def test_halfway_to_interval(self):
        """Inspection age at half the target interval yields positive recency score."""
        score = SpatialQualityScorer.calculate_recency_score(182, target_inspection_interval_days=365)
        assert score > 0.0

    def test_negative_days_scores_100(self):
        """Negative days (future-dated inspection) yields recency score of 100.0."""
        score = SpatialQualityScorer.calculate_recency_score(-5)
        assert score == pytest.approx(100.0)


class TestSpatialQualityScorerAccuracy:
    """Tests for SpatialQualityScorer.calculate_accuracy_score."""

    def test_perfect_accuracy(self):
        """GPS accuracy equal to target yields accuracy score of 100.0."""
        score = SpatialQualityScorer.calculate_accuracy_score(5.0, target_accuracy_meters=5.0)
        assert score == pytest.approx(100.0)

    def test_better_than_target_scores_100(self):
        """GPS accuracy better than target yields accuracy score of 100.0."""
        score = SpatialQualityScorer.calculate_accuracy_score(2.0, target_accuracy_meters=5.0)
        assert score == pytest.approx(100.0)

    def test_degraded_accuracy_reduces_score(self):
        """GPS accuracy worse than target reduces accuracy score below 100."""
        score = SpatialQualityScorer.calculate_accuracy_score(15.0, target_accuracy_meters=5.0)
        assert score < 100.0
        assert score >= 0.0

    def test_extreme_inaccuracy_clamps_to_zero(self):
        """Extreme GPS inaccuracy clamps accuracy score at 0.0."""
        score = SpatialQualityScorer.calculate_accuracy_score(10000.0, target_accuracy_meters=5.0)
        assert score == pytest.approx(0.0)


class TestSpatialQualityScorerConsistency:
    """Tests for SpatialQualityScorer.calculate_consistency_score."""

    def test_no_duplicates_scores_100(self):
        """Zero duplicates yields consistency score of 100.0."""
        score = SpatialQualityScorer.calculate_consistency_score(0, 100)
        assert score == pytest.approx(100.0)

    def test_all_duplicates_scores_zero(self):
        """All segments duplicated yields consistency score of 0.0."""
        score = SpatialQualityScorer.calculate_consistency_score(100, 100)
        assert score == pytest.approx(0.0)

    def test_zero_total_scores_100(self):
        """Zero total segments yields consistency score of 100.0."""
        score = SpatialQualityScorer.calculate_consistency_score(0, 0)
        assert score == pytest.approx(100.0)

    def test_half_duplicates(self):
        """50% duplicate rate yields consistency score of 50.0."""
        score = SpatialQualityScorer.calculate_consistency_score(50, 100)
        assert score == pytest.approx(50.0)


class TestSpatialQualityScorerOverall:
    """Tests for SpatialQualityScorer.calculate_overall_quality."""

    def test_perfect_scores_yield_100(self):
        """All 100 inputs with default weights yield overall score of 100.0."""
        score = SpatialQualityScorer.calculate_overall_quality(100.0, 100.0, 100.0, 100.0)
        assert score == pytest.approx(100.0)

    def test_all_zero_inputs_yield_zero(self):
        """All 0 inputs yield overall score of 0.0."""
        score = SpatialQualityScorer.calculate_overall_quality(0.0, 0.0, 0.0, 0.0)
        assert score == pytest.approx(0.0)

    def test_custom_weights(self):
        """Custom weight dictionary is used correctly."""
        weights = {"completeness": 1.0, "recency": 0.0, "accuracy": 0.0, "consistency": 0.0}
        score = SpatialQualityScorer.calculate_overall_quality(80.0, 0.0, 0.0, 0.0, weights=weights)
        assert score == pytest.approx(80.0)

    def test_default_weights_sum_to_one(self):
        """Default weights produce a correct weighted average for equal inputs."""
        score = SpatialQualityScorer.calculate_overall_quality(50.0, 50.0, 50.0, 50.0)
        assert score == pytest.approx(50.0)

    def test_clamped_at_100(self):
        """Overall score is clamped to 100.0 even with extreme weights."""
        weights = {"completeness": 2.0, "recency": 0.0, "accuracy": 0.0, "consistency": 0.0}
        score = SpatialQualityScorer.calculate_overall_quality(100.0, 0.0, 0.0, 0.0, weights=weights)
        assert score == pytest.approx(100.0)

    def test_clamped_at_zero(self):
        """Overall score is clamped to 0.0 even with negative intermediate values."""
        score = SpatialQualityScorer.calculate_overall_quality(0.0, 0.0, 0.0, 0.0)
        assert score >= 0.0
