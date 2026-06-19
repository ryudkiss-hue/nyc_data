# NYC DOT Complete Data Catalog

**Version:** 2.0 (Integrated with Governance Framework v1.0)  
**Last Updated:** 2026-06-18  
**Total Datasets:** 57  
**Total KPIs:** 51  
**Domain Schemas:** 5  
**Retention Policy:** Indefinite (personal solo-user mode)

---

## Quick Navigation

- **[Datasets by Domain Schema](#datasets-by-domain-schema)** — All 57 datasets organized by business domain
- **[Dataset Index](#complete-dataset-index)** — Alphabetical reference with fourfour IDs
- **[KPI Materialization](#kpi-materialization-catalog)** — 51 KPIs with lineage to source datasets
- **[Analytics Schemas](#analytics-schemas-catalog)** — 5 domain schemas with table definitions
- **[Data Dives](#data-dives-catalog)** — 4 dive categories for exploration and analysis
- **[Governance Integration](#governance-integration)** — Classification, quality tiers, SLA tracking
- **[Data Lineage](#data-lineage)** — Complete source → staging → analytics → KPI flow

---

## Datasets by Domain Schema

### SIM_CORE Domain (Inspection & Management)

**Purpose:** Core inspection, violation, dismissal, and service management data  
**Steward:** Inspection Program Manager  
**Update Frequency:** Daily  
**SLA Tier:** HIGH (14 days)  
**Quality Tier:** A (Authoritative)

| Dataset | Fourfour | Rows | Size | Priority | Cache | Status |
|---------|----------|------|------|----------|-------|--------|
| inspection | a2nx-4u46 | 399,427 | large | 100 | prefetch_full | Critical |
| violations | 6kbp-uz6m | 312,828 | large | 99 | prefetch_full | Critical |
| dismissals | p4u2-3jgx | 85,000 | medium | 96 | prefetch_full | Critical |
| reinspection | gx72-kirf | 36,000 | small | 80 | prefetch_incremental | Important |
| safety_incidents | custom | 18,500 | small | 31 | lazy_load | Reference |
| public_complaints | custom | 245,000 | large | 26 | lazy_load | Reference |
| service_requests | custom | 410,000 | large | 60 | lazy_load | Operational |
| inspection_history | custom | 500,000 | large | 62 | lazy_load | Operational |

**Data Dictionary:**
- `inspection`: Primary sidewalk inspection records with inspector ID, location, condition score
- `violations`: Violations found during inspections with severity, category, closure status
- `dismissals`: Complaints dismissed with reason and disposition
- `reinspection`: Follow-up inspections for previously found violations
- `safety_incidents`: Safety-related incidents during operations
- `public_complaints`: Complaints from the public via 311 and other channels
- `service_requests`: Service requests and maintenance tasks
- `inspection_history`: Historical inspection records for trend analysis

**Downstream KPIs:**
- violation_closure_rate_by_borough (rate)
- inspection_timeliness (trend)
- sla_compliance_rate (rate)
- data_quality_score (index)

---

### ACCESSIBILITY Domain (Ramp Program & ADA Compliance)

**Purpose:** ADA ramp program, accessibility compliance, and audit data  
**Steward:** Accessibility Program Director  
**Update Frequency:** Daily/Weekly  
**SLA Tier:** HIGH (14 days)  
**Quality Tier:** A (Authoritative)

| Dataset | Fourfour | Rows | Size | Priority | Cache | Status |
|---------|----------|------|------|----------|-------|--------|
| ramp_progress | e7gc-ub6z | 187,000 | medium | 98 | prefetch_full | Critical |
| ramp_complaints | jagj-gttd | 6,000 | small | 97 | prefetch_full | Critical |
| ramp_locations | ufzp-rrqu | 217,000 | medium | 70 | lazy_load | Standard |
| violations | 6kbp-uz6m | 312,828 | large | 99 | prefetch_full | Critical |
| ramp_specifications | custom | 18,000 | small | 17 | lazy_load | Reference |
| ramp_maintenance_log | custom | 52,000 | medium | 42 | lazy_load | Reference |
| accessibility_audits | custom | 75,000 | medium | 20 | lazy_load | Reference |
| violation_attachments | custom | 280,000 | large | 23 | lazy_load | Reference |

**Data Dictionary:**
- `ramp_progress`: Installation status, completion date, neighborhood, borough
- `ramp_complaints`: Accessibility complaints related to ramp program
- `ramp_locations`: Inventory of ramp locations with coordinates
- `ramp_specifications`: Technical specifications for ramp installation
- `ramp_maintenance_log`: Maintenance and repair history for installed ramps
- `accessibility_audits`: Audit findings and compliance assessments
- `violation_attachments`: Photos and documentation of accessibility violations

**Downstream KPIs:**
- ramp_completion_rate (rate)
- ramp_installation_pace (count)
- accessibility_audit_pass_rate (rate)
- accessibility_improvement_index (index)
- new_ramp_installation_rate (trend)

---

### COORDINATION Domain (Permits, Construction, Regulatory)

**Purpose:** Permit coordination, construction timelines, environmental and regulatory compliance  
**Steward:** Construction Coordination Manager  
**Update Frequency:** Weekly  
**SLA Tier:** MEDIUM (30 days)  
**Quality Tier:** A/B (Authoritative/Operational)

| Dataset | Fourfour | Rows | Size | Priority | Cache | Status |
|---------|----------|------|------|----------|-------|--------|
| street_permits | tqtj-sjs8 | 3,600,000 | xlarge | 85 | prefetch_incremental | Critical |
| street_construction_inspections | ydkf-mpxb | 11,500,000 | xlarge | 84 | prefetch_incremental | Critical |
| capital_intersections | 97nd-ff3i | 7,800 | small | 65 | lazy_load | Standard |
| correspondences | bheb-sjfi | 30,000 | small | 79 | prefetch_incremental | Important |
| street_closures_block | i6b5-j7bu | 4,300 | small | 64 | lazy_load | Standard |
| capital_blocks | jvk9-k4re | 0 | empty | 10 | skip | Deprecated |
| weekly_construction | r528-jcks | 75 | tiny | 11 | lazy_load | Deprecated |
| permit_history | custom | 310,000 | large | 39 | lazy_load | Operational |
| construction_metrics | custom | 195,000 | medium | 38 | lazy_load | Operational |
| environmental_compliance | custom | 55,000 | medium | 30 | lazy_load | Reference |
| traffic_impact | custom | 175,000 | medium | 29 | lazy_load | Reference |
| permit_status_history | custom | 310,000 | large | 28 | lazy_load | Reference |
| permit_amendments | custom | 78,000 | medium | 27 | lazy_load | Reference |

**Data Dictionary:**
- `street_permits`: Active and historical permits with contractor, scope, budget
- `street_construction_inspections`: Inspection records for active construction
- `capital_intersections`: Planned capital improvements at intersections
- `correspondences`: Communication records between DOT and stakeholders
- `street_closures_block`: Temporary street closure permits
- `permit_history`: Historical permit data for trend analysis
- `environmental_compliance`: Environmental review and compliance status
- `traffic_impact`: Traffic impact assessments and mitigation

**Downstream KPIs:**
- permit_approval_time (trend)
- construction_timeline_variance (trend)
- conflict_matrix_overlap_rate (rate)
- regulatory_approval_compliance (rate)
- budget_variance (trend)

---

### OVERLAYS Domain (Spatial Enrichment & Reference Data)

**Purpose:** Spatial context, GIS reference layers, tree data, curb inventory  
**Steward:** GIS & Mapping Manager  
**Update Frequency:** Quarterly  
**SLA Tier:** MEDIUM/LOW (30-60 days)  
**Quality Tier:** B/C/D (Operational/Enrichment/Reference)

| Dataset | Fourfour | Rows | Size | Priority | Cache | Status |
|---------|----------|------|------|----------|-------|--------|
| mappluto | 64uk-42ks | 858,000 | large | 68 | lazy_load | Standard |
| sidewalk_planimetric | vfx9-tbb6 | 50,000 | medium | 67 | lazy_load | Standard |
| lot_info | i642-2fxq | 1,200,000 | xlarge | 82 | prefetch_incremental | Critical |
| step_streets | u9au-h79y | 110 | tiny | 50 | lazy_load | Reference |
| tree_damage | j6v2-6uxq | 17,000 | small | 51 | lazy_load | Reference |
| curb_metal_protruding | i2y3-sx2e | 23,000 | small | 52 | lazy_load | Reference |
| pedestrian_demand | fwpa-qxaf | 127,000 | medium | 66 | lazy_load | Standard |
| tree_inventory | custom | 340,000 | large | 36 | lazy_load | Operational |
| curb_inventory | custom | 650,000 | large | 35 | lazy_load | Operational |
| block_face_inventory | custom | 280,000 | large | 37 | lazy_load | Operational |
| surface_condition_history | custom | 380,000 | large | 16 | lazy_load | Reference |
| spatial_geometry | custom | 520,000 | large | 15 | lazy_load | Reference |

**Data Dictionary:**
- `mappluto`: NYC property master file with zoning, building characteristics
- `sidewalk_planimetric`: Sidewalk segments with geometric coordinates
- `lot_info`: Property lot information with assessed values
- `step_streets`: Locations of step streets (hillside pedestrian pathways)
- `tree_damage`: Tree damage assessments from storms or maintenance
- `curb_metal_protruding`: Locations of protruding metal hazards on curbs
- `pedestrian_demand`: Estimated pedestrian volume by location
- `tree_inventory`: Complete tree asset inventory
- `curb_inventory`: Curb segments with usage classification
- `block_face_inventory`: Block face inventory for street assets
- `surface_condition_history`: Historical surface condition assessments

**Downstream KPIs:**
- spatial_conflict_density (count)
- tree_asset_utilization_rate (rate)
- curb_usage_efficiency (index)
- block_face_coverage (rate)

---

### EXTENDED Domain (Budget, Planning, Resource Management)

**Purpose:** Budget tracking, project scheduling, equipment, resource allocation  
**Steward:** Planning & Analysis Manager  
**Update Frequency:** Weekly/Monthly  
**SLA Tier:** MEDIUM/LOW (30-60 days)  
**Quality Tier:** B/C (Operational/Enrichment)

| Dataset | Fourfour | Rows | Size | Priority | Cache | Status |
|---------|----------|------|------|----------|-------|--------|
| built | ugc8-s3f6 | 105,990 | medium | 83 | prefetch_incremental | Important |
| street_resurfacing_schedule | xnfm-u3k5 | 309,000 | large | 63 | lazy_load | Standard |
| street_resurfacing_inhouse | ffaf-8mrv | 602,000 | xlarge | 81 | prefetch_incremental | Important |
| project_scheduling | custom | 95,000 | medium | 34 | lazy_load | Operational |
| project_budget | custom | 62,000 | medium | 34 | lazy_load | Operational |
| project_resources | custom | 158,000 | medium | 33 | lazy_load | Operational |
| vendor_performance | custom | 28,000 | small | 33 | lazy_load | Reference |
| equipment_log | custom | 42,000 | small | 32 | lazy_load | Reference |
| cost_tracking | custom | 185,000 | medium | 23 | lazy_load | Reference |
| funding_sources | custom | 22,000 | small | 22 | lazy_load | Reference |
| noise_monitoring | custom | 92,000 | medium | 28 | lazy_load | Reference |
| air_quality | custom | 38,000 | small | 27 | lazy_load | Reference |

**Data Dictionary:**
- `built`: Construction project records with cost and budget data
- `street_resurfacing_schedule`: Planned street resurfacing projects
- `street_resurfacing_inhouse`: Completed resurfacing projects with actual costs
- `project_scheduling`: Project timelines and milestone tracking
- `project_budget`: Project budget allocations and tracking
- `project_resources`: Resource allocation (staff, equipment) by project
- `vendor_performance`: Vendor evaluation and performance metrics
- `equipment_log`: Equipment maintenance and utilization log
- `cost_tracking`: Budget vs actual cost tracking
- `funding_sources`: Funding allocations by source
- `noise_monitoring`: Construction noise monitoring data
- `air_quality`: Air quality monitoring during construction

**Downstream KPIs:**
- cost_per_inspection (rate)
- budget_variance (trend)
- project_schedule_variance (trend)
- contractor_efficiency (rate)
- resource_utilization (index)
- inspection_cost_per_unit (rate)

---

## Complete Dataset Index

### Tier 0 - Critical (5 datasets, Daily, HIGH SLA)

| ID | Name | Fourfour | Rows | Domain | Priority | Cache | Status |
|----|------|----------|------|--------|----------|-------|--------|
| 1 | inspection | a2nx-4u46 | 399,427 | sim_core | 100 | prefetch_full | Active |
| 2 | violations | 6kbp-uz6m | 312,828 | accessibility | 99 | prefetch_full | Active |
| 3 | ramp_progress | e7gc-ub6z | 187,000 | accessibility | 98 | prefetch_full | Active |
| 4 | ramp_complaints | jagj-gttd | 6,000 | accessibility | 97 | prefetch_full | Active |
| 5 | dismissals | p4u2-3jgx | 85,000 | sim_core | 96 | prefetch_full | Active |

### Tier 1 - High Priority (8 datasets, Weekly, MEDIUM SLA)

| ID | Name | Fourfour | Rows | Domain | Priority | Cache | Status |
|----|------|----------|------|--------|----------|-------|--------|
| 6 | street_permits | tqtj-sjs8 | 3,600,000 | coordination | 85 | prefetch_incremental | Active |
| 7 | street_construction_inspections | ydkf-mpxb | 11,500,000 | coordination | 84 | prefetch_incremental | Active |
| 8 | built | ugc8-s3f6 | 105,990 | extended | 83 | prefetch_incremental | Active |
| 9 | lot_info | i642-2fxq | 1,200,000 | overlays | 82 | prefetch_incremental | Active |
| 10 | complaints_311 | erm2-nwe9 | 21,300,000 | sim_core | 75 | lazy_load | Active |
| 11 | street_resurfacing_inhouse | ffaf-8mrv | 602,000 | extended | 81 | prefetch_incremental | Active |
| 12 | reinspection | gx72-kirf | 36,000 | sim_core | 80 | prefetch_incremental | Active |
| 13 | correspondences | bheb-sjfi | 30,000 | coordination | 79 | prefetch_incremental | Active |

### Tier 2 - Standard (12 datasets, Quarterly, LOW/MEDIUM SLA)

| ID | Name | Fourfour | Rows | Domain | Priority | Cache | Status |
|----|------|----------|------|--------|----------|-------|--------|
| 14 | ramp_locations | ufzp-rrqu | 217,000 | accessibility | 70 | lazy_load | Active |
| 15 | mappluto | 64uk-42ks | 858,000 | overlays | 68 | lazy_load | Active |
| 16 | sidewalk_planimetric | vfx9-tbb6 | 50,000 | overlays | 67 | lazy_load | Active |
| 17 | pedestrian_demand | fwpa-qxaf | 127,000 | extended | 66 | lazy_load | Active |
| 18 | capital_intersections | 97nd-ff3i | 7,800 | coordination | 65 | lazy_load | Active |
| 19 | street_closures_block | i6b5-j7bu | 4,300 | coordination | 64 | lazy_load | Active |
| 20 | street_resurfacing_schedule | xnfm-u3k5 | 309,000 | extended | 63 | lazy_load | Active |
| 21 | step_streets | u9au-h79y | 110 | overlays | 50 | lazy_load | Reference |
| 22 | tree_damage | j6v2-6uxq | 17,000 | overlays | 51 | lazy_load | Reference |
| 23 | curb_metal_protruding | i2y3-sx2e | 23,000 | overlays | 52 | lazy_load | Reference |
| 24 | capital_blocks | jvk9-k4re | 0 | coordination | 10 | skip | Empty |
| 25 | weekly_construction | r528-jcks | 75 | coordination | 11 | lazy_load | Stale |

### Tier 3 - Supplemental (32 datasets, On-Demand, LOW SLA)

Datasets 26-57: Photos, logs, budgets, vendors, equipment, safety, environmental, traffic, noise, air quality, complaints, outreach, contractors, costs, funding, approvals, audits, service requests, metrics, feedback, history, surfaces, geometry, etc.

**Cache Policy:** All lazy_load  
**Access:** On-demand via governance framework  
**Retention:** Indefinite

---

## KPI Materialization Catalog

### Service Delivery KPIs

| KPI ID | Name | Source Datasets | Calculation | Frequency | SLA | Domain |
|--------|------|-----------------|-------------|-----------|-----|--------|
| KPI-001 | ramp_completion_rate | ramp_progress, ramp_locations | COUNT(*) FILTER status='completed' / COUNT(*) | daily | HIGH | accessibility |
| KPI-002 | violation_closure_rate | violations | COUNT(*) FILTER closed_date IS NOT NULL / COUNT(*) | daily | HIGH | sim_core |
| KPI-003 | inspection_timeliness | inspection | PERCENTILE_CONT(days_to_complete, 0.75) | weekly | MEDIUM | sim_core |
| KPI-004 | ramp_installation_pace | ramp_progress | COUNT(*) FILTER DATE_TRUNC('month', created_date) | monthly | MEDIUM | accessibility |

### Operational Efficiency KPIs

| KPI ID | Name | Source Datasets | Calculation | Frequency | SLA | Domain |
|--------|------|-----------------|-------------|-----------|-----|--------|
| KPI-005 | inspection_cost_per_unit | inspection, cost_tracking | SUM(total_cost) / COUNT(*) | monthly | MEDIUM | sim_core |
| KPI-006 | average_resolution_time | violations | AVG(CAST(days_to_close AS FLOAT)) | weekly | MEDIUM | accessibility |
| KPI-007 | resource_utilization | equipment_log, project_resources | SUM(hours_used) / SUM(hours_available) | monthly | MEDIUM | extended |
| KPI-008 | contractor_efficiency | vendor_performance | AVG(performance_score) | monthly | MEDIUM | extended |

### Compliance & Governance KPIs

| KPI ID | Name | Source Datasets | Calculation | Frequency | SLA | Domain |
|--------|------|-----------------|-------------|-----------|-----|--------|
| KPI-009 | sla_compliance_rate | inspection, ramp_progress, violations | COUNT(*) FILTER date_diff <= sla_threshold / COUNT(*) | monthly | HIGH | sim_core |
| KPI-010 | accessibility_audit_pass_rate | accessibility_audits | COUNT(*) FILTER result='pass' / COUNT(*) | quarterly | MEDIUM | accessibility |
| KPI-011 | budget_variance | cost_tracking, project_budget | (actual_cost - budgeted_cost) / budgeted_cost | monthly | MEDIUM | extended |
| KPI-012 | permit_approval_time | street_permits | AVG(days_to_approval) | weekly | MEDIUM | coordination |

### Strategic Impact KPIs

| KPI ID | Name | Source Datasets | Calculation | Frequency | SLA | Domain |
|--------|------|-----------------|-------------|-----------|-----|--------|
| KPI-013 | new_ramp_installation_rate | ramp_progress | COUNT(*) FILTER status='completed' AND created_date > (now - interval 30 day) | monthly | MEDIUM | accessibility |
| KPI-014 | accessibility_improvement_index | accessibility_audits, violations | (pass_rate * 100) + (completion_rate * 100) | quarterly | MEDIUM | accessibility |
| KPI-015 | community_satisfaction | public_complaints | (resolved_count - reopened_count) / total_count | quarterly | LOW | sim_core |
| KPI-016 | strategic_goal_progress | all_domains | Composite index across all KPIs | quarterly | MEDIUM | sim_core |

**Total KPIs Materialized:** 51 across 4 business outcome categories  
**Borough Breakdowns:** Each KPI × 5 boroughs (Manhattan, Bronx, Brooklyn, Queens, Staten Island) = 255 KPI records  
**Quality Assurance:** All KPIs include 95% confidence intervals using Wilson Score binomial CI for rates, Poisson for counts, bootstrap for composites

---

## Analytics Schemas Catalog

### raw schema
**Purpose:** Unmodified source data from Socrata and caches  
**Tables:** 57 (one per source dataset)  
**Grain:** Row-level, as provided by source  
**Retention:** Indefinite (personal solo-user)  
**Refresh:** Daily/Weekly/Quarterly per source SLA  
**Audit Columns:** source_timestamp, load_timestamp, record_hash

### staging schema
**Purpose:** Cleaned, deduplicated, type-cast data ready for analytics  
**Tables:** 57 (one per source dataset, deduplicated by PK)  
**Grain:** Unique by primary key  
**Retention:** Indefinite (personal solo-user)  
**Transformations:**
- Deduplication: QUALIFY ROW_NUMBER() OVER (PARTITION BY pk ORDER BY _load_time DESC) = 1
- Type casting: TRY_CAST per `staging/type_mapping.json` with safe fallback
- Null handling: per data dictionary specification (required fields: NOT NULL, optional: NULL allowed)
- Calculated columns: _rn (row_number), _valid_from, _valid_to

### sim_core schema
**Purpose:** Inspection, violation, and service management analytics  
**Materialized Views:**
- `inspection_summary`: rolled-up counts, rates by inspector/borough/time
- `violation_timeline`: violation lifecycle with SLA tracking
- `resolution_funnel`: stages of closure process
- `inspector_performance`: KPIs per inspector
**Update Frequency:** Daily  
**Primary Keys:** inspection_id, violation_id

### accessibility schema
**Purpose:** Ramp program and ADA compliance analytics  
**Materialized Views:**
- `ramp_completion_status`: by neighborhood, borough, program
- `complaint_triage`: categorized, prioritized complaints
- `accessibility_readiness_index`: composite score
- `audit_findings_summary`: by finding type, severity
**Update Frequency:** Daily/Weekly  
**Primary Keys:** ramp_id, complaint_id

### coordination schema
**Purpose:** Permit, construction, and regulatory analytics  
**Materialized Views:**
- `permit_lifecycle`: issued→completed with milestones
- `construction_timeline`: start→completion tracking
- `conflict_matrix`: permit overlaps, dependencies
- `environmental_compliance_status`: regulatory requirements
**Update Frequency:** Weekly  
**Primary Keys:** permit_id, construction_id

### overlays schema
**Purpose:** Spatial enrichment and reference data analytics  
**Materialized Views:**
- `block_face_inventory`: every NYC block face
- `tree_asset_registry`: tree locations with maintenance history
- `curb_segment_registry`: curb usage inventory
- `spatial_conflicts`: geometries that overlap
**Update Frequency:** Quarterly  
**Primary Keys:** block_face_id, tree_id, curb_id

### extended schema
**Purpose:** Budget, scheduling, and planning analytics  
**Materialized Views:**
- `project_financial_summary`: budget, actuals, variance
- `resource_allocation`: equipment, staff, budget
- `schedule_variance`: planned vs. actual delivery
- `cost_analytics`: unit cost trends, efficiency metrics
**Update Frequency:** Weekly/Monthly  
**Primary Keys:** project_id, resource_id

---

## Data Dives Catalog

### Exploratory Dives

**Purpose:** Ad-hoc analysis and hypothesis testing  
**Retention:** 30 days (auto-expire if not promoted)  
**Access:** Creator only  
**Documentation:** Optional  
**Examples:**
- quick_borough_comparison: Compare metrics across 5 boroughs
- outlier_investigation: Find anomalies in inspection costs
- seasonal_pattern_detection: Identify seasonal trends in ramp complaints

### Operational Dives

**Purpose:** Regular monitoring dashboards  
**Retention:** Indefinite  
**Access:** Team access  
**Documentation:** Required (purpose, usage, refresh schedule)  
**Refresh:** Daily or Weekly  
**Owner:** Department head  
**Examples:**
- daily_inspection_status: Inspection completions, violations found, closure rate
- weekly_permit_pipeline: Active permits, processing time, approval rates
- ramp_program_status: Installation progress, budget tracking, complaint trends

### Analytical Dives

**Purpose:** Deep investigation for reporting  
**Retention:** Indefinite  
**Access:** Team access  
**Documentation:** Required (methodology, assumptions, caveats)  
**Refresh:** Weekly or Monthly  
**Owner:** Analytics manager  
**Examples:**
- ramp_completion_trend_analysis: Historical trends, forecasting, bottleneck identification
- permit_workflow_efficiency: Processing time analysis, variance by permit type
- violation_resolution_patterns: Closure rate analysis, SLA compliance by type/borough

### Strategic Dives

**Purpose:** Executive briefing and decision support  
**Retention:** Indefinite  
**Access:** Executives only  
**Documentation:** Required (business context, recommendations)  
**Refresh:** Monthly or Quarterly  
**Owner:** Executive sponsor  
**Sign-off Required:** YES (Commissioner approval)  
**Examples:**
- strategic_goal_progress: Multi-dimensional goal tracking, achievement index
- commissioner_briefing: Executive summary across all programs, risk areas, recommendations

---

## Governance Integration

### Classification Framework

**All 57 datasets classified by:**
- **Tier (0-3):** Critical → High Priority → Standard → Supplemental
- **Size:** tiny → small → medium → large → xlarge
- **Update Frequency:** real-time → daily → weekly → monthly → quarterly → static
- **SLA Tier:** HIGH (14d) → MEDIUM (30d) → LOW (60d)
- **Cache Policy:** prefetch_full → prefetch_incremental → lazy_load → skip
- **Priority Score:** 100 (critical) → 5 (deprecated)
- **Domain Schema:** sim_core | accessibility | coordination | overlays | extended
- **Quality Tier:** A (authoritative) → B (operational) → C (enrichment) → D (reference)
- **Sensitivity:** public → internal → restricted → confidential

### Quality Gates

**Raw Layer:**
- Row count matches source system
- PK uniqueness = 100%
- Audit columns present (source_timestamp, load_timestamp, record_hash)

**Staging Layer:**
- PK uniqueness = 100%
- Row count: 95-110% of raw (allows for dedup)
- No nulls in required fields
- Data types match specification

**Analytics Layer:**
- Monthly reconciliation vs. staging layer
- Data latency <= 24 hours
- Row count stability (no >20% swings without explanation)

### SLA Tracking

**HIGH SLA Datasets (14 days):** inspection, violations, ramp_progress, dismissals, ramp_complaints, complaints_311, service_requests  
**MEDIUM SLA Datasets (30 days):** street_permits, construction_inspections, built, lot_info, resurfacing_inhouse, reinspection, correspondences, capital_intersections, street_closures, resurfacing_schedule  
**LOW SLA Datasets (60 days):** All tier 2/3 datasets

### Audit Logging

**Automatically Captures:**
- Data access (read/write/delete)
- Dataset ingestion events (dataset name, row count, load time, tier, priority, domain)
- Lineage transitions (source→target transformations)
- Quality gate violations
- Access control violations
- KPI calculation runs (inputs, outputs, dependencies)

**Retention:** Indefinite (personal solo-user mode)  
**Format:** JSONL (one event per line)  
**Location:** `pipeline/logs/governance_audit.jsonl`

---

## Data Lineage

### Source → Raw → Staging → Analytics → KPI Flow

```
Socrata Sources (57)
    │
    ├─→ raw.inspection (399K rows)
    │   ├─→ staging.inspection (399K rows, deduplicated)
    │   └─→ sim_core.inspection_summary (aggregated by inspector/borough/time)
    │       └─→ KPI-001: violation_closure_rate
    │           KPI-002: inspection_timeliness
    │           KPI-009: sla_compliance_rate
    │
    ├─→ raw.violations (313K rows)
    │   ├─→ staging.violations (313K rows, deduplicated)
    │   └─→ sim_core.violation_timeline (with SLA tracking)
    │       └─→ KPI-002: violation_closure_rate
    │           KPI-010: accessibility_audit_pass_rate
    │
    ├─→ raw.ramp_progress (187K rows)
    │   ├─→ staging.ramp_progress (187K rows, deduplicated)
    │   └─→ accessibility.ramp_completion_status (by neighborhood/borough)
    │       └─→ KPI-001: ramp_completion_rate
    │           KPI-004: ramp_installation_pace
    │           KPI-014: accessibility_improvement_index
    │
    └─→ ... (54 more datasets following same pattern)
```

### Cross-Domain Lineage

**Conflict Detection Pipeline:**
```
street_permits (3.6M) → raw.street_permits
    ├─→ staging.street_permits
    └─→ coordination.permit_lifecycle
        └─→ KPI-012: permit_approval_time
            └─→ Commissioner Briefing Dashboard
```

**Cost Analysis Pipeline:**
```
street_permits (3.6M) + cost_tracking (185K) → raw layer
    ├─→ staging layer (deduplicated)
    └─→ extended.project_financial_summary
        ├─→ KPI-005: inspection_cost_per_unit
        ├─→ KPI-011: budget_variance
        └─→ Executive Budget Review Dashboard
```

**Quality Score Pipeline:**
```
All 57 datasets → quality_assessment
    ├─→ completeness (non-null %), validity (TRY_CAST success), consistency (duplicate %), freshness (days since update)
    └─→ sim_core.quality_scorecard
        └─→ KPI: data_quality_score (composite: 35% completeness + 25% validity + 25% consistency + 15% freshness)
```

---

## Access & Discovery

### Dataset Discovery

1. **Browse by Domain:** Start with sim_core, accessibility, coordination, overlays, or extended domains above
2. **Search by Fourfour ID:** All fourfour IDs reference the NYC Open Data portal (data.cityofnewyork.us)
3. **Query by Tier:** Filter by criticality (Tier 0-3) and your availability/latency requirements
4. **Check Governance:** Each dataset entry includes SLA, quality tier, cache policy, and retention

### Schema Discovery

All SQL queries against DuckDB default to `main.staging` schema (cleaned, deduplicated data ready for analysis).

```sql
SELECT * FROM staging.inspection LIMIT 10;           -- Cleaned SIM data
SELECT * FROM sim_core.inspection_summary;             -- Pre-aggregated analytics
SELECT * FROM serving.kpi_borough_results WHERE kpi_id = 'KPI-001';  -- KPI values
```

### Governance Verification

All datasets classified in `pipeline/config/personal_data_governance.json`:
- Check tier, size, frequency, SLA, cache policy for any dataset
- Validate retention is indefinite (personal solo-user mode)
- View audit trail at `pipeline/logs/governance_audit.jsonl`

---

## Related Documentation

- **Governance Framework:** `pipeline/config/personal_data_governance.json` (classification, retention, lineage)
- **Unified Dataset Model:** `pipeline/config/unified_57_datasets.json` (tier-based ingestion strategy)
- **Pipeline Specification:** `PIPELINE_FINAL_SPECIFICATION.md` (technical implementation)
- **SQL Reference:** `pipeline/sql/` directory (raw, staging, analytics, serving layers)

---

**Last Verified:** 2026-06-18  
**Governance Mode:** Personal Solo-User (Indefinite Retention)  
**Data Lake Status:** Production-Ready
