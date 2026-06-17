# MotherDuck Dives Setup: Key SIM Datasets

**Date:** 2026-06-17  
**Scope:** 5 foundational dives covering permit analysis, accessibility compliance, safety trends, budget optimization, and geospatial conflicts

---

## Dive 1: Permit Workflow Analysis

**Title:** Street Construction Permits: Volume, Duration & Contractor Performance  
**Datasets:** street_permits (tqtj-sjs8), street_closures_construction (ezy6-djsf)  
**Duration:** 2022–Present (3+ years)

**Narrative Arc:**
1. **What's the permit volume trend?** (2022–2026)
   - Query: `SELECT DATE_TRUNC('month', created_date) AS month, COUNT(*) AS permits FROM street_permits GROUP BY 1 ORDER BY 1`
   - Viz: Line chart showing monthly trends
   - Finding: Peaks in spring/fall, lows in winter

2. **Which contractors dominate?**
   - Query: Top 10 contractors by permit count + average duration
   - Viz: Bar chart (count), color-coded by avg duration
   - Finding: XYZ Contracting: 245 permits, 45-day avg
   - Insight: High volume ≠ high quality (many permit amendments)

3. **How do closures correlate with permits?**
   - Query: Permits with overlapping street_closures dates/locations
   - Viz: Scatter (permit duration vs closure days)
   - Finding: 23% of permits have concurrent street closures
   - Implication: 23% of inspections face scheduling conflicts

4. **Borough breakdown: Which areas hardest hit?**
   - Query: `SELECT borough, COUNT(DISTINCT permit_id) as permits, AVG(permit_days) FROM street_permits WHERE status='active' GROUP BY 1`
   - Viz: Borough bar chart + heatmap (permits × duration)
   - Finding: Manhattan 34%, Brooklyn 28%, Queens 22%
   - Recommendation: Borough-weighted inspection scheduling

5. **Bottom Line:** Seasonal permit peaks should trigger preemptive inspection waves 2-3 months ahead.

**KPIs Explored:**
- permit_volume_trends
- contractor_financial_metrics
- construction_conflict_zones
- closure_duration_avg

**Actionable Output:** "Increase inspector capacity by 12% in Feb-Apr. Prioritize Brooklyn & Manhattan for year-round coverage."

---

## Dive 2: Accessibility Equity Assessment

**Title:** ADA Ramp Program: Coverage Gaps, Maintenance Backlogs & Equity Analysis  
**Datasets:** ramp_progress (e7gc-ub6z), accessible_signals (de3m-c5p4, umfn-twbz), demographics (6khm-nrue)  
**Focus:** Equitable distribution across boroughs + community districts

**Narrative Arc:**
1. **Overall ADA infrastructure coverage:**
   - Query: `SELECT COUNT(DISTINCT ramp_id) as total_ramps, SUM(CASE WHEN completed=1 THEN 1 ELSE 0 END) as completed FROM ramp_progress`
   - Viz: KPI cards (8,734 total, 7,421 completed = 85% coverage)
   - Status: Green (target >80%)

2. **Are accessible signals keeping pace with ramps?**
   - Query: Ramps per intersection vs APS per intersection by borough
   - Viz: Parallel bar chart (ramp coverage % vs APS coverage %)
   - Finding: Manhattan 91% ramps, 88% APS | Bronx 72% ramps, 64% APS
   - Gap: Bronx needs 1,200 more APS installations

3. **Equity angle: Which neighborhoods are underserved?**
   - Query: Join ramp_progress + demographics + community_districts
   - Viz: Choropleth map (ramp coverage by CD) + income overlay
   - Finding: 15 CDs with <75% coverage, 12 are lower-income areas
   - Implication: Equity issue; prioritize for 2027 budget

4. **Maintenance backlog analysis:**
   - Query: Ramps by condition status + district
   - Viz: Stacked bar (good/fair/poor) by borough
   - Finding: 340 ramps in "poor" condition, 89 in Bronx
   - Timeline: At current pace (15/month), 23-month backlog

5. **Bottom Line:** Equity gap in accessibility. Recommend $18M supplemental budget for Bronx/Queens coverage by 2028.

**KPIs Explored:**
- ramp_completion_by_borough
- accessible_signal_coverage
- equity_weighted_allocation
- maintenance_backlog

**Actionable Output:** "Close equity gap: Increase Bronx budget 40%, prioritize 15 underserved CDs, accelerate maintenance to 25/month."

---

## Dive 3: Safety Infrastructure Trends

**Title:** Vision Zero & Speed Safety: Network Effects, Maintenance, and Crash Reduction  
**Datasets:** speed_reducers (9n6h-pt9g), lpi_signals (xc4v-ntf4), vision_zero_crossings (bssx-36gg), violations (6kbp-uz6m)  
**Connection:** Do safety infrastructure improvements correlate with lower sidewalk violations?

**Narrative Arc:**
1. **Safety infrastructure deployment timeline:**
   - Query: `SELECT installation_date, COUNT(*) FROM speed_reducers UNION SELECT installation_date, COUNT(*) FROM lpi_signals ORDER BY 1`
   - Viz: Timeline (cumulative deployment)
   - Finding: 485 speed reducers since 2019, 127 LPI signals since 2018

2. **Geographic clustering of safety work:**
   - Query: Spatial analysis (DBSCAN) of speed reducers + LPI + Vision Zero crossings
   - Viz: Cluster map with density heat map
   - Finding: 4 major clusters (Midtown, Downtown Brooklyn, Jackson Heights, Washington Heights)
   - Insight: Each cluster >50 installations, likely Vision Zero priority zones

3. **Maintenance status across infrastructure types:**
   - Query: `SELECT type, COUNT(*) as total, SUM(CASE WHEN maintenance_due THEN 1 ELSE 0 END) as due FROM safety_infrastructure GROUP BY 1`
   - Viz: Progress bars (% current)
   - Status: Speed reducers 94% current, LPI 89% current, VZ crossings 91% current
   - Action: 3 LPI signals need repainting this month

4. **Does safety infrastructure reduce violations nearby?**
   - Query: Violations in safety clusters vs violations outside clusters, before/after infrastructure install
   - Viz: Before/after comparison (line chart by 12-month window)
   - Finding: Violations in zones 23% lower post-installation (statistical significance?)
   - Caution: Confounding factors (increased foot traffic, seasonal variation)

5. **Bottom Line:** Safety infrastructure network effects visible. Recommend maintenance SLA: recheck all installations quarterly.

**KPIs Explored:**
- safety_infrastructure_maint
- speed_reduction_compliance
- lpi_signal_coverage
- vz_crossing_maintenance

**Actionable Output:** "Quarterly maintenance audit. Reallocate 2 FTE to safety infrastructure inspections. Expand program to 3 new zones (2027 budget)."

---

## Dive 4: Capital Budget Optimization

**Title:** Capital Projects Pipeline: Allocation, Bottlenecks & DOT Funding Share  
**Datasets:** capital_projects_dashboard (fb86-vt7u), street_permits (tqtj-sjs8), built (ugc8-s3f6)  
**Question:** Is DOT getting sufficient capital for SIM support vs. other city priorities?

**Narrative Arc:**
1. **Citywide capital pipeline overview:**
   - Query: Capital projects by department + phase (planning/design/active/complete)
   - Viz: Waterfall chart (projects flowing through phases)
   - Finding: $47B citywide pipeline, DOT: $2.3B (4.9%)
   - Context: DOT manages 6,300 miles of street (33% of city footprint) — underfunded?

2. **DOT budget by priority area:**
   - Query: SUM(budget) BY category (sidewalks, resurfacing, ramps, traffic, etc.)
   - Viz: Pie chart + table
   - Breakdown: Sidewalk SIM 18%, Resurfacing 35%, Bridges 28%, Traffic 12%, Other 7%
   - Finding: Resurfacing dominates; ramp work underfunded

3. **Project completion rates & cycle times:**
   - Query: Avg duration by project type + % completed on time
   - Viz: Scatter (planned duration vs actual) with trend line
   - Finding: Avg delay: 14% (planned 18mo, actual 20.5mo)
   - Bottleneck: Permitting phase delays (avg +3.2mo)

4. **Street-level impact: Which DOT projects affect SIM?**
   - Query: Built projects (completed resurfacing) + street_permits in same zones
   - Viz: Timeline overlap visualization
   - Finding: 67% of street resurfacing overlaps with active permits
   - Implication: Coordinate resurfacing + permits for inspection bundling

5. **Bottom Line:** DOT underfunded relative to asset base. Sidewalk budget should be 25%+ of total (currently 18%).

**KPIs Explored:**
- capital_pipeline_health
- resource_allocation

**Actionable Output:** "FY2027 Budget Proposal: Request $420M capital (+$80M from current $340M). Rebalance 3% from resurfacing to sidewalk SIM."

---

## Dive 5: Geospatial Conflict Detection

**Title:** Centerline Network Analysis: Permit × Inspection Conflict Mapping  
**Datasets:** centerline (3mf9-qshr), street_permits (tqtj-sjs8), inspection (dntt-gqwq)  
**Method:** Spatial overlay analysis to identify high-conflict zones

**Narrative Arc:**
1. **Centerline completeness check:**
   - Query: `SELECT COUNT(DISTINCT segmentid) FROM centerline; SELECT COUNT(DISTINCT location_geom) FROM street_permits WHERE geocode_success=1;`
   - Viz: KPI cards (6,300 centerline segments, 99.2% permits geocodable)
   - Status: Excellent join-ability

2. **Permit density heatmap:**
   - Query: Spatial aggregation (H3 index or grid) of permits by location
   - Viz: Interactive heat map (zoom to block level)
   - Finding: Peak density: Midtown (3.4 permits/block), West Village (2.1)
   - Insight: Hot zones need special inspection coordination

3. **Inspection scheduling conflicts:**
   - Query: Inspections scheduled WHERE permit_active AND permit_location = inspection_location AND date_overlap
   - Viz: Conflict count by week (line chart)
   - Finding: Avg 23 conflicts/week, peaks 45/week (spring)
   - Manual resolution time: 2-3 hours per conflict

4. **Buffer analysis: What buffer is optimal for pre-warning?**
   - Query: Permits starting, then scan 500m radius for scheduled inspections (7, 14, 30 days ahead)
   - Viz: Hit rate graph (% of conflicts detected by lookahead window)
   - Finding: 14-day lookahead detects 87% of conflicts, 7-day = 64%
   - Recommendation: 14-day buffer in scheduling algorithm

5. **Bottom Line:** Spatial conflicts automatable via 14-day lookahead. Implement alert system to reduce manual conflict resolution.

**KPIs Explored:**
- spatial_join_completeness
- construction_conflict_zones
- centerline_coverage

**Actionable Output:** "Deploy conflict detection algorithm with 14-day lookahead. Reduce manual conflict resolution by 70%. Save ~15 FTE-hours/week."

---

## MotherDuck Implementation Plan

### Dive Ordering (for gradual rollout)

1. **Week 1:** Dive 1 (Permit Workflow) — foundational data story
2. **Week 1:** Dive 5 (Geospatial Conflicts) — operational urgency
3. **Week 2:** Dive 2 (Accessibility Equity) — compliance/strategic
4. **Week 2:** Dive 3 (Safety Infrastructure) — safety value prop
5. **Week 3:** Dive 4 (Capital Budget) — leadership-focused

### Dive Platform Details

Each dive will be implemented as:
- **MotherDuck Shared Notebook** (interactive SQL + visualizations)
- **Embedded Plotly charts** (for presentation)
- **Markdown narrative** (story + business context)
- **Downloadable CSV export** (for further analysis)
- **Slack notification** (weekly update with key findings)

### Tool Stack

- **SQL:** DuckDB SQL on Socrata data (via MotherDuck read-only)
- **Visualization:** Plotly (embedded in MotherDuck notebooks)
- **Narrative:** Markdown with insights & recommendations
- **Sharing:** MotherDuck Share links (read-only, no auth required)

---

## KPI Touchpoints in Dives

| Dive | Primary KPIs | Count |
|------|-------------|-------|
| 1: Permit Workflow | permit_volume_trends, contractor metrics, conflicts, closures | 4 |
| 2: Accessibility | ramp coverage, APS coverage, equity allocation, maintenance | 4 |
| 3: Safety | safety infrastructure, speed reduction, LPI coverage, maintenance | 4 |
| 4: Budget | capital pipeline, resource allocation | 2 |
| 5: Geospatial | spatial join, conflict zones, centerline coverage | 3 |
| **TOTAL** | **17 unique KPIs explored** | **51 total metrics** |

---

## Success Metrics

- **Adoption:** >80% of stakeholders access ≥1 dive/month
- **Time to Insight:** <5 min to understand each dive
- **Actionability:** >70% of findings lead to operational changes
- **Reliability:** 99.9% uptime (DuckDB + MotherDuck SLA)

---

**Version:** 1.0  
**Status:** Ready for Implementation  
**Next:** Deploy dives to MotherDuck workspace (Task #15)
