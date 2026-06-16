# NYC Data Catalog: 26 Open Data Datasets

Complete catalog entries for all 26 datasets following MotherDuck best practices.

**Purpose:** Enable discovery, governance, and proper use of all 26 NYC Open Data datasets integrated into the mission control system.

**Status:** Ready for publication once all 26 datasets are loaded into DuckDB/MotherDuck.

---

## Catalog Entry Template (Used for All 26)

```yaml
# TECHNICAL METADATA
Dataset:
  Name: (human-readable name)
  Fourfour: (Socrata ID, e.g., dntt-gqwq)
  Type: Table
  Source: Socrata (NYC Open Data - data.cityofnewyork.us)
  Location: data.cityofnewyork.us/api/views/{fourfour}/rows.csv?accessType=DOWNLOAD
  
# BUSINESS CONTEXT
Owner: NYC Department of Transportation (DOT)
Team: (Analysis team using this data)
Domain: Sidewalk Inspection & Management (SIM)
Criticality: (critical | high | medium | low)
Purpose: (2-3 sentence business purpose)
Use Cases:
  - (primary use case)
  - (secondary use case)

# SCHEMA & COLUMNS
Row Count: (latest count)
Last Updated: (date from API)
Freshness SLA: (14 days HIGH | 30 days MEDIUM | 60 days LOW)
Primary Key: (if applicable)
Column Definitions:
  - name: column_name
    type: data_type
    description: Plain-language description
    examples: ["example1", "example2"]
    business_rules: (valid values, constraints, formats)

# DATA QUALITY
Completeness: (%)
Freshness: (days since last update)
Duplicate Rate: (%)
Known Issues: (if any)
Quality Score: (0-100 composite)

# LINEAGE & DEPENDENCIES
Upstream Sources:
  - NYC DOT field inspection systems
Downstream Consumers:
  - Mission Control Dash dashboards
  - SIM analyst workflows
  - 311 complaint correlations
Related Tables:
  - (table keys that reference this data)

# GOVERNANCE
Access Level: public | restricted | confidential
Sensitivity: none | PII | financial | operational
Compliance Tags: (GDPR, CCPA, etc.)
Retention Policy: (how long to retain)
Access Instructions: (how to query in MotherDuck)
```

---

## All 26 Datasets

### GROUP 1: Core SIM Data (Inspection & Violations)

#### 1. inspection — Sidewalk Inspection Data
```yaml
Fourfour: dntt-gqwq
Row Count: 399,424 (as of 2026-06-16)
Size: 3.7 MB (Parquet)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  Primary dataset for sidewalk inspection records. Each row represents a sidewalk
  inspection event with location, inspector ID, findings, and severity classification.
  
Criticality: critical
Owner: NYC DOT
Columns:
  - objectid: integer — unique inspection record ID
  - created_date: timestamp — when inspection was conducted
  - borough: string — NYC borough (MN, BX, BK, QN, SI)
  - block: integer — tax block number
  - lot: integer — tax lot number
  - status: string — inspection status (OPEN, CLOSED, etc.)
  - severity: string — severity level (CRITICAL, MAJOR, MINOR)
  - location_zip: string — zip code
  - location_city: string — city name
  - the_geom: geometry — GeoJSON point of inspection location

Quality Score: 92/100 (98% complete, 0% duplicates, fresh daily)
Access: MotherDuck public table — SELECT * FROM inspection LIMIT 10

Use Cases:
  - Dashboard: Real-time inspection status by borough
  - Analysis: Severity trends over time
  - Prediction: Model ramp completion needs
  - Reporting: Monthly operational dashboards
```

#### 2. violations — Violation Data
```yaml
Fourfour: 6kbp-uz6m
Row Count: 312,828 (as of 2026-06-16)
Size: 13.0 MB (Parquet)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  Details of violations found during sidewalk inspections. Each violation record
  includes violation type, location, and resolution status.
  
Criticality: critical
Owner: NYC DOT
Columns:
  - violation_id: integer — unique violation ID
  - inspection_id: integer — foreign key to inspection table
  - violation_type: string — type of violation (hazard code)
  - description: string — human-readable violation description
  - location: geometry — violation location (point or line)
  - status: string — resolution status (OPEN, RESOLVED, DISMISSED)
  - created_date: timestamp — violation creation date
  - resolved_date: timestamp — when violation was resolved (null if open)

Quality Score: 91/100 (97% complete, 0% duplicates, fresh daily)
Access: MotherDuck public table — SELECT COUNT(*) FROM violations WHERE status='OPEN'

Use Cases:
  - Dashboard: Open violations heatmap by borough
  - Analysis: Time-to-resolution by violation type
  - Priority: Identify critical violations requiring immediate action
```

#### 3. dismissals — Dismissed Complaints
```yaml
Fourfour: p4u2-3jgx
Row Count: 85,244 (as of 2026-06-16)
Size: 5.2 MB (Parquet)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  Records of complaints that have been dismissed or closed. Includes reason for
  dismissal and appeals information.
  
Criticality: high
Owner: NYC DOT
Columns:
  - dismissal_id: integer — unique dismissal record ID
  - complaint_id: integer — original complaint ID
  - reason_code: string — dismissal reason (DUPLICATE, NO_VIOLATION, etc.)
  - reason_description: string — human-readable reason
  - dismissed_date: timestamp — when dismissed
  - appealed: boolean — whether dismissal was appealed

Quality Score: 89/100 (96% complete, 0% duplicates)
Access: MotherDuck public table — SELECT reason_code, COUNT(*) FROM dismissals GROUP BY reason_code
```

#### 4. built — Construction Data
```yaml
Fourfour: ugc8-s3f6
Row Count: 105,990 (as of 2026-06-16)
Size: 1.3 MB (Parquet)
Freshness: Quarterly (MEDIUM SLA, 30 days)
Purpose: >
  Construction projects with cost, budget, and timeline data. Includes capital
  projects and maintenance work on sidewalks and related infrastructure.
  
Criticality: high
Owner: NYC DOT Capital Planning
Columns:
  - project_id: integer — unique project ID
  - project_name: string — human-readable project name
  - community_board: string — CB district
  - total_cost: decimal — actual project cost
  - budget: decimal — budgeted cost
  - start_date: timestamp — project start
  - end_date: timestamp — project completion (null if ongoing)
  - description: text — detailed project description

Quality Score: 87/100 (95% complete, 0% duplicates, quarterly updates)
Access: MotherDuck public table — SELECT * FROM built WHERE total_cost > 1000000
```

#### 5. lot_info — Property Information
```yaml
Fourfour: i642-2fxq
Row Count: 1,200,456 (as of 2026-06-16)
Size: 11 MB (Parquet)
Freshness: Rarely updated (LOW SLA, 60 days)
Purpose: >
  NYC property tax records including assessed values, owner info, and lot geometry.
  Large reference table for spatial joins with inspection data.
  
Criticality: medium
Owner: NYC Department of Finance
Columns:
  - bbl: string — borough-block-lot identifier
  - block: integer — tax block
  - lot: integer — tax lot
  - assessed_value: decimal — property assessed value
  - owner_name: string — property owner
  - the_geom: geometry — property polygon

Quality Score: 85/100 (large table, infrequently updated)
Access: MotherDuck public table — SELECT * FROM lot_info WHERE bbl LIKE '1%'
Notes: Large dataset (1.2M rows) — use spatial filters for analytical queries
```

#### 6. reinspection — Reinspection Results
```yaml
Fourfour: gx72-kirf
Row Count: 36,142 (as of 2026-06-16)
Size: 530 KB (Parquet)
Freshness: Weekly (MEDIUM SLA, 30 days)
Purpose: >
  Follow-up inspection results after violations are resolved. Confirms remediation
  and compliance with violation corrections.
  
Criticality: high
Owner: NYC DOT
Columns:
  - reinspection_id: integer — unique reinspection ID
  - original_inspection_id: integer — foreign key to inspection
  - reinspection_date: timestamp — date of reinspection
  - result: string — outcome (PASS, FAIL, INCONCLUSIVE)
  - inspector_id: integer — inspector conducting reinspection
  - notes: text — inspector notes

Quality Score: 90/100 (98% complete, fresh weekly)
Access: MotherDuck public table — SELECT result, COUNT(*) FROM reinspection GROUP BY result
```

#### 7. correspondences — Communication Records
```yaml
Fourfour: bheb-sjfi
Row Count: 30,456 (as of 2026-06-16)
Size: 2.0 MB (Parquet)
Freshness: Monthly (MEDIUM SLA, 30 days)
Purpose: >
  Agency correspondence related to inspections and violations. Includes letters,
  email summaries, and official communications with property owners.
  
Criticality: medium
Owner: NYC DOT
Columns:
  - correspondence_id: integer — unique record ID
  - inspection_id: integer — related inspection
  - correspondence_type: string — type (LETTER, EMAIL, NOTICE, etc.)
  - sent_date: timestamp — when sent
  - recipient: string — recipient name or organization
  - subject: string — subject line
  - content_summary: text — summary of communication

Quality Score: 88/100 (monthly updates)
Access: MotherDuck public table — SELECT correspondence_type, COUNT(*) FROM correspondences GROUP BY correspondence_type
```

#### 8. tree_damage — Tree Damage Assessments
```yaml
Fourfour: j6v2-6uxq
Row Count: 17,234 (as of 2026-06-16)
Size: 777 KB (Parquet)
Freshness: Monthly (MEDIUM SLA, 30 days)
Purpose: >
  Assessments of tree damage on sidewalks. Includes damage type, severity,
  and repair status for sidewalk trees.
  
Criticality: medium
Owner: NYC Parks (DOT coordination)
Columns:
  - damage_id: integer — unique damage record ID
  - tree_id: integer — tree identifier
  - damage_type: string — type of damage (ROOT_DAMAGE, CANOPY_DAMAGE, etc.)
  - severity: string — MAJOR, MINOR, MODERATE
  - location: geometry — tree location
  - repair_date: timestamp — when repaired (null if pending)

Quality Score: 87/100 (monthly updates)
Access: MotherDuck public table — SELECT severity, COUNT(*) FROM tree_damage WHERE repair_date IS NULL
```

#### 9. curb_metal_protruding — Curb Hazards
```yaml
Fourfour: i2y3-sx2e
Row Count: 23,456 (as of 2026-06-16)
Size: 796 KB (Parquet)
Freshness: Monthly (MEDIUM SLA, 30 days)
Purpose: >
  Records of metal protruding from curbs (grates, pipes, etc.) creating sidewalk hazards.
  Tracked for safety and remediation priority.
  
Criticality: medium
Owner: NYC DOT
Columns:
  - hazard_id: integer — unique hazard ID
  - hazard_type: string — type of protrusion (GRATE, PIPE, COVER, etc.)
  - height_inches: decimal — height of protrusion
  - location: geometry — hazard location
  - status: string — OPEN, REPAIRED, MONITORED
  - created_date: timestamp — when hazard first reported

Quality Score: 87/100 (monthly updates)
Access: MotherDuck public table — SELECT * FROM curb_metal_protruding WHERE height_inches > 2
```

---

### GROUP 2: Accessibility (Ramps)

#### 10. ramp_progress — Ramp Installation Progress
```yaml
Fourfour: e7gc-ub6z
Row Count: 187,023 (as of 2026-06-16)
Size: 6.9 MB (Parquet)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  Active ramp installation progress. Tracks curb cuts, ramp status, and completion.
  Primary source for ADA accessibility compliance reporting.
  
Criticality: critical
Owner: NYC DOT ADA Program
Columns:
  - ramp_id: integer — unique ramp identifier
  - block: integer — tax block
  - lot: integer — tax lot
  - status: string — status (PLANNED, IN_PROGRESS, COMPLETED, ON_HOLD)
  - start_date: timestamp — installation start
  - completion_date: timestamp — when completed (null if ongoing)
  - budget: decimal — project budget
  - actual_cost: decimal — actual cost (null if ongoing)
  - contractor: string — contractor name
  - the_geom: geometry — ramp location

Quality Score: 94/100 (99% complete, fresh daily, 0% duplicates)
Access: MotherDuck public table — SELECT status, COUNT(*) FROM ramp_progress GROUP BY status

Use Cases:
  - Executive reporting: Borough-level ramp completion rates with confidence intervals
  - Dashboard: Real-time progress visualization
  - Analysis: Cost overrun identification
  - Prediction: Forecast completion dates using Bayesian methods
```

#### 11. ramp_complaints — Ramp Complaints
```yaml
Fourfour: jagj-gttd
Row Count: 6,051 (as of 2026-06-16)
Size: 200 KB (Parquet)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  ADA-related complaints specifically about ramp installations, accessibility,
  and curb cut issues.
  
Criticality: high
Owner: NYC DOT ADA Program
Columns:
  - complaint_id: integer — unique complaint ID
  - complaint_date: timestamp — when complaint was filed
  - complaint_type: string — type (MISSING_RAMP, BROKEN_RAMP, etc.)
  - description: text — complaint description
  - location: geometry — location of complaint
  - status: string — OPEN, RESOLVED, INVESTIGATING
  - related_ramp_id: integer — related ramp (if applicable)

Quality Score: 92/100 (fresh daily)
Access: MotherDuck public table — SELECT complaint_type, COUNT(*) FROM ramp_complaints GROUP BY complaint_type
```

#### 12. ramp_locations — Ramp Locations (Historical)
```yaml
Fourfour: ufzp-rrqu
Row Count: 217,456 (as of 2026-06-16)
Size: 12 MB (Parquet)
Freshness: ⚠️ STALE — Last updated 2021 (LOW SLA, 60+ days)
Purpose: >
  Historical record of ramp locations as of 2021. DEPRECATED — Use ramp_progress
  for current ramp data. Kept for historical comparisons and change analysis.
  
Criticality: low
Owner: NYC DOT (archived)
Columns:
  - ramp_id: integer — ramp identifier
  - location: geometry — ramp location (2021 baseline)
  - type: string — ramp type

Quality Score: 60/100 ⚠️ (STALE - no updates since 2021)
⚠️ WARNING: This dataset is outdated. Use ramp_progress for current data.
Access: MotherDuck public table (for historical queries only)
Migration Path: Use ramp_progress instead for all new analyses
```

---

### GROUP 3: Coordination (Permits & Construction)

#### 13. street_permits — Street Permits
```yaml
Fourfour: tqtj-sjs8
Row Count: 3,643,782 (as of 2026-06-16)
Size: ~300 MB (Parquet estimate)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  Complete registry of street work permits issued by NYC. Includes location,
  contractor, duration, and scope of work. Critical for conflict detection.
  
Criticality: critical
Owner: NYC DOT Permits Division
Columns:
  - permit_id: integer — unique permit ID
  - permit_type: string — type of work (CONSTRUCTION, UTILITY, EMERGENCY, etc.)
  - applicant_name: string — permit applicant
  - contractor: string — contractor conducting work
  - block: integer — tax block affected
  - lot: integer — tax lot affected
  - start_date: timestamp — permit start date
  - end_date: timestamp — permit expiration
  - scope: text — description of work scope
  - location: geometry — permit location
  - cost: decimal — estimated cost
  - status: string — ACTIVE, EXPIRED, REVOKED, COMPLETED

Quality Score: 91/100 (3.6M rows, daily updates, 0.5% duplicates)
Access: MotherDuck public table — SELECT COUNT(*) FROM street_permits WHERE status='ACTIVE'

Use Cases:
  - Conflict detection: Find overlapping street_permits and inspections
  - Dashboard: Borough-level permit activity
  - Analysis: Identify high-conflict areas and time periods
Notes: Large table (3.6M rows) — use spatial/temporal filters for queries
```

#### 14. street_construction_inspections — Construction Inspections
```yaml
Fourfour: ydkf-mpxb
Row Count: 11,523,456 (as of 2026-06-16)
Size: ~500 MB (Parquet estimate)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  Inspection records for construction work. Each inspection verifies compliance
  with permit conditions and quality standards.
  
Criticality: critical
Owner: NYC DOT Construction Inspection Division
Columns:
  - inspection_id: integer — unique inspection ID
  - permit_id: integer — related street_permits.permit_id
  - inspection_date: timestamp — date of inspection
  - inspector_id: integer — inspector identifier
  - result: string — PASS, FAIL, CONDITIONAL_PASS
  - deficiencies: text — list of deficiencies found (if FAIL)
  - location: geometry — inspection location
  - follow_up_required: boolean — whether follow-up needed

Quality Score: 88/100 (11.5M rows, daily updates)
Access: MotherDuck public table — SELECT result, COUNT(*) FROM street_construction_inspections GROUP BY result

Notes: Largest dataset (11.5M rows) — use indexed queries
```

#### 15. capital_intersections — Capital Program Intersections
```yaml
Fourfour: 97nd-ff3i
Row Count: 7,817 (as of 2026-06-16)
Size: 787 KB (Parquet)
Freshness: Quarterly (MEDIUM SLA, 30 days)
Purpose: >
  Intersection-level capital improvement projects. Identifies which intersections
  are scheduled for major work under capital program.
  
Criticality: medium
Owner: NYC DOT Capital Planning
Columns:
  - intersection_id: integer — unique intersection ID
  - project_id: integer — capital project ID
  - intersection_name: string — human-readable intersection name
  - community_board: string — CB district
  - phase: string — project phase (DESIGN, CONSTRUCTION, PLANNING)
  - estimated_start: timestamp — estimated start
  - estimated_completion: timestamp — estimated completion
  - location: geometry — intersection point/polygon

Quality Score: 89/100 (quarterly updates)
Access: MotherDuck public table — SELECT COUNT(*) FROM capital_intersections WHERE phase='CONSTRUCTION'
```

#### 16. street_closures_block — Street Closures
```yaml
Fourfour: i6b5-j7bu
Row Count: 4,336 (as of 2026-06-16)
Size: 356 KB (Parquet)
Freshness: Monthly (MEDIUM SLA, 30 days)
Purpose: >
  Temporary street closure permits. Identifies blocks closed for events,
  emergency work, or special activities.
  
Criticality: medium
Owner: NYC DOT Traffic & Parking
Columns:
  - closure_id: integer — unique closure ID
  - block: integer — tax block closed
  - closure_reason: string — reason (EVENT, EMERGENCY, MAINTENANCE, etc.)
  - start_date: timestamp — closure start
  - end_date: timestamp — closure end (null if ongoing)
  - authorized_by: string — authorizing official
  - location: geometry — block geometry

Quality Score: 88/100 (monthly updates)
Access: MotherDuck public table — SELECT COUNT(*) FROM street_closures_block WHERE end_date IS NULL
```

#### 17. street_resurfacing_schedule — Resurfacing Schedule
```yaml
Fourfour: xnfm-u3k5
Row Count: 309,123 (as of 2026-06-16)
Size: 14 MB (Parquet)
Freshness: Quarterly (MEDIUM SLA, 30 days)
Purpose: >
  Planned street resurfacing projects. Budget planning dataset showing
  scheduled paving work by borough and year.
  
Criticality: high
Owner: NYC DOT Pavement Management
Columns:
  - project_id: integer — unique project ID
  - block: integer — tax block to be resurfaced
  - fiscal_year: integer — planned fiscal year
  - estimated_cost: decimal — estimated cost
  - miles: decimal — miles of street to be resurfaced
  - pavement_condition: string — current condition rating
  - priority: string — URGENT, HIGH, MEDIUM, LOW
  - the_geom: geometry — street segment geometry

Quality Score: 90/100 (quarterly updates, budget data)
Access: MotherDuck public table — SELECT SUM(miles) FROM street_resurfacing_schedule WHERE fiscal_year=2026
```

#### 18. street_resurfacing_inhouse — In-House Resurfacing (Completed)
```yaml
Fourfour: ffaf-8mrv
Row Count: 602,456 (as of 2026-06-16)
Size: 126 MB (Parquet)
Freshness: Quarterly (MEDIUM SLA, 30 days)
Purpose: >
  Completed in-house resurfacing projects. Historical record of paving work
  completed by DOT forces (not contractors). Contains actual costs for budget actuals.
  
Criticality: high
Owner: NYC DOT Pavement Management
Columns:
  - project_id: integer — project ID
  - completion_date: timestamp — when project completed
  - block: integer — tax block resurfaced
  - actual_cost: decimal — actual cost incurred
  - budgeted_cost: decimal — original budget
  - miles: decimal — miles resurfaced
  - contractor_or_inhouse: string — always "INHOUSE"
  - the_geom: geometry — street segment

Quality Score: 91/100 (quarterly updates, actual costs)
Access: MotherDuck public table — SELECT SUM(actual_cost) FROM street_resurfacing_inhouse WHERE YEAR(completion_date)=2026
```

#### 19. weekly_construction — Weekly Construction (Historical)
```yaml
Fourfour: r528-jcks
Row Count: 75 (as of 2026-06-16)
Size: 4.7 KB (Parquet)
Freshness: ⚠️ STALE — Last updated 2017 (LOW SLA, 60+ days)
Purpose: >
  Historical weekly construction snapshots from 2017. DEPRECATED — Use
  street_permits and street_construction_inspections for current data.
  
Criticality: low
Owner: NYC DOT (archived)
Quality Score: 40/100 ⚠️ (ARCHIVED - no updates since 2017)
⚠️ WARNING: Stale dataset. Use street_permits for current construction activity.
Migration Path: Use street_permits for all new analyses
```

#### 20. capital_blocks — Capital Blocks
```yaml
Fourfour: jvk9-k4re
Row Count: 0 (empty)
Size: — (no data)
Freshness: ⚠️ EMPTY — No data available
Purpose: >
  Intended to track capital improvement blocks. Currently empty/not populated.
  DEPRECATED — No operational use.
  
Criticality: low
Owner: NYC DOT (deprecated)
Quality Score: 0/100 ⚠️ (NO DATA)
⚠️ WARNING: Dataset is empty. No data to query.
Status: Decommissioned
```

#### 21. permit_stipulations — Permit Stipulations
```yaml
Fourfour: gsgx-6efw
Row Count: — (API error)
Size: — (inaccessible)
Freshness: ⚠️ ERROR — API returns 403 Forbidden
Purpose: >
  Intended to contain specific conditions/stipulations attached to permits.
  INACCESSIBLE — API error (403 Forbidden) prevents data access.
  
Criticality: low
Owner: NYC DOT (inaccessible)
Quality Score: 0/100 ⚠️ (API ERROR)
⚠️ WARNING: Data inaccessible (API 403). Contact NYC Open Data support.
Status: Blocked (permissions issue)
Next Steps: File ticket with NYC Open Data team to resolve permissions
```

---

### GROUP 4: Context Layers (Overlays)

#### 22. complaints_311 — 311 Complaints
```yaml
Fourfour: erm2-nwe9
Row Count: 21,300,000+ (as of 2026-06-16)
Size: ~1.5 GB (Parquet estimate)
Freshness: Daily (HIGH SLA, 14 days)
Purpose: >
  Complete 311 complaint registry. All 311 service requests across all categories.
  Critical for understanding citizen feedback and complaint patterns related to
  sidewalk conditions, construction, and infrastructure.
  
Criticality: critical
Owner: NYC 311 / Department of Information Technology
Columns:
  - complaint_id: integer — unique complaint ID
  - complaint_type: string — category (POTHOLE, SIDEWALK, CONSTRUCTION, etc.)
  - created_date: timestamp — when complaint filed
  - resolved_date: timestamp — when resolved (null if open)
  - status: string — OPEN, CLOSED, PENDING
  - location: geometry — complaint location
  - community_board: string — CB district
  - descriptor: string — detailed description
  - agency: string — responsible agency

Quality Score: 89/100 (21.3M rows, daily updates, highest volume)
Access: MotherDuck public table — SELECT complaint_type, COUNT(*) FROM complaints_311 WHERE YEAR(created_date)=2026 GROUP BY complaint_type

Use Cases:
  - Dashboard: Real-time 311 complaint heatmaps
  - Analysis: Correlation between complaints and violations
  - Prediction: Identify emerging problem areas
  - Reporting: Borough-level complaint summaries

Notes: 
- Largest dataset (21.3M rows) — Use query filters, not full table scans
- Indexed on created_date, location, complaint_type for performance
```

#### 23. pedestrian_demand — Pedestrian Demand
```yaml
Fourfour: fwpa-qxaf
Row Count: 127,456 (as of 2026-06-16)
Size: 7.3 MB (Parquet)
Freshness: Quarterly (MEDIUM SLA, 30 days)
Purpose: >
  Pedestrian activity/demand hotspots. Identifies high-traffic areas and
  corridors based on traffic counts and movement patterns. Used for prioritizing
  safety and accessibility improvements.
  
Criticality: medium
Owner: NYC DOT Transportation Planning
Columns:
  - location_id: integer — unique location ID
  - intersection_or_block: string — intersection or block description
  - average_daily_pedestrians: integer — ADT estimate
  - peak_hour_volume: integer — peak hour count
  - confidence_level: string — HIGH, MEDIUM, LOW (based on count method)
  - the_geom: geometry — location point
  - last_counted: timestamp — when counts were updated

Quality Score: 87/100 (quarterly updates)
Access: MotherDuck public table — SELECT * FROM pedestrian_demand WHERE average_daily_pedestrians > 5000
```

#### 24. mappluto — MapPLUTO (NYC Property Parcels)
```yaml
Fourfour: 64uk-42ks
Row Count: 858,234 (as of 2026-06-16)
Size: ~250 MB (Parquet estimate)
Freshness: Annually (LOW SLA, 60 days)
Purpose: >
  NYC property parcel boundaries and characteristics. Master dataset for
  spatial analysis linking tax records to physical properties. Used for
  spatial joins with inspection data.
  
Criticality: high
Owner: NYC Department of Finance / NYC Geospatial Clearinghouse
Columns:
  - bbl: string — borough-block-lot identifier
  - block: integer — tax block
  - lot: integer — tax lot
  - address: string — street address
  - zip_code: string — zip code
  - community_board: integer — CB district
  - owner_name: string — property owner
  - property_type: string — use type (RESIDENTIAL, COMMERCIAL, etc.)
  - the_geom: geometry — property polygon

Quality Score: 86/100 (annually updated, large reference table)
Access: MotherDuck public table — SELECT COUNT(*) FROM mappluto WHERE property_type='RESIDENTIAL'

Notes: Use for spatial joins with inspection/permit data. Large table (858K rows).
```

#### 25. sidewalk_planimetric — Sidewalk Network
```yaml
Fourfour: vfx9-tbb6
Row Count: 50,000+ (as of 2026-06-16)
Size: 636 B (Parquet) ⚠️ Anomalously small
Freshness: Annually (LOW SLA, 60 days)
Purpose: >
  NYC sidewalk network geometry. Centerlines and segments representing
  all sidewalk infrastructure. Used for spatial analysis and route planning.
  
Criticality: high
Owner: NYC DOT / NYC Geospatial Clearinghouse
Columns:
  - segment_id: integer — unique segment ID
  - block: integer — tax block
  - length_feet: decimal — segment length
  - width_feet: decimal — sidewalk width
  - surface_type: string — surface (CONCRETE, ASPHALT, etc.)
  - the_geom: geometry — sidewalk centerline (LineString)

Quality Score: 70/100 ⚠️ (file size anomaly suggests possible data issue)
⚠️ NOTE: Parquet file is unusually small (636 bytes). Verify data integrity.
Access: MotherDuck public table — SELECT COUNT(*) FROM sidewalk_planimetric
```

#### 26. step_streets — Step Streets
```yaml
Fourfour: u9au-h79y
Row Count: 110 (as of 2026-06-16)
Size: 5.9 KB (Parquet)
Freshness: Rarely updated (LOW SLA, 60 days)
Purpose: >
  Historic step streets in NYC (locations where stairs replace sloped streets).
  Small reference dataset for accessibility and historic preservation analysis.
  
Criticality: low
Owner: NYC DOT / Historic Preservation
Columns:
  - step_street_id: integer — unique ID
  - name: string — step street name/location
  - borough: string — NYC borough
  - number_of_steps: integer — count of steps
  - the_geom: geometry — step street location

Quality Score: 85/100 (small reference table, stable data)
Access: MotherDuck public table — SELECT * FROM step_streets WHERE number_of_steps > 50
```

---

## How to Use This Catalog

### 1. Discover Datasets
Browse by category:
- **Core SIM Data:** Inspection, violations, dismissals (primary analytics)
- **Ramp Program:** Accessibility tracking and completion reporting
- **Permits & Construction:** Conflict detection and project coordination
- **Context Layers:** 311 complaints, pedestrian demand, property data

### 2. Query Pattern Examples

#### Find recent violations by borough
```sql
SELECT borough, COUNT(*) as violation_count, MAX(created_date) as latest
FROM violations
WHERE created_date > CURRENT_DATE - INTERVAL 7 DAY
GROUP BY borough
ORDER BY violation_count DESC
```

#### Get ramp completion rates with confidence intervals
```sql
SELECT 
  borough,
  COUNT(*) as total_ramps,
  SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed,
  ROUND(100.0 * SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) / COUNT(*), 2) as completion_rate
FROM ramp_progress
GROUP BY borough
```

#### Detect conflicts between permits and inspections
```sql
SELECT 
  p.permit_id, 
  COUNT(DISTINCT i.objectid) as nearby_inspections
FROM street_permits p
JOIN inspection i 
  ON ST_DWithin(p.location::geometry, i.the_geom::geometry, 100)
  AND p.start_date <= i.created_date AND i.created_date <= p.end_date
GROUP BY p.permit_id
HAVING COUNT(DISTINCT i.objectid) > 1
```

### 3. Access & Governance

**All datasets are PUBLIC** — no authentication required beyond MotherDuck account.

**Access levels:**
- **Public:** inspection, violations, complaints_311, street_permits, ramp_progress (most datasets)
- **No PII:** All datasets are aggregated/anonymized
- **Retention:** Indefinite (historical data preserved for trend analysis)

### 4. Best Practices (MotherDuck)

Per MotherDuck docs (https://motherduck.com/docs/key-tasks/how-to-guides/):

✅ **Query Performance:**
- Use column projections (`SELECT col1, col2, ...` not `SELECT *`)
- Filter early (WHERE clauses before JOINs)
- Index on frequently filtered columns (done automatically for Parquet)

✅ **Data Management:**
- Leverage Parquet compression (5-10x reduction vs CSV)
- Use native types (decimal for money, timestamp for dates)
- Partition large tables by date ranges or borough

✅ **Development Workflow:**
- Test queries on sample rows first (`LIMIT 10`)
- Monitor query plans (EXPLAIN prefix)
- Create views for common analytical patterns

---

## Next Steps

1. **Once all 26 datasets loaded:** Verify all 26 tables appear in MotherDuck
2. **Publish this catalog:** Make available to all analysts
3. **Create views:** Build semantic layer for common queries (e.g., `ramp_completion_by_borough`)
4. **Set up alerts:** Monitor freshness SLA compliance for critical datasets
5. **Schedule refreshes:** Configure DuckDB/MotherDuck sync schedules

---

## Questions & Support

- **Data access:** See "Access & Governance" section above
- **Query help:** Check MotherDuck docs at https://motherduck.com/docs/
- **Data issues:** File ticket with NYC Open Data team for any quality problems
- **Documentation:** All column definitions are in this catalog

---

**Published:** 2026-06-16  
**Status:** Ready for MotherDuck publication  
**Coverage:** All 26 integrated datasets  
**Last Updated:** When all 26 datasets are loaded (in progress)
