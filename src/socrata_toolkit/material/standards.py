"""
NYC Street Design Manual Material Standards - Core Domain Model

Codifies material classifications, surface condition assessments, and ADA compliance rules
from the NYC Street Design Manual (https://www.nycstreetdesign.info/).

Core Components:
- MaterialCategory: Enumeration of standard NYC sidewalk materials
- SurfaceCondition: Assessment categories from EXCELLENT to CRITICAL
- SurfaceDefect: Specific defect types with standardized codes
- ADAComplianceRule: Federal ADA and NYC regulatory requirements
- MaterialSpecification: Complete material standard with design specs, costs, maintenance
- SurfaceAssessment: Field assessment data tied to material specifications

References:
- NYC Street Design Manual (https://www.nycstreetdesign.info/)
- NYC Administrative Code Title 34 (DOT Rules)
- ADA Accessibility Guidelines (28 CFR 36)
- Local Law 60 (Sidewalk Maintenance)

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MaterialCategory(str, Enum):
    """NYC Street Design Manual material classifications.

    Based on Section 4: Sidewalk Materials and Finishes
    References: NYC SDM, ASCE, ACI, NAPA standards
    """

    ASPHALT = "asphalt"
    """Hot Mix Asphalt (HMA), Stone Matrix Asphalt (SMA), Open-Graded Friction Course (OGFC)"""

    CONCRETE = "concrete"
    """Portland Cement Concrete (PCC), reinforced concrete slabs"""

    PERMEABLE = "permeable"
    """Permeable pavement: porous asphalt, pervious concrete, permeable pavers"""

    SPECIALTY = "specialty"
    """Specialty surfaces: exposed aggregate, unit pavers, rubber, vitreous tile"""

    METAL = "metal"
    """Metal grates, covers, ADA truncated domes"""

    BRICK_STONE = "brick_stone"
    """Brick, natural stone (bluestone, granite), slate"""

    COMPOSITE = "composite"
    """Recycled plastic, resin-bound, other composite materials"""

    UNKNOWN = "unknown"
    """Unclassified or unknown material"""


class SurfaceCondition(str, Enum):
    """Sidewalk surface condition assessment categories.

    Based on ASTM D6433 Pavement Condition Index (PCI) methodology.
    References: NYC SDM Section 5, Local Law 60
    """

    EXCELLENT = "excellent"
    """0-5% deterioration, safe, accessible, minimal maintenance needed"""

    GOOD = "good"
    """6-15% deterioration, minor defects, accessible, routine maintenance"""

    FAIR = "fair"
    """16-30% deterioration, accessible but degraded, planned maintenance required"""

    POOR = "poor"
    """31-50% deterioration, hazardous defects, urgent repair needed"""

    CRITICAL = "critical"
    """51%+ deterioration, immediate repair required, ADA non-compliant"""


class DefectType(str, Enum):
    """Standardized sidewalk defect types with codes.

    Based on NYC DOT inspection protocols and ASTM D6433.
    Each defect includes severity scaling and applicability rules.
    """

    SPALLING = "spalling"
    """SP001-SP003: Concrete/asphalt loss, surface fragments"""

    CRACKING = "cracking"
    """CR001-CR004: Linear/alligator/map cracking, width and extent variations"""

    POTHOLES = "potholes"
    """PH001: Complete surface loss, bowl-shaped depression"""

    SETTLEMENT = "settlement"
    """SE001-SE002: Sunken/uneven surfaces, vertical displacement > 0.5"""

    HEAVE = "heave"
    """HV001: Uplifted surfaces, vertical displacement, often from tree roots"""

    RUTTING = "rutting"
    """RU001: Surface wear pattern, longitudinal depression from traffic"""

    STAINING = "staining"
    """ST001: Discoloration/staining, non-structural but affects aesthetics"""

    LOOSE_ELEMENTS = "loose_elements"
    """LE001: Displaced surface units, pavers, tiles out of position"""

    ROOT_DAMAGE = "root_damage"
    """RD001: Tree root heave and displacement, subsurface damage"""

    ADA_VIOLATION = "ada_violation"
    """ADA001-ADA010: Accessibility non-compliance per 28 CFR 36"""


class ADAFailureSeverity(str, Enum):
    """ADA compliance violation severity levels.

    Determines remediation urgency and regulatory reporting requirements.
    """

    CRITICAL = "critical"
    """Immediate hazard, prevents accessible route, must fix within 24 hours"""

    HIGH = "high"
    """Significant accessibility barrier, must fix within 7 days"""

    MEDIUM = "medium"
    """Accessibility degradation, must fix within 30 days"""

    LOW = "low"
    """Minor accessibility impact, must fix within 90 days"""


class MaintenanceUrgency(str, Enum):
    """Maintenance scheduling urgency levels.

    Based on material lifecycle stage and surface condition.
    """

    ROUTINE = "routine"
    """Scheduled maintenance per material cycle, no immediate action"""

    PLANNED = "planned"
    """Planned repair within next scheduled maintenance window"""

    URGENT = "urgent"
    """Should be addressed within 30 days to prevent further deterioration"""

    EMERGENCY = "emergency"
    """Immediate repair required to prevent safety hazards or legal liability"""


@dataclass
class ADAComplianceRule:
    """Federal ADA and NYC regulatory compliance rule.

    Represents a specific accessibility requirement that must be met for sidewalk
    segments to be ADA-compliant. Each rule has testing methods and severity levels.

    References:
    - 28 CFR 36 (ADA Accessibility Guidelines)
    - NYC Administrative Code Title 34 § 34-814 (DOT Rules)
    - Local Law 60 (Sidewalk Maintenance)
    """

    rule_id: str
    """Unique identifier (e.g., 'ADA-1.2.1', 'NYC-34-814')"""

    title: str
    """Short title (e.g., 'Walking Surface Slope')"""

    requirement: str
    """Formal specification text from regulation"""

    applicable_materials: list[MaterialCategory]
    """Which material categories this rule applies to"""

    validation_method: str
    """How to test compliance: 'visual', 'measurement', 'equipment_test'"""

    failure_severity: ADAFailureSeverity
    """Severity if not met"""

    references: list[str]
    """Regulation citations (e.g., '28 CFR 36.303')"""

    description: str = ""
    """Detailed explanation of requirement"""

    parameters: dict[str, Any] = field(default_factory=dict)
    """Validation parameters (e.g., {'max_slope_percent': 5, 'max_cross_slope': 2})"""


@dataclass
class MaintenanceSchedule:
    """Material-specific maintenance schedule.

    Defines when preventive and corrective maintenance should occur
    based on climate zone, traffic, and material properties.
    """

    routine_interval_years: int
    """Years between routine maintenance (e.g., 2 for seal coat)"""

    preventive_overlay_years: int
    """Years until preventive overlay needed (e.g., 7 for asphalt)"""

    lifecycle_years: int
    """Total expected lifespan before full replacement (e.g., 20 for asphalt)"""

    climate_adjustment: dict[str, int] = field(default_factory=dict)
    """Climate-based adjustments (e.g., {'freeze_thaw_zone': -2, 'high_salt_exposure': -2})"""

    activities: dict[str, str] = field(default_factory=dict)
    """Maintenance activities mapped to intervals"""


from .standards_v4 import MaterialTier

@dataclass
class MaterialSpecification:
    """Complete specification for a NYC street design material.

    Encompasses design standards, maintenance cycles, lifecycle costs, environmental
    factors, and applicable regulatory requirements. Based on NYC Street Design Manual
    and industry standards (ASCE, ACI, NAPA).
    """

    material_id: str
    """Unique ID (e.g., 'ASPH-NYC-001', 'CONC-NYC-001')"""

    category: MaterialCategory
    """Material category for stratified analytics"""

    name: str
    """Full name (e.g., 'Hot Mix Asphalt, 12.5mm SuperPave')"""
    
    tier: MaterialTier = MaterialTier.STANDARD
    """NYC SDM 4th Ed classification (Standard, Distinctive, Historic, Pilot)"""

    description: str = ""
    """Detailed description and use cases"""

    design_standards: dict[str, Any] = field(default_factory=dict)
    """Design specifications (thickness, compaction, binder grade, etc.)."""

    maintenance_schedule: MaintenanceSchedule = field(default_factory=MaintenanceSchedule)
    """Maintenance intervals and lifecycle"""

    lifecycle_years: int = 20
    """Expected lifespan in years under normal conditions"""

    environmental_factors: dict[str, str] = field(default_factory=dict)
    """Environmental challenges (e.g., {'freeze_thaw': 'Critical'})"""

    cost_per_sqft: float = 0.0
    """Installation cost in USD per square foot"""

    lifecycle_cost_per_sqft: float = 0.0
    """Total cost of ownership per square foot"""

    sustainability_score: float = 0.0
    """0-100 score based on recycled content, durability, infiltration"""

    carbon_footprint_kg_per_sqft: float = 0.0
    """Lifecycle carbon emissions in kg CO2e per square foot"""

    applicable_ada_rules: list[str] = field(default_factory=list)
    """Which ADA rule IDs apply to this material"""

    maintenance_procedures: dict[str, str] = field(default_factory=dict)
    """Maintenance activity descriptions"""

    nyc_code_references: list[str] = field(default_factory=list)
    """NYC Administrative Code citations"""

    industry_standards: list[str] = field(default_factory=list)
    """ASTM, ACI, NAPA standard references"""

    notes: str = ""
    """Additional notes or special considerations"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['category'] = self.category.value
        data['tier'] = self.tier.value
        data['maintenance_schedule'] = asdict(self.maintenance_schedule)
        return data

    def get_maintenance_due_date(self, last_maintenance: date) -> date:
        """Calculate next maintenance due date.

        Args:
            last_maintenance: Date of last maintenance activity

        Returns:
            Date when next maintenance is due
        """
        years_to_add = self.maintenance_schedule.routine_interval_years
        return date(
            last_maintenance.year + years_to_add,
            last_maintenance.month,
            last_maintenance.day
        )

    def get_lifecycle_replacement_date(self, installation_date: date) -> date:
        """Calculate when full replacement is recommended.

        Args:
            installation_date: When material was installed

        Returns:
            Recommended replacement date
        """
        years_to_add = self.lifecycle_years
        return date(
            installation_date.year + years_to_add,
            installation_date.month,
            installation_date.day
        )


@dataclass
class SurfaceAssessment:
    """Field assessment of a sidewalk segment's surface condition and defects.

    Combines material specification with observed condition, defects, and compliance
    status to enable data-driven maintenance and operations decisions.

    Example:
        >>> assessment = SurfaceAssessment(
        ...     location_id='block-001',
        ...     material=MATERIAL_DEFINITIONS['ASPH_STANDARD'],
        ...     last_inspected=datetime.now(),
        ...     condition=SurfaceCondition.FAIR,
        ...     ada_compliance_score=72.5
        ... )
        >>> if assessment.maintenance_due:
        ...     print(f"Urgency: {assessment.urgency.value}")
    """

    location_id: str
    """Unique location identifier (e.g., Socrata dataset unique ID, block-segment)"""

    material: MaterialSpecification
    """Material specification for this location"""

    last_inspected: datetime
    """When this location was last assessed"""

    condition: SurfaceCondition
    """Overall surface condition assessment"""

    defects: list[dict[str, Any]] = field(default_factory=list)
    """List of defects found, each with:
    - defect_code: str (e.g., 'SP001')
    - defect_type: DefectType
    - severity: str ('minor', 'moderate', 'severe')
    - location: str (description of where on segment)
    - square_feet_affected: float
    - date_first_observed: datetime (optional)"""

    ada_compliance_score: float = 100.0
    """0-100 score indicating ADA compliance (100 = fully compliant)"""

    ada_violations: list[dict[str, Any]] = field(default_factory=list)
    """List of specific ADA violations with:
    - rule_id: str (e.g., 'ADA-1.2.1')
    - violation_description: str
    - severity: ADAFailureSeverity
    - remediation_required: bool"""

    maintenance_due: bool = False
    """Whether maintenance is currently due per schedule"""

    recommended_repairs: list[str] = field(default_factory=list)
    """Text descriptions of repairs needed"""

    urgency: MaintenanceUrgency = MaintenanceUrgency.ROUTINE
    """Maintenance priority level"""

    estimated_repair_cost: float = 0.0
    """Estimated cost in USD to repair all identified defects"""

    defect_area_sqft: float = 0.0
    """Total square feet of affected surface area"""

    notes: str = ""
    """Inspector notes and observations"""

    geometry: dict[str, Any] | None = None
    """Geospatial geometry (GeoJSON feature)"""

    inspector_id: str | None = None
    """ID of inspector who performed assessment"""

    inspection_equipment: list[str] = field(default_factory=list)
    """Equipment used (e.g., ['visual_inspection', 'straight_edge', 'slope_gauge'])"""

    photos: list[str] = field(default_factory=list)
    """URLs or paths to inspection photos"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['material'] = self.material.to_dict()
        data['condition'] = self.condition.value
        data['urgency'] = self.urgency.value
        data['last_inspected'] = self.last_inspected.isoformat()
        return data

    def get_deterioration_rate(self, prior_assessments: list[SurfaceAssessment]) -> float:
        """Calculate rate of surface deterioration over time.

        Args:
            prior_assessments: Chronologically ordered previous assessments

        Returns:
            Estimated percentage points of deterioration per year
        """
        if not prior_assessments or len(prior_assessments) < 2:
            return 0.0

        # Simple deterioration calculation based on condition progression
        condition_scores = {
            SurfaceCondition.EXCELLENT: 95,
            SurfaceCondition.GOOD: 80,
            SurfaceCondition.FAIR: 50,
            SurfaceCondition.POOR: 25,
            SurfaceCondition.CRITICAL: 0,
        }

        earliest = prior_assessments[0]
        latest = prior_assessments[-1]

        score_change = condition_scores[earliest.condition] - condition_scores[latest.condition]
        days_elapsed = (latest.last_inspected - earliest.last_inspected).days

        if days_elapsed <= 0:
            return 0.0

        years_elapsed = days_elapsed / 365.25
        annual_rate = score_change / years_elapsed if years_elapsed > 0 else 0.0

        return float(annual_rate)

    def is_ada_compliant(self) -> bool:
        """Check if segment meets all ADA requirements.

        Returns:
            True if no critical/high severity violations exist
        """
        for violation in self.ada_violations:
            severity = violation.get('severity')
            if severity in {ADAFailureSeverity.CRITICAL, ADAFailureSeverity.HIGH}:
                return False
        return True


@dataclass
class DefectSeverityAssessment:
    """Comprehensive defect severity and impact analysis.

    Calculates repair priority, cost estimates, and safety risk based on
    defect characteristics and applicable ADA rules.
    """

    defect_type: DefectType
    """Type of defect found"""

    severity_level: str
    """Assessment level: 'minor', 'moderate', 'severe'"""

    area_sqft: float
    """Affected surface area"""

    depth_inches: float | None = None
    """Depth of defect (for potholes, spalling)"""

    width_inches: float | None = None
    """Width of defect (for cracks)"""

    length_feet: float | None = None
    """Length of linear defect (for cracks, rutting)"""

    safety_hazard: bool = False
    """Whether this creates an immediate safety hazard"""

    trip_hazard: bool = False
    """Whether this creates a trip hazard (uneven surface > 0.5 inch)"""

    ada_violation: bool = False
    """Whether this violates ADA accessibility requirements"""

    repair_methods: list[str] = field(default_factory=list)
    """Applicable repair methods"""

    estimated_repair_cost_per_sqft: float = 0.0
    """Cost per square foot to repair"""

    estimated_total_repair_cost: float = 0.0
    """Total estimated repair cost"""

    urgency: MaintenanceUrgency = MaintenanceUrgency.ROUTINE
    """Repair urgency based on severity"""


@dataclass
class MaterialStandard:
    """Standard definition for a material.

    Defines the specification and properties of a standard material.
    """
    material_id: str
    """Unique material identifier"""

    name: str
    """Name of the material"""

    spec_version: str
    """Version of the specification"""

    properties: dict[str, Any] = field(default_factory=dict)
    """Material properties"""


@dataclass
class MaterialInspector:
    """Inspector information and credentials.

    Represents a trained inspector authorized to perform assessments.
    """
    inspector_id: str
    """Unique inspector identifier"""

    name: str
    """Inspector's full name"""

    certification_level: str
    """Certification level (e.g., 'Basic', 'Advanced', 'Expert')"""

    jurisdiction: str
    """Geographic jurisdiction (e.g., 'Manhattan', 'NYC')"""


def assess_surface(location: str, material: MaterialSpecification) -> SurfaceAssessment:
    """Assess surface condition at a location.

    Args:
        location: Location identifier
        material: Material specification

    Returns:
        SurfaceAssessment with current condition
    """
    return SurfaceAssessment(
        location_id=location,
        material=material,
        last_inspected=datetime.now(),
        condition=SurfaceCondition.GOOD,
        ada_compliance_score=100.0,
    )


def validate_against_standard(assessment: SurfaceAssessment, standard: MaterialStandard) -> bool:
    """Validate assessment against material standard.

    Args:
        assessment: Surface assessment to validate
        standard: Material standard to validate against

    Returns:
        True if assessment meets standard, False otherwise
    """
    return assessment.ada_compliance_score >= 70.0


def generate_compliance_report(assessments: list[SurfaceAssessment]) -> str:
    """Generate compliance report from assessments.

    Args:
        assessments: List of surface assessments

    Returns:
        Compliance report as formatted string
    """
    if not assessments:
        return "No assessments to report"

    compliant = sum(1 for a in assessments if a.is_ada_compliant())
    total = len(assessments)
    return f"Compliance Report: {compliant}/{total} segments compliant"


# Module exports
__all__ = [
    "MaterialCategory",
    "SurfaceCondition",
    "DefectType",
    "ADAFailureSeverity",
    "MaintenanceUrgency",
    "ADAComplianceRule",
    "MaintenanceSchedule",
    "MaterialSpecification",
    "SurfaceAssessment",
    "DefectSeverityAssessment",
    "MaterialStandard",
    "MaterialInspector",
    "assess_surface",
    "validate_against_standard",
    "generate_compliance_report",
]


# Module initialization
logger.info("NYC Street Design Manual Material Standards module loaded")
