# NYC DOT SIM - New Datasets Quick Reference

**Date:** 2026-06-17 | **Status:** Systematic discovery complete  
**Source:** NYC Open Data portal (Socrata API) | **Total Found:** 382 datasets

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total unique datasets from search | 382 |
| Already in SOCRATA_DATASETS_CONSOLIDATED.md | 14 |
| **NEW candidates** | **368** |
| **HIGH relevance (recommended)** | **89** |
| MEDIUM relevance | 202 |
| LOW/other | 77 |

---

## TOP 20 READY-TO-ADD (Ordered by Operational Impact)

### Group 1: CRITICAL (Permit & Conflict Detection)

1. **Street Construction Permits - Fee** | `9fnm-j6if`
   - Views: 5,009 | Downloads: 3,450 | Dept: NYC DOT
   - Why: Financial tracking + contractor accountability
   - Add to: CONTRACTS category

2. **Street Closures due to Construction** | `ezy6-djsf`
   - Views: 1,117 | Downloads: 565 | Dept: NYC DOT
   - Why: Direct conflict detection for inspection scheduling
   - Add to: TRANSPORTATION category

3. **Street Construction Permits (2013-2021)** | `c9sj-fmsg`
   - Views: 11,185 | Downloads: 2,697 | Dept: NYC DOT
   - Why: Time-series for trend analysis (fills gap from 2013-2022)
   - Add to: CONTRACTS/HISTORICAL

4. **Street Construction Permits - Cranes** | `hcv3-zacv`
   - Views: 4,173 | Downloads: 2,997 | Dept: NYC DOT
   - Why: Specialized permit type; intensive construction signal
   - Add to: CONTRACTS category

5. **Street Construction Permits - Related Agency** | `cj3v-xdpd`
   - Views: 3,444 | Downloads: 3,438 | Dept: NYC DOT
   - Why: Non-contractor street work; essential for conflict detection
   - Add to: CONTRACTS category

### Group 2: PEDESTRIAN INFRASTRUCTURE (Sidewalk Condition & Accessibility)

6. **Open Streets Locations** | `uiay-nctu`
   - Views: 84,612 | Downloads: 6,052 | Dept: NYC DOT
   - Why: Public engagement layer; conflicts with construction/inspections
   - Add to: SIDEWALK category

7. **Pedestrian Mobility Plan Demand (Map)** | `c4kr-96ik`
   - Views: 21,213 | Downloads: 17 | Dept: NYC DOT
   - Why: Strategic demand layer for SIM priority allocation
   - Add to: SIDEWALK/STRATEGIC category

8. **Accessible Pedestrian Signal Locations (Map)** | `umfn-twbz`
   - Views: 10,264 | Downloads: 10 | Dept: NYC DOT
   - Why: ADA compliance overlay; infrastructure maintenance
   - Add to: SIDEWALK/ACCESSIBILITY category

9. **Accessible Pedestrian Signal Locations (Table)** | `de3m-c5p4`
   - Views: 5,816 | Downloads: 3,099 | Dept: NYC DOT
   - Why: ADA infrastructure accountability
   - Add to: SIDEWALK/ACCESSIBILITY category

10. **NYC DOT Pedestrian Plazas (Polygon)** | `k5k6-6jex`
    - Views: 8,323 | Downloads: 4,960 | Dept: NYC DOT
    - Why: Specialized pedestrian infrastructure; SIM inspection scope
    - Add to: SIDEWALK category

### Group 3: STREET CONDITIONS & SAFETY

11. **Parking Meters Locations & Status (Map)** | `mvib-nh9w`
    - Views: 52,513 | Downloads: 20 | Dept: NYC DOT
    - Why: Sidewalk obstruction and public space conflict
    - Add to: SIDEWALK/PUBLIC SPACE category

12. **Parking Meters Locations & Status (Table)** | `693u-uax6`
    - Views: 38,384 | Downloads: 3,341 | Dept: NYC DOT
    - Why: Data version for analysis (vs. map visualization)
    - Add to: SIDEWALK/PUBLIC SPACE category

13. **Speed Reducer Tracking System (SRTS)** | `9n6h-pt9g`
    - Views: 5,333 | Downloads: 4,806 | Dept: NYC DOT
    - Why: Street safety overlay; correlates with sidewalk conditions
    - Add to: SIDEWALK/SAFETY category

14. **Leading Pedestrian Interval Signals** | `xc4v-ntf4`
    - Views: 885 | Downloads: 1,213 | Dept: NYC DOT
    - Why: Pedestrian safety infrastructure; maintenance coordination
    - Add to: TRANSPORTATION/SAFETY category

15. **Vision Zero Enhanced Crossings (Map)** | `bssx-36gg`
    - Views: 2,934 | Downloads: 378 | Dept: NYC DOT
    - Why: High-visibility crosswalks; maintenance + safety data
    - Add to: SIDEWALK/SAFETY category

### Group 4: BUDGET & VENDOR MANAGEMENT

16. **Capital Projects Dashboard** | `fb86-vt7u`
    - Views: 6,706 | Downloads: 22,469 | Dept: Mayor's Office
    - Why: Citywide capital context; resource allocation and prioritization
    - Add to: BUDGET category

17. **Bicycle Parking Shelters (Map)** | `thbt-gfu9`
    - Views: 12,017 | Downloads: 13,074 | Dept: NYC DOT
    - Why: Vendor (JCDecaux) contract tracking; street furniture obstruction
    - Add to: CONTRACTS/INFRASTRUCTURE category

18. **Bus Pad Tracking** | `eyb2-p5s8`
    - Views: 1,484 | Downloads: 1,706 | Dept: NYC DOT
    - Why: Construction + sidewalk intersection; contract status
    - Add to: CONTRACTS/CONSTRUCTION category

### Group 5: REFERENCE & GEOSPATIAL

19. **Centerline (Street Reference)** | `3mf9-qshr` or `inkn-q76z`
    - Views: 9,450 / 8,557 | Downloads: 140 / 3,337 | Dept: OTI
    - Why: Universal street reference; foundational join key
    - Add to: REFERENCE/GEOSPATIAL category

20. **MBPO Pedestrian Ramp Audit** | `8kic-uvpz`
    - Views: 3,140 | Downloads: 1,895 | Dept: Manhattan BP Office
    - Why: Borough-specific ADA compliance assessment
    - Add to: SIDEWALK/ACCESSIBILITY category

---

## By Category Summary

### SIDEWALK (43 HIGH relevance)
**Essential:** Open Streets, Pedestrian Demand, ADA Signals, Pedestrian Plazas, Parking Meters
**Recommended:** Ramp locations (map), Speed reducers, Enhanced crossings, LPI signals, Green infrastructure
**Total Tier 1:** 6-8 datasets

### CONTRACTS (8 HIGH relevance)
**Essential:** Street permits (fees, cranes, related agency, stipulations), Historical permits
**Recommended:** Bicycle parking, Bus pads, Construction work orders
**Total Tier 1:** 5-6 datasets

### BUDGET (1 HIGH relevance, 30+ MEDIUM)
**Essential:** Capital Projects Dashboard, Capital Projects (citywide >$25M)
**Recommended:** Council capital budget, DDC construction contracts, SCA project schedules
**Total Tier 1:** 2-3 datasets

### TRANSPORTATION (40 HIGH relevance)
**Essential:** Street closures, Parking meters, Enhanced crossings, Centerline reference
**Recommended:** Signal timing, Traffic data, Vision Zero infrastructure, Bicycle counts
**Total Tier 1:** 8-10 datasets

---

## What to SKIP (Already Known Issues)

| Fourfour | Name | Reason |
|----------|------|--------|
| ufzp-rrqu | Pedestrian Ramp Locations (OLD) | Stale since 2021 |
| r528-jcks | Weekly Construction | Stale since 2017 |
| jvk9-k4re | Capital Blocks | Empty (0 rows) |
| gsgx-6efw | Permit Stipulations | API 403 error |

---

## Implementation Path

### Phase 1 (This Month): Top 20 datasets
- Duration: 2-4 weeks
- Teams: 1-2 analysts + 1 engineer
- Effort: ~40-60 hours
- Deliverable: SOCRATA_DATASETS_CONSOLIDATED.md v3.0

**Action:** Review + approve Phase 1 list

### Phase 2 (Next Month): Medium-priority datasets
- Condition: Phase 1 complete + validated
- Size: ~30-50 additional datasets
- Focus: Budget, specific permit types, historical data

### Phase 3 (Ongoing): Low-priority context datasets
- As-needed basis
- Community/equity data, supplementary references

---

## Quick Checks Before Adding Each Dataset

- [ ] Last updated within SLA? (HIGH=14d, MEDIUM=30d, LOW=60d)
- [ ] API returns data? (not 403, not empty)
- [ ] Row count > 0?
- [ ] Can join to existing data? (address, block, intersection, permit ID)
- [ ] Update frequency matches operational need?

---

## File References

- **Full Report:** `NEW_DATASETS_DISCOVERY_REPORT.md` (comprehensive analysis)
- **Current Registry:** `SOCRATA_DATASETS_CONSOLIDATED.md` (v2.0, will update to v3.0)
- **KPI Mappings:** `KPI_MAPPINGS.md`
- **Entity Relationship Diagram:** `erd_37_datasets_verified.md`

---

## Contact & Questions

**Report Date:** 2026-06-17  
**Prepared for:** NYC DOT SIM Division  
**Author:** Claude Code Data Discovery Agent  
**Next Review:** After Phase 1 implementation (~2026-07-17)  

**Questions?** Email ryudkiss@gmail.com
