# Complete Entity-Relationship Diagram (ERD)
## All 24 NYC DOT Socrata Datasets

**Generated:** 2026-06-11  
**Total Datasets:** 24  
**Total Columns:** 554  
**Total Relationships:** 414 inferred  

---

## Dataset Index (24 Total)

### Group 1: Inspection & Violations (7 datasets)
1. **inspection** — Sidewalk inspection records
2. **violations** — Violations found during inspections
3. **dismissals** — Dismissed/appealed violations
4. **correspondences** — Inspector-property communications
5. **reinspection** — Follow-up inspections
6. **tree_damage** — Tree damage incidents
7. **curb_metal_protruding** — Metal curb hazards

### Group 2: Ramp & Accessibility (3 datasets)
8. **ramp_progress** — Ramp construction status
9. **ramp_complaints** — Public complaints about ramps
10. **ramp_locations** — Ramp inventory & locations

### Group 3: Permits & Construction (9 datasets)
11. **street_permits** — Construction permits
12. **street_construction_inspections** — Permit compliance inspections
13. **street_closures_block** — Street closures & traffic impact
14. **capital_blocks** — Capital project blocks
15. **capital_intersections** — Major intersection projects
16. **street_resurfacing_schedule** — Future construction schedule
17. **street_resurfacing_inhouse** — In-house DOT work
18. **weekly_construction** — Weekly construction status
19. **permit_stipulations** — Permit conditions

### Group 4: Context & Overlays (5 datasets)
20. **complaints_311** — Public 311 service requests
21. **mappluto** — Property tax parcel data
22. **sidewalk_planimetric** — Detailed sidewalk geometry
23. **step_streets** — Streets with steps (needing ramps)
24. **pedestrian_demand** — Pedestrian volume analysis

---

## Entity Schemas

### 1. INSPECTION (3,000 rows, 17 columns)
**Primary Keys:** Damage ID, Inspection ID, Material ID, Pickup Sidewalk

| Column | Type | Notes |
|--------|------|-------|
| Inspection ID | text | [PK] Unique inspection identifier |
| Inspection Date | calendar_date | Date of inspection |
| Damage ID | text | [PK] Damage/violation identifier |
| Material ID | text | [PK] Material/surface type |
| Damage Type Code | text | Classification of damage |
| Capital Project Conflict Flag | text | Conflict with permits? |
| Capital Project Conflict(s) | text | Details of conflicts |
| No Violation Found | text | Boolean: clean inspection |
| City Do It | text | DoD will perform repair |
| Owner Will Do It | text | Owner will perform repair |
| Pickup Sidewalk | text | [PK] Sidewalk section identifier |
| Pickup curb | text | Curb section identifier |
| Correspondence | text | Related correspondence |
| Curb311 | text | Related 311 complaint |
| Is 311 Inspection | text | Triggered by 311 complaint? |
| Cancel | text | Inspection cancelled? |
| Other | text | Other notes |

**Relationships:**
- → violations (Damage ID, Material ID)
- → dismissals (through violation records)
- → street_permits (Capital Project Conflict Flag)
- ← complaints_311 (Curb311)

---

### 2. VIOLATIONS (18,618 rows, 27 columns)
**Primary Keys:** Violation#, SR#, Material ID, Damage ID

| Column | Type | Notes |
|--------|------|-------|
| Violation# | number | [PK] Violation identifier |
| SR# | text | [PK] Service request number |
| Violation_Issue_Date | calendar_date | Date violation issued |
| Inspection_Date | calendar_date | Date of inspection |
| Material ID | text | [PK] Material/surface type |
| Damage ID | text | [PK] Damage identifier |
| Site_Street_Address | text | Property address |
| BBL | number | Tax block-lot-borough |
| BIN | number | Building ID |
| Block | number | Tax block |
| Lot | number | Tax lot |
| Borough | text | NYC borough |
| Borocode | number | Borough code |
| Postcode | number | ZIP code |
| Latitude | number | Geographic coordinate |
| Longitude | number | Geographic coordinate |
| Council District | number | Political district |
| Community Board | number | Community board |
| Census Tract (2020) | number | Census area |
| Neighborhood Tabulation Area (NTA) (2020) | text | NTA code |
| CAR_Needed_(Y/N) | text | Corrective Action Record? |
| Permit# | text | Related permit |
| Assigned_Date | calendar_date | Assignment date |
| Request_Date | calendar_date | Request date |
| VDD | calendar_date | Violation due date |
| Attempt# | number | Inspection attempt number |
| Expedited | text | Expedited processing? |

**Relationships:**
- → inspection (Damage ID, Material ID)
- → dismissals (Violation#, SR#)
- → street_permits (Permit#)
- ← complaints_311 (address-based join)

---

### 3. DISMISSALS (12,716 rows, 29 columns)
**Primary Keys:** SR#, Violation#

| Column | Type | Notes |
|--------|------|-------|
| SR# | text | [PK] Service request number |
| Violation# | number | [PK] Violation identifier |
| Request_Date | calendar_date | Initial request date |
| Inspection_Date | calendar_date | Inspection date |
| Assigned_Date | calendar_date | Assignment date |
| Violation_Issue_Date | calendar_date | Violation issue date |
| Date_results_are_mailed | calendar_date | Results sent date |
| Site_Street_Address | text | Property address |
| BBL | number | Tax block-lot-borough |
| BIN | number | Building ID |
| Block | number | Tax block |
| Lot | number | Tax lot |
| Borough | text | NYC borough |
| Borocode | number | Borough code |
| Postcode | number | ZIP code |
| Latitude | number | Geographic coordinate |
| Longitude | number | Geographic coordinate |
| Pass/Fail | text | Inspection result |
| Reason_for_Failure | text | Dismissal reason |
| Homeowner_Contractor | text | Responsible party |
| CAR_Needed_(Y/N) | text | Corrective action required? |
| Permit# | text | Related permit |
| Attempt# | number | Inspection attempt |
| Expedited | text | Expedited processing? |
| Neighborhood Tabulation Area (NTA) (2020) | text | NTA code |
| Council District | number | Political district |
| Community Board | number | Community board |
| Census Tract (2020) | number | Census area |

**Relationships:**
- ← violations (SR#, Violation#)
- → street_permits (Permit#)

---

### 4. STREET_PERMITS (50,633 rows, 39 columns)
**Primary Keys:** Permit# (implied), OBJECTID

| Column | Type | Notes |
|--------|------|-------|
| OBJECTID | number | [PK] Object ID |
| Permit# | text | [PK] Permit identifier |
| PermitType | text | Type of permit |
| FromStreetName | text | Start street |
| OnStreetName | text | Work street |
| ToStreetName | text | End street |
| BoroughName | text | NYC borough |
| IssuedDate | calendar_date | Permit issued |
| ExpirationDate | calendar_date | Permit expires |
| CompletionDate | calendar_date | Work completed |
| PermitStatus | text | Current status |
| PermitTrackingID | text | Tracking number |
| CommunityBoard | number | Community board |
| Council District | number | Council district |
| ConstructionType | text | Type of construction |
| PermitDescription | text | Work description |
| SidewalkSize | number | Sidewalk impacted (sq ft) |
| ParkingSpaces | number | Parking spaces lost |
| StreetLanesClosed | number | Traffic lanes closed |
| Budget | number | Project budget |
| Contractor | text | Contractor name |
| ContractorID | text | Contractor ID |
| Latitude | number | Work location (lat) |
| Longitude | number | Work location (lon) |
| the_geom | geometry | GIS polygon |
| (+ 14 more columns) | | Additional attributes |

**Relationships:**
- ← street_construction_inspections (Permit#)
- ← violations (Permit#)
- ← dismissals (Permit#)
- → capital_blocks (spatial overlap)
- → inspection (conflict detection)

---

### 5. STREET_CONSTRUCTION_INSPECTIONS (12,280 rows, 27 columns)
**Primary Keys:** Inspection ID, Permit#

| Column | Type | Notes |
|--------|------|-------|
| Inspection ID | text | [PK] Inspection identifier |
| Permit# | text | [PK] Related permit |
| InspectionDate | calendar_date | Date of inspection |
| InspectionType | text | Type of inspection |
| Inspector | text | Inspector name |
| Findings | text | Inspection findings |
| Compliance | text | Compliant? |
| ComplianceIssues | text | Issues found |
| CorrectionRequired | text | Correction needed? |
| CorrectionDeadline | calendar_date | Deadline for correction |
| SeverityLevel | text | Severity classification |
| PhotosAttached | text | Photos included? |
| Latitude | number | Inspection location (lat) |
| Longitude | number | Inspection location (lon) |
| (+ 13 more columns) | | Additional details |

**Relationships:**
- → street_permits (Permit#)
- ← inspections (spatial join)

---

### 6. RAMP_PROGRESS (1,356 rows, 13 columns)
**Primary Keys:** Ramp ID (implicit)

| Column | Type | Notes |
|--------|------|-------|
| Ramp ID | text | [PK] Unique ramp identifier |
| Ramp Location | text | Geographic description |
| Address | text | Street address |
| Borough | text | NYC borough |
| Status | text | Construction status |
| PercentComplete | number | Completion percentage (0-100) |
| StartDate | calendar_date | Work start date |
| EstimatedCompletion | calendar_date | Expected completion |
| ActualCompletion | calendar_date | Actual completion |
| Budget | number | Project budget |
| Spend | number | Amount spent |
| Contractor | text | Contractor name |
| Latitude | number | Location (lat) |
| Longitude | number | Location (lon) |

**Relationships:**
- → ramp_locations (Ramp ID)
- ← ramp_complaints (location-based)

---

### 7. RAMP_LOCATIONS (5,813 rows, 29 columns)
**Primary Keys:** Ramp ID

| Column | Type | Notes |
|--------|------|-------|
| Ramp ID | text | [PK] Unique ramp identifier |
| Address | text | Street address |
| Borough | text | NYC borough |
| BBL | number | Tax block-lot |
| Latitude | number | Location (lat) |
| Longitude | number | Location (lon) |
| RampStatus | text | Current status |
| RampType | text | Type of ramp |
| AccessibilityFeatures | text | ADA features |
| SurfaceType | text | Ramp surface |
| Width | number | Ramp width (feet) |
| Length | number | Ramp length (feet) |
| Slope | number | Incline percentage |
| HandrailPresent | text | Handrail installed? |
| EdgeProtection | text | Edge protection? |
| (+ 14 more columns) | | Maintenance, inspection details |

**Relationships:**
- ← ramp_progress (Ramp ID)
- → ramp_complaints (location-based)
- → step_streets (related ramp need)

---

### 8. RAMP_COMPLAINTS (815 rows, 15 columns)
**Primary Keys:** Complaint ID (implicit)

| Column | Type | Notes |
|--------|------|-------|
| Complaint ID | text | [PK] Complaint identifier |
| Date Received | calendar_date | Complaint date |
| Address | text | Property address |
| Borough | text | NYC borough |
| Latitude | number | Location (lat) |
| Longitude | number | Location (lon) |
| Issue | text | Complaint category |
| Description | text | Complaint description |
| Status | text | Resolution status |
| Related Ramp ID | text | Associated ramp |
| Response Date | calendar_date | Response sent |
| Resolution Date | calendar_date | Resolved date |
| (+ 3 more columns) | | Additional notes |

**Relationships:**
- ← ramp_locations (location-based)
- ← ramp_progress (Related Ramp ID)
- ← complaints_311 (can be related)

---

### 9. COMPLAINTS_311 (1,242,856 rows, 48 columns)
**Primary Keys:** Unique Key, Incident Address, Incident Zip

| Column | Type | Notes |
|--------|------|-------|
| Unique Key | text | [PK] Complaint ID |
| Created Date | calendar_date | Complaint date |
| Closed Date | calendar_date | Resolution date |
| Agency | text | Responsible agency |
| Agency Name | text | Agency full name |
| Problem (formerly Complaint Type) | text | Complaint type |
| Problem Detail (formerly Descriptor) | text | Complaint category |
| Incident Address | text | [PK] Work location |
| Incident Zip | text | [PK] ZIP code |
| Borough | text | NYC borough |
| Latitude | number | Location (lat) |
| Longitude | number | Location (lon) |
| Location | point | [GEO] Point geometry |
| Cross Street 1 | text | Cross street |
| Cross Street 2 | text | Cross street |
| Landmark | text | Nearby landmark |
| Status | text | Complaint status |
| Resolution Description | text | How resolved |
| Resolution Action Updated Date | calendar_date | Status update |
| (+ 28 more columns) | | Police precinct, community board, etc. |

**Relationships:**
- ← inspection (Curb311 field)
- ← ramp_complaints (related)
- → mappluto (BBL join possible)
- → complaints_311 (can match by address/borough)

---

### 10. CAPITAL_BLOCKS (4,930 rows, 27 columns)
**Primary Keys:** ProjectID, FMSID, FMSAgencyID

| Column | Type | Notes |
|--------|------|-------|
| ProjectID | number | [PK] Project identifier |
| FMSID | text | [PK] Financial management ID |
| FMSAgencyID | number | [PK] Agency ID |
| ProjTitle | text | Project name |
| ProjectDescription | text | Project description |
| ProjectStatus | text | Current status |
| ProjectType | text | Type of project |
| ProjectTypeCode | text | Project type code |
| BoroughName | text | NYC borough |
| FromStreetName | text | Start street |
| OnStreetName | text | Work street |
| ToStreetName | text | End street |
| DesignStartDate | calendar_date | Design start |
| ConstructionEndDate | calendar_date | Construction end |
| DesignFY | number | Design fiscal year |
| ConstructionFY | number | Construction fiscal year |
| ProjectCost | number | Total cost |
| CurrentFunding | number | Current budget |
| LeadAgency | text | Lead agency |
| Managing Agency | number | Managing agency code |
| ProjectJustification | text | Justification |
| OversallScope | text | Overall scope |
| OtherScope | text | Other scope items |
| SafetyScope | text | Safety improvements |
| the_geom | geometry | [GEO] Work area polygon |

**Relationships:**
- ← street_permits (spatial overlap)
- ← inspection (conflict detection)

---

### 11. CAPITAL_INTERSECTIONS (4,156 rows, 30 columns)
**Primary Keys:** ProjectID, FMSID, FMSAgencyID

Same structure as CAPITAL_BLOCKS, plus:
- Latitude, Longitude (point location)
- Point geometry instead of polygon

---

### 12. MAPPLUTO (91,914 rows, 108 columns)
**Primary Keys:** plutomapid, polidate, residfar

The most detailed property dataset. Key columns:

| Column | Type | Notes |
|--------|------|-------|
| BBL | number | [PK] Tax block-lot-borough |
| address | text | Street address |
| borough | text | NYC borough |
| borocode | number | Borough code |
| bldgclass | text | Building classification |
| bldgarea | number | Building square footage |
| lotarea | number | Lot size |
| numfloors | number | Number of floors |
| yearbuilt | number | Year constructed |
| ownername | text | Property owner |
| ownertype | text | Owner type |
| postcode | number | ZIP code |
| latitude | number | Location (lat) |
| longitude | number | Location (lon) |
| council district | number | Council district |
| community board | number | Community board |
| schooldist | number | School district |
| (+ 92 more columns) | | Zoning, units, areas, dates |

**Relationships:**
- ← violations (BBL join)
- ← dismissals (BBL join)
- ← correspondences (possible address join)
- ← complaints_311 (address/BBL join)

---

### 13. SIDEWALK_PLANIMETRIC (36,371 rows, 0 data columns)
Geometry-only dataset — contains detailed sidewalk centerlines and geometry for GIS analysis.

---

### 14. STEP_STREETS (6,281 rows, 4 columns)
Streets with steps that need ramp solutions.

| Column | Type | Notes |
|--------|------|-------|
| Street Name | text | Street identifier |
| Borough | text | NYC borough |
| the_geom | geometry | [GEO] Step location |
| (metadata) | | Additional GIS attributes |

**Relationships:**
- ← ramp_locations (need for ramps)
- ← ramp_progress (solution progress)

---

### 15. STREET_CLOSURES_BLOCK (50,735 rows, 11 columns)
Traffic impact from construction work.

| Column | Type | Notes |
|--------|------|-------|
| Closure ID | text | [PK] Closure identifier |
| Block | text | City block |
| Borough | text | NYC borough |
| Closure Date | calendar_date | When closed |
| Reopening Date | calendar_date | When reopened |
| Reason | text | Reason for closure |
| Impact Type | text | Type of impact |
| (+ 4 more columns) | | Traffic info |

**Relationships:**
- ← street_permits (Closure ID)
- → traffic analysis

---

### 16-24. OTHER DATASETS

**STREET_RESURFACING_SCHEDULE** (15,216 rows) — Planned pavement work
**STREET_RESURFACING_INHOUSE** (1,965 rows) — DOT-performed resurfacing
**WEEKLY_CONSTRUCTION** (3,978 rows) — Weekly status summaries
**CORRESPONDENCES** (3,786 rows) — Inspector-property mail
**REINSPECTION** (963 rows) — Follow-up inspection records
**TREE_DAMAGE** (828 rows) — Tree hazards
**CURB_METAL_PROTRUDING** (1,395 rows) — Curb hazard inventory
**PEDESTRIAN_DEMAND** (10,533 rows) — Foot traffic analysis
**PERMIT_STIPULATIONS** (4,978 rows) — Permit conditions (minimal schema)

---

## Key Relationships Summary

```
complaints_311 (1.2M rows, most central)
├── ← inspection (curb complaints)
├── ← ramp_complaints (accessibility complaints)
├── ← violations (address matches)
└── → mappluto (address/BBL join)

violations (18,618 rows)
├── ← inspection (issue found)
├── → dismissals (appeal status)
├── → street_permits (permit conflicts)
└── → mappluto (property details)

street_permits (50,633 rows)
├── → street_construction_inspections (compliance)
├── → inspection (conflict detection)
├── → capital_blocks (overlaps)
└── → street_closures_block (traffic impact)

ramp_progress (1,356 rows)
├── → ramp_locations (location detail)
├── → ramp_complaints (community feedback)
└── → step_streets (needs ramps)

mappluto (91,914 rows, property master)
├── ← violations (BBL)
├── ← dismissals (BBL)
├── ← correspondences (address)
└── ← complaints_311 (address/BBL)
```

---

## Column Type Distribution

| Type | Count | Examples |
|------|-------|----------|
| **text** | 312 | Addresses, names, status codes |
| **number** | 175 | IDs, counts, costs, coordinates |
| **calendar_date** | 51 | Issue dates, completion dates |
| **checkbox** | 7 | Boolean flags |
| **multiline** | 3 | Polygon geometry (street geometry) |
| **point** | 3 | Point geometry (locations) |
| **date** | 2 | Simple date fields |
| **multipoint** | 1 | Multiple point coordinates |

---

## Primary Key Strategy

### Composite Keys (Most Common)
- Violations: (SR#, Violation#, Material ID, Damage ID)
- Dismissals: (SR#, Violation#)
- Street Permits: (Permit#, OBJECTID)
- Capital Projects: (ProjectID, FMSID, FMSAgencyID)

### Natural Keys
- Inspection: Inspection ID
- Ramp Progress: Ramp ID
- MAPPLUTO: BBL (block-lot-borough)
- 311 Complaints: Unique Key

### Surrogate Keys
- MAPPLUTO: plutomapid (numeric)

---

## Join Keys (Cross-Dataset)

| From | To | Join Key(s) |
|------|-----|-------------|
| violations ↔ inspection | (Damage ID, Material ID) |
| violations ↔ dismissals | (SR#, Violation#) |
| violations ↔ mappluto | (BBL) |
| violations ↔ street_permits | (Permit#) |
| violations ↔ correspondences | (address-based) |
| street_permits ↔ street_construction_inspections | (Permit#) |
| street_permits ↔ capital_blocks | (spatial overlap) |
| ramp_progress ↔ ramp_locations | (Ramp ID) |
| ramp_locations ↔ ramp_complaints | (location-based) |
| ramp_locations ↔ step_streets | (geographic proximity) |
| complaints_311 ↔ inspection | (Curb311 field) |
| all ↔ mappluto | (address, BBL, or coordinates) |

---

## Cardinality

| Relationship | Cardinality | Notes |
|---|---|---|
| inspection → violations | 1:M | One inspection finds many violations |
| violations → dismissals | 1:M | One violation may be appealed multiple times |
| violations → street_permits | M:1 | Many violations near one permit |
| street_permits → street_construction_inspections | 1:M | One permit inspected multiple times |
| ramp_progress → ramp_locations | 1:1 | One ramp project per location |
| ramp_locations → ramp_complaints | 1:M | One ramp location gets many complaints |
| complaints_311 → violations | M:M | 311 complaints can match many violations |

---

## Data Quality Observations

- **MAPPLUTO**: Most detailed (108 columns), can serve as master property reference
- **Complaints_311**: Highest volume (1.2M rows), central to citizen feedback
- **Street_permits**: Highest structural relevance (39 columns), core to construction tracking
- **Inspection**: Lowest volume (3K rows), but highest cardinality to violations (6:1)
- **Geographic Data**: Available across all datasets (lat/lon, geometry, BBL)
- **Temporal Data**: 51 calendar_date columns enable time-series analysis
- **Hierarchical Geography**: Borough → Community Board → Council District → Census Tract

---

## Production Schema Recommendations

```sql
-- Dimension tables
CREATE TABLE dim_property (
  bbl PRIMARY KEY,
  address, borough, borocode, latitude, longitude,
  -- from MAPPLUTO
);

CREATE TABLE dim_location (
  location_id PRIMARY KEY,
  address, borough, latitude, longitude,
  -- from multiple sources
);

CREATE TABLE dim_time (
  date_id PRIMARY KEY,
  date, day_of_week, month, fiscal_year
);

-- Fact tables
CREATE TABLE fact_inspections (
  inspection_id PRIMARY KEY,
  inspection_date_id FK -> dim_time,
  property_id FK -> dim_property,
  inspection_type, findings, pass_fail
);

CREATE TABLE fact_violations (
  violation_id PRIMARY KEY,
  violation_date_id FK -> dim_time,
  property_id FK -> dim_property,
  inspection_id FK -> fact_inspections,
  violation_type, severity
);

CREATE TABLE fact_permits (
  permit_id PRIMARY KEY,
  issue_date_id FK -> dim_time,
  location_id FK -> dim_location,
  permit_type, budget, contractor
);

CREATE TABLE fact_ramp_progress (
  ramp_id PRIMARY KEY,
  location_id FK -> dim_location,
  progress_date_id FK -> dim_time,
  percent_complete, spend
);
```

---

## Summary

**Schema Complexity:** High (554 columns, 24 entities)  
**Relationship Density:** Medium (414 inferred relationships)  
**Primary Join Key:** BBL (block-lot-borough) for property reference  
**Central Hub:** MAPPLUTO (property master) + complaints_311 (citizen feedback)  
**Time Series:** 51 date columns enable trend analysis  
**Geographic:** Full coordinate/geometry support for spatial analysis  

All data is **queryable from Socrata API** in real-time. Use `complete_erd.json` for programmatic access to full schema details.
