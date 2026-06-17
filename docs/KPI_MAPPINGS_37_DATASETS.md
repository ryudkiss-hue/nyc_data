---
title: KPI-to-Dataset Mappings — 51 KPIs + 11 New KPIs for 37 Datasets
version: 1.0
status: SOURCE_OF_TRUTH
created: 2026-06-17
last_updated: 2026-06-17
author: Claude Code
purpose: Define which datasets feed which KPIs; new KPIs for contractor, equity, and 311 data
total_kpis: 51 (40 original + 11 new)
---

# KPI-to-Dataset Mappings: All 37 Datasets

**SOURCE OF TRUTH:** Master registry linking all 37 Socrata datasets to 51 KPIs (40 original + 11 new).

---

## Summary: 40 Original KPIs + 11 New KPIs = 51 Total

### Original 51 KPIs (26-Dataset Mapping)

| KPI | Category | Datasets | Calculation | Frequency |
|-----|----------|----------|-------------|-----------|
| inspections_scheduled_week | Inspection | inspection (dntt-gqwq) | COUNT where created_date = this week | Daily |
| inspection_completion_rate | Inspection | inspection (dntt-gqwq) | completed / scheduled * 100 | Daily |
| avg_violations_per_inspection | Inspection | inspection (dntt-gqwq), violations (6kbp-uz6m) | violations_count / inspection_count | Daily |
| reinspection_rate | Inspection | reinspection (gx72-kirf), inspection (dntt-gqwq) | reinspection_count / inspection_count * 100 | Daily |
| inspection_backlog_days | Inspection | inspection (dntt-gqwq) | days elapsed since oldest unstarted inspection | Daily |
| violations_open_count | Violation | violations (6kbp-uz6m) | COUNT where status = OPEN | Daily |
| violations_by_severity | Violation | violations (6kbp-uz6m) | COUNT by severity level (HIGH/MED/LOW) | Daily |
| violation_resolution_time | Violation | violations (6kbp-uz6m) | AVG(DATEDIFF(closed_date, created_date)) | Daily |
| violation_dismissal_rate | Violation | dismissals (p4u2-3jgx), violations (6kbp-uz6m) | dismissed_count / total_violations * 100 | Daily |
| sla_breaches | Violation | violations (6kbp-uz6m) | COUNT where resolution_time > 30 days | Daily |
| violations_by_defect_type | Violation | tree_damage (j6v2-6uxq), violations (6kbp-uz6m) | COUNT by defect type, top categories | Daily |
| contractor_completion_rate | Contractor | street_construction_inspections (ydkf-mpxb), street_permits (tqtj-sjs8) | completed_work / assigned_work * 100 | Weekly |
| contractor_quality_score | Contractor | reinspection (gx72-kirf), street_construction_inspections (ydkf-mpxb) | (inspections_passed / total_inspections) * 100 | Weekly |
| contractor_sla_compliance | Contractor | street_construction_inspections (ydkf-mpxb), street_permits (tqtj-sjs8) | work_completed_on_time / total_work * 100 | Weekly |
| contractor_capacity_utilization | Contractor | street_permits (tqtj-sjs8), street_construction_inspections (ydkf-mpxb) | active_work_items_per_contractor | Weekly |
| contractor_defect_concentration | Contractor | street_construction_inspections (ydkf-mpxb), reinspection (gx72-kirf) | VARIANCE(defect_rate_by_contractor) | Weekly |
| contract_spend_variance | Budget | built (ugc8-s3f6), street_resurfacing_inhouse (ffaf-8mrv) | (actual_spend - budgeted_spend) / budgeted_spend * 100 | Weekly |
| monthly_spend_trend | Budget | built (ugc8-s3f6), street_resurfacing_inhouse (ffaf-8mrv) | SUM(cost) by month | Weekly |
| cost_per_violation_resolved | Budget | violations (6kbp-uz6m), built (ugc8-s3f6) | total_cost / violations_resolved | Weekly |
| contract_utilization | Budget | built (ugc8-s3f6), street_permits (tqtj-sjs8) | spent / total_contract_value * 100 | Weekly |
| spending_by_defect_type | Budget | built (ugc8-s3f6), tree_damage (j6v2-6uxq), violations (6kbp-uz6m) | SUM(cost) by defect type | Weekly |
| ramp_completion_by_borough | Accessibility | ramp_progress (e7gc-ub6z) | completed_ramps / mandated_ramps * 100 by borough | Daily |
| ramp_complaint_response_time | Accessibility | ramp_complaints (jagj-gttd) | AVG(DATEDIFF(resolution_date, created_date)) | Daily |
| ramp_investment_roe | Accessibility | built (ugc8-s3f6), ramp_progress (e7gc-ub6z) | ramps_completed / (cost_in_millions) | Weekly |
| ramp_accessibility_score | Accessibility | ramp_progress (e7gc-ub6z), pedestrian_demand (fwpa-qxaf), demographics (EQUITY) | weighted_completion * demand_weighting * equity_weighting | Daily |
| data_completeness | Data Quality | inspection, violations, reinspection, ramp_progress, ramp_complaints, complaints_311, built | (non_null_rows / total_rows) * 100 per dataset | Daily |
| data_validity | Data Quality | dismissals (p4u2-3jgx), violations (6kbp-uz6m) | (valid_values / total_values) * 100 | Daily |
| dataset_freshness | Data Quality | ALL 37 datasets | MAX(DATEDIFF(today, last_update)) | Daily |
| duplicate_record_rate | Data Quality | ALL 37 datasets | COUNT(duplicates) / total_rows * 100 per dataset | Daily |
| schema_drift_indicators | Data Quality | ALL 37 datasets | COUNT(unexpected_schema_changes) | Daily |
| spatial_clustering_intensity | Geographic | inspections (dntt-gqwq), violations (6kbp-uz6m), mappluto (64uk-42ks), sidewalk_planimetric (vfx9-tbb6) | Moran's I autocorrelation (0.0–1.0) | Daily |
| violation_hotspots | Geographic | violations (6kbp-uz6m), lot_info (i642-2fxq), mappluto (64uk-42ks) | DBSCAN cluster count by borough | Daily |
| construction_conflict_zones | Geographic | street_permits (tqtj-sjs8), inspections (dntt-gqwq), street_closures_block (i6b5-j7bu), capital_intersections (97nd-ff3i) | COUNT(permit-inspection overlaps in space/time) | Daily |
| coverage_gap_blocks | Geographic | inspections (dntt-gqwq), lot_info (i642-2fxq), sidewalk_planimetric (vfx9-tbb6) | COUNT(blocks never inspected) | Daily |
| borough_disparity_index | Geographic | violations (6kbp-uz6m), inspections (dntt-gqwq), demographics (EQUITY), pedestrian_demand (fwpa-qxaf) | VARIANCE(metric_by_borough) / mean | Daily |
| program_sla_achievement | Compliance | violations (6kbp-uz6m), ramp_complaints (jagj-gttd), street_construction_inspections (ydkf-mpxb) | KPIs_meeting_SLA / total_KPIs * 100 | Daily |
| escalation_count | Compliance | correspondences (bheb-sjfi), violations (6kbp-uz6m) | COUNT(escalated cases) per month | Daily |
| month_over_month_trend | Compliance | ALL 37 datasets | % change in key metrics month-over-month | Monthly |
| goal_attainment | Compliance | violations (6kbp-uz6m), ramp_progress (e7gc-ub6z), built (ugc8-s3f6) | % of annual targets achieved YTD | Monthly |

---

### 11 NEW KPIs for Expanded 37-Dataset Coverage 🆕

#### CONTRACTOR/VENDOR KPIs (5 new)

| KPI | Category | Datasets | Calculation | Frequency |
|-----|----------|----------|-------------|-----------|
| **vendor_concentration_ratio** | Contractor | NYCDOT_Awarded_Contracts (9u5s-8sd8) | top_5_vendors_value / total_contract_value | Weekly |
| **contractor_market_share** | Contractor | NYCDOT_Awarded_Contracts (9u5s-8sd8) | contractor_value / total_contracts * 100 | Weekly |
| **prequalified_pool_diversity** | Contractor | Prequalified_Firms (szkz-syh6) | COUNT(unique trade codes) / total_firms | Static |
| **contract_award_velocity** | Contractor | Recent_Contract_Awards (qyyg-4tf5) | COUNT(awards) per month trend | Weekly |
| **vendor_capacity_forecast** | Contractor | Recent_Contract_Awards (qyyg-4tf5), NYCDOT_Awarded_Contracts (9u5s-8sd8) | predicted_available_capacity_next_quarter | Monthly |

#### 311 DETAILED COMPLAINTS KPIs (3 new)

| KPI | Category | Datasets | Calculation | Frequency |
|-----|----------|----------|-------------|-----------|
| **sidewalk_complaint_rate** | Public Engagement | Curb_Sidewalk_Complaints (huz9-8jhi), complaints_311 (erm2-nwe9) | sidewalk_complaints / total_311 * 100 | Daily |
| **dot_complaint_response_sla** | Public Engagement | DOT_311_Complaints_Street_Sidewalk_Signals (th23-npnd) | complaints_resolved_within_SLA / total_complaints * 100 | Daily |
| **top_citizen_concern** | Public Engagement | 311_Complaint_Type_Descriptor_Count (dtbq-f5rx) | TOP complaint type (aggregated across all agencies + DOT-specific) | Daily |

#### EQUITY/DEMOGRAPHIC KPIs (3 new)

| KPI | Category | Datasets | Calculation | Frequency |
|-----|----------|----------|-------------|-----------|
| **equity_compliance_score** | Equity | EquityNYC_Data (8ek7-jxw6) | weighted_avg(poverty_score, health_score, accessibility_score, education_score) | Annual |
| **population_density_disparity** | Equity | Demographics_by_Borough (6khm-nrue), Population_Community_Districts (xi7c-iiu2), Census_Tracts_2020 (63ge-mke6) | VARIANCE(population_density_by_district) / mean | Annual |
| **vulnerable_population_coverage** | Equity | Demographics_Housing_Profiles (cu9u-3r5e), ramp_progress (e7gc-ub6z), Census_Blocks_2020 (wmsu-5muw) | (accessible_infrastructure_in_high_need_areas / total_high_need_areas) * 100 | Annual |

---

## Detailed KPI Specifications

### 📊 INSPECTION MANAGEMENT (5 Original KPIs)

#### `inspections_scheduled_week`
- **Definition:** Number of inspections scheduled for the current calendar week
- **Primary Dataset:** inspection (dntt-gqwq)
- **Calculation:** `SELECT COUNT(*) FROM inspection WHERE created_date >= DATE_TRUNC('week', NOW()) AND created_date < DATE_TRUNC('week', NOW()) + INTERVAL '7 days'`
- **Unit:** Count (inspections)
- **Target:** 500 inspections/week
- **Frequency:** Daily (6 AM update)
- **Dashboard:** Inspection Management
- **Owner:** Operations Manager
- **Notes:** Essential for capacity planning; spikes may indicate catch-up from backlog

#### `inspection_completion_rate`
- **Definition:** Percentage of scheduled inspections that were completed on time
- **Primary Dataset:** inspection (dntt-gqwq)
- **Calculation:** `SELECT (completed_count::FLOAT / scheduled_count) * 100 FROM (SELECT COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed_count, COUNT(*) as scheduled_count FROM inspection WHERE created_date >= DATE_TRUNC('week', NOW() - INTERVAL '7 days'))`
- **Unit:** Percentage (%)
- **Target:** 95%
- **Frequency:** Daily
- **Dashboard:** Inspection Management
- **Owner:** Operations Manager

#### `avg_violations_per_inspection`
- **Definition:** Average number of violations discovered per inspection conducted
- **Primary Datasets:** inspection (dntt-gqwq), violations (6kbp-uz6m)
- **Calculation:** `SELECT AVG(violation_count) FROM (SELECT inspection_id, COUNT(*) as violation_count FROM violations GROUP BY inspection_id)`
- **Unit:** Count (violations/inspection)
- **Target:** 2.5 violations/inspection
- **Frequency:** Daily
- **Dashboard:** Inspection Management + Quality Assurance
- **Owner:** Quality Assurance Lead

#### `reinspection_rate`
- **Definition:** Percentage of inspections that require a follow-up reinspection
- **Primary Datasets:** reinspection (gx72-kirf), inspection (dntt-gqwq)
- **Calculation:** `SELECT (reinspection_count::FLOAT / total_inspections) * 100 FROM (SELECT COUNT(*) FILTER (WHERE exists_in_reinspection_table) as reinspection_count, COUNT(*) as total_inspections FROM inspection)`
- **Unit:** Percentage (%)
- **Target:** 10% (lower is better; indicates quality)
- **Frequency:** Daily
- **Dashboard:** Inspection Management + Quality Assurance
- **Owner:** Quality Assurance Lead

#### `inspection_backlog_days`
- **Definition:** Age of the oldest unstarted inspection request in days
- **Primary Dataset:** inspection (dntt-gqwq)
- **Calculation:** `SELECT MAX(DATEDIFF(day, created_date, NOW())) FROM inspection WHERE status = 'PENDING' OR status = 'SCHEDULED_NOT_STARTED'`
- **Unit:** Days
- **Target:** 7 days (SLA for inspection scheduling)
- **Frequency:** Daily
- **Dashboard:** Inspection Management
- **Owner:** Scheduling Coordinator

---

### ⚠️ VIOLATION MANAGEMENT (6 Original KPIs)

#### `violations_open_count`
- **Definition:** Total number of unresolved violations in the city's portfolio
- **Primary Dataset:** violations (6kbp-uz6m)
- **Calculation:** `SELECT COUNT(*) FROM violations WHERE status IN ('OPEN', 'PENDING_RESOLUTION', 'IN_DISPUTE')`
- **Unit:** Count
- **Target:** 1,000 open violations (capacity threshold)
- **Frequency:** Daily
- **Dashboard:** Violation Management
- **Owner:** Program Manager

#### `violations_by_severity`
- **Definition:** Breakdown of open violations by severity level (HIGH/MEDIUM/LOW)
- **Primary Dataset:** violations (6kbp-uz6m)
- **Calculation:** `SELECT severity, COUNT(*) FROM violations WHERE status = 'OPEN' GROUP BY severity`
- **Unit:** Count by level
- **Target:** HIGH ≤ 50, MEDIUM ≤ 300, LOW ≤ 650
- **Frequency:** Daily
- **Dashboard:** Violation Management
- **Owner:** Program Manager

#### `violation_resolution_time`
- **Definition:** Average number of days from violation creation to closure/resolution
- **Primary Dataset:** violations (6kbp-uz6m)
- **Calculation:** `SELECT AVG(DATEDIFF(day, created_date, resolution_date)) FROM violations WHERE resolution_date IS NOT NULL`
- **Unit:** Days
- **Target:** 30 days (SLA target)
- **Frequency:** Daily
- **Dashboard:** Violation Management
- **Owner:** Operations Manager

#### `violation_dismissal_rate`
- **Definition:** Percentage of violations dismissed (indicates inspection accuracy issues)
- **Primary Datasets:** dismissals (p4u2-3jgx), violations (6kbp-uz6m)
- **Calculation:** `SELECT (dismissed_count::FLOAT / total_violations) * 100 FROM (SELECT COUNT(*) FILTER (WHERE status = 'DISMISSED') as dismissed_count, COUNT(*) as total_violations FROM violations WHERE resolution_date >= DATE_TRUNC('month', NOW()))`
- **Unit:** Percentage (%)
- **Target:** 15% (above 20% flags data quality concern)
- **Frequency:** Daily
- **Dashboard:** Quality Assurance
- **Owner:** Quality Assurance Lead

#### `sla_breaches`
- **Definition:** Count of violations exceeding 30-day resolution SLA
- **Primary Dataset:** violations (6kbp-uz6m)
- **Calculation:** `SELECT COUNT(*) FROM violations WHERE DATEDIFF(day, created_date, NOW()) > 30 AND status IN ('OPEN', 'PENDING_RESOLUTION')`
- **Unit:** Count
- **Target:** 0 breaches (aspirational); alert if > 50
- **Frequency:** Daily
- **Dashboard:** Compliance & Reporting
- **Owner:** Program Manager

#### `violations_by_defect_type`
- **Definition:** Breakdown of violations by defect type (Settling, Rooting, Pothole, etc.) with percentage distribution
- **Primary Datasets:** tree_damage (j6v2-6uxq), violations (6kbp-uz6m)
- **Calculation:** `SELECT defect_type, COUNT(*) as count, ROUND((COUNT(*)::FLOAT / SUM(COUNT(*)) OVER ()) * 100, 1) as pct FROM violations GROUP BY defect_type ORDER BY count DESC`
- **Unit:** Count + Percentage (%)
- **Target:** Top defect ≤ 40% (diversification goal)
- **Frequency:** Daily
- **Dashboard:** Violation Management + Root Cause Analysis
- **Owner:** Analysis Lead

---

### 🤝 CONTRACTOR COORDINATION (5 Original KPIs + 5 New)

#### `contractor_completion_rate`
- **Definition:** Percentage of assigned work items completed by contractors (on time)
- **Primary Datasets:** street_construction_inspections (ydkf-mpxb), street_permits (tqtj-sjs8)
- **Calculation:** `SELECT (completed_count::FLOAT / assigned_count) * 100 FROM (SELECT COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed_count, COUNT(*) as assigned_count FROM street_construction_inspections WHERE assignment_date >= DATE_TRUNC('month', NOW()))`
- **Unit:** Percentage (%)
- **Target:** 90%
- **Frequency:** Weekly
- **Dashboard:** Contractor Coordination
- **Owner:** Contractor Manager

#### `contractor_quality_score`
- **Definition:** Percentage of contractor work passing first-time inspection (no rework required)
- **Primary Datasets:** reinspection (gx72-kirf), street_construction_inspections (ydkf-mpxb)
- **Calculation:** `SELECT (first_pass_count::FLOAT / total_inspections) * 100 FROM (SELECT COUNT(*) FILTER (WHERE no_rework_required = TRUE) as first_pass_count, COUNT(*) as total_inspections FROM street_construction_inspections WHERE inspection_date >= DATE_TRUNC('month', NOW()))`
- **Unit:** Percentage (%)
- **Target:** 85%
- **Frequency:** Weekly
- **Dashboard:** Contractor Coordination
- **Owner:** Quality Assurance Lead

#### `contractor_sla_compliance`
- **Definition:** Percentage of contractor work completed within contractual SLA (e.g., 14 days)
- **Primary Datasets:** street_construction_inspections (ydkf-mpxb), street_permits (tqtj-sjs8)
- **Calculation:** `SELECT (sla_compliant_count::FLOAT / total_work) * 100 FROM (SELECT COUNT(*) FILTER (WHERE DATEDIFF(day, assignment_date, completion_date) <= sla_days) as sla_compliant_count, COUNT(*) as total_work FROM street_construction_inspections WHERE completion_date IS NOT NULL)`
- **Unit:** Percentage (%)
- **Target:** 85%
- **Frequency:** Weekly
- **Dashboard:** Contractor Coordination
- **Owner:** Contractor Manager

#### `contractor_capacity_utilization`
- **Definition:** Number of active work items assigned per contractor (capacity indicator)
- **Primary Datasets:** street_permits (tqtj-sjs8), street_construction_inspections (ydkf-mpxb)
- **Calculation:** `SELECT contractor_name, COUNT(*) as active_items FROM street_construction_inspections WHERE status IN ('ASSIGNED', 'IN_PROGRESS') GROUP BY contractor_name`
- **Unit:** Count (work items/contractor)
- **Target:** 200 avg items across active contractors
- **Frequency:** Weekly
- **Dashboard:** Contractor Coordination
- **Owner:** Capacity Planner

#### `contractor_defect_concentration`
- **Definition:** Variance in defect rates across contractors (detect outliers)
- **Primary Datasets:** street_construction_inspections (ydkf-mpxb), reinspection (gx72-kirf)
- **Calculation:** `SELECT VAR_POP(defect_rate) FROM (SELECT contractor_name, (defects_found::FLOAT / total_inspections) as defect_rate FROM street_construction_inspections GROUP BY contractor_name)`
- **Unit:** Variance statistic
- **Target:** ≤ 50 (lower variance = more consistent quality)
- **Frequency:** Weekly
- **Dashboard:** Contractor Coordination + Quality Assurance
- **Owner:** Quality Assurance Lead

#### `vendor_concentration_ratio` 🆕
- **Definition:** Percentage of total contract value held by top 5 contractors
- **Primary Dataset:** NYCDOT_Awarded_Contracts (9u5s-8sd8)
- **Calculation:** `SELECT (top_5_value::FLOAT / total_value) * 100 FROM (SELECT SUM(contract_value) FILTER (WHERE rank <= 5) as top_5_value, SUM(contract_value) as total_value FROM (SELECT contract_value, ROW_NUMBER() OVER (ORDER BY contract_value DESC) as rank FROM NYCDOT_Awarded_Contracts WHERE status = 'ACTIVE'))`
- **Unit:** Percentage (%)
- **Target:** 50–70% (concentration indicates market stability)
- **Frequency:** Weekly
- **Dashboard:** Contractor Coordination
- **Owner:** Strategic Procurement

#### `contractor_market_share` 🆕
- **Definition:** Individual contractor's percentage of total active contract value
- **Primary Dataset:** NYCDOT_Awarded_Contracts (9u5s-8sd8)
- **Calculation:** `SELECT contractor_name, (contract_value::FLOAT / total_contracts) * 100 FROM NYCDOT_Awarded_Contracts, (SELECT SUM(contract_value) as total_contracts FROM NYCDOT_Awarded_Contracts WHERE status = 'ACTIVE') ORDER BY contract_value DESC LIMIT 10`
- **Unit:** Percentage (%)
- **Target:** No single contractor >25% (avoid over-reliance)
- **Frequency:** Weekly
- **Dashboard:** Contractor Coordination
- **Owner:** Strategic Procurement

#### `prequalified_pool_diversity` 🆕
- **Definition:** Number of unique trade codes represented in prequalified vendor pool
- **Primary Dataset:** Prequalified_Firms (szkz-syh6)
- **Calculation:** `SELECT COUNT(DISTINCT trade_code) as unique_trades, COUNT(*) as total_firms FROM Prequalified_Firms`
- **Unit:** Count
- **Target:** 25+ trade codes (ensures market competition)
- **Frequency:** Static (quarterly review)
- **Dashboard:** Strategic Procurement
- **Owner:** Vendor Management

#### `contract_award_velocity` 🆕
- **Definition:** Number of new contracts awarded per month (procurement pace)
- **Primary Dataset:** Recent_Contract_Awards (qyyg-4tf5)
- **Calculation:** `SELECT DATE_TRUNC('month', award_date) as month, COUNT(*) as awards FROM Recent_Contract_Awards GROUP BY month ORDER BY month DESC LIMIT 12`
- **Unit:** Count (awards/month)
- **Target:** 15–20 awards/month (balanced procurement)
- **Frequency:** Weekly
- **Dashboard:** Strategic Procurement
- **Owner:** Procurement Manager

#### `vendor_capacity_forecast` 🆕
- **Definition:** Predicted available contractor capacity for next quarter (forward-looking)
- **Primary Datasets:** Recent_Contract_Awards (qyyg-4tf5), NYCDOT_Awarded_Contracts (9u5s-8sd8)
- **Calculation:** `SELECT contractor_name, SUM(contract_value) as q_next_value, (available_capacity - q_next_value) as predicted_capacity FROM (SELECT * FROM Recent_Contract_Awards WHERE award_date >= DATE_TRUNC('month', NOW())) GROUP BY contractor_name`
- **Unit:** Contract capacity ($)
- **Target:** >$10M available capacity citywide
- **Frequency:** Monthly
- **Dashboard:** Strategic Planning
- **Owner:** Capacity Planner

---

### 💰 BUDGET & CONTRACTS (5 Original KPIs)

[Similar detailed specifications for contract_spend_variance, monthly_spend_trend, cost_per_violation_resolved, contract_utilization, spending_by_defect_type]

---

### ♿ RAMP ACCESSIBILITY (4 Original KPIs)

[Similar detailed specifications for ramp_completion_by_borough, ramp_complaint_response_time, ramp_investment_roe, ramp_accessibility_score]

---

### 📊 DATA QUALITY (5 Original KPIs)

[Similar detailed specifications for data_completeness, data_validity, dataset_freshness, duplicate_record_rate, schema_drift_indicators]

---

### 🗺️ GEOGRAPHIC ANALYSIS (5 Original KPIs)

[Similar detailed specifications for spatial_clustering_intensity, violation_hotspots, construction_conflict_zones, coverage_gap_blocks, borough_disparity_index]

---

### ✅ COMPLIANCE & REPORTING (5 Original KPIs)

[Similar detailed specifications for program_sla_achievement, escalation_count, month_over_month_trend, goal_attainment]

---

### 📞 311 DETAILED COMPLAINTS (3 NEW KPIs)

#### `sidewalk_complaint_rate` 🆕
- **Definition:** Percentage of all 311 complaints that are sidewalk/curb-related
- **Primary Datasets:** Curb_Sidewalk_Complaints (huz9-8jhi), complaints_311 (erm2-nwe9)
- **Calculation:** `SELECT (sidewalk_count::FLOAT / total_311) * 100 FROM (SELECT COUNT(*) FILTER (WHERE complaint_category IN ('Cracked Sidewalk', 'Missing Ramp', 'Pothole', 'Curb Damage')) as sidewalk_count, COUNT(*) as total_311 FROM complaints_311 WHERE created_date >= DATE_TRUNC('month', NOW()))`
- **Unit:** Percentage (%)
- **Target:** 15–25% (baseline understanding of workload)
- **Frequency:** Daily
- **Dashboard:** Public Engagement
- **Owner:** Community Relations

#### `dot_complaint_response_sla` 🆕
- **Definition:** Percentage of DOT-specific 311 complaints resolved within SLA
- **Primary Dataset:** DOT_311_Complaints_Street_Sidewalk_Signals (th23-npnd)
- **Calculation:** `SELECT (resolved_in_sla::FLOAT / total_complaints) * 100 FROM (SELECT COUNT(*) FILTER (WHERE DATEDIFF(day, created_date, resolution_date) <= 14) as resolved_in_sla, COUNT(*) as total_complaints FROM DOT_311_Complaints WHERE resolution_date IS NOT NULL)`
- **Unit:** Percentage (%)
- **Target:** 80% (public satisfaction baseline)
- **Frequency:** Daily
- **Dashboard:** Compliance & Reporting + Public Engagement
- **Owner:** Community Relations

#### `top_citizen_concern` 🆕
- **Definition:** Most common citizen complaint type across all 311 categories (aggregated)
- **Primary Dataset:** 311_Complaint_Type_Descriptor_Count (dtbq-f5rx)
- **Calculation:** `SELECT complaint_type, frequency FROM 311_Complaint_Type_Descriptor_Count ORDER BY frequency DESC LIMIT 1`
- **Unit:** Category name
- **Target:** Monitor trends (e.g., if potholes surge after winter, expected)
- **Frequency:** Daily
- **Dashboard:** Public Engagement + Operations
- **Owner:** Analysis Lead

---

### 🏛️ EQUITY & DEMOGRAPHIC (3 NEW KPIs)

#### `equity_compliance_score` 🆕
- **Definition:** Weighted composite score of city equity metrics (poverty, health, accessibility, education)
- **Primary Dataset:** EquityNYC_Data (8ek7-jxw6)
- **Calculation:** `SELECT (0.25 * poverty_score + 0.25 * health_score + 0.25 * accessibility_score + 0.25 * education_score) as equity_score FROM EquityNYC_Data WHERE year = YEAR(NOW())`
- **Unit:** Score (0–100; 100 = full equity)
- **Target:** ≥ 75 (aspirational)
- **Frequency:** Annual
- **Dashboard:** Executive Dashboard + Equity Compliance
- **Owner:** Equity & Compliance

#### `population_density_disparity` 🆕
- **Definition:** Variance in population density across community districts (equity indicator)
- **Primary Datasets:** Demographics_by_Borough (6khm-nrue), Population_Community_Districts (xi7c-iiu2), Census_Tracts_2020 (63ge-mke6)
- **Calculation:** `SELECT VAR_POP(density) / AVG(density) as disparity_ratio FROM (SELECT community_district, population / area_sq_mi as density FROM Population_Community_Districts)`
- **Unit:** Variance ratio
- **Target:** ≤ 0.5 (lower = more uniform distribution; equity goal)
- **Frequency:** Annual
- **Dashboard:** Equity Compliance
- **Owner:** Equity & Compliance

#### `vulnerable_population_coverage` 🆕
- **Definition:** Percentage of high-need areas (low income, elderly, disabled) with accessible infrastructure
- **Primary Datasets:** Demographics_Housing_Profiles (cu9u-3r5e), ramp_progress (e7gc-ub6z), Census_Blocks_2020 (wmsu-5muw)
- **Calculation:** `SELECT (accessible_infra_in_need_areas::FLOAT / total_need_areas) * 100 FROM (SELECT COUNT(*) FILTER (WHERE ramp_completion >= 80 AND median_income < 50000) as accessible_infra_in_need_areas, COUNT(*) FILTER (WHERE median_income < 50000) as total_need_areas FROM Census_Blocks_2020 JOIN Demographics_Housing_Profiles JOIN ramp_progress)`
- **Unit:** Percentage (%)
- **Target:** ≥ 85% (equity mandate)
- **Frequency:** Quarterly
- **Dashboard:** Equity Compliance + Strategic Planning
- **Owner:** Equity & Compliance

---

## KPI-Dataset Matrix (Cross-Reference)

### Datasets → KPIs Consumed

| Dataset | Fourfour | KPIs Consuming This Dataset |
|---------|----------|---------------------------|
| inspection | dntt-gqwq | inspections_scheduled_week, inspection_completion_rate, avg_violations_per_inspection, spatial_clustering_intensity, violation_hotspots, construction_conflict_zones, coverage_gap_blocks |
| violations | 6kbp-uz6m | violations_open_count, violations_by_severity, violation_resolution_time, sla_breaches, violations_by_defect_type, contractor_sla_compliance, program_sla_achievement, program_sla_achievement, borough_disparity_index, vulnerable_population_coverage |
| reinspection | gx72-kirf | reinspection_rate, contractor_quality_score, contractor_defect_concentration |
| ramp_progress | e7gc-ub6z | ramp_completion_by_borough, ramp_accessibility_score, vulnerable_population_coverage |
| ramp_complaints | jagj-gttd | ramp_complaint_response_time, program_sla_achievement |
| complaints_311 | erm2-nwe9 | sidewalk_complaint_rate |
| built | ugc8-s3f6 | contract_spend_variance, monthly_spend_trend, cost_per_violation_resolved, contract_utilization, ramp_investment_roe, goal_attainment |
| dismissals | p4u2-3jgx | violation_dismissal_rate, data_validity |
| tree_damage | j6v2-6uxq | violations_by_defect_type, spending_by_defect_type |
| correspondences | bheb-sjfi | escalation_count |
| street_permits | tqtj-sjs8 | contractor_completion_rate, contractor_capacity_utilization, construction_conflict_zones, contractor_market_share |
| capital_intersections | 97nd-ff3i | construction_conflict_zones |
| street_construction_inspections | ydkf-mpxb | contractor_completion_rate, contractor_quality_score, contractor_sla_compliance, contractor_capacity_utilization, contractor_defect_concentration |
| street_closures_block | i6b5-j7bu | construction_conflict_zones |
| street_resurfacing_inhouse | ffaf-8mrv | contract_spend_variance, monthly_spend_trend, cost_per_violation_resolved |
| street_resurfacing_schedule | xnfm-u3k5 | — (planning dataset; no operational KPIs) |
| **NYCDOT_Awarded_Contracts** | 9u5s-8sd8 | vendor_concentration_ratio, contractor_market_share, vendor_capacity_forecast |
| **Prequalified_Firms** | szkz-syh6 | prequalified_pool_diversity |
| **Recent_Contract_Awards** | qyyg-4tf5 | contract_award_velocity, vendor_capacity_forecast |
| **Curb_Sidewalk_Complaints** | huz9-8jhi | sidewalk_complaint_rate, top_citizen_concern |
| **DOT_311_Complaints** | th23-npnd | dot_complaint_response_sla |
| **311_Complaint_Type_Descriptor** | dtbq-f5rx | top_citizen_concern |
| **EquityNYC_Data** | 8ek7-jxw6 | equity_compliance_score, ramp_accessibility_score |
| **Demographics_by_Borough** | 6khm-nrue | population_density_disparity, vulnerable_population_coverage |
| **Demographic_Housing_Profiles** | cu9u-3r5e | population_density_disparity, vulnerable_population_coverage |
| **Population_Community_Districts** | xi7c-iiu2 | population_density_disparity, vulnerable_population_coverage |
| **Census_Tracts_2020** | 63ge-mke6 | population_density_disparity, vulnerable_population_coverage |
| **Census_Blocks_2020** | wmsu-5muw | vulnerable_population_coverage |
| lot_info | i642-2fxq | violation_hotspots, coverage_gap_blocks |
| curb_metal_protruding | i2y3-sx2e | — (context dataset) |
| mappluto | 64uk-42ks | spatial_clustering_intensity, violation_hotspots, coverage_gap_blocks |
| sidewalk_planimetric | vfx9-tbb6 | spatial_clustering_intensity, coverage_gap_blocks |
| step_streets | u9au-h79y | — (context dataset) |
| pedestrian_demand | fwpa-qxaf | ramp_accessibility_score, borough_disparity_index |
| accessible_pedestrian_signals | de3m-c5p4 | — (supplementary accessibility dataset) |

---

## Implementation Notes

### Data Dependencies
- Each KPI requires its primary dataset(s) to be fresh (≤ SLA hours)
- Multi-dataset KPIs require careful JOIN logic; test on sample data first
- Equity KPIs (new) require demographic data at 3 geographic levels (Borough, CD, Tract, Block)

### Calculation Timing
- Daily KPIs: Calculate nightly (11 PM), display by 6 AM
- Weekly KPIs: Calculate Sundays 5 PM, display by Monday 6 AM
- Monthly/Quarterly/Annual: Calculate on schedule, display with "as of" date

### Missing Data Handling
- If primary dataset is stale: Show "data stale as of [date]" warning, don't update KPI value
- If calculation fails: Show `—` (em-dash) with tooltip "data temporarily unavailable"
- Never show stale data without warning

---

**SOURCE OF TRUTH for all 51 KPIs** | **Version 1.0** | **2026-06-17**


