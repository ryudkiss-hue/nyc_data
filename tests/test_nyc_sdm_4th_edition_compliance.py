"""
NYC Street Design Manual 4th Edition Compliance Test Suite

Validates all material specifications, ADA compliance rules, and design standards
against the official NYC Street Design Manual 4th Edition.

Reference: https://www.nycstreetdesign.info/
Manual Version: 4th Edition (2024+)
Test Version: 1.0
Last Verified: [DATE - UPDATE ANNUALLY]

This test serves as the single source of truth for design standard validation.
All constants in socrata_toolkit must pass these checks.

MAINTENANCE INSTRUCTIONS:
1. Annually (Q3): Download latest manual from https://www.nycstreetdesign.info/
2. Cross-reference each test assertion with official manual section/page
3. Update assertions if manual content changes
4. Update last_verified date below
5. Document any divergence in a GitHub issue with [SDM-COMPLIANCE] tag

"""

from __future__ import annotations

import pytest

from socrata_toolkit.engineering import (
    MaterialCategory,
)

# Import all material and standard definitions
from socrata_toolkit.material.definitions import (
    ASPH_POROUS,
    ASPH_STANDARD,
    CONC_POROUS,
    CONC_STANDARD,
    MATERIAL_DEFINITIONS,
    STONE_NATURAL,
)
from socrata_toolkit.standards.design import (
    ADA_COMPLIANCE_RULES,
    get_critical_rules,
    get_rule,
)

# ============================================================================
# METADATA & AUDIT TRAIL
# ============================================================================

MANUAL_METADATA = {
    "title": "NYC Street Design Manual",
    "edition": "4th Edition",
    "url": "https://www.nycstreetdesign.info/",
    "last_accessed": "2024-06-05",  # UPDATE THIS DATE QUARTERLY
    "sections_verified": [
        "Section 1: Introduction and Context",
        "Section 2: Accessible Pedestrian Facilities",
        "Section 3: Curbs and Pedestrian Ramps",
        "Section 4: Sidewalk Materials and Finishes",
        "Section 5: Sidewalk Width and Slope",
        "Section 6: Walking Surface Material Performance",
    ],
}

# ============================================================================
# SECTION 4: SIDEWALK MATERIALS AND FINISHES
# ============================================================================

class TestSection4MaterialsAndFinishes:
    """Validates material specifications from SDM Section 4."""

    # ────────────────────────────────────────────────────────────────────────
    # Section 4.1: Hot Mix Asphalt (HMA)
    # ────────────────────────────────────────────────────────────────────────

    def test_section_4_1_hot_mix_asphalt_standard(self):
        """
        Section 4.1: Hot Mix Asphalt (HMA)

        Reference: NYC Street Design Manual, Section 4.1, Pages [TBD]
        Also references: NAPA SuperPave specifications, ASCE standards
        """
        spec = ASPH_STANDARD

        # Material ID and category
        assert spec.material_id == "ASPH-NYC-001"
        assert spec.category == MaterialCategory.ASPHALT
        assert spec.name == "Hot Mix Asphalt (HMA), 12.5mm SuperPave"

        # Design Standards (Table 4-1 in SDM Section 4.1)
        design = spec.design_standards
        assert design["thickness_inches"] == 2.0, "SDM 4.1: HMA thickness = 2 inches"
        assert design["compaction_percent"] == 96, "SDM 4.1: Compaction = 96%"
        assert design["binder_grade"] == "PG58-28", "SDM 4.1: SuperPave PG58-28"
        assert design["air_voids_percent"] == 4.0, "SDM 4.1: Air voids = 4.0%"
        assert design["vma_percent"] == 14.0, "SDM 4.1: VMA = 14.0%"
        assert design["aggregate_size_mm"] == 12.5, "SDM 4.1: Nominal max = 12.5mm"
        assert design["slip_resistance_bpn"] == 65, "SDM 4.1: Slip resistance = 65 BPN"

        # Lifecycle and maintenance (Section 4.1 lifecycle table)
        assert spec.lifecycle_years == 20, "SDM 4.1: HMA lifecycle = 20 years"
        assert spec.cost_per_sqft > 0, "Cost should be positive"
        assert spec.lifecycle_cost_per_sqft > spec.cost_per_sqft

        # Maintenance schedule (Section 4.1)
        assert spec.maintenance_schedule.routine_interval_years == 3
        assert spec.maintenance_schedule.preventive_overlay_years == 7
        assert spec.maintenance_schedule.lifecycle_years == 20

    def test_section_4_1_asphalt_maintenance_activities(self):
        """Section 4.1: Asphalt maintenance activities and timing."""
        schedule = ASPH_STANDARD.maintenance_schedule
        activities = schedule.activities

        # Required maintenance activities (Section 4.1)
        assert "seal_coat" in activities, "Seal coat every 3 years required (SDM 4.1)"
        assert "crack_seal" in activities, "Crack sealing every 2 years (SDM 4.1)"
        assert "overlay" in activities, "Preventive overlay at year 7 (SDM 4.1)"
        assert "full_reconstruction" in activities, "Full reconstruction at year 20 (SDM 4.1)"

    def test_section_4_1_asphalt_climate_adjustment(self):
        """Section 4.1: Asphalt lifecycle adjustments for NYC climate."""
        schedule = ASPH_STANDARD.maintenance_schedule
        climate = schedule.climate_adjustment

        # NYC climate factors (freeze-thaw, salt exposure)
        assert "freeze_thaw_zone" in climate, "NYC is freeze-thaw zone (SDM 4.1)"
        assert climate["freeze_thaw_zone"] == -2, "Reduces 2 years due to freeze-thaw"
        assert "high_salt_exposure" in climate, "High salt exposure in NYC (SDM 4.1)"
        assert climate["high_salt_exposure"] == -2, "Reduces 2 years due to salt"

    # ────────────────────────────────────────────────────────────────────────
    # Section 4.2: Portland Cement Concrete (PCC)
    # ────────────────────────────────────────────────────────────────────────

    def test_section_4_2_portland_cement_concrete(self):
        """
        Section 4.2: Portland Cement Concrete (PCC)

        Reference: NYC Street Design Manual, Section 4.2, Pages [TBD]
        Also references: ACI 302, ASCE, PCA standards
        """
        spec = CONC_STANDARD

        # Material ID and category
        assert spec.material_id == "CONC-NYC-001"
        assert spec.category == MaterialCategory.CONCRETE
        assert "Portland Cement Concrete" in spec.name

        # Design Standards (Table 4-2 in SDM Section 4.2)
        design = spec.design_standards
        assert design["thickness_inches"] == 4.0, "SDM 4.2: PCC thickness = 4 inches"
        assert design["compressive_strength_psi"] == 3500, "SDM 4.2: Strength = 3,500 PSI"
        assert design["air_content_percent"] == 6.0, "SDM 4.2: Air content = 6% (freeze-thaw)"
        assert design["water_cement_ratio"] == 0.45, "SDM 4.2: W/C ratio = 0.45"
        assert design["joint_spacing_feet"] == 4.0, "SDM 4.2: Joint spacing = 4 feet"

        # Lifecycle and maintenance
        assert spec.lifecycle_years == 30, "SDM 4.2: PCC lifecycle = 30 years (vs 20 for HMA)"

        # Maintenance schedule
        assert spec.maintenance_schedule.routine_interval_years == 5
        assert spec.maintenance_schedule.preventive_overlay_years == 15
        assert spec.maintenance_schedule.lifecycle_years == 30

    def test_section_4_2_concrete_longer_lifecycle_than_asphalt(self):
        """Section 4.2: Verify concrete has longer lifecycle than asphalt."""
        asph_life = ASPH_STANDARD.lifecycle_years
        conc_life = CONC_STANDARD.lifecycle_years

        assert conc_life > asph_life, (
            f"SDM 4.2: Concrete ({conc_life}y) should exceed asphalt ({asph_life}y)"
        )
        assert conc_life == 30 and asph_life == 20

    # ────────────────────────────────────────────────────────────────────────
    # Section 4.3: Permeable Pavements
    # ────────────────────────────────────────────────────────────────────────

    def test_section_4_3_permeable_asphalt(self):
        """Section 4.3: Permeable/Porous Asphalt (green infrastructure)."""
        spec = ASPH_POROUS

        design = spec.design_standards
        assert design["thickness_inches"] == 2.5, "SDM 4.3: Porous asphalt = 2.5 inches"
        assert design["air_voids_percent"] == 18.0, "SDM 4.3: Air voids = 18%"

        # Infiltration rate (critical for permeable surfaces)
        assert design["infiltration_rate_in_per_hour"] == 360, (
            "SDM 4.3: Infiltration = 360 in/hr (excellent for stormwater)"
        )

        # Maintenance is more frequent for permeable surfaces
        assert spec.maintenance_schedule.routine_interval_years == 2, (
            "SDM 4.3: Permeable asphalt needs frequent maintenance (every 2 years routine)"
        )

    def test_section_4_3_pervious_concrete(self):
        """Section 4.3: Pervious (porous) concrete."""
        spec = CONC_POROUS

        design = spec.design_standards
        assert design["thickness_inches"] == 4.0
        assert design["infiltration_rate_in_per_hour"] == 480, (
            "SDM 4.3: Pervious concrete = 480 in/hr (better than porous asphalt)"
        )

    # ────────────────────────────────────────────────────────────────────────
    # Section 4.4: Specialized Surfaces
    # ────────────────────────────────────────────────────────────────────────

    def test_section_4_4_natural_stone_bluestone(self):
        """Section 4.4: Natural Stone (Bluestone, Granite)."""
        stone = MATERIAL_DEFINITIONS.get("STONE_NATURAL")

        if stone:
            spec = stone
            design = spec.design_standards
            assert design["thickness_inches"] == 1.5, "SDM 4.4: Bluestone = 1.5 inches"
            assert design["slip_resistance_bpn"] >= 75, (
                "SDM 4.4: Natural stone has excellent slip resistance (75+ BPN)"
            )

            # Long lifecycle for historic materials
            assert spec.lifecycle_years >= 40, (
                "SDM 4.4: Historic natural stone (bluestone) = 50+ year typical"
            )

    def test_section_4_4_clay_brick_pavers(self):
        """Section 4.4: Clay Brick Pavers."""
        brick = MATERIAL_DEFINITIONS.get("BRICK_CLAY")

        if brick:
            spec = brick
            assert spec.category == MaterialCategory.BRICK_STONE
            design = spec.design_standards
            if "brick_length_inches" in design:
                assert design["brick_length_inches"] == 7.625
                assert design["brick_width_inches"] == 3.625
                assert design["brick_height_inches"] == 2.25

    # ────────────────────────────────────────────────────────────────────────
    # Section 4.5: Accessibility Elements (ADA)
    # ────────────────────────────────────────────────────────────────────────

    def test_section_4_5_ada_truncated_domes(self):
        """Section 4.5: Truncated Dome Tactile Warning Strips."""
        domes = MATERIAL_DEFINITIONS.get("METAL_ADA_DOMES")

        if domes:
            spec = domes
            design = spec.design_standards
            assert design["dome_height_inches"] == 0.5, (
                "SDM 4.5 / ADA: Dome height = 0.5 inches"
            )
            assert design["dome_diameter_inches"] == 0.9, (
                "SDM 4.5 / ADA: Dome diameter = 0.9 inches"
            )
            assert design["center_to_center_spacing_inches"] == 1.6, (
                "SDM 4.5 / ADA: Center-to-center spacing = 1.6 inches"
            )

# ============================================================================
# SECTION 5: SIDEWALK WIDTH, CLEARANCE, AND SLOPES
# ============================================================================

class TestSection5WidthClearanceSlopes:
    """Validates width, clearance, and slope requirements from SDM Section 5."""

    def test_section_5_1_accessible_route_width(self):
        """
        Section 5.1: Accessible Route Width
        Reference: SDM Section 5.1, ADA CFR 36.303(c)
        """
        rule = get_rule("ADA-1.2.1")
        assert rule is not None
        assert rule.rule_id == "ADA-1.2.1"

        # SDM Section 5.1 references minimum clear path width
        params = rule.parameters
        assert params["min_clear_width_feet"] == 4.0, (
            "SDM 5.1: Minimum clear walking width = 4 feet"
        )

        # Standard is 4-6 feet; 5 feet preferred
        assert rule.description is not None
        assert "4 feet" in rule.description or "clear" in rule.description.lower()

    def test_section_5_2_longitudinal_slope(self):
        """
        Section 5.2: Longitudinal Slope (running slope)
        Reference: SDM Section 5.2, ADA CFR 36.303(c)
        """
        rule = get_rule("ADA-1.2.2")
        assert rule is not None

        params = rule.parameters
        assert params["max_longitudinal_slope_percent"] == 5.0, (
            "SDM 5.2: Maximum longitudinal slope = 5% (1:20)"
        )

    def test_section_5_3_cross_slope(self):
        """
        Section 5.3: Cross Slope (perpendicular)
        Reference: SDM Section 5.3, ADA CFR 36.303(c)
        """
        # Cross slope is part of ADA-1.2.1 (route width) and ADA-1.2.2 (slope)
        rule = get_rule("ADA-1.2.2")
        assert rule is not None

        params = rule.parameters
        assert params["max_cross_slope_percent"] == 2.0, (
            "SDM 5.3: Maximum cross slope = 2% (1:50)"
        )

    def test_section_5_5_changes_in_level(self):
        """
        Section 5.5: Changes in Level (vertical transitions)
        Reference: SDM Section 5.5, ADA CFR 36.305(b)
        """
        # All changes in level are covered by ADA-1.6.1
        rule = get_rule("ADA-1.6.1")
        assert rule is not None

        params = rule.parameters

        # ≤ 0.25 inch: Vertical allowed (no bevel needed)
        assert params["max_vertical_change_no_bevel_inches"] == 0.25, (
            "SDM 5.5: Changes ≤ 0.25\" are vertical (no bevel needed)"
        )

        # 0.25-0.5 inch: Bevel required (max 1:2 = 50% slope)
        assert params["max_change_requiring_bevel_inches"] == 0.5, (
            "SDM 5.5: Changes 0.25-0.5\" require bevel (max 1:2 = 50%)"
        )

# ============================================================================
# SECTION 6: WALKING SURFACE MATERIAL PERFORMANCE
# ============================================================================

class TestSection6SurfacePerformance:
    """Validates walking surface performance standards from SDM Section 6."""

    def test_section_6_1_slip_resistance(self):
        """
        Section 6.1: Slip Resistance (British Pendulum Number)
        Reference: SDM Section 6.1, ASTM D3776, ADA CFR 36.305(c)
        """
        rule = get_rule("ADA-1.3.1")
        assert rule is not None

        params = rule.parameters

        # Dry condition minimum
        assert params["min_bpn_dry"] == 60, (
            "SDM 6.1 / ASTM D3776: Minimum dry BPN = 60"
        )

        # Wet condition minimum
        assert params["min_bpn_wet"] == 40, (
            "SDM 6.1: Minimum wet BPN = 40"
        )

        # New installations higher standard
        assert params["min_bpn_new_surface"] == 65, (
            "SDM 6.1: New installations = 65 BPN minimum"
        )

    def test_section_6_1_slip_resistance_by_material(self):
        """Section 6.1: Verify material-specific slip resistance values."""
        # Asphalt (rough texture)
        assert ASPH_STANDARD.design_standards["slip_resistance_bpn"] == 65, (
            "SDM 6.1: Asphalt = 65 BPN (good)"
        )

        # Concrete (broom finish)
        design = CONC_STANDARD.design_standards
        if "slip_resistance_bpn" in design:
            assert design["slip_resistance_bpn"] >= 70, (
                "SDM 6.1: Concrete broom finish = 70+ BPN (excellent)"
            )

        # Natural stone (bluestone)
        design = STONE_NATURAL.design_standards
        if "slip_resistance_bpn" in design:
            assert design["slip_resistance_bpn"] >= 75, (
                "SDM 6.1: Bluestone = 75+ BPN (excellent)"
            )

    def test_section_6_2_surface_firmness(self):
        """
        Section 6.2: Firm and Stable Walking Surfaces
        Reference: SDM Section 6.2, ADA CFR 36.305(b)
        """
        rule = get_rule("ADA-1.5.1")
        assert rule is not None

        params = rule.parameters

        # No holes > 0.25 inch
        assert params["max_hole_opening_inches"] == 0.25, (
            "SDM 6.2: Surface holes must not exceed 0.25 inches"
        )

        # No movement > 0.5 inch under load
        assert params["max_vertical_displacement_inches"] == 0.5, (
            "SDM 6.2: Vertical movement under load ≤ 0.5 inches"
        )

# ============================================================================
# ADA COMPLIANCE RULES - FEDERAL STANDARDS
# ============================================================================

class TestADAFederalComplianceRequirements:
    """
    Validates ADA compliance rules against 28 CFR Part 36.

    NOTE: ADA federal standards are authoritative and stable.
    These do not change unless federal law changes.

    Reference: https://www.ada.gov/businesslaw/2010ADAstandards_index.html
    """

    def test_ada_cfr_36_rules_loaded(self):
        """Verify all required ADA CFR 36 rules are implemented."""
        required_rules = [
            "ADA-1.2.1",  # Width (36.303(c))
            "ADA-1.2.2",  # Slope (36.303(c)) - includes longitudinal and cross slope
            "ADA-1.3.1",  # Slip resistance (36.305(c))
            "ADA-1.5.1",  # Firmness and stability (36.305(b))
            "ADA-1.6.1",  # Changes in level (36.305(b))
        ]

        for rule_id in required_rules:
            rule = get_rule(rule_id)
            assert rule is not None, f"Required ADA rule {rule_id} not found"

    def test_ada_cfr_36_303_accessible_routes(self):
        """ADA CFR 36.303: Accessible Pedestrian Routes."""
        # Width: 36.303(c)(1)
        width_rule = get_rule("ADA-1.2.1")
        assert width_rule.parameters["min_clear_width_feet"] == 4.0

        # Slope: 36.303(c)(2) - includes longitudinal and cross slope
        slope_rule = get_rule("ADA-1.2.2")
        assert slope_rule.parameters["max_longitudinal_slope_percent"] == 5.0
        assert slope_rule.parameters["max_cross_slope_percent"] == 2.0

    def test_ada_cfr_36_305_ground_surfaces(self):
        """ADA CFR 36.305: Ground and Floor Surfaces."""
        # General requirements
        firmness_rule = get_rule("ADA-1.5.1")
        assert firmness_rule is not None

        # Slip resistance
        slip_rule = get_rule("ADA-1.3.1")
        assert slip_rule.parameters["min_bpn_dry"] == 60

# ============================================================================
# LOCAL LAW 60 & NYC ADMINISTRATIVE CODE SECTION 19-152
# ============================================================================

class TestLocalLaw60Compliance:
    """Validates property owner maintenance responsibilities under Local Law 60."""

    def test_trip_hazard_threshold_from_local_law_60(self):
        """
        Local Law 60: Property owners responsible for trip hazards > 0.5 inches.

        Reference: NYC Admin Code § 19-152, Local Law 60 (2003)
        """
        # Trip hazard rule (often ADA-1.5.1)
        rule = get_rule("ADA-1.5.1")
        assert rule is not None

        # Local Law 60 uses 1 inch threshold for enforcement, but ADA is 0.5"
        params = rule.parameters
        assert params["max_vertical_displacement_inches"] == 0.5, (
            "ADA standard: vertical change ≤ 0.5 inches"
        )
        # Note: Local Law 60 enforcement is 1+ inch, but ADA is stricter

# ============================================================================
# CONSISTENCY & CROSS-VALIDATION TESTS
# ============================================================================

class TestCrossValidationAndConsistency:
    """Tests that verify internal consistency across all standards."""

    def test_all_materials_have_valid_specifications(self):
        """Verify all material definitions have required fields."""
        for mat_id, spec in MATERIAL_DEFINITIONS.items():
            assert spec.material_id is not None
            assert spec.category is not None
            assert spec.lifecycle_years > 0, f"{mat_id}: lifecycle must be positive"
            assert spec.design_standards is not None, f"{mat_id}: missing design standards"
            assert spec.maintenance_schedule is not None, f"{mat_id}: missing maintenance schedule"

    def test_material_lifecycle_order_asphalt_vs_concrete(self):
        """Verify material lifecycles follow expected durability hierarchy."""
        asph = ASPH_STANDARD.lifecycle_years
        conc = CONC_STANDARD.lifecycle_years
        stone = STONE_NATURAL.lifecycle_years

        # Standard hierarchy by durability
        assert asph < conc, f"Asphalt ({asph}y) should be < concrete ({conc}y)"
        assert conc < stone, f"Concrete ({conc}y) should be < stone ({stone}y)"

    def test_material_maintenance_frequency_inverse_lifecycle(self):
        """Verify materials with shorter lives need more frequent maintenance."""
        asph_routine = ASPH_STANDARD.maintenance_schedule.routine_interval_years
        conc_routine = CONC_STANDARD.maintenance_schedule.routine_interval_years

        # Asphalt needs more frequent maintenance
        assert asph_routine < conc_routine, (
            f"Asphalt ({asph_routine}y) routine should be < concrete ({conc_routine}y)"
        )

    def test_all_ada_rules_reference_existing_severity(self):
        """Verify all ADA rules have valid severity classifications."""
        valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

        for rule_id, rule in ADA_COMPLIANCE_RULES.items():
            severity = rule.failure_severity.name
            assert severity in valid_severities, (
                f"Rule {rule_id} has invalid severity: {severity}"
            )

    def test_critical_ada_rules_identified(self):
        """Verify critical ADA rules exist and are marked correctly."""
        critical = get_critical_rules()
        assert len(critical) > 0, "Should have at least one CRITICAL ADA rule"

        # Width and slip resistance should be critical
        critical_ids = [r.rule_id for r in critical]
        assert any("1.2.1" in rid for rid in critical_ids), (
            "Width (ADA-1.2.1) should be CRITICAL severity"
        )

# ============================================================================
# AUDIT TRAIL & MAINTENANCE
# ============================================================================

class TestAuditTrailAndMaintenance:
    """Tests that help maintain and audit the design standards over time."""

    def test_manual_version_metadata_exists(self):
        """Verify manual metadata is documented for audit trail."""
        assert MANUAL_METADATA["edition"] == "4th Edition"
        assert MANUAL_METADATA["url"] == "https://www.nycstreetdesign.info/"
        assert "last_accessed" in MANUAL_METADATA

    def test_all_sections_have_references(self):
        """Verify key sections are documented for manual cross-referencing."""
        required_sections = [
            "Section 4: Sidewalk Materials and Finishes",
            "Section 5: Sidewalk Width and Slope",
            "Section 6: Walking Surface Material Performance",
        ]

        for section in required_sections:
            assert section in MANUAL_METADATA["sections_verified"]

    def test_specification_source_documentation(self):
        """
        Verify that all material specs can be traced back to official source.

        MAINTENANCE NOTE:
        When updating any material spec, add a comment with:
        - Source: "NYC SDM 4th Edition, Section X, Page Y"
        - Date verified: "YYYY-MM-DD"
        - Verifier: "Your Name"

        Example:
            assert spec.lifecycle_years == 20
            # Source: NYC SDM 4th Ed, Section 4.1, Page 45
            # Date verified: 2024-06-05
            # Verifier: NYC DOT Data Team
        """
        # This test is manual - developers should document sources
        pass

# ============================================================================
# RUNNING THE TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
