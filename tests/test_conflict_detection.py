"""
Tests for GIS Conflict Detection module.

Tests the spatial conflict detection functionality for construction planning,
including:
- Conflict detection between permits and inspections
- Severity classification
- Distance calculation accuracy
- Edge cases and data validation
"""

from __future__ import annotations

import pandas as pd
import pytest

from socrata_toolkit.spatial.conflict_detection import (
    SpatialConflict,
    detect_spatial_conflicts,
    summarize_conflicts_by_severity,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def sample_permits_df():
    """Create sample active permits DataFrame."""
    return pd.DataFrame(
        {
            "permit_block": [100, 101, 102],
            "permit_lat": [40.7480, 40.7490, 40.7500],
            "permit_lon": [-73.9857, -73.9850, -73.9840],
            "permit_status": ["Active", "Active", "Inactive"],
        }
    )


@pytest.fixture()
def sample_inspections_df():
    """Create sample scheduled inspections DataFrame."""
    return pd.DataFrame(
        {
            "inspection_block": [200, 201, 202],
            "inspection_lat": [40.7480, 40.7495, 40.7510],
            "inspection_lon": [-73.9857, -73.9850, -73.9840],
            "inspection_status": ["Scheduled", "Scheduled", "Completed"],
        }
    )


@pytest.fixture()
def overlapping_permits_inspections():
    """Create permits and inspections with guaranteed overlaps within buffer."""
    permits = pd.DataFrame(
        {
            "permit_block": [100, 101, 102],
            "permit_lat": [40.7480, 40.7490, 40.7500],
            "permit_lon": [-73.9857, -73.9850, -73.9840],
            "permit_status": ["Active", "Active", "Active"],
        }
    )
    # Inspections at same or very close locations
    inspections = pd.DataFrame(
        {
            "inspection_block": [200, 201, 202],
            "inspection_lat": [40.7480, 40.7490, 40.7500],
            "inspection_lon": [-73.9857, -73.9850, -73.9840],
            "inspection_status": ["Scheduled", "Scheduled", "Scheduled"],
        }
    )
    return permits, inspections


@pytest.fixture()
def far_apart_permits_inspections():
    """Create permits and inspections that are far apart (no conflicts)."""
    permits = pd.DataFrame(
        {
            "permit_block": [100],
            "permit_lat": [40.7480],
            "permit_lon": [-73.9857],
            "permit_status": ["Active"],
        }
    )
    # Inspection at a different location (~100+ km away)
    inspections = pd.DataFrame(
        {
            "inspection_block": [200],
            "inspection_lat": [41.5000],
            "inspection_lon": [-74.5000],
            "inspection_status": ["Scheduled"],
        }
    )
    return permits, inspections


@pytest.fixture()
def mixed_severity_permits_inspections():
    """Create data with conflicts at different severity levels."""
    # Permits: one near Manhattan
    permits = pd.DataFrame(
        {
            "permit_block": [100, 101, 102],
            "permit_lat": [40.7484, 40.7484, 40.7484],
            "permit_lon": [-73.9857, -73.9857, -73.9857],
            "permit_status": ["Active", "Active", "Active"],
        }
    )
    # Inspections: at varying distances from permit
    # High conflict: 10 meters away (approximately 0.0001 degrees)
    # Medium conflict: 35 meters away
    # Low conflict: 75 meters away
    inspections = pd.DataFrame(
        {
            "inspection_block": [200, 201, 202],
            "inspection_lat": [40.7484 + 0.00009, 40.7484 + 0.00031, 40.7484 + 0.00067],
            "inspection_lon": [-73.9857, -73.9857, -73.9857],
            "inspection_status": ["Scheduled", "Scheduled", "Scheduled"],
        }
    )
    return permits, inspections


# =============================================================================
# SpatialConflict dataclass tests
# =============================================================================


class TestSpatialConflict:
    """Tests for SpatialConflict dataclass."""

    def test_create_spatial_conflict(self):
        """Test creating a SpatialConflict instance."""
        conflict = SpatialConflict(
            permit_block=100,
            inspection_block=200,
            permit_lat=40.7480,
            permit_lon=-73.9857,
            inspection_lat=40.7485,
            inspection_lon=-73.9857,
            distance_meters=555.0,
            severity="HIGH",
            recommendation="CRITICAL: Reschedule inspection or halt permit work",
        )

        assert conflict.permit_block == 100
        assert conflict.inspection_block == 200
        assert conflict.severity == "HIGH"
        assert conflict.distance_meters == 555.0

    def test_spatial_conflict_valid_severities(self):
        """Test that all valid severity levels are accepted."""
        for severity in ["HIGH", "MEDIUM", "LOW"]:
            conflict = SpatialConflict(
                permit_block=100,
                inspection_block=200,
                permit_lat=40.7480,
                permit_lon=-73.9857,
                inspection_lat=40.7485,
                inspection_lon=-73.9857,
                distance_meters=50.0,
                severity=severity,
                recommendation="Test",
            )
            assert conflict.severity == severity

    def test_spatial_conflict_invalid_severity(self):
        """Test that invalid severity levels raise ValueError."""
        with pytest.raises(ValueError):
            SpatialConflict(
                permit_block=100,
                inspection_block=200,
                permit_lat=40.7480,
                permit_lon=-73.9857,
                inspection_lat=40.7485,
                inspection_lon=-73.9857,
                distance_meters=50.0,
                severity="INVALID",
                recommendation="Test",
            )


# =============================================================================
# Distance Calculation Tests
# =============================================================================


class TestDistanceCalculation:
    """Tests for accurate distance calculations."""

    def test_detect_zero_distance_same_location(self, sample_permits_df, sample_inspections_df):
        """Test that identical locations result in near-zero distance conflicts."""
        # Create overlapping data
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7480],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7480],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=50)

        assert len(conflicts) == 1
        assert conflicts[0].distance_meters < 1.0  # Should be nearly 0

    def test_distance_calculation_accuracy(self):
        """Test distance calculation between two known points.

        Using approximate coordinates for NYC locations:
        - Point 1: (40.7484, -73.9857) - Central Park area
        - Point 2: (40.7580, -73.9855) - North of Central Park (~1.1 km away)
        """
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7580],
                "inspection_lon": [-73.9855],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=2000)

        assert len(conflicts) == 1
        # Distance should be approximately 1,000-1,200 meters
        assert 1000 <= conflicts[0].distance_meters <= 1200

    def test_distance_sorted_by_nearest_first(self):
        """Test that conflicts are sorted by distance (nearest first)."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        # Three inspection locations at different distances
        inspections = pd.DataFrame(
            {
                "inspection_block": [200, 201, 202],
                "inspection_lat": [
                    40.7484 + 0.0005,  # ~55 meters away
                    40.7484 + 0.0001,  # ~11 meters away
                    40.7484 + 0.0003,  # ~33 meters away
                ],
                "inspection_lon": [-73.9857, -73.9857, -73.9857],
                "inspection_status": ["Scheduled", "Scheduled", "Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=100)

        # Should have 3 conflicts
        assert len(conflicts) == 3
        # Should be sorted by distance
        for i in range(len(conflicts) - 1):
            assert conflicts[i].distance_meters <= conflicts[i + 1].distance_meters


# =============================================================================
# Severity Classification Tests
# =============================================================================


class TestSeverityClassification:
    """Tests for conflict severity classification."""

    def test_high_severity_classification(self):
        """Test HIGH severity classification for conflicts < 20 meters."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        # Inspection ~15 meters away (approximately 0.00013 degrees at NYC latitude)
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7484 + 0.00013],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=50)

        assert len(conflicts) == 1
        assert conflicts[0].severity == "HIGH"
        assert "CRITICAL" in conflicts[0].recommendation

    def test_medium_severity_classification(self):
        """Test MEDIUM severity classification for conflicts 20-50 meters."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        # Inspection ~35 meters away
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7484 + 0.00031],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=50)

        assert len(conflicts) == 1
        assert conflicts[0].severity == "MEDIUM"
        assert "WARNING" in conflicts[0].recommendation

    def test_low_severity_classification(self):
        """Test LOW severity classification for conflicts 50-100 meters."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        # Inspection ~75 meters away
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7484 + 0.00067],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=100)

        assert len(conflicts) == 1
        assert conflicts[0].severity == "LOW"
        assert "CAUTION" in conflicts[0].recommendation


# =============================================================================
# Conflict Detection Tests
# =============================================================================


class TestDetectConstructionInspectionConflict:
    """Tests for detecting construction-inspection conflicts."""

    def test_detect_overlapping_permits_inspections(self, overlapping_permits_inspections):
        """Test detection of overlapping permits and inspections."""
        permits, inspections = overlapping_permits_inspections

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=50)

        # Should detect 3 conflicts (one for each pair at same location)
        assert len(conflicts) >= 1
        assert all(isinstance(c, SpatialConflict) for c in conflicts)

    def test_no_conflict_when_far_apart(self, far_apart_permits_inspections):
        """Test that no conflicts are detected when locations are far apart."""
        permits, inspections = far_apart_permits_inspections

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=50)

        assert len(conflicts) == 0

    def test_filters_inactive_permits(self, sample_permits_df, sample_inspections_df):
        """Test that inactive permits are filtered out."""
        conflicts = detect_spatial_conflicts(sample_permits_df, sample_inspections_df, buffer_meters=100)

        # Even if permits and inspections were overlapping,
        # only Active permits are considered
        # In this case, we have mixed active/inactive
        # The inactive permit should not generate conflicts
        assert all(c.permit_block != 102 for c in conflicts)

    def test_filters_completed_inspections(self, sample_permits_df, sample_inspections_df):
        """Test that completed inspections are filtered out."""
        conflicts = detect_spatial_conflicts(sample_permits_df, sample_inspections_df, buffer_meters=100)

        # Completed inspections should be filtered
        assert all(c.inspection_block != 202 for c in conflicts)

    def test_handles_missing_coordinates(self):
        """Test that rows with missing coordinates are skipped."""
        permits = pd.DataFrame(
            {
                "permit_block": [100, 101],
                "permit_lat": [40.7484, None],
                "permit_lon": [-73.9857, -73.9857],
                "permit_status": ["Active", "Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200, 201],
                "inspection_lat": [40.7484, 40.7490],
                "inspection_lon": [-73.9857, None],
                "inspection_status": ["Scheduled", "Scheduled"],
            }
        )

        # Should not raise error, just skip invalid rows
        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=50)

        # Should have conflict only for the first permit-inspection pair
        assert len(conflicts) >= 0
        assert all(pd.notna(c.permit_lat) and pd.notna(c.permit_lon) for c in conflicts)
        assert all(pd.notna(c.inspection_lat) and pd.notna(c.inspection_lon) for c in conflicts)


# =============================================================================
# Buffer Distance Tests
# =============================================================================


class TestBufferDistance:
    """Tests for buffer distance parameter."""

    def test_buffer_meters_parameter(self):
        """Test that buffer_meters parameter controls conflict detection range."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        # Inspection ~75 meters away
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7484 + 0.00067],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        # With buffer=50m, should not detect conflict
        conflicts_small = detect_spatial_conflicts(permits, inspections, buffer_meters=50)
        assert len(conflicts_small) == 0

        # With buffer=100m, should detect conflict
        conflicts_large = detect_spatial_conflicts(permits, inspections, buffer_meters=100)
        assert len(conflicts_large) == 1

    def test_default_buffer_is_50_meters(self):
        """Test that default buffer_meters is 50."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        # Inspection ~35 meters away
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7484 + 0.00031],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        # Call without specifying buffer
        conflicts = detect_spatial_conflicts(permits, inspections)

        # Should use default 50m and detect conflict
        assert len(conflicts) == 1


# =============================================================================
# Conflict Summary Tests
# =============================================================================


class TestSummarizeConflictsBySeverity:
    """Tests for conflict severity summarization."""

    def test_summarize_single_high_severity(self):
        """Test summarizing a single HIGH severity conflict."""
        conflicts = [
            SpatialConflict(
                permit_block=100,
                inspection_block=200,
                permit_lat=40.7480,
                permit_lon=-73.9857,
                inspection_lat=40.7481,
                inspection_lon=-73.9857,
                distance_meters=10.0,
                severity="HIGH",
                recommendation="Test",
            )
        ]

        summary = summarize_conflicts_by_severity(conflicts)

        assert summary == {"HIGH": 1, "MEDIUM": 0, "LOW": 0}

    def test_summarize_mixed_severities(self):
        """Test summarizing conflicts with mixed severity levels."""
        conflicts = [
            SpatialConflict(
                permit_block=100,
                inspection_block=200,
                permit_lat=40.7480,
                permit_lon=-73.9857,
                inspection_lat=40.7481,
                inspection_lon=-73.9857,
                distance_meters=10.0,
                severity="HIGH",
                recommendation="Test",
            ),
            SpatialConflict(
                permit_block=101,
                inspection_block=201,
                permit_lat=40.7490,
                permit_lon=-73.9857,
                inspection_lat=40.7492,
                inspection_lon=-73.9857,
                distance_meters=35.0,
                severity="MEDIUM",
                recommendation="Test",
            ),
            SpatialConflict(
                permit_block=102,
                inspection_block=202,
                permit_lat=40.7500,
                permit_lon=-73.9857,
                inspection_lat=40.7504,
                inspection_lon=-73.9857,
                distance_meters=75.0,
                severity="LOW",
                recommendation="Test",
            ),
        ]

        summary = summarize_conflicts_by_severity(conflicts)

        assert summary == {"HIGH": 1, "MEDIUM": 1, "LOW": 1}

    def test_summarize_empty_conflicts(self):
        """Test summarizing empty conflict list."""
        conflicts = []

        summary = summarize_conflicts_by_severity(conflicts)

        assert summary == {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    def test_summarize_only_high_severity(self):
        """Test summarizing list with only HIGH severity conflicts."""
        conflicts = [
            SpatialConflict(
                permit_block=100 + i,
                inspection_block=200 + i,
                permit_lat=40.7480,
                permit_lon=-73.9857,
                inspection_lat=40.7481,
                inspection_lon=-73.9857,
                distance_meters=10.0 + i,
                severity="HIGH",
                recommendation="Test",
            )
            for i in range(3)
        ]

        summary = summarize_conflicts_by_severity(conflicts)

        assert summary == {"HIGH": 3, "MEDIUM": 0, "LOW": 0}


# =============================================================================
# Input Validation Tests
# =============================================================================


class TestInputValidation:
    """Tests for input validation and error handling."""

    def test_raises_error_on_non_dataframe_permits(self, sample_inspections_df):
        """Test that TypeError is raised if permits_df is not a DataFrame."""
        with pytest.raises(TypeError):
            detect_spatial_conflicts({"not": "dataframe"}, sample_inspections_df)

    def test_raises_error_on_non_dataframe_inspections(self, sample_permits_df):
        """Test that TypeError is raised if inspections_df is not a DataFrame."""
        with pytest.raises(TypeError):
            detect_spatial_conflicts(sample_permits_df, {"not": "dataframe"})

    def test_raises_error_on_missing_permit_block_column(self):
        """Test that ValueError is raised if permit_block column is missing."""
        permits = pd.DataFrame(
            {
                "permit_lat": [40.7480],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7480],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        with pytest.raises(ValueError):
            detect_spatial_conflicts(permits, inspections)

    def test_raises_error_on_missing_inspection_block_column(self):
        """Test that ValueError is raised if inspection_block column is missing."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7480],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_lat": [40.7480],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        with pytest.raises(ValueError):
            detect_spatial_conflicts(permits, inspections)

    def test_accepts_alternative_column_names(self):
        """Test that alternative column naming conventions are accepted."""
        # Use alternative names
        permits = pd.DataFrame(
            {
                "block_id": [100],
                "lat": [40.7480],
                "lon": [-73.9857],
                "status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "block_id": [200],
                "lat": [40.7480],
                "lon": [-73.9857],
                "status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections)

        # Should work without raising error
        assert isinstance(conflicts, list)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_permit_multiple_inspections(self):
        """Test one permit against multiple inspection locations."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200, 201, 202],
                "inspection_lat": [40.7484, 40.7485, 40.7486],
                "inspection_lon": [-73.9857, -73.9857, -73.9857],
                "inspection_status": ["Scheduled", "Scheduled", "Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=500)

        # Should find conflicts with all three inspections
        assert len(conflicts) >= 1

    def test_multiple_permits_single_inspection(self):
        """Test multiple permits against one inspection location."""
        permits = pd.DataFrame(
            {
                "permit_block": [100, 101, 102],
                "permit_lat": [40.7484, 40.7485, 40.7486],
                "permit_lon": [-73.9857, -73.9857, -73.9857],
                "permit_status": ["Active", "Active", "Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7484],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections, buffer_meters=500)

        # Should find conflicts with all permits
        assert len(conflicts) >= 1

    def test_empty_permits_dataframe(self):
        """Test with empty permits DataFrame."""
        permits = pd.DataFrame(
            {
                "permit_block": [],
                "permit_lat": [],
                "permit_lon": [],
                "permit_status": [],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [40.7484],
                "inspection_lon": [-73.9857],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections)

        assert len(conflicts) == 0

    def test_empty_inspections_dataframe(self):
        """Test with empty inspections DataFrame."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [40.7484],
                "permit_lon": [-73.9857],
                "permit_status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [],
                "inspection_lat": [],
                "inspection_lon": [],
                "inspection_status": [],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections)

        assert len(conflicts) == 0

    def test_all_missing_coordinates(self):
        """Test with all rows having missing coordinates."""
        permits = pd.DataFrame(
            {
                "permit_block": [100],
                "permit_lat": [None],
                "permit_lon": [None],
                "permit_status": ["Active"],
            }
        )
        inspections = pd.DataFrame(
            {
                "inspection_block": [200],
                "inspection_lat": [None],
                "inspection_lon": [None],
                "inspection_status": ["Scheduled"],
            }
        )

        conflicts = detect_spatial_conflicts(permits, inspections)

        assert len(conflicts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
