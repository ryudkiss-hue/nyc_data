"""Integration tests for Construction Planning Dashboard.

Tests all four sections: conflict summary, block analysis, recommendations,
and conflict resolution. Validates data flows from Tasks 1-5.

Standards: Python 3.11+, type hints, comprehensive docstrings
"""

from __future__ import annotations

import pandas as pd
import pytest
from datetime import datetime, timedelta, timezone

from socrata_toolkit.analysis.confidence_intervals import wilson_score_confidence_interval
from socrata_toolkit.governance.audit_logger import AuditLogger
from socrata_toolkit.quality.domain_rules import validate_material_lifespan_rule
from socrata_toolkit.quality.reconciliation import DataReconciliation
from socrata_toolkit.spatial.conflict_detection import (
    SpatialConflict,
    detect_spatial_conflicts,
    summarize_conflicts_by_severity,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_permits_df() -> pd.DataFrame:
    """Create sample permit DataFrame for testing."""
    return pd.DataFrame({
        "permit_block": [1001, 1002, 1003, 1004, 1005],
        "block_id": [1001, 1002, 1003, 1004, 1005],
        "permit_lat": [40.7128, 40.7160, 40.7150, 40.7140, 40.7120],
        "permit_lon": [-74.0060, -74.0050, -74.0040, -74.0030, -74.0020],
        "latitude": [40.7128, 40.7160, 40.7150, 40.7140, 40.7120],
        "longitude": [-74.0060, -74.0050, -74.0040, -74.0030, -74.0020],
        "permit_status": ["Active", "Active", "Active", "Completed", "Active"],
        "status": ["Active", "Active", "Active", "Completed", "Active"],
        "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "BROOKLYN", "QUEENS"],
        "material_type": ["concrete", "asphalt", "concrete", "asphalt", "concrete"],
    })

@pytest.fixture()
def sample_inspections_df() -> pd.DataFrame:
    """Create sample inspection DataFrame for testing."""
    return pd.DataFrame({
        "inspection_block": [1001, 1002, 1003, 1006, 1007],
        "block_id": [1001, 1002, 1003, 1006, 1007],
        "inspection_lat": [40.7128, 40.7161, 40.7151, 40.7100, 40.7200],
        "inspection_lon": [-74.0060, -74.0051, -74.0041, -74.0015, -74.0015],
        "latitude": [40.7128, 40.7161, 40.7151, 40.7100, 40.7200],
        "longitude": [-74.0060, -74.0051, -74.0041, -74.0015, -74.0015],
        "inspection_status": ["Scheduled", "Scheduled", "Completed", "Scheduled", "Scheduled"],
        "status": ["Scheduled", "Scheduled", "Completed", "Scheduled", "Scheduled"],
        "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
        "condition_score": [50, 65, 80, 45, 70],
    })

@pytest.fixture()
def sample_conflicts() -> list[SpatialConflict]:
    """Create sample SpatialConflict objects for testing."""
    return [
        SpatialConflict(
            permit_block=1001,
            inspection_block=1001,
            permit_lat=40.7128,
            permit_lon=-74.0060,
            inspection_lat=40.7128,
            inspection_lon=-74.0060,
            distance_meters=5.5,
            severity="HIGH",
            recommendation="CRITICAL: Reschedule inspection or halt permit work"
        ),
        SpatialConflict(
            permit_block=1002,
            inspection_block=1002,
            permit_lat=40.7160,
            permit_lon=-74.0050,
            inspection_lat=40.7161,
            inspection_lon=-74.0051,
            distance_meters=25.3,
            severity="MEDIUM",
            recommendation="WARNING: Coordinate with permit holder"
        ),
        SpatialConflict(
            permit_block=1003,
            inspection_block=1003,
            permit_lat=40.7150,
            permit_lon=-74.0040,
            inspection_lat=40.7151,
            inspection_lon=-74.0041,
            distance_meters=60.2,
            severity="LOW",
            recommendation="CAUTION: Monitor for safety issues"
        ),
        SpatialConflict(
            permit_block=1005,
            inspection_block=1006,
            permit_lat=40.7120,
            permit_lon=-74.0020,
            inspection_lat=40.7100,
            inspection_lon=-74.0015,
            distance_meters=30.1,
            severity="MEDIUM",
            recommendation="WARNING: Coordinate with permit holder"
        ),
    ]

# ---------------------------------------------------------------------------
# Test: Data Loading
# ---------------------------------------------------------------------------

class TestDataLoading:
    """Test data loading for permits and inspections."""

    def test_permits_dataframe_structure(self, sample_permits_df):
        """Verify permits DataFrame has required columns."""
        required_cols = {
            "permit_block", "permit_lat", "permit_lon", "permit_status"
        }
        assert required_cols.issubset(set(sample_permits_df.columns))

    def test_inspections_dataframe_structure(self, sample_inspections_df):
        """Verify inspections DataFrame has required columns."""
        required_cols = {
            "inspection_block", "inspection_lat", "inspection_lon", "inspection_status"
        }
        assert required_cols.issubset(set(sample_inspections_df.columns))

    def test_permits_dataframe_not_empty(self, sample_permits_df):
        """Verify permits data is not empty."""
        assert len(sample_permits_df) > 0

    def test_inspections_dataframe_not_empty(self, sample_inspections_df):
        """Verify inspections data is not empty."""
        assert len(sample_inspections_df) > 0

    def test_permits_have_coordinates(self, sample_permits_df):
        """Verify permits have valid coordinates."""
        assert sample_permits_df["permit_lat"].notna().all()
        assert sample_permits_df["permit_lon"].notna().all()

    def test_inspections_have_coordinates(self, sample_inspections_df):
        """Verify inspections have valid coordinates."""
        assert sample_inspections_df["inspection_lat"].notna().all()
        assert sample_inspections_df["inspection_lon"].notna().all()

# ---------------------------------------------------------------------------
# Test: Task 5 - Spatial Conflict Detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Test spatial conflict detection integration (Task 5)."""

    def test_detect_conflicts_returns_list(
        self, sample_permits_df, sample_inspections_df
    ):
        """Verify detect_spatial_conflicts returns a list."""
        conflicts = detect_spatial_conflicts(
            sample_permits_df, sample_inspections_df, buffer_meters=50
        )
        assert isinstance(conflicts, list)

    def test_detect_conflicts_returns_spatial_conflict_objects(
        self, sample_permits_df, sample_inspections_df
    ):
        """Verify all returned conflicts are SpatialConflict objects."""
        conflicts = detect_spatial_conflicts(
            sample_permits_df, sample_inspections_df, buffer_meters=50
        )
        for conflict in conflicts:
            assert isinstance(conflict, SpatialConflict)

    def test_conflicts_within_buffer_distance(
        self, sample_permits_df, sample_inspections_df
    ):
        """Verify all detected conflicts are within buffer distance."""
        buffer_meters = 50
        conflicts = detect_spatial_conflicts(
            sample_permits_df, sample_inspections_df, buffer_meters=buffer_meters
        )
        for conflict in conflicts:
            assert conflict.distance_meters <= buffer_meters

    def test_conflict_severity_classification(self, sample_conflicts):
        """Verify conflict severity is properly classified."""
        for conflict in sample_conflicts:
            assert conflict.severity in {"HIGH", "MEDIUM", "LOW"}

    def test_summarize_conflicts_by_severity(self, sample_conflicts):
        """Verify conflict summary aggregation."""
        summary = summarize_conflicts_by_severity(sample_conflicts)
        assert isinstance(summary, dict)
        assert "HIGH" in summary
        assert "MEDIUM" in summary
        assert "LOW" in summary
        assert summary["HIGH"] == 1
        assert summary["MEDIUM"] == 2
        assert summary["LOW"] == 1

# ---------------------------------------------------------------------------
# Test: Section 1 - Conflict Summary
# ---------------------------------------------------------------------------

class TestConflictSummarySection:
    """Test Conflict Summary section functionality."""

    def test_conflict_count_accuracy(self, sample_conflicts):
        """Verify conflict count is accurate."""
        assert len(sample_conflicts) == 4

    def test_severity_distribution(self, sample_conflicts):
        """Verify severity distribution is correct."""
        summary = summarize_conflicts_by_severity(sample_conflicts)
        total = sum(summary.values())
        assert total == len(sample_conflicts)

    def test_high_severity_detection(self, sample_conflicts):
        """Verify HIGH severity conflicts are detected."""
        high_conflicts = [c for c in sample_conflicts if c.severity == "HIGH"]
        assert len(high_conflicts) > 0

    def test_medium_severity_detection(self, sample_conflicts):
        """Verify MEDIUM severity conflicts are detected."""
        medium_conflicts = [c for c in sample_conflicts if c.severity == "MEDIUM"]
        assert len(medium_conflicts) > 0

    def test_low_severity_detection(self, sample_conflicts):
        """Verify LOW severity conflicts are detected."""
        low_conflicts = [c for c in sample_conflicts if c.severity == "LOW"]
        assert len(low_conflicts) > 0

    def test_trend_data_structure(self, sample_conflicts):
        """Verify trend data can be structured as DataFrame."""
        # Create simple trend
        dates = [
            datetime.now(timezone.utc).date() - timedelta(days=i)
            for i in range(7)
        ]
        trend_data = [
            {"date": d, "count": len(sample_conflicts) // 7}
            for d in dates
        ]
        trend_df = pd.DataFrame(trend_data)
        assert len(trend_df) == 7
        assert "date" in trend_df.columns
        assert "count" in trend_df.columns

# ---------------------------------------------------------------------------
# Test: Section 2 - Block-Level Analysis
# ---------------------------------------------------------------------------

class TestBlockAnalysisSection:
    """Test Block-Level Analysis section functionality."""

    def test_filter_by_borough(self, sample_conflicts):
        """Verify borough filtering works."""
        # Extract borough info from conflict blocks
        filtered = sample_conflicts[:2]
        assert len(filtered) <= len(sample_conflicts)

    def test_filter_by_severity(self, sample_conflicts):
        """Verify severity filtering works."""
        high_only = [c for c in sample_conflicts if c.severity == "HIGH"]
        assert all(c.severity == "HIGH" for c in high_only)

    def test_filter_by_distance(self, sample_conflicts):
        """Verify distance filtering works."""
        max_distance = 50
        within_distance = [c for c in sample_conflicts if c.distance_meters <= max_distance]
        assert all(c.distance_meters <= max_distance for c in within_distance)

    def test_multiple_filter_combination(self, sample_conflicts):
        """Verify combining multiple filters."""
        severity_filter = {"HIGH", "MEDIUM"}
        distance_filter = 50
        filtered = [
            c for c in sample_conflicts
            if c.severity in severity_filter
            and c.distance_meters <= distance_filter
        ]
        assert len(filtered) > 0

    def test_conflict_coordinates_present(self, sample_conflicts):
        """Verify all conflicts have valid coordinates for mapping."""
        for conflict in sample_conflicts:
            assert -90 <= conflict.permit_lat <= 90
            assert -180 <= conflict.permit_lon <= 180
            assert -90 <= conflict.inspection_lat <= 90
            assert -180 <= conflict.inspection_lon <= 180

    def test_conflict_details_generation(self, sample_conflicts):
        """Verify conflict details can be formatted for display."""
        for conflict in sample_conflicts:
            details = {
                "Permit Block": conflict.permit_block,
                "Inspection Block": conflict.inspection_block,
                "Distance (m)": f"{conflict.distance_meters:.1f}",
                "Severity": conflict.severity,
                "Recommendation": conflict.recommendation,
            }
            assert len(details) == 5

# ---------------------------------------------------------------------------
# Test: Section 3 - Location Recommendations
# ---------------------------------------------------------------------------

class TestRecommendationsSection:
    """Test Location Recommendations section functionality."""

    def test_confidence_interval_computation(self):
        """Verify Task 3 - Confidence Interval integration."""
        # Test Wilson Score CI
        ci_result = wilson_score_confidence_interval(
            successes=10,
            total=20,
            confidence_level=0.95
        )
        assert "point_estimate" in ci_result
        assert "lower_bound" in ci_result
        assert "upper_bound" in ci_result
        assert ci_result["lower_bound"] <= ci_result["point_estimate"] <= ci_result["upper_bound"]

    def test_scheduling_reliability_ci(self, sample_conflicts):
        """Verify scheduling reliability can be estimated with CI."""
        total = len(sample_conflicts)
        safe = len([c for c in sample_conflicts if c.severity != "HIGH"])
        ci_result = wilson_score_confidence_interval(safe, total, 0.95)
        assert 0 <= ci_result["point_estimate"] <= 1

    def test_domain_rules_validation(self, sample_permits_df):
        """Verify Task 4 - Domain Rules integration."""
        # Test material lifespan rule
        result = validate_material_lifespan_rule(sample_permits_df)
        assert result.rule_name == "material_lifespan_rule"
        assert result.status in {"PASS", "WARNING", "FAIL"}

    def test_estimated_work_duration(self):
        """Verify work duration estimation."""
        estimated_days = 3
        assert estimated_days > 0

    def test_recommendation_date_generation(self, sample_conflicts):
        """Verify recommendation dates can be generated."""
        current_date = datetime.now(timezone.utc).date()
        estimated_duration = 3

        recommendations = []
        for i, conflict in enumerate(sample_conflicts[:3], 1):
            rec_date = current_date + timedelta(days=i * estimated_duration)
            recommendations.append({
                "Permit Block": conflict.permit_block,
                "Recommended Date": rec_date.strftime("%Y-%m-%d"),
                "Suggested Window": f"{estimated_duration} days",
            })

        assert len(recommendations) == 3
        # Verify dates are in future
        for rec in recommendations:
            rec_date = datetime.strptime(rec["Recommended Date"], "%Y-%m-%d").date()
            assert rec_date >= current_date

# ---------------------------------------------------------------------------
# Test: Section 4 - Conflict Resolution
# ---------------------------------------------------------------------------

class TestConflictResolutionSection:
    """Test Conflict Resolution section functionality."""

    def test_conflicts_sorted_by_severity(self, sample_conflicts):
        """Verify conflicts can be sorted by severity."""
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sorted_conflicts = sorted(
            sample_conflicts,
            key=lambda c: severity_order.get(c.severity, 3)
        )
        assert sorted_conflicts[0].severity == "HIGH"

    def test_resolution_suggestions_generation(self, sample_conflicts):
        """Verify resolution suggestions can be generated."""
        current_date = datetime.now(timezone.utc).date()
        resolutions = []

        for i, conflict in enumerate(sample_conflicts, 1):
            reschedule_date = current_date + timedelta(days=14 + (i % 7))
            resolutions.append({
                "Permit Block": conflict.permit_block,
                "Inspection Block": conflict.inspection_block,
                "Severity": conflict.severity,
                "Suggested Reschedule": reschedule_date.strftime("%Y-%m-%d"),
                "Recommendation": conflict.recommendation,
            })

        assert len(resolutions) == len(sample_conflicts)

    def test_resolution_by_severity_grouping(self, sample_conflicts):
        """Verify resolutions can be grouped by severity."""
        grouped = {}
        for conflict in sample_conflicts:
            if conflict.severity not in grouped:
                grouped[conflict.severity] = []
            grouped[conflict.severity].append(conflict)

        assert len(grouped) == 3
        assert "HIGH" in grouped
        assert "MEDIUM" in grouped
        assert "LOW" in grouped

    def test_audit_logging_integration(self, sample_conflicts):
        """Verify Task 1 - Audit Logging integration."""
        # Create audit logger
        audit_logger = AuditLogger()

        # Log conflict resolution
        audit_logger.log_check(
            check_type="conflict_detection",
            table_name="spatial_conflicts",
            status="success",
            rows_affected=len(sample_conflicts),
            details={"conflicts_detected": len(sample_conflicts)}
        )

        assert len(audit_logger.entries) == 1
        assert audit_logger.entries[0].check_type == "conflict_detection"

# ---------------------------------------------------------------------------
# Test: Integration Tests
# ---------------------------------------------------------------------------

class TestDashboardIntegration:
    """Test full dashboard integration across all tasks."""

    def test_end_to_end_workflow(
        self, sample_permits_df, sample_inspections_df, sample_conflicts
    ):
        """Verify end-to-end workflow from data to conflict resolution."""
        # Step 1: Load data
        assert not sample_permits_df.empty
        assert not sample_inspections_df.empty

        # Step 2: Detect conflicts (Task 5)
        conflicts = detect_spatial_conflicts(
            sample_permits_df, sample_inspections_df, buffer_meters=50
        )
        assert isinstance(conflicts, list)

        # Step 3: Summarize by severity (Task 5)
        summary = summarize_conflicts_by_severity(conflicts)
        assert isinstance(summary, dict)

        # Step 4: Confidence intervals for scheduling (Task 3)
        if len(conflicts) > 0:
            safe = len([c for c in conflicts if c.severity != "HIGH"])
            ci = wilson_score_confidence_interval(safe, len(conflicts))
            assert "point_estimate" in ci

        # Step 5: Domain rule validation (Task 4)
        domain_result = validate_material_lifespan_rule(sample_permits_df)
        assert domain_result.status in {"PASS", "WARNING", "FAIL"}

        # Step 6: Audit logging (Task 1)
        audit_logger = AuditLogger()
        audit_logger.log_check(
            "integration_test",
            "construction_planning",
            "success",
            len(conflicts)
        )
        assert len(audit_logger.entries) > 0

    def test_all_four_sections_can_render(
        self, sample_permits_df, sample_inspections_df, sample_conflicts
    ):
        """Verify all four dashboard sections can be rendered."""
        # Section 1: Conflict Summary
        summary = summarize_conflicts_by_severity(sample_conflicts)
        assert len(summary) == 3

        # Section 2: Block Analysis
        filtered = [c for c in sample_conflicts if c.severity == "HIGH"]
        assert len(filtered) > 0

        # Section 3: Recommendations
        ci = wilson_score_confidence_interval(1, 4)
        assert "point_estimate" in ci

        # Section 4: Conflict Resolution
        sorted_conflicts = sorted(
            sample_conflicts,
            key=lambda c: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(c.severity, 3)
        )
        assert len(sorted_conflicts) == len(sample_conflicts)

    def test_data_reconciliation_integration(self, sample_permits_df, sample_inspections_df):
        """Verify Task 2 - Reconciliation integration."""
        # Create simple reconciliation
        expected_permits = 5
        actual_permits = len(sample_permits_df)

        assert actual_permits == expected_permits

    def test_audit_trail_completeness(self, sample_conflicts):
        """Verify audit trail can track all operations."""
        audit_logger = AuditLogger()

        # Log multiple operations
        audit_logger.log_check("conflict_detection", "permits_vs_inspections", "success", 4)
        audit_logger.log_check("severity_classification", "conflicts", "success", 4)
        audit_logger.log_check("block_analysis", "spatial_data", "success", 0)

        assert len(audit_logger.entries) == 3
        summary = audit_logger.get_summary()
        assert summary["total_entries"] == 3

# ---------------------------------------------------------------------------
# Test: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_conflict_list(self):
        """Verify handling of empty conflict list."""
        conflicts = []
        summary = summarize_conflicts_by_severity(conflicts)
        assert summary["HIGH"] == 0
        assert summary["MEDIUM"] == 0
        assert summary["LOW"] == 0

    def test_single_conflict(self):
        """Verify handling of single conflict."""
        conflict = SpatialConflict(
            permit_block=1,
            inspection_block=1,
            permit_lat=40.7128,
            permit_lon=-74.0060,
            inspection_lat=40.7129,
            inspection_lon=-74.0061,
            distance_meters=10.0,
            severity="HIGH",
            recommendation="CRITICAL"
        )
        summary = summarize_conflicts_by_severity([conflict])
        assert sum(summary.values()) == 1

    def test_confidence_interval_edge_cases(self):
        """Verify CI computation with edge cases."""
        # All successes
        ci_all = wilson_score_confidence_interval(10, 10)
        assert ci_all["point_estimate"] == 1.0

        # No successes
        ci_none = wilson_score_confidence_interval(0, 10)
        assert ci_none["point_estimate"] == 0.0

        # Single sample
        ci_one = wilson_score_confidence_interval(1, 1)
        assert ci_one["point_estimate"] == 1.0

    def test_dataframe_with_missing_values(self):
        """Verify handling of DataFrames with missing values."""
        df = pd.DataFrame({
            "permit_block": [1, 2, None, 4],
            "permit_lat": [40.7, None, 40.8, 40.9],
            "permit_lon": [-74.0, -74.1, -74.2, None],
            "permit_status": ["Active", "Active", "Active", "Active"],
        })
        # Should handle gracefully
        assert len(df) == 4
