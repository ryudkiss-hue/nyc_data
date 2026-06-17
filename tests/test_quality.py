import pytest

"""
Comprehensive Test Suite for Data Quality Framework

Tests for quality expectations, profiling, validation, SLAs, anomaly detection,
rules, reporting, and integration. Covers 45+ test cases.

Standards: pytest, comprehensive coverage, fixture-based setup
"""

import json
from datetime import datetime, timedelta, timezone

import pandas as pd

from socrata_toolkit.analysis import (
    Anomaly,
    AnomalyDetector,
    AnomalyReport,
    AnomalySeverity,
    BusinessRulesEngine,
    DataQualityCatalog,
    DataQualityTracker,
    DatasetQualityScore,
    DataType,
    DriftReport,
    Expectation,
    ExpectationSuite,
    ExpectationType,
    MetricType,
    ProfileGenerator,
    QualityReportGenerator,
    QualityRule,
    QualityValidator,
    RuleMode,
    RuleSeverity,
    RuleViolations,
    Severity,
    SeverityLevel,
    SLADefinition,
    TrendDirection,
    ValidationResult,
    ValidationResultsAggregator,
    create_311_complaints_rules,
    create_311_complaints_suite,
    create_sidewalk_inspections_suite,
    create_sidewalk_rules,
    create_standard_slas,
)

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_dataframe():
    """Create sample sidewalk inspection data."""
    return pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002", "INS003", "INS004", "INS005"],
            "location_address": [
                "123 Main St",
                "456 Broadway",
                "789 5th Ave",
                "321 Park Ave",
                "654 Madison Ave",
            ],
            "material_type": ["asphalt", "concrete", "asphalt", "concrete", "permeable"],
            "condition_rating": ["GOOD", "EXCELLENT", "FAIR", "POOR", "GOOD"],
            "inspection_date": [
                datetime(2026, 1, 1),
                datetime(2026, 1, 2),
                datetime(2026, 1, 3),
                datetime(2026, 1, 4),
                datetime(2026, 1, 5),
            ],
            "latitude": [40.7128, 40.7505, 40.7489, 40.7614, 40.7505],
            "longitude": [-74.0060, -73.9776, -73.9680, -73.9776, -73.9735],
        }
    )

@pytest.fixture
def invalid_dataframe():
    """Create invalid data with quality issues."""
    return pd.DataFrame(
        {
            "inspection_id": ["INS001", None, "INS003", "INS004", "INS005"],
            "location_address": [
                "123 Main St",
                "456 Broadway",
                None,
                "321 Park Ave",
                "654 Madison Ave",
            ],
            "material_type": ["asphalt", "invalid_material", "asphalt", "concrete", None],
            "condition_rating": ["GOOD", "EXCELLENT", "INVALID", "POOR", "GOOD"],
            "inspection_date": [
                datetime(2025, 1, 1),  # Very old
                datetime(2026, 1, 2),
                datetime(2026, 1, 3),
                datetime(2026, 1, 4),
                datetime(2026, 1, 5),
            ],
            "latitude": [40.7128, 50.0, 40.7489, 40.7614, 40.7505],  # One out of bounds
            "longitude": [-74.0060, -73.9776, -100.0, -73.9776, -73.9735],  # One out of bounds
        }
    )

@pytest.fixture
def expectation_suite():
    """Create an expectation suite for testing."""
    suite = create_sidewalk_inspections_suite()
    return suite

@pytest.fixture
def tracker():
    """Create a quality tracker."""
    tracker = DataQualityTracker()
    for sla in create_standard_slas():
        tracker.register_sla(sla)
    return tracker

# ============================================================================
# EXPECTATION TESTS (8 tests)
# ============================================================================

def test_expectation_creation():
    """Test creating a single expectation."""
    expectation = Expectation(
        expectation_type=ExpectationType.COLUMN_EXISTS,
        kwargs={"column": "test_col"},
        meta={"name": "test_column_exists"},
        severity=SeverityLevel.CRITICAL,
    )
    assert expectation.expectation_type == ExpectationType.COLUMN_EXISTS
    assert expectation.severity == SeverityLevel.CRITICAL

def test_expectation_suite_creation():
    """Test creating an expectation suite."""
    suite = ExpectationSuite(
        name="test_suite",
        description="Test suite",
        version="1.0.0",
    )
    assert suite.name == "test_suite"
    assert len(suite.expectations) == 0

def test_expectation_suite_add_expectations():
    """Test adding expectations to a suite."""
    suite = ExpectationSuite("test")
    suite.add_column_exists("col1")
    suite.add_column_not_null("col2")
    suite.add_column_values_in_set("col3", {"A", "B", "C"})
    assert len(suite.expectations) == 3

def test_expectation_suite_validate_pass(sample_dataframe, expectation_suite):
    """Test validation with passing data."""
    result = expectation_suite.validate(sample_dataframe)
    assert result.overall_status in ("PASS", "WARN")
    assert result.passed_count > 0

def test_expectation_suite_validate_fail(invalid_dataframe):
    """Test validation with invalid data."""
    suite = create_sidewalk_inspections_suite()
    result = suite.validate(invalid_dataframe)
    # Should have failures due to invalid material types
    assert result.failed_count > 0

def test_expectation_suite_to_from_dict():
    """Test serialization/deserialization of suite."""
    suite = ExpectationSuite("test")
    suite.add_column_exists("col1")

    suite_dict = suite.to_dict()
    assert suite_dict["name"] == "test"
    assert len(suite_dict["expectations"]) == 1

def test_sidewalk_expectations_suite():
    """Test sidewalk inspection expectation suite."""
    suite = create_sidewalk_inspections_suite()
    assert suite.name == "sidewalk_inspections"
    assert len(suite.expectations) > 5

def test_311_complaints_expectations_suite():
    """Test 311 complaints expectation suite."""
    suite = create_311_complaints_suite()
    assert suite.name == "311_complaints"
    assert len(suite.expectations) > 3

# ============================================================================
# PROFILER TESTS (8 tests)
# ============================================================================

def test_profiler_initialization():
    """Test profiler initialization."""
    profiler = ProfileGenerator(sample_size=5000)
    assert profiler.sample_size == 5000

def test_profile_dataset(sample_dataframe):
    """Test dataset profiling."""
    profiler = ProfileGenerator()
    profile = profiler.profile_dataset(sample_dataframe, "test_dataset")

    assert profile.table_name == "test_dataset"
    assert profile.row_count == 5
    assert profile.column_count == 7
    assert len(profile.column_profiles) == 7

def test_column_profile_numeric():
    """Test profiling of numeric column."""
    profiler = ProfileGenerator()
    numeric_series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    col_profile = profiler._profile_column(numeric_series, "test_col")

    assert col_profile.data_type == DataType.NUMERIC
    assert col_profile.min_value == 1.0
    assert col_profile.max_value == 5.0

def test_column_profile_categorical():
    """Test profiling of categorical column."""
    profiler = ProfileGenerator()
    cat_series = pd.Series(["A", "B", "A", "C", "B"])
    col_profile = profiler._profile_column(cat_series, "test_col")

    assert col_profile.data_type == DataType.STRING
    assert col_profile.cardinality == 3

def test_suggest_expectations(sample_dataframe):
    """Test suggesting expectations from profile."""
    profiler = ProfileGenerator()
    profile = profiler.profile_dataset(sample_dataframe)
    suggestions = profiler.suggest_expectations(profile)

    assert len(suggestions) > 0
    assert any(s["expectation_type"] == "column_exists" for s in suggestions)

def test_compare_profiles():
    """Test comparing two profiles for drift."""
    profiler = ProfileGenerator()
    df1 = pd.DataFrame({"col1": [1, 2, 3], "col2": ["A", "B", "C"]})
    df2 = pd.DataFrame({"col1": [1, 2, 3, 4, 5], "col2": ["A", "B", "C", "D", "E"]})

    profile1 = profiler.profile_dataset(df1, "dataset")
    profile2 = profiler.profile_dataset(df2, "dataset")

    drift_report = profiler.compare_profiles(profile1, profile2)
    assert isinstance(drift_report, DriftReport)

def test_detect_schema_drift():
    """Test detecting schema changes."""
    profiler = ProfileGenerator()
    df1 = pd.DataFrame({"col1": [1, 2], "col2": ["A", "B"]})
    df2 = pd.DataFrame({"col1": [1, 2], "col3": ["X", "Y"]})  # col2 -> col3

    profile1 = profiler.profile_dataset(df1)
    profile2 = profiler.profile_dataset(df2)

    schema_changes = profiler.detect_schema_drift(profile1, profile2)
    assert "columns_added" in schema_changes
    assert "columns_removed" in schema_changes

def test_generate_summary(sample_dataframe):
    """Test generating profile summary."""
    profiler = ProfileGenerator()
    profile = profiler.profile_dataset(sample_dataframe)
    summary = profiler.generate_summary(profile)

    assert summary["row_count"] == 5
    assert summary["column_count"] == 7

# ============================================================================
# SLA TESTS (8 tests)
# ============================================================================

def test_sla_definition_creation():
    """Test creating SLA definition."""
    sla = SLADefinition(
        metric_name="completeness",
        metric_type=MetricType.COMPLETENESS,
        target=0.99,
        window="daily",
        dataset="test_dataset",
        severity=Severity.HIGH,
        owner="test@example.com",
    )
    assert sla.metric_name == "completeness"
    assert sla.target == 0.99

def test_quality_tracker_registration(tracker):
    """Test registering SLAs in tracker."""
    assert len(tracker._slas) > 0

def test_quality_tracker_record_metric(tracker):
    """Test recording metrics."""
    tracker.record_metric(
        "sidewalk_inspections_completeness",
        0.95,
        "sidewalk_inspections",
        MetricType.COMPLETENESS,
    )
    assert len(tracker._metric_history) > 0

def test_quality_tracker_evaluate_sla(tracker):
    """Test SLA evaluation."""
    tracker.record_metric(
        "sidewalk_inspections_completeness",
        0.99,
        "sidewalk_inspections",
        MetricType.COMPLETENESS,
    )

    compliant, actual = tracker.evaluate_sla("sidewalk_inspections_completeness")
    assert isinstance(compliant, bool)
    assert actual >= 0.0

def test_quality_tracker_get_trend(tracker):
    """Test trend analysis."""
    for i in range(10):
        value = 0.90 + (i * 0.01)
        tracker.record_metric(
            "test_metric",
            value,
            "test_dataset",
            MetricType.COMPLETENESS,
        )

    trend = tracker.get_trend("test_metric")
    assert trend.direction in (
        TrendDirection.IMPROVING,
        TrendDirection.DEGRADING,
        TrendDirection.STABLE,
    )

def test_quality_tracker_breach_summary(tracker):
    """Test breach tracking."""
    tracker.record_metric(
        "sidewalk_inspections_completeness",
        0.50,  # Below target of 0.98
        "sidewalk_inspections",
        MetricType.COMPLETENESS,
    )

    summary = tracker.get_breach_summary()
    assert "active_breaches" in summary

def test_create_standard_slas():
    """Test creating standard SLAs."""
    slas = create_standard_slas()
    assert len(slas) > 0
    assert all(isinstance(sla, SLADefinition) for sla in slas)

def test_sla_compliance_report(tracker):
    """Test SLA compliance reporting."""
    for sla_name in list(tracker._slas.keys())[:2]:
        tracker.record_metric(
            sla_name,
            0.99,
            "dataset",
            MetricType.COMPLETENESS,
        )

    report = tracker.get_sla_compliance_report()
    assert "sla_results" in report
    assert "overall_compliance" in report

# ============================================================================
# VALIDATOR TESTS (8 tests)
# ============================================================================

def test_validator_initialization():
    """Test validator initialization."""
    validator = QualityValidator()
    assert not validator.fail_fast

def test_validator_validate_pass(sample_dataframe, expectation_suite):
    """Test validation with passing data."""
    validator = QualityValidator()
    result = validator.validate(sample_dataframe, expectation_suite, "test_dataset")

    assert isinstance(result, ValidationResult)
    assert result.row_count == 5
    assert result.column_count == 7

def test_validator_validate_fail(invalid_dataframe):
    """Test validation with failing data."""
    validator = QualityValidator()
    suite = create_sidewalk_inspections_suite()
    result = validator.validate(invalid_dataframe, suite, "test_dataset")

    assert len(result.failed_expectations) > 0

def test_validation_result_properties(sample_dataframe, expectation_suite):
    """Test validation result properties."""
    validator = QualityValidator()
    result = validator.validate(sample_dataframe, expectation_suite)

    assert 0 <= result.pass_rate <= 1.0
    assert result.is_critical_failure in (True, False)

def test_validator_record_validation(sample_dataframe, expectation_suite):
    """Test recording validation results."""
    validator = QualityValidator()
    aggregator = ValidationResultsAggregator()

    result = validator.validate(sample_dataframe, expectation_suite)
    aggregator.add_result(result)

    stats = aggregator.get_statistics()
    assert "total_validations" in stats

def test_aggregator_recent_failures(sample_dataframe, expectation_suite):
    """Test getting recent failures."""
    validator = QualityValidator()
    aggregator = ValidationResultsAggregator()

    for i in range(3):
        result = validator.validate(sample_dataframe, expectation_suite)
        aggregator.add_result(result)

    failures = aggregator.get_recent_failures(limit=2)
    assert len(failures) <= 2

def test_validator_fail_fast():
    """Test fail-fast validation."""
    validator = QualityValidator(fail_fast=True)
    assert validator.fail_fast

def test_validation_result_to_dict(sample_dataframe, expectation_suite):
    """Test validation result serialization."""
    validator = QualityValidator()
    result = validator.validate(sample_dataframe, expectation_suite)

    result_dict = result.to_dict()
    assert "status" in result_dict
    assert "pass_rate" in result_dict

# ============================================================================
# ANOMALY DETECTION TESTS (7 tests)
# ============================================================================

def test_anomaly_detector_initialization():
    """Test anomaly detector initialization."""
    detector = AnomalyDetector(z_score_threshold=3.0)
    assert detector.z_score_threshold == 3.0

def test_anomaly_detector_outliers():
    """Test detecting outliers."""
    detector = AnomalyDetector()
    history = [(datetime.now(timezone.utc) - timedelta(hours=i), 100.0 - i) for i in range(10)]
    history.append((datetime.now(timezone.utc), 500.0))  # Outlier

    report = detector.detect_outliers("test_metric", history)
    assert isinstance(report, AnomalyReport)

def test_anomaly_detector_drift():
    """Test detecting drift."""
    detector = AnomalyDetector()
    history = [
        (datetime.now(timezone.utc) - timedelta(hours=i), 100.0 + (i * 5)) for i in range(20)
    ]

    report = detector.detect_drift("test_metric", history)
    assert isinstance(report, AnomalyReport)

def test_anomaly_detector_seasonality():
    """Test detecting seasonality violations."""
    detector = AnomalyDetector()
    history = [(datetime.now(timezone.utc) - timedelta(hours=i), 100.0) for i in range(50)]
    history[-1] = (datetime.now(timezone.utc), 500.0)  # Violation

    report = detector.detect_seasonality_violation("test_metric", history)
    assert isinstance(report, AnomalyReport)

def test_anomaly_report_properties():
    """Test anomaly report properties."""
    anomaly = Anomaly(
        timestamp=datetime.now(timezone.utc),
        metric_name="test",
        anomaly_type="z_score",
        value=100.0,
        expected_range=(0, 50),
        severity=AnomalySeverity.HIGH,
    )

    report = AnomalyReport(detected_at=datetime.now(timezone.utc))
    report.anomalies.append(anomaly)

    assert not report.has_critical_anomalies

def test_multi_metric_anomaly_detection():
    """Test detecting anomalies across multiple metrics."""
    detector = AnomalyDetector()
    metrics = {
        "metric1": [(datetime.now(timezone.utc) - timedelta(hours=i), 100.0) for i in range(10)],
        "metric2": [(datetime.now(timezone.utc) - timedelta(hours=i), 200.0) for i in range(10)],
    }

    report = detector.detect_multi_metric_anomaly(metrics)
    assert isinstance(report, AnomalyReport)

def test_anomaly_to_dict():
    """Test anomaly serialization."""
    anomaly = Anomaly(
        timestamp=datetime.now(timezone.utc),
        metric_name="test",
        anomaly_type="z_score",
        value=100.0,
        expected_range=(0, 50),
        severity=AnomalySeverity.HIGH,
    )

    anom_dict = anomaly.to_dict()
    assert "metric_name" in anom_dict
    assert "severity" in anom_dict

# ============================================================================
# BUSINESS RULES TESTS (6 tests)
# ============================================================================

def test_business_rules_engine_registration():
    """Test registering rules in engine."""
    engine = BusinessRulesEngine()

    def test_rule(df):
        return []

    rule = QualityRule(
        rule_id="test_rule",
        rule_name="Test Rule",
        rule_func=test_rule,
    )
    engine.register_rule(rule)

    assert "test_rule" in engine.rules

def test_business_rules_evaluation():
    """Test evaluating business rules."""
    engine = BusinessRulesEngine()

    def rule_func(df):
        return df[df["value"] < 0].index.astype(str).tolist()

    rule = QualityRule(
        rule_id="positive_values",
        rule_name="Positive Values",
        rule_func=rule_func,
    )
    engine.register_rule(rule)

    df = pd.DataFrame({"value": [1, 2, -1, 3]})
    violations = engine.apply_rules(df)

    assert violations.total_violations > 0

def test_sidewalk_rules_engine():
    """Test sidewalk-specific rules."""
    engine = create_sidewalk_rules()
    assert len(engine.rules) > 0

def test_311_rules_engine():
    """Test 311 complaints rules."""
    engine = create_311_complaints_rules()
    assert len(engine.rules) > 0

def test_hard_rules_filtering():
    """Test filtering hard rules."""
    engine = BusinessRulesEngine()

    def rule_func(df):
        return []

    hard_rule = QualityRule(
        rule_id="hard",
        rule_name="Hard",
        rule_func=rule_func,
        mode=RuleMode.HARD,
    )
    soft_rule = QualityRule(
        rule_id="soft",
        rule_name="Soft",
        rule_func=rule_func,
        mode=RuleMode.SOFT,
    )

    engine.register_rule(hard_rule)
    engine.register_rule(soft_rule)

    df = pd.DataFrame({"col": [1, 2, 3]})
    violations = engine.apply_hard_rules(df)

    assert isinstance(violations, RuleViolations)

def test_rule_violations_grouping():
    """Test grouping violations by severity."""
    engine = BusinessRulesEngine()

    def rule_func(df):
        return ["row1"]

    engine.register_rule(
        QualityRule(
            rule_id="critical_rule",
            rule_name="Critical",
            rule_func=rule_func,
            severity=RuleSeverity.CRITICAL,
        )
    )

    df = pd.DataFrame({"col": [1, 2]})
    violations = engine.apply_rules(df)

    by_severity = engine.get_violations_by_severity(violations)
    assert "critical" in by_severity

# ============================================================================
# REPORTING TESTS (3 tests)
# ============================================================================

def test_report_generator_daily_report():
    """Test generating daily report."""
    generator = QualityReportGenerator()

    datasets = {
        "dataset1": {"quality_score": 0.95, "row_count": 1000},
        "dataset2": {"quality_score": 0.85, "row_count": 500},
    }
    sla_results = {"overall_compliance": 0.95}
    anomalies = []

    report = generator.generate_daily_report(datasets, sla_results, anomalies)
    assert "title" in report
    assert "summary" in report

def test_report_generator_dataset_report():
    """Test generating dataset-specific report."""
    generator = QualityReportGenerator()

    report = generator.generate_dataset_report(
        "test_dataset",
        profile={"columns": 5},
        validation_results=[],
    )
    assert report["dataset_name"] == "test_dataset"

def test_report_export_json(tmp_path):
    """Test exporting report to JSON."""
    generator = QualityReportGenerator(output_dir=tmp_path)

    report = {"title": "Test", "data": [1, 2, 3]}
    path = generator.export_to_json(report, "test_report.json")

    assert path.exists()
    with open(path) as f:
        loaded = json.load(f)
    assert loaded["title"] == "Test"

# ============================================================================
# DATA CATALOG TESTS (4 tests)
# ============================================================================

def test_quality_catalog_registration():
    """Test registering dataset in catalog."""
    catalog = DataQualityCatalog()
    catalog.register_dataset("dataset1", "Dataset 1")

    assert "dataset1" in catalog.profiles

def test_quality_catalog_update_score():
    """Test updating quality score."""
    catalog = DataQualityCatalog()
    catalog.register_dataset("dataset1", "Dataset 1")

    score = DatasetQualityScore(overall=95.0)
    catalog.update_quality_score("dataset1", score)

    profile = catalog.get_profile("dataset1")
    assert profile.quality_score.overall == 95.0

def test_quality_catalog_list_by_quality():
    """Test listing datasets by quality score."""
    catalog = DataQualityCatalog()

    catalog.register_dataset("high", "High Quality")
    catalog.register_dataset("low", "Low Quality")

    catalog.update_quality_score("high", DatasetQualityScore(overall=95.0))
    catalog.update_quality_score("low", DatasetQualityScore(overall=50.0))

    filtered = catalog.list_by_quality(min_score=90.0)
    assert len(filtered) == 1

def test_quality_catalog_health_summary():
    """Test catalog health summary."""
    catalog = DataQualityCatalog()

    catalog.register_dataset("dataset1", "Dataset 1")
    catalog.update_quality_score("dataset1", DatasetQualityScore(overall=85.0))

    summary = catalog.get_health_summary()
    assert "total_datasets" in summary
    assert summary["total_datasets"] == 1

# ============================================================================
# INTEGRATION TESTS (4 tests)
# ============================================================================

def test_end_to_end_quality_flow(sample_dataframe):
    """Test end-to-end quality validation flow."""
    # Profile
    profiler = ProfileGenerator()
    profile = profiler.profile_dataset(sample_dataframe, "test_dataset")

    # Validate
    suite = create_sidewalk_inspections_suite()
    validator = QualityValidator()
    result = validator.validate(sample_dataframe, suite)

    # Report
    generator = QualityReportGenerator()
    report = generator.generate_dataset_report(
        "test_dataset",
        profile=profile.to_dict(),
        validation_results=[result.to_dict()],
    )

    assert report["dataset_name"] == "test_dataset"
    assert len(report["validation_results"]) > 0

def test_quality_tracking_and_sla_enforcement(sample_dataframe):
    """Test quality tracking with SLA enforcement."""
    tracker = DataQualityTracker()
    sla = SLADefinition(
        metric_name="test_completeness",
        metric_type=MetricType.COMPLETENESS,
        target=0.99,
        window="daily",
        dataset="test",
        severity=Severity.CRITICAL,
        owner="test@example.com",
    )
    tracker.register_sla(sla)

    # Record metrics
    tracker.record_metric("test_completeness", 0.99, "test", MetricType.COMPLETENESS)

    # Check compliance
    compliant, _ = tracker.evaluate_sla("test_completeness")
    assert compliant

def test_quality_validation_with_rules(sample_dataframe):
    """Test validation combined with business rules."""
    engine = create_sidewalk_rules()
    df = sample_dataframe

    violations = engine.apply_hard_rules(df)
    assert isinstance(violations, RuleViolations)

def test_anomaly_detection_integration(tracker):
    """Test anomaly detection with quality metrics."""
    detector = AnomalyDetector()

    # Simulate metric history
    history = [(datetime.now(timezone.utc) - timedelta(hours=i), 100.0 - i) for i in range(20)]

    report = detector.detect_outliers("test_metric", history)
    assert isinstance(report, AnomalyReport)

# ============================================================================
# EDGE CASES AND ERROR HANDLING (4 tests)
# ============================================================================

def test_empty_dataframe_profiling():
    """Test profiling empty DataFrame."""
    profiler = ProfileGenerator()
    df = pd.DataFrame()

    profile = profiler.profile_dataset(df, "empty")
    assert profile.row_count == 0

def test_null_dataframe_validation():
    """Test validation with all-null columns."""
    df = pd.DataFrame(
        {
            "col1": [None, None, None],
            "col2": [None, None, None],
        }
    )

    suite = ExpectationSuite("test")
    suite.add_column_not_null("col1", mostly=0.0)

    validator = QualityValidator()
    result = validator.validate(df, suite)

    assert result.row_count == 3

def test_expectation_with_missing_column():
    """Test expectation when column doesn't exist."""
    df = pd.DataFrame({"col1": [1, 2, 3]})

    suite = ExpectationSuite("test")
    suite.add_column_exists("missing_col")

    result = suite.validate(df)
    assert result.failed_count > 0

def test_division_by_zero_protection():
    """Test protection against division by zero."""
    profiler = ProfileGenerator()

    # Single value series
    series = pd.Series([1])
    col_profile = profiler._profile_column(series, "col")

    # Should not raise division by zero
    assert col_profile is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# ============================================================================
# UNIT-13 ADDITIONS
# ============================================================================

# ---------------------------------------------------------------------------
# Quality scorecard (compute_quality_score from governance.core)
# ---------------------------------------------------------------------------

def _nyc_inspection_df(nrows: int = 10) -> pd.DataFrame:
    """Small realistic-looking NYC inspection DataFrame."""
    from datetime import datetime

    boroughs = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]
    rows = [
        {
            "inspection_id": f"INS-{i:04d}",
            "borough": boroughs[i % 5],
            "condition_score": 50 + (i * 3) % 50,
            "address": f"{100 + i} {'Broadway' if i % 2 == 0 else 'Atlantic Ave'}",
            "inspection_date": datetime(2025, 1, 1 + (i % 28)),
        }
        for i in range(nrows)
    ]
    return pd.DataFrame(rows)

class TestQualityScorecard:
    def test_quality_scorecard_basic(self):
        """compute_quality_score on a clean DataFrame should return total in [0,100]."""
        from socrata_toolkit.governance.core import compute_quality_score

        df = _nyc_inspection_df(nrows=20)
        score = compute_quality_score(df)
        assert 0.0 <= score.overall <= 100.0

    def test_quality_scorecard_has_dimensions(self):
        """Score object should carry completeness, validity, consistency, freshness."""
        from socrata_toolkit.governance.core import compute_quality_score

        df = _nyc_inspection_df(nrows=10)
        score = compute_quality_score(df)
        assert hasattr(score, "completeness")
        assert hasattr(score, "validity")
        assert hasattr(score, "consistency")
        assert hasattr(score, "freshness")

    def test_quality_scorecard_empty_df(self):
        """Empty DataFrame should not raise; overall should be 0 or handled gracefully."""
        from socrata_toolkit.governance.core import compute_quality_score

        empty = pd.DataFrame()
        score = compute_quality_score(empty)
        assert score.overall == 0.0 or score.overall >= 0.0

    def test_quality_scorecard_with_nulls_lower_score(self):
        """A DataFrame with many nulls should score lower than a clean one."""
        from socrata_toolkit.governance.core import compute_quality_score

        clean = _nyc_inspection_df(nrows=20)
        dirty = clean.copy()
        dirty.loc[:10, "condition_score"] = None
        dirty.loc[:10, "borough"] = None

        score_clean = compute_quality_score(clean)
        score_dirty = compute_quality_score(dirty)
        assert score_dirty.overall <= score_clean.overall

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_validate_schema_missing_col_appears_in_errors(self):
        """Missing required column should appear in validation errors."""
        from socrata_toolkit.quality.validation import validate_required_columns

        df = pd.DataFrame({"inspection_id": [1, 2], "borough": ["M", "B"]})
        required = ["inspection_id", "borough", "condition_score"]
        report = validate_required_columns(df, required)
        assert not report.valid
        assert any("condition_score" in e for e in report.errors)

    def test_validate_schema_all_present(self):
        from socrata_toolkit.quality.validation import validate_required_columns

        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        report = validate_required_columns(df, ["a", "b", "c"])
        assert report.valid
        assert report.errors == []

# ---------------------------------------------------------------------------
# Expectations — min rows
# ---------------------------------------------------------------------------

class TestValidateExpectations:
    def test_validate_expectations_min_rows(self):
        """A DataFrame with 1 row — ExpectationSuite.validate should not raise."""
        suite = ExpectationSuite("min_rows_test")
        suite.add_column_exists("col1")

        df = pd.DataFrame({"col1": ["value"]})
        result = suite.validate(df)

        # The single column exists, so it should pass
        assert result.passed_count >= 1

    def test_validate_missing_column_is_violation(self):
        """Expecting a column that doesn't exist → failed_count >= 1."""
        suite = ExpectationSuite("min_rows_explicit")
        suite.add_column_exists("expected_col_that_is_missing")

        df = pd.DataFrame({"col1": range(1)})  # only 1 row, wrong column
        result = suite.validate(df)
        assert result.failed_count >= 1

# ---------------------------------------------------------------------------
# SLA breach forecast
# ---------------------------------------------------------------------------

class TestForecastSlaBreaches:
    def test_flag_sla_violations_returns_dataframe(self):
        """flag_sla_violations should return a DataFrame with sla columns."""
        from socrata_toolkit.quality.sla_tracking import flag_sla_violations

        df = pd.DataFrame(
            {
                "complaint_date": pd.to_datetime(
                    ["2024-01-01", "2024-01-15", "2024-02-01", "2023-06-01"]
                ),
                "inspection_date": pd.to_datetime(
                    ["2024-02-15", "2024-03-01", "2024-02-20", "2023-08-01"]
                ),
                "repair_date": pd.to_datetime(
                    ["2024-06-01", "2024-07-01", "2024-06-15", "2024-02-01"]
                ),
                "borough": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
            }
        )
        result = flag_sla_violations(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)

    def test_flag_sla_violations_columns(self):
        """Result DataFrame should include _sla_violation column."""
        from socrata_toolkit.quality.sla_tracking import SLATarget, flag_sla_violations

        df = pd.DataFrame(
            {
                "complaint_date": pd.to_datetime(["2024-01-01"]),
                "inspection_date": pd.to_datetime(["2024-04-01"]),  # > 30 days
                "repair_date": pd.to_datetime(["2024-12-01"]),
                "borough": ["MANHATTAN"],
            }
        )
        # Use SLATarget to set tight thresholds so the row above triggers a violation
        target = SLATarget(complaint_to_inspection_days=30)
        result = flag_sla_violations(df, target=target)
        # Should have at least one violation column
        assert "_sla_violation" in result.columns
        assert "_sla_violation_type" in result.columns

# ---------------------------------------------------------------------------
# Quality trend record and load
# ---------------------------------------------------------------------------

class TestQualityTrend:
    def test_record_and_load_quality_trend(self):
        """Record a metric and load trend — should appear in history."""
        tracker = DataQualityTracker()
        tracker.record_metric(
            "unit13_completeness",
            0.97,
            "unit13_dataset",
            MetricType.COMPLETENESS,
        )
        # _metric_history is a dict[str, list[MetricPoint]]
        history = tracker._metric_history
        assert "unit13_completeness" in history
        assert len(history["unit13_completeness"]) >= 1

    def test_record_multiple_metrics_trend(self):
        """Multiple records for the same key should accumulate in that key's list."""
        tracker = DataQualityTracker()
        for val in [0.90, 0.92, 0.95, 0.97]:
            tracker.record_metric(
                "unit13_trend",
                val,
                "unit13_dataset",
                MetricType.COMPLETENESS,
            )
        assert "unit13_trend" in tracker._metric_history
        assert len(tracker._metric_history["unit13_trend"]) >= 4
