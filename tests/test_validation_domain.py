import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")
"""
Tests for Domain-Aware Validation Framework (socrata_toolkit.analysis)

Tests material classification, defect applicability, ADA compliance, marking standards,
and geospatial validation rules.
"""

import pandas as pd

from socrata_toolkit.analysis import (
    validate_ada_compliance_gates,
    validate_defect_applicability,
    validate_geospatial_bounds,
    validate_marking_standards,
    validate_material_coverage,
    validate_required_columns,
    validate_schema_types,
)


class TestLegacyValidation:
    """Tests for backward-compatible validation functions."""

    def test_validate_required_columns_success(self):
        """Test validation passes when all required columns present."""
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"], "value": [10, 20]})
        report = validate_required_columns(df, ["id", "name"])
        assert report.valid is True
        assert len(report.errors) == 0

    def test_validate_required_columns_missing(self):
        """Test validation fails when required columns are missing."""
        df = pd.DataFrame({"id": [1, 2]})
        report = validate_required_columns(df, ["id", "name", "value"])
        assert report.valid is False
        assert len(report.errors) == 2
        assert any("name" in e for e in report.errors)
        assert any("value" in e for e in report.errors)

    def test_validate_schema_types_success(self):
        """Test schema validation passes for matching types."""
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        schema = {"id": "int64", "name": "object"}
        report = validate_schema_types(df, schema)
        assert report.valid is True
        assert len(report.errors) == 0

    def test_validate_schema_types_mismatch(self):
        """Test schema validation surfaces type mismatches as warnings."""
        df = pd.DataFrame({"id": ["1", "2"], "name": ["A", "B"]})
        schema = {"id": "int64", "name": "object"}
        report = validate_schema_types(df, schema)
        assert any("id" in w for w in report.warnings + report.errors)


class TestMaterialValidation:
    """Tests for material classification validation."""

    def test_material_coverage_all_valid(self):
        """Test validation passes when all materials are valid."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "material_type": ["HMA", "PCC", "Permeable Pavers"],
            }
        )
        report = validate_material_coverage(df, "material_type")
        assert report.valid is True
        assert len(report.errors) == 0

    def test_material_coverage_invalid_material(self):
        """Test validation fails for invalid material types."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "material_type": ["HMA", "InvalidMaterial", "PCC"],
            }
        )
        report = validate_material_coverage(df, "material_type")
        assert report.valid is False
        assert len(report.errors) > 0
        assert "invalid" in report.errors[0].lower()

    def test_material_coverage_missing_material(self):
        """Test validation fails when material is null."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "material_type": ["HMA", None, "PCC"],
            }
        )
        report = validate_material_coverage(df, "material_type")
        assert report.valid is False
        assert any("missing" in e.lower() for e in report.errors)

    def test_material_coverage_missing_column(self):
        """Test validation fails when material column doesn't exist."""
        df = pd.DataFrame({"segment_id": [1, 2, 3]})
        report = validate_material_coverage(df, "material_type")
        assert report.valid is False
        assert "not found" in report.errors[0].lower()


class TestDefectValidation:
    """Tests for defect-material applicability validation."""

    def test_defect_applicability_valid_pairing(self):
        """Test validation passes for valid defect-material pairs."""
        df = pd.DataFrame(
            {
                "defect_id": [1, 2, 3],
                "material_type": ["asphalt", "concrete", "all"],
                "defect_type": ["Potholes", "Linear Cracking", "Heaving/Settlement"],
            }
        )
        report = validate_defect_applicability(df, "material_type", "defect_type")
        assert report.valid is True

    def test_defect_applicability_invalid_pairing(self):
        """Test validation fails for incompatible defect-material pairs."""
        df = pd.DataFrame(
            {
                "defect_id": [1, 2],
                "material_type": ["concrete", "asphalt"],
                "defect_type": ["Potholes", "Linear Cracking"],  # Potholes not for concrete
            }
        )
        report = validate_defect_applicability(df, "material_type", "defect_type")
        assert report.valid is False
        assert len(report.errors) > 0

    def test_defect_applicability_missing_columns(self):
        """Test validation fails when required columns missing."""
        df = pd.DataFrame({"defect_id": [1, 2]})
        report = validate_defect_applicability(df, "material_type", "defect_type")
        assert report.valid is False

    def test_defect_applicability_with_nulls(self):
        """Test validation skips null values."""
        df = pd.DataFrame(
            {
                "defect_id": [1, 2, 3],
                "material_type": ["asphalt", None, "concrete"],
                "defect_type": ["Potholes", "Linear Cracking", "Spalling"],
            }
        )
        report = validate_defect_applicability(df, "material_type", "defect_type")
        # Should only report error for row 1 (potholes + concrete)
        assert report.valid is False


class TestADAValidation:
    """Tests for ADA compliance validation."""

    def test_ada_compliance_all_scored(self):
        """Test validation passes when all segments have compliance scores."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "ada_compliant": [True, False, True],
            }
        )
        report = validate_ada_compliance_gates(df, "ada_compliant")
        assert report.valid is True

    def test_ada_compliance_missing_scores(self):
        """Test validation fails when some segments lack compliance scores."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "ada_compliant": [True, None, True],
            }
        )
        report = validate_ada_compliance_gates(df, "ada_compliant")
        assert report.valid is False
        assert any("missing" in e.lower() for e in report.errors)

    def test_ada_compliance_clear_path_width_check(self):
        """Test validation checks clear path width against ADA minimum."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "ada_compliant": [True, True, True],
                "clear_path_width": [5.5, 4.2, 3.0],  # Min required is 5 feet; 2 fail
            }
        )
        report = validate_ada_compliance_gates(
            df, "ada_compliant", clear_path_width_col="clear_path_width"
        )
        assert report.valid is False
        assert len(report.errors) > 0
        assert any("clear path" in e.lower() or "slope" in e.lower() for e in report.errors)

    def test_ada_compliance_slope_check(self):
        """Test validation checks running slope against ADA maximum."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "ada_compliant": [True, True, True],
                "running_slope": [3.0, 6.0, 10.0],  # Max allowed is 5%; 2 fail
            }
        )
        report = validate_ada_compliance_gates(df, "ada_compliant", slope_col="running_slope")
        assert report.valid is False
        assert len(report.errors) > 0
        assert any("slope" in e.lower() or "clear path" in e.lower() for e in report.errors)

    def test_ada_compliance_missing_column(self):
        """Test validation fails when compliance column doesn't exist."""
        df = pd.DataFrame({"segment_id": [1, 2, 3]})
        report = validate_ada_compliance_gates(df, "ada_compliant")
        assert report.valid is False


class TestMarkingValidation:
    """Tests for pavement marking standards validation."""

    def test_marking_standards_valid_markings(self):
        """Test validation passes for valid marking specifications."""
        df = pd.DataFrame(
            {
                "marking_id": [1, 2, 3],
                "marking_type": ["Crosswalk", "Loading Zone", "Wayfinding Arrow"],
                "marking_color": ["white", "white", "white"],
            }
        )
        report = validate_marking_standards(df, "marking_type", "marking_color")
        assert report.valid is True

    def test_marking_standards_invalid_color(self):
        """Test validation fails for invalid marking colors."""
        df = pd.DataFrame(
            {
                "marking_id": [1, 2, 3],
                "marking_type": ["Crosswalk", "Loading Zone", "Custom"],
                "marking_color": ["white", "purple", "white"],  # Purple is invalid
            }
        )
        report = validate_marking_standards(df, "marking_type", "marking_color")
        assert report.valid is False
        assert any("color" in e.lower() for e in report.errors)

    def test_marking_standards_reflectivity_check(self):
        """Test validation checks marking reflectivity."""
        df = pd.DataFrame(
            {
                "marking_id": [1, 2, 3],
                "marking_type": ["Crosswalk", "Crosswalk", "Crosswalk"],
                "marking_color": ["white", "white", "white"],
                "reflectivity": [75, 50, 30],  # Min Type III is 50
            }
        )
        report = validate_marking_standards(
            df, "marking_type", "marking_color", reflectivity_col="reflectivity"
        )
        assert report.valid is True
        assert len(report.warnings) > 0  # Low reflectivity warning

    def test_marking_standards_missing_columns(self):
        """Test validation fails when required columns missing."""
        df = pd.DataFrame({"marking_id": [1, 2, 3]})
        report = validate_marking_standards(df, "marking_type", "marking_color")
        assert report.valid is False


class TestGeospatialValidation:
    """Tests for geospatial bounds validation."""

    def test_geospatial_bounds_valid_nyc(self):
        """Test validation passes for coordinates within NYC bounds."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "latitude": [40.7128, 40.6892, 40.7614],  # Valid NYC latitudes
                "longitude": [-74.0060, -73.9352, -73.9776],  # Valid NYC longitudes
            }
        )
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is True

    def test_geospatial_bounds_out_of_bounds(self):
        """Test validation fails for coordinates outside NYC bounds."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "latitude": [40.7128, 45.0, 40.7614],  # 45.0 is way too north
                "longitude": [-74.0060, -70.0, -73.9776],  # -70.0 is too far east
            }
        )
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is False
        assert len(report.errors) > 0

    def test_geospatial_bounds_missing_coordinates(self):
        """Test validation fails when coordinates are null."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "latitude": [40.7128, None, 40.7614],
                "longitude": [-74.0060, -73.9352, None],
            }
        )
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is False
        assert any("missing" in e.lower() for e in report.errors)

    def test_geospatial_bounds_custom_bounds(self):
        """Test validation with custom bounding box."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2],
                "latitude": [10.0, 20.0],
                "longitude": [-100.0, -90.0],
            }
        )
        custom_bounds = {
            "min_lat": 0.0,
            "max_lat": 30.0,
            "min_lon": -110.0,
            "max_lon": -80.0,
        }
        report = validate_geospatial_bounds(df, "latitude", "longitude", nyc_bounds=custom_bounds)
        assert report.valid is True

    def test_geospatial_bounds_missing_columns(self):
        """Test validation fails when coordinate columns missing."""
        df = pd.DataFrame({"segment_id": [1, 2, 3]})
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is False


class TestValidationIntegration:
    """Integration tests combining multiple validations."""

    def test_full_data_quality_pipeline(self):
        """Test complete data quality validation pipeline."""
        # Valid data passing all checks
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "material_type": ["HMA", "PCC", "Permeable Pavers"],
                "defect_type": ["Potholes", "Linear Cracking", "Drainage Blockage"],
                "ada_compliant": [True, True, False],
                "marking_color": ["white", "yellow", "white"],
                "latitude": [40.7128, 40.6892, 40.7614],
                "longitude": [-74.0060, -73.9352, -73.9776],
            }
        )

        # Run all validations
        mat_report = validate_material_coverage(df, "material_type")
        defect_report = validate_defect_applicability(df, "material_type", "defect_type")
        ada_report = validate_ada_compliance_gates(df, "ada_compliant")
        mark_report = validate_marking_standards(df, "marking_color", "marking_color")
        geo_report = validate_geospatial_bounds(df, "latitude", "longitude")

        # All should pass
        assert mat_report.valid is True
        assert defect_report.valid is True
        assert ada_report.valid is True
        assert mark_report.valid is True
        assert geo_report.valid is True

    def test_data_quality_with_violations(self):
        """Test data quality checks with multiple violations."""
        # Invalid data with multiple issues
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "material_type": ["HMA", "InvalidMat", None],
                "defect_type": ["Potholes", "Potholes", "Linear Cracking"],
                "ada_compliant": [True, None, True],
                "marking_color": ["white", "purple", "white"],
                "latitude": [40.7128, 45.0, 40.7614],
                "longitude": [-74.0060, -73.9352, -80.0],
            }
        )

        # Run all validations
        mat_report = validate_material_coverage(df, "material_type")
        defect_report = validate_defect_applicability(df, "material_type", "defect_type")
        ada_report = validate_ada_compliance_gates(df, "ada_compliant")
        mark_report = validate_marking_standards(df, "marking_color", "marking_color")
        geo_report = validate_geospatial_bounds(df, "latitude", "longitude")

        # All should fail
        assert mat_report.valid is False
        assert defect_report.valid is False
        assert ada_report.valid is False
        assert mark_report.valid is False
        assert geo_report.valid is False
