"""
NYC Street Design Manual Design Rules Engine

Implements all applicable ADA compliance rules, maintenance schedules, and design standards
from the NYC Street Design Manual and federal regulations.

References:
- ADA Accessibility Guidelines (28 CFR 36)
- NYC Administrative Code Title 34
- Local Law 60 (Sidewalk Maintenance)
- NYC Street Design Manual (https://www.nycstreetdesign.info/)

Standards: Python 3.9+, type hints, comprehensive docstrings
"""

from __future__ import annotations

import logging

from socrata_toolkit.material.standards import (
    ADAComplianceRule,
    ADAFailureSeverity,
    MaterialCategory,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ADA COMPLIANCE RULES - Federal and NYC Requirements
# ============================================================================

# Accessible Routes and Width Requirements
ADA_RULE_1_2_1 = ADAComplianceRule(
    rule_id="ADA-1.2.1",
    title="Accessible Route Width",
    requirement=(
        "Walking surface width must be minimum 4 feet (1220mm) clear of obstruction. "
        "For narrower sidewalks, push-button shelters and street furniture must not "
        "reduce clear walking width below 4 feet."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.PERMEABLE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
        MaterialCategory.COMPOSITE,
    ],
    validation_method="measurement",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "28 CFR 36.303 - Accessible Routes",
        "ADA Standards Section 301 - General",
        "NYC ADC Title 34 § 34-814",
    ],
    description=(
        "Sidewalk width is the first accessibility requirement. Minimum 4 feet allows "
        "movement of wheelchairs and walkers. This is NYC's most common ADA violation."
    ),
    parameters={
        "min_clear_width_feet": 4.0,
        "max_cross_slope_percent": 2.0,
        "max_longitudinal_slope_percent": 5.0,
    }
)

# Walking Surface Slope
ADA_RULE_1_2_2 = ADAComplianceRule(
    rule_id="ADA-1.2.2",
    title="Walking Surface Slope",
    requirement=(
        "Longitudinal slope (direction of travel) must not exceed 5% (1:20). "
        "Cross slope (perpendicular to travel) must not exceed 2% (1:50). "
        "Where sidewalk must slope for drainage, use most generous slope possible."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.PERMEABLE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
        MaterialCategory.COMPOSITE,
    ],
    validation_method="measurement",
    failure_severity=ADAFailureSeverity.MEDIUM,
    references=[
        "28 CFR 36.303(c) - Slope",
        "NYC ADC Title 34 § 34-814",
    ],
    description=(
        "Slope is critical for wheelchair users and people with mobility disabilities. "
        "Excessive slope forces users off accessible route."
    ),
    parameters={
        "max_longitudinal_slope_percent": 5.0,
        "max_cross_slope_percent": 2.0,
    }
)

# Walking Surface Slip Resistance
ADA_RULE_1_3_1 = ADAComplianceRule(
    rule_id="ADA-1.3.1",
    title="Walking Surface Slip Resistance",
    requirement=(
        "Walking surface must have slip resistance value of at least 60 BPN "
        "(British Pendulum Number) when tested dry, and minimum 40 BPN when wet. "
        "New surfaces must achieve 65 BPN minimum. Slippery surfaces create hazard "
        "especially in rain and winter conditions."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.PERMEABLE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
        MaterialCategory.METAL,
        MaterialCategory.COMPOSITE,
    ],
    validation_method="equipment_test",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "28 CFR 36.305(b)(2) - Floor and Ground Surfaces",
        "ASTM D3776 - Slip Resistance Testing",
        "NYC DOT Sidewalk Standards",
    ],
    description=(
        "Slip resistance prevents falls, especially in wet and icy conditions. "
        "Critical for vulnerable populations (elderly, disabled). Test with "
        "British Pendulum test or equivalent."
    ),
    parameters={
        "min_bpn_dry": 60,
        "min_bpn_wet": 40,
        "min_bpn_new_surface": 65,
    }
)

# Firm and Stable Surfaces
ADA_RULE_1_5_1 = ADAComplianceRule(
    rule_id="ADA-1.5.1",
    title="Firm and Stable Walking Surfaces",
    requirement=(
        "Surface must be firm, stable, and slip-resistant. Surface must not have "
        "unmaintained bumps, holes, or openings that exceed 0.25 inch (6mm). "
        "Surface movement should not exceed 0.5 inch (13mm) with wheelchair wheel loading."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.PERMEABLE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
        MaterialCategory.COMPOSITE,
    ],
    validation_method="visual",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "28 CFR 36.305 - Floor and Ground Surfaces",
        "ADA Standards Section 302",
    ],
    description=(
        "Wheelchair users cannot navigate over rough or unstable surfaces. This rule "
        "addresses potholes, cracked pavement, heave, and other surface defects."
    ),
    parameters={
        "max_hole_opening_inches": 0.25,
        "max_vertical_displacement_inches": 0.5,
        "max_surface_irregularity_inches": 0.25,
    }
)

# Changes in Level
ADA_RULE_1_6_1 = ADAComplianceRule(
    rule_id="ADA-1.6.1",
    title="Changes in Level - Bevels and Slopes",
    requirement=(
        "Changes in level up to 0.25 inch (6mm) may be vertical. Changes from "
        "0.25 to 0.5 inch must be beveled with slope no steeper than 1:2 (50%). "
        "Changes larger than 0.5 inch must be treated as a curb ramp."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
    ],
    validation_method="measurement",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "28 CFR 36.303(c) - Changes in Level",
        "ADA Standards Section 303",
    ],
    description=(
        "Vertical edges and sharp level changes create trip hazards and are impassable "
        "for wheelchair users. Bevels reduce hazard."
    ),
    parameters={
        "max_vertical_change_no_bevel_inches": 0.25,
        "max_change_requiring_bevel_inches": 0.5,
        "max_bevel_slope_ratio": "1:2",  # 50%
    }
)

# Protruding Objects
ADA_RULE_1_7_1 = ADAComplianceRule(
    rule_id="ADA-1.7.1",
    title="Protruding Objects (Overhanging Structures)",
    requirement=(
        "Objects that protrude more than 4 inches (100mm) into the walking path from "
        "walls or other vertical surfaces, with leading edge between 27 and 80 inches "
        "(685-2030mm) above ground, must be protected by barriers or warnings. "
        "Applies to signs, tree branches, building features, etc."
    ),
    applicable_materials=[
        MaterialCategory.METAL,  # Primarily affects signs, grates, covers
    ],
    validation_method="visual",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "28 CFR 36.307 - Protruding Objects",
        "ADA Standards Section 307",
    ],
    description=(
        "Blind pedestrians depend on cane detection. Protruding objects in the "
        "head-striking zone create hazards."
    ),
    parameters={
        "protrusion_threshold_inches": 4.0,
        "min_height_inches": 27,  # Below this, cane detects it
        "max_height_inches": 80,
    }
)

# Gratings and Openings
ADA_RULE_1_8_1 = ADAComplianceRule(
    rule_id="ADA-1.8.1",
    title="Gratings and Floor Openings",
    requirement=(
        "Gratings and openings in walking surface must have openings that do not permit "
        "passage of a sphere 0.5 inch (13mm) in diameter. Gratings perpendicular to "
        "direction of travel must have no openings larger than 0.5 inch. Gratings parallel "
        "to direction of travel must have no opening larger than 1.75 inches to prevent "
        "cane entrapment."
    ),
    applicable_materials=[
        MaterialCategory.METAL,
    ],
    validation_method="measurement",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "28 CFR 36.302(d) - Gratings",
        "ADA Standards Section 302",
    ],
    description=(
        "Wheel casters can slip into gratings, creating hazards. Canes can be trapped. "
        "Opening size must be controlled."
    ),
    parameters={
        "max_sphere_diameter_inches": 0.5,
        "max_perpendicular_opening_inches": 0.5,
        "max_parallel_opening_inches": 1.75,
    }
)

# Detectable Warning (Tactile Domes)
ADA_RULE_1_9_1 = ADAComplianceRule(
    rule_id="ADA-1.9.1",
    title="Detectable Warning Surface (Tactile Domes)",
    requirement=(
        "Platform edges, drop-offs, and transition areas require detectable warning "
        "surface with truncated domes. Domes must be 0.5 inches (13mm) high, 0.9 inches "
        "(23mm) diameter, spaced 1.6 inches (41mm) center-to-center. Provide 24-36 inches "
        "deep warning strip perpendicular to direction of travel."
    ),
    applicable_materials=[
        MaterialCategory.METAL,
        MaterialCategory.CONCRETE,
    ],
    validation_method="measurement",
    failure_severity=ADAFailureSeverity.CRITICAL,
    references=[
        "28 CFR 36.303(c) - Edge Protection",
        "ADA Standards Section 307",
    ],
    description=(
        "Blind pedestrians use truncated domes to detect edge conditions and platform "
        "transitions. This is critical safety feature at curb ramps and transit stations."
    ),
    parameters={
        "dome_height_inches": 0.5,
        "dome_diameter_inches": 0.9,
        "dome_spacing_inches": 1.6,
        "warning_depth_inches": 24,  # Minimum
    }
)

# Maintenance and Surface Quality
ADA_RULE_NYC_1 = ADAComplianceRule(
    rule_id="ADA-NYC-LOC-LAW-60",
    title="Local Law 60 - Sidewalk Maintenance and Repair",
    requirement=(
        "NYC Local Law 60 requires property owners to maintain sidewalks free from hazardous "
        "conditions. Defects exceeding 1 inch vertical displacement, potholes, cracked pavement "
        "affecting more than 10% of surface, or missing surface material must be repaired. "
        "Notice of violation gives owner 14 days to remedy condition."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.PERMEABLE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
        MaterialCategory.COMPOSITE,
    ],
    validation_method="visual",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "Local Law 60 (effective 2005)",
        "NYC Administrative Code Title 34 § 34-814",
    ],
    description=(
        "NYC's primary sidewalk maintenance law. Creates private liability for "
        "property owners and requires maintenance. DOT can also perform repairs "
        "and bill the property."
    ),
    parameters={
        "max_vertical_displacement_inches": 1.0,
        "max_cracking_percent_surface": 10,
    }
)

# Winter Maintenance and Snow Removal
MAINTENANCE_RULE_SNOWLOAD = ADAComplianceRule(
    rule_id="NYC-SNOWLOAD-MAINTENANCE",
    title="Winter Maintenance - Snow and Ice Removal",
    requirement=(
        "NYC Administrative Code § 34-805 requires removal of snow and ice within 4 hours "
        "after snow stops falling (8am-4pm) or within 8 hours (4pm-8am). Must be removed to "
        "bare pavement. Failure to remove snow/ice creates hazard and accessibility barrier. "
        "Applies to all material types equally."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.PERMEABLE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
        MaterialCategory.COMPOSITE,
        MaterialCategory.METAL,
    ],
    validation_method="visual",
    failure_severity=ADAFailureSeverity.HIGH,
    references=[
        "NYC Administrative Code § 34-805",
        "NYC DOT Snow and Ice Removal Guidelines",
    ],
    description=(
        "Winter is peak hazard season in NYC. Ice creates hazard for all pedestrians, "
        "especially elderly and disabled. Maintenance is not optional."
    ),
    parameters={
        "removal_time_daytime_hours": 4,  # 8am-4pm
        "removal_time_nighttime_hours": 8,  # 4pm-8am
    }
)

# Stormwater and Drainage Maintenance
MAINTENANCE_RULE_DRAINAGE = ADAComplianceRule(
    rule_id="NYC-DRAINAGE-MAINTENANCE",
    title="Stormwater Drainage and Maintenance",
    requirement=(
        "Sidewalk must drain properly and not accumulate water (puddles > 6 inches). "
        "For permeable surfaces, infiltration rate must be maintained. Drainage must not "
        "create slipping hazard. Debris must be cleared to maintain function."
    ),
    applicable_materials=[
        MaterialCategory.ASPHALT,
        MaterialCategory.CONCRETE,
        MaterialCategory.PERMEABLE,
        MaterialCategory.SPECIALTY,
        MaterialCategory.BRICK_STONE,
        MaterialCategory.COMPOSITE,
    ],
    validation_method="visual",
    failure_severity=ADAFailureSeverity.MEDIUM,
    references=[
        "NYC DEP Stormwater Management Guidelines",
        "NYC Street Design Manual Section 3",
    ],
    description=(
        "Poor drainage creates slipping hazards, water damage, and surface deterioration. "
        "Particularly important for asphalt and concrete."
    ),
    parameters={
        "max_puddle_depth_inches": 6,
    }
)


# ============================================================================
# DESIGN RULES REGISTRY
# ============================================================================

ADA_COMPLIANCE_RULES: dict[str, ADAComplianceRule] = {
    # Accessible routes
    "ADA-1.2.1": ADA_RULE_1_2_1,
    "ADA-1.2.2": ADA_RULE_1_2_2,
    # Walking surfaces
    "ADA-1.3.1": ADA_RULE_1_3_1,
    "ADA-1.5.1": ADA_RULE_1_5_1,
    # Changes in level
    "ADA-1.6.1": ADA_RULE_1_6_1,
    # Protruding objects
    "ADA-1.7.1": ADA_RULE_1_7_1,
    # Gratings
    "ADA-1.8.1": ADA_RULE_1_8_1,
    # Detectable warnings
    "ADA-1.9.1": ADA_RULE_1_9_1,
    # NYC-specific rules
    "ADA-NYC-LOC-LAW-60": ADA_RULE_NYC_1,
    "NYC-SNOWLOAD": MAINTENANCE_RULE_SNOWLOAD,
    "NYC-DRAINAGE": MAINTENANCE_RULE_DRAINAGE,
}


# ============================================================================
# MATERIAL-TO-RULES MAPPING
# ============================================================================

MATERIAL_APPLICABLE_RULES: dict[MaterialCategory, list[str]] = {
    MaterialCategory.ASPHALT: [
        "ADA-1.2.1",
        "ADA-1.2.2",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-1.6.1",
        "ADA-NYC-LOC-LAW-60",
        "NYC-SNOWLOAD",
        "NYC-DRAINAGE",
    ],
    MaterialCategory.CONCRETE: [
        "ADA-1.2.1",
        "ADA-1.2.2",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-1.6.1",
        "ADA-NYC-LOC-LAW-60",
        "NYC-SNOWLOAD",
        "NYC-DRAINAGE",
    ],
    MaterialCategory.PERMEABLE: [
        "ADA-1.2.1",
        "ADA-1.2.2",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-1.6.1",
        "ADA-NYC-LOC-LAW-60",
        "NYC-SNOWLOAD",
        "NYC-DRAINAGE",
    ],
    MaterialCategory.SPECIALTY: [
        "ADA-1.2.1",
        "ADA-1.2.2",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-1.6.1",
        "ADA-NYC-LOC-LAW-60",
        "NYC-SNOWLOAD",
        "NYC-DRAINAGE",
    ],
    MaterialCategory.METAL: [
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.7.1",
        "ADA-1.8.1",
        "ADA-1.9.1",
        "NYC-SNOWLOAD",
    ],
    MaterialCategory.BRICK_STONE: [
        "ADA-1.2.1",
        "ADA-1.2.2",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-1.6.1",
        "ADA-NYC-LOC-LAW-60",
        "NYC-SNOWLOAD",
        "NYC-DRAINAGE",
    ],
    MaterialCategory.COMPOSITE: [
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.5.1",
        "ADA-NYC-LOC-LAW-60",
        "NYC-SNOWLOAD",
    ],
    MaterialCategory.UNKNOWN: [
        "ADA-1.2.1",
        "ADA-1.5.1",
    ],
}


# ============================================================================
# QUERY AND VALIDATION FUNCTIONS
# ============================================================================

def get_rule(rule_id: str) -> ADAComplianceRule | None:
    """Retrieve a specific ADA compliance rule by ID.

    Args:
        rule_id: Rule identifier (e.g., 'ADA-1.2.1')

    Returns:
        ADAComplianceRule or None if not found
    """
    return ADA_COMPLIANCE_RULES.get(rule_id)


def get_rules_for_material(material_category: MaterialCategory) -> list[ADAComplianceRule]:
    """Get all applicable ADA rules for a material category.

    Args:
        material_category: MaterialCategory enum value

    Returns:
        List of applicable ADAComplianceRule objects
    """
    rule_ids = MATERIAL_APPLICABLE_RULES.get(material_category, [])
    return [ADA_COMPLIANCE_RULES[rule_id] for rule_id in rule_ids if rule_id in ADA_COMPLIANCE_RULES]


def get_critical_rules() -> list[ADAComplianceRule]:
    """Get all rules with CRITICAL failure severity.

    Returns:
        List of CRITICAL-severity rules
    """
    return [
        rule
        for rule in ADA_COMPLIANCE_RULES.values()
        if rule.failure_severity == ADAFailureSeverity.CRITICAL
    ]


def get_rules_requiring_measurement() -> list[ADAComplianceRule]:
    """Get all rules requiring equipment measurement for validation.

    Returns:
        List of rules with 'measurement' validation method
    """
    return [
        rule
        for rule in ADA_COMPLIANCE_RULES.values()
        if rule.validation_method == "measurement"
    ]


def get_rules_by_severity(severity: ADAFailureSeverity) -> list[ADAComplianceRule]:
    """Get all rules matching a specific failure severity.

    Args:
        severity: ADAFailureSeverity enum value

    Returns:
        List of matching rules
    """
    return [
        rule
        for rule in ADA_COMPLIANCE_RULES.values()
        if rule.failure_severity == severity
    ]


logger.info(
    f"Loaded {len(ADA_COMPLIANCE_RULES)} ADA compliance rules and "
    f"{len(MATERIAL_APPLICABLE_RULES)} material-to-rules mappings"
)
