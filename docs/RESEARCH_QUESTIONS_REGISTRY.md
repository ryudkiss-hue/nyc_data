# Research Questions Registry

**Complete mapping of analyst research questions → recommended charts for Chart Finder**

All questions your Chart Finder should recognize and route to appropriate visualizations.

---

## Legend

| Category | Color | Count |
|----------|-------|-------|
| 📈 Trend & Time Series | Blue | 4 questions |
| 🗺️ Geographic & Spatial | Green | 5 questions |
| 🏢 Property Owner & Enforcement | Purple | 4 questions |
| 📊 Violation Characteristics | Red | 4 questions |
| ⚖️ Enforcement Efficiency | Orange | 4 questions |
| 🔍 Quality & Gaps | Brown | 4 questions |
| ⚠️ Risk & Prioritization | Maroon | 4 questions |
| 🔮 Predictive | Teal | 3 questions |
| 📋 Comparative | Navy | 3 questions |
| 🎯 Anomaly Detection | Crimson | 3 questions |

---

## 📈 TREND & TIME SERIES (4 Questions)

### Q1: How have violations changed over time?
**Data Patterns Trigger:** Temporal (date/time series) column

**Analytical Intent:** Understand violation volume trend direction and magnitude over months/years

**Primary Charts:**
1. **Line Chart (trend)** — Classic time series; see overall direction at a glance
2. **Area Chart (volume over time)** — Emphasis on cumulative volume; easy to see peak periods
3. **CUSUM Control Chart** — Detect process control violations; identify when shift occurred

**Secondary Charts:**
4. Ridge Plot (KDE by time period)
5. Changepoint Overlay (temporal breaks)

**Example Question Variants:**
- "Are violations increasing?"
- "How many violations per month?"
- "Show me the violation count trend"
- "What's the 12-month rolling average?"

**Data Sources (SIM):** violations (6kbp-uz6m), inspection (dntt-gqwq)

---

### Q2: What's the seasonal pattern of violations?
**Data Patterns Trigger:** Temporal (date/time series) column with monthly/quarterly granularity

**Analytical Intent:** Identify recurring cycles (e.g., winter surge in pothole violations)

**Primary Charts:**
1. **Ridge Plot (KDE by time period)** — Compare distributions across months/quarters; see seasonality clearly
2. **Area Chart (volume over time)** — Stacked by season or quarter; shows pattern
3. **Seasonal Decomposition** — Isolate trend from seasonal component

**Secondary Charts:**
4. CUSUM Control Chart
5. Line Chart (trend)

**Example Question Variants:**
- "Do we see more violations in winter?"
- "Is there a quarterly pattern?"
- "Which months are busiest?"
- "Show seasonal breakdown"

**Data Sources (SIM):** violations (6kbp-uz6m), inspection (dntt-gqwq)

---

### Q3: Is there a structural break in violation counts?
**Data Patterns Trigger:** Temporal (date/time series) column; policy/intervention date known

**Analytical Intent:** Detect if a policy change or external event caused a shift in violation trends

**Primary Charts:**
1. **Changepoint Overlay (temporal breaks)** — Highlights exact period when trend shifts
2. **CUSUM Control Chart (process shifts)** — Signals when process goes out of control
3. **Line Chart (trend)** — Visualize before/after clearly

**Example Question Variants:**
- "Did the new inspection protocol change violation rates?"
- "When did the trend shift?"
- "Show me the breakpoint"
- "Did complaint volume drop after the enforcement campaign?"

**Data Sources (SIM):** violations (6kbp-uz6m), inspection (dntt-gqwq), correspondences (bheb-sjfi)

---

### Q4: What's the forecast for next period?
**Data Patterns Trigger:** Temporal (date/time series) column; user explicitly asks "forecast" or "predict" for trend

**Analytical Intent:** Extrapolate trend into future; estimate next month/quarter violations

**Primary Charts:**
1. **Line Chart (trend)** — Show forecast as extended line with confidence band
2. **Area Chart (volume over time)** — Show projected volume with shaded confidence region

**Example Question Variants:**
- "How many violations next month?"
- "Forecast Q3 violations"
- "What's the expected count?"
- "Trend projection"

**Data Sources (SIM):** violations (6kbp-uz6m), inspection (dntt-gqwq)

---

## 🗺️ GEOGRAPHIC & SPATIAL (5 Questions)

### Q5: Where are violations concentrated?
**Data Patterns Trigger:** Geographic (lat/lon/block) column

**Analytical Intent:** Identify hotspots; answer "which blocks/neighborhoods have the most violations?"

**Primary Charts:**
1. **Heatmap (block-level density)** — Each block colored by violation count; instant visual hotspot identification
2. **Hex-Bin Map (spatial density)** — Binned hexagons for smooth density; less jitter than point scatter
3. **Choropleth (borough/CB aggregate)** — If aggregating to borough/community board level
4. **Scatter Map (lat/lon violations)** — Each violation as dot; shows individual locations

**Secondary Charts:**
5. Conflict Buffer Map (permit overlaps)

**Example Question Variants:**
- "What's the violation hotspot?"
- "Which blocks are worst?"
- "Show me Manhattan violations on a map"
- "Where should we prioritize inspections?"

**Data Sources (SIM):** violations (6kbp-uz6m) + sidewalk_planimetric (vfx9-tbb6), lot_info (i642-2fxq), mappluto (64uk-42ks)

---

### Q6: Are violations spatially clustered?
**Data Patterns Trigger:** Geographic (lat/lon/block) column; analyst asks about clustering, spatial patterns

**Analytical Intent:** Test if violations form contiguous clusters or are randomly dispersed

**Primary Charts:**
1. **DBSCAN Cluster Map (spatial groups)** — Automatically detects clusters; shows cluster membership
2. **Moran's I Scatter (spatial autocorrelation)** — Statistical test for clustering; quadrant chart shows cluster types
3. **Hex-Bin Map (spatial density)** — Visual equivalent; shows concentration

**Example Question Variants:**
- "Are violations clustered or random?"
- "Do violations cluster by block?"
- "Show me violation clusters"
- "Spatial clustering analysis"

**Data Sources (SIM):** violations (6kbp-uz6m) + sidewalk_planimetric (vfx9-tbb6), planimetric_curbs (ikvd-dex8)

---

### Q7: Which neighborhoods rank highest in violations?
**Data Patterns Trigger:** Geographic (lat/lon/block) column; hierarchical structure (borough → CB → block)

**Analytical Intent:** Rank neighborhoods by violation count or rate; compare across geographies

**Primary Charts:**
1. **Bar Chart (side-by-side)** — Each neighborhood as bar; easy ranking
2. **Lollipop Chart (ordered comparison)** — Similar to bar but cleaner; emphasizes gaps
3. **Choropleth (borough/CB aggregate)** — Color-coded map; fastest visual comparison
4. **Treemap (hierarchical ranking)** — If multi-level (borough → CB); shows both count and proportion

**Example Question Variants:**
- "Which community boards have the most violations?"
- "Rank neighborhoods by violation count"
- "Top 10 blocks"
- "Borough comparison"

**Data Sources (SIM):** violations (6kbp-uz6m) + lot_info (i642-2fxq) + mappluto (64uk-42ks) for CB/borough

---

### Q8: Is there spatial autocorrelation?
**Data Patterns Trigger:** Geographic (lat/lon/block) column; analyst explicitly asks about autocorrelation, Moran's I

**Analytical Intent:** Quantify whether violations in nearby blocks are similar (positive autocorr) or different (negative)

**Primary Charts:**
1. **Moran's I Scatter (spatial autocorrelation)** — Shows correlation statistic + quadrant classification (HH, LH, LL, LH clusters)
2. **Hex-Bin Map (spatial density)** — Visual confirmation of clustering

**Example Question Variants:**
- "Is there spatial autocorrelation in violations?"
- "Do high-violation blocks cluster together?"
- "Moran's I test"

**Data Sources (SIM):** violations (6kbp-uz6m) + sidewalk_planimetric (vfx9-tbb6)

---

## 🏢 PROPERTY OWNER & ENFORCEMENT (4 Questions)

### Q9: What's the compliance rate by owner type?
**Data Patterns Trigger:** Categorical (owner type from mappluto) + Numeric (repair status)

**Analytical Intent:** Compare enforcement outcomes across city-owned, 1-3 family, multi-unit properties

**Primary Charts:**
1. **Bar Chart (side-by-side)** — Owner type × compliance rate; easy comparison
2. **Diverging Stacked Bar (positive/negative)** — Compliant % vs non-compliant %; shows balance
3. **Dot Plot (precise comparison)** — Precise values; minimal visual clutter
4. **KPI Card (single metric)** — Overall compliance rate; executive summary

**Example Question Variants:**
- "How compliant are city-owned properties?"
- "Compare 1-3 family vs multi-unit compliance"
- "What's our overall compliance rate?"
- "Repair rate by owner type"

**Data Sources (SIM):** violations (6kbp-uz6m) + reinspection (gx72-kirf) + mappluto (64uk-42ks)

---

### Q10: Which properties are repeat offenders?
**Data Patterns Trigger:** Geographic (block/bbl) + Numeric (violation count over time window)

**Analytical Intent:** Identify properties with >2 violations in 3 years; likely structural/maintenance issues

**Primary Charts:**
1. **Outlier Scatter (flagged points)** — Flag repeat offenders; show on map or scatter
2. **Scatter Plot (2D relationship)** — X=property age, Y=violation count; identify pattern
3. **Bar Chart (side-by-side)** — Rank properties by violation count
4. **Bubble Chart (3D scatter)** — X=property value, Y=violation count, Z=days-to-repair; multi-dimensional

**Example Question Variants:**
- "Which properties have repeat violations?"
- "Show me repeat offenders"
- "Properties with >2 violations in 3 years"
- "Chronic violation problem addresses"

**Data Sources (SIM):** violations (6kbp-uz6m) + mappluto (64uk-42ks) + lot_info (i642-2fxq)

---

### Q11: How do owner types compare on enforcement metrics?
**Data Patterns Trigger:** Categorical (owner type) + Multiple numeric columns (compliance %, repair speed, cost, etc.)

**Analytical Intent:** Benchmark owner types across multiple dimensions (not just compliance)

**Primary Charts:**
1. **Grouped Bar (multi-dimensional)** — Multiple metrics side-by-side by owner type
2. **Box Plot (distribution comparison)** — Owner type × repair days; see median + spread
3. **Violin Plot (distribution by group)** — Similar to box but shows full distribution shape
4. **Radar Chart (multi-metric profile)** — Each owner type as axis; compare profiles at a glance

**Example Question Variants:**
- "Compare owner types on compliance, speed, cost"
- "Profile each owner type"
- "Multi-metric owner comparison"

**Data Sources (SIM):** violations (6kbp-uz6m) + reinspection (gx72-kirf) + mappluto (64uk-42ks) + pothole_workorders (x9wy-ing4)

---

### Q12: Does property value predict repair speed?
**Data Patterns Trigger:** Numeric (property value from mappluto) × Numeric (days to repair)

**Analytical Intent:** Test correlation; do high-value properties repair faster?

**Primary Charts:**
1. **Scatter Plot (2D relationship)** — X=assessed value, Y=days-to-repair; see trend + spread
2. **Bubble Chart (3D scatter)** — Add Z=violation severity; multi-dimensional insight
3. **Hexbin Plot (density scatter)** — If many points; shows concentration
4. **Correlation Heatmap (matrix)** — If comparing multiple property metrics

**Example Question Variants:**
- "Does property value predict repair speed?"
- "Correlation between value and compliance"
- "Do expensive properties repair faster?"

**Data Sources (SIM):** violations (6kbp-uz6m) + reinspection (gx72-kirf) + mappluto (64uk-42ks)

---

## 📊 VIOLATION CHARACTERISTICS (4 Questions)

### Q13: What's the distribution of violation types?
**Data Patterns Trigger:** Categorical (violation type or defect category)

**Analytical Intent:** Understand which defect types are most common

**Primary Charts:**
1. **Bar Chart (side-by-side)** — Violation type × count; sorted descending
2. **Stacked Bar (composition)** — If grouping by another dimension (e.g., borough × violation type)
3. **Pie Chart (simple composition)** — If 3-5 categories; proportion emphasis
4. **Histogram (distribution shape)** — If continuous violation severity score

**Example Question Variants:**
- "What types of violations do we see most?"
- "Distribution of defect types"
- "Violation type breakdown"

**Data Sources (SIM):** violations (6kbp-uz6m) + tree_damage (j6v2-6uxq), curb_metal_protruding (i2y3-sx2e), encroachments_defacements (kyvb-rbwd)

---

### Q14: How do violations rank by severity?
**Data Patterns Trigger:** Categorical (violation type) + Numeric (severity score or cost)

**Analytical Intent:** Prioritize by risk; which defect types pose highest safety/financial risk?

**Primary Charts:**
1. **Lollipop Chart (ordered comparison)** — Violation type × severity; ordered from high to low
2. **Bar Chart (side-by-side)** — Similar but bar-based
3. **Treemap (hierarchical ranking)** — If multi-level hierarchy (category → type); size = severity
4. **Bump Chart (ranking changes)** — If showing severity change over time

**Example Question Variants:**
- "Which violation types are most severe?"
- "Rank defects by risk"
- "Safety priority ranking"

**Data Sources (SIM):** violations (6kbp-uz6m) with severity scoring

---

### Q15: How long does each violation type take to repair?
**Data Patterns Trigger:** Categorical (violation type) + Numeric (days to repair)

**Analytical Intent:** Understand which defect types take longest; helps with timeline estimation

**Primary Charts:**
1. **Ridge Plot (KDE by time period)** — Violation type × days-to-repair distribution; see shape
2. **Box Plot (distribution comparison)** — Violation type × days; median + IQR
3. **Violin Plot (distribution by group)** — Similar but full distribution shape
4. **Grouped Bar (multi-dimensional)** — If comparing multiple time metrics (inspection→violation→repair)

**Example Question Variants:**
- "How long does each violation type take to repair?"
- "Average repair time by defect type"
- "Timeline by violation category"

**Data Sources (SIM):** violations (6kbp-uz6m) + reinspection (gx72-kirf)

---

### Q16: What's the cost distribution by violation type?
**Data Patterns Trigger:** Categorical (violation type) + Numeric (repair cost or city work cost)

**Analytical Intent:** Identify costliest defect types; financial prioritization

**Primary Charts:**
1. **Histogram (distribution shape)** — Cost distribution across all violations
2. **Box Plot (distribution comparison)** — Violation type × cost; compare by category
3. **Violin Plot (distribution by group)** — Similar but full shape
4. **Bubble Chart (3D scatter)** — X=violation type, Y=cost, Z=count; size = frequency

**Example Question Variants:**
- "What's the cost distribution of violations?"
- "Which defects cost most to repair?"
- "Financial impact by violation type"

**Data Sources (SIM):** violations (6kbp-uz6m) + pothole_workorders (x9wy-ing4), street_resurfacing_schedule (xnfm-u3k5)

---

## ⚖️ ENFORCEMENT EFFICIENCY (4 Questions)

### Q17: What's our overall compliance rate?
**Data Patterns Trigger:** Binary (compliant/non-compliant) or numeric (% repairs by deadline)

**Analytical Intent:** Executive summary; what % of violations are resolved?

**Primary Charts:**
1. **KPI Card (single metric)** — Large number; "78% compliance rate"
2. **Gauge Chart (target tracking)** — Visual speedometer; show vs. target
3. **Metric Sparkline (mini trend)** — Compliance rate over past 12 months

**Example Question Variants:**
- "What's our compliance rate?"
- "How many violations are repaired?"
- "Overall 75-day cure success rate"

**Data Sources (SIM):** violations (6kbp-uz6m) + reinspection (gx72-kirf)

---

### Q18: City repairs vs owner self-repairs: what's the ratio?
**Data Patterns Trigger:** Categorical (repair source: owner vs city) + Numeric (count)

**Analytical Intent:** Understand enforcement burden; how often do we have to perform city work?

**Primary Charts:**
1. **100% Stacked Bar (proportions)** — Repair source composition; emphasizes ratio
2. **Stacked Bar (composition)** — Absolute counts; emphasizes volume
3. **Sankey Diagram (flow/transitions)** — Violation → outcome flow; visual storytelling
4. **Grouped Bar (multi-dimensional)** — By owner type × repair source

**Example Question Variants:**
- "What % of violations do owners repair vs city?"
- "City work rate"
- "How often do we have to step in?"

**Data Sources (SIM):** violations (6kbp-uz6m) + reinspection (gx72-kirf) + pothole_workorders (x9wy-ing4)

---

### Q19: What's our 75-day cure window adherence?
**Data Patterns Trigger:** Temporal (notification date, repair date) + Binary (on-time/late)

**Analytical Intent:** Quality metric; are owners meeting cure deadline?

**Primary Charts:**
1. **Control Chart (SPC limits)** — Days-to-repair over time; show control limits
2. **Line Chart (trend)** — Median days-to-repair trend
3. **Gauge Chart (target tracking)** — % on-time vs. 75-day target

**Example Question Variants:**
- "What % meet the 75-day deadline?"
- "Average cure time"
- "Are we hitting our SLA?"

**Data Sources (SIM):** violations (6kbp-uz6m) + reinspection (gx72-kirf) + correspondences (bheb-sjfi)

---

### Q20: How do contractors/inspectors perform?
**Data Patterns Trigger:** Categorical (contractor/inspector ID) + Multiple numeric (cost, speed, quality)

**Analytical Intent:** Performance benchmarking; which contractors are most efficient?

**Primary Charts:**
1. **Bar Chart (side-by-side)** — Contractor × avg repair days; show performance gap
2. **Scatter Plot (2D relationship)** — X=cost, Y=days; identify efficient contractors
3. **Radar Chart (multi-metric profile)** — Contractor profile (cost, speed, quality, on-time %)
4. **Box Plot (distribution comparison)** — Contractor × cost/time distribution

**Example Question Variants:**
- "Which contractor is fastest?"
- "Contractor performance benchmark"
- "Cost efficiency by contractor"

**Data Sources (SIM):** pothole_workorders (x9wy-ing4), street_resurfacing_schedule (xnfm-u3k5), concrete_repair_schedule (78sp-6jhj)

---

## 🔍 QUALITY & GAPS (4 Questions)

### Q21: How many 311 complaints have NO matching inspection?
**Data Patterns Trigger:** Categorical (complaint status) + Temporal (date alignment)

**Analytical Intent:** Identify gaps in inspection coverage; are we responding to all complaints?

**Primary Charts:**
1. **Funnel Chart (drop-off analysis)** — 311 complaints → inspections → violations; show drop-off at each stage
2. **Sankey Diagram (flow/transitions)** — Complaint source → inspection → violation flow; visual gap identification
3. **Scatter Plot (2D relationship)** — 311 complaint locations vs inspection locations; visual gap coverage

**Example Question Variants:**
- "How many complaints have no inspection?"
- "Coverage gap analysis"
- "Are we inspecting all complaint areas?"
- "Complaint response rate"

**Data Sources:** complaints_311 (erm2-nwe9) + inspection (dntt-gqwq)

---

### Q22: What's our data completeness?
**Data Patterns Trigger:** Multiple columns, nulls/blanks

**Analytical Intent:** Data quality assessment; how complete are inspection records?

**Primary Charts:**
1. **Scorecard (quality metrics)** — Completeness %, validity %, freshness % by field
2. **Heatmap (block-level density)** — Show data coverage by block; identify areas with missing data
3. **Bar Chart (side-by-side)** — Column × null rate; identify worst columns

**Example Question Variants:**
- "What's our data completeness?"
- "Which fields have missing values?"
- "Data quality scorecard"

**Data Sources (SIM):** violations (6kbp-uz6m) + inspection (dntt-gqwq)

---

### Q23: Where are we missing inspections?
**Data Patterns Trigger:** Geographic (lat/lon) + 311 data without matched inspection

**Analytical Intent:** Coverage equity; which neighborhoods are under-inspected?

**Primary Charts:**
1. **Scatter Map (lat/lon violations)** — Show complaints with no matched inspection; identify coverage gaps
2. **Choropleth (borough/CB aggregate)** — Complaint-to-inspection ratio by neighborhood
3. **Heatmap (block-level density)** — 311 complaint density vs inspection density; identify gaps

**Example Question Variants:**
- "Which blocks have the most complaints but no inspections?"
- "Inspection coverage gaps"
- "Under-served neighborhoods"

**Data Sources:** complaints_311 (erm2-nwe9) + inspection (dntt-gqwq) + sidewalk_planimetric (vfx9-tbb6)

---

### Q24: Is inspection coverage equitable across neighborhoods?
**Data Patterns Trigger:** Geographic (borough/CB) + Numeric (inspection count or rate)

**Analytical Intent:** Equity audit; do all neighborhoods get proportional inspection resources?

**Primary Charts:**
1. **Choropleth (borough/CB aggregate)** — Color by inspection rate; visual equity assessment
2. **Box Plot (distribution comparison)** — Borough/CB × inspection count; see spread
3. **Violin Plot (distribution by group)** — Similar but full distribution shape

**Example Question Variants:**
- "Are all neighborhoods equally inspected?"
- "Inspection equity analysis"
- "Which areas are under-served?"

**Data Sources:** inspection (dntt-gqwq) + sidewalk_planimetric (vfx9-tbb6) + complaints_311 (erm2-nwe9)

---

## ⚠️ RISK & PRIORITIZATION (4 Questions)

### Q25: Which violations overlap with Vision Zero priority corridors?
**Data Patterns Trigger:** Geographic (violations location) + Categorical (Vision Zero priority flag)

**Analytical Intent:** Safety prioritization; violations in high-KSI corridors deserve faster action

**Primary Charts:**
1. **Conflict Buffer Map (permit overlaps)** — Show violations buffered against VZ corridors; highlight conflicts
2. **Scatter Map (lat/lon violations)** — Color by VZ overlap; instant visual
3. **Heatmap (block-level density)** — Violation density × VZ corridor overlap

**Example Question Variants:**
- "Which violations are in Vision Zero corridors?"
- "Safety overlap analysis"
- "High-KSI violation concentrations"

**Data Sources:** violations (6kbp-uz6m) + vzv_priority_corridors (kdda-2wcy), vzv_priority_intersections (2nj7-jxah), motor_vehicle_collisions (h9gi-nx95)

---

### Q26: Which violations are in high-pedestrian-demand areas?
**Data Patterns Trigger:** Geographic (violations location) + Numeric (pedestrian demand)

**Analytical Intent:** Impact prioritization; violations affecting more pedestrians are higher priority

**Primary Charts:**
1. **Heatmap (block-level density)** — Violation density colored by pedestrian demand
2. **Bubble Chart (3D scatter)** — X=location, Y=violation count, Z=pedestrian demand; size = impact
3. **Scatter Map (lat/lon violations)** — Color by pedestrian demand overlay

**Example Question Variants:**
- "Which violations affect the most pedestrians?"
- "High-impact violation locations"
- "Pedestrian demand hotspots"

**Data Sources:** violations (6kbp-uz6m) + pedestrian_demand (fwpa-qxaf), pedestrian_counts_biannual (2de2-6x2h)

---

### Q27: Which violations have the highest financial impact?
**Data Patterns Trigger:** Numeric (repair cost or property value) + Geographic (block)

**Analytical Intent:** Budget prioritization; which violations cost most to fix or affect highest-value properties?

**Primary Charts:**
1. **Lollipop Chart (ordered comparison)** — Block × total repair cost; ordered descending
2. **Bar Chart (side-by-side)** — Similar but bar-based
3. **Treemap (hierarchical ranking)** — Borough → CB → block; size = cost
4. **Bubble Chart (3D scatter)** — X=location, Y=violation count, Z=avg cost per violation

**Example Question Variants:**
- "Which blocks will cost most to repair?"
- "Financial impact ranking"
- "Budget allocation prioritization"

**Data Sources:** violations (6kbp-uz6m) + pothole_workorders (x9wy-ing4) + mappluto (64uk-42ks)

---

### Q28: Which neighborhoods have the highest 311 complaint volume?
**Data Patterns Trigger:** Geographic (complaint location) + Temporal (recent complaints)

**Analytical Intent:** Citizen priority; where are people most dissatisfied?

**Primary Charts:**
1. **Heatmap (block-level density)** — Complaint density; instant hotspot visual
2. **Hex-Bin Map (spatial density)** — Smoothed complaint density
3. **Scatter Map (lat/lon violations)** — Each complaint as point; color by recency

**Example Question Variants:**
- "Which neighborhoods complain most?"
- "311 complaint hotspots"
- "Citizen dissatisfaction areas"

**Data Sources:** complaints_311 (erm2-nwe9) + sidewalk_planimetric (vfx9-tbb6)

---

## 🔮 PREDICTIVE (3 Questions)

### Q29: Which properties are at risk for future violations?
**Data Patterns Trigger:** Numeric (property age, past violation count, pavement rating) + Binary (future violation)

**Analytical Intent:** Proactive inspection; identify properties likely to violate soon

**Primary Charts:**
1. **Scatter Plot (2D relationship)** — X=property age, Y=past violations; color by violation flag
2. **Bubble Chart (3D scatter)** — Add Z=pavement condition; multi-dimensional risk profile
3. **Calibration Plot (prediction accuracy)** — Show model prediction accuracy

**Example Question Variants:**
- "Which properties are at risk?"
- "Proactive inspection candidates"
- "Violation risk prediction"

**Data Sources:** violations (6kbp-uz6m) + mappluto (64uk-42ks) + street_pavement_ratings (6yyb-pb25)

---

### Q30: What's the expected repair timeline for this violation?
**Data Patterns Trigger:** Numeric (violation severity, property type, owner type, past timelines)

**Analytical Intent:** Set expectations; estimate cure window completion date

**Primary Charts:**
1. **Scatter Plot (2D relationship)** — X=severity, Y=days-to-repair; prediction fit line
2. **Line Chart (trend)** — Historical median timeline by severity
3. **Box Plot (distribution comparison)** — Severity level × days-to-repair distribution; show expected range

**Example Question Variants:**
- "How long will this violation take to repair?"
- "Estimated cure completion date"
- "Timeline prediction"

**Data Sources:** violations (6kbp-uz6m) + reinspection (gx72-kirf) + mappluto (64uk-42ks)

---

### Q31: Is this property likely to be non-compliant?
**Data Patterns Trigger:** Numeric (property characteristics, past compliance) + Binary (future non-compliance)

**Analytical Intent:** Risk flagging; prioritize enforcement resources on high-risk properties

**Primary Charts:**
1. **ROC Curve (classifier performance)** — Model discrimination; show AUC
2. **Lift Chart (model lift)** — How much better than baseline random targeting
3. **Scatter Plot (2D relationship)** — X=risk score, Y=actual compliance; calibration visual

**Example Question Variants:**
- "Will this owner comply?"
- "Non-compliance risk score"
- "Compliance prediction"

**Data Sources:** violations (6kbp-uz6m) + mappluto (64uk-42ks) + correspondences (bheb-sjfi)

---

## 📋 COMPARATIVE (3 Questions)

### Q32: How do boroughs benchmark on key metrics?
**Data Patterns Trigger:** Categorical (borough) + Multiple numeric columns (compliance %, avg days, cost, etc.)

**Analytical Intent:** Borough performance comparison; identify leaders and laggards

**Primary Charts:**
1. **Grouped Bar (multi-dimensional)** — Borough × multiple metrics side-by-side
2. **Radar Chart (multi-metric profile)** — Each borough as axis; compare profiles at glance
3. **Parallel Coordinates (multivariate)** — Borough as line; metrics as vertical axes
4. **Dot Plot (precise comparison)** — Precise values; minimal clutter

**Example Question Variants:**
- "How do boroughs compare on compliance?"
- "Borough benchmark analysis"
- "Multi-metric borough comparison"

**Data Sources:** violations (6kbp-uz6m) + mappluto (64uk-42ks) + reinspection (gx72-kirf)

---

### Q33: How do community boards rank on violations?
**Data Patterns Trigger:** Categorical (community board) + Numeric (violation count or rate)

**Analytical Intent:** Community board performance; identify high-need areas

**Primary Charts:**
1. **Choropleth (borough/CB aggregate)** — CB colored by metric; fastest visual
2. **Bar Chart (side-by-side)** — CB × metric; ordered ranking
3. **Lollipop Chart (ordered comparison)** — Similar to bar but cleaner
4. **Treemap (hierarchical ranking)** — Borough → CB; size = count

**Example Question Variants:**
- "Which community boards have most violations?"
- "CB ranking analysis"
- "Neighborhood performance"

**Data Sources:** violations (6kbp-uz6m) + lot_info (i642-2fxq) + mappluto (64uk-42ks)

---

### Q34: How do different dimensions (owner type, defect, severity) correlate?
**Data Patterns Trigger:** Multiple categorical or numeric columns; analyst asks for "multi-dimensional" or "cross-dimensional" analysis

**Analytical Intent:** Find patterns across multiple attributes; holistic view

**Primary Charts:**
1. **Parallel Coordinates (multivariate)** — Each data point as line; see multi-dimensional patterns
2. **SPLOM (scatter plot matrix)** — All pairwise relationships at once; find correlations
3. **Radar Chart (multi-metric profile)** — Profile shape comparison; good for 4-8 dimensions
4. **Clustermap (heatmap + dendro)** — Heatmap + hierarchical clustering; show relationships

**Example Question Variants:**
- "How do owner type, defect, and compliance correlate?"
- "Multi-dimensional pattern analysis"
- "Correlation across dimensions"

**Data Sources:** violations (6kbp-uz6m) + mappluto (64uk-42ks) + reinspection (gx72-kirf)

---

## 🎯 ANOMALY DETECTION (3 Questions)

### Q35: Which violations are statistical outliers?
**Data Patterns Trigger:** Numeric column (cost, days, etc.); analyst asks for outliers or anomalies

**Analytical Intent:** Identify unusual cases; may indicate data errors or real anomalies

**Primary Charts:**
1. **Outlier Scatter (flagged points)** — Flagged outliers on scatter; clear identification
2. **Isolation Forest Scatter (anomalies)** — Machine learning anomaly detection; multivariate outliers
3. **Z-Score Strip (standardized outliers)** — Standardized values; outliers >3σ flagged
4. **Scatter Plot (2D relationship)** — X=value, Y=count; outliers stand out visually

**Example Question Variants:**
- "Which violations are outliers?"
- "Unusual violations"
- "Anomaly detection"

**Data Sources:** violations (6kbp-uz6m) + pothole_workorders (x9wy-ing4)

---

### Q36: Are there unusual patterns in the violation data?
**Data Patterns Trigger:** Time series or multi-dimensional data; analyst asks for anomalies or patterns

**Analytical Intent:** Discover unexpected behaviors; data quality check or real operational anomalies

**Primary Charts:**
1. **Line Chart (trend)** — Visual inspection; spot deviations
2. **Clustermap (heatmap + dendro)** — Hierarchical clustering; spot unusual rows/columns
3. **Heatmap (block-level density)** — Spot unusual density patterns
4. **Parallel Coordinates (multivariate)** — Spot unusual line patterns

**Example Question Variants:**
- "Are there unusual patterns?"
- "Anomaly patterns in violations"
- "Unexpected trends"

**Data Sources:** violations (6kbp-uz6m), inspection (dntt-gqwq)

---

### Q37: Which properties are extreme outliers?
**Data Patterns Trigger:** Numeric property characteristics (age, value, violation count); extreme values

**Analytical Intent:** Identify properties requiring special attention; very new/old, very valuable, very problematic

**Primary Charts:**
1. **Outlier Scatter (flagged points)** — Flag extreme properties; show on map or scatter
2. **Bubble Chart (3D scatter)** — X=value, Y=age, Z=violation count; extreme cases stand out
3. **Scatter Plot (2D relationship)** — Any two dimensions; visually spot extremes
4. **Box Plot (distribution comparison)** — Show whiskers/outliers clearly

**Example Question Variants:**
- "Which properties are extreme outliers?"
- "Very new/old/valuable/problematic properties"
- "Outlier property analysis"

**Data Sources:** mappluto (64uk-42ks) + violations (6kbp-uz6m)

---

## Integration with Chart Finder

### Intent Recognition

**Chart Finder should:**
1. Parse analyst question for keywords (time, spatial, compare, predict, anomaly, etc.)
2. Match to question category
3. Score available charts by fit
4. Return top 3-5 ranked charts with confidence

### Example Recognition

**User Input:** "Show me which neighborhoods have the most violations"

**Intent Parsing:**
- Keywords: "neighborhoods", "most", "violations"
- Data Pattern: Geographic + categorical + numeric
- Question Match: Q7 (neighborhood rankings)
- Primary Charts: Choropleth, Bar, Lollipop, Treemap

**Chart Finder Output:**
```
Top recommendations for "Show me which neighborhoods have the most violations":

1. ⭐⭐⭐ Choropleth (borough/CB aggregate) 
   Map visualization; each community board colored by violation count
   
2. ⭐⭐⭐ Bar Chart (side-by-side)
   Each neighborhood as bar; ranked from highest to lowest
   
3. ⭐⭐ Lollipop Chart (ordered comparison)
   Similar to bar chart; cleaner presentation
   
4. ⭐⭐ Treemap (hierarchical ranking)
   If you also want to see borough-level summaries
```

---

## Complete Dataset Reference

All research questions leverage these 51 NYC Open Data datasets:

**Core SIM Program:**
- violations (6kbp-uz6m) — formal violation records
- inspection (dntt-gqwq) — inspector findings
- reinspection (gx72-kirf) — compliance verification
- dismissals (p4u2-3jgx) — disputed/dismissed violations
- correspondences (bheb-sjfi) — owner notifications and communications

**Property & Enforcement:**
- mappluto (64uk-42ks) — property ownership and characteristics
- lot_info (i642-2fxq) — lot information for joining

**Citizen Input:**
- complaints_311 (erm2-nwe9) — 311 complaint records

**Spatial Context:**
- sidewalk_planimetric (vfx9-tbb6) — sidewalk location basemap
- planimetric_curbs (ikvd-dex8) — curb features
- step_streets (u9au-h79y) — step streets

**Defect Classification:**
- tree_damage (j6v2-6uxq) — tree-caused damage
- curb_metal_protruding (i2y3-sx2e) — protruding hardware
- encroachments_defacements (kyvb-rbwd) — encroachments

**Construction Coordination:**
- street_permits (tqtj-sjs8) — active street permits
- street_construction_inspections (ydkf-mpxb) — active construction
- protected_streets_block (wyih-3nzf) — protected streets
- holiday_construction_embargo (bbj7-8idq) — construction embargo periods
- street_closures_block (i6b5-j7bu) — street closures

**Repair Tracking:**
- pothole_workorders (x9wy-ing4) — city pothole repairs
- street_resurfacing_schedule (xnfm-u3k5) — resurfacing schedule
- street_resurfacing_inhouse (ffaf-8mrv) — in-house resurfacing
- concrete_repair_schedule (78sp-6jhj) — concrete repair schedule

**Context & Prioritization:**
- motor_vehicle_collisions (h9gi-nx95) — crash locations
- vzv_priority_corridors (kdda-2wcy) — Vision Zero priority areas
- vzv_priority_intersections (2nj7-jxah) — VZ priority intersections
- vzv_enhanced_crossings (bssx-36gg) — high-priority crossings
- pedestrian_demand (fwpa-qxaf) — foot traffic patterns
- pedestrian_counts_biannual (2de2-6x2h) — pedestrian volume trends
- street_pavement_ratings (6yyb-pb25) — pavement condition

---

## Questions Not Yet Covered

Potential future research questions for Chart Finder expansion:

- **Equity & Fairness:** Do violation rates vary unfairly by neighborhood SES?
- **Trend Decomposition:** Separate trend from seasonality from noise
- **Survival Analysis:** Time to violation (property age → first violation)
- **Network Analysis:** Contractor relationships, inspector collaboration patterns
- **Forecasting:** ARIMA, exponential smoothing, Prophet forecasts
- **Causal Inference:** Did the new policy actually change outcomes?
- **Text Analysis:** Parse 311 complaint text for themes
- **Image Analysis:** Defect photos classification (if available)

---

## Chart Count Summary

| Category | # Questions | # Recommended Charts |
|----------|-------------|----------------------|
| Trend & Time Series | 4 | 7 |
| Geographic & Spatial | 5 | 9 |
| Property Owner | 4 | 12 |
| Violation Characteristics | 4 | 8 |
| Enforcement Efficiency | 4 | 8 |
| Quality & Gaps | 4 | 3 |
| Risk & Prioritization | 4 | 9 |
| Predictive | 3 | 3 |
| Comparative | 3 | 12 |
| Anomaly Detection | 3 | 3 |
| **TOTAL** | **37** | **65+** |

---

End of Research Questions Registry.
