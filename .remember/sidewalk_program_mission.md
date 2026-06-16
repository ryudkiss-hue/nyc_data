---
name: sidewalk-program-mission
description: NYC DOT Sidewalk Program mission, enforcement loop, property owner accountability, and complete dataset lineage across 51 NYC Open Data sources
metadata:
  type: project
---

# NYC DOT Sidewalk Program: Mission & Enforcement Loop

## Program Context
- **Launch:** 1992 (34 years operational)
- **Scope:** ~1M sq ft repaired annually (~1% of city's total sidewalk area)
- **Focus:** 1-3 family homes + City-owned properties
- **Legal Framework:** NYC law + NYC DOT specifications

## Core Mission
Ensure pedestrian safety by preventing injuries from defective sidewalks.  
**Key mechanism:** Notify property owners of their responsibility + enforce compliance.

## The Complete Enforcement Loop (75-day Cure Period)

```
TRIGGER SOURCES:
├─ 311 Complaint (erm2-nwe9) — citizen reports trips/cracks
├─ Elected Officials / Community Boards
└─ Proactive Inspector Dispatch

    ↓

FIELD INSPECTION:
├─ SIM Inspection (dntt-gqwq) — record defect finding
├─ Against: sidewalk_planimetric (vfx9-tbb6) — sidewalk location basemap
├─ Against: planimetric_curbs (ikvd-dex8) — curb feature basemap
├─ Check: street_tree_census_2015 (uvpi-gqnh) — identify city trees
├─ Check: tree_damage (j6v2-6uxq) — is damage from city tree? (→ no violation for 1-3 family)
├─ Check: curb_metal_protruding (i2y3-sx2e) — protruding hardware
├─ Check: encroachments_defacements (kyvb-rbwd) — encroachments/defacements
└─ Check: step_streets (u9au-h79y) — special case (step streets)

    ↓

CONFLICT SCREENING (Don't issue violation if construction underway):
├─ street_permits (tqtj-sjs8) — active street/sidewalk permits
├─ protected_streets_block (wyih-3nzf) — protected streets (can't repair during window)
├─ protected_streets_intersection (bryy-vqd9) — protected at intersection
├─ protected_streets_segments (9p9k-tusd) — protected segments
├─ street_construction_inspections (ydkf-mpxb) — active construction
├─ capital_intersections (97nd-ff3i) — capital project work
├─ capital_blocks (jvk9-k4re) — capital block work
├─ holiday_construction_embargo (bbj7-8idq) — embargo windows (Nov-Dec)
├─ street_closures_block (i6b5-j7bu) — active street closures
└─ dob_permit_issuance (ipu4-2q9a) — DOB construction permits (related disruption)

    ↓

DEFECT MEETS CRITERIA? → ISSUE VIOLATION:
├─ violations (6kbp-uz6m) — formal violation record
├─ Look up owner via: lot_info (i642-2fxq) then mappluto (64uk-42ks)
├─ built (ugc8-s3f6) — built feature type (affects defect criteria)
└─ correspondences (bheb-sjfi) — notification sent & tracking

    ↓

PROPERTY OWNER CLASSIFICATION (from mappluto 64uk-42ks):
├─ City-Owned → DOT direct repair
├─ 1-3 Family → Outreach focus; NO LIENS for tree damage (j6v2-6uxq)
└─ Multi-Unit/Commercial → Full enforcement; liens available

    ↓

75-DAY CURE WINDOW:
├─ Track via dismissals (p4u2-3jgx) → owner disputes/dismisses
├─ Track via reinspection (gx72-kirf) → inspection to verify repair
├─ Track via correspondences (bheb-sjfi) → owner communications
└─ Deadline = notification_date + 75 days

    ↓

OUTCOME 1: OWNER COMPLIES (Self-Repairs Within 75 Days)
└─ Verified by reinspection (gx72-kirf)

    ↓

OUTCOME 2: OWNER NON-COMPLIANT (City Performs Work)
├─ City work order: pothole_workorders (x9wy-ing4)
├─ Street resurfacing: street_resurfacing_schedule (xnfm-u3k5) or street_resurfacing_inhouse (ffaf-8mrv)
├─ Concrete repair: concrete_repair_schedule (78sp-6jhj)
└─ Bill owner for cost

    ↓

COLLECTIONS:
├─ If unpaid → lien placed (except 1-3 family with tree damage j6v2-6uxq)
└─ Finance team tracks delinquency

```

## Supporting Context Datasets (Used for Prioritization & Analysis)

**Vision Zero Safety Context:**
- vzv_priority_corridors (kdda-2wcy) — high KSI corridors (prioritize repairs here)
- vzv_priority_zones (n4hs-fahn) — high KSI zones
- vzv_priority_intersections (2nj7-jxah) — dangerous intersections
- vzv_street_improvement_corridors (wqhs-q6wd) — SIP improvements underway
- vzv_street_improvement_intersections (79sh-heg3) — SIP improvements at intersections
- vzv_enhanced_crossings (bssx-36gg) — enhanced crosswalk areas (higher pedestrian impact)
- motor_vehicle_collisions (h9gi-nx95) — crash locations (sidewalk defects near high-crash areas = higher priority)

**Pavement Quality Context:**
- street_pavement_ratings (6yyb-pb25) — block-level pavement condition (correlate with sidewalk conditions)
- street_pavement_ratings_map (h933-akrx) — map layer of pavement ratings

**Pedestrian Demand Context:**
- pedestrian_demand (fwpa-qxaf) — foot traffic volume by location (high-demand areas = higher priority)
- pedestrian_counts_biannual (2de2-6x2h) — corridor pedestrian volume trends
- automated_traffic_counts (7ym2-wayt) — volume counts (proxy for foot traffic)

**Accessibility Program Context (Related SIM divisions):**
- ramp_locations (ufzp-rrqu) — ADA ramp locations (coordinate with sidewalk repair scheduling)
- ramp_complaints (jagj-gttd) — ramp complaints (similar enforcement cycle)
- ramp_progress (e7gc-ub6z) — ramp repair progress tracking
- mbpo_ramp_report (8kic-uvpz) — ramp survey near accessible stations
- accessible_pedestrian_signals (umfn-twbz) — APS locations (high-demand pedestrian corridors)
- lpi_signals (mqt5-ctec) — Leading Pedestrian Interval signals (Vision Zero corridors)
- exclusive_pedestrian_signals (8kuj-2n3u) — Barnes Dance intersections (high pedestrian volume)

**Construction Schedule Context:**
- street_permits_historical (c9sj-fmsg) — historical permits (detect repeat problem areas)
- weekly_construction (r528-jcks) — active construction schedule [⚠️ stale since 2017]
- capital_blocks_map (si9g-fztb) — map layer for capital projects
- capital_intersections_map (3zy2-a8eg) — map layer for capital intersections
- permit_stipulations (gsgx-6efw) — permit conditions/restrictions
- bridge_hold_stipulations (ge3f-inui) — bridge holds (don't repair adjacent if bridge on hold)
- traffic_signal_studies (w76s-c5u4) — signal studies (avoid disruption to planned work)

---

## Property Owner Classification

**Three categories drive enforcement strategy:**
1. **City-Owned Properties (via mappluto 64uk-42ks)** → DOT contractors directly repair (no enforcement needed)
2. **1-3 Family Homes (via mappluto 64uk-42ks)** → Community Outreach focus; NO LIENS (as of current policy); special handling for tree_damage (j6v2-6uxq)
3. **Multi-Unit / Commercial (via mappluto 64uk-42ks)** → Full enforcement; liens available; tracked via lot_info (i642-2fxq)

---

## Sidewalk Program Responsibilities

### Inspection & Finding
- Community Boards, elected officials, Borough Commissioners report issues
- 311 (erm2-nwe9) triggers inspector dispatch
- Inspector checks all adjacent streets against sidewalk_planimetric (vfx9-tbb6) and planimetric_curbs (ikvd-dex8)
- Documents findings in inspection (dntt-gqwq)
- Identifies eligible repairs using specific defect criteria:
  - curb_metal_protruding (i2y3-sx2e)
  - encroachments_defacements (kyvb-rbwd)
  - tree_damage (j6v2-6uxq) via cross-reference with street_tree_census_2015 (uvpi-gqnh)
  - step_streets (u9au-h79y) special cases
  - built (ugc8-s3f6) feature types

### Violation Issuance
- Only issued if defect meets criteria; documented in violations (6kbp-uz6m)
- Cross-check against protected streets (protected_streets_block wyih-3nzf, protected_streets_intersection bryy-vqd9, protected_streets_segments 9p9k-tusd)
- Cross-check against active construction (street_permits tqtj-sjs8, street_construction_inspections ydkf-mpxb)
- Cross-check against closures (street_closures_block i6b5-j7bu, holiday_construction_embargo bbj7-8idq)
- Notification sent to property owner via mappluto (64uk-42ks) contact info
- 75-day clock starts from notification; tracked via correspondences (bheb-sjfi)

### Enforcement & Collection
- Track 75-day compliance window via correspondences (bheb-sjfi) and dismissals (p4u2-3jgx)
- Coordinate City contractor work (if owner fails to repair) via:
  - pothole_workorders (x9wy-ing4)
  - street_resurfacing_schedule (xnfm-u3k5) or street_resurfacing_inhouse (ffaf-8mrv)
  - concrete_repair_schedule (78sp-6jhj)
- Verify repair via reinspection (gx72-kirf)
- Bill property owner for city-performed work via mappluto (64uk-42ks) owner contact
- Place lien (if applicable; not for 1-3 family homes with tree_damage j6v2-6uxq)

### Community Outreach
- Dedicated Outreach Unit coordinates with:
  - Community Boards
  - Elected official offices
  - Borough Commissioners
  - Property owners (direct education) — contact via mappluto (64uk-42ks)
- Uses pedestrian_demand (fwpa-qxaf) and vzv_enhanced_crossings (bssx-36gg) to identify high-impact areas
- Prioritizes using motor_vehicle_collisions (h9gi-nx95) near sidewalk defects

---

## Critical Legal Notes

**City trees (tree_damage j6v2-6uxq):** City NO LONGER issues violations for defects caused by city trees alone (applies to 1-3 family homes).  
→ Key for your analysis: **Separate "city tree damage" from "owner responsibility" defects** via street_tree_census_2015 (uvpi-gqnh) cross-reference

**Protected streets (protected_streets_block wyih-3nzf):** Cannot issue violation or schedule city repairs during protection window

**1-3 family homes:** NO liens placed (even if city repairs). Use mappluto (64uk-42ks) `bldgtype` to filter these.

---

## Your Role: Bridging Data to Enforcement

As Project Analyst, you own the **enforcement data pipeline** leveraging all 51 datasets:

1. **Identify violations** (inspection dntt-gqwq → violations 6kbp-uz6m)
2. **Link to property owners** (lot_info i642-2fxq → mappluto 64uk-42ks)
3. **Screen for conflicts** (street_permits tqtj-sjs8, protected_streets_block wyih-3nzf, etc.)
4. **Track 75-day cure window** (correspondences bheb-sjfi, dismissals p4u2-3jgx)
5. **Prioritize enforcement** (owner type from mappluto 64uk-42ks, severity, history, Vision Zero context vzv_priority_corridors kdda-2wcy)
6. **Verify compliance** (reinspection gx72-kirf)
7. **Report on compliance rates** (% of owners who repair vs. city-performs-work via pothole_workorders x9wy-ing4)
8. **Support outreach team** (which owner types need targeted engagement + high-demand areas from pedestrian_demand fwpa-qxaf)
9. **Calculate liability & collections** (who gets billed + lien status via mappluto 64uk-42ks)

---

## Property Datasets Core to Analysis

### Primary: MapPLUTO (64uk-42ks)
- **Fourfour:** 64uk-42ks
- **Size:** ~858K rows (NYC tax lots)
- **Key Columns:**
  - `bbl` (Borough-Block-Lot): primary key to link violations (6kbp-uz6m)
  - `ownertype` (City-owned vs Private vs Corporation) → enforcement strategy
  - `assessland`, `assesstot` (property value → ability to pay)
  - `bldgtype` (single-family vs multi-unit) → 1-3 family special rules (tree_damage j6v2-6uxq)
  - `yearbuilt` (age → structural risk)
  - `active` (current ownership status)
  - `ownername` (outreach contact)

### Secondary: Lot Info (i642-2fxq)
- **Fourfour:** i642-2fxq
- **Link:** violations (6kbp-uz6m) → lot_info (i642-2fxq) → mappluto (64uk-42ks)
- Key for joining violations to property ownership data

### Cross-Reference: Built Features (ugc8-s3f6)
- **Fourfour:** ugc8-s3f6
- Links to sidewalk_planimetric (vfx9-tbb6) for built feature type (affects defect criteria)

### Key Join: Violation → Property Owner → Enforcement Action
```sql
violations (6kbp-uz6m)
  LEFT JOIN lot_info (i642-2fxq) ON violations.block = lot_info.block AND violations.lot = lot_info.lot
  LEFT JOIN mappluto (64uk-42ks) ON lot_info.bbl = mappluto.bbl
  LEFT JOIN street_tree_census_2015 (uvpi-gqnh) ON ST_DWithin(violations.geom, tree_census.geom, 10)
  LEFT JOIN tree_damage (j6v2-6uxq) ON violations.bbl = tree_damage.bbl
  LEFT JOIN correspondences (bheb-sjfi) ON violations.violation_id = correspondences.violation_id
  LEFT JOIN dismissals (p4u2-3jgx) ON violations.violation_id = dismissals.violation_id
  LEFT JOIN reinspection (gx72-kirf) ON violations.violation_id = reinspection.violation_id
-- Result: for each violation, know who owns it, property type, value, whether tree caused damage, 
-- notification status, dispute status, and repair verification
```

---

## New Dashboards Enabled by Complete Dataset Integration

### 1. Violation Enforcement Tracker
```
For each violation (6kbp-uz6m):
├─ Property owner name (from mappluto 64uk-42ks)
├─ Owner type (City/1-3 Family/Multi-Unit)
├─ Notification date + 75-day deadline (via correspondences bheb-sjfi)
├─ Compliance status (via reinspection gx72-kirf):
│  ├─ Self-repaired within 75 days
│  ├─ Disputed/dismissed (dismissals p4u2-3jgx)
│  └─ City-performed (pothole_workorders x9wy-ing4, street_resurfacing_schedule xnfm-u3k5, concrete_repair_schedule 78sp-6jhj)
├─ Vision Zero context (motor_vehicle_collisions h9gi-nx95 near location? vzv_priority_corridors kdda-2wcy?)
├─ If city-performed: cost to owner + lien status (exception: 1-3 family with tree_damage j6v2-6uxq)
└─ Action: "Follow up with these 12 owners (deadline next week)"
```

### 2. Compliance Rate by Owner Type
```
Grouping by mappluto (64uk-42ks) ownertype:
├─ % who self-repair within 75 days (verified via reinspection gx72-kirf)
├─ % where City had to perform work (pothole_workorders x9wy-ing4)
├─ % who paid bills vs. delinquent
├─ Avg days to repair (by owner type)
├─ Vision Zero context (are high-KSI corridors vzv_priority_corridors kdda-2wcy slower to repair?)
└─ Insight: "City-owned properties slow; 1-3 family homes need more outreach"
```

### 3. Repeat Offender Detection
```
Which properties (via mappluto 64uk-42ks bbl) have >2 violations (6kbp-uz6m) in past 3 years?
├─ Likely structural/maintenance issues (not one-off)
├─ May indicate tree damage (tree_damage j6v2-6uxq) or encroachment issues (encroachments_defacements kyvb-rbwd)
├─ Protected street conflicts (protected_streets_block wyih-3nzf)
├─ Correlation with Vision Zero hotspots (vzv_priority_zones n4hs-fahn)
├─ May need different outreach strategy
├─ Higher risk for future non-compliance
└─ Recommendation: "Coordinate proactive inspection on 47 repeat-offender blocks"
```

### 4. Property Value vs. Compliance
```
Does mappluto (64uk-42ks) assesstot predict compliance?
├─ High-value properties: faster repairs? (reinspection gx72-kirf)
├─ Lower-value properties: need City assistance?
├─ Corner properties (built ugc8-s3f6 / sidewalk_planimetric vfx9-tbb6): higher foot traffic (pedestrian_demand fwpa-qxaf)?
└─ Strategy adjustment: "Lower-value properties get priority contractor slots (street_resurfacing_schedule xnfm-u3k5)"
```

### 5. Outreach Efficiency
```
Community Outreach team question: "Which neighborhoods need more engagement?"
├─ By Community Board (via mappluto 64uk-42ks): violation density + owner type mix
├─ High 311 complaint areas (complaints_311 erm2-nwe9) = high citizen impact
├─ High pedestrian demand areas (pedestrian_demand fwpa-qxaf, pedestrian_counts_biannual 2de2-6x2h)
├─ Vision Zero corridors (vzv_enhanced_crossings bssx-36gg)
├─ Identify: high multi-unit areas (more enforcement needed) vs. high city-owned (less)
├─ Protected streets (protected_streets_block wyih-3nzf) = different timeline strategy
└─ Outreach Team: "Focus Q3 outreach on CB 304 (80% multi-unit, low compliance, high 311 volume)"
```

### 6. Conflict Detection & Construction Coordination
```
Which violation locations (6kbp-uz6m) conflict with ongoing construction?
├─ Active permits: street_permits (tqtj-sjs8) within 50m
├─ Active construction: street_construction_inspections (ydkf-mpxb)
├─ Protected streets: protected_streets_block (wyih-3nzf), protected_streets_intersection (bryy-vqd9), protected_streets_segments (9p9k-tusd)
├─ Street closures: street_closures_block (i6b5-j7bu)
├─ Embargoes: holiday_construction_embargo (bbj7-8idq)
├─ Capital projects: capital_intersections (97nd-ff3i), capital_blocks (jvk9-k4re)
├─ DOB permits: dob_permit_issuance (ipu4-2q9a)
├─ Bridge holds: bridge_hold_stipulations (ge3f-inui)
├─ Pavement work: street_resurfacing_schedule (xnfm-u3k5), street_resurfacing_inhouse (ffaf-8mrv), concrete_repair_schedule (78sp-6jhj)
└─ Recommend: "Delay enforcement on these 23 blocks (active resurfacing until Q4)"
```

### 7. 311 Complaint-to-Action Pipeline
```
311 complaints (erm2-nwe9) that led to formal violations (6kbp-uz6m):
├─ Hotspots: where do citizens report (complaints_311 erm2-nwe9)? Do we inspect?
├─ Complaint types (trip hazard, crack, etc.) → violation types match?
├─ Response time: days from complaint → inspection (dntt-gqwq) → violation (6kbp-uz6m)
├─ Pedestrian demand weight (pedestrian_demand fwpa-qxaf): high-traffic areas = faster response?
├─ Vision Zero context (vzv_enhanced_crossings bssx-36gg): prioritize crossings?
├─ Gap analysis: open complaints (status='Open') with no matched inspection
└─ Weekly alert: "47 open complaints, 15 have no matched inspection (gaps)"
```

---

## Implementation: Complete Data Pipeline Integration

**Phase 1: Core Datasets (Weeks 1–2)**
- violations (6kbp-uz6m)
- inspection (dntt-gqwq)
- mappluto (64uk-42ks)
- lot_info (i642-2fxq)
- complaints_311 (erm2-nwe9)

**Phase 2: Context & Conflict Detection (Weeks 3–4)**
- street_permits (tqtj-sjs8)
- protected_streets_block (wyih-3nzf)
- sidewalk_planimetric (vfx9-tbb6)
- tree_damage (j6v2-6uxq)
- motor_vehicle_collisions (h9gi-nx95)

**Phase 3: Tracking & Verification (Weeks 5–6)**
- correspondences (bheb-sjfi)
- dismissals (p4u2-3jgx)
- reinspection (gx72-kirf)
- pothole_workorders (x9wy-ing4)

**Phase 4: Full Context Integration (Weeks 7–8)**
- street_tree_census_2015 (uvpi-gqnh)
- street_construction_inspections (ydkf-mpxb)
- pedestrian_demand (fwpa-qxaf)
- vzv_priority_corridors (kdda-2wcy)
- All remaining 40+ supporting datasets

---

## Why This Matters for Your Actual Job

**Before property data:** You track violations (reactive).  
**With complete dataset integration:** You track **enforcement + prioritization + compliance + collection** (proactive + legal + strategic).

Your role shifts from:
- ❌ "Here are the violations"  
- ✅ "Here are the violations + owners + property context + construction conflicts + citizen demand + Vision Zero priority + enforcement timeline + compliance tracking + collection risk"

This directly supports:
1. **Community Outreach team** ("Which properties need personalized contact? + Which neighborhoods have high 311 volume?")
2. **Enforcement team** ("Whose 75-day window expires next? + Who is a repeat offender?")
3. **City contractor scheduling** ("If owner doesn't repair, queue these for city work. + Avoid these (protected streets). + High pedestrian demand = rush priority.")
4. **Finance/collections** ("Who owes money? + Collection risk by property value?")
5. **Legal** ("Lien-eligible violations + delinquent amounts + tree damage exceptions")
6. **Leadership/Data Governance** ("Are we hitting Vision Zero goals? + Equity analysis: low-value vs high-value compliance rates?")

