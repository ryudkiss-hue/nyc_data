"""
Validation Framework - NYC DOT Sidewalk Toolkit

Provides comprehensive data quality validation including:
- Material classification enforcement (per NYC Street Design Manual Section 4)
- Defect-material applicability checks
- ADA compliance verification
- Pavement marking standards validation
- Geospatial bounds validation

All validations include detailed error messages and references to applicable standards.

Standards: Python 3.9+, type hints, comprehensive docstrings, operational logging
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class ValidationReport:
    """Result of a validation check with detailed error and warning information.

    Attributes:
        valid: True if validation passed with no errors
        errors: List of validation error messages (blocking issues)
        warnings: List of validation warnings (non-blocking but important)
        affected_records: Number of records that failed validation
    """

    valid: bool
    errors: list[str]
    warnings: list[str]
    affected_records: int = 0

# NYC Street Design Manual Material Classifications (Section 4)
VALID_MATERIALS = {
    "Hot Mix Asphalt (HMA)",
    "Stone Matrix Asphalt (SMA)",
    "Open-Graded Friction Course (OGFC)",
    "Portland Cement Concrete (PCC)",
    "Reinforced Concrete Slabs",
    "Decorative Concrete",
    "Permeable Pavers",
    "Pervious Concrete",
    "Granite Block Pavement",
    "Vitreous Tile",
    "Red Asphalt (Traffic Calming)",
    "Green Asphalt (Permeable)",
    "HMA",
    "PCC",
    "asphalt",
    "concrete",
}

# Material categories per SDM
MATERIAL_CATEGORIES = {
    "asphalt": {"HMA", "SMA", "OGFC"},
    "concrete": {"PCC", "Reinforced Concrete", "Decorative Concrete"},
    "permeable_surfaces": {"Pavers", "Pervious Concrete", "Permeable Pavers"},
    "specialty": {"Granite Block", "Vitreous Tile"},
    "color_treatments": {"Red Asphalt", "Green Asphalt"},
}

# Defect applicability matrix (defect_type -> applicable_materials)
DEFECT_APPLICABILITY = {
    "Potholes": {"asphalt", "SMA", "OGFC"},
    "Linear Cracking": {"concrete", "PCC"},
    "Alligator Cracking": {"asphalt", "SMA"},
    "Spalling": {"concrete", "decorative", "asphalt"},
    "Heaving/Settlement": {"concrete", "pavers", "all"},
    "Rutting": {"asphalt", "SMA"},
    "Loose Pavers": {"pavers", "granite", "tile"},
    "Drainage Blockage": {"permeable_surfaces"},
    "Accessible Route Gap": "all",
    "Faded Markings": "all",
}

# ADA Compliance Requirements Reference
ADA_REQUIREMENTS = {
    "clear_path_width": {"min_feet": 5.0, "sdm_ref": "Section 2"},
    "running_slope": {"max_ratio": 1 / 20, "max_percent": 5.0, "sdm_ref": "Section 2"},
    "level_change": {"max_inches": 0.5, "sdm_ref": "Section 2"},
    "slip_resistance": {"min_coefficient": 0.5, "sdm_ref": "Section 4"},
    "tactile_strip": {"required": True, "depth_inches": 24, "sdm_ref": "Section 3"},
    "curb_ramp_width": {"min_feet": 4.0, "sdm_ref": "Section 3"},
    "curb_ramp_slope": {"max_ratio": 1 / 12, "max_percent": 8.33, "sdm_ref": "Section 3"},
}

def validate_required_columns(df: pd.DataFrame, required: list[str]) -> ValidationReport:
    """Validate that DataFrame contains all required columns.

    Args:
        df: Input DataFrame
        required: List of column names that must be present

    Returns:
        ValidationReport with any missing columns listed as errors

    Example:
        >>> df = pd.DataFrame({"id": [1, 2], "value": [10, 20]})
        >>> report = validate_required_columns(df, ["id", "value", "status"])
        >>> print(report.errors)
        ['Missing required column: status']
    """
    missing = [c for c in required if c not in df.columns]
    errors = [f"Missing required column: {c}" for c in missing]
    return ValidationReport(valid=not errors, errors=errors, warnings=[])

def validate_schema_types(df: pd.DataFrame, schema: dict[str, str]) -> ValidationReport:
    """Validate DataFrame column types against expected schema.

    Args:
        df: Input DataFrame
        schema: Dict mapping column name to expected dtype string

    Returns:
        ValidationReport with dtype mismatches as warnings

    Example:
        >>> df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        >>> schema = {"id": "int64", "name": "object"}
        >>> report = validate_schema_types(df, schema)
        >>> print(report.valid)
        True
    """
    errors: list[str] = []
    warns: list[str] = []
    for c, expected in schema.items():
        if c not in df.columns:
            errors.append(f"Missing expected column: {c}")
            continue
        actual = str(df[c].dtype)

        # Check for compatibility
        is_compatible = False
        if expected in actual:
            is_compatible = True
        elif expected == "int64" and "int" in actual:
            is_compatible = True
        elif expected in ("float", "float64") and "float" in actual:
            is_compatible = True
        elif expected in ("float", "float64") and "int" in actual:
            warns.append(f"Column {c}: expected {expected}, got {actual}")
            is_compatible = True
        elif expected == "object" and "str" in actual:
            is_compatible = True
        else:
            warns.append(f"Column {c}: expected {expected}, got {actual}")
    hard_type_mismatch = any(
        "got object" in w or "got string" in w or "got str" in w for w in warns
    )
    return ValidationReport(
        valid=not errors and not hard_type_mismatch,
        errors=errors,
        warnings=warns,
    )

def validate_material_coverage(
    df: pd.DataFrame, material_col: str = "material_type"
) -> ValidationReport:
    """Validate that all segments have valid material classification.

    Enforces that all sidewalk segments are assigned to a valid material type
    per NYC Street Design Manual Section 4 classifications.

    Args:
        df: Sidewalk segments DataFrame
        material_col: Column name containing material type

    Returns:
        ValidationReport with invalid or missing material assignments

    Example:
        >>> df = pd.DataFrame({
        ...     "segment_id": [1, 2, 3],
        ...     "material_type": ["HMA", "PCC", "unknown"]
        ... })
        >>> report = validate_material_coverage(df, "material_type")
        >>> print(len(report.errors))
        1
    """
    if material_col not in df.columns:
        return ValidationReport(
            valid=False,
            errors=[f"Material column '{material_col}' not found"],
            warnings=[],
        )

    # Check for null materials
    null_mask = df[material_col].isna()
    null_count = null_mask.sum()

    # Check for invalid materials
    invalid_mask = ~df[material_col].isin(VALID_MATERIALS) & ~null_mask
    invalid_count = invalid_mask.sum()

    errors: list[str] = []
    affected = null_count + invalid_count

    if null_count > 0:
        errors.append(
            f"SDM Section 4: {null_count} segments missing material classification"
        )

    if invalid_count > 0:
        invalid_materials = df[invalid_mask][material_col].unique().tolist()
        errors.append(
            f"SDM Section 4: {invalid_count} segments with invalid materials: {invalid_materials}"
        )

    logger.info(
        f"Material coverage validation: {len(df) - affected}/{len(df)} segments valid"
    )

    return ValidationReport(
        valid=not errors, errors=errors, warnings=[], affected_records=affected
    )

def validate_defect_applicability(
    df: pd.DataFrame,
    material_col: str = "material_type",
    defect_col: str = "defect_type",
) -> ValidationReport:
    """Validate that defect types only apply to applicable materials.

    Cross-checks defect assignments against the material applicability matrix
    to ensure data quality and prevent invalid repair specifications.

    Args:
        df: Defect records DataFrame
        material_col: Column name for material type
        defect_col: Column name for defect type

    Returns:
        ValidationReport with applicability mismatches

    Example:
        >>> df = pd.DataFrame({
        ...     "defect_id": [1, 2],
        ...     "material_type": ["PCC", "asphalt"],
        ...     "defect_type": ["Potholes", "Linear Cracking"]
        ... })
        >>> report = validate_defect_applicability(df, "material_type", "defect_type")
        >>> print(len(report.errors))
        1  # "Potholes" doesn't apply to PCC
    """
    missing_cols = [c for c in [material_col, defect_col] if c not in df.columns]
    if missing_cols:
        return ValidationReport(
            valid=False,
            errors=[f"Required columns missing: {missing_cols}"],
            warnings=[],
        )

    errors: list[str] = []
    invalid_count = 0

    for idx, row in df.iterrows():
        material = row[material_col]
        defect = row[defect_col]

        if pd.isna(defect):
            continue

        if pd.isna(material):
            errors.append(f"Row {idx}: Defect '{defect}' present but material is missing")
            invalid_count += 1
            continue

        applicable = DEFECT_APPLICABILITY.get(defect)
        if applicable is None:
            errors.append(f"Unknown defect type: {defect}")
            continue

        if applicable != "all":
            # Check if material itself is in applicable set
            # Or if material belongs to a category that is in applicable set
            is_valid = material in applicable
            if not is_valid:
                for category, members in MATERIAL_CATEGORIES.items():
                    if category in applicable and material in members:
                        is_valid = True
                        break

            # Special case for "concrete" category members
            if not is_valid and "concrete" in applicable and "PCC" in material:
                 is_valid = True

            if not is_valid:
                errors.append(
                    f"Row {idx}: Defect '{defect}' not applicable to material '{material}'"
                )
                invalid_count += 1

    if invalid_count > 0:
        logger.warning(
            f"Defect applicability: {invalid_count} invalid defect-material pairs detected"
        )

    return ValidationReport(
        valid=not errors, errors=errors, warnings=[], affected_records=int(invalid_count)
    )

def validate_ada_compliance_gates(
    df: pd.DataFrame,
    ada_compliance_col: str = "ada_compliant",
    clear_path_width_col: str | None = None,
    slope_col: str | None = None,
) -> ValidationReport:
    """Validate ADA compliance gates and scoring.

    Checks that all segments have been scored for ADA compliance and that
    reported compliance aligns with measured parameters per ADA guidelines.

    Args:
        df: Sidewalk segments DataFrame
        ada_compliance_col: Column with boolean/percentage compliance flag
        clear_path_width_col: Optional column with clear path width in feet
        slope_col: Optional column with running slope as percentage

    Returns:
        ValidationReport with compliance scoring issues

    Example:
        >>> df = pd.DataFrame({
        ...     "segment_id": [1, 2],
        ...     "ada_compliant": [True, None],
        ...     "clear_path_width": [5.5, 4.2]
        ... })
        >>> report = validate_ada_compliance_gates(df, "ada_compliant", "clear_path_width")
        >>> print(len(report.errors))
        1  # Segment 2 missing compliance score
    """
    if ada_compliance_col not in df.columns:
        return ValidationReport(
            valid=False,
            errors=[f"ADA compliance column '{ada_compliance_col}' not found"],
            warnings=[],
        )

    errors: list[str] = []
    warnings: list[str] = []

    # Check for missing compliance scores
    null_mask = df[ada_compliance_col].isna()
    null_count = null_mask.sum()

    if null_count > 0:
        errors.append(f"ADA-4.3: {null_count} segments missing compliance scoring")

    # Validate clear path width if provided
    if clear_path_width_col and clear_path_width_col in df.columns:
        min_width = ADA_REQUIREMENTS["clear_path_width"]["min_feet"]
        width_violation = df[clear_path_width_col] < min_width
        width_count = width_violation.sum()
        if width_count > 0:
            warnings.append(
                f"ADA-4.3.1: {width_count} segments below minimum {min_width}ft clear path width"
            )

    # Validate slope if provided
    if slope_col and slope_col in df.columns:
        max_slope = ADA_REQUIREMENTS["running_slope"]["max_percent"]
        slope_violation = df[slope_col] > max_slope
        slope_count = slope_violation.sum()
        if slope_count > 0:
            warnings.append(
                f"ADA-4.3.2: {slope_count} segments exceed maximum {max_slope}% running slope"
            )

    affected = null_count
    logger.info(f"ADA compliance validation: {len(df) - affected}/{len(df)} segments scored")

    return ValidationReport(
        valid=not errors, errors=errors, warnings=warnings, affected_records=affected
    )

def validate_marking_standards(
    df: pd.DataFrame,
    marking_col: str = "marking_type",
    color_col: str = "marking_color",
    reflectivity_col: str | None = None,
) -> ValidationReport:
    """Validate pavement marking standards per SDM Section 5.

    Ensures markings follow NYC DOT specifications for color, reflectivity,
    and visibility per SDM Section 5 standards.

    Args:
        df: Marking records DataFrame
        marking_col: Column with marking type
        color_col: Column with marking color
        reflectivity_col: Optional column with reflectivity measurement

    Returns:
        ValidationReport with marking standard violations

    Example:
        >>> df = pd.DataFrame({
        ...     "marking_id": [1, 2],
        ...     "marking_type": ["Crosswalk", "Loading Zone"],
        ...     "marking_color": ["white", "invalid"]
        ... })
        >>> report = validate_marking_standards(df, "marking_type", "marking_color")
        >>> print(len(report.errors))
        1
    """
    missing_cols = [c for c in [marking_col, color_col] if c not in df.columns]
    if missing_cols:
        return ValidationReport(
            valid=False,
            errors=[f"Required columns missing: {missing_cols}"],
            warnings=[],
        )

    # Valid marking colors per SDM Section 5
    valid_colors = {"white", "yellow", "blue", "red"}

    errors: list[str] = []
    warnings: list[str] = []
    affected = 0

    # Validate marking colors
    invalid_colors = df[~df[color_col].isin(valid_colors)]
    if len(invalid_colors) > 0:
        errors.append(
            f"SDM Section 5: {len(invalid_colors)} markings with invalid colors"
        )
        affected += len(invalid_colors)

    # Check reflectivity if provided
    if reflectivity_col and reflectivity_col in df.columns:
        # Type III minimum is approximately 50% reflectivity
        min_reflectivity = 50
        low_reflectivity = df[df[reflectivity_col] < min_reflectivity]
        if len(low_reflectivity) > 0:
            warnings.append(
                f"SDM Section 5: {len(low_reflectivity)} markings below Type III reflectivity minimum"
            )

    logger.info(f"Marking standards validation: {len(df) - affected}/{len(df)} compliant")

    return ValidationReport(
        valid=not errors, errors=errors, warnings=warnings, affected_records=affected
    )

def validate_geospatial_bounds(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    nyc_bounds: dict[str, float] | None = None,
) -> ValidationReport:
    """Validate that all coordinates fall within NYC bounds.

    Checks geospatial validity (coordinates within NYC, no topology errors).
    NYC bounds default: 40.4774° to 40.9176° N, -74.2591° to -73.7004° W

    Args:
        df: Segments with geospatial data
        lat_col: Latitude column name
        lon_col: Longitude column name
        nyc_bounds: Optional custom bounds dict with keys: min_lat, max_lat, min_lon, max_lon

    Returns:
        ValidationReport with out-of-bounds records

    Example:
        >>> df = pd.DataFrame({
        ...     "segment_id": [1, 2],
        ...     "latitude": [40.7, 45.0],
        ...     "longitude": [-73.9, -70.0]
        ... })
        >>> report = validate_geospatial_bounds(df, "latitude", "longitude")
        >>> print(len(report.errors))
        2  # Both records outside NYC bounds
    """
    # Default NYC bounds
    if nyc_bounds is None:
        nyc_bounds = {
            "min_lat": 40.4774,
            "max_lat": 40.9176,
            "min_lon": -74.2591,
            "max_lon": -73.7004,
        }

    missing_cols = [c for c in [lat_col, lon_col] if c not in df.columns]
    if missing_cols:
        return ValidationReport(
            valid=False,
            errors=[f"Geospatial columns missing: {missing_cols}"],
            warnings=[],
        )

    errors: list[str] = []
    affected = 0

    # Check latitude bounds
    lat_out = (df[lat_col] < nyc_bounds["min_lat"]) | (
        df[lat_col] > nyc_bounds["max_lat"]
    )
    lat_count = lat_out.sum()
    if lat_count > 0:
        errors.append(f"{lat_count} records with invalid latitude (outside NYC bounds)")
        affected += lat_count

    # Check longitude bounds
    lon_out = (df[lon_col] < nyc_bounds["min_lon"]) | (
        df[lon_col] > nyc_bounds["max_lon"]
    )
    lon_count = lon_out.sum()
    if lon_count > 0:
        errors.append(f"{lon_count} records with invalid longitude (outside NYC bounds)")
        affected += lon_count

    # Check for null coordinates
    null_coords = df[lat_col].isna() | df[lon_col].isna()
    null_count = null_coords.sum()
    if null_count > 0:
        errors.append(f"{null_count} records with missing geospatial coordinates")
        affected += null_count

    logger.info(f"Geospatial validation: {len(df) - affected}/{len(df)} within NYC bounds")

    return ValidationReport(
        valid=not errors, errors=errors, warnings=[], affected_records=affected
    )
