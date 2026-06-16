"""
Test Suite for Domain Validation Rules for NYC Sidewalk Data

Tests validate material lifespan rules, borough coverage distribution,
permit-inspection relationships, and rule orchestration.

Standards: pytest, comprehensive coverage, edge case handling
"""

from __future__ import annotations

import pandas as pd
import pytest

from socrata_toolkit.quality.domain_rules import (
    DomainRuleResult,
    summarize_domain_rule_results,
    validate_all_domain_rules,
    validate_borough_coverage_distribution,
    validate_material_lifespan_rule,
    validate_permit_inspection_relationship,
)

# ============================================================================
# FIXTURES - Test Data Setup
# ============================================================================

@pytest.fixture
def inspection_data_material():
    """Create sample inspection data with material types and lifespans."""
    return pd.DataFrame(
        {
            "inspection_id": [
                "INS001",
                "INS002",
                "INS003",
                "INS004",
                "INS005",
                "INS006",
            ],
            "material_type": [
                "concrete",
                "concrete",
                "asphalt",
                "asphalt",
                "concrete",
                "asphalt",
            ],
            "lifespan_years": [18.0, 19.0, 11.0, 10.5, 17.5, 11.5],
            "borough": [
                "MANHATTAN",
                "BROOKLYN",
                "QUEENS",
                "BRONX",
                "MANHATTAN",
                "STATEN_ISLAND",
            ],
        }
    )

@pytest.fixture
def inspection_data_borough_manhattan_heavy():
    """Create inspection data with Manhattan representing 40% (PASS case)."""
    return pd.DataFrame(
        {
            "inspection_id": [
                f"INS{i:03d}" for i in range(100)
            ],
            "borough": (
                (["MANHATTAN"] * 40)
                + (["BROOKLYN"] * 30)
                + (["QUEENS"] * 20)
                + (["BRONX"] * 10)
            ),
            "material_type": ["concrete"] * 100,
            "lifespan_years": [18.0] * 100,
        }
    )

@pytest.fixture
def inspection_data_borough_manhattan_low():
    """Create inspection data with Manhattan at 20% (FAIL case)."""
    return pd.DataFrame(
        {
            "inspection_id": [
                f"INS{i:03d}" for i in range(100)
            ],
            "borough": (
                (["MANHATTAN"] * 20)
                + (["BROOKLYN"] * 30)
                + (["QUEENS"] * 30)
                + (["BRONX"] * 20)
            ),
            "material_type": ["concrete"] * 100,
            "lifespan_years": [18.0] * 100,
        }
    )

@pytest.fixture
def inspection_data_borough_manhattan_warning():
    """Create inspection data with Manhattan at 32% (WARNING case)."""
    return pd.DataFrame(
        {
            "inspection_id": [
                f"INS{i:03d}" for i in range(100)
            ],
            "borough": (
                (["MANHATTAN"] * 32)
                + (["BROOKLYN"] * 30)
                + (["QUEENS"] * 20)
                + (["BRONX"] * 18)
            ),
            "material_type": ["concrete"] * 100,
            "lifespan_years": [18.0] * 100,
        }
    )

@pytest.fixture
def permits_data():
    """Create sample permits data."""
    return pd.DataFrame(
        {
            "permit_id": ["P001", "P002", "P003"],
            "borough": ["MANHATTAN", "BROOKLYN", "MANHATTAN"],
            "start_date": ["2026-01-01", "2026-02-01", "2026-03-01"],
            "end_date": ["2026-03-01", "2026-04-01", "2026-05-01"],
            "latitude": [40.7128, 40.6501, 40.7580],
            "longitude": [-74.0060, -73.9496, -73.9855],
        }
    )

@pytest.fixture
def inspections_data():
    """Create sample inspections data with dates within permit range."""
    return pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002", "INS003"],
            "borough": ["MANHATTAN", "BROOKLYN", "MANHATTAN"],
            "inspection_date": ["2026-02-01", "2026-03-01", "2026-04-01"],
            "latitude": [40.7128, 40.6501, 40.7580],
            "longitude": [-74.0060, -73.9496, -73.9855],
        }
    )

@pytest.fixture
def inspections_data_misaligned():
    """Create inspections data with dates outside permit range."""
    return pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002", "INS003", "INS004"],
            "borough": ["MANHATTAN", "BROOKLYN", "MANHATTAN", "QUEENS"],
            "inspection_date": [
                "2026-02-01",
                "2026-03-01",
                "2026-07-01",  # Outside permit range
                "2026-08-01",  # Different borough
            ],
            "latitude": [40.7128, 40.6501, 40.7580, 40.7282],
            "longitude": [-74.0060, -73.9496, -73.9855, -73.7949],
        }
    )

@pytest.fixture
def material_data_condition_score():
    """Create data with condition_score instead of lifespan_years."""
    return pd.DataFrame(
        {
            "inspection_id": [
                "INS001",
                "INS002",
                "INS003",
                "INS004",
                "INS005",
                "INS006",
            ],
            "material_type": [
                "concrete",
                "concrete",
                "asphalt",
                "asphalt",
                "concrete",
                "asphalt",
            ],
            "condition_score": [85.0, 88.0, 65.0, 62.0, 87.0, 64.0],  # Higher is better
            "borough": [
                "MANHATTAN",
                "BROOKLYN",
                "QUEENS",
                "BRONX",
                "MANHATTAN",
                "STATEN_ISLAND",
            ],
        }
    )

@pytest.fixture
def material_data_with_nulls():
    """Create material data with missing values."""
    return pd.DataFrame(
        {
            "inspection_id": [
                "INS001",
                "INS002",
                "INS003",
                "INS004",
                "INS005",
                "INS006",
            ],
            "material_type": [
                "concrete",
                "concrete",
                "asphalt",
                None,
                "concrete",
                "asphalt",
            ],
            "lifespan_years": [18.0, None, 11.0, 10.5, 17.5, 11.5],
            "borough": [
                "MANHATTAN",
                "BROOKLYN",
                "QUEENS",
                "BRONX",
                "MANHATTAN",
                "STATEN_ISLAND",
            ],
        }
    )

# ============================================================================
# TESTS - Material Lifespan Rule
# ============================================================================

def test_material_lifespan_pass(inspection_data_material):
    """Test material_lifespan_rule with passing data (concrete > asphalt)."""
    result = validate_material_lifespan_rule(inspection_data_material)

    assert isinstance(result, DomainRuleResult)
    assert result.status == "PASS"
    assert result.rule_name == "material_lifespan_rule"
    assert result.rows_affected == 0  # No violations
    assert "Concrete avg: 18.2" in result.details
    assert "Asphalt avg: 11.0" in result.details
    assert result.fix_recommendation is None

def test_material_lifespan_fail_reversed_data():
    """Test material_lifespan_rule with failing data (asphalt > concrete)."""
    df = pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002", "INS003", "INS004"],
            "material_type": ["concrete", "concrete", "asphalt", "asphalt"],
            "lifespan_years": [8.0, 9.0, 18.0, 19.0],  # Asphalt > concrete
            "borough": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
        }
    )

    result = validate_material_lifespan_rule(df)

    assert result.status == "FAIL"
    assert result.rows_affected > 0
    assert "Review asphalt records" in result.fix_recommendation

def test_material_lifespan_condition_score(material_data_condition_score):
    """Test material_lifespan_rule with condition_score column."""
    result = validate_material_lifespan_rule(material_data_condition_score)

    assert result.status == "PASS"
    assert "Concrete avg: 86.7" in result.details
    assert "Asphalt avg: 63.7" in result.details

def test_material_lifespan_missing_column():
    """Test material_lifespan_rule with missing lifespan/age column."""
    df = pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002"],
            "material_type": ["concrete", "asphalt"],
            "borough": ["MANHATTAN", "BROOKLYN"],
        }
    )

    result = validate_material_lifespan_rule(df)

    assert result.status == "WARNING"
    assert "No lifespan/age column found" in result.details
    assert "Add a lifespan or age column" in result.fix_recommendation

def test_material_lifespan_no_material_data():
    """Test material_lifespan_rule with no concrete/asphalt data."""
    df = pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002"],
            "material_type": ["permeable", "rubber"],
            "lifespan_years": [15.0, 12.0],
            "borough": ["MANHATTAN", "BROOKLYN"],
        }
    )

    result = validate_material_lifespan_rule(df)

    assert result.status == "WARNING"
    assert "No concrete or asphalt records found" in result.details

def test_material_lifespan_with_nulls(material_data_with_nulls):
    """Test material_lifespan_rule with null values."""
    result = validate_material_lifespan_rule(material_data_with_nulls)

    # Should handle nulls gracefully
    assert result.status in ["PASS", "FAIL", "WARNING"]

# ============================================================================
# TESTS - Borough Coverage Distribution Rule
# ============================================================================

def test_borough_coverage_pass(inspection_data_borough_manhattan_heavy):
    """Test borough_coverage_rule with passing data (40% Manhattan)."""
    result = validate_borough_coverage_distribution(inspection_data_borough_manhattan_heavy)

    assert result.status == "PASS"
    assert result.rule_name == "borough_coverage_distribution"
    assert "40.0%" in result.details
    assert result.fix_recommendation is None

def test_borough_coverage_warning(inspection_data_borough_manhattan_warning):
    """Test borough_coverage_rule with warning data (32% Manhattan)."""
    result = validate_borough_coverage_distribution(inspection_data_borough_manhattan_warning)

    assert result.status == "WARNING"
    assert "32.0%" in result.details
    assert "Monitor Manhattan coverage trend" in result.fix_recommendation

def test_borough_coverage_fail(inspection_data_borough_manhattan_low):
    """Test borough_coverage_rule with failing data (20% Manhattan)."""
    result = validate_borough_coverage_distribution(inspection_data_borough_manhattan_low)

    assert result.status == "FAIL"
    assert "20.0%" in result.details
    assert "Investigate potential data collection bias" in result.fix_recommendation
    assert result.rows_affected > 0

def test_borough_coverage_missing_column():
    """Test borough_coverage_rule with missing borough column."""
    df = pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002"],
            "material_type": ["concrete", "asphalt"],
        }
    )

    result = validate_borough_coverage_distribution(df)

    assert result.status == "WARNING"
    assert "No 'borough' column found" in result.details

def test_borough_coverage_all_manhattan():
    """Test borough_coverage_rule with all Manhattan records (100%)."""
    df = pd.DataFrame(
        {
            "inspection_id": [f"INS{i:03d}" for i in range(50)],
            "borough": ["MANHATTAN"] * 50,
        }
    )

    result = validate_borough_coverage_distribution(df)

    assert result.status == "FAIL"
    assert "100.0%" in result.details

def test_borough_coverage_no_manhattan():
    """Test borough_coverage_rule with no Manhattan records (0%)."""
    df = pd.DataFrame(
        {
            "inspection_id": [f"INS{i:03d}" for i in range(50)],
            "borough": (
                (["BROOKLYN"] * 20)
                + (["QUEENS"] * 20)
                + (["BRONX"] * 10)
            ),
        }
    )

    result = validate_borough_coverage_distribution(df)

    assert result.status == "FAIL"
    assert "0.0%" in result.details

# ============================================================================
# TESTS - Permit-Inspection Relationship Rule
# ============================================================================

def test_permit_inspection_pass(permits_data, inspections_data):
    """Test permit_inspection_rule with well-aligned data."""
    result = validate_permit_inspection_relationship(permits_data, inspections_data)

    assert result.status == "PASS"
    assert result.rule_name == "permit_inspection_relationship"
    assert "0 Borough mismatches" in result.details

def test_permit_inspection_misaligned(permits_data, inspections_data_misaligned):
    """Test permit_inspection_rule with misaligned dates."""
    result = validate_permit_inspection_relationship(permits_data, inspections_data_misaligned)

    assert result.status in ["WARNING", "FAIL"]
    assert result.rows_affected > 0

def test_permit_inspection_missing_columns():
    """Test permit_inspection_rule with missing required columns."""
    permits = pd.DataFrame({"permit_id": ["P001"]})
    inspections = pd.DataFrame({"inspection_id": ["INS001"]})

    result = validate_permit_inspection_relationship(permits, inspections)

    assert result.status == "WARNING"
    assert "Missing columns" in result.details

def test_permit_inspection_empty_dataframes():
    """Test permit_inspection_rule with empty DataFrames."""
    permits = pd.DataFrame()
    inspections = pd.DataFrame()

    result = validate_permit_inspection_relationship(permits, inspections)

    assert result.status == "PASS"  # Empty data = no violations
    assert "empty" in result.details.lower()

def test_permit_inspection_null_dates(permits_data):
    """Test permit_inspection_rule with invalid dates."""
    inspections = pd.DataFrame(
        {
            "inspection_id": ["INS001", "INS002"],
            "borough": ["MANHATTAN", "BROOKLYN"],
            "inspection_date": ["invalid_date", None],
            "latitude": [40.7128, 40.6501],
            "longitude": [-74.0060, -73.9496],
        }
    )

    result = validate_permit_inspection_relationship(permits_data, inspections)

    assert result.status in ["WARNING", "PASS"]

# ============================================================================
# TESTS - Rule Orchestration
# ============================================================================

def test_validate_all_domain_rules(inspection_data_material):
    """Test validate_all_domain_rules orchestrator."""
    results = validate_all_domain_rules(inspection_data_material)

    assert isinstance(results, list)
    assert len(results) >= 2  # At least material + borough rules
    assert all(isinstance(r, DomainRuleResult) for r in results)
    assert any(r.rule_name == "material_lifespan_rule" for r in results)
    assert any(r.rule_name == "borough_coverage_distribution" for r in results)

def test_validate_all_domain_rules_with_permits(
    inspection_data_material, permits_data, inspections_data
):
    """Test validate_all_domain_rules with permit data."""
    results = validate_all_domain_rules(
        inspection_data_material,
        permits_df=permits_data,
        inspections_df=inspections_data,
    )

    assert len(results) >= 3  # material + borough + permit-inspection
    assert any(r.rule_name == "permit_inspection_relationship" for r in results)

def test_summarize_domain_rule_results(inspection_data_material):
    """Test summarize_domain_rule_results utility."""
    results = validate_all_domain_rules(inspection_data_material)
    summary = summarize_domain_rule_results(results)

    assert "total_rules" in summary
    assert "passed" in summary
    assert "warnings" in summary
    assert "failures" in summary
    assert "total_rows_affected" in summary
    assert "rules" in summary
    assert summary["total_rules"] == len(results)
    assert summary["passed"] + summary["warnings"] + summary["failures"] == len(results)

# ============================================================================
# TESTS - Edge Cases
# ============================================================================

def test_domain_rule_empty_dataframe():
    """Test rules with empty DataFrame."""
    df = pd.DataFrame()
    result = validate_material_lifespan_rule(df)
    assert result.status in ["WARNING", "PASS"]

def test_domain_rule_single_row():
    """Test rules with single-row DataFrame."""
    df = pd.DataFrame(
        {
            "inspection_id": ["INS001"],
            "material_type": ["concrete"],
            "lifespan_years": [18.0],
            "borough": ["MANHATTAN"],
        }
    )
    result = validate_material_lifespan_rule(df)
    assert result.status in ["WARNING", "PASS", "FAIL"]

def test_borough_large_dataset():
    """Test borough coverage with large dataset (1000 rows)."""
    df = pd.DataFrame(
        {
            "inspection_id": [f"INS{i:05d}" for i in range(1000)],
            "borough": (
                (["MANHATTAN"] * 400)
                + (["BROOKLYN"] * 300)
                + (["QUEENS"] * 200)
                + (["BRONX"] * 100)
            ),
        }
    )
    result = validate_borough_coverage_distribution(df)
    assert result.status == "PASS"
    assert "40.0%" in result.details

# ============================================================================
# TESTS - Data Quality Integration
# ============================================================================

def test_domain_rules_with_realistic_inspection_data():
    """Test domain rules with realistic NYC inspection data structure."""
    df = pd.DataFrame(
        {
            "objectid": range(1000),
            "the_geom": ["POINT(...)"] * 1000,
            "borough": (
                (["MANHATTAN"] * 420)
                + (["BROOKLYN"] * 280)
                + (["QUEENS"] * 150)
                + (["BRONX"] * 100)
                + (["STATEN_ISLAND"] * 50)
            ),
            "material_type": (
                (["concrete"] * 600)
                + (["asphalt"] * 300)
                + (["permeable"] * 100)
            ),
            "condition_rating": ["GOOD", "FAIR", "POOR"] * 334,
            "created_date": pd.date_range("2025-01-01", periods=1000, freq="H"),
            "lifespan_years": (
                [18.0] * 600  # Concrete
                + [11.0] * 300  # Asphalt
                + [15.0] * 100  # Permeable
            ),
        }
    )

    results = validate_all_domain_rules(df)

    assert len(results) >= 2
    assert results[0].rule_name == "material_lifespan_rule"
    assert results[0].status == "PASS"
    assert results[1].rule_name == "borough_coverage_distribution"
    assert results[1].status == "PASS"

# ============================================================================
# TESTS - Exception Handling
# ============================================================================

def test_material_lifespan_exception_handling(inspection_data_material):
    """Test exception handling in material_lifespan_rule."""
    # Create a DataFrame that will cause an exception
    df = inspection_data_material.copy()
    df["lifespan_years"] = "invalid"  # Non-numeric

    result = validate_material_lifespan_rule(df)

    # Should handle gracefully
    assert result.status == "WARNING"
    assert "error" in result.details.lower()

def test_borough_coverage_exception_handling(inspection_data_borough_manhattan_heavy):
    """Test exception handling in borough_coverage_rule."""
    df = inspection_data_borough_manhattan_heavy.copy()
    df["borough"] = None  # Null borough

    result = validate_borough_coverage_distribution(df)

    # Should handle gracefully
    assert result.status in ["WARNING", "PASS"]

def test_permit_inspection_exception_handling(permits_data):
    """Test exception handling in permit_inspection_rule."""
    # Create malformed inspection data
    inspections = pd.DataFrame(
        {
            "inspection_id": ["INS001"],
            "borough": ["MANHATTAN"],
            "inspection_date": ["not_a_date"],
            "latitude": [40.7128],
            "longitude": [-74.0060],
        }
    )

    result = validate_permit_inspection_relationship(permits_data, inspections)

    # Should handle gracefully
    assert result.status in ["WARNING", "PASS"]
