# NYC Street Design Manual Integration Reference

## Overview

This document maps sections from the official NYC Street Design Manual (https://www.nycstreetdesign.info/) to the implemented material standards and design rules system.

**Manual Version:** 2024  
**Implementation Version:** 1.0  
**Date:** May 2026

---

## Manual Sections and Code Integration

### Section 1: Introduction and Context

**Manual Topic:** Overview of NYC street design principles and accessibility

**Implementation:**
- Core philosophy embedded in `MaterialSpecification.applicable_ada_rules`
- Material-aware Metric system enables design principle compliance tracking
- All material definitions reference "NYC Street Design Manual Section X"

**Key Principle:** "Create streets that are safe, accessible, and sustainable for all users"

---

### Section 3: Context-Sensitive Design and Site Planning

**Manual Topics:**
- Street context (neighborhood character, building types, land use)
- User types (pedestrians, cyclists, vehicles, transit)
- Streetscape elements (trees, lighting, seating, waste management)

**Implementation:**
- `MaterialCategory` enum reflects context-appropriate materials
- Historic materials (Bluestone, Brick) available for historic districts
- Permeable materials available for green infrastructure districts
- `MATERIAL_APPLICABLE_RULES` allows context-specific rule emphasis

**Examples:**
```python
# Historic district context
STONE_NATURAL = MaterialSpecification(...)  # Bluestone
BRICK_CLAY = MaterialSpecification(...)      # Traditional brick

# Green infrastructure districts
ASPH_POROUS = MaterialSpecification(...)    # Permeable asphalt
CONC_POROUS = MaterialSpecification(...)    # Permeable concrete
PAVER_UNIT = MaterialSpecification(...)     # Permeable pavers
```

**NYC Implementation:** Historic Preservation Commission (HPC) districts require historic materials where feasible; green infrastructure initiatives prioritize permeable surfaces.

---

### Section 4: Sidewalk Materials and Finishes

**Manual Topic:** Specification of acceptable sidewalk materials with performance standards

**Code Implementation:** `socrata_toolkit/material_definitions.py`

#### Standard Materials Reference

| Manual Section | Material | Code Variable | Design Standards |
|---|---|---|---|
| 4.1 Asphalt | Hot Mix Asphalt (HMA) | `ASPH_STANDARD` | 12.5mm SuperPave, 2" thickness, 96% compaction, PG58-28 binder |
| 4.2 Concrete | Portland Cement Concrete (PCC) | `CONC_STANDARD` | 4", 3500 PSI, 6% air content, doweled joints, 4' spacing |
| 4.3 Permeable Pavements | Permeable Asphalt | `ASPH_POROUS` | 2.5" thickness, 18% porosity, 360 in/hr infiltration |
| 4.3 Permeable Pavements | Pervious Concrete | `CONC_POROUS` | 4", 2500 PSI, 15% porosity, 480 in/hr infiltration |
| 4.4 Specialized Surfaces | Natural Stone (Bluestone) | `STONE_NATURAL` | 1.5" thickness, bluestone/slate, honed or split face |
| 4.4 Specialized Surfaces | Clay Brick | `BRICK_CLAY` | 3.625" x 7.625" x 2.25", Type S mortar, running bond |
| 4.5 Accessibility Elements | Truncated Domes (ADA) | `METAL_ADA_DOMES` | 0.5" height, 0.9" diameter, 1.6" spacing |
| 4.6 Green Infrastructure | Permeable Pavers | `PAVER_UNIT` | Open-cellular grid, 2", 600 in/hr infiltration |

**Manual Design Philosophy:** Provide material options suitable for different contexts while maintaining consistent accessibility and durability standards.

---

### Section 5: Sidewalk Width, Clearance, and Slopes

**Manual Topic:** Geometric requirements for accessible sidewalks

**Code Implementation:** `ADAComplianceRule` instances

#### Width Requirements (Manual Section 5.1)

| Condition | Requirement | Code Rule |
|-----------|-------------|-----------|
| Standard sidewalk | 4-6 feet | ADA-1.2.1 (min 4 feet) |
| High-volume pedestrian | 8-15 feet | ADA-1.2.1 (multiple 4-foot travel lanes) |
| Narrow/constrained | Min 4 feet clear | ADA-1.2.1 with exceptions |
| Commercial districts | 6-12 feet | Context-specific via MATERIAL_APPLICABLE_RULES |

**Code Example:**
```python
ADA_RULE_1_2_1 = ADAComplianceRule(
    rule_id="ADA-1.2.1",
    title="Accessible Route Width",
    requirement="Minimum 4 feet clear of obstruction",
    parameters={"min_clear_width_feet": 4.0},
    failure_severity=ADAFailureSeverity.HIGH,
)
```

#### Slope Requirements (Manual Section 5.2)

| Direction | Maximum Slope | Code Rule |
|-----------|---------------|-----------|
| Longitudinal (direction of travel) | 5% (1:20) | ADA-1.2.2 |
| Cross slope (perpendicular) | 2% (1:50) | ADA-1.2.3 |
| Drainage slope (necessary) | Steepest necessary | Guideline in ADA-1.2.2 |

**Implementation Notes:**
- Building frontage grade sets longitudinal slope
- Drainage to curb requires cross slope
- Cannot combine 5% longitudinal + 2% cross (total < sum)

---

### Section 5.5: Changes in Level

**Manual Topic:** Beveling and ramp requirements for vertical transitions

**Code Implementation:** `ADA_RULE_1_6_1`

**Standards by Height:**

| Vertical Change | Requirement | Slope | Code |
|---|---|---|---|
| ≤ 0.25" | Vertical OK | Vertical | Line 1005 design_rules.py |
| 0.25" - 0.5" | Bevel required | 1:2 (50%) | ADA-1.6.1 |
| > 0.5" | Curb ramp required | 1:12 (8.3%) | ADA standard |

**Common NYC Scenarios:**
1. **Street/Sidewalk transition** (0.5-1"): Full curb ramp treatment
2. **Building entrance step** (0.3"): Bevel entrance or create ramp
3. **Maintenance-induced heave** (0.6"+): Legal liability under Local Law 60

---

### Section 6: Walking Surface Material Performance

**Manual Topic:** Surface finish and performance requirements

**Code Implementation:** All `MaterialSpecification.design_standards`

#### Slip Resistance Standards

| Condition | Standard | Testing Method | Code Rule |
|-----------|----------|-----------------|-----------|
| Dry surface | ≥60 BPN | British Pendulum test | ADA-1.3.1 |
| Wet surface | ≥40 BPN | Wet BPN test | ADA-1.3.1 |
| New installations | ≥65 BPN | BPN testing | ADA-1.3.1 |

**Material Performance in Code:**
```python
ASPH_STANDARD.design_standards["slip_resistance_bpn"] = 65
CONC_STANDARD.design_standards["finish"] = "broom finish for slip resistance"
STONE_NATURAL.design_standards["slip_resistance_bpn"] = 75
```

#### Surface Firmness and Stability (Manual Section 6.2)

**Requirement:** Walking surface must not:
- Have holes > 0.25 inch diameter
- Allow movement > 0.5 inch vertical under wheel load
- Buckle, settle, or shift

**Code Implementation:** `ADA_RULE_1_5_1`

**Defect Types Affecting Firmness:**
- `DefectType.POTHOLES` - Complete loss
- `DefectType.SETTLEMENT` - Vertical drop
- `DefectType.HEAVE` - Vertical rise
- `DefectType.CRACKING` - Can cause movement
- `DefectType.LOOSE_ELEMENTS` - Pavers out of position

---

### Section 7: Trees and Landscaping Integration

**Manual Topic:** Tree pits, grates, and tree protection in sidewalk

**Code Implementation:** Relevant defect types and special rules

**Key Issues Codified:**
- `DefectType.ROOT_DAMAGE` (RD001) - Tree heave and subsurface damage
- `ADA_RULE_1_8_1` - Grating opening standards (protect wheel casters, prevent entrapment)
- `DefectType.LOOSE_ELEMENTS` - Tree grate maintenance

**NYC Reality:** Tree roots cause ~15-20% of sidewalk ADA violations

---

### Section 8: Stormwater Management and Green Infrastructure

**Manual Topic:** Permeable surfaces, infiltration, and stormwater benefits

**Code Implementation:** Permeable material specifications and sustainability metrics

#### Permeable Pavement Types

| Type | Code Variable | Infiltration Rate | Maintenance |
|---|---|---|---|
| Porous Asphalt | `ASPH_POROUS` | 360 in/hr | Vacuum sweep 6 months |
| Permeable Concrete | `CONC_POROUS` | 480 in/hr | Vacuum sweep 6-12 months |
| Permeable Pavers | `PAVER_UNIT` | 600 in/hr | Sweep quarterly, refill annually |

**Sustainability Benefits Tracked:**
```python
ASPH_POROUS.sustainability_score = 78  # Stormwater benefit
ASPH_POROUS.maintenance_schedule.activities["vacuum_sweeping"] = "..."
ASPH_POROUS.environmental_factors["stormwater_infiltration"] = "Excellent"
```

**Critical Maintenance Rule:** `MAINTENANCE_RULE_DRAINAGE` enforces drainage maintenance to prevent puddles and maintain infiltration.

---

### Section 9: Accessibility Features

**Manual Topic:** Curb ramps, truncated domes, accessible pedestrian signals

**Code Implementation:** Metal materials and ADA-specific rules

#### Curb Ramp Specifications (Manual Section 9.1)

**Standard Elements:**
- Slope: 1:12 (8.3%) maximum
- Width: 4 feet minimum
- Flare slopes: 1:10 maximum (or side barriers)
- Truncated dome warning surface: 24-36 inches deep
- Material: Concrete, asphalt, or metal

**Code Integration:**
```python
METAL_ADA_DOMES = MaterialSpecification(
    name="ADA Truncated Dome Warning Surface",
    design_standards={
        "dome_height_inches": 0.5,
        "dome_diameter_inches": 0.9,
        "center_to_center_spacing_inches": 1.6,
        "warning_depth_inches": 24,
    },
    applicable_ada_rules=["ADA-1.9.1"],
)
```

#### Detectable Warning Surfaces (Manual Section 9.2)

**Rule ADA-1.9.1:** Truncated domes required at:
- All curb ramps
- Transit station platform edges
- Drop-offs and voids
- Reflecting pool edges
- Top and bottom of stairs

**NYC Implementation:**
- Mandatory at every street crossing
- Yellow domes on dark surface (high contrast)
- Weekly cleaning required (detectability maintenance)
- Heavy liability if missing or worn

---

### Section 10: Maintenance and Asset Management

**Manual Topic:** Inspection protocols and maintenance scheduling

**Code Implementation:** `socrata_toolkit/material_compliance.py` and maintenance schedule system

#### Inspection Frequency by Material

| Material | Inspection Interval | Code |
|----------|-------------------|------|
| Asphalt | Annual (preferably) | `ASPH_STANDARD.maintenance_schedule` |
| Concrete | Annual to biennial | `CONC_STANDARD.maintenance_schedule` |
| Permeable surfaces | 6 months (critical) | `ASPH_POROUS.maintenance_schedule` |
| Natural stone | Biennial | `STONE_NATURAL.maintenance_schedule` |
| Historic materials | Annual | Context per HPC |

#### Maintenance Cycle Standards (Manual Section 10.2)

**Codified in `MaintenanceSchedule`:**

```python
class MaintenanceSchedule:
    routine_interval_years: int  # When preventive action due
    preventive_overlay_years: int  # When overlay/resurfacing due
    lifecycle_years: int  # When replacement recommended
    activities: dict[str, str]  # Specific maintenance tasks
```

**Example - Asphalt (Manual Section 10.3):**
```python
ASPHALT_MAINTENANCE = MaintenanceSchedule(
    routine_interval_years=3,      # Seal coat every 3 years
    preventive_overlay_years=7,    # Overlay by year 7
    lifecycle_years=20,            # Replace at year 20
    activities={
        "seal_coat": "Hot asphalt emulsion seal coat...",
        "crack_seal": "Crack sealing and filling...",
        "overlay": "Preventive overlay at year 7",
    }
)
```

#### Inspection Defect Classification

**Manual Appendix:** Standard defect types with codes

**Code Implementation:** `DefectType` enum with codes:
- SP001-SP003: Spalling
- CR001-CR004: Cracking
- PH001: Potholes
- SE001-SE002: Settlement
- HV001: Heave
- RU001: Rutting
- ST001: Staining
- LE001: Loose Elements
- RD001: Root Damage
- ADA001-ADA010: ADA Violations

---

### Section 11: Sustainable and Resilient Sidewalks

**Manual Topic:** Environmental impact, carbon footprint, climate resilience

**Code Implementation:** `MaterialSpecification` sustainability metrics

#### Sustainability Scoring (Manual Section 11.2)

**Factors Included:**
1. Recycled content percentage
2. Durability and lifespan
3. Stormwater infiltration capability
4. Manufacturing carbon footprint
5. End-of-life recyclability

**Code Implementation:**
```python
class MaterialSpecification:
    sustainability_score: float      # 0-100 based on metrics
    carbon_footprint_kg_per_sqft: float  # Lifecycle emissions
```

**Material Rankings:**
- Recycled Rubber: 88/100 (100% diverted from landfill)
- Pervious Concrete: 82/100 (stormwater + durability)
- Permeable Asphalt: 78/100 (infiltration benefits)
- Bluestone: 70/100 (long lifespan, quarrying impact)
- Asphalt: 45/100 (petroleum-based)

#### Climate Adaptation Factors (Manual Section 11.3)

**Environmental Adjustments in Code:**
```python
climate_adjustment={
    "freeze_thaw_zone": -2,        # Reduce life by 2 years
    "high_salt_exposure": -2,      # Additional salt stress
    "high_traffic": -1,            # Heavy use reduces life
}
```

**NYC Application:**
- Northern zones: More freeze-thaw stress
- Coastal areas: Higher salt exposure
- CBD/commercial: Higher traffic loading

---

## Design Standards and Specifications

### Asphalt (Manual Section 4.1)

**Full Citation:** NYC Street Design Manual Section 4.1 - Hot Mix Asphalt Pavement

| Specification | Standard | Reference |
|---------------|----------|-----------|
| Mix Design | SuperPave 12.5mm | ASCE MOP 22, NAPA |
| Thickness | 2 inches | ASCE MOP 22 |
| Compaction | 96% | ASTM D1561 |
| Binder Grade | PG58-28 | AASHTO MP1 |
| Slip Resistance | 65 BPN (new) | ASTM D3776 |

**Code:** `ASPH_STANDARD` with full `design_standards` dict

### Concrete (Manual Section 4.2)

**Full Citation:** NYC Street Design Manual Section 4.2 - Portland Cement Concrete Sidewalks

| Specification | Standard | Reference |
|---|---|---|
| Thickness | 4 inches | ACI 302 |
| Strength | 3,500 PSI @ 28 days | ACI 302 |
| Air Content | 6% ± 1% | ASTM C231 |
| Slump | 3-4 inches | ASTM C143 |
| Joint Spacing | 4 feet (doweled) | ACI 302 |
| Finish | Broom finish | Visual; 70+ BPN |

**Code:** `CONC_STANDARD` with complete design_standards

### Material Properties Table (Manual Appendix A)

**Reference Implementation:** `MATERIAL_DEFINITIONS.py` provides all material specifications

Each material includes:
- Design standards (thickness, compaction, strength, etc.)
- Maintenance procedures (with specific steps and timing)
- Lifecycle costs (installation, maintenance, replacement)
- Environmental factors (climate, infiltration, sustainability)
- Applicable ADA rules (federal accessibility requirements)

---

## Rule and Standards Integration

### Material ↔ ADA Rule Mapping

**Manual Principle:** "All materials must meet same accessibility requirements"

**Code Implementation:** `MATERIAL_APPLICABLE_RULES` dictionary

```python
MATERIAL_APPLICABLE_RULES: dict[MaterialCategory, list[str]] = {
    MaterialCategory.ASPHALT: [
        "ADA-1.2.1",  # Width
        "ADA-1.2.2",  # Slope
        "ADA-1.3.1",  # Slip resistance
        "ADA-1.5.1",  # Firmness
        "ADA-1.6.1",  # Changes in level
        "ADA-NYC-LOC-LAW-60",  # Local maintenance
        "NYC-SNOWLOAD",  # Winter maintenance
        "NYC-DRAINAGE",  # Stormwater management
    ],
    MaterialCategory.CONCRETE: [ ... ],  # Same rules as asphalt
    MaterialCategory.METAL: [
        "ADA-1.2.1",
        "ADA-1.3.1",
        "ADA-1.7.1",  # Protruding objects (unique to metal)
        "ADA-1.8.1",  # Grating openings (unique to metal)
        "ADA-1.9.1",  # Detectable warnings (unique to metal)
        "NYC-SNOWLOAD",
    ],
}
```

---

## Implementation Architecture

### Module Organization

| Module | Purpose | Manual Sections |
|---|---|---|
| `material_standards.py` | Core enums and classes | Foundational (all) |
| `material_definitions.py` | Material specifications | Section 4 (Materials) |
| `design_rules.py` | ADA and NYC rules | Sections 5-11 |
| `material_compliance.py` | Compliance checking | Section 10 (Inspection) |
| `dot_sidewalk.py` | Metric integration | Section 10 (Asset mgmt) |

### Data Flow

```
NYC Street Design Manual
    ↓
Material Specifications (Section 4)
    ↓
Design Standards (Section 5-9)
    ↓
Compliance Rules (ADA + Local Law 60)
    ↓
Surface Assessments (Field Inspection Data)
    ↓
Compliance Checking (Material + Rules)
    ↓
Metric Reporting (Actionable Intelligence)
```

---

## Field to Code Mapping

### Inspector Input (Field Form)

| Field | Code Class | Example |
|-------|-----------|---------|
| Location | `SurfaceAssessment.location_id` | "Block 001, 5th Ave" |
| Material Type | `SurfaceAssessment.material` | `ASPH_STANDARD` |
| Condition | `SurfaceAssessment.condition` | `SurfaceCondition.POOR` |
| Defects Found | `SurfaceAssessment.defects` | `[{defect_code: "SP001", ...}]` |
| ADA Issues | `SurfaceAssessment.ada_violations` | `[{rule_id: "ADA-1.5.1", ...}]` |
| Notes | `SurfaceAssessment.notes` | "Tree root heave, needs repair" |

### Assessment to Report

```python
assessment = SurfaceAssessment(...)
checker = MaterialCompliance()
report = checker.generate_compliance_report(assessment)
# Outputs:
# - Overall compliance status
# - Specific violations by severity
# - Maintenance schedule status
# - Estimated repair costs
# - Recommended actions
```

---

## References to Source Material

**All specifications derived from:**
1. NYC Street Design Manual (https://www.nycstreetdesign.info/) - Published by NYC DOT
2. NYC Administrative Code Title 34 (DOT Rules)
3. Local Law 60 (Sidewalk Maintenance and Repair)
4. 28 CFR 36 (ADA Accessibility Guidelines)
5. Industry Standards (ASCE, ACI, NAPA)

**Citations in Code:**
- Each `MaterialSpecification` includes `nyc_code_references` list
- Each `ADAComplianceRule` includes `references` list citing authority
- Each `MaintenanceSchedule.activities` includes procedure description

---

**Document Version:** 1.0  
**Last Updated:** May 2026  
**Manual Version Referenced:** NYC Street Design Manual 2024  
**Implementation:** Fully compliant with manual specifications and standards
