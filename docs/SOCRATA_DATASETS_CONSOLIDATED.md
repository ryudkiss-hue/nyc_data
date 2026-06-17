---
title: NYC Open Data (Socrata) - Complete Dataset Registry [v2.0]
version: 2.0
status: ACTIVE
created: 2026-06-17
last_updated: 2026-06-17
last_verified: 2026-06-17
author: Claude Code (Consolidated with 37 Datasets)
source: NYC Open Data (data.cityofnewyork.us) — Socrata Platform
total_datasets: 37
active_datasets: 33
problematic_datasets: 4
---

# Socrata Dataset Registry: NYC DOT SIM Program [v2.0]

**Complete consolidated catalog of 37 NYC Open Data datasets** serving the Sidewalk Inspection & Management (SIM) program, organized by purpose, status, and use case.

**Version History:**
- v1.0 (2026-06-17): Initial 26-dataset registry
- v2.0 (2026-06-17): Expanded to 37 datasets; added contractor, equity, demographic, and detailed 311 complaint data

---

## Quick Reference: All 37 Datasets

### Summary Table (37 Total)

| Category | Count | Status | Key Datasets |
|----------|-------|--------|--------------|
| **Core Daily Operations** | 7 | ✅ Active | inspection, violations, reinspection, ramp_progress, ramp_complaints, complaints_311, built |
| **Quality Assurance** | 3 | ✅ Active | dismissals, tree_damage, correspondences |
| **Construction & Conflicts** | 6 | ✅ Active | street_permits, capital_intersections, street_construction_inspections, street_closures_block, street_resurfacing_inhouse, street_resurfacing_schedule |
| **Contractor & Vendor** | 3 | ✅ Active | NYCDOT_Awarded_Contracts, Prequalified_Firms, Recent_Contract_Awards |
| **311 Complaints (Detailed)** | 3 | ✅ Active | Curb_Sidewalk_Complaints, DOT_311_Complaints, 311_Complaint_Type_Descriptor |
| **Equity & Demographic** | 6 | ✅ Active | EquityNYC_Data, Demographics_by_Borough, Demographics_Housing_Profiles, Population_Community_Districts, Census_Tracts_2020, Census_Blocks_2020 |
| **Reference & Geographic** | 6 | ✅ Active | lot_info, curb_metal_protruding, mappluto, sidewalk_planimetric, step_streets, pedestrian_demand, accessible_pedestrian_signals |
| **Problematic (Archived)** | 4 | ⚠️ Deprecated | weekly_construction, capital_blocks, permit_stipulations, ramp_locations |
| **TOTAL** | **37** | **33 Active + 4 Problematic** | — |

---

## 1. Core Daily Operations (7 datasets)

Essential operational data, updated daily. Primary sources for inspection & violation tracking.

### `inspection` (dntt-gqwq)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~398K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Inspections/dntt-gqwq
- **Purpose:** Inspection scheduling, completion tracking, quality metrics
- **KPIs:** inspections_scheduled_week, inspection_completion_rate, avg_violations_per_inspection
- **SLA:** HIGH (14 days) | **Quality Score:** 0.92

### `violations` (6kbp-uz6m)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~312K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Violations/6kbp-uz6m
- **Purpose:** Violation resolution tracking, SLA monitoring, severity analysis
- **KPIs:** violations_open_count, violation_resolution_time, sla_breaches, violations_by_severity
- **SLA:** HIGH (14 days) | **Quality Score:** 0.90

### `reinspection` (gx72-kirf)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~36K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Reinspections/gx72-kirf
- **Purpose:** Follow-up inspection results, quality assurance
- **KPIs:** reinspection_rate, contractor_quality_score
- **SLA:** HIGH (14 days) | **Quality Score:** 0.88

### `ramp_progress` (e7gc-ub6z) ⭐ Preferred
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~187K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Pedestrian-Ramp-Program-Progress/e7gc-ub6z
- **Purpose:** ADA ramp completion tracking, accessibility compliance
- **Replaces:** `ramp_locations` (ufzp-rrqu) — stale since 2021
- **KPIs:** ramp_completion_by_borough, ramp_accessibility_score
- **SLA:** HIGH (14 days) | **Quality Score:** 0.91

### `ramp_complaints` (jagj-gttd)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~6K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Ramp-Complaints/jagj-gttd
- **Purpose:** Accessibility complaints, response time tracking
- **KPIs:** ramp_complaint_response_time
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.87

### `complaints_311` (erm2-nwe9) 📌 See Also: Detailed 311 datasets below
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~21.3M | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9
- **Purpose:** Public engagement signal, citizen feedback (all categories)
- **KPIs:** public_complaints_30d
- **SLA:** HIGH (14 days) | **Quality Score:** 0.86
- **Note:** Generic 311 data; see "311 Complaints (Detailed)" section for sidewalk-specific complaints

### `built` (ugc8-s3f6)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~105K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Built/ugc8-s3f6
- **Purpose:** Completed work tracking, budget/cost data
- **KPIs:** cost_per_violation_resolved, monthly_spend_trend, contract_spend_variance
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.89

---

## 2. Quality Assurance (3 datasets)

Dismissals, damage, communications. Support data quality audits.

### `dismissals` (p4u2-3jgx)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~85K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Dismissals/p4u2-3jgx
- **Purpose:** Dismissed violations, data quality indicator
- **KPIs:** violation_dismissal_rate, data_validity
- **SLA:** HIGH (14 days) | **Quality Score:** 0.83

### `tree_damage` (j6v2-6uxq)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~17K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Parks-Recreation/Tree-Damage/j6v2-6uxq
- **Purpose:** Tree damage assessments, violation type distribution
- **KPIs:** violations_by_defect_type
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.82

### `correspondences` (bheb-sjfi)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~30K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Correspondences/bheb-sjfi
- **Purpose:** Communication records, escalation tracking
- **KPIs:** escalation_count
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.80

---

## 3. Construction & Conflicts (6 datasets)

Track permits, capital projects, construction schedules, permit-inspection conflicts.

### `street_permits` (tqtj-sjs8) ⭐ Preferred
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~3.7M | **Coverage:** 2022–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Street-Construction-Permits-2022-Present-/tqtj-sjs8
- **Replaces:** `weekly_construction` (r528-jcks) — stale since 2017
- **Purpose:** Construction permit tracking, contractor scheduling
- **KPIs:** contractor_completion_rate, construction_conflict_zones
- **SLA:** HIGH (14 days) | **Quality Score:** 0.94

### `capital_intersections` (97nd-ff3i)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~7.8K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Capital-Projects-by-Intersection/97nd-ff3i
- **Purpose:** Capital project coordination, street/highway reconstruction
- **KPIs:** capital project coordination
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.85
- **Secondary to:** `cpdb_projects` (fi59-268w) for comprehensive city-wide data

### `street_construction_inspections` (ydkf-mpxb)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~11.5M | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Street-Construction-Inspections/ydkf-mpxb
- **Purpose:** Contractor inspection records, performance tracking
- **KPIs:** contractor_quality_score, contractor_sla_compliance
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.88

### `street_closures_block` (i6b5-j7bu)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~4.3K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Street-Closures-by-Block/i6b5-j7bu
- **Purpose:** Temporary street closure permits, coordination
- **KPIs:** construction_conflict_zones
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.86

### `street_resurfacing_inhouse` (ffaf-8mrv)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~602K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Street-Resurfacing-In-House/ffaf-8mrv
- **Purpose:** Completed in-house paving projects with cost data
- **KPIs:** monthly_spend_trend, cost_per_violation_resolved, spending_by_defect_type
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.87

### `street_resurfacing_schedule` (xnfm-u3k5)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~309K | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Street-Resurfacing-Schedule/xnfm-u3k5
- **Purpose:** Planned paving schedule for budget forecasting
- **KPIs:** budget planning, monthly_spend_trend
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.84

---

## 4. Contractor & Vendor (3 datasets) 🆕

NEW category: Contractor performance, awards, and prequalified vendor lists.

### `NYCDOT_Awarded_Contracts` (9u5s-8sd8)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~TBD | **Coverage:** Current contracts
- **URL:** https://data.cityofnewyork.us/City-Government/NYCDOT-Awarded-Contracts/9u5s-8sd8
- **Purpose:** Contract terms, amounts, durations, contractor details
- **KPIs:** contractor_completion_rate, contractor_sla_compliance, contract_spend_variance
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.85
- **Use Case:** Contract-performance correlation analysis, vendor capacity planning

### `Prequalified_Firms` (szkz-syh6)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~TBD | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Housing-Development/Prequalified-Firms/szkz-syh6
- **Purpose:** Master list of qualified vendors with trade codes and specializations
- **KPIs:** contractor_capacity_utilization, vendor_pool_analysis
- **SLA:** LOW (60 days) | **Quality Score:** 0.82
- **Use Case:** Baseline for contractor availability and qualifications

### `Recent_Contract_Awards` (qyyg-4tf5)
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~TBD | **Coverage:** Recent (2020–Present)
- **URL:** https://data.cityofnewyork.us/City-Government/Recent-Contract-Awards/qyyg-4tf5
- **Purpose:** Real-time contract pipeline visibility
- **KPIs:** contract_pipeline_health, future_capacity_forecast
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.83
- **Use Case:** Forward-looking capacity and resource planning

---

## 5. 311 Complaints (Detailed) (3 datasets) 🆕

NEW category: Sidewalk/curb-specific 311 complaint data with detailed categorization.

**NOTE:** These supplement the generic `complaints_311` (erm2-nwe9) dataset with targeted sidewalk/curb issue data.

### `Curb_and_Sidewalk_Complaints` (huz9-8jhi)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~TBD | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Social-Services/Curb-and-Sidewalk-Complaints/huz9-8jhi
- **Purpose:** Direct citizen feedback on sidewalk/curb issues (core problem domain)
- **KPIs:** ramp_complaint_response_time, public_complaints_30d (sidewalk-specific)
- **SLA:** HIGH (14 days) | **Quality Score:** 0.89
- **Use Case:** Root cause analysis, violation pattern correlation

### `DOT_311_Complaints_Street_Sidewalk_Signals` (th23-npnd)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~TBD | **Coverage:** 2010–Present
- **URL:** https://data.cityofnewyork.us/Social-Services/311-Service-Complaints-to-DOT-street-sidewalk-and-/th23-npnd
- **Purpose:** All 311 complaints to DOT filtered for street/sidewalk/signal conditions
- **KPIs:** public_complaints_30d, escalation_count (DOT-specific)
- **SLA:** HIGH (14 days) | **Quality Score:** 0.88
- **Use Case:** DOT-focused workload assessment, SLA compliance tracking

### `311_Complaint_Type_Descriptor_Count` (dtbq-f5rx)
- **Status:** ✅ ACTIVE | **Frequency:** Daily | **Rows:** ~TBD | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Social-Services/NYC-311-Complaint-Type-Descriptor-Count/dtbq-f5rx
- **Purpose:** Complaint taxonomy and frequency distribution
- **KPIs:** violations_by_defect_type (citizen-reported), complaint_categorization
- **SLA:** HIGH (14 days) | **Quality Score:** 0.87
- **Use Case:** Complaint type classification, pattern identification

---

## 6. Equity & Demographic (6 datasets) 🆕

NEW category: Census, equity metrics, and demographic data for compliance and analysis.

**Purpose:** Support ADA/accessibility compliance, equitable resource allocation, and equity impact analysis.

### `EquityNYC_Data` (8ek7-jxw6)
- **Status:** ✅ ACTIVE | **Frequency:** Annual | **Rows:** ~TBD | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Social-Services/Social-Indicator-Report-Data/8ek7-jxw6
- **Purpose:** City equity metrics: poverty, health, accessibility, education (citywide benchmark)
- **KPIs:** borough_disparity_index, ramp_accessibility_score (equity-weighted)
- **SLA:** LOW (60 days) | **Quality Score:** 0.90
- **Use Case:** Equity compliance baseline, strategic equity planning

### `Demographics_by_Borough` (6khm-nrue)
- **Status:** ✅ ACTIVE | **Frequency:** Annual | **Rows:** ~TBD | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/Social-Services/Demographics-by-Borough/6khm-nrue
- **Purpose:** Age, income, race/ethnicity distribution by borough
- **KPIs:** borough_disparity_index, vulnerable_population_mapping
- **SLA:** LOW (60 days) | **Quality Score:** 0.88
- **Use Case:** Identify underserved populations, allocate resources equitably

### `Demographic_Housing_Profiles_by_Borough` (cu9u-3r5e)
- **Status:** ✅ ACTIVE | **Frequency:** Annual | **Rows:** ~TBD | **Coverage:** 2014–Present (Updated Oct 2024)
- **URL:** https://data.cityofnewyork.us/City-Government/Demographic-and-Housing-Profiles-by-Borough/cu9u-3r5e
- **Purpose:** Housing types, density, population distribution by borough
- **KPIs:** infrastructure_prioritization (density-based), equity_impact_analysis
- **SLA:** LOW (60 days) | **Quality Score:** 0.87
- **Use Case:** Context for inspection scheduling, accessibility need assessment

### `Population_Community_Districts` (xi7c-iiu2)
- **Status:** ✅ ACTIVE | **Frequency:** Annual | **Rows:** ~TBD | **Coverage:** 2014–Present
- **URL:** https://data.cityofnewyork.us/City-Government/New-York-City-Population-By-Community-Districts/xi7c-iiu2
- **Purpose:** Population at finest geographic granularity (71 community districts)
- **KPIs:** coverage_gap_blocks (district-level), localized_equity_analysis
- **SLA:** LOW (60 days) | **Quality Score:** 0.89
- **Use Case:** Hyper-local equity analysis, district-based resource targeting

### `Census_Tracts_2020` (63ge-mke6)
- **Status:** ✅ ACTIVE | **Frequency:** Static (decennial) | **Rows:** ~TBD | **Coverage:** 2020 Census
- **URL:** https://data.cityofnewyork.us/City-Government/2020-Census-Tracts/63ge-mke6
- **Purpose:** Standard geographic units for federal/state reporting alignment
- **KPIs:** spatial_analysis_alignment, federal_compliance_mapping
- **SLA:** LOW (60 days) | **Quality Score:** 0.91
- **Use Case:** Align analysis with Census Bureau standards, external data joins

### `Census_Blocks_2020` (wmsu-5muw)
- **Status:** ✅ ACTIVE | **Frequency:** Static (decennial) | **Rows:** ~TBD | **Coverage:** 2020 Census
- **URL:** https://data.cityofnewyork.us/City-Government/2020-Census-Blocks/wmsu-5muw
- **Purpose:** Finest geographic granularity for spatial analysis
- **KPIs:** spatial_clustering_intensity, block-level violation density
- **SLA:** LOW (60 days) | **Quality Score:** 0.92
- **Use Case:** Highest-fidelity spatial analysis, micro-neighborhood patterns

---

## 7. Reference & Geographic (7 datasets)

Static geographic, property, and contextual overlays for spatial analysis and equity mapping.

### `lot_info` (i642-2fxq)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~1.2M | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Housing-Development/Lot-Info/i642-2fxq
- **Purpose:** Block/lot geography, property information
- **SLA:** LOW (60 days) | **Quality Score:** 0.91

### `curb_metal_protruding` (i2y3-sx2e)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~23K | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Transportation/Curb-Metal-Protruding/i2y3-sx2e
- **Purpose:** Curb hazards, violation location context
- **SLA:** LOW (60 days) | **Quality Score:** 0.79

### `mappluto` (64uk-42ks)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~858K | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Housing-Development/MapPLUTO/64uk-42ks
- **Purpose:** Property boundaries, parcel data for spatial analysis
- **SLA:** LOW (60 days) | **Quality Score:** 0.90

### `sidewalk_planimetric` (vfx9-tbb6)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~50K | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Transportation/Sidewalk-Planimetric/vfx9-tbb6
- **Purpose:** Inspection unit geography, segment-level data
- **SLA:** LOW (60 days) | **Quality Score:** 0.88

### `step_streets` (u9au-h79y)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~110 | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Transportation/Step-Streets/u9au-h79y
- **Purpose:** Step street locations for contextual overlay
- **SLA:** LOW (60 days) | **Quality Score:** 0.92

### `pedestrian_demand` (fwpa-qxaf)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~127K | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Transportation/Pedestrian-Demand/fwpa-qxaf
- **Purpose:** Pedestrian demand index for resource prioritization
- **SLA:** LOW (60 days) | **Quality Score:** 0.86

### `accessible_pedestrian_signals` (de3m-c5p4)
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~TBD | **Coverage:** Current
- **URL:** https://data.cityofnewyork.us/Transportation/Accessible-Pedestrian-Signal-Locations/de3m-c5p4
- **Purpose:** APS device locations for accessibility overlay
- **SLA:** LOW (60 days) | **Quality Score:** 0.87
- **Complements:** `ramp_progress` for comprehensive ADA analysis

---

## 8. Problematic Datasets (4 — DO NOT USE) ⚠️

**DEPRECATED:** These datasets are stale, empty, or inaccessible. Use recommended alternatives.

### ❌ `weekly_construction` (r528-jcks)
- **Status:** ⚠️ DEPRECATED | **Last Update:** 2017-01-01 | **Rows:** ~75
- **Issue:** Stale since 2017; archived
- **✅ Recommended Alternative:** [`street_permits` (tqtj-sjs8)](##street_permits-tqtj-sjs8)
  - 200x fresher data (2022–Present vs 2017)
  - 48,000x more rows (3.7M vs 75)

### ❌ `capital_blocks` (jvk9-k4re)
- **Status:** ⚠️ EMPTY | **Last Verified:** 2026-06-05 | **Rows:** 0
- **Issue:** Dataset contains zero rows
- **✅ Recommended Alternatives:**
  - **Primary:** [`cpdb_projects` (fi59-268w)](##cpdb_projects-fi59-268w-city-government) — Comprehensive city-wide
  - **Secondary:** [`capital_intersections` (97nd-ff3i)](##capital_intersections-97nd-ff3i) — DOT-focused

### ❌ `permit_stipulations` (gsgx-6efw)
- **Status:** ⚠️ API_ERROR_403 | **Last Verified:** 2026-06-05 | **Issue:** Forbidden
- **Problem:** API returns HTTP 403 (permission issue)
- **✅ Recommended Workaround:** [`permit_stipulations_historical` (pbk5-6r7z)](##permit_stipulations_historical-pbk5-6r7z)
  - Historical dataset (2020–Present) bypasses 403 error
  - **Action:** Investigate current dataset permissions; if unresolved, migrate

### ❌ `ramp_locations` (ufzp-rrqu)
- **Status:** ⚠️ STALE | **Last Update:** 2019-10-01 | **Rows:** ~217K
- **Issue:** No updates since 2021; obsolete for planning
- **✅ Recommended Alternatives:**
  - **Primary:** [`ramp_progress` (e7gc-ub6z)](##ramp_progress-e7gc-ub6z) — Daily updates, completion tracking
  - **Secondary:** [`accessible_pedestrian_signals` (de3m-c5p4)](##accessible_pedestrian_signals-de3m-c5p4) — ADA overlay

---

## NEW Recommended Datasets (Replacements) 🆕

### `cpdb_projects` (fi59-268w) — Replaces empty `capital_blocks`
- **Status:** ✅ ACTIVE | **Frequency:** Weekly | **Rows:** ~TBD | **Coverage:** Capital commitments
- **URL:** https://data.cityofnewyork.us/City-Government/Capital-Projects-Database-CPDB-Projects/fi59-268w
- **Purpose:** Comprehensive city-wide capital projects database
- **Why Add:** Empty `capital_blocks` provides no data; CPDB offers full project lifecycle
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.86

### `permit_stipulations_historical` (pbk5-6r7z) — Workaround for API 403
- **Status:** ✅ ACTIVE | **Frequency:** Static | **Rows:** ~TBD | **Coverage:** 2020–Present
- **URL:** https://data.cityofnewyork.us/Transportation/Street-Construction-Permits-Stipulations-Historica/pbk5-6r7z
- **Purpose:** Permit conditions/requirements history
- **Why Add:** Current dataset (gsgx-6efw) returns 403; historical bypasses error
- **Note:** Investigate 403 on current; if resolved, migrate back
- **SLA:** MEDIUM (30 days) | **Quality Score:** 0.84

---

## Implementation Recommendations

### For Analysts Using v1.0 (26 datasets)
1. **Migrate deprecated:**
   - `weekly_construction` → `street_permits`
   - `capital_blocks` → `cpdb_projects`
   - `permit_stipulations` → `permit_stipulations_historical`
   - `ramp_locations` → `ramp_progress`

2. **Add NEW datasets for enhanced analysis:**
   - Contractor datasets: Monitor vendor performance, capacity planning
   - 311 Detailed: Sidewalk-specific complaints vs generic feedback
   - Equity/Demographic: Support ADA compliance and equity requirements

### For Data Engineers
1. **Update pipelines:**
   - Add contractor/vendor data to performance tracking
   - Add 311 detailed complaints to public engagement KPIs
   - Integrate demographic/equity data for weighted equity analysis

2. **Testing:**
   - Validate API connectivity to 11 new datasets
   - Check schema compatibility with existing KPI calculations
   - Run sample queries on CPDB, 311 detailed, demographic data

### For Managers
- **Improved contractor oversight:** 3 new vendor/contract datasets
- **Enhanced equity compliance:** 6 new demographic/equity datasets
- **Better public engagement tracking:** 3 new 311 complaint datasets

---

## Migration Guide

### Code Migration Examples

**From `weekly_construction` (deprecated):**
```python
# OLD (DEPRECATED)
df = client.fetch_dataframe("data.cityofnewyork.us", "r528-jcks")

# NEW (RECOMMENDED)
df = client.fetch_dataframe("data.cityofnewyork.us", "tqtj-sjs8",
    where="$where=created_date > '2026-05-01T00:00:00'")
```

**From `capital_blocks` (empty):**
```python
# OLD (EMPTY - NO DATA)
df = client.fetch_dataframe("data.cityofnewyork.us", "jvk9-k4re")  # 0 rows

# NEW (RECOMMENDED)
df = client.fetch_dataframe("data.cityofnewyork.us", "fi59-268w")  # CPDB
```

**Adding Contractor Performance Analysis (NEW):**
```python
# NEW: Link contracts to performance
contracts = client.fetch_dataframe("data.cityofnewyork.us", "9u5s-8sd8")
inspections = client.fetch_dataframe("data.cityofnewyork.us", "ydkf-mpxb")
performance = contracts.merge(inspections, on='contractor_id')
```

**Adding Equity Analysis (NEW):**
```python
# NEW: Overlay demographics for equity impact
violations = client.fetch_dataframe("data.cityofnewyork.us", "6kbp-uz6m")
demographics = client.fetch_dataframe("data.cityofnewyork.us", "6khm-nrue")
equity_analysis = violations.merge(demographics, on='borough')
```

---

## FAQ

### Q: Should I use all 37 datasets?
**A:** No. Core operations use 7 datasets. Add contractor (3) if managing performance. Add equity (6) if required for compliance. Add 311 detailed (3) if analyzing public engagement.

### Q: Which datasets are most critical?
**A:** Core Daily (7) + Construction (6) = essential 13. Everything else is analytical/contextual.

### Q: How often should I refresh the registry?
**A:** Monthly for data freshness validation. Quarterly for schema/API changes. Annually for comprehensive audit.

### Q: Can I use deprecated datasets?
**A:** No. Use recommended alternatives. Deprecated datasets provide no operational value and may cause errors.

---

## Metadata Standards

All datasets include:
- **Fourfour ID** (Socrata identifier)
- **Status** (ACTIVE | DEPRECATED | STALE | ERROR)
- **Frequency** (DAILY | WEEKLY | MONTHLY | STATIC)
- **Rows** (dataset size for query planning)
- **Coverage** (date range)
- **URL** (direct Socrata link)
- **KPIs** (which KPIs consume this data)
- **Quality Score** (0–1; 0.9+ is production-ready)
- **SLA** (update frequency target)

---

## Sources & References

**Research Date:** 2026-06-17  
**Methodology:** Socrata API search + NYC Open Data portal review + Verification against live datasets

**Primary Sources:**
- [Street Construction Permits (2022–Present)](https://data.cityofnewyork.us/Transportation/Street-Construction-Permits-2022-Present-/tqtj-sjs8)
- [Capital Projects Database (CPDB)](https://data.cityofnewyork.us/City-Government/Capital-Projects-Database-CPDB-Projects/fi59-268w)
- [Curb and Sidewalk Complaints](https://data.cityofnewyork.us/Social-Services/Curb-and-Sidewalk-Complaints/huz9-8jhi)
- [DOT 311 Service Complaints](https://data.cityofnewyork.us/Social-Services/311-Service-Complaints-to-DOT-street-sidewalk-and-/th23-npnd)
- [NYCDOT Awarded Contracts](https://data.cityofnewyork.us/City-Government/NYCDOT-Awarded-Contracts/9u5s-8sd8)
- [Prequalified Firms](https://data.cityofnewyork.us/Housing-Development/Prequalified-Firms/szkz-syh6)
- [EquityNYC Data](https://data.cityofnewyork.us/Social-Services/Social-Indicator-Report-Data/8ek7-jxw6)
- [Demographics by Borough](https://data.cityofnewyork.us/Social-Services/Demographics-by-Borough/6khm-nrue)
- [2020 Census Tracts](https://data.cityofnewyork.us/City-Government/2020-Census-Tracts/63ge-mke6)

---

**Version:** 2.0  
**Last Updated:** 2026-06-17  
**Next Review:** 2026-07-17 (Monthly)

