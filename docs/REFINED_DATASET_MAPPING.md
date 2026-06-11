# Refined Dataset Mapping — NYC DOT Project Analyst (Staff Analyst 12626)

## Job Description Analysis

**Title:** Project Analyst / Staff Analyst (Sidewalk Program)

**Key Responsibilities:**
1. Analyze locations where sidewalk repairs are needed
2. Create construction lists & identify conflicts (GIS + contract scope)
3. Report on contract progress, budget dollars, productivity
4. Perform analytical studies for contract efficiency
5. Respond to contract planning inquiries
6. Track program metrics (construction data, contract performance, budget codes)

---

## Dataset Mapping by Responsibility

### Responsibility 1: "Analyze locations where sidewalk repairs are needed"

**Datasets:**
- **violations** (18,618 rows) — Core: Sidewalk violations found during inspections
- **inspection** (3,000 rows) — Core: Inspection locations & findings
- **mappluto** (91,914 rows) — Supporting: Property/location context
- **sidewalk_planimetric** (36,369 rows) — Supporting: Detailed sidewalk geometry

**Workflows:**
- `violations-triage` — Classify violations by severity & location
- `hotspot-analysis` — Find geographic clusters of needed repairs
- `root-cause` — Investigate why certain areas have high violation rates

---

### Responsibility 2: "Create construction lists & identify conflicts (GIS + scope)"

**Datasets:**
- **street_permits** (50,629 rows) — Core: Construction permits (contract scope)
- **street_construction_inspections** (12,280 rows) — Core: Inspector findings on permit compliance
- **inspection** (3,000 rows) — Core: Sidewalk inspections (conflict with permits)
- **violations** (18,618 rows) — Core: Violations near construction sites
- **capital_blocks** (4,930 rows) — Supporting: Capital project blocks
- **capital_intersections** (4,156 rows) — Supporting: Major intersection projects
- **street_closures_block** (50,725 rows) — Supporting: Traffic impact data
- **mappluto** (91,914 rows) — Supporting: Geographic/property context

**Workflows:**
- `conflict-detect` — Identify 50m buffer overlaps between permits & inspections
- `resource-allocation` — Plan inspector routes around active construction
- `hotspot-analysis` — Find geographic conflict clusters

---

### Responsibility 3: "Report on contract progress, budget dollars, productivity"

**Datasets:**
- **street_permits** (50,629 rows) — Core: Permits (= contracts)
- **street_construction_inspections** (12,280 rows) — Core: Contract compliance inspections
- **ramp_progress** (1,356 rows) — Core: Ramp construction progress (% complete)
- **street_resurfacing_schedule** (15,215 rows) — Core: Scheduled work
- **street_resurfacing_inhouse** (1,965 rows) — Supporting: DOT-performed work
- **capital_blocks** (4,930 rows) — Supporting: Budget allocation data
- **capital_intersections** (4,156 rows) — Supporting: Budget allocation data

**Workflows:**
- `forecasting` — Predict contract completion dates
- `velocity-analysis` — Track contract progress/productivity metrics
- `sla-compliance` — Monitor contract milestone adherence
- `dataset-health` — Verify data freshness for reporting

---

### Responsibility 4: "Perform analytical studies for contract efficiency"

**Datasets:**
- **street_permits** (50,629 rows) — Core: Permit data for efficiency analysis
- **street_construction_inspections** (12,280 rows) — Core: Inspection data (quality)
- **street_closures_block** (50,725 rows) — Supporting: Traffic impact (efficiency metric)
- **complaints_311** (1.2M rows) — Supporting: Public complaints during construction

**Workflows:**
- `velocity-analysis` — Analyze contract productivity trends
- `inspector-performance` — Evaluate inspector efficiency on permit enforcement
- `root-cause` — Investigate delays or inefficiencies
- `hotspot-analysis` — Identify problematic/delayed areas

---

### Responsibility 5: "Respond to contract planning inquiries"

**Datasets:**
- **street_permits** (50,629 rows) — Core: Permit/contract details
- **street_construction_inspections** (12,280 rows) — Core: Permit status
- **capital_intersections** (4,156 rows) — Core: Project schedules
- **street_resurfacing_schedule** (15,215 rows) — Core: Work schedules

**Workflows:**
- `dataset-health` — Verify data is current for accurate responses
- `conflict-detect` — Answer "What conflicts exist?" queries

---

### Responsibility 6: "Track program metrics"

**Datasets:**
- **street_permits** (50,629 rows) — Core: Contract volume
- **street_construction_inspections** (12,280 rows) — Core: Inspection metrics
- **ramp_progress** (1,356 rows) — Core: Program progress
- **street_closures_block** (50,725 rows) — Core: Traffic impact metrics
- **violations** (18,618 rows) — Core: Repair needs
- **inspection** (3,000 rows) — Supporting: Inspection activity
- **complaints_311** (1.2M rows) — Supporting: Public satisfaction

**Workflows:**
- `sla-compliance` — Track metric SLAs
- `velocity-analysis` — Monitor productivity metrics
- `forecasting` — Project future metrics

---

## Consolidated: All Applicable Datasets

| Dataset | Primary? | Why |
|---------|----------|-----|
| **street_permits** | ✅ | Core to contract planning |
| **street_construction_inspections** | ✅ | Contract compliance |
| **violations** | ✅ | Where repairs are needed |
| **inspection** | ✅ | Sidewalk assessment |
| **ramp_progress** | ✅ | Program progress tracking |
| **street_resurfacing_schedule** | ✅ | Contract scheduling |
| **capital_blocks** | ✅ | Budget allocation |
| **capital_intersections** | ✅ | Major projects |
| **street_closures_block** | ✅ | Efficiency metrics |
| mappluto | ✓ | Geographic context |
| sidewalk_planimetric | ✓ | Sidewalk geometry |
| street_resurfacing_inhouse | ✓ | In-house work tracking |
| complaints_311 | ✓ | Public feedback |
| capital_blocks | ✓ | Budget context |

---

## Consolidated: All Applicable Workflows

### High Priority (Daily Use)
1. **violations-triage** — Where repairs are needed
2. **conflict-detect** — Construction/inspection overlaps
3. **velocity-analysis** — Contract progress & productivity
4. **sla-compliance** — Track metric adherence

### Regular Use (Weekly/Monthly)
5. **forecasting** — Predict completion dates
6. **hotspot-analysis** — Problem areas
7. **dataset-health** — Data freshness
8. **resource-allocation** — Inspector planning
9. **inspector-performance** — Permit enforcer efficiency

### As-Needed (Ad-hoc)
10. **root-cause** — Investigate delays/inefficiencies
11. **impact-assessment** — Program impact reporting

---

## Recommended Implementation Order

### Phase 1: Immediate (Core Analytics)
- `violations-triage` — Identify where repairs needed
- `conflict-detect` — Find permit/inspection conflicts
- `velocity-analysis` — Track contract progress
- Dataset: violations, street_permits, street_construction_inspections, inspection

### Phase 2: Short-term (Management Reporting)
- `sla-compliance` — Metric tracking
- `forecasting` — Completion date predictions
- `hotspot-analysis` — Geographic problem identification
- Datasets: All primary datasets + ramp_progress

### Phase 3: Ongoing (Operational Excellence)
- `inspector-performance` — Enforcement quality
- `resource-allocation` — Deployment optimization
- `root-cause` — Efficiency investigation

---

## Key Metrics to Track

Based on job responsibilities:

1. **Repair Needs Analysis**
   - Total violations identified (count)
   - Violations by borough (distribution)
   - Avg severity score (0-100)
   - Backlog size (repairs needed)

2. **Construction Conflict Analysis**
   - Conflicts detected (count)
   - Conflict rate (% of permits with overlaps)
   - Geographic clusters (hotspots)
   - Buffer distance distribution

3. **Contract Performance**
   - Contracts active (count)
   - % complete (avg progress)
   - On-time delivery rate (%)
   - Budget utilization (%)

4. **Productivity**
   - Inspections per month
   - Violations found per inspection
   - Average time-to-contract (days)
   - Efficiency trend (month-over-month)

5. **Program Metrics**
   - Ramp completion %
   - Public complaint rate
   - Data freshness (days since update)
   - SLA adherence (%)

---

## Summary

**Total Applicable Datasets:** 14 (9 primary, 5 supporting)

**Total Applicable Workflows:** 11

**Data Sources:** All 24 Socrata datasets discovered, refined to 14 most relevant for Project Analyst role

**Status:** Ready for deployment. All datasets verified against live Socrata API.
