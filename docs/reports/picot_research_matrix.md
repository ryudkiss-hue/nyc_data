# PICO(T) Research Question Matrix: NYC DOT SIM Division

## Executive Summary
This document expands the strategic research capabilities of the NYC DOT Sidewalk Inspection and Management (SIM) division by utilizing the **PICO** (Population, Intervention, Comparison, Outcome) and **PICOT** (Population, Intervention, Comparison, Outcome, Time) frameworks. 

We have aggressively bucketed these into Operational Relevance Tiers. **Tier 1 (Core SIM)** and **Tier 2 (SIM-Adjacent / Coordination)**. Tier 3 questions (out of scope RRM paving tasks) have been formally discarded.

---

## 1. Relational Questions
**Template:** *"What is the relationship between [Variable A] and [Variable B] among [Population]?"*

| ID | Tier | Population | Variable A | Variable B | Generated Question | Target Datasets |
|:---|:---|:---|:---|:---|:---|:---|
| **RQ-01** | Tier 1 | High-Density Residential Lots | Built Floor Area Ratio (FAR) | 311 Sidewalk/Curb complaint volume | *What is the relationship between Built Floor Area Ratio (FAR) and 311 Sidewalk/Curb complaint volume among High-Density Residential Lots?* | `mappluto`, `complaints_311` |
| **RQ-03** | Tier 1 | HIQA Inspections | Time of day (shift hours elapsed) | Violation issuance severity | *What is the relationship between time of day (shift hours elapsed) and violation issuance severity among HIQA Inspections?* | `street_construction_inspections`, `violations` |
| **RQ-04** | Tier 2 | NYC Arterial Streets | Planimetric sidewalk width | Frequency of protruding curb metal defects | *What is the relationship between planimetric sidewalk width and frequency of protruding curb metal defects among NYC Arterial Streets?* | `sidewalk_planimetric`, `curb_metal_protruding` |
| **RQ-05** | Tier 2 | Outer-Borough Intersections | Pedestrian demand index | ADA ramp complaint generation | *What is the relationship between pedestrian demand index and ADA ramp complaint generation among Outer-Borough Intersections?* | `pedestrian_demand`, `ramp_complaints` |

*(Note: RQ-02 was discarded to Tier 3).*

---

## 2. Comparative Questions
**Template:** *"Is there a significant difference in [Outcome] between [Comparison Group] and [Intervention Group] at [Time]?"*

| ID | Tier | Outcome | Comparison Group | Intervention Group | Time | Generated Question | Target Datasets |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **CQ-01** | Tier 2 | Mean-Time-To-Resolution (MTTR) | Standard routed complaints | Complaints with Equity Multipliers | 6 Months Post-Launch | *Is there a significant difference in Mean-Time-To-Resolution (MTTR) between standard routed complaints and complaints with Equity Multipliers at 6 months post-launch?* | `complaints_311`, `mappluto` |
| **CQ-03** | Tier 1 | Sidewalk dismissal rate | Residential (R1-R5) zones | Manufacturing/Commercial (M1) zones | Fiscal Year 2025 | *Is there a significant difference in sidewalk dismissal rate between Residential (R1-R5) zones and Manufacturing (M1) zones at the end of Fiscal Year 2025?* | `dismissals`, `lot_info` |

*(Note: CQ-02, CQ-04, and CQ-05 were discarded to Tier 3).*

---

## 3. Predictive Questions
**Template:** *"To what extent can [Variable X] and [Variable Y] predict [Variable Z] in [Population]?"*

| ID | Tier | Population | Variable X | Variable Y | Variable Z (Outcome) | Generated Question | Target Datasets |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **PQ-02** | Tier 1 | Repair Contractors | Active permit volume | Previous quarter stipulation violations | Monthly repair completion yield | *To what extent can active permit volume and previous quarter stipulation violations predict monthly repair completion yield in Repair Contractors?* | `street_permits`, `permit_stipulations`, `built` |
| **PQ-03** | Tier 1 | 311 Complaint Backlog | NLP negative sentiment polarity | Initial transcript length | Probability of identifying a severe safety hazard | *To what extent can NLP negative sentiment polarity and initial transcript length predict the probability of identifying a severe safety hazard in the 311 Complaint Backlog?* | `complaints_311` (NLP), `inspection` |
| **PQ-04** | Tier 2 | ADA Pedestrian Ramps | Catchment population density | Distance to nearest transit hub | Time-to-next-complaint | *To what extent can catchment population density and distance to nearest transit hub predict time-to-next-complaint in ADA Pedestrian Ramps?* | `ramp_locations`, `pedestrian_demand` |
| **PQ-05** | Tier 1 | Defective Lots | Property assessed value | Year of last structural alteration | Probability of homeowner defaulting to City-repair | *To what extent can property assessed value and year of last structural alteration predict the probability of a homeowner defaulting to City-repair in Defective Lots?* | `lot_info`, `mappluto`, `violations` |

*(Note: PQ-01 was discarded to Tier 3).*

---

## 4. Descriptive Questions
**Template:** *"What are the key characteristics of [Population] regarding [Variable]?"*

| ID | Tier | Population | Variable | Generated Question | Target Datasets |
|:---|:---|:---|:---|:---|:---|
| **DQ-01** | Tier 1 | Non-compliant ADA Pedestrian Ramps | Spatial clustering within outer-borough Community Districts | *What are the key characteristics of non-compliant ADA Pedestrian Ramps regarding spatial clustering within outer-borough Community Districts?* | `ramp_locations`, `ramp_progress` |
| **DQ-02** | Tier 1 | Chronically active street construction permits | Average duration of extension requests | *What are the key characteristics of chronically active street construction permits regarding the average duration of extension requests?* | `street_permits` |
| **DQ-03** | Tier 1 | Sidewalk Violations dismissed in court | Primary cited defect type (e.g., Trip Hazard vs. Hardware) | *What are the key characteristics of Sidewalk Violations dismissed in court regarding the primary cited defect type?* | `dismissals`, `violations` |
| **DQ-04** | Tier 1 | High-demand pedestrian corridors | Overlap with outstanding Parks Department tree-damage | *What are the key characteristics of high-demand pedestrian corridors regarding overlap with outstanding Parks Department tree-damage?* | `pedestrian_demand`, `tree_damage` |

*(Note: DQ-05 was discarded to Tier 3).*

---
*Generated by the NYC DOT SIM Data Science Copilot. Integrated with Bayesian and Markov Engine routing.*