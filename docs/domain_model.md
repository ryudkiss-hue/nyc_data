# NYC Street Design Manual Domain Model

## Overview

This document describes the Phase 1 foundational implementation of the NYC Street Design Manual (SDM) as a first-class data model. The domain model codifies NYC DOT guidance on sidewalk materials, defects, pavement markings, ADA compliance, and contractor qualifications.

**Status**: Phase 1 Foundation - Blocking all downstream transformation, KPI, and serving layers  
**Last Updated**: 2024-2026  
**Maintained By**: NYC DOT Sidewalk Toolkit Team

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Reference Dimensions (dim_*)](#reference-dimensions)
3. [Material Classification Guide](#material-classification-guide)
4. [Defect Classification Guide](#defect-classification-guide)
5. [ADA Compliance Mapping](#ada-compliance-mapping)
6. [Pavement Markings Standards](#pavement-markings-standards)
7. [Contractor Classifications](#contractor-classifications)
8. [KPI Definitions](#kpi-definitions)
9. [Validation Rules & Quality Gates](#validation-rules--quality-gates)
10. [Schema Registry & Change Detection](#schema-registry--change-detection)
11. [Example Queries & Use Cases](#example-queries--use-cases)

---

## Architecture Overview

### Domain Model Components

The NYC Domain Model consists of **immutable reference dimensions** that codify NYC DOT guidance:

```
┌─────────────────────────────────────────────────────────────┐
│                  Sidewalk Fact Table(s)                      │
│        (Segments, Defects, Maintenance Records, etc.)        │
└────────┬──────────┬──────────┬──────────┬──────────┬─────────┘
         │          │          │          │          │
    ┌────▼────┐ ┌───▼───┐ ┌────▼────┐ ┌──▼──┐ ┌────▼─────┐
    │Materials │ │Defects│ │Markings │ │ADA  │ │Contractors
    │(Sec 4)  │ │(S4.x) │ │(Sec 5)  │ │Req  │ │Types
    └─────────┘ └───────┘ └─────────┘ └─────┘ └──────────┘
         │
    ┌────▼────────────────────┐
    │Surface Treatments (4.9) │
    └─────────────────────────┘
```

### Data Model Principles

1. **Immutability**: Reference dimensions are read-only after creation
2. **Traceability**: Every data point references SDM section numbers
3. **Domain-Driven**: Models follow NYC DOT operational structures
4. **Compliance-First**: ADA and safety requirements are primary
5. **Material-Aware**: All computations stratified by material type

### Supporting Infrastructure

- **Schema Registry** (`socrata_toolkit/schema_registry.py`): Tracks schema versions, detects breaking changes
- **Validation Framework** (`socrata_toolkit/validation.py`): Enforces material taxonomy, ADA compliance, geospatial bounds
- **KPI Computation** (`socrata_toolkit/dot_sidewalk.py`): Material-aware KPI calculation with full lineage
- **Domain Model Audit Log**: Records all changes to reference dimensions

---

## Reference Dimensions

### dim_materials (NYC Street Design Manual Section 4)

Codifies material guidance per SDM specifications. Every sidewalk segment must be classified to one of these materials.

#### Table Structure

```sql
CREATE TABLE dim_materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(128) UNIQUE,      -- Official name from SDM
    material_category VARCHAR(64),           -- asphalt|concrete|permeable|specialty|color_treatments
    sdm_section VARCHAR(16),                 -- Section number (4.1-4.9)
    classification VARCHAR(32),              -- standardized|distinctive|historic|pilot
    cost_per_sqft DECIMAL(10, 4),           -- Cost guidance from SDM
    lifespan_years INT,                      -- Expected lifespan per SDM
    maintenance_frequency VARCHAR(64),       -- Maintenance interval guidance
    description TEXT,                        -- Full description with SDM references
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Material Classification Taxonomy

**Asphalt Materials (SDM Section 4.1-4.3)**

| Material | Section | Classification | Lifespan | Cost/sqft | Use Case |
|----------|---------|-----------------|----------|-----------|----------|
| Hot Mix Asphalt (HMA) | 4.1 | Standardized | 12 years | $2.50 | Standard sidewalk pavement |
| Stone Matrix Asphalt (SMA) | 4.2 | Distinctive | 15 years | $3.75 | High-performance, noise reduction |
| Open-Graded Friction Course (OGFC) | 4.3 | Standardized | 10 years | $3.25 | Drainage improvement |

**Concrete Materials (SDM Section 4.4-4.6)**

| Material | Section | Classification | Lifespan | Cost/sqft | Use Case |
|----------|---------|-----------------|----------|-----------|----------|
| Portland Cement Concrete (PCC) | 4.4 | Standardized | 25 years | $4.00 | Standard concrete sidewalk |
| Reinforced Concrete Slabs | 4.5 | Standardized | 30 years | $4.50 | High-traffic areas |
| Decorative Concrete | 4.6 | Distinctive | 25 years | $6.00 | Special districts |

**Permeable Surfaces (SDM Section 4.7)**

| Material | Section | Classification | Lifespan | Cost/sqft | Use Case |
|----------|---------|-----------------|----------|-----------|----------|
| Permeable Pavers | 4.7 | Pilot | 20 years | $8.00 | Stormwater management |
| Pervious Concrete | 4.7 | Pilot | 20 years | $5.50 | Green infrastructure |

**Specialty & Historic Materials (SDM Section 4.8)**

| Material | Section | Classification | Lifespan | Cost/sqft | Use Case |
|----------|---------|-----------------|----------|-----------|----------|
| Granite Block Pavement | 4.8 | Historic | 50 years | $12.00 | Historic preservation |
| Vitreous Tile | 4.8 | Distinctive | 40 years | $9.00 | Special districts |

**Color Surface Treatments (SDM Section 4.9)**

| Material | Section | Classification | Lifespan | Cost/sqft | Use Case |
|----------|---------|-----------------|----------|-----------|----------|
| Red Asphalt (Traffic Calming) | 4.9 | Distinctive | 12 years | $3.50 | Traffic calming zones |
| Green Asphalt (Permeable) | 4.9 | Pilot | 10 years | $4.25 | Eco-friendly surfaces |

#### Classification Levels

- **Standardized**: Widely used, well-tested, default choice for general repairs
- **Distinctive**: Enhanced aesthetics or performance, used in special districts
- **Historic**: Used in landmark districts, requires preservation council approval
- **Pilot**: Emerging materials, limited deployment, performance monitoring required

---

### dim_defect_types (Sidewalk Defect Classifications)

Codifies defect taxonomy with severity levels and material applicability per SDM guidance.

#### Defect Categories

**Surface Damage** (SDM Section 4, various subsections)

| Defect | Severity | Material Applicability | Description |
|--------|----------|------------------------|-------------|
| Potholes | Severe | Asphalt, SMA, OGFC | Surface depressions exposing base; immediate trip hazard |
| Linear Cracking | Moderate | Concrete, PCC | Cracks >1/8" allowing water infiltration |
| Alligator Cracking | Severe | Asphalt, SMA | Interconnected pattern indicating imminent failure |
| Spalling | Moderate | Concrete, Decorative | Surface flaking/chipping; potential trip hazard |
| Rutting | Moderate | Asphalt, SMA | Longitudinal depression from traffic wear |
| Loose Pavers | Moderate | Pavers, Granite, Tile | Individual units rocking or displaced |
| Faded Markings | Minor | All Materials | Markings below reflectivity minimum (SDM 5) |

**Structural Issues**

| Defect | Severity | Material Applicability | Description |
|--------|----------|------------------------|-------------|
| Heaving/Settlement | **Hazardous** | All Materials | >1/2" vertical displacement; critical ADA violation |

**Drainage Issues**

| Defect | Severity | Material Applicability | Description |
|--------|----------|------------------------|-------------|
| Drainage Blockage | Moderate | Permeable Surfaces | Outlets clogged, preventing infiltration |

**Accessibility Issues**

| Defect | Severity | Material Applicability | Description |
|--------|----------|------------------------|-------------|
| Accessible Route Gap | **Hazardous** | All Materials | Gap/level change ≥1/4"; ADA violation |

#### Severity Levels

- **Minor**: Non-urgent, can be deferred 6+ months
- **Moderate**: Should be addressed within 3 months
- **Severe**: Address within 30 days
- **Hazardous**: Immediate action required (<14 days); legal liability

---

### dim_ada_compliance (ADA Accessibility Requirements)

Maps official ADA requirements to infrastructure-specific standards per NYC DOT ADA standards.

#### Key ADA Requirements

| Requirement | Standard | Measurement | Target | SDM Reference |
|-------------|----------|-------------|--------|-----------------|
| Clear Pedestrian Path | ≥5 feet | Linear feet | 100% compliance | Section 2 |
| Running Slope | ≤1:20 (5%) | Grade percentage | 100% compliance | Section 2 |
| Level Changes | ≤1/2" vertical | Inches | 100% compliance | Section 2 |
| Surface Quality | Firm, stable, slip-resistant | Coefficient >0.5 | 100% compliance | Section 4 |
| Tactile Strips | 24" deep, detectable | Linear feet | 100% of ramps | Section 3 |
| Curb Ramp Width | ≥4 feet | Linear feet | 100% compliance | Section 3 |
| Curb Ramp Slope | ≤1:12 (8.33%) | Grade percentage | 100% compliance | Section 3 |

#### ADA Compliance Scoring

The system tracks ADA compliance as:

- **Binary (Boolean)**: Segment fully compliant (1) or not (0)
- **Percentage**: 0-100% indicating extent of compliance
- **Gap Analysis**: Specific measurements vs. requirements

---

### dim_pavement_markings (SDM Section 5)

Codifies pavement marking standards for visibility, durability, and safety.

#### Marking Types & Standards

| Marking Type | Color | Reflectivity | Replacement | SDM Ref | Purpose |
|--------------|-------|--------------|-------------|---------|---------|
| Crosswalk | White | Type III | 2 years | 5.1 | Pedestrian guidance |
| Wayfinding Arrow | White | Type III | 2 years | 5.2 | Directional guidance |
| Dashed Line (Driveway) | Yellow | Type II | 3 years | 5.3 | Access delineation |
| Solid Line (Curb Cut) | White | Type III | 2 years | 5.4 | Route boundary |
| Corner Box | White | Type III | 2 years | 5.5 | Refuge areas |
| Loading Zone | White | Type II | 3 years | 5.6 | Zone demarcation |
| Bike Lane | White | Type III | 2 years | 5.7 | Bike infrastructure |

#### Reflectivity Standards

- **Type II**: Minimum retroreflectivity 50-150 mcd/(m²·lx)
- **Type III**: Enhanced retroreflectivity 250+ mcd/(m²·lx) (high-traffic areas)

---

### dim_surface_treatments (Color Treatments, SDM Section 4.9)

Codifies colored surface treatment specifications with performance characteristics.

#### Surface Treatment Specifications

| Treatment | Color | Hex | Permeability | Heat Reflection | Durability | Use Case |
|-----------|-------|-----|--------------|-----------------|-----------|----------|
| NYC Red (Standard) | Red | #C41E3A | Impermeable | 25.5 | Good | Standard colored asphalt |
| NYC Green (Cool) | Green | #2D8659 | Semi-permeable | 42.0 | Good | Heat island reduction |
| Traffic Calming Yellow | Yellow | #FFD700 | Impermeable | 65.0 | Fair | Traffic calming zones |
| Historic Blue | Blue | #004B87 | Impermeable | 15.0 | Excellent | Landmark districts |
| Accessibility Yellow | Yellow | #FFE135 | Semi-permeable | 60.0 | Good | Curb cuts, accessible routes |

**Performance Metrics**

- **Solar Reflectance Index (SRI)**: 0-100, higher = cooler surface
- **Permeability**: Stormwater infiltration capability
- **Stain Resistance**: High/Medium/Low
- **Durability Rating**: Fair/Good/Excellent

---

### dim_contractor_type (Contractor Classifications)

Codifies contractor expertise, certifications, and specializations for repair work.

#### Contractor Categories

| Category | Specialization | Required Certifications | Min Bond | QA Requirements |
|----------|-----------------|------------------------|----------|-----------------|
| General Sidewalk | Asphalt, Concrete basics | NYC CHAR, DOT, OSHA 30 | $250k | 25%, 50%, final inspection |
| Specialty Asphalt | HMA, SMA, OGFC, Colors | Paving cert, DOT, CHAR | $500k | Core testing, plant cert |
| Concrete Specialist | PCC, Reinforced, Decorative | Concrete lic, ACI cert | $500k | Strength testing (7, 28 days) |
| Permeable Specialist | Pavers, Pervious concrete | Permeable cert, Drainage | $350k | Permeability post-test |
| Historic Preservation | Granite, Historic materials | Historic specialist cert | $350k | Material matching, council approval |
| Accessible Design | ADA compliance focused | ADA compliance specialist | $250k | Slope/width verification, audit |
| Color Treatment | Colored surfaces | Color cert, Traffic mgmt | $200k | Color matching, reflectivity test |

---

## KPI Definitions

### Legacy KPIs (Backward Compatible)

These metrics are maintained for backward compatibility but are material-agnostic:

- **Defect Density**: Defects per curb mile overall
- **Throughput Velocity**: Built linear feet per day
- **Burn Variance**: Actual spend minus planned spend
- **First Pass Yield**: First-pass inspections / total inspections
- **Rework Factor**: Rework spend / total spend

### Material-Aware KPIs (Phase 1 New)

These KPIs stratify performance by material type per SDM classifications:

#### Defect Metrics

```python
defect_rate_asphalt: float       # Defect rate for asphalt materials (%)
defect_rate_concrete: float      # Defect rate for concrete materials (%)
defect_rate_permeable: float     # Defect rate for permeable surfaces (%)
defect_rate_specialty: float     # Defect rate for specialty materials (%)
```

**Calculation**: (Total defects for material / Total linear feet for material) * 100

**Use Case**: Identify material types with higher defect rates for targeted remediation

#### ADA Compliance

```python
ada_compliance_rate: float  # Percentage of segments meeting all ADA requirements (0-100)
```

**Calculation**: (Segments fully ADA compliant / Total segments) * 100

**Use Case**: Operational tracking toward ADA compliance goals

#### Hazardous Defect Coverage

```python
hazardous_defect_coverage: dict[str, float]  # Linear feet of hazardous defects by material
hazardous_defect_count: int                  # Total count of hazardous defects
```

**Use Case**: Prioritization of urgent repairs by material

#### Maintenance Cycle Adherence

```python
maintenance_cycle_adherence: dict[str, float]  # Actual vs planned maintenance per material (%)
```

**Calculation**: (Material actually maintained this period / Planned maintenance) * 100

**Use Case**: Track maintenance program execution

#### Contractor Quality

```python
contractor_quality_by_material: dict[str, dict[str, float]]
# Structure: {material_type: {contractor_id: quality_score}}
```

**Calculation**: Repair success rate per contractor per material (TBD - placeholder)

**Use Case**: Contractor performance evaluation, material-specific expertise assessment

#### Material Longevity

```python
material_longevity: dict[str, dict[str, Any]]
# {material_type: {segment_count: int, total_linear_feet: float, age_distribution: ...}}
```

**Use Case**: Asset lifecycle planning, replacement scheduling

#### Cost Analysis

```python
cost_per_linear_foot: dict[str, float]       # Cost per linear foot by repair type
cost_per_sqft_by_material: dict[str, float]  # Cost per square foot by material
```

**Use Case**: Budget planning, material cost comparison

#### Hazard Response Time

```python
hazard_response_time_days: float  # Average days to address hazardous defects
```

**Use Case**: Safety/liability tracking, legal compliance

### KPI Lineage

All KPIs include comprehensive lineage metadata:

```python
lineage_metadata: dict = {
    "source_row_count": int,          # Input records processed
    "computed_at": str,               # ISO 8601 timestamp
    "material_col": str,              # Column name for material type
    "defect_col": str,                # Column name for defects
    "period_label": str,              # Time period identifier (e.g., "2024-Q1")
    "columns_used": list[str],        # Complete list of input columns
}
```

**Use**: Reproduce calculations, audit trail, impact analysis of schema changes

---

## Validation Rules & Quality Gates

The validation framework enforces data quality gates based on domain models:

### Material Coverage Validation

**Rule**: Every sidewalk segment must have a valid material classification.

**Enforcement**: `validate_material_coverage(df, material_col="material_type")`

**Error**: Invalid or missing material assignments block ingestion

**SDM Reference**: Section 4 (all material types)

### Defect-Material Applicability Validation

**Rule**: Defect types can only be assigned to materials where they apply.

**Enforcement**: `validate_defect_applicability(df, material_col, defect_col)`

**Examples**:
- ❌ Cannot assign "Potholes" to concrete (asphalt-only defect)
- ❌ Cannot assign "Linear Cracking" to asphalt (concrete-only)
- ✅ Can assign "Heaving/Settlement" to any material

**SDM Reference**: Section 4 defect applicability matrix

### ADA Compliance Gates

**Rule**: All segments must be scored for ADA compliance.

**Enforcement**: `validate_ada_compliance_gates(df, ada_compliance_col)`

**Metrics Validated**:
- Clear path width ≥ 5 feet (ADA-4.3.1)
- Running slope ≤ 5% (ADA-4.3.2)
- Level changes ≤ 1/2" (ADA-4.3.3)
- Surface quality (firm, stable, slip-resistant) (ADA-4.3.4)

**SDM Reference**: ADA requirements mapped in dim_ada_compliance

### Pavement Marking Standards

**Rule**: All markings must comply with SDM Section 5 specifications.

**Enforcement**: `validate_marking_standards(df, marking_col, color_col, reflectivity_col)`

**Validated**:
- Valid colors (white, yellow, blue, red)
- Reflectivity ≥ Type II/III minimum
- Replacement intervals respected

### Geospatial Bounds Validation

**Rule**: All coordinates must fall within NYC bounds.

**Enforcement**: `validate_geospatial_bounds(df, lat_col, lon_col)`

**NYC Bounds**:
- Latitude: 40.4774° to 40.9176° N
- Longitude: -74.2591° to -73.7004° W

**Use**: Detect data quality issues, erroneous imports

---

## Schema Registry & Change Detection

### Purpose

The Schema Registry tracks schema versions, detects breaking changes, and enforces contracts on ingested datasets. This blocks downstream KPI and transformation pipelines when data contracts are violated.

### Breaking vs. Non-Breaking Changes

| Change Type | Example | Impact | Action |
|-------------|---------|--------|--------|
| Column Addition | New optional column | Non-breaking | Log and proceed |
| Column Deletion | Remove unused column | **Breaking** | Alert + block |
| Type Change | int → varchar | **Breaking** | Alert + block |
| Rename | `material` → `material_type` | **Breaking** | Alert + block |
| Null Constraint Change | Make non-null nullable | **Breaking** | Alert + block |
| Position Change | Reorder columns | Non-breaking | Log and proceed |

### Usage Example

```python
from socrata_toolkit.schema_registry import SchemaRegistry
import pandas as pd

# Initialize registry
registry = SchemaRegistry(storage_dir="schema_registry/")

# Extract schema from new data
df = pd.read_csv("sidewalk_segments.csv")
current_schema = SchemaRegistry.extract_schema_from_dataframe(df, "sidewalk-segments-xyz")

# Register initial schema
registry.register_schema(current_schema)

# Later, check for drift
new_df = pd.read_csv("sidewalk_segments_updated.csv")
new_schema = SchemaRegistry.extract_schema_from_dataframe(new_df, "sidewalk-segments-xyz")

# Detect changes
changes = registry.detect_drift("sidewalk-segments-xyz", new_schema)

# Check compliance (raises exception on breaking changes)
is_compliant, changes = registry.check_schema_compliance(
    "sidewalk-segments-xyz", 
    new_schema,
    enforce_breaking=True  # In production
)
```

### Audit Trail

All schema changes are logged to `schema_registry/schema_changes_audit.jsonl`:

```json
{
  "timestamp": "2024-05-10T01:00:00.000Z",
  "dataset_id": "sidewalk-segments-xyz",
  "operation": "drift_detected",
  "change_count": 2,
  "breaking_count": 1,
  "changes": [
    {
      "type": "column_addition",
      "field": "contractor_quality_score",
      "description": "Column 'contractor_quality_score' added with type float64"
    },
    {
      "type": "type_change",
      "field": "repair_cost",
      "description": "Column 'repair_cost' type changed: float64 → object"
    }
  ]
}
```

---

## Example Queries & Use Cases

### Use Case 1: Material-Specific Defect Rate Analysis

**Question**: "Which material type has the highest defect rate? What's our concrete defect rate this quarter?"

```python
import pandas as pd
from socrata_toolkit.dot_sidewalk import compute_material_aware_kpis

# Load sidewalk segment data
df = pd.read_csv("sidewalk_segments.csv")

# Compute material-aware KPIs
kpi = compute_material_aware_kpis(
    df,
    period_label="2024-Q1",
    material_col="material",
    defect_col="defect_count",
    linear_feet_col="segment_length_ft"
)

# Access material-specific defect rates
print(f"Asphalt defect rate: {kpi.defect_rate_asphalt:.2f}%")
print(f"Concrete defect rate: {kpi.defect_rate_concrete:.2f}%")
print(f"Permeable surfaces defect rate: {kpi.defect_rate_permeable:.2f}%")

# Export to CSV for reporting
df_kpi = pd.DataFrame([kpi.to_dict()])
df_kpi.to_csv("kpi_q1_2024.csv", index=False)
```

### Use Case 2: ADA Compliance Tracking

**Question**: "What percentage of our sidewalk segments are fully ADA compliant? Where are the biggest gaps?"

```sql
-- SQL Query: ADA Compliance Summary
SELECT 
    dim_ada_compliance.requirement_id,
    dim_ada_compliance.requirement_description,
    COUNT(CASE WHEN sidewalk_segments.ada_compliant = true THEN 1 END) as compliant_count,
    COUNT(*) as total_segments,
    ROUND(
        COUNT(CASE WHEN sidewalk_segments.ada_compliant = true THEN 1 END)::numeric / 
        COUNT(*) * 100, 2
    ) as compliance_rate
FROM sidewalk_segments
CROSS JOIN dim_ada_compliance
GROUP BY dim_ada_compliance.requirement_id, dim_ada_compliance.requirement_description
ORDER BY compliance_rate ASC
LIMIT 10;
```

### Use Case 3: Contractor Performance by Material

**Question**: "Which contractors perform best on concrete repairs? Which ones need monitoring?"

```python
# Using material-aware KPIs
contractor_quality = kpi.contractor_quality_by_material

for material, contractors in contractor_quality.items():
    print(f"\n{material}:")
    for contractor_id, quality_score in sorted(contractors.items(), key=lambda x: x[1], reverse=True):
        print(f"  {contractor_id}: {quality_score:.2f}")
```

### Use Case 4: Hazardous Defect Prioritization

**Question**: "Where are our hazardous defects concentrated? What's the total linear feet at risk?"

```python
# Access hazardous defect coverage
total_hazard_ft = sum(kpi.hazardous_defect_coverage.values())
print(f"Total hazardous linear feet: {total_hazard_ft:,.0f} ft")
print(f"Hazardous defect count: {kpi.hazardous_defect_count}")

# By material
for material, linear_ft in sorted(
    kpi.hazardous_defect_coverage.items(), 
    key=lambda x: x[1], 
    reverse=True
):
    print(f"  {material}: {linear_ft:,.0f} ft")
```

### Use Case 5: Material Lifecycle Planning

**Question**: "When will our asphalt segments reach end-of-life? What's the replacement forecast?"

```python
# Access material longevity data
for material, stats in kpi.material_longevity.items():
    print(f"{material}:")
    print(f"  Segments: {stats['segment_count']}")
    print(f"  Total linear feet: {stats['total_linear_feet']:,.0f}")
    
    # Reference dim_materials for lifespan
    # Query: SELECT lifespan_years FROM dim_materials WHERE material_name = ?
```

### Use Case 6: Schema Change Impact Analysis

**Question**: "A new dataset version was just released. Did any breaking changes that impact our KPI calculations?"

```python
from socrata_toolkit.schema_registry import SchemaRegistry

registry = SchemaRegistry()

# Check compliance
try:
    is_compliant, changes = registry.check_schema_compliance(
        "my-dataset-id",
        new_schema,
        enforce_breaking=True  # Raises exception on breaking changes
    )
except SchemaRegistry.BreakingChangeAlert as alert:
    print(f"⚠️  BREAKING CHANGE DETECTED:\n{alert}")
    # Notify data engineers, pause upstream processes
```

---

## Phase 2 Readiness

This Phase 1 foundation enables Phase 2 deliverables:

- **Observability & Lineage**: Full KPI computation tracing with schema registry
- **Transformation Layer**: Material-aware ETL with validation gates
- **API & Serving**: Material-stratified endpoints with compliance metadata
- **Monitoring & Alerting**: Schema drift detection, ADA compliance tracking
- **Historical Reporting**: Material-specific trend analysis, contractor performance

---

## Appendices

### A. SDM Section Cross-Reference

| Topic | Sections | Key Domain Models |
|-------|----------|-------------------|
| Materials | 4.1-4.9 | `dim_materials`, `dim_surface_treatments` |
| Defects | 4.x (various) | `dim_defect_types` |
| Pavement Markings | 5.1-5.7 | `dim_pavement_markings` |
| ADA Requirements | 2, 3, 4 | `dim_ada_compliance` |
| Contractors | N/A | `dim_contractor_type` |

### B. Data Quality Checklist

Before using sidewalk data for reporting:

- [ ] All segments have valid material classification (`validate_material_coverage`)
- [ ] Defects only apply to compatible materials (`validate_defect_applicability`)
- [ ] All segments scored for ADA compliance (`validate_ada_compliance_gates`)
- [ ] Pavement markings meet SDM standards (`validate_marking_standards`)
- [ ] Geospatial coordinates within NYC bounds (`validate_geospatial_bounds`)
- [ ] Schema version matches expected contract (Schema Registry)

### C. Common Issues & Resolutions

**Issue**: "ValidationError: Material 'Unknown' not in VALID_MATERIALS"

**Resolution**: Update data source to use official SDM material names from `dim_materials`. Allowable values listed in Material Classification Taxonomy section.

**Issue**: "BreakingChangeAlert: Column 'defect_type' type changed float64 → object"

**Resolution**: Data source may have introduced new defect types. Update `dim_defect_types` if valid per SDM, or correct data source schema.

**Issue**: "ADA compliance rate is 0%"

**Resolution**: `ada_compliance_col` may be missing or improperly named. Verify column exists and is populated before running validation.

---

## Document Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2024-05-10 | Initial Phase 1 Foundation release | NYC DOT Sidewalk Toolkit |

---

**Document Owner**: NYC DOT Sidewalk Toolkit Team  
**Last Review**: 2024-05-10  
**Next Review**: 2024-08-10 (quarterly)  
**Status**: Production
