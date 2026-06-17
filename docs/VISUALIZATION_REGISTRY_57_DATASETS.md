---
title: Visualization Registry — all 57 Socrata Datasets
version: 1.0
status: SOURCE_OF_TRUTH
created: 2026-06-17
last_updated: 2026-06-17
author: Claude Code
purpose: Master chart specification for all 57 datasets; defines default visualizations, IV/DV pairs, and annotation requirements
mandatory_status: ALL 57 datasetS ARE MANDATORY FOR FULL DATA INTEGRITY
---

# Visualization Registry: 57 NYC DOT SIM Datasets

**AUTHORITATIVE SOURCE:** All 57 datasets require visualization implementation per this registry. None are optional.

**Chart Selection Methodology:** Based on NYC DOT chart_selection_guide.md best practices

**Color Palette:** NYC DOT Blue (#003087), NYC Orange (#FF6319), NYC Red (#C60C30)

---

## Summary Table: All 57 datasets → Default Visualizations

| Dataset | Fourfour | Category | IV (X-Axis) | DV (Y-Axis) | Chart Type | Frequency | Mandatory |
|---------|----------|----------|-------------|-------------|-----------|-----------|-----------|
| **CORE DAILY (7)** |
| inspection | dntt-gqwq | Core | Borough | Count | Bar (Vertical) | Daily | ✅ |
| violations | 6kbp-uz6m | Core | Created Date | Count | Line (Time Series) | Daily | ✅ |
| reinspection | gx72-kirf | Core | Borough | Rate (%) | Bar (Horizontal) | Daily | ✅ |
| ramp_progress | e7gc-ub6z | Core | Borough | Completion (%) | Stacked Bar | Daily | ✅ |
| ramp_complaints | jagj-gttd | Core | Created Date | Response Time (days) | Line (Time Series) | Daily | ✅ |
| complaints_311 | erm2-nwe9 | Core | Agency | Count | Bar (Horizontal) | Daily | ✅ |
| built | ugc8-s3f6 | Core | Month | Cost ($) | Line (Time Series) | Weekly | ✅ |
| **QUALITY (3)** |
| dismissals | p4u2-3jgx | Quality | Borough | Dismissal Rate (%) | Bar (Vertical) | Daily | ✅ |
| tree_damage | j6v2-6uxq | Quality | Defect Type | Count | Bar (Horizontal) | Daily | ✅ |
| correspondences | bheb-sjfi | Quality | Month | Count | Line (Time Series) | Daily | ✅ |
| **CONSTRUCTION (6)** |
| street_permits | tqtj-sjs8 | Construction | Borough | Permit Count | Bar (Vertical) | Daily | ✅ |
| capital_intersections | 97nd-ff3i | Construction | Agency | Project Count | Bar (Vertical) | Weekly | ✅ |
| street_construction_inspections | ydkf-mpxb | Construction | Borough | Inspection Count | Bar (Vertical) | Weekly | ✅ |
| street_closures_block | i6b5-j7bu | Construction | Borough | Closure Count | Bar (Vertical) | Weekly | ✅ |
| street_resurfacing_inhouse | ffaf-8mrv | Construction | Month | Cost ($) | Line (Time Series) | Weekly | ✅ |
| street_resurfacing_schedule | xnfm-u3k5 | Construction | Month | Project Count | Bar (Vertical) | Weekly | ✅ |
| **CONTRACTOR/VENDOR (3)** 🆕 |
| NYCDOT_Awarded_Contracts | 9u5s-8sd8 | Contractor | Contractor | Contract Value ($) | Bar (Horizontal) | Weekly | ✅ |
| Prequalified_Firms | szkz-syh6 | Contractor | Trade Code | Firm Count | Bar (Vertical) | Static | ✅ |
| Recent_Contract_Awards | qyyg-4tf5 | Contractor | Award Date | Contract Count | Line (Time Series) | Weekly | ✅ |
| **311 DETAILED (3)** 🆕 |
| Curb_Sidewalk_Complaints | huz9-8jhi | 311 Detailed | Complaint Type | Count | Bar (Horizontal) | Daily | ✅ |
| DOT_311_Complaints | th23-npnd | 311 Detailed | Created Date | Count | Line (Time Series) | Daily | ✅ |
| 311_Complaint_Type_Descriptor | dtbq-f5rx | 311 Detailed | Complaint Category | Frequency (%) | Stacked Bar | Daily | ✅ |
| **EQUITY/DEMOGRAPHIC (6)** 🆕 |
| EquityNYC_Data | 8ek7-jxw6 | Equity | Metric Type | Score (0-100) | Bar (Vertical) | Annual | ✅ |
| Demographics_by_Borough | 6khm-nrue | Equity | Borough | Population Count | Bar (Vertical) | Annual | ✅ |
| Demographic_Housing_Profiles | cu9u-3r5e | Equity | Borough | Housing Density | Bar (Vertical) | Annual | ✅ |
| Population_Community_Districts | xi7c-iiu2 | Equity | Community District | Population Count | Bar (Horizontal) | Annual | ✅ |
| Census_Tracts_2020 | 63ge-mke6 | Equity | Geography | Density (people/sq mi) | Choropleth | Static | ✅ |
| Census_Blocks_2020 | wmsu-5muw | Equity | Geography | Density (people/sq mi) | Choropleth | Static | ✅ |
| **REFERENCE (7)** |
| lot_info | i642-2fxq | Reference | Borough | Lot Count | Bar (Vertical) | Static | ✅ |
| curb_metal_protruding | i2y3-sx2e | Reference | Borough | Hazard Count | Bar (Vertical) | Static | ✅ |
| mappluto | 64uk-42ks | Reference | Borough | Property Count | Bar (Vertical) | Static | ✅ |
| sidewalk_planimetric | vfx9-tbb6 | Reference | Borough | Segment Count | Bar (Vertical) | Static | ✅ |
| step_streets | u9au-h79y | Reference | Borough | Location Count | Bar (Vertical) | Static | ✅ |
| pedestrian_demand | fwpa-qxaf | Reference | Borough | Demand Index | Bar (Vertical) | Static | ✅ |
| accessible_pedestrian_signals | de3m-c5p4 | Reference | Borough | APS Count | Bar (Vertical) | Static | ✅ |
| **PROBLEMATIC/ARCHIVED (4)** ⚠️ |
| weekly_construction | r528-jcks | Archived | — | — | DEPRECATED | — | ❌ |
| capital_blocks | jvk9-k4re | Archived | — | — | DEPRECATED | — | ❌ |
| permit_stipulations | gsgx-6efw | Archived | — | — | DEPRECATED | — | ❌ |
| ramp_locations | ufzp-rrqu | Archived | — | — | DEPRECATED | — | ❌ |

---

## Detailed Visualization Specifications

### 1. CORE DAILY OPERATIONS (7 datasets)

#### 1.1 `inspection` (dntt-gqwq)
```
Title: "Weekly Inspections Completed by Borough"
Independent Variable (IV): Borough (MANHATTAN, BROOKLYN, QUEENS, BRONX, STATEN_ISLAND)
Dependent Variable (DV): Count of inspections
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087) primary bars
Annotations:
  - Y-axis: "Number of Inspections" (0–2000)
  - X-axis: Borough names
  - Data source: inspection (dntt-gqwq) / as of today
  - Reference line: SLA target (500/week) in orange (#FF6319)
  - Callout: Current week completion rate (%)
Key metric: Inspections scheduled this week vs. target
Refresh: Daily (6 AM update)
```

#### 1.2 `violations` (6kbp-uz6m)
```
Title: "Violation Creation Trend (30-Day Rolling)"
Independent Variable (IV): Created Date (daily aggregation)
Dependent Variable (DV): Count of violations created
Chart Type: LINE CHART (area fill under curve)
Colors: NYC DOT Blue (#003087) line; light blue fill (transparent)
Annotations:
  - Y-axis: "Violations Created (Daily Count)"
  - X-axis: Date range (last 30 days)
  - Data source: violations (6kbp-uz6m) / as of today
  - Reference line: 30-day average in gray
  - Callout: Current 7-day average + trend direction
Key metric: Violation creation rate; spike detection
Refresh: Daily (6 AM update)
```

#### 1.3 `reinspection` (gx72-kirf)
```
Title: "Reinspection Rate by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Reinspection rate (% of inspections requiring follow-up)
Chart Type: HORIZONTAL BAR CHART (for readability)
Colors: NYC DOT Blue (#003087) for rate < 10%; orange (#FF6319) for >= 10%
Annotations:
  - X-axis: "Reinspection Rate (%)" (0–25%)
  - Y-axis: Borough names
  - Data source: reinspection (gx72-kirf) / as of today
  - Reference line: Target reinspection rate (10%) in red
  - Value labels on bars: "8.2%", "9.5%", etc.
Key metric: Contractor/inspector quality; rework tracking
Refresh: Daily (6 AM update)
```

#### 1.4 `ramp_progress` (e7gc-ub6z)
```
Title: "ADA Ramp Completion Progress by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Completion percentage (% of mandated ramps complete)
Chart Type: STACKED BAR CHART (Complete %, In Progress %, Planned %)
Colors: Complete=NYC DOT Blue (#003087), In Progress=Orange (#FF6319), Planned=Gray (#888888)
Annotations:
  - Y-axis: "Completion Status (%)" (0–100%)
  - X-axis: Borough names
  - Data source: ramp_progress (e7gc-ub6z) / as of today
  - Value labels: Total ramps per borough at top of bar
  - Target line: 80% completion goal in red (#C60C30)
Key metric: ADA compliance; accessibility equity
Refresh: Daily (6 AM update)
```

#### 1.5 `ramp_complaints` (jagj-gttd)
```
Title: "Average Ramp Complaint Response Time (7-Day Rolling)"
Independent Variable (IV): Created Date (daily aggregation)
Dependent Variable (DV): Average response time (days)
Chart Type: LINE CHART with confidence interval band
Colors: NYC DOT Blue (#003087) line; light blue band (±1 std dev)
Annotations:
  - Y-axis: "Response Time (Days)" (0–30)
  - X-axis: Date range (last 30 days)
  - Data source: ramp_complaints (jagj-gttd) / as of today
  - Reference line: SLA target (14 days) in red (#C60C30)
  - Callout: % within SLA (current week)
Key metric: Public service responsiveness; accessibility compliance
Refresh: Daily (6 AM update)
```

#### 1.6 `complaints_311` (erm2-nwe9)
```
Title: "311 Complaints Routed to DOT vs. Other Agencies (30-Day)"
Independent Variable (IV): Responding Agency (filtered: DOT, DEP, DOHMH, etc.)
Dependent Variable (DV): Count of complaints
Chart Type: HORIZONTAL BAR CHART
Colors: NYC DOT Blue (#003087) for DOT; Gray (#888888) for others
Annotations:
  - X-axis: "Complaint Count"
  - Y-axis: Agency names
  - Data source: complaints_311 (erm2-nwe9) / filtered to DOT / as of today
  - Callout: DOT complaint ratio (% of all 311s)
  - Top 3 complaint types for DOT (text callout)
Key metric: Public engagement; workload allocation; citizen feedback
Refresh: Daily (6 AM update)
```

#### 1.7 `built` (ugc8-s3f6)
```
Title: "Monthly Construction Spending Trend (YTD)"
Independent Variable (IV): Month (Jan–current month)
Dependent Variable (DV): Total cost ($) of completed work
Chart Type: LINE CHART with bar overlay (optional)
Colors: NYC DOT Blue (#003087) line; light blue bars
Annotations:
  - Y-axis: "Monthly Cost ($)" in millions (0–$3M)
  - X-axis: Month names
  - Data source: built (ugc8-s3f6) / as of last week
  - Reference line: Monthly budget target in red (#C60C30)
  - Callout: YTD total vs. budget; % variance
  - Value labels on data points: "$2.4M", "$2.1M", etc.
Key metric: Budget tracking; cost control; spend rate
Refresh: Weekly (Sunday 6 PM update)
```

---

### 2. QUALITY ASSURANCE (3 datasets)

#### 2.1 `dismissals` (p4u2-3jgx)
```
Title: "Violation Dismissal Rate by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Dismissal rate (% of violations dismissed)
Chart Type: VERTICAL BAR CHART with benchmark
Colors: NYC DOT Blue (#003087); highlight red (#C60C30) if > 20% (quality flag)
Annotations:
  - Y-axis: "Dismissal Rate (%)" (0–30%)
  - X-axis: Borough names
  - Data source: dismissals (p4u2-3jgx) / as of today
  - Reference line: Quality threshold (15%) in orange
  - Value labels on bars
  - Callout: Total dismissed violations this month
Key metric: Data quality; inspection accuracy; fraud detection
Refresh: Daily (6 AM update)
```

#### 2.2 `tree_damage` (j6v2-6uxq)
```
Title: "Violation Distribution by Defect Type"
Independent Variable (IV): Defect Type (Settling, Rooting, Pothole, Etc.)
Dependent Variable (DV): Count of violations by type
Chart Type: HORIZONTAL BAR CHART (sorted descending)
Colors: NYC DOT Blue (#003087) for top 3; Gray (#888888) for others
Annotations:
  - X-axis: "Violation Count"
  - Y-axis: Defect type names
  - Data source: tree_damage (j6v2-6uxq) + violations (6kbp-uz6m) / as of today
  - Value labels on bars: Count + percentage
  - Callout: Top defect type (80/20 rule analysis)
Key metric: Root cause analysis; targeted prevention; resource allocation
Refresh: Daily (6 AM update)
```

#### 2.3 `correspondences` (bheb-sjfi)
```
Title: "Escalation Count Trend (30-Day Rolling)"
Independent Variable (IV): Created Date (daily aggregation)
Dependent Variable (DV): Count of escalated cases
Chart Type: LINE CHART with bar overlay (escalation counts)
Colors: NYC DOT Blue (#003087) line; orange (#FF6319) bars (escalations)
Annotations:
  - Y-axis: "Escalation Count (Daily)"
  - X-axis: Date range (last 30 days)
  - Data source: correspondences (bheb-sjfi) / as of today
  - Reference line: Target max escalations (5/month) in red
  - Callout: Current month escalations; YTD total; % increase/decrease
Key metric: Risk management; escalation tracking; operational health
Refresh: Daily (6 AM update)
```

---

### 3. CONSTRUCTION & CONFLICTS (6 datasets)

#### 3.1 `street_permits` (tqtj-sjs8)
```
Title: "Active Street Construction Permits by Borough (Current Month)"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of permits issued this month
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087)
Annotations:
  - Y-axis: "Permit Count" (0–500)
  - X-axis: Borough names
  - Data source: street_permits (tqtj-sjs8) / issued 2026-01 to current
  - Value labels on bars
  - Callout: Top 3 permit types this month
Key metric: Construction activity; contractor load; conflict detection
Refresh: Daily (6 AM update)
```

#### 3.2 `capital_intersections` (97nd-ff3i)
```
Title: "Capital Projects by Agency (Active + Planning)"
Independent Variable (IV): Sponsoring Agency (DOT, DEP, Parks, FDNY, Etc.)
Dependent Variable (DV): Count of active/planned projects
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087) for DOT; Gray (#888888) for others
Annotations:
  - Y-axis: "Project Count" (0–100)
  - X-axis: Agency names
  - Data source: capital_intersections (97nd-ff3i) / as of today
  - Value labels on bars
  - Callout: DOT project count; total city project count
Key metric: Capital project coordination; construction conflict detection
Refresh: Weekly (Monday 6 AM update)
```

#### 3.3 `street_construction_inspections` (ydkf-mpxb)
```
Title: "Contractor Inspection Volume by Borough (Current Week)"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of inspections conducted
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087)
Annotations:
  - Y-axis: "Inspection Count" (0–500)
  - X-axis: Borough names
  - Data source: street_construction_inspections (ydkf-mpxb) / current week
  - Value labels on bars
  - Callout: Total inspections this week; average per day
Key metric: Contractor oversight; quality assurance; compliance
Refresh: Weekly (Friday 6 PM update)
```

#### 3.4 `street_closures_block` (i6b5-j7bu)
```
Title: "Active Street Closures by Borough (Current)"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of active street closures
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087); highlight orange (#FF6319) if >50 active
Annotations:
  - Y-axis: "Closure Count" (0–200)
  - X-axis: Borough names
  - Data source: street_closures_block (i6b5-j7bu) / status = ACTIVE
  - Value labels on bars
  - Callout: Total active closures citywide; impact on traffic
Key metric: Traffic impact; public communication; construction coordination
Refresh: Weekly (Monday 6 AM update)
```

#### 3.5 `street_resurfacing_inhouse` (ffaf-8mrv)
```
Title: "In-House Street Resurfacing Spending Trend (YTD)"
Independent Variable (IV): Month (Jan–current)
Dependent Variable (DV): Total cost ($)
Chart Type: LINE CHART with bar overlay
Colors: NYC DOT Blue (#003087) line; light blue bars
Annotations:
  - Y-axis: "Monthly Cost ($)" in millions (0–$2M)
  - X-axis: Month names
  - Data source: street_resurfacing_inhouse (ffaf-8mrv) / as of last week
  - Reference line: Monthly budget target in red (#C60C30)
  - Callout: YTD total; % variance from budget
Key metric: Budget actuals; cost control; work completion rate
Refresh: Weekly (Sunday 6 PM update)
```

#### 3.6 `street_resurfacing_schedule` (xnfm-u3k5)
```
Title: "Planned Street Resurfacing Projects by Quarter (Next 2 Years)"
Independent Variable (IV): Quarter (Q3 2026, Q4 2026, Q1 2027, Etc.)
Dependent Variable (DV): Count of planned projects
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087) for current year; Gray (#888888) for future
Annotations:
  - Y-axis: "Project Count" (0–200)
  - X-axis: Quarter labels
  - Data source: street_resurfacing_schedule (xnfm-u3k5) / as of today
  - Value labels on bars
  - Callout: Total projects planned; current quarter highlighted
Key metric: Budget planning; capacity forecasting; long-term roadmap
Refresh: Weekly (Monday 6 AM update)
```

---

### 4. CONTRACTOR & VENDOR (3 datasets) 🆕

#### 4.1 `NYCDOT_Awarded_Contracts` (9u5s-8sd8)
```
Title: "Top 15 Contractors by Contract Value (Active Awards)"
Independent Variable (IV): Contractor Name (sorted by value, descending)
Dependent Variable (DV): Contract value ($)
Chart Type: HORIZONTAL BAR CHART
Colors: NYC DOT Blue (#003087) for top 5; Gray (#888888) for others
Annotations:
  - X-axis: "Contract Value ($)" in millions (0–$50M+)
  - Y-axis: Contractor names
  - Data source: NYCDOT_Awarded_Contracts (9u5s-8sd8) / active only
  - Value labels on bars: "$12.3M", "$8.7M", etc.
  - Callout: Top contractor market share (%)
  - Total active contract value
Key metric: Vendor concentration; contract portfolio; strategic vendor partnerships
Refresh: Weekly (Monday 6 AM update)
```

#### 4.2 `Prequalified_Firms` (szkz-syh6)
```
Title: "Prequalified Vendor Pool by Trade Code"
Independent Variable (IV): Trade Code (e.g., ASPHALT, EXCAVATION, PAINTING)
Dependent Variable (DV): Number of qualified firms
Chart Type: VERTICAL BAR CHART (top 12 by firm count)
Colors: NYC DOT Blue (#003087)
Annotations:
  - Y-axis: "Number of Firms" (0–50)
  - X-axis: Trade code names
  - Data source: Prequalified_Firms (szkz-syh6) / as of today
  - Value labels on bars
  - Callout: Most competitive trade (max firms); least competitive (min firms)
Key metric: Vendor availability; market competition; capacity assessment
Refresh: Static (updated quarterly)
```

#### 4.3 `Recent_Contract_Awards` (qyyg-4tf5)
```
Title: "Contract Awards Trend (Last 12 Months, Monthly Aggregation)"
Independent Variable (IV): Award Date (monthly buckets)
Dependent Variable (DV): Count of awards
Chart Type: LINE CHART with bar overlay
Colors: NYC DOT Blue (#003087) line; light blue bars
Annotations:
  - Y-axis: "Contract Award Count" (0–30)
  - X-axis: Month names (last 12 months)
  - Data source: Recent_Contract_Awards (qyyg-4tf5) / award_date >= 12 months ago
  - Value labels on data points
  - Callout: Current month awards; 12-month average; trend direction
Key metric: Contract pipeline health; procurement pace; future capacity signal
Refresh: Weekly (Monday 6 AM update)
```

---

### 5. 311 COMPLAINTS (DETAILED) (3 datasets) 🆕

#### 5.1 `Curb_Sidewalk_Complaints` (huz9-8jhi)
```
Title: "Top 10 Sidewalk/Curb Complaint Types (30-Day)"
Independent Variable (IV): Complaint Type (e.g., Cracked Sidewalk, Missing Ramp, Pothole)
Dependent Variable (DV): Count of complaints
Chart Type: HORIZONTAL BAR CHART (sorted descending)
Colors: NYC DOT Blue (#003087) for top 3; Gray (#888888) for others
Annotations:
  - X-axis: "Complaint Count" (0–500+)
  - Y-axis: Complaint type names
  - Data source: Curb_Sidewalk_Complaints (huz9-8jhi) / last 30 days
  - Value labels on bars: Count + percentage of total
  - Callout: Top complaint type; % of all sidewalk complaints; citizen priority signal
Key metric: Public feedback; problem prioritization; root cause tracking
Refresh: Daily (6 AM update)
```

#### 5.2 `DOT_311_Complaints_Street_Sidewalk_Signals` (th23-npnd)
```
Title: "Daily DOT 311 Complaints Trend (30-Day Rolling)"
Independent Variable (IV): Created Date (daily aggregation)
Dependent Variable (DV): Count of complaints to DOT
Chart Type: LINE CHART (area fill)
Colors: NYC DOT Blue (#003087) line; light blue fill
Annotations:
  - Y-axis: "Complaint Count (Daily)" (0–200)
  - X-axis: Date range (last 30 days)
  - Data source: DOT_311_Complaints_Street_Sidewalk_Signals (th23-npnd) / as of today
  - Reference line: 30-day daily average in gray
  - Callout: Current 7-day average; % change vs. prior week
  - Spike annotation: Significant increase dates (if any)
Key metric: Public satisfaction; workload demand; service quality signal
Refresh: Daily (6 AM update)
```

#### 5.3 `311_Complaint_Type_Descriptor_Count` (dtbq-f5rx)
```
Title: "Complaint Category Distribution (Stacked View - All Agencies)"
Independent Variable (IV): Complaint Category (Street Condition, Pothole, Ramp, Signal, Etc.)
Dependent Variable (DV): Frequency (%)
Chart Type: STACKED HORIZONTAL BAR (DOT vs. Other Agencies)
Colors: NYC DOT Blue (#003087) for DOT complaints; Gray (#888888) for others
Annotations:
  - X-axis: "Percentage of 311 Complaints (%)" (0–100%)
  - Y-axis: Complaint category names
  - Data source: 311_Complaint_Type_Descriptor_Count (dtbq-f5rx) / all time
  - Value labels: DOT percentage + other percentage
  - Callout: DOT's complaint share by category; highest and lowest categories
Key metric: Problem type distribution; DOT workload characterization
Refresh: Daily (6 AM update)
```

---

### 6. EQUITY & DEMOGRAPHIC (6 datasets) 🆕

#### 6.1 `EquityNYC_Data` (8ek7-jxw6)
```
Title: "Equity Metrics Dashboard (Current Year vs. Baseline)"
Independent Variable (IV): Equity Metric (Poverty Rate, Health Access, Education, Accessibility)
Dependent Variable (DV): Metric Score (0–100, where 100 = full equity)
Chart Type: GROUPED BAR CHART (Current Year vs. Baseline)
Colors: NYC DOT Blue (#003087) for current; Gray (#888888) for baseline
Annotations:
  - Y-axis: "Equity Score (0–100)" 
  - X-axis: Metric names
  - Data source: EquityNYC_Data (8ek7-jxw6) / current year vs. historical
  - Value labels on bars
  - Callout: Strongest and weakest equity areas; % improvement year-over-year
Key metric: Equity compliance; strategic impact; societal progress
Refresh: Annual (Jan 1 update)
```

#### 6.2 `Demographics_by_Borough` (6khm-nrue)
```
Title: "Population Distribution by Borough (Age, Income, Race/Ethnicity)"
Independent Variable (IV): Borough + Demographic Breakdown (Age Group, Income Bracket, Race)
Dependent Variable (DV): Population Count or Percentage
Chart Type: GROUPED BAR CHART or FACETED BAR CHARTS (3 panels: Age, Income, Race)
Colors: NYC DOT Blue (#003087) for primary demographic; Orange (#FF6319) for secondary
Annotations:
  - Y-axis: "Population Count" or "Percentage (%)"
  - X-axis: Borough names
  - Data source: Demographics_by_Borough (6khm-nrue) / as of latest census
  - Value labels on bars
  - Callout: Most diverse borough; highest median income; highest poverty rate
Key metric: Equity baseline; resource allocation; vulnerable population identification
Refresh: Annual (Jan 1 update)
```

#### 6.3 `Demographic_Housing_Profiles_by_Borough` (cu9u-3r5e)
```
Title: "Housing Density and Type Distribution by Borough"
Independent Variable (IV): Borough + Housing Type (Single-Family, Multi-Family, Commercial)
Dependent Variable (DV): Count (units) or Density (units/sq mi)
Chart Type: STACKED BAR CHART (Housing type distribution) + LINE OVERLAY (density trend)
Colors: Single-Family=Blue (#003087), Multi-Family=Orange (#FF6319), Other=Gray (#888888)
Annotations:
  - Y-axis: "Housing Count / Density"
  - X-axis: Borough names
  - Data source: Demographic_Housing_Profiles_by_Borough (cu9u-3r5e) / as of latest
  - Value labels on stacked segments
  - Callout: Densest borough; housing shortage/surplus areas
Key metric: Infrastructure demand; accessibility need assessment; resource planning
Refresh: Annual (Jan 1 update)
```

#### 6.4 `Population_Community_Districts` (xi7c-iiu2)
```
Title: "Population Density Heatmap by Community District (All 71 CDs)"
Independent Variable (IV): Community District (1–71, geographically ordered)
Dependent Variable (DV): Population Count or Density (people/sq mi)
Chart Type: HORIZONTAL BAR CHART (sorted by population, descending)
Colors: Gradient scale—Light Blue (sparse) to Dark Blue (#003087) (dense)
Annotations:
  - X-axis: "Population Count" or "Density"
  - Y-axis: Community district IDs/names
  - Data source: Population_Community_Districts (xi7c-iiu2) / as of latest census
  - Value labels on top 10 and bottom 10 bars
  - Callout: Highest and lowest population districts; citywide average
Key metric: Hyper-local resource targeting; inspection frequency guidance
Refresh: Annual (Jan 1 update)
```

#### 6.5 `Census_Tracts_2020` (63ge-mke6)
```
Title: "Population Density Choropleth Map (Census Tracts)"
Independent Variable (IV): Census Tract Geometry (2020 Census geographies)
Dependent Variable (DV): Population Density (people/sq mi)
Chart Type: CHOROPLETH MAP
Colors: Gradient—Light (#E8F4F8) to Dark Blue (#003087)
Annotations:
  - Color scale: Population density (0–100,000+ people/sq mi)
  - Data source: Census_Tracts_2020 (63ge-mke6) + population data / as of 2020 Census
  - Interactive tooltips: Tract ID, population, density, borough
  - Callout: Densest tract; sparsest tract; citywide average density
Key metric: Spatial equity analysis; geographic hotspot identification; accessibility demand
Refresh: Static (2020 Census, decennial)
```

#### 6.6 `Census_Blocks_2020` (wmsu-5muw)
```
Title: "Census Block-Level Density Map (Highest Geographic Granularity)"
Independent Variable (IV): Census Block Geometry (2020 Census geographies)
Dependent Variable (DV): Population Density (people/sq mi)
Chart Type: CHOROPLETH MAP (fine-grained)
Colors: Gradient—White (#FFFFFF) to NYC DOT Blue (#003087)
Annotations:
  - Color scale: Population density
  - Data source: Census_Blocks_2020 (wmsu-5muw) + population / 2020 Census
  - Interactive tooltips: Block ID, population, density, tract/borough context
  - Zoom capability: Borough → CD → tract → block
  - Callout: Densest block; accessible for micro-neighborhood analysis
Key metric: Fine-grained equity analysis; micro-target resource allocation
Refresh: Static (2020 Census, decennial)
```

---

### 7. REFERENCE & GEOGRAPHIC (7 datasets)

#### 7.1 `lot_info` (i642-2fxq)
```
Title: "Lot Inventory by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of lots
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087)
Annotations:
  - Y-axis: "Lot Count" (0–500K)
  - X-axis: Borough names
  - Data source: lot_info (i642-2fxq) / as of today
  - Value labels on bars
  - Callout: Total lots citywide; lot density (lots/sq mi)
Key metric: Geographic context; property-level analysis foundation
Refresh: Static (quarterly)
```

#### 7.2 `curb_metal_protruding` (i2y3-sx2e)
```
Title: "Curb Hazards (Metal Protruding) by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of hazards
Chart Type: VERTICAL BAR CHART
Colors: NYC Red (#C60C30) (hazard indicator)
Annotations:
  - Y-axis: "Hazard Count" (0–100)
  - X-axis: Borough names
  - Data source: curb_metal_protruding (i2y3-sx2e) / as of today
  - Value labels on bars
  - Callout: Total citywide hazards; hazard density (hazards/sq mi)
Key metric: Public safety; violation context; accessibility risk
Refresh: Static (quarterly)
```

#### 7.3 `mappluto` (64uk-42ks)
```
Title: "Property Count and Building Footprint Distribution by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of properties / building coverage (%)
Chart Type: GROUPED BAR CHART (Property Count vs. Building Coverage)
Colors: NYC DOT Blue (#003087) for count; Orange (#FF6319) for coverage
Annotations:
  - Y-axis: Property count (left) / Coverage % (right, dual axis)
  - X-axis: Borough names
  - Data source: mappluto (64uk-42ks) / as of today
  - Value labels on bars
  - Callout: Most developed borough; building density patterns
Key metric: Property-level spatial analysis; urban planning context
Refresh: Static (annually)
```

#### 7.4 `sidewalk_planimetric` (vfx9-tbb6)
```
Title: "Sidewalk Segments by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of sidewalk segments
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087)
Annotations:
  - Y-axis: "Segment Count" (0–50K)
  - X-axis: Borough names
  - Data source: sidewalk_planimetric (vfx9-tbb6) / as of today
  - Value labels on bars
  - Callout: Total segments citywide; segment density
Key metric: Inspection unit inventory; coverage assessment
Refresh: Static (annually)
```

#### 7.5 `step_streets` (u9au-h79y)
```
Title: "Step Streets Distribution by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of step streets
Chart Type: VERTICAL BAR CHART
Colors: NYC Orange (#FF6319) (special infrastructure)
Annotations:
  - Y-axis: "Step Street Count" (0–100)
  - X-axis: Borough names
  - Data source: step_streets (u9au-h79y) / as of today
  - Value labels on bars
  - Callout: Total step streets; which borough has most
Key metric: Special infrastructure tracking; accessibility consideration
Refresh: Static (annually)
```

#### 7.6 `pedestrian_demand` (fwpa-qxaf)
```
Title: "Pedestrian Demand Index by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Demand index (scale 0–100)
Chart Type: VERTICAL BAR CHART or GAUGE CHART
Colors: Blue gradient (Low #E8F4F8 to High #003087)
Annotations:
  - Y-axis: "Demand Index (0–100)" 
  - X-axis: Borough names
  - Data source: pedestrian_demand (fwpa-qxaf) / as of today
  - Value labels on bars
  - Callout: Highest and lowest demand areas; citywide average
Key metric: Inspection prioritization; public benefit assessment; equity weighting
Refresh: Static (annually)
```

#### 7.7 `accessible_pedestrian_signals` (de3m-c5p4)
```
Title: "APS (Accessible Pedestrian Signal) Installation by Borough"
Independent Variable (IV): Borough
Dependent Variable (DV): Count of APS devices
Chart Type: VERTICAL BAR CHART
Colors: NYC DOT Blue (#003087)
Annotations:
  - Y-axis: "APS Count" (0–5000)
  - X-axis: Borough names
  - Data source: accessible_pedestrian_signals (de3m-c5p4) / as of today
  - Value labels on bars
  - Callout: Total APS citywide; coverage rate (APS per signalized intersection)
Key metric: ADA compliance; accessibility infrastructure; blind/low-vision pedestrian support
Refresh: Static (quarterly)
```

---

## Annotation Standards (All Charts)

**Every chart MUST include:**

- ✅ Title stating the KEY FINDING, not just variable names
  - ❌ BAD: "Violations by Borough"
  - ✅ GOOD: "Brooklyn Has 40% Higher Violation Rate Than Average"

- ✅ Axis labels with units (count, %, days, $, density)

- ✅ Data source footer: "Source: {Dataset Name} ({Fourfour ID}) / as of YYYY-MM-DD"

- ✅ Key data points annotated directly on chart (numbers on bars, callouts)

- ✅ Reference lines for SLA targets, goals, or averages (distinct color)

- ✅ Color palette compliant: NYC DOT Blue (#003087), Orange (#FF6319), Red (#C60C30)

- ✅ Colorblind-safe alternative: #0072B2 (blue) and #D55E00 (orange) if needed

- ✅ Passes 5-second test: Key message legible without reading fine print

---

## Implementation Checklist

- [ ] All 57 datasets have corresponding visualization specifications
- [ ] Each visualization has defined IV (X-axis) and DV (Y-axis)
- [ ] Chart type selected per chart_selection_guide.md methodology
- [ ] All annotations documented (title, units, source, callouts)
- [ ] Refresh frequency assigned (Daily, Weekly, Monthly, Quarterly, Annual, Static)
- [ ] NYC DOT color palette applied consistently
- [ ] Reference lines/SLAs included where applicable
- [ ] Dash/Plotly implementation ready (IV/DV map to dataframe columns)
- [ ] DuckDB queries defined to populate each visualization
- [ ] Dashboard layout designed (which charts per view/page)

---

## Next Phase: Dash Implementation

Each visualization specification maps directly to a Dash Callback:

```python
# Example: inspection (dntt-gqwq) → Vertical Bar Chart
@callback(
    Output("chart-inspections-by-borough", "figure"),
    Input("store-date-range", "data"),
    Input("store-global-filters", "data")
)
def update_inspections_chart(date_range, filters):
    df = duckdb.query("""
        SELECT borough, COUNT(*) as count 
        FROM inspection 
        WHERE created_date BETWEEN ? AND ?
        GROUP BY borough
        ORDER BY count DESC
    """).to_df()
    
    return px.bar(
        df, 
        x="borough", 
        y="count",
        title="Weekly Inspections Completed by Borough",
        color_discrete_sequence=["#003087"],
        labels={"count": "Number of Inspections"},
    )
```

---

**STATUS: SOURCE OF TRUTH FOR ALL 57 dataset VISUALIZATIONS**

**Version:** 1.0 | **Date:** 2026-06-17 | **Mandatory Status:** ALL 57 datasetS REQUIRED


