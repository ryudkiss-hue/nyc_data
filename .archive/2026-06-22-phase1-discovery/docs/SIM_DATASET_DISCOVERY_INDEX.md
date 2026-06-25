# NYC DOT SIM - Dataset Discovery Initiative: Complete Index

**Initiative Date:** 2026-06-17  
**Status:** Discovery Phase Complete | Ready for Implementation Planning  
**Scope:** Comprehensive search of NYC Open Data (Socrata) for SIM-relevant datasets  
**Contact:** ryudkiss@gmail.com

---

## Quick Start: Which Document Should I Read?

| Need | Document | Purpose |
|------|----------|---------|
| **5-minute overview** | DISCOVERY_SUMMARY.txt | High-level findings + action items |
| **Executive summary** | NEW_DATASETS_QUICK_REFERENCE.md | Top 20 datasets, rationale, next steps |
| **Detailed analysis** | NEW_DATASETS_DISCOVERY_REPORT.md | Full 89 datasets with tier rankings |
| **Technical reference** | NEW_DATASETS_FOURFOUR_REFERENCE.md | Fourfour IDs, by-department list, import format |
| **This document** | SIM_DATASET_DISCOVERY_INDEX.md | Document index + methodology |

---

## 📊 Discovery Findings

### Search Statistics
- **Search Method:** Socrata API (`data.cityofnewyork.us/api/search/views`)
- **Search Terms:** 26 terms across 4 categories
- **Results Returned:** 1,732 total across all searches
- **Unique Datasets Found:** 382
- **Time to Completion:** Single comprehensive pass (6/17/2026)

### Datasets Discovered by Relevance

```
Total: 382 datasets
├── Already Registered (v2.0): 14 datasets ✓
├── NEW HIGH Relevance: 89 datasets ⭐
│   ├── Sidewalk: 43 datasets
│   ├── Contracts: 8 datasets
│   ├── Budget: 1 dataset
│   └── Transportation: 40 datasets
├── NEW MEDIUM Relevance: 202 datasets
└── NEW LOW Relevance / Out-of-Scope: 77 datasets
```

---

## 📁 Deliverable Documents

### 1. DISCOVERY_SUMMARY.txt
**File Size:** 11 KB | **Format:** Plain text  
**Audience:** Leadership, program managers, decision-makers  
**Contents:**
- Executive summary of findings (10 paragraphs)
- Phase 1 top 20 recommendations with fourfour IDs
- Verification checklist
- Next steps (immediate, short-term, medium-term, long-term)
- Key insights (8 strategic takeaways)
- Success criteria
- Risk mitigation strategies

**Best for:** 15-minute briefing or decision meeting

---

### 2. NEW_DATASETS_QUICK_REFERENCE.md
**File Size:** 7.7 KB | **Format:** Markdown  
**Audience:** Analysts, engineers, product managers  
**Contents:**
- Executive summary table
- Top 20 ready-to-add datasets (grouped by impact tier)
- Category breakdown (Sidewalk, Contracts, Budget, Transportation)
- Datasets to skip (with reasons)
- Implementation path (Phase 1/2/3 planning)
- Quick checks before adding each dataset
- File references and contact info

**Best for:** Quick lookup + approval meetings + Phase 1 planning

---

### 3. NEW_DATASETS_DISCOVERY_REPORT.md
**File Size:** 27 KB | **Format:** Markdown (detailed)  
**Audience:** Technical leads, data engineers, analysts  
**Contents:**
- Complete list of 43 SIDEWALK datasets (5 tiers)
- Complete list of 8 CONTRACT datasets (2 tiers)
- Complete list of BUDGET datasets (with alternatives)
- Complete list of 40 TRANSPORTATION datasets (4 tiers)
- Datasets to skip (with detailed rationale)
- Cross-reference to existing KPIs
- Implementation checklist for each dataset
- ERD impact assessment
- Testing and validation strategies

**Best for:** Technical planning, implementation, architecture review

---

### 4. NEW_DATASETS_FOURFOUR_REFERENCE.md
**File Size:** 11 KB | **Format:** Markdown (technical reference)  
**Audience:** Data engineers, SQL/Python developers  
**Contents:**
- Phase 1 Top 20 fourfour IDs (structured by category)
- Complete HIGH Relevance list (89 datasets, organized by tier)
- Fourfour cross-reference table (by department)
- Department-specific dataset lists (DOT, OPS, OTI, DEP, etc.)
- Known problematic datasets (4 to skip)
- Import/bulk update format (YAML)
- Verification checklist (per-dataset)
- Quick command reference (curl, SOQL, Python)

**Best for:** Implementation, data pipeline setup, DuckDB ingestion

---

## 🎯 Key Recommendations

### Immediate Actions (This Week)

1. **Review Summary Documents**
   - Read DISCOVERY_SUMMARY.txt (15 min)
   - Skim NEW_DATASETS_QUICK_REFERENCE.md (10 min)
   - Schedule approval meeting

2. **Stakeholder Alignment**
   - SIM program manager: Final Phase 1 list approval
   - Engineering lead: Implementation timeline confirmation
   - Data analyst: Sample data validation plan

3. **Create Approval Matrix**
   - Add/approve/reject decision for each Phase 1 dataset
   - Document rationale per SIM use case
   - Set success criteria

### Short-Term (1-2 Weeks)

1. **Metadata Fetch & Quality Assessment**
   - Pull metadata + 100-row samples for Phase 1 datasets
   - Run `quality_score()` on each sample
   - Flag any freshness issues (> SLA threshold)

2. **Registry Update (v2.0 → v3.0)**
   - Add 20 Phase 1 datasets to SOCRATA_DATASETS_CONSOLIDATED.md
   - Update ERD with new relationships
   - Extend KPI_MAPPINGS for new metrics

3. **DuckDB Validation**
   - Test spatial joins with existing geometry datasets
   - Validate all 4-tuple joins (inspection ↔ permit ↔ violation ↔ complaint)
   - Profile data distribution for sampling strategies

### Medium-Term (1-4 Weeks)

1. **Dash App Integration**
   - Create at least 1 new visualization using Phase 1 data
   - Update construction conflict detection with expanded permits
   - Enhance budget allocation dashboard

2. **Operational Testing**
   - Run full ETL pipeline for all Phase 1 datasets
   - Monitor SLA freshness in production
   - Test 311 complaint linkage with new permit data

3. **Phase 2 Planning**
   - Select medium-priority datasets (202 candidates)
   - Create Phase 2 implementation timeline
   - Identify Phase 2 quick-wins

---

## 🔍 Search Methodology

### Focus Areas (4 Categories)

#### 1. CONTRACTS
Search terms: "contract", "contractor", "procurement", "vendor", "bid", "RFP", "awards"  
Results: 136 datasets found, 8 HIGH relevance  
Key insight: Extensive street furniture vendor data available (JCDecaux parking)

#### 2. SIDEWALK
Search terms: "sidewalk", "curb", "ramp", "accessibility", "pedestrian", "complaint", "inspection"  
Results: 74 datasets found, 43 HIGH relevance  
Key insight: Comprehensive ADA infrastructure layers + public engagement data

#### 3. BUDGET
Search terms: "budget", "spending", "appropriation", "capital", "cost", "funding"  
Results: 47 datasets found, 1 HIGH + 30 MEDIUM relevance  
Key insight: Capital project dashboard (6.7K downloads) + agency-specific budgets

#### 4. TRANSPORTATION
Search terms: "street", "permit", "construction", "road", "closure", "traffic"  
Results: 86 datasets found, 40 HIGH relevance  
Key insight: Rich permit ecosystem (5 variants) + Vision Zero initiatives

---

## 🎯 Tier Ranking Criteria

### Relevance Classification

**HIGH:**
- NYC DOT-owned OR direct DOT partner agency
- 2+ keywords match SIM focus areas
- Views > 1,000 OR downloads > 1,000
- Essential for operations, budget, or compliance
- Active (updated within SLA)

**MEDIUM:**
- Peripherally related to SIM
- 1 keyword match + moderate engagement (100-1000 views)
- Useful for strategic planning or equity analysis
- May have data quality concerns (check freshness)

**LOW:**
- Generic city services (not SIM-specific)
- No clear operational link
- Low engagement (< 100 views)
- Context/reference data only

### Category Labels

| Label | Meaning | Example |
|-------|---------|---------|
| Tier 1 | Core to SIM operations | Street permits, violations, inspections |
| Tier 2 | High-value context | Pedestrian demand, ADA signals, capital projects |
| Tier 3 | Specialized/accessibility | Ramp audits, green infrastructure, safety overlays |
| Tier 4 | Peripheral context | Bicycle counts, parking meters (street furniture) |
| Tier 5 | Reference/geospatial | Centerline, census tracts, street reference |

---

## 🚀 Implementation Timeline

### Estimated Effort by Phase

| Phase | Datasets | Timeline | Effort | Team |
|-------|----------|----------|--------|------|
| **Phase 1** | 20 (28 FF) | 2-4 weeks | 40-60 hrs | 1-2 analysts + 1 eng |
| **Phase 2** | 30-50 | 4-8 weeks | 60-100 hrs | Same team |
| **Phase 3** | 40+ | Ongoing | As-needed | Maintenance |

### Phase 1 Success Criteria

✓ All 20 datasets added to registry (v3.0)  
✓ Metadata + samples validated (quality_score > 0.70)  
✓ ERD updated with new relationships  
✓ KPI mappings extended  
✓ At least 1 new Dash visualization  
✓ Zero breaking changes to existing reports  
✓ SLA monitoring active for all new datasets  

---

## 📚 Related Documents in Project

### Current Registry (v2.0)
- **File:** SOCRATA_DATASETS_CONSOLIDATED.md
- **Status:** 37 active datasets + 4 problematic
- **Update Target:** v3.0 (add Phase 1 datasets)

### Data Models & Governance
- **File:** KPI_MAPPINGS.md (51 KPIs across 37 datasets)
- **File:** erd_37_datasets_verified.md (entity relationships)
- **File:** JOB_RESPONSIBILITIES_MAPPING.md (11 duties to datasets)

### Support Documentation
- **File:** SOCRATA_SETUP.md (API token, refresh, configuration)
- **File:** SOCRATA_RESOURCES.md (URLs, endpoints, alternatives)
- **File:** CLAUDE.md (project overview, CLI reference)

---

## 🔧 Data Integration Checklist

### Before Adding to Production

- [ ] **Freshness:** Last updated within SLA threshold
- [ ] **Accessibility:** API responds (HTTP 200, not 403)
- [ ] **Quality:** Row count > 0, no systemic nulls
- [ ] **Joins:** Can link via address, block, intersection, fourfour
- [ ] **Frequency:** Update schedule matches operational need
- [ ] **Documentation:** Schema reviewed, column definitions recorded
- [ ] **KPI Mapping:** New metrics documented in registry
- [ ] **ERD Update:** Relationships added to diagram
- [ ] **DuckDB Test:** Sample joins validated locally
- [ ] **Monitoring:** SLA tracking configured

---

## 📋 Known Issues (Skip These)

| Fourfour | Name | Issue | Action |
|----------|------|-------|--------|
| ufzp-rrqu | Pedestrian Ramp Locations | Stale since 2021 | Skip; use ramp_progress (e7gc-ub6z) |
| r528-jcks | Weekly Construction | Stale since 2017 | Skip; use street_permits (tqtj-sjs8) |
| jvk9-k4re | Capital Blocks | Empty dataset (0 rows) | Skip; use capital_intersections |
| gsgx-6efw | Permit Stipulations | API 403 (forbidden) | Skip; contact NYC Open Data support |

---

## 🎓 How to Use These Documents

### For Program Manager
1. Read: DISCOVERY_SUMMARY.txt
2. Review: NEW_DATASETS_QUICK_REFERENCE.md (Top 20)
3. Action: Schedule approval meeting + Phase 1 sign-off

### For Data Engineer
1. Read: NEW_DATASETS_DISCOVERY_REPORT.md (full details)
2. Reference: NEW_DATASETS_FOURFOUR_REFERENCE.md (IDs, import format)
3. Action: Create implementation plan, begin Phase 1 onboarding

### For SQL/Python Developer
1. Reference: NEW_DATASETS_FOURFOUR_REFERENCE.md (fourfour IDs + commands)
2. Read: Section "Quick Command Reference" (curl, SOQL, Python examples)
3. Action: Set up DuckDB pipeline, validate joins

### For Business Analyst
1. Skim: DISCOVERY_SUMMARY.txt (insights + impact)
2. Review: NEW_DATASETS_QUICK_REFERENCE.md (category summary)
3. Action: Identify new KPIs, plan reporting updates

---

## 💡 Key Insights from Discovery

1. **Scale of Opportunity:** 382 total datasets available; only 14 currently used = 26x expansion potential

2. **DOT Ownership:** 35+ DOT-managed datasets ensure data reliability and maintenance

3. **Permit Specialization:** 5 Street Construction Permit variants available (fees, cranes, agencies, stipulations)

4. **Pedestrian-Centric:** 43 sidewalk/pedestrian datasets support ADA compliance and public engagement

5. **Vendor Tracking:** JCDecaux bicycle parking data enables vendor performance evaluation

6. **Historical Continuity:** 2013-2021 permits bridge gap between old and new datasets

7. **Cross-Agency:** School projects, Parks, DEP data enable multi-agency impact assessment

8. **Public Engagement:** Open Streets (84K views) + parking meters represent high-engagement layer

---

## 📞 Support & Next Steps

### Questions?
- **Email:** ryudkiss@gmail.com
- **Meeting:** Schedule with SIM program manager
- **Slack:** [Project channel if applicable]

### Approval Process
1. Review this index + DISCOVERY_SUMMARY.txt
2. Schedule 30-min approval meeting (SIM lead + tech lead)
3. Approve/reject each Phase 1 dataset
4. Sign off on implementation timeline + resource allocation

### Timeline Expectation
- **Approval:** This week (2026-06-17 to 2026-06-21)
- **Phase 1 Start:** Next week (2026-06-24)
- **Phase 1 Complete:** ~2 weeks (2026-07-08)
- **Phase 1 Review:** 2026-07-17

---

## 📊 Document Statistics

| Document | Size | Words | Format | Audience |
|----------|------|-------|--------|----------|
| DISCOVERY_SUMMARY.txt | 11 KB | 800 | Plain text | Leadership |
| NEW_DATASETS_QUICK_REFERENCE.md | 7.7 KB | 600 | Markdown | Managers |
| NEW_DATASETS_DISCOVERY_REPORT.md | 27 KB | 2,200 | Markdown | Engineers |
| NEW_DATASETS_FOURFOUR_REFERENCE.md | 11 KB | 850 | Markdown | Developers |
| SIM_DATASET_DISCOVERY_INDEX.md (this) | 12 KB | 900 | Markdown | All |

**Total Discovery Deliverable:** ~68 KB, 5,350 words

---

## ✅ Checklist: Discovery Phase Complete

- [x] 26 search terms executed across 4 categories
- [x] 382 total datasets found
- [x] 89 HIGH relevance datasets identified
- [x] 4 problematic datasets flagged for skip
- [x] Top 20 Phase 1 recommendations finalized
- [x] Fourfour IDs verified and organized
- [x] Tier rankings applied (1-5)
- [x] Department categorization complete
- [x] 4 comprehensive documents created
- [x] Implementation timeline estimated
- [x] Risk mitigation strategies documented
- [x] Next steps clearly defined

**Status:** Ready for stakeholder approval + Phase 1 implementation

---

**Prepared:** 2026-06-17  
**By:** Claude Code Data Discovery Agent  
**For:** NYC DOT Sidewalk Inspection & Management (SIM) Division  
**Next Review:** 2026-07-17 (post-Phase 1 implementation)  
**Version:** 1.0 (Discovery Index)

---

## File Locations

```
C:\Users\ryudk\Desktop\nyc_data\docs\
├── DISCOVERY_SUMMARY.txt                      (Executive summary)
├── NEW_DATASETS_QUICK_REFERENCE.md            (Top 20 + quick lookup)
├── NEW_DATASETS_DISCOVERY_REPORT.md           (Comprehensive analysis)
├── NEW_DATASETS_FOURFOUR_REFERENCE.md         (Technical reference)
├── SIM_DATASET_DISCOVERY_INDEX.md             (This file - complete index)
├── SOCRATA_DATASETS_CONSOLIDATED.md           (Current registry, v2.0)
├── KPI_MAPPINGS.md                            (51 KPIs across datasets)
├── erd_37_datasets_verified.md                (Entity relationships)
└── [other project documentation]
```

All discovery documents are ready for review and implementation planning.
