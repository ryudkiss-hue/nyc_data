---
name: nyc-dot-sidewalk-policy-definitive
description: Definitive NYC DOT Sidewalk Program policies from official sources - enforcement procedures, cost calculations, inter-agency coordination, financial flows
metadata:
  type: project
  date: 2026-06-12
  status: VERIFIED_OFFICIAL_SOURCES
---

# NYC DOT Sidewalk Program: Definitive Policy (2026-06-12)

**STATUS:** All facts below sourced from NYC Administrative Code, Street Works Manual, and NYC official documentation. Not assumptions.

## Legal Authority & Enforcement

**Program Owner:** NYC Department of Transportation, Division of Sidewalk & Inspection Management (SIM)
- Scope: 12,760 miles of sidewalks, ~162,000 pedestrian ramps
- Legal authority: NYC Admin Code § 19-152 (Duties and obligations of property owner)
- Enforcer: NYC DOT (issues violations); Department of Finance (bills and places liens)

## Defects Triggering Violations

**Official list (11 criteria):**
1. Cracks wider than 0.5"
2. Vertical displacement ≥0.5" between adjacent flags
3. Trip hazards (vertical grade differential ≥0.5")
4. Flags cracked to extent pieces loosened/removable
5. Undermined/loose sidewalk flags
6. Missing sidewalk flags
7. Surface defects ≥1" in all horizontal directions + ≥0.5" depth
8. Holes, potholes, depressions
9. Structural cracks/missing sections
10. Tree root heave
11. Patchwork/non-compliant asphalt repairs

**Source:** Street Works Manual 4.6

## Cure Period

**Standard:** 75 days from notification date
- Starts: Certified mail receipt date OR posting date if owner absent
- **Source:** NYC Admin Code § 19-152, Street Works Manual 4.6

**Emergency (immediate danger):** 10 days
- Applies: Collapsed sections, serious trip hazards
- **Source:** Street Works Manual 4.6

## Tree Damage Exemption

**Scope:** City-owned street trees ONLY (not private trees)
- **Applies to:** 1-3 family homes (Tax Class 1) not used commercially
- **City responsibility:** NYC does NOT charge owners; City repairs at no cost
- **Policy basis:** NYC Admin Code § 7-210; Trees & Sidewalks Program (NYC Parks)
- **Historical note:** NYC reviewed all outstanding violations for 1-3 family properties caused by City trees; cancelled liens for qualifying cases

**Critical distinction:** Exemption does NOT apply to:
- Multi-unit or commercial properties
- Private trees on adjacent properties
- Damage NOT caused by City trees

**Source:** NYC Parks Trees & Sidewalks Program, NYC Admin Code § 7-210

## Violation Dismissal Procedure

**Process:**
1. Owner completes repairs meeting DOT specifications
2. Owner contacts 311 to schedule Dismissal Inspection
3. Provide: permit number, address, block/lot, violation number, contact info
4. DOT inspector verifies work meets standards
5. If approved, violation officially removed (including County Clerk copy)

**Key points:**
- NO automatic closure; owner must request dismissal inspection
- MANDATORY inspection always required
- Violation removal includes filing with County Clerk
- **Source:** Street Works Manual 4.6, NYC311 procedures

## Dismissal Appeals

**If owner disputes violation:**
- Contact 311 to request re-inspection
- DOT will reschedule within 180 days
- Can contest if defect doesn't meet standards or was misidentified
- **Source:** Street Works Manual 4.6

## Cost Calculation & Billing

**Formula:** Square footage × price-per-square-foot (specified on Notice of Violation)

**Typical rates:**
- Minor patches/cracks: $5–$11/sq ft
- Full flag replacement: $15–$25/sq ft
- Demolition/removal: $2–$4/sq ft
- Materials/labor/disposal: $5–$10/sq ft combined

**Permit fee:** $70 flat fee (covers up to 300 linear feet for single property)

**Contractor rates:** City contractors typically on par with or higher than private rates

**No fine on violation itself:** Non-compliance results in cost, not fine

**Billing authority:** Department of Finance (DOF)
- Invoices after city performs repair
- Property owner has 90 days to pay
- **Source:** NYC Admin Code § 19-152

## Collections & Lien Enforcement

**Timeline:**
- Day 76: If owner doesn't repair, city may perform work
- City incurs cost, bills property owner
- Owner has 90 days to pay invoice
- Day 166+: If unpaid, DOF places lien on property
- Lien filed in County Clerk's office

**Lien authority:** Department of Finance (DOF)
- Enforced through property tax lien system
- Enforceable via property sale or tax foreclosure
- Lien removal: After Finance receives payment, DOT files release; removal takes ~90 days

**Source:** NYC Admin Code § 19-152

## Inter-Agency Coordination

**DOB (Construction Permits):**
- Office of Construction Mitigation & Coordination (OCMC) reviews all construction permits
- Valid DOB permit required before NYC DOT construction permits
- OCMC develops stipulations to minimize disruption, avoid conflicts
- **Source:** NYC DOT Street Works Manual

**DCAS (Property Assessments):**
- NO official documentation found on direct coordination
- Status: Not coordinated in published sources

**OMB (Budget & Reporting):**
- NYC DOT budget: $1.4B (2025), 1.3% of city budget
- Roadway Repair/Maintenance/Inspection: $317.9M (22.7% of DOT budget)
- Sidewalk program scope: 2+ million sq ft/year repairs
- **Source:** NYC OMB FY2025 Budget, NYC DOT testimony

## Permit Requirements

**Homeowner DIY repairs:**
- May apply by mail for repair permit
- No contractor registration needed if owner does own work
- Permit fee: $70

**Contractor repairs:**
- Contractor must be registered with NYC DOT
- Must obtain permit
- Permit fee: $70
- **Source:** Street Works Manual 4.6

## Annual Enforcement Activity

**Recent (Feb 2026):** NYC Council hearing on sidewalk enforcement & snow-clearing compliance
- 4,500+ summonses issued for snow-clearing violations post-January storm
- Focus: Accessibility (inadequate clearing at ramps, crosswalks, bus stops)
- **Source:** THE CITY, Feb 2026

## Data Available

**NYC Open Data:**
- Sidewalk Violations (dataset: 6kbp-uz6m)
- Sidewalk Inspections (dataset: dntt-gqwq)
- Dismissal Tracking (dataset: p4u2-3jgx)
- Lot Info (dataset: i642-2fxq)
- **Source:** nyc.gov/html/dot/html/about/datafeeds.shtml

## Key Metrics Tracked

- Compliance rate (% of sidewalks in safe condition)
- Cost recovery rate (billed vs. collected)
- Response time (inspection → violation → repair)
- Violation dismissal rate
- Annual sq ft repaired (2+ million/year)

## Critical for Data Dictionary

**Must define (for Chart Finder):**
1. Defect type: Binary violation columns (broken, trip_haz, etc.) map to 11 official criteria
2. Compliance: Violation is "compliant" if: (reinspection.pass_fail='Y' AND inspection_date ≤ deadline) OR dismissal confirmed OR violation closed
3. Cost: Which dataset is source of truth? Pothole workorders (current) or contractor bids?
4. Tree damage: Is tree_damage dataset or spatial join authoritative?
5. Dismissal finality: Is dismissal reversible? Under what conditions?

