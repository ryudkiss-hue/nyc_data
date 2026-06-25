# Phase 1 Implementation - Dataset Approval Checklist

**Date:** 2026-06-17  
**Status:** Ready for Management Approval  
**Format:** Quick reference checklist for stakeholder review  

---

## PHASE 1 DATASET LIST (20 Datasets, 28 Fourfours)

Use this checklist to approve/reject each dataset for Phase 1 implementation.

---

## TIER 1: CRITICAL (Permit & Conflict Detection)

| # | Dataset Name | Fourfour | Category | Status | Views | Approve? | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Street Construction Permits - Fee | 9fnm-j6if | CONTRACTS | ACTIVE | 5,009 | ⬜ | Financial tracking |
| 2 | Street Closures due to Construction | ezy6-djsf | TRANSPORTATION | ACTIVE | 1,117 | ⬜ | Conflict detection |
| 3 | Street Construction Permits (2013-2021) | c9sj-fmsg | CONTRACTS/HISTORICAL | ACTIVE | 11,185 | ⬜ | 9-year time-series |
| 4 | Street Construction Permits - Cranes | hcv3-zacv | CONTRACTS | ACTIVE | 4,173 | ⬜ | Equipment-level detail |
| 5 | Street Construction Permits - Related Agency | cj3v-xdpd | CONTRACTS | ACTIVE | 3,444 | ⬜ | Non-contractor work |

**Tier 1 Subtotal:** 5 datasets | **Estimated Fourfours:** 5

---

## TIER 2: PEDESTRIAN INFRASTRUCTURE

| # | Dataset Name | Fourfour | Category | Status | Views | Approve? | Notes |
|---|---|---|---|---|---|---|---|
| 6 | Open Streets Locations | uiay-nctu | SIDEWALK | ACTIVE | 84,612 | ⬜ | Public engagement (HIGH VIEW) |
| 7 | Pedestrian Mobility Plan Demand (Map) | c4kr-96ik | SIDEWALK/STRATEGIC | ACTIVE | 21,213 | ⬜ | Demand-weighted prioritization |
| 8 | Accessible Pedestrian Signals (Map) | umfn-twbz | SIDEWALK/ACCESSIBILITY | ACTIVE | 10,264 | ⬜ | ADA compliance |
| 9 | Accessible Pedestrian Signals (Table) | de3m-c5p4 | SIDEWALK/ACCESSIBILITY | ACTIVE | 5,816 | ⬜ | ADA data version |
| 10 | NYC DOT Pedestrian Plazas (Polygon) | k5k6-6jex | SIDEWALK | ACTIVE | 8,323 | ⬜ | Specialized infrastructure |
| 11 | NYC DOT Pedestrian Plazas (Map) | fnkv-pyhj | SIDEWALK | ACTIVE | 6,579 | ⬜ | Plaza visualization |

**Tier 2 Subtotal:** 6 datasets | **Estimated Fourfours:** 6

---

## TIER 3: STREET CONDITIONS & SAFETY

| # | Dataset Name | Fourfour | Category | Status | Views | Approve? | Notes |
|---|---|---|---|---|---|---|---|
| 12 | Parking Meters Locations (Map) | mvib-nh9w | SIDEWALK/PUBLIC SPACE | ACTIVE | 52,513 | ⬜ | Obstruction tracking (HIGH VIEW) |
| 13 | Parking Meters Locations (Table) | 693u-uax6 | SIDEWALK/PUBLIC SPACE | ACTIVE | 38,384 | ⬜ | Data version for analysis |
| 14 | Speed Reducer Tracking System (SRTS) | 9n6h-pt9g | SIDEWALK/SAFETY | ACTIVE | 5,333 | ⬜ | Street safety context |
| 15 | Leading Pedestrian Interval Signals | xc4v-ntf4 | TRANSPORTATION/SAFETY | ACTIVE | 885 | ⬜ | Pedestrian safety infra |
| 16 | Vision Zero Enhanced Crossings (v1) | bssx-36gg | SIDEWALK/SAFETY | ACTIVE | 2,934 | ⬜ | Maintenance coordination |

**Tier 3 Subtotal:** 5 datasets | **Estimated Fourfours:** 5

---

## TIER 4: BUDGET & VENDOR

| # | Dataset Name | Fourfour | Category | Status | Views | Approve? | Notes |
|---|---|---|---|---|---|---|---|
| 17 | Capital Projects Dashboard | fb86-vt7u | BUDGET | ACTIVE | 6,706 | ⬜ | Resource allocation |
| 18 | Bicycle Parking Shelters (Map) | thbt-gfu9 | CONTRACTS/INFRASTRUCTURE | ACTIVE | 12,017 | ⬜ | Vendor tracking |
| 19 | Bus Pad Tracking | eyb2-p5s8 | CONTRACTS/CONSTRUCTION | ACTIVE | 1,484 | ⬜ | Service continuity |

**Tier 4 Subtotal:** 3 datasets | **Estimated Fourfours:** 3

---

## TIER 5: REFERENCE & GEOSPATIAL

| # | Dataset Name | Fourfour | Category | Status | Views | Approve? | Notes |
|---|---|---|---|---|---|---|---|
| 20 | Centerline (Street Reference) | 3mf9-qshr | REFERENCE/GEOSPATIAL | ACTIVE | 9,450 | ⬜ | Universal join key |
| 21 | MBPO Pedestrian Ramp Audit | 8kic-uvpz | SIDEWALK/ACCESSIBILITY | ACTIVE | 3,140 | ⬜ | Borough ADA audit |

**Tier 5 Subtotal:** 2 datasets | **Estimated Fourfours:** 2

---

## SUMMARY COUNTS

| Tier | Datasets | Fourfours | Approve All? |
|---|---|---|---|
| **TIER 1: Critical** | 5 | 5 | ⬜ |
| **TIER 2: Infrastructure** | 6 | 6 | ⬜ |
| **TIER 3: Conditions & Safety** | 5 | 5 | ⬜ |
| **TIER 4: Budget & Vendor** | 3 | 3 | ⬜ |
| **TIER 5: Reference** | 2 | 2 | ⬜ |
| **TOTAL** | **21** | **21** | **⬜** |

---

## APPROVAL DECISION MATRIX

### For Each Dataset, Check One:

- **APPROVE** ✅ — Add to Phase 1 implementation
- **DEFER** ⏸️ — Add to Phase 2/3 (include rationale)
- **REJECT** ❌ — Skip entirely (include rationale)

### Questions to Consider:

1. **Operational Need:** Does this dataset support SIM's core mission?
2. **Data Quality:** Is it fresh (within SLA) and accessible (not 403/empty)?
3. **Integration:** Can it join to existing data on address/block/fourfour?
4. **Availability:** Are there alternatives if this dataset becomes stale?
5. **Priority:** Should this be Phase 1 or can it wait for Phase 2?

---

## KNOWN ISSUES (DO NOT ADD)

| Fourfour | Name | Issue | Action |
|----------|------|-------|--------|
| ufzp-rrqu | Pedestrian Ramp Locations | Stale since 2021 | Use ramp_progress (e7gc-ub6z) |
| r528-jcks | Weekly Construction | Stale since 2017 | Use street_permits (tqtj-sjs8) |
| jvk9-k4re | Capital Blocks | Empty (0 rows) | Use cpdb_projects (fi59-268w) |
| gsgx-6efw | Permit Stipulations | API 403 error | Use pbk5-6r7z (historical) |

**Status:** These are documented as SKIP in all discovery reports.

---

## SCORING RUBRIC (Optional)

Use this to score each dataset on 1-5 scale:

| Criterion | Weight | Scale |
|-----------|--------|-------|
| **Operational Impact** | 35% | 1=Nice-to-have → 5=Critical |
| **Data Quality** | 25% | 1=Poor → 5=Excellent |
| **Integration Effort** | 20% | 1=Complex → 5=Simple |
| **Availability** | 15% | 1=Stale/Risky → 5=Fresh/Reliable |
| **OVERALL SCORE** | 100% | **(Weighted Average)** |

**Recommendation Threshold:** ≥ 3.5/5 = Approve for Phase 1

---

## APPROVAL SIGN-OFF

| Role | Name | Signature | Date |
|------|------|-----------|------|
| **Data Steward** | _____ | _____ | _____ |
| **SIM Program Manager** | _____ | _____ | _____ |
| **Technical Lead** | _____ | _____ | _____ |
| **Data Engineer** | _____ | _____ | _____ |

---

## NEXT STEPS (After Approval)

### Week 1:
- [ ] Distribute this checklist to stakeholders
- [ ] Collect approval decisions (Approve/Defer/Reject per dataset)
- [ ] Create approval log documenting rationales
- [ ] Confirm final Phase 1 list

### Week 2-3:
- [ ] Fetch metadata for approved datasets via Socrata API
- [ ] Pull 100-row samples from each dataset
- [ ] Run quality_score() assessments
- [ ] Validate join keys in DuckDB
- [ ] Document all columns and data types

### Week 4:
- [ ] Update SOCRATA_DATASETS_CONSOLIDATED.md → v3.0
- [ ] Add datasets to KPI_MAPPINGS.md
- [ ] Update ERD with new relationships
- [ ] Create sample Dash visualization

---

## DOCUMENTS FOR REFERENCE

| Document | When to Read |
|----------|---|
| **SIM_DATASET_DISCOVERY_FINAL_REPORT.md** | Comprehensive strategy & roadmap |
| **NEW_DATASETS_QUICK_REFERENCE.md** | 5-min executive briefing |
| **DISCOVERY_SUMMARY.txt** | High-level overview |
| **NEW_DATASETS_DISCOVERY_REPORT.md** | Detailed analysis of all 89 datasets |
| **NEW_DATASETS_FOURFOUR_REFERENCE.md** | Technical reference (fourfours by category) |

---

**Prepared:** 2026-06-17  
**For:** SIM Division Management & Technical Team  
**Contact:** ryudkiss@gmail.com  
**Project:** C:\Users\ryudk\Desktop\nyc_data\
