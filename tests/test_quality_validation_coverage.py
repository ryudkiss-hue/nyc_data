"""Tests for quality.validation module - Data validation framework."""

from __future__ import annotations

import pandas as pd

from socrata_toolkit.quality.validation import (
    ValidationReport,
    validate_ada_compliance_gates,
    validate_defect_applicability,
    validate_geospatial_bounds,
    validate_marking_standards,
    validate_material_coverage,
    validate_required_columns,
    validate_schema_types,
)


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_validation_report_creation_valid(self):
        """Test creating a valid ValidationReport."""
        report = ValidationReport(valid=True, errors=[], warnings=[])
        assert report.valid is True
        assert report.errors == []
        assert report.warnings == []
        assert report.affected_records == 0

    def test_validation_report_creation_invalid(self):
        """Test creating an invalid ValidationReport."""
        report = ValidationReport(
            valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            affected_records=5,
        )
        assert report.valid is False
        assert len(report.errors) == 2
        assert len(report.warnings) == 1
        assert report.affected_records == 5


class TestValidateRequiredColumns:
    """Tests for validate_required_columns function."""

    def test_all_columns_present(self):
        """Test when all required columns are present."""
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})
        report = validate_required_columns(df, ["id", "name"])
        assert report.valid is True
        assert len(report.errors) == 0

    def test_missing_one_column(self):
        """Test when one required column is missing."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        report = validate_required_columns(df, ["id", "name"])
        assert report.valid is False
        assert len(report.errors) == 1
        assert "name" in report.errors[0]

    def test_missing_multiple_columns(self):
        """Test when multiple required columns are missing."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        report = validate_required_columns(df, ["id", "name", "age"])
        assert report.valid is False
        assert len(report.errors) == 2

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        report = validate_required_columns(df, ["id"])
        assert report.valid is False
        assert len(report.errors) == 1

    def test_no_required_columns(self):
        """Test with no required columns."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        report = validate_required_columns(df, [])
        assert report.valid is True
        assert len(report.errors) == 0


class TestValidateSchemaTypes:
    """Tests for validate_schema_types function."""

    def test_all_types_match(self):
        """Test when all types match expected schema."""
        df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        schema = {"id": "int64", "name": "object"}
        report = validate_schema_types(df, schema)
        assert report.valid is True

    def test_int_type_variation(self):
        """Test int32 vs int64 compatibility."""
        df = pd.DataFrame({"id": pd.array([1, 2], dtype="int32")})
        schema = {"id": "int64"}
        report = validate_schema_types(df, schema)
        assert report.valid is True

    def test_missing_column_in_schema(self):
        """Test when schema expects column not in DataFrame."""
        df = pd.DataFrame({"id": [1, 2]})
        schema = {"id": "int64", "name": "object"}
        report = validate_schema_types(df, schema)
        assert report.valid is False
        assert any("name" in e for e in report.errors)

    def test_object_string_compatibility(self):
        """Test object vs string type compatibility."""
        df = pd.DataFrame({"name": ["a", "b"]})
        schema = {"name": "object"}
        report = validate_schema_types(df, schema)
        assert report.valid is True


class TestValidateMaterialCoverage:
    """Tests for validate_material_coverage function."""

    def test_all_valid_materials(self):
        """Test when all materials are valid."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "material_type": ["HMA", "PCC", "asphalt"],
            }
        )
        report = validate_material_coverage(df, "material_type")
        assert report.valid is True
        assert len(report.errors) == 0

    def test_invalid_material(self):
        """Test when segment has invalid material."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2],
                "material_type": ["HMA", "unknown_material"],
            }
        )
        report = validate_material_coverage(df, "material_type")
        assert report.valid is False
        assert len(report.errors) == 1

    def test_null_material(self):
        """Test when segment has null material."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2],
                "material_type": ["HMA", None],
            }
        )
        report = validate_material_coverage(df, "material_type")
        assert report.valid is False
        assert len(report.errors) == 1

    def test_missing_material_column(self):
        """Test when material column is missing."""
        df = pd.DataFrame({"segment_id": [1, 2]})
        report = validate_material_coverage(df, "material_type")
        assert report.valid is False
        assert "not found" in report.errors[0]


class TestValidateDefectApplicability:
    """Tests for validate_defect_applicability function."""

    def test_valid_defect_material_pair(self):
        """Test when defect-material pair is valid."""
        df = pd.DataFrame(
            {
                "defect_id": [1],
                "material_type": ["asphalt"],
                "defect_type": ["Potholes"],
            }
        )
        report = validate_defect_applicability(df, "material_type", "defect_type")
        assert report.valid is True

    def test_invalid_defect_material_pair(self):
        """Test when defect doesn't apply to material."""
        df = pd.DataFrame(
            {
                "defect_id": [1],
                "material_type": ["PCC"],
                "defect_type": ["Potholes"],
            }
        )
        report = validate_defect_applicability(df, "material_type", "defect_type")
        assert report.valid is False
        assert len(report.errors) >= 1

    def test_missing_material_column(self):
        """Test when material column is missing."""
        df = pd.DataFrame({"defect_id": [1], "defect_type": ["Potholes"]})
        report = validate_defect_applicability(df, "material_type", "defect_type")
        assert report.valid is False


class TestValidateADAComplianceGates:
    """Tests for validate_ada_compliance_gates function."""

    def test_all_segments_scored(self):
        """Test when all segments have compliance scores."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "ada_compliant": [True, False, True],
            }
        )
        report = validate_ada_compliance_gates(df, "ada_compliant")
        assert report.valid is True

    def test_missing_compliance_score(self):
        """Test when some segments lack compliance scores."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "ada_compliant": [True, None, False],
            }
        )
        report = validate_ada_compliance_gates(df, "ada_compliant")
        assert report.valid is False
        assert len(report.errors) >= 1

    def test_missing_ada_column(self):
        """Test when ada_compliant column is missing."""
        df = pd.DataFrame({"segment_id": [1, 2]})
        report = validate_ada_compliance_gates(df, "ada_compliant")
        assert report.valid is False


class TestValidateMarkingStandards:
    """Tests for validate_marking_standards function."""

    def test_valid_marking_colors(self):
        """Test when all markings have valid colors."""
        df = pd.DataFrame(
            {
                "marking_id": [1, 2, 3],
                "marking_type": ["Crosswalk", "Stop Line", "Arrow"],
                "marking_color": ["white", "white", "yellow"],
            }
        )
        report = validate_marking_standards(df, "marking_type", "marking_color")
        assert report.valid is True

    def test_invalid_marking_color(self):
        """Test when marking has invalid color."""
        df = pd.DataFrame(
            {
                "marking_id": [1, 2],
                "marking_type": ["Crosswalk", "Arrow"],
                "marking_color": ["white", "purple"],
            }
        )
        report = validate_marking_standards(df, "marking_type", "marking_color")
        assert report.valid is False
        assert len(report.errors) >= 1

    def test_missing_marking_column(self):
        """Test when marking column is missing."""
        df = pd.DataFrame({"marking_id": [1, 2], "marking_color": ["white", "yellow"]})
        report = validate_marking_standards(df, "marking_type", "marking_color")
        assert report.valid is False


class TestValidateGeospatialBounds:
    """Tests for validate_geospatial_bounds function."""

    def test_coordinates_within_nyc_bounds(self):
        """Test when all coordinates are within NYC."""
        df = pd.DataFrame(
            {
                "segment_id": [1, 2, 3],
                "latitude": [40.7, 40.8, 40.6],
                "longitude": [-73.9, -73.8, -74.0],
            }
        )
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is True

    def test_latitude_out_of_bounds_high(self):
        """Test when latitude is too high."""
        df = pd.DataFrame(
            {
                "segment_id": [1],
                "latitude": [41.0],
                "longitude": [-73.9],
            }
        )
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is False
        assert len(report.errors) >= 1

    def test_longitude_out_of_bounds_high(self):
        """Test when longitude is too high."""
        df = pd.DataFrame(
            {
                "segment_id": [1],
                "latitude": [40.7],
                "longitude": [-73.0],
            }
        )
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is False

    def test_missing_latitude_column(self):
        """Test when latitude column is missing."""
        df = pd.DataFrame({"segment_id": [1, 2], "longitude": [-73.9, -73.8]})
        report = validate_geospatial_bounds(df, "latitude", "longitude")
        assert report.valid is False
