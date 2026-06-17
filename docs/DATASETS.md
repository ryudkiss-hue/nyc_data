# 🏛️ NYC DOT Socrata Toolkit Dataset Directory

**Last Generated:** 2026-06-07 23:55:01 UTC

**DEPRECATED:** This document is superseded by `SOCRATA_DATASETS_CONSOLIDATED.md` which documents all 37 datasets with complete mappings, alternatives, and KPI cross-references.

For current dataset registry and technical reference, see: [`SOCRATA_DATASETS_CONSOLIDATED.md`](SOCRATA_DATASETS_CONSOLIDATED.md)

| # | Official Title | 4x4 ID | Category | Link |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **SMD Inspection** | `dntt-gqwq` | General | [Jump to Schema](#inspection) |
| 2 | **SMD Violations** | `6kbp-uz6m` | General | [Jump to Schema](#violations) |
| 3 | **SMD Built** | `ugc8-s3f6` | General | [Jump to Schema](#built) |
| 4 | **SMD Lot Info** | `i642-2fxq` | General | [Jump to Schema](#lot_info) |
| 5 | **SMD ReInspection** | `gx72-kirf` | General | [Jump to Schema](#reinspection) |
| 6 | **All Tree Damage** | `j6v2-6uxq` | General | [Jump to Schema](#tree_damage) |
| 7 | **Sidewalk Dismissal Inspection Tracking** | `p4u2-3jgx` | General | [Jump to Schema](#dismissals) |
| 8 | **Sidewalk Correspondences** | `bheb-sjfi` | General | [Jump to Schema](#correspondences) |
| 9 | **Pedestrian Ramp Locations** | `ufzp-rrqu` | General | [Jump to Schema](#ramp_locations) |
| 10 | **Ramp Complaints** | `jagj-gttd` | General | [Jump to Schema](#ramp_complaints) |
| 11 | **Ramp Program Progress** | `e7gc-ub6z` | General | [Jump to Schema](#ramp_progress) |
| 12 | **Street Construction Permits** | `tqtj-sjs8` | General | [Jump to Schema](#street_permits) |
| 13 | **Weekly Construction Schedule** | `r528-jcks` | General | [Jump to Schema](#weekly_construction) |
| 14 | **Capital Reconstruction Blocks** | `jvk9-k4re` | General | [Jump to Schema](#capital_blocks) |
| 15 | **Capital Reconstruction Projects - Intersection** | `97nd-ff3i` | General | [Jump to Schema](#capital_intersections) |
| 16 | **Street Construction Inspections (HIQA)** | `ydkf-mpxb` | General | [Jump to Schema](#street_construction_inspections) |
| 17 | **Street Closures by Block** | `i6b5-j7bu` | General | [Jump to Schema](#street_closures_block) |
| 18 | **Street Construction Permit Stipulations** | `gsgx-6efw` | General | [Jump to Schema](#permit_stipulations) |
| 19 | **Curb Metal Protruding Data** | `i2y3-sx2e` | General | [Jump to Schema](#curb_metal_protruding) |
| 20 | **Step Streets Locations** | `u9au-h79y` | General | [Jump to Schema](#step_streets) |
| 21 | **Street Resurfacing Schedule** | `xnfm-u3k5` | General | [Jump to Schema](#street_resurfacing_schedule) |
| 22 | **DOT In-house Street Resurfacing Projects** | `ffaf-8mrv` | General | [Jump to Schema](#street_resurfacing_inhouse) |
| 23 | **Planimetric Sidewalks** | `vfx9-tbb6` | General | [Jump to Schema](#sidewalk_planimetric) |
| 24 | **Pedestrian Demand** | `fwpa-qxaf` | General | [Jump to Schema](#pedestrian_demand) |
| 25 | **MapPLUTO** | `64uk-42ks` | General | [Jump to Schema](#mappluto) |
| 26 | **311 Sidewalk/Curb** | `erm2-nwe9` | General | [Jump to Schema](#complaints_311) |

## 📂 Detailed Schemas

### Sidewalk Management Database - Inspection (`inspection`)

> Sidewalk Management System is used to track and organize inspections, violations and the status of New York City sidewalks Identifies locations where DOT inspectors performed sidewalk inspections for defects.
For more information please visit NYC DOT website: www.nyc.gov/sidewalks

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Inspection ID** | `inspectionid` | `text` | Unique five digit numerical ID used to track inspection records. |
| **No Violation Found** | `noviolationfound` | `text` | The inspection did not identify any sidewalk defects. |
| **City Do It** | `citydoit` | `text` | Property owner requests that the city performs the sidewalk repairs. |
| **Owner Will Do It** | `ownerwilldoit` | `text` | Property owner will perform the sidewalk repairs. |
| **Capital Project Conflict Flag** | `capconflictflag` | `text` | Identifies if there is a capital project with planned work at the taxlot |
| **Capital Project Conflict(s)** | `capitalconflicts` | `text` | Identified there is a capital reconstruction project with sidewalk repairs at the location. |
| **Cancel** | `cancel` | `text` | An outstanding violation cancelled - no sidewalk defects identified. |
| **Inspection Date** | `inspectiondate` | `calendar_date` | Inspection Date |
| **Is 311 Inspection** | `is_311_inspection` | `text` | To determine if the sidewalk inspection occurred at a taxlot where a 311 complaint for defective sidewalk was received. |
| **Material ID** | `materialid` | `text` | The type of material used for sidewalk. |
| **Pickup Sidewalk** | `pickupsidewalk` | `text` | To determine if the sidewalk inspection occurred at a taxlot where a 311 complaint for defective sidewalk was received on the block. |
| **Curb311** | `curb311` | `text` | To determine if the sidewalk inspection occurred at a taxlot where a 311 complaint for defective curb was received. |
| **Pickup curb** | `pickupcurb` | `text` | To determine if the sidewalk inspection occurred at a taxlot where a 311 complaint for defective curb was received on the block. |
| **Other** | `other` | `text` | To determine if the sidewalk inspection occurred due to a reason other than the receipt of a 311 complaint or correspondence. |
| **Correspondence** | `correspondence` | `text` | To determine if the sidewalk inspection occurred at a taxlot where correspondence was received. |
| **Damage ID** | `damageid` | `text` | A numerical code identifying the root of the sidewalk damage. |
| **Damage Type Code** | `damagetypecode` | `text` | Identifies if all or any of the sidewalk defects are caused by a City tree |

---
### Sidewalk Management Database - Violations (`violations`)

> Sidewalk Management System is used to track and organize inspections, violations and the status of New York City sidewalks. Identifies a Notice of Violation has been issued for a sidewalk defect.
For more information please visit NYC DOT website: www.nyc.gov/sidewalks

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **BROKEN** | `broken` | `text` | The sidewalk is broken at this location. |
| **CB** | `cb` | `number` | The New York City Community Board number. |
| **CERTI_DATE** | `certi_date` | `calendar_date` | The date the property owner received the Notice of Violation in the mail via certified return receipt. |
| **CONTRACT** | `contract` | `text` | This field identifies the Prior Notice contract number for performed sidewalk repairs. |
| **EntryDate** | `entrydate` | `calendar_date` | The date of the record entry generated by the system. |
| **FLAG** | `flag` | `text` | To determine if this is a freestanding flag. |
| **FRSTNAME** | `frstname` | `text` | The cross street where sidewalk violation was found. |
| **GRACE_PD** | `grace_pd` | `number` | The number of days from property owner receipt of violation until the City can perform sidewalk repairs. |
| **HARDWARE** | `hardware` | `text` | To determine if there are any defective hardware on a sidewalk. |
| **HOUSE_NUM** | `house_num` | `text` | The house number of the address where the violation was issued. |
| **INTEGRITY** | `integrity` | `text` | To determine if a sidewalk flag has a structural integrity issue. |
| **ONFRTOCODE** | `onfrtocode` | `text` | A combination of unique identifiers assigned to the On, From, and To streets. |
| **ONSTNAME** | `onstname` | `text` | The street name where the violation was found. |
| **OTHER_DEF** | `other_def` | `text` | To determine whether other sidewalk defects are present at the property. |
| **PATCHWORK** | `patchwork` | `text` | To determine if the defective sidewalk was patched. |
| **POST_DATE** | `post_date` | `calendar_date` | The date the Notice of Violation was posted to the taxlot where defective sidewalk was found. |
| **SLOPE** | `slope` | `text` | To determine if improper slope or pitch of sidewalk exist. |
| **SQ_FEET** | `sq_feet` | `number` | The total defective in sq. ft. of sidewalk. |
| **SW_MISSING** | `sw_missing` | `text` | Determination if there is missing sidewalk. |
| **SWV_Number** | `swv_number` | `number` | The violation number issued to the property owner that is in ascending order for each borough. |
| **TOSTNAME** | `tostname` | `text` | The closest cross street where sidewalk violation was found. |
| **TRIP_HAZ** | `trip_haz` | `text` | To determine if there is a trip hazard/deflection/hole at sidewalk. |
| **UNDERMINED** | `undermined` | `text` | To determine if any undermined condition or visible void exist at sidewalk. |
| **VDismissDate** | `vdismissdate` | `calendar_date` | The date of the violation dismissal. |
| **ViolationID** | `violationid` | `number` | A sequential count for the sidewalk violations. |
| **VIssueDate** | `vissuedate` | `calendar_date` | The date the violation was issued. |
| **BBLID** | `bblid` | `number` | The unique numerical identifier for the borough, block and lot. |

---
### Sidewalk Management Database - Built (`built`)

> Sidewalk Management System is used to track and organize inspections, violations and the status of New York City sidewalks.
Tracks the repairs that were performed via NYC DOT's Prior Notice Sidewalk Repair contracts and on properties that were repaired privately or by other organizations.
For more information please visit NYC DOT website: www.nyc.gov/sidewalks

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **BBLID** | `bblid` | `number` | The unique numerical identifier for the borough, block and lot. |
| **DOT_CONTSTRUCT_DATE** | `dot_contstruct_date` | `calendar_date` | The last time the taxlot was repaired via a Prior Notice Sidewalk Repair contract. |
| **DBO** | `dbo` | `text` | Sidewalk repair was performed by a contractor/private entity other than a Prior Notice Sidewalk Repair contract. |
| **DBO_Date** | `dbo_date` | `calendar_date` | The date the taxlot was found to DBO. |
| **CONTRACT** | `contract` | `text` | This field identifies the Prior Notice contract number for performed sidewalk repairs. |
| **ATDByStreetTree** | `atdbystreettree` | `text` | Identifies that all sidewalk defects repaired that were caused by a City tree |
| **PortionofDefectByStreetTree** | `portionofdefectbystreettree` | `text` | Identifies that a portion of sidewalk defects repaired were caused by a City tree. |
| **NoneofDefectByStreetTree** | `noneofdefectbystreettree` | `text` | Identifies that a City tree did not cause sidewalk defects at the lot that was repaired. |
| **TotalSQFTSidewalkRepaired** | `totalsqftsidewalkrepaired` | `number` | Total Sq. Ft. of sidewalk repaired at taxlot |
| **TotalLFCurbRepaired** | `totallfcurbrepaired` | `number` | Total linear foot of curb repaired at taxlot |
| **TotalCostToConstruct** | `totalcosttoconstruct` | `number` | Total cost to the City to repair the taxlot |
| **TotalSQFTSDWRepairedStreetTreeOnly** | `totalsqftsdwrepairedstre` | `number` | Total Sq. Ft. of sidewalk repaired where defects were caused by trees |
| **TotalLFCurbRepairedStreetTreeOnly** | `totallfcurbrepairedstree` | `number` | Total linear foot of sidewalk repaired where defects were caused by trees |
| **TotalCostofRepairStreetTreeOnly** | `totalcostofrepairstreett` | `number` | Total cost to the City to repair defects caused by trees |

---
### Sidewalk Management Database - Lot Info (`lot_info`)

> Sidewalk Management System is used to track and organize inspections, violations and the status of New York City sidewalks. This identifies sidewalk locations by borough, block and lot numbers.
For more information please visit NYC DOT website: www.nyc.gov/sidewalks

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Borough, Block and Lot (BBL) ID** | `bblid` | `number` | The borough, block and lot number assigned to the street block for identification for the Lotinfo table. |
| **Block** | `block` | `number` | The unique tax block number. |
| **Borough** | `boro` | `number` | The one digit New York City borough code for the block and lot. |
| **Lot** | `lot` | `number` | The unique lot number. |
| **ZIP Code** | `zipcode` | `text` | The postal ZIP code. |

---
### Sidewalk Management Database - ReInspection (`reinspection`)

> Sidewalk Management System is used to track and organize inspections, violations and the status of New York City sidewalks.
A reinspection can be requested by the property owner if they do not agree with the initial inspection. A different DOT inspector performs a second sidewalk inspection. 
For more information please visit NYC DOT website: www.nyc.gov/sidewalks

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **ReinspectionID** | `reinspectionid` | `number` | Unique numerical ID used to track inspection records. |
| **RequestReinspection** | `requestreinspection` | `text` | If the property owner requested a re-inspection. |
| **RequestReinspectionDate** | `requestreinspectiondate` | `calendar_date` | The date the re-inspection was requested by the property owner. |
| **ReinspectSqFT** | `reinspectsqft` | `number` | The square footage of the defective sidewalk identified from the re-inspection. |
| **ActualReinspectDate** | `actualreinspectdate` | `calendar_date` | The actual date the re-inspection was performed on the property. |
| **ResponseDate** | `responsedate` | `calendar_date` | The date the re-inspection results were mailed to the property owner. |
| **DamageID** | `damageid` | `text` | A numerical code identifying the root of the sidewalk damage. |
| **DamageTypeCode** | `damagetypecode` | `text` | Identifies if all or any of the sidewalk defects are caused by a City tree |

---
### Sidewalk Management Database - All Tree Damage (ATD) (`tree_damage`)

> Sidewalk Management System is used to track and organize inspections, violations and the status of New York City sidewalks.
Tracks properties where all sidewalk defects on the tax lot are due to trees/tree roots (All Tree Defects - ATD)
For more information please visit NYC DOT website: www.nyc.gov/sidewalks

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **ATDID** | `atdid` | `number` | A system generated numerical value assigned to each ATD entry. A sequential count on the number of entries in the database. |
| **ATD_NUMBER** | `atd_number` | `text` | A combination of the ATD Suffix (A system generated numerical value assigned to each ATD by borough) and borough code. |
| **BBLID** | `bblid` | `number` | The unique numerical identifier for the borough, block and lot. |
| **ViolationId** | `violationid` | `number` | A sequential count for the sidewalk violations. |
| **InspectionId** | `inspectionid` | `number` | Unique five digit numerical ID used to track inspection records. |
| **ReInspectionId** | `reinspectionid` | `number` | Six digit identifier to uniquely identify the inspector for the reinspection. |
| **Inspect_date** | `inspect_date` | `calendar_date` | The date the sidewalk inspection was performed. |
| **ATDIssueDate** | `atdissuedate` | `calendar_date` | The date an ATD was determined based on an inspection. |
| **CB** | `cb` | `number` | The New York City Community Board number. |
| **HOUSE_NUM** | `house_num` | `text` | The house number of the address where the violation was issued. |
| **ONSTNAME** | `onstname` | `text` | The street name where the ATD was found. |
| **ATDDismissed** | `atddismissed` | `text` | The all tree damage on the sidewalk was resolved. |
| **ATDDismissedOn** | `atddismissedon` | `calendar_date` | The date the violation was resolved. |

---
### Sidewalk Dismissal Inspection Tracking (`dismissals`)

> Tracks dismissal inspection requests and results from property owners who repairs their sidewalk privately.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **SR#** | `sr` | `text` |  |
| **Request_Date** | `request_date` | `calendar_date` |  |
| **Site_Street_Address** | `site_street_address` | `text` |  |
| **Borocode** | `borocode` | `number` |  |
| **Community Board** | `community_board` | `number` |  |
| **Block** | `block` | `number` |  |
| **Lot** | `lot` | `number` |  |
| **Violation#** | `violation` | `number` |  |
| **Permit#** | `permit` | `text` |  |
| **Homeowner_Contractor** | `homeowner_contractor` | `text` |  |
| **Attempt#** | `attempt` | `number` |  |
| **Violation_Issue_Date** | `violation_issue_date` | `calendar_date` |  |
| **Assigned_Date** | `assigned_date` | `calendar_date` |  |
| **Inspection_Date** | `inspection_date` | `calendar_date` |  |
| **Pass/Fail** | `pass_fail` | `text` |  |
| **Reason_for_Failure** | `reason_for_failure` | `text` |  |
| **CAR_Needed_(Y/N)** | `car_needed_y_n` | `text` |  |
| **Date_results_are_mailed** | `date_results_are_mailed` | `calendar_date` |  |
| **Expedited** | `expedited` | `text` |  |
| **VDD** | `vdd` | `calendar_date` |  |
| **Borough** | `borough` | `text` |  |
| **Postcode** | `postcode` | `number` |  |
| **Latitude** | `latitude` | `number` |  |
| **Longitude** | `longitude` | `number` |  |
| **Council District** | `council_district` | `number` |  |
| **BIN** | `bin` | `number` |  |
| **BBL** | `bbl` | `number` |  |
| **Census Tract (2020)** | `census_tract` | `number` |  |
| **Neighborhood Tabulation Area (NTA) (2020)** | `nta` | `text` |  |

---
### Sidewalk Correspondences (`correspondences`)

> Tracks all written correspondences to the Sidewalk Program.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Date Received** | `date_received` | `calendar_date` |  |
| **Borough** | `borough` | `text` |  |
| **Block** | `block` | `text` |  |
| **Lot** | `lot` | `text` |  |
| **Class** | `class` | `text` |  |
| **Community Board** | `community_board` | `text` |  |
| **Violation** | `violation` | `text` |  |
| **OSM** | `osm` | `text` |  |
| **CCU** | `ccu` | `text` |  |
| **SIM** | `sim` | `text` |  |
| **BC** | `bc` | `text` |  |
| **Other Log** | `other_log` | `text` |  |
| **Issue** | `issue` | `text` |  |
| **Address** | `address` | `text` |  |
| **Cross Streets** | `cross_streets` | `text` |  |
| **Referred/Routed To** | `referred_routed_to` | `text` |  |
| **Resoultion** | `resoultion` | `text` |  |
| **Date Closed** | `date_closed` | `calendar_date` |  |
| **Results of Inspection** | `results_of_inspection` | `text` |  |
| **Postcode** | `postcode` | `number` |  |
| **Latitude** | `latitude` | `number` |  |
| **Longitude** | `longitude` | `number` |  |
| **Council District** | `council_district` | `number` |  |
| **Census Tract** | `census_tract` | `number` |  |
| **BIN** | `bin` | `number` |  |
| **BBL** | `bbl` | `number` |  |
| **NTA** | `nta` | `text` |  |

---
### Pedestrian Ramp Locations (`ramp_locations`)

> Pedestrian ramps provide access on and off streets and sidewalks and are an essential tool for all pedestrians. This data is a comprehensive list of all pedestrian ramps throughout New York City.

Please note that measurements shown are not indicative of whether a particular ramp is compliant with design and construction standards pursuant to the Americans with Disabilities Act (ADA). DOT applies additional parameters in its compliance assessment of the data collected by Cyclomedia, including specific site constraints located at or near a pedestrian ramp, otherwise referred to as a technical infeasibility in the ADA. The constraints that constitute a technical infeasibility can include but are not limited to elements such as underground vaults, transit facilities, steep terrain conditions, and limited public right-of-way, which are not readily apparent through the data and imagery collected. As such, compliance determinations at some locations require further analysis and site inspection. These locations are noted as “Pending Technical Review” in the published assessment available at: https://www.nycpedramps.info/survey.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **the_geom** | `the_geom` | `point` | Each ramp is represented by a point in the dataset |
| **CornerID** | `cornerid` | `number` | Unique identifier assigned to the corner by the surveyor for the street corner |
| **RampID** | `rampid` | `number` | Unique identifier assigned to the ramp by the surveyor for the ramp |
| **Ramp_OnStreet** | `ramp_onstr` | `text` | Street(s) for where the ramp is facing/serving |
| **GeoCyclora** | `geocyclora` | `calendar_date` | The date the data was captured by the surveyor |
| **Borough** | `borough` | `number` | Borough of the ramp location |
| **StName1** | `stname1` | `text` | Street name one at intersection |
| **StName2** | `stname2` | `text` | Street name two at intersection |
| **CURB_REVEAL** | `curb_reveal` | `number` | Maximum height of lip at dropped curb |
| **RAMP_RUNNING_SLOPE_TOTAL** | `ramp_running_slope_total` | `number` | Longitudinal slope of ramp's entire extent |
| **DWS_CONDITIONS** | `dws_conditions` | `text` | Detectable Warning Surface condition |
| **GUTTER_SLOPE** | `gutter_slope` | `number` | Slope measured along the roadway gutter line |
| **LND_WIDTH** | `lnd_width` | `number` | Width of top landing (perpendicular to ramp) |
| **LND_LENGTH** | `lnd_length` | `number` | Length of top landing (in direction of ramp) |
| **LND_CROSS_SLOPE** | `lnd_cross_slope` | `number` | Slope of top landing (perpendicular to direction of ramp) |
| **COUNTER_SLOPE** | `counter_slope` | `number` | Slope of adjacent street at ramp interface (roadway grade) |
| **RAMP_WIDTH** | `ramp_width` | `number` | Width of ramp |
| **RAMP_RIGHT_FLARE** | `ramp_right_flare` | `number` | Max slope of right flare (from the frontal view of ramp) |
| **RAMP_LEFT_FLARE** | `ramp_left_flare` | `number` | Max slope of left flare (from the frontal view of ramp) |
| **RAMP_LENGTH** | `ramp_length` | `number` | Length of ramp |
| **RAMP_CROSS_SLOPE** | `ramp_cross_slope` | `number` | Cross slope of ramp |
| **PONDING** | `ponding` | `text` | Is there pooling of water at the base of ramp? |
| **OBSTACLES_RAMP** | `obstacles_ramp` | `text` | List of infrastructure/permanent street furniture within pedestrian access route: ramp area. |
| **OBSTACLES_LANDING** | `obstacles_landing` | `text` | List of infrastructure/permanent street furniture within pedestrian access route: area behind ramp(s). |
| **Zip Codes** | `:@computed_region_efsh_h5xi` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Zip Codes' (efsh-h5xi) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **Community Districts** | `:@computed_region_f5dn_yrer` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Community Districts' (f5dn-yrer) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **Borough Boundaries** | `:@computed_region_yeji_bk3q` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Borough Boundaries' (yeji-bk3q) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **City Council Districts** | `:@computed_region_92fq_4b7q` | `number` | This column was automatically created in order to record in what polygon from the dataset 'City Council Districts' (92fq-4b7q) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **Police Precincts** | `:@computed_region_sbqj_enih` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Police Precincts' (sbqj-enih) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |

---
### Pedestrian Ramp Complaints (`ramp_complaints`)

> This dataset tracks corner and pedestrian ramp complaints and their temporary repair status. Temporary repairs may include but are not limited to the use of asphalt on corners and pedestrian ramps.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **CMT_Corner_ID** | `cmt_corner_id` | `number` | Unique numeric identifier assigned to a corner point. A corner may contain more than one ramp. |
| **Street_Name1** | `street_name1` | `text` | The first street name where the corner is located. |
| **Street_Name2** | `street_name2` | `text` | The second street name where the corner is located. |
| **Borough** | `borough` | `text` | Borough where the corner is located. |
| **Community_District** | `community_district` | `number` | The three digit community district number to identify the community district the corner is located in. |
| **Block** | `block` | `number` | Tax Block identification number adjacent to the corner. |
| **Lot** | `lot` | `number` | Tax Lot identification number adjacent to the corner. |
| **Complaint_ID** | `complaint_id` | `text` | Unique identification number for each complaint record. |
| **Complaint_Date** | `complaint_date` | `calendar_date` | The date the complaint was made. |
| **Temp_Repair_Feasible** | `temp_repair_feasible` | `text` | If a temporary repair is feasible. |
| **Temp_Repair_Date** | `temp_repair_date` | `calendar_date` | The date the temporary repair was completed. |
| **Temp_Repair_Type** | `temp_repair_type` | `text` | What type of temporary repair was done on the corner or pedestrian ramp. |
| **Second_Temp_Repair_Needed** | `second_temp_repair_needed` | `text` | If a second temporary repair is needed for a corner or pedestrian ramp. |
| **Date_Second_Temp_Repair** | `date_second_temp_repair` | `calendar_date` | The date of the second temporary repair. |
| **BulkComplaint** | `bulkcomplaint` | `text` | If the complaint involves multiple corners. |

---
### Pedestrian Ramp - Program Progress (`ramp_progress`)

> New York City Department of Transportation (NYC DOT) has developed a program dedicated to upgrading and installing pedestrian ramps and is committed to making our pedestrian space safe and accessible for all road users.

The term corner refers to intersection corners (space on the sidewalk at the intersection of two streets), midblocks (a crossing that is not at an intersection, usually in between two streets), tops of T-shaped intersections, medians or islands (a small section of raised concrete in the street). A corner can have one or more ramps.
Dataset used to generate the Program Progress Map on the Pedestrian Ramp Program Website: https://www.nycpedramps.info/program-progress

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **the_geom** | `the_geom` | `point` | Geometry column used for mapping |
| **OBJECTID** | `objectid` | `number` | A system-managed value that uniquely identifies a record or feature |
| **CornerID** | `cornerid` | `number` | Unique numeric identifier assigned to a corner point. A corner may contain more than one ramp. |
| **Street_Name1** | `street_nam` | `text` | The first street name where the corner is located. |
| **Street_Name2** | `street_n_1` | `text` | The second street name where the corner is located. |
| **Borough** | `borough` | `text` | Borough where the corner is located. |
| **Construction_Type** | `constructi` | `text` | If the construction type is a pedestrian ramp upgrade or new installation. |
| **Construction_End_Date** | `construc_1` | `text` | The date the corner construction was completed. |
| **Construction_Status_Value** | `construc_2` | `text` | The status for the corner. |
| **Community Districts** | `:@computed_region_f5dn_yrer` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Community Districts' (f5dn-yrer) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **Borough Boundaries** | `:@computed_region_yeji_bk3q` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Borough Boundaries' (yeji-bk3q) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **Police Precincts** | `:@computed_region_sbqj_enih` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Police Precincts' (sbqj-enih) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **City Council Districts** | `:@computed_region_92fq_4b7q` | `number` | This column was automatically created in order to record in what polygon from the dataset 'City Council Districts' (92fq-4b7q) the point in column 'the_geom' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |

---
### Street Construction Permits (2022 - Present) (`street_permits`)

> DOT issues over 150 different types of sidewalk and roadway construction permits to utilities, contractors, government agencies and homeowners. Permits cover activities such as street openings, sidewalk construction and installing canopies over sidewalks.
The core permit data, including permittee, type of permit, date issued, location.

<b>Street Construction Permits 2013-2021:</b> https://data.cityofnewyork.us/Transportation/Street-Construction-Permits-2013-2021-/c9sj-fmsg

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **PermitNumber** | `permitnumber` | `text` |  |
| **ApplicationTrackingID** | `applicationtrackingid` | `text` |  |
| **SequenceNumber** | `sequencenumber` | `text` |  |
| **ApplicationTypeShortDesc** | `applicationtypeshortdesc` | `text` |  |
| **PermitStatusID** | `permitstatusid` | `text` |  |
| **PermitStatusShortDesc** | `permitstatusshortdesc` | `text` |  |
| **PermitSeriesID** | `permitseriesid` | `text` |  |
| **PermitSeriesShortDesc** | `permitseriesshortdesc` | `text` |  |
| **PermitTypeID** | `permittypeid` | `text` |  |
| **PermitTypeDesc** | `permittypedesc` | `text` |  |
| **PermitNumberOfZones** | `permitnumberofzones` | `number` |  |
| **PermitLinearFeet** | `permitlinearfeet` | `number` |  |
| **PermitTotalSqFeet** | `permittotalsqfeet` | `number` |  |
| **PermitEstimatedNumberOfCuts** | `permitestimatednumberofcuts` | `number` |  |
| **EquipmentTypeDesc** | `equipmenttypedesc` | `text` |  |
| **NumberOfContainers** | `numberofcontainers` | `number` |  |
| **NumberOfMiniContainers** | `numberofminicontainers` | `number` |  |
| **SpecificStipulations** | `specificstipulations` | `text` |  |
| **PreviousPermitNumber** | `previouspermitnumber` | `text` |  |
| **NextPermitNumber** | `nextpermitnumber` | `text` |  |
| **EmergencyIssueDate** | `emergencyissuedate` | `calendar_date` |  |
| **PermitIssueDate** | `permitissuedate` | `calendar_date` |  |
| **IssuedWorkStartDate** | `issuedworkstartdate` | `calendar_date` |  |
| **IssuedWorkEndDate** | `issuedworkenddate` | `calendar_date` |  |
| **BoroughName** | `boroughname` | `text` |  |
| **PermitHouseNumber** | `permithousenumber` | `text` |  |
| **OnStreetName** | `onstreetname` | `text` |  |
| **FromStreetName** | `fromstreetname` | `text` |  |
| **ToStreetName** | `tostreetname` | `text` |  |
| **PermitteeName** | `permitteename` | `text` |  |
| **PermitPurposeComments** | `permitpurposecomments` | `text` |  |
| **PermitLocationComments** | `permitlocationcomments` | `text` |  |
| **PavementShortDesc** | `pavementshortdesc` | `text` |  |
| **SideWalkShortDesc** | `sidewalkshortdesc` | `text` |  |
| **CreatedOn** | `createdon` | `calendar_date` |  |
| **ModifiedOn** | `modifiedon` | `calendar_date` |  |
| **OFTCode** | `oftcode` | `text` |  |
| **WKT** | `wkt` | `text` |  |
| **LocationGeometry** | `locationgeometry` | `text` |  |

---
### Sidewalk Weekly Construction Schedule (`weekly_construction`)

> Sidewalk schedule to install, maintain and repair sidewalks, curbs and pedestrian ramps.
https://www.nyc.gov/html/dot/html/motorist/resurfintro.shtml

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Borough** | `borough` | `text` | Borough |
| **Contract No** | `cb` | `text` | The City contract for the work |
| **CB** | `contract_no` | `text` | Community District |
| **Location** | `location` | `text` | Description of the work location |

---
### Street and Highway Capital Reconstruction Projects - Block (`capital_blocks`)

> This data is a spatial representation of street construction projects. Street and Highway capital projects are major street reconstruction projects, ranging from general street resurfacing projects to full reconstruction of the roadbed, sidewalks, sewer and water pipes and other utilities. Capital projects are essential to keep the City's infrastructure in a state of good repair.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **the_geom** | `the_geom` | `multiline` |  |
| **ProjectID** | `projectid` | `number` | A unique number assigned to identify a capital project. |
| **ProjTitle** | `projtitle` | `text` | The full title of the capital project. |
| **FMSID** | `fmsid` | `text` | The unique budget code assigned to the capital project in the citywide Financial Management System (FMS). |
| **FMSAgencyID** | `fmsagencyi` | `number` | The three number citywide Financial Management System (FMS) agency code. |
| **LeadAgency** | `leadagency` | `text` | The primary agency leading the capital project in three letter acronym. |
| **Managing Agency** | `managingag` | `number` | The agency that manages the project in three letter acronym. |
| **ProjectDescription** | `projectdes` | `text` | The description of the capital project. |
| **ProjectTypeCode** | `projecttyp` | `text` | The three letter code that identifies the type of work being performed. |
| **ProjectType** | `projectt_1` | `text` | The full description on the type of work that is being performed for the capital project. |
| **ProjectStatus** | `projectsta` | `text` | The current status of the capital project. |
| **ConstructionFY** | `constructi` | `number` | The fiscal year of the capital project. |
| **DesignStartDate** | `designstar` | `calendar_date` | The date the design phase of the capital project starts. |
| **ConstructionEndDate** | `construc_2` | `calendar_date` | The date the project will be completed. |
| **CurrentFunding** | `currentfun` | `number` | Estimated current funding allocated for this capital project. |
| **ProjectCost** | `projectcos` | `number` | Estimated cost of the capital project. |
| **OversallScope** | `overallsco` | `text` | Overall brief description of the capital projects. |
| **OtherScope** | `otherscope` | `text` | Brief description for any other capital projects. |
| **ProjectJustification** | `projectjus` | `text` | The reason for the initiation of the project. |
| **OnStreetName** | `onstreetna` | `text` | The street where the capital project is taking place. |
| **FromStreetName** | `fromstreet` | `text` | The nearest cross street from where the capital project is taking place. |
| **ToStreetName** | `tostreetna` | `text` | The nearest cross street to where the capital project is taking place. |
| **BoroughName** | `boroughnam` | `text` | The New York City borough where the project would take place. |
| **OFTCode** | `oftcode` | `text` | A 18 digit code consisting of three 6-digit street codes representing On-From-To streets as returned by GeoSupport functions. |
| **LocationGeometry.STLength()** | `location_1` | `number` | The length of the street segment or geometry of the project in feet. |
| **DesignFY** | `designfy` | `number` | The fiscal year in which the design was initiated. |
| **SafetyScope** | `safetyscop` | `text` | Brief description for a safety related capital projects. |

---
### Street and Highway Capital Reconstruction Projects - Intersection (`capital_intersections`)

> This data is a spatial representation of street construction projects. Street and Highway capital projects are major street reconstruction projects, ranging from general street resurfacing projects to full reconstruction of the roadbed, sidewalks, sewer and water pipes and other utilities. Capital projects are essential to keep the City's infrastructure in a state of good repair.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **the_geom** | `the_geom` | `multipoint` |  |
| **ProjectID** | `projectid` | `number` | A unique number assigned to identify a capital project. |
| **ProjTitle** | `projtitle` | `text` | The full title of the capital project. |
| **FMSID** | `fmsid` | `text` | The unique budget code assigned to the capital project in the citywide Financial Management System (FMS). |
| **FMSAgencyID** | `fmsagencyi` | `number` | The three number citywide Financial Management System (FMS) agency code. |
| **LeadAgency** | `leadagency` | `text` | The primary agency leading the capital project in three letter acronym. |
| **Managing Agency** | `managingag` | `number` | The agency that manages the project in three letter acronym. |
| **ProjectDescription** | `projectdes` | `text` | The description of the capital project. |
| **ProjectTypeCode** | `projecttyp` | `text` | The three letter code that identifies the type of work being performed. |
| **ProjectType** | `projectt_1` | `text` | The full description on the type of work that is being performed for the capital project. |
| **ProjectStatus** | `projectsta` | `text` | The current status of the capital project. |
| **ConstructionFY** | `constructi` | `number` | The fiscal year of the capital project. |
| **DesignStartDate** | `designstar` | `calendar_date` | The date the design phase of the capital project starts. |
| **ConstructionEndDate** | `construc_2` | `calendar_date` | The date the project will be completed. |
| **CurrentFunding** | `currentfun` | `number` | Estimated current funding allocated for this capital project. |
| **ProjectCost** | `projectcos` | `number` | Estimated cost of the capital project. |
| **OversallScope** | `overallsco` | `text` | Overall brief description of the capital projects. |
| **SafetyScope** | `safetyscop` | `text` | Brief description for a safety related capital projects. |
| **OtherScope** | `otherscope` | `text` | Brief description for any other capital projects. |
| **ProjectJustification** | `projectjus` | `text` | The reason for the initiation of the project. |
| **OnStreetName** | `onstreetna` | `text` | The street where the capital project is taking place. |
| **FromStreetName** | `fromstreet` | `text` | The nearest cross street from where the capital project is taking place. |
| **ToStreetName** | `tostreetna` | `text` | The nearest cross street to where the capital project is taking place. |
| **BoroughName** | `boroughnam` | `text` | The New York City borough where the project would take place. |
| **OFTCode** | `oftcode` | `text` | A 18 digit code consisting of three 6-digit street codes representing On-From-To streets as returned by GeoSupport functions. |
| **DesignFY** | `designfy` | `number` | The fiscal year in which the design was initiated. |
| **Latitude** | `latitude` | `number` |  |
| **Longitude** | `longitude` | `number` |  |
| **x** | `x` | `text` |  |
| **y** | `y` | `text` |  |

---
### Street Construction Inspections and Corrective Action Requests (`street_construction_inspections`)

> DOT's Highway Inspection & Quality Assurance (HIQA) enforces the laws and rules that govern the way utilities, plumbers, contractors, other governmental agencies, and property owners perform work on the City's sidewalks, roadways and highways. DOT's inspectors also review work sites for compliance with permit stipulations, and issue violations when they find non-compliance with the laws and rules.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **InspectionID** | `inspectionid` | `number` |  |
| **PermitNumber** | `permitnumber` | `text` |  |
| **PermitteeName** | `permitteename` | `text` |  |
| **PermitType** | `permittype` | `text` |  |
| **OnstreetName** | `onstreetname` | `text` |  |
| **FromStreetName** | `fromstreetname` | `text` |  |
| **ToStreetName** | `tostreetname` | `text` |  |
| **SpecificLocation** | `specificlocation` | `text` |  |
| **InspectionType** | `inspectiontype` | `text` |  |
| **InspectionDate** | `inspectiondate` | `date` |  |
| **InspectionResultType** | `inspectionresulttype` | `text` |  |
| **InspectionRemarks** | `inspectionremarks` | `text` |  |
| **CARNumber** | `carnumber` | `text` |  |
| **DefectiveCuts** | `defectivecuts` | `number` |  |
| **FeetFromCrossStreet** | `feetfromcrossstreet` | `number` |  |
| **FeetFromCurb** | `feetfromcurb` | `number` |  |
| **CARComments** | `carcomments` | `text` |  |
| **LaneOfCut** | `laneofcut` | `text` |  |
| **TrafficFlow** | `trafficflow` | `text` |  |
| **CrossStreetName** | `crossstreetname` | `text` |  |
| **CurbStreetName** | `curbstreetname` | `text` |  |
| **NOVNumber** | `novnumber` | `text` |  |
| **NOVCode** | `novcode` | `text` |  |
| **NOVCodeDescription** | `novcodedescription` | `text` |  |
| **DetailsofViolation** | `detailsofviolation` | `text` |  |
| **CreatedOn** | `createdon` | `date` |  |
| **ModifiedOn** | `modifiedon` | `calendar_date` |  |

---
### Street Closures due to Construction Activities by Block (`street_closures_block`)

> DOT Street Closure data identifies locations in the New York City Street Closure map where a street is subject to a full closure, restricting through traffic, for the purpose of conducting construction related activity on a City street. Details about DOT construction permits can be found at Street Works Manual, http://streetworksmanual.nyc/.  Full Closure Permits are issued for a period of time during which the street may be closed to through traffic for only a portion of the time, and open at other times.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **the_geom** | `the_geom` | `multiline` | geometry column |
| **SEGMENTID** | `segmentid` | `number` | The Segment ID is a Department of City Planning LION reference  number. |
| **OFT** | `oft` | `number` | A 18 digit code consisting of three 6-digit street codes representing On-From-To (OFT) streets as returned by GeoSupport functions. |
| **ONSTREETNAME** | `onstreetname` | `text` | The On Street Name as is defined in GOAT, the Department of City Planning Geographic Online Address Translator (GOAT). |
| **FROMSTREETNAME** | `fromstreetname` | `text` | From Street Name refers to the cross street where the lowest house numbers of the on-street begins, or as defined in GOAT. |
| **TOSTREETNAME** | `tostreetname` | `text` | To Street Name refers to the cross street where the highest house numbers of the on-street ends, or as defined un GOAT. |
| **BOROUGH_CODE** | `borough_code` | `text` | New York City is composed of five boroughs, each borough has a code as an identifier. |
| **WORK_START_DATE** | `work_start_date` | `calendar_date` | The Work Start Date is the date the permit holder can  begin the work. |
| **WORK_END_DATE** | `work_end_date` | `calendar_date` | The Work End Date is the permit expiration date. |
| **UNIQUEID** | `uniqueid` | `text` | Unique hexadecimal identification number of each entry. |
| **PURPOSE** | `purpose` | `text` | Type of work being done at location. |

---
### Street Construction Permits - Stipulations (2020 - Present) (`permit_stipulations`)

> DOT issues over 150 different types of sidewalk and roadway construction permits to utilities, contractors, government agencies and homeowners. Permits cover activities such as street openings, sidewalk construction and installing canopies over sidewalks.
Stipulations are rules that apply to a permit. One permit may have multiple stipulations.

For the list of permit stipulations for the 2013-2019, please refer to <a href="https://data.cityofnewyork.us/d/pbk5-6r7z">this link</a>.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **PermitNumber** | `permitnumber` | `text` |  |
| **StipulationID** | `stipulationid` | `text` |  |
| **StipulationFullText** | `stipulationfulltext` | `text` |  |
| **CreatedOn** | `createdon` | `calendar_date` |  |

---
### Curb Metal Protruding Data (`curb_metal_protruding`)

> This database tracks all correspondence and repairs on steel that protrudes from a sidewalk curb.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **File** | `file` | `text` |  |
| **Closed** | `closed` | `text` |  |
| **311** | `_311` | `text` |  |
| **SR .** | `sr` | `text` |  |
| **Steel Curb** | `steel_curb` | `text` |  |
| **SC Cut** | `sc_cut` | `text` |  |
| **Ref to Other** | `ref_to_other` | `text` |  |
| **CB** | `cb` | `text` |  |
| **On Street** | `on_street` | `text` |  |
| **I/F/O** | `i_f_o` | `text` |  |
| **Cross St .1** | `cross_st_1` | `text` |  |
| **Cross St .2** | `cross_st_2` | `text` |  |
| **Lin ft** | `lin_ft` | `text` |  |
| **Sq ft** | `sq_ft` | `text` |  |
| **Rec'd 2** | `rec_d_2` | `calendar_date` |  |
| **Insp** | `insp` | `calendar_date` |  |
| **Borough** | `borough` | `text` |  |

---
### Step Streets Locations (`step_streets`)

> Step Street are steps that were built, instead of a typical roadway, on a mapped street that has a huge grade difference.  They were built to avoid very steep roadway and provide access for public use. These steep, block-long, open-air staircases for pedestrians connect two streets at different elevations.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Boro/CB** | `boro_cb` | `text` | Borough/ Community Board of the step streets locations |
| **On-street** | `on_street` | `text` | The street block the step street is located on |
| **From** | `from` | `text` | The name of the closest cross street on one end |
| **To** | `to` | `text` | The name of the closest cross street on the other end |

---
### Street Resurfacing Schedule (`street_resurfacing_schedule`)

> DOT issues a list of streets where crews will be doing milling or resurfacing work each week.* 
*Schedules are subject to change due to inclement weather or equipment issues.
For more information, visit NYC DOT website: https://www.nyc.gov/html/dot/html/motorist/resurfintro.shtml

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Work Schedule Project Location ID** | `workscheduleprojectlocationid` | `number` | Unique ID |
| **Borough Name** | `boroughname` | `text` | The New York City borough where the resurfacing would take place. |
| **Day** | `day` | `text` | Day of the week the resurfacing was conducted |
| **Date** | `date` | `calendar_date` | The date and times that the resurfacing occurred |
| **On Street Name** | `onstreetname` | `text` | Roadway segment where street resurfacing  is taking place |
| **From Street Name** | `fromstreetname` | `text` | Street name at the start of the onstreet segment, or intersection |
| **To Street Name** | `tostreetname` | `text` | Street name at the end of the onstreet segment, or intersection |
| **Community Board** | `communityboard` | `number` | New York City Community Board where the resurfacing was located |
| **Area** | `area` | `text` | The neighborhood name of the resurfacing project. |
| **Work Type** | `worktype` | `text` | The crew conducting the work, DOT in-house crew or contractors |
| **Crew Type** | `crewtype` | `text` | The type of work being complete by either in-house crew or contractors |
| **Shift Type** | `shifttype` | `text` | Shift of the work being completed |
| **OFTCode** | `oftcode` | `text` | A 18 digit  code consisting of three 6-digit street codes representing On-From-To streets as returned by GeoSupport functions. |
| **Location Segment ID** | `location_segment_id` | `number` | Unique identifier for the street block. |
| **Location WKT** | `location_wkt` | `text` | A text markup language for representing vector geometry objects on a map and spatial reference systems of spatial objects. |
| **Location Node ID** | `location_node_id` | `number` | Unique identifier for the street intersections. |

---
### DOT In-house Street Resurfacing Projects (`street_resurfacing_inhouse`)

> List of all New York City Department of Transportation (NYC DOT) in-house street paving and milling projects for a street block or at an intersection. For information, please the DOT website: https://www.nyc.gov/html/dot/html/motorist/resurfintro.shtml

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **OFT Code** | `oft_code` | `text` | A unique numerical 18 digit code for the On- From- To location of the street segment. |
| **Project Type** | `project_type` | `text` | Flags whether the street resurfacing project is for the block or intersection |
| **Borough Code** | `borough_code` | `text` | The borough of the street segment in one letter format. |
| **Location On Street** | `location_on_street` | `text` | The name of the street where the construction embargo is taking place. |
| **Location From Street** | `location_from_street` | `text` | The closest intersection to the on street in one direction. |
| **Location To Street** | `location_to_street` | `text` | The closest intersection to the on street in the opposite direction. |
| **Project ID** | `project_id` | `text` | The unique identifier assigned to the capital project. |
| **Project Status** | `project_status` | `text` | The project status. |
| **Project Speed Bumps** | `project_speed_bumps` | `number` | The street block contains a speed reducer. |
| **Location Community Board** | `location_community_board` | `number` | The three digit borough code and community board where the street resurfacing takes place. |
| **Location Actual Milling Start Date** | `location_actual_milling_start_date` | `calendar_date` | The actual start date for road milling. |
| **Location Actual Milling End Date** | `location_actual_milling_end_date` | `calendar_date` | The actual end date for road milling. |
| **Location Actual Paving Start Date** | `location_actual_paving_start_date` | `calendar_date` | The actual start date for road paving. |
| **Location Actual Paving End Date** | `location_actual_paving_end_date` | `calendar_date` | The actual end date for road paving. |
| **Location Actual Protect Until** | `location_actual_protect_until` | `calendar_date` | The actual date the street is protected until after street replacement. |
| **Location Actual Lane Miles Paved** | `location_actual_lane_miles` | `number` | The number of lane miles paved. |
| **Location Actual Paving Square Yard** | `location_actual_paving_square` | `number` | The amount of square yards paved. |
| **Location Status** | `location_status` | `text` | The project paving and milling status at the location. |
| **Location Segment ID** | `location_segment_id` | `number` | Unique identifier for the street block. |
| **Location WKT** | `location_wkt` | `text` | A text markup language for representing vector geometry objects on a map and spatial reference systems of spatial objects. |
| **Location Node ID** | `location_node_id` | `text` | Unique identifier for the street intersections. |

---
### NYC Planimetric Database: Sidewalk (`sidewalk_planimetric`)

> Planimetric basemap polygon layer containing sidewalk features. 
Please see the following link for additional documentation- https://github.com/CityOfNewYork/nyc-planimetrics/blob/master/Capture_Rules.md.

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |

---
### Pedestrian Mobility Plan Pedestrian Demand (`pedestrian_demand`)

> Based on citywide data sources for pedestrian generators, NYC DOT developed a holistic, data-driven framework to categorize streets based on pedestrian needs. The plan aims to improve pedestrian comfort and convenience as well as increase walking citywide. NYC DOT created five broad street categories to determine the pedestrian needs on the city’s sidewalks. For more information, please visit NYC DOT website: https://www1.nyc.gov/html/dot/html/pedestrians/pedestrian-mobility.shtml

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **the_geom** | `the_geom` | `multiline` | Description of the spatial file format. |
| **BoroCode** | `borocode` | `text` | BoroCode |
| **BoroName** | `boroname` | `text` | The name of the borough where the exclusive pedestrian signal was installed. |
| **BoroCD** | `borocd` | `text` | The three digit number that represents the borough and the community district. |
| **CounDist** | `coundist` | `text` | The Council District where the exclusive pedestrian signal was installed. |
| **AssemDist** | `assemdist` | `text` | The Assembly District where the exclusive pedestrian signal was installed. |
| **StSenDist** | `stsendist` | `text` | The State Senate District where the exclusive pedestrian signal was installed. |
| **CongDist** | `congdist` | `text` | The Congressional District where the exclusive pedestrian signal was installed. |
| **street** | `street` | `text` | The name of the street block. |
| **segmentid** | `segmentid` | `text` | Unique seven digit identifier from LION. |
| **Rank** | `rank` | `number` | The number that correlates with the category for each street block. |
| **PMP_ID** | `pmp_id` | `number` | Unique identifier used in creation of the sidewalk demand map. |
| **NTA2020** | `nta2020` | `text` | Neighborhood Tabulation Area Code |
| **Boro** | `boro` | `text` | Two letter acronym for the New York City borough. |
| **Category** | `category` | `text` | The street description for pedestrian mobility program. |
| **NTAName** | `ntaname` | `text` | The name of the New York City neighborhood the signal was installed. |
| **FEMAFldz** | `femafldz` | `text` | FEMA flood zone code for the exclusive pedestrian signal intersection. |
| **FEMAFldT** | `femafldt` | `text` | FEMA flood zone description for the exclusive pedestrian signal intersection. |
| **HrcEvac** | `hrcevac` | `text` | The hurricane evacuation zone of the exclusive pedestrian signal. |
| **SHAPE_Leng** | `shape_leng` | `number` | The length of the line segment in inches. |

---
### Primary Land Use Tax Lot Output (PLUTO) (`mappluto`)

> Extensive land use and geographic data at the tax lot level in comma-separated values (CSV) file format. The PLUTO files contain more than seventy fields derived from data maintained by city agencies.

All previously released versions of this data are available on the <a href="https://www.nyc.gov/content/planning/pages/resources/datasets/mappluto-pluto-change">DCP Website: BYTES of the BIG APPLE</a>. Current version: 26v1

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **borough** | `borough` | `text` | The borough in which the tax lot is located. This field contains a two-character borough code.  Two portions of the city, Marble Hill and Rikers Island, are legally located in one borough but are serviced by a different borough. The BOROUGH codes associated with these areas are the boroughs in which they are legally located. Marble Hill is serviced by the Bronx, but is legally located in Manhattan and has a BOROUGH of MN. Rikers Island is serviced by Queens, but is legally located in the Bronx and has a BOROUGH of BX. |
| **Tax block** | `block` | `number` | The tax block in which the tax lot is located. This field contains a one to five-digit tax block number. Each tax block is unique within a borough (see BOROUGH). |
| **Tax lot** | `lot` | `number` | The number of the tax lot.  This field contains a one to four-digit tax lot number.  Each tax lot is unique within a tax block (see TAX BLOCK).  <b>Special handling for condominiums:</b>  In a condominium complex, each condominium unit is a separate tax lot and has its own lot number. In a residential condominium, the condominium units are generally the individual apartments; in a commercial condominium, the units might be floors in an office building, individual retail shops, or blocks of office space. These unit lot numbers have values between 1001 - 6999.  Each unit tax lot has an associated billing lot number, with values between 7501 - 7599. Lots in a condominium complex on the same block will have the same billing lot number. To make condominium information more compatible with parcel information, the Department of City Planning aggregates condominium unit tax lot information to the billing lot. For example, if a residential condominium building contains 20 units, the Department of Finance will assign 20 unit lot numbers and each of these lot numbers will have the same billing lot number. PLUTO will contain one record with the billing lot number and RESIDENTIAL UNITS will be set to 20.  If the Department of Finance has not yet assigned a billing lot number to the condominium complex, PLUTO uses the lowest unit lot number within the complex.  Note on MapPLUTO: The Department of Finance Digital Tax Map (DTM) contains the geography of the base lot for condominiums. The base lot is also called the "Formerly Known As" or FKA lot. For most condominium complexes, there is one base lot per billing lot. In using the DTM to create MapPLUTO, DCP replaces the base lot number with the billing lot number. If there is more than one base lot with the same billing lot number, DCP merges the base lots to create a geography for the billing lot.  Under certain circumstances, DCP is unable to aggregate condominium unit tax lot information to the billing lot or to the lowest unit lot number. This occurs when a CONDOMINIUM NUMBER has not yet been assigned to the unit lots in PTS. In most cases, these unit lots will appear in PLUTO and in the NOT_MAPPED_LOTS table that is released with MapPLUTO. Before including these unit lots, the data is checked to verify that it pertains only to the unit lot. If unit lots have an identical address and a value for RESIDENTIAL UNITS that is greater than 1 and the same for all records, and there is no matching BBL in the DTM, they are assumed to part of the same condominium. BUILDING AREA is checked in the same way. These unit lots are removed from PLUTO and NOT_MAPPED_LOTS to avoid overcounting the number of residential units and building area. |
| **community board** | `cd` | `number` | The community district (CD) or joint interest area (JIA) for the tax lot. The city is divided into 59 community districts and 12 joint interest areas, which are large parks or airports that are not considered part of any community district.  This field consists of three digits, the first of which is the borough code (see BORO CODE). The second and third digits are the community district or joint interest area number, whichever is applicable.  Joint interest areas: BOROUGH JIA NAME Manhattan 164 Central Park Bronx 226 Van Cortlandt Park 227 Bronx Park 228 Pelham Bay Park Brooklyn 355 Prospect Park 356 Gateway National Recreation Area Queens 480 LaGuardia Airport 481 Flushing Meadow/Corona Park 482 Forest Park 483 JFK International Airport 484 Gateway National Recreation Area Staten Island 595 Gateway National Recreation Area  Two portions of the city, Marble Hill and Rikers Island, are legally located in one borough, but serviced by a different borough. The COMMUNITY DISTRICT associated with these areas is the community district by which they are serviced.  Marble Hill is legally located in Manhattan, but is serviced by the Bronx and is divided between community districts 207 and 208. Rikers Island is legally located in the Bronx, but is serviced by Queens and is part of community district 401.  COMMUNITY DISTRICT contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, COMMUNITY DISTRICT is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **census tract 2010** | `ct2010` | `number` | The 2010 census tract in which the tax lot is located.  This field contains a one to four-digit census tract number, sometimes with a decimal point and a two-digit suffix.  2010 census tracts are geographic areas defined by the U.S. Census Bureau for the 2010 Census. Census tracts are comprised of census blocks.  Each census tract is unique within a borough (see BOROUGH).  Examples:    Census Tract 203.01    Census Tract 23  CENSUS TRACT 2010 contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, CENSUS TRACT 2010 is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **cb2010** | `cb2010` | `number` | The 2010 census block in which the tax lot is located.  This field contains a four-digit census block number and, when applicable, a one- character alphabetic suffix.  2010 census blocks are the smallest geographic areas defined by the U.S. Census Bureau.  Each census block number is unique within a census tract (see CENSUS TRACT).  Examples:    Census Block 101A    Census Block 102 |
| **schooldist** | `schooldist` | `number` | The school district in which the tax lot is located.  This field contains a two-digit school district number, which is preceded with a zero when the district number is one digit.  The city is divided up into 34 school districts. Those districts are then divided into smaller zones which determine the area served by local schools. Each district has its own superintendent and receives guidance from a Community District Education Council made up of parents and local representatives.  SCHOOL DISTRICT contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, SCHOOL DISTRICT is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **council district** | `council` | `number` | The city council district in which the tax lot is located.  This field contains a two-digit city council district number, which is preceded with a zero when the district number is one digit.  There are currently 51 city council districts in the City, which serve as political districts for the legislative branch of city government. |
| **postcode** | `zipcode` | `number` | A ZIP code that is valid for one of the addresses assigned to the tax lot.  Note that a tax lot may have multiple addresses and these addresses may not have the same ZIP code. A building with entrances on two streets may have a different ZIP code for each street address. ZIP CODE may not be valid for the street address in ADDRESS.  If a tax lot does not have an ADDRESS or the ADDRESS contains a street name without a house number, ZIP CODE will be blank. |
| **firecomp** | `firecomp` | `text` | The fire company that services the tax lot.  This field consists of four characters, the first of which is an alphabetic code identifying the type of fire company, where E stands for Engine, L stands for Ladder and Q stands for Squad. The type code is followed by a one to three- digit fire company number which is preceded with leading zeros if the company number is less than three digits.  FIRE COMPANY contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, FIRE COMPANY is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. data_type: text |
| **policeprct** | `policeprct` | `number` | The police precinct in which the tax lot is located.  This field contains a three-digit police precinct number which is preceded with leading zeros if the precinct number has less than three digits.  POLICE PRECINCT contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, POLICE PRECINCT is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **healtharea** | `healtharea` | `number` | The health area in which the tax lot is located.  Health areas were originally created in the 1920s for the purpose of reporting and statistical analysis of public health data. They were based on census tracts and created to be areas of equal population. Health areas are contained within health center districts.  This field contains a four-digit health area number, which is preceded with leading zeros when the health area is less than four digits. There is an implied decimal point after the first two digits.  HEALTH AREA contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, HEALTH AREA is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **sanitboro** | `sanitboro` | `number` | The borough of the sanitation district that services the tax lot.  SANITATION DISTRICT BORO contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, SANITATION DISTRICT BORO is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **sanitsub** | `sanitsub` | `text` | The subsection of the sanitation district that services the tax lot.  SANITATION SUBSECTION contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, SANITATION SUBSECTION is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files.    data_source: | |
| **address** | `address` | `text` | An address for the tax lot.  Tax lots may be assigned a single house number on a street, a range of house numbers on a street, or addresses on multiple streets. ADDRESS contains the address in PTS, using the low number when there is a range of house numbers. Some tax lots, such as vacant lots or parks, have only a street name and no house number.  A complete list of the addresses assigned to a tax lot is available through Geosupport or by downloading the Property Address Directory (PAD) from the BYTES of the BIG APPLETM.  Most house numbers in Queens contain a hyphen. |
| **zonedist1** | `zonedist1` | `text` | The zoning district classification of the tax lot. Under the Zoning Resolution, the map of New York City is generally apportioned into three basic zoning district categories: Residence (R), Commercial (C) and Manufacturing (M), which are further divided into a range of individual zoning districts, denoted by different number and letter combinations. In general, the higher the number immediately following the first letter (R, C or M), the higher the density or intensity of land use permitted.  If the tax lot is divided by a zoning boundary line, ZONING DISTRICT 1 represents the zoning district classification occupying the greatest percentage of the tax lot's area.  For example: Tax lot 98 is divided by a zoning boundary line into part A and part B. Part A, the largest portion of the lot, is in a commercial zoning district, while part B is in a residential zoning district. ZONING DISTRICT 1 will contain the commercial zoning district associated with part A.  Tax lots that intersect with areas designated in NYC Zoning Districts as PARK, BALL FIELD, PLAYGROUND, and PUBLIC SPACE are assigned a single value of PARK in PLUTO. The NYC Zoning Districts do not constitute a definitive list of parks in the city. Lots designated as PARK should not be used to calculate the amount of open space in an area.  See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided.  Abbreviation Description R1-1 - R12 Residential Districts C1-6 - C8-4 Commercial Districts M1-1 - M3-2 Manufacturing Districts M1-1/R5 - M1-6/R10 Mixed Manufacturing & Residential Districts BPC Battery Park City PARK Areas designated as PARK, BALL FIELD, PLAYGROUND and PUBLIC SPACE in NYC Zoning Districts |
| **zonedist2** | `zonedist2` | `text` | If the tax lot is divided by zoning boundary lines, ZONING DISTRICT 2 represents the zoning classification occupying the second greatest percentage of the tax lot's area. Only zoning districts that cover at least 10% of a tax lot's area are included.  If the tax lot is not divided by a zoning boundary line, the field is blank.  For example: Tax lot 98 is divided by a zoning boundary line into part A and part B. Part A, the larger portion of the lot, is in a commercial zoning district, while part B is in a residential zoning district. ZONING DISTRICT 2 will contain the residential zoning district associated with part B.  See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **zonedist3** | `zonedist3` | `text` | If the tax lot is divided by zoning boundary lines, ZONING DISTRICT 3 represents the zoning classification occupying the third greatest percentage of the tax lot's area. Only zoning districts that cover at least 10% of a tax lot's area are included.  If the tax lot is not split between three zoning districts, the field is blank.  For example: Tax lot 98 is divided by zoning boundary lines into three sections - part A, part B and part C. Part A represents the largest portion of the lot, part B is the second largest portion of the lot, and part C covers the smallest portion of the tax lot. ZONING DISTRICT 3 will contain the zoning associated with part C.  See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **zonedist4** | `zonedist4` | `text` | If the tax lot is divided by zoning boundary lines, ZONING DISTRICT 4 represents  the zoning classification occupying the fourth greatest percentage of the tax lot's area. Only zoning districts that cover at least 10% of a tax lot's area are included.  If the tax lot is not split between four zoning districts, the field is blank.  For example: Tax lot 98 is divided by zoning boundary lines into four sections - part A, part B, part C and part D. Part A represents the largest portion of the lot, part B is the second largest portion of the lot, part C represents the third largest portion of the lot, and part D covers the smallest portion of the tax lot. ZONING DISTRICT 4 will contain the zoning associated with part D.  See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **overlay1** | `overlay1` | `text` | The commercial overlay assigned to the tax lot. A commercial overlay is a C1 or C2 zoning district mapped within residential zoning districts to serve local retail needs (grocery stores, dry cleaners, restaurants, for example).  If more than one commercial overlay exists on the tax lot, COMMERCIAL OVERLAY 1 represents the commercial overlay occupying the greatest percentage of the lot area. The commercial overlay district must either cover at least 10% of a tax lot's area or at least 50% of the commercial overlay district must be contained within the tax lot.  If the tax lot is does not contain a commercial overlay, the field is blank.  See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **overlay2** | `overlay2` | `text` | A commercial overlay assigned to the tax lot.  If the tax lot has more than one commercial overlays, COMMERCIAL OVERLAY 2 represents the commercial overlay occupying the second largest percentage of the tax lot's area. The commercial overlay district must either cover at least 10% of a tax lot's area or at least 50% of the commercial overlay district must be contained within the tax lot.  If the tax lot is not divided by two commercial overlays the field is blank. See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **spdist1** | `spdist1` | `text` | The special purpose district assigned to the tax lot. The regulations for special purpose districts are designed to supplement and modify the underlying zoning in order to respond to distinctive neighborhoods with particular issues and goals. Only special purpose districts that cover at least 10% of a tax lot's area are included.  If the tax lot is not in a special purpose district, the field is blank.  If more than one special purpose district exists on the tax lot, SPECIAL PURPOSE DISTRICT 1 represents the special purpose district occupying the greatest percentage of the lot area. If the greatest percentage is occupied by two special purpose districts that overlap each other and cover the same percentage of the lot, SPECIAL PURPOSE DISTRICT 1 contains both special purpose districts. separated by "/". • See Appendix A for valid values. See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **spdist2** | `spdist2` | `text` | The special purpose district assigned to the tax lot. The regulations for special purpose districts are designed to supplement and modify the underlying zoning in order to respond to distinctive neighborhoods with particular issues and goals. Only special purpose districts that cover at least 10% of a tax lot's area are included.  If the tax lot is not divided by at least two special purpose districts, the field is blank.  If more than one special purpose district exists on the tax lot, SPECIAL PURPOSE DISTRICT 2 represents the special purpose district occupying the second greatest percentage of the lot area. If the second greatest percentage is occupied by two special purpose districts that overlap each other and cover the same percentage of the lot, SPECIAL PURPOSE DISTRICT 2 contains both special purpose districts. separated by "/".  See Appendix A for valid values.  See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **spdist3** | `spdist3` | `text` | The special purpose district assigned to the tax lot. The regulations for special purpose districts are designed to supplement and modify the underlying zoning in order to respond to distinctive neighborhoods with particular issues and goals. Only special purpose districts that cover at least 10% of a tax lot's area are included.  If the tax lot is not divided by at least three special purpose districts, the field is blank.  If the tax lot has more than two special purpose districts, SPECIAL PURPOSE DISTRICT 3 represents the special purpose district occupying the smallest percentage of the lot area.  See Appendix A for valid values.  See SPLIT BOUNDARY INDICATOR to determine if the tax lot is divided. |
| **ltdheight** | `ltdheight` | `text` | The limited height district assigned to the tax lot. A limited height district is superimposed on an area designated as an historic district by the Landmarks Preservation Commission.  See Appendix B for valid values. |
| **splitzone** | `splitzone` | `checkbox` | A code indicating whether the tax lot is split between multiple zoning features. The split boundary indicator is equal to "Y" if the tax lot has a value for ZONING DISTRICT 2, COMMERCIAL OVERLAY 2, or SPECIAL DISTRICT BOUNDARY 2. |
| **bldgclass** | `bldgclass` | `text` | A code describing the major use of structures on the tax lot.  Except as described below, BUILDING CLASS is taken from PTS without modification.  For condominiums, PTS contains the building class for each unit lot. When merging this data into a single record for the billing lot, DCP creates several mixed-use building classes (RC, RD, RI, RM, RX, and RZ). These are assigned as follows: • If all unit lots have the same building class, that building class is used for the billing lot. • PTS building class types are grouped as follows:   o Commercial - R5, R7, R8, RA, RB, RH, and RK   o Residential - R1, R2, R3, R4, R6, and RR   o Mixed commercial and residential - R9   o Industrial/warehouse - RW • If the unit lots are a mixture of commercial building types, BUILDING CLASS = RC. • If the unit lots are a mixture of residential building types, BUILDING CLASS = RD. • If the unit lots are a mixture of commercial and residential building types, BUILDING CLASS = RM. • If the unit lots are a mixture of commercial and industrial/warehouse building types, BUILDING CLASS = RI. • If the unit lots are a mixture of commercial, residential, and industrial/warehouse building types, BUILDING CLASS = RX. • If the unit lots are a mixture of residential and industrial/warehouse building types, BUILDING CLASS = RZ. • When unit lots with a building class of RG (Indoor Parking), RP (Outdoor Parking), RS (Non-Business Storage Space), or RT (Terraces/Gardens/Cabanas) have the same billing lot as another building class, their building class is ignored. For example, if the billing lot has unit lots with a building class of R4 (Residential Unit in Elevator Bldg) and RG (Indoor Parking), BUILDING CLASS = R4.  Q0 is assigned by DCP to tax lots with a PTS building class starting with "V" that are identified in the NYC GIS Zoning Database as PARK, BALL FIELD, PLAYGROUND, or PUBLIC SPACE.  QG is assigned by DCP to tax lots with a PTS building class starting with "V" that contain community gardens from the Department of Parks and Recreation's NYC Greenthumb Community Gardens dataset. This is done to comply with Local Law 46 of 2020, which requires that such lots be given a land use category of open space, outdoor recreation, a community garden, or other similar description. Lots with a BUILDING CLASS of QG are assigned to LAND USE CATEGORY "09" (Open Space & Outdoor Recreation). This land use assignment is solely informational and does not confer or change a legal status for such a tax lot.  PTS contains two building classes for some tax lots, with one of the building classes being Z7 (Easement). BUILDING CLASS is only set to Z7 when it is the only PTS building class for the tax lot.  See Appendix C - Building Class Codes for valid values |
| **landuse** | `landuse` | `number` | A code for the tax lot's land use category.  The Department of City Planning has created 11 land use categories and assigns each BUILDING CLASS to the most appropriate land use category.  Appendix D - Land Use Categories details the relationship of building classes to land use categories. |
| **easements** | `easements` | `number` | The number of unique easements on the tax lot.  PTS contains a record for each easement. NUMBER OF EASEMENTS is calculated by counting the number of unique PTS easement records for the tax lot.  If the number of easements is zero, the tax lot has no easements. |
| **ownertype** | `ownertype` | `text` | A code indicating type of ownership for the tax lot.  Only one data source is used per tax lot.  The COLP file, which contains more accurate and specific type of city ownership data than PTS, is used when data is available for that lot. Codes C, M, O, P are derived from COLP.  If the tax lot is not in COLP, PTS is checked to see if the lot's EXEMPT TOTAL VALUE equals its ASSESSED TOTAL VALUE. If the two values are the same, the lot is given a code of X. Otherwise the tax lot is not given any TYPE OF OWNERSHIP CODE.  OWNER NAME should be referenced to verify type of ownership, particularly when it's important to distinguish between state, federal, and public authority ownership. |
| **ownername** | `ownername` | `text` | The name of the owner of the tax lot.  For publicly owned tax lots, owner names have been normalized. For example, "NYC PARKS", "PARKS DEPARTMENT", and "PARKS AND RECREATION (GENERAL)" have been changed to "NYC DEPARTMENT OF PARKS AND RECREATION".  If OWNER NAME is normalized, DCPEdited is set to "1". (see CHANGED BY DCP). |
| **lotarea** | `lotarea` | `number` | Total area of the tax lot, expressed in square feet rounded to the nearest integer.  LOT AREA contains street beds when the tax lot contains "paper streets" i.e., streets mapped but not built.  If the tax lot is not an irregularly shaped lot (see IRREGULAR LOT CODE) the Department of Finance calculates the LOT AREA by multiplying the LOT FRONTAGE by the LOT DEPTH. If the tax lot is irregularly shaped, DOF calculates the LOT AREA from the Digital Tax Map.  If PTS contains a zero value for LOT AREA, this field is changed to show the area of the tax lot's geometric shape in the Digital Tax Map and DCPEdited is set to "1". (see CHANGED BY DCP). |
| **bldgarea** | `bldgarea` | `number` | The total gross area in square feet, except for condominium measurements which come from the Condo Declaration and are net square footage not gross.  TOTAL BUILDING FLOOR AREA is populated in the following order of preference:   1. Gross floor area from PTS   2. Gross floor area from CAMA   3. Calculated from the PTS building dimensions and number of stories for the primary building on the lot. TOTAL BUILDING FLOOR AREA calculated by this method will not include floor area for any other buildings on the lot.   4. TOTAL BUILDING FLOOR AREA is set to zero if the building class starts with "V" and the number of buildings is zero.  See TOTAL BUILDING FLOOR AREA SOURCE CODE to determine which method was used.  If TOTAL BUILDING FLOOR AREA SOURCE CODE has a value of 2 (PTS) or 7 (CAMA), the TOTAL BUILDING FLOOR AREA is based on gross building area, also known as total gross square feet. For these data sources, the TOTAL BUILDING FLOOR AREA is for all of the structures on the tax lot, including stairwells, halls, elevator shafts, attics and extensions such as attached garages. Measurements are based on exterior dimensions and take into account setbacks.  If the TOTAL BUILDING FLOOR AREA SOURCE CODE field has a value of 5, the floor area was calculated from the DOF Property Tax System (PTS) using the building dimensions and number of stories for ONLY the largest structure on the tax lot.  In all cases, this is a rough estimate of the gross building floor area and does not necessarily take into account all the criteria for calculating floor area as defined in section 12-10 of the Zoning Resolution.  Roof areas used for parking/garden/playground are not included in the floor area.  If TOTAL BUILDING FLOOR AREA SOURCE CODE is 2, TOTAL BUILDING FLOOR AREA contains the common area for condominiums.  If FLOOR AREA, TOTAL BUILDING SOURCE CODE is 7, TOTAL BUILDING FLOOR AREA does not include below grade finished basements.  If the basement in a one, two or three family structure is above grade and finished, its square footage is included in TOTAL BUILDING FLOOR AREA.  A TOTAL BUILDING FLOOR AREA of zero can mean it is either not available or not applicable. If NUMBER OF BUILDINGS is greater than zero, then a TOTAL BUILDING FLOOR AREA of zero means it is not available. If NUMBER OF BUILDINGS is zero, then a TOTAL BUILDING FLOOR AREA of zero means it is not applicable. |
| **comarea** | `comarea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for commercial use.  Value is taken from PTS, if available. When calculated from PTS data, COMMERCIAL FLOOR AREA is the sum of floor areas for office, retail, garage, storage, factory, and other uses. If these fields are not populated in PTS, the value is taken from CAMA.  Originally square footage came from sketches, but, for both new construction and alterations, it now comes from site visits. Basement square footage may be included in COMMERCIAL FLOOR AREA if the commercial buildings meets two of the three following criteria: • Finished • Active • Publicly accessible For condominiums, COMMERCIAL FLOOR AREA is the sum of the commercial floor area for condominium lots with the same billing lot. COMMERCIAL FLOOR AREA does not contain the condominium's common area.  A COMMERCIAL FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **resarea** | `resarea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for residential use.  Value is taken from PTS, if available. Otherwise it comes from CAMA.  For condominiums, RESIDENTIAL FLOOR AREA is the sum of the residential floor area for condominium lots with the same billing lot. RESIDENTIAL FLOOR AREA does not contain the condominium's common area.  A RESIDENTIAL FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **officearea** | `officearea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for office use.  Value is taken from PTS, if available. Otherwise it comes from CAMA.  This information is NOT available for one, two or three family structures.  An OFFICE FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **retailarea** | `retailarea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for retail use.  Value is taken from PTS, if available. Otherwise it comes from CAMA.  This information is NOT available for one, two or three family structures.  A RETAIL FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **garagearea** | `garagearea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for garage use.  Value is taken from PTS, if available. Otherwise it comes from CAMA.  This information is NOT available for one, two or three family structures.  A GARAGE FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **strgearea** | `strgearea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for storage or loft purposes.  Value is taken from PTS, if available. Otherwise it comes from CAMA.  This information is NOT available for one, two or three family structures.  A STORAGE FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **factryarea** | `factryarea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for factory, warehouse or loft use.  Value is taken from PTS, if available. Otherwise it comes from CAMA.  This information is NOT available for one, two or three family structures.  A FACTORY FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **otherarea** | `otherarea` | `number` | An estimate of the exterior dimensions of the portion of the structure(s) allocated for other than commercial, residential, office, retail, garage, storage, or factory use.  Value is taken from PTS, if available. Otherwise it comes from CAMA.  This information is NOT available for one, two or three family structures.  An OTHER FLOOR AREA of zero can mean it is either not available or not applicable.  An update to the floor area is triggered by the issuance of a Department of Buildings permit, feedback from the public, or site visits by Department of Finance assessors.  The sum of the various floor area fields does not always equal TOTAL BUILDING FLOOR AREA. |
| **areasource** | `areasource` | `number` | A code indicating the methodology used to determine the tax lot's TOTAL BUILDING FLOOR AREA (BldgArea)  Only one source is used per tax lot. |
| **numbldgs** | `numbldgs` | `number` | The number of buildings on the tax lot.  The number of buildings on a lot is calculated by taking the Building Identification Number (BIN) for every building in DoITT's Building Footprints dataset, running Geosupport function BN to get the BBL associated with that BIN, and summing the number of buildings per tax lot. |
| **numfloors** | `numfloors` | `number` | The number of full and partial floors starting from the ground floor, for the tallest building on the tax lot. A partial floor is a floor that does not span the entire building envelope. For example, if a building is 3 stories tall and 2 floors cover the entire footprint of the building and one floor covers half of the footprint, the number of floors would be 2.5.  Above ground basements are not included in the NUMBER OF FLOORS.  A roof used for parking, farming, playground, etc. is not included in NUMBER OF FLOORS.  If the NUMBER OF FLOORS is null and the NUMBER OF BUILDINGS is greater than zero, then NUMBER OF FLOORS is not available for the tax lot. |
| **unitsres** | `unitsres` | `number` | The sum of residential units in all buildings on the tax lot.  If there are no residential units in the tax lot, this field will be zero.  Hotels/motels, nursing homes and SROs do not have residential units, but boarding houses do. Basement units for building superintendents are counted as a residential unit.  An update to residential units is triggered by the issuance of a Department of Buildings permit. |
| **unitstotal** | `unitstotal` | `number` | The sum of residential and non-residential (offices, retail stores, etc.) units for all buildings on the tax lot.  The count of non-residential units is sometimes not available if the building contains residential units.  Non-residential units are units with a separate use.  If a building has 25 different offices it would be counted as 1 unit because they have the same use.  Updates to residential and non-residential units are triggered by the issuance of a Department of Buildings permit. |
| **lotfront** | `lotfront` | `number` | The tax lot's frontage measured in feet.  NOTE: It appears that if a lot fronts on more than one street, the PTS building address often determines which side of the lot used for calculating lot frontage. |
| **lotdepth** | `lotdepth` | `number` | The tax lot's depth measured in feet. |
| **bldgfront** | `bldgfront` | `number` | The building's frontage along the street measured in feet. |
| **bldgdepth** | `bldgdepth` | `number` | The building's depth, which is the effective perpendicular distance, measured in feet. |
| **ext** | `ext` | `text` | A code identifying whether there is an extension on the lot or a garage other than the primary structure. |
| **proxcode** | `proxcode` | `number` | A code describing the physical relationship of the building to neighboring buildings. If there are multiple buildings on the lot, CAMA data for building number 1 is used. |
| **irrlotcode** | `irrlotcode` | `checkbox` | A code indicating whether the tax lot is irregularly shaped. |
| **lottype** | `lottype` | `number` | A code indicating the location of the tax lot in relationship to another tax lot and/or the water.  CAMA may contain multiple lot types for a tax lot. For instance, a lot may be both a corner lot and waterfront lot. DCP assigns LOT TYPE by taking the lowest CAMA lot type for the tax lot, with the exception of LOT TYPE 5, which is only assigned if the lot has no other lot types in CAMA. |
| **bsmtcode** | `bsmtcode` | `number` | A code describing the building's basement. |
| **assessland** | `assessland` | `number` | The assessed land value for the tax lot.  The Department of Finance calculates the assessed value by multiplying the tax lot's estimated full market land value, determined as if vacant and unimproved, by a uniform percentage for the property's tax class.  Assessed and exempt values are updated twice a year. Tentative values are released in mid-January and final values are released around May 25. If the date on source file (PTS), as reported in the Readme file, is between January 15 and May 25, ASSESSED LAND VALUE is from the tentative roll for the tax year starting in July. Otherwise, ASSESSED LAND VALUE is from the final roll. |
| **assesstot** | `assesstot` | `number` | The assessed total value for the tax lot.  The Department of Finance (DOF) calculates the assessed value by multiplying the tax lot's estimated full market value by a uniform percentage for the property's tax class.  DOF values properties based on current and constructive use, rather than legal use. The predominant active use, which determines the classification of a property, is determined by square footage. If the second story of a three-story building is mixed-use, an interior inspection may be necessary to establish the commercial percentage of that story before reclassification. In other cases, a two-story building with retail on the first floor may have a sign identifying a second story accounting office.  If, for example, the second story is a primary residence and there is a difference in square footage from the first to second floor, the mere presence of a business sign does not confirm a predominant commercial use.  Additional research is required to ensure proper classification.  This can include an internal inspection, speaking to someone at the location or a neighbor, and researching various records (such as filed Real Property Income and Expenses statements) from DOF or other city agencies.  NYC Property Tax Classes are determined by NYS and described under Real Property Tax Law (RPTL) [Article §18-02](https://gcc02.safelinks.protection.outlook.com/?url=https%3A%2F%2Fwww.nysenate.gov%2Flegislation%2Flaws%2FRPT%2F1802&data=05%7C01%7CLSeirup%40planning.nyc.gov%7Cd62da5a4813248adc71e08dab374460e%7C32f56fc75f814e22a95b15da66513bef%7C0%7C0%7C638019609211103424%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C3000%7C%7C%7C&sdata=rr4wH48ewePfrBbuHeY18ewwelGkQVsF62Rs9tJbBj8%3D&reserved=0) which mentions primary use for real property classification.  Property value is assessed as of January 5th.  If a new building is not completed by April 14th, the assessed building value is 0 and the Building Class reverts to Vacant.  Assessed and exempt values are updated twice a year. Tentative values are released in mid-January and final values are released around May 25. If the date on source file (PTS), as reported in the Readme file, is between January 15 and May 25, ASSESSED TOTAL VALUE is from the tentative roll for the tax year starting in July. Otherwise, ASSESSED TOTAL VALUE is from the final roll |
| **exempttot** | `exempttot` | `number` | The exempt total value, which is determined differently for each exemption program, is the dollar amount related to that portion of the tax lot that has received an exemption.  Assessed and exempt values are updated twice a year. Tentative values are released in mid-January and final values are released around May 25. If the date on source file (PTS), as reported in the Readme file, is between January 15 and May 25, EXEMPT TOTAL VALUE is from the tentative roll for the tax year starting in July. Otherwise, EXEMPT TOTAL VALUE is from the final roll.  Note that New York State typically releases STAR exempt values right after the tentative roll is released. EXEMPT TOTAL VALUE will change to reflect these values after they are received. |
| **yearbuilt** | `yearbuilt` | `number` | The year construction of the building was completed.  In general, YEAR BUILT is accurate for the decade, but not necessarily for the specific year. Between 1910 and 1985, the majority of YEAR BUILT values are in years ending in 5 or 0. Many structures built between 1800s and early 1900s have a YEAR BUILT between 1899 and 1901.  For ~26,000 buildings in historic districts, YEAR BUILT has been changed to the date_high value from Landmarks Preservation Commission's [Individual Landmark and Historic District Building Database](https://data.cityofnewyork.us/Housing-Development/LPC-Individual-Landmark-and-Historic-District-Buil/7mgd-s57w). Any tax lot updated with LPC data has a value of 1 in field CHANGED BY DCP. The original YEAR BUILT value can be found in PLUTOChangeFileYYv#.#.csv, where YYv#.# is the version number.  If Year Built is null or 0, then the value is unknown. |
| **yearalter1** | `yearalter1` | `number` | If a building has only been altered once, YEAR ALTERED 1 is the date that alteration began.  If a building has been altered more than once, YEAR ALTERED 1 is the year of the second most recent alteration.  The Department of Finance defines alterations as modifications to the structure that, according to the assessor, change the value of the real property.  The date comes from Department of Buildings permits and may either be the actual date or an estimate. |
| **yearalter2** | `yearalter2` | `number` | If a building has only been altered once, this field is blank.  If a building has been altered more than once, YEAR ALTERED 2 is the year that the most recent alteration began.  The Department of Finance defines alterations as modifications to the structure that, according to the assessor, change the value of the real property.  The date comes from Department of Buildings permits and may either be the actual date or an estimate. |
| **histdist** | `histdist` | `text` | The name of the Historic District that the tax lot is within. Historic Districts are designated by the New York City Landmarks Preservation Commission. |
| **landmark** | `landmark` | `text` | This value indicates whether the lot contains an individual landmark building, an interior landmark building, or both. |
| **builtfar** | `builtfar` | `number` | The BUILT FLOOR AREA RATIO is the total building floor area divided by the area of the tax lot.  This is an estimate by City Planning based on rough building area and lot area measurements provided by the Department of Finance.  BUILT FLOOR AREA RATIO is calculated using the TOTAL BUILDING FLOOR AREA and the LOT AREA. |
| **residfar** | `residfar` | `number` | The maximum allowable residential floor area ratio for standard residences, based on the zoning district classification occupying the greatest percentage of the tax lot’s area as reported in ZoneDist1. If the lot is assigned to more than one zoning district and ZoneDist1 does not allow residential uses, MAXIMUM ALLOWABLE RESIDENTIAL FAR is based on ZoneDist2, ZoneDist3 or ZoneDist4, in that order.  The maximum allowable residential floor area ratios are exclusive of bonuses for plazas, plaza-connected open areas, arcades, or other amenities. For the maximum allowable floor area for affordable housing, Users should consult the AffResFAR field.  Users should consult Section 23-20 of the Zoning Resolution for more information.  For properties zoned R6, R7-1, R7-2, R8 or R9, ResidFAR reflects the maximum achievable floor area under ideal conditions for sky exposure plane buildings. Users should consult Section 23-73 of the Zoning Resolution for more information. |
| **commfar** | `commfar` | `number` | The maximum allowable commercial floor area ratio, based on the zoning district classification occupying the greatest percentage of the tax lot's area as reported in ZoneDist1. If the lot is assigned to more than one zoning district and ZoneDist1 does not allow commercial uses, MAXIMUM ALLOWABLE COMMERCIAL FAR is based on ZoneDist2, ZoneDist3 or ZoneDist4, in that order.  The maximum allowable commercial floor area ratios are exclusive of bonuses for plazas, plaza-connected open areas, arcades, or other amenities.  Users should consult Section 33-12 of the Zoning Resolution for more information. |
| **facilfar** | `facilfar` | `number` | The maximum allowable community facility floor area ratio, based on the zoning district classification occupying the greatest percentage of the tax lot's area as reported in ZoneDist1. If the lot is assigned to more than one zoning district and ZoneDist1 does not allow community facility uses, MAXIMUM ALLOWABLE COMMUNITY FACILITY FAR is based on ZoneDist2, ZoneDist3 or ZoneDist4, in that order.  The maximum allowable community facility floor area ratios are exclusive of bonuses for plazas, plaza-connected open areas, arcades, or other amenities.  Users should consult Section 24-11, 33-12, or 43-12 of the Zoning Resolution, as applicable, for more information. |
| **affresfar** | `affresfar` | `number` | The maximum allowable residential floor area ratio for affordable housing, based on the zoning district classification occupying the greatest percentage of the tax lot’s area as reported in ZoneDist1. If the lot is assigned to more than one zoning district and ZoneDist1 does not allow residential uses, MAXIMUM ALLOWABLE AFFORDABLE RESIDENTIAL FAR is based on ZoneDist2, ZoneDist3 or ZoneDist4, in that order.  The maximum allowable residential floor area ratios are exclusive of bonuses for plazas, plaza-connected open areas, arcades, or other amenities.  Users should consult Section 23-20 of the Zoning Resolution for more information. |
| **mnffar** | `mnffar` | `number` | The maximum allowable Manufacturing floor area ratio, based on the zoning district classification occupying the greatest percentage of the tax lot’s area as reported in ZoneDist1. If the lot is assigned to more than one zoning district and ZoneDist1 does not allow manufacturing uses, MAXIMUM ALLOWABLE MANUFACTURING FAR is based on ZoneDist2, ZoneDist3 or ZoneDist4, in that order.  The maximum allowable manufacturing floor area ratios are exclusive of bonuses for plazas, plaza-connected open areas, arcades, or other amenities.  Users should consult Section 43-12 of the Zoning Resolution for more information. |
| **borocode** | `borocode` | `number` | The borough in which the tax lot is located.  Two portions of the city, Marble Hill and Rikers Island, are legally located in one borough but are serviced by a different borough. The BORO CODEs associated with these areas are the boroughs in which they are legally located.  Marble Hill is serviced by the Bronx, but is legally located in Manhattan and has a BORO CODE of 1. Rikers Island is serviced by Queens, but is legally located in the Bronx and has a BORO CODE of 2. |
| **BBL** | `bbl` | `number` | A concatenation of the borough code, tax block and tax lot.  This field consists of the borough code followed by the tax block followed by the tax lot.  The borough code is one numeric digit.  The tax block is one to five numeric digits, preceded with leading zeros when the block is less than five digits.  The tax lot is one to four digits and is preceded with leading zeros when the lot is less than four digits.  For condominiums, the BBL is for the billing lot. See TAX LOT for more information on how condominiums are handled.  Examples: Manhattan Borough Code 1, Tax Block 16, Tax Lot 100 would be stored as 1000160100. Brooklyn Borough Code 3, Tax Block 15828, Tax Lot 7501 would be stored as 3158287501. |
| **condono** | `condono` | `number` | The condominium number assigned to the complex.  Condominium numbers are unique within a borough (see BOROUGH). |
| **tract2010** | `tract2010` | `number` | The 2010 census tract in which the tax lot is located.  This field contains a one to four-digit census tract number and a two-digit suffix.  There is an implied decimal point between the census tract number and the suffix.  The census tract number is preceded with leading zeros when the tract is less than four digits.  If the tract has no suffix, CENSUS TRACT 2 contains 4 characters.  2010 census tracts are geographic areas defined by the U.S. Census Bureau for the 2010 Census.  Examples: Census Tract 203.01 would be stored as 020301 Census Tract 23 would be stored as 0023 |
| **xcoord** | `xcoord` | `number` | The X coordinate of the XY coordinate pair which depicts the approximate location of the lot.  If the X coordinate is not available from Geosupport, it is calculated from the centroid of the tax lot, with the constraint that the resulting point must be within the lot boundaries.  The XY coordinates are expressed in the New York-Long Island State Plane coordinate system. |
| **ycoord** | `ycoord` | `number` | The Y coordinate of the XY coordinate pair which depicts the approximate location of the lot.  If the Y coordinate is not available from Geosupport, it is calculated from the centroid of the tax lot, with the constraint that the resulting point must be within the lot boundaries  The XY coordinates are expressed in the New York-Long Island State Plane coordinate system. |
| **latitude** | `latitude` | `number` | The WGS 84 latitude of the latitude/longitude coordinate pair for the approximate location of the tax lot. |
| **longitude** | `longitude` | `number` | The WGS 84 longitude of the latitude/longitude coordinate pair for the approximate location of the tax lot |
| **zonemap** | `zonemap` | `text` | The Department of City Planning Zoning Map Number associated with the tax lot's X and Y Coordinates. If the tax lot is on the border of two or more zoning maps, ZONING MAP \# is the zoning map covering the greatest area. |
| **zmcode** | `zmcode` | `checkbox` | A code (Y) identifies a tax lot on the border of two or more zoning maps. |
| **sanborn** | `sanborn` | `text` | The Sanborn Map Company map number associated with the tax block and lot.  SANBORN MAP \# format is Borough Code/Volume Number/Page Number,  where Borough Code is 1 (Manhattan), 2 (Bronx), 3 (Brooklyn), 4 (Queens), or 5 (Staten Island)  For example:  the SANBORN MAP \# associated with tax block 154, tax lot 23 in Manhattan is 1/01S/020.  This field has been deprecated and will be removed at a future date. The data in the field cannot be considered reliable. |
| **taxmap** | `taxmap` | `number` | The Department of Finance paper tax map volume number associated with the tax block and lot.  The first character of the Tax Map \# is the Borough Code - 1 (Manhattan), 2 (Bronx), 3 (Brooklyn), 4 (Queens), or 5 (Staten Island). The second and third characters are the Section Number and the fourth and fifth characters are the Volume Number.  NOTE: The Department of Finance no longer updates their paper tax maps. |
| **edesignum** | `edesignum` | `text` | The (E) designation number assigned to the tax lot. An (E) designation provides notice of the presence of an environmental requirement pertaining to potential hazardous materials contamination, high ambient noise levels or air emission concerns on a particular tax lot.  Note that a tax lot may have more than one (E) designation. See the source file for all designations on the lot. |
| **appbbl** | `appbbl` | `number` | The originating BBL (borough, block and lot) from the apportionment prior to the merge, split or property's conversion to a condominium.  APPORTIONMENT BBL is only available for mergers, splits, and conversions since 1984. |
| **appdate** | `appdate` | `calendar_date` | The date of the apportionment.  The data is in the format MM/DD/YYYY, where MM is a two-digit month, DD is the two-digit day, and YYYY is the four-digit year. |
| **plutomapid** | `plutomapid` | `number` | A code indicating whether the tax lot is in the PLUTO file, the MapPLUTO file with water areas included, and/or the MapPLUTO file that is clipped to the shoreline.  Because the Digital Tax Map (DTM) and the Property Tax System (PTS) are not updated at the same time, they are slightly out-of-sync. There will be lots in PTS that are not in the DTM and vice versa. In addition, some lots are wholly underwater and are not included in the version of MapPLUTO that is clipped to the shoreline.  The lot geographies in MapPLUTO (with water areas included) are created from the DTM. City Planning modifies the DTM for condominium lots to show the billing tax lot in MapPLUTO, rather than the base tax lot. If there is more than one base tax lot with the same billing lot, the base tax lots are merged into a single feature and assigned to the billing lot. See LOT for more information on condominium lots.  MapPLUTO (clipped to shoreline) is created by clipping the full MapPLUTO using DOF's Shoreline File. |
| **version** | `version` | `text` | The version number for this release of PLUTO.  The Version Number is in the format YYv#.# where:   YY is the last two digits of the year;   v stands for version;   \# is the release number for that year; and .# indicates an amendment to the original release, if applicable. |
| **sanitdistrict** | `sanitdistrict` | `number` | The sanitation district that services the tax lot.  SANITATION DISTRICT NUMBER contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, SANITATION DISTRICT NUMBER is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **healthcenterdistrict** | `healthcenterdistrict` | `number` | The health center district in which the tax lot is located. Thirty health center districts were created by the City in 1930 to conduct neighborhood focused health interventions.  This field contains a two-digit health district number.  HEALTH CENTER DISTRICT contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, HEALTH CENTER DISTRICT is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **firm07_flag** | `firm07_flag` | `number` | A value of 1 means that some portion of the tax lot falls within the 1% annual chance floodplain as determined by FEMA's 2007 Flood Insurance Rate Map.  Note that buildings on the tax lot may or may not be in the portion of the tax lot that is within the 1% annual chance floodplain. |
| **pfirm15_flag** | `pfirm15_flag` | `number` | A value of 1 means that some portion of the tax lot falls within the 1% annual chance floodplain as determined by FEMA's 2015 Preliminary Flood Insurance Rate Map.  Note that buildings on the tax lot may or may not be in the portion of the tax lot that is within the 1% annual chance floodplain. |
| **dcpedited** | `dcpedited` | `text` | Flag indicating that City Planning has applied a correction to the record.  Flag set to "1" if City Planning has made a change to any field values for this tax lot. To see which field(s) were changed, refer to the PLUTOChangeFileYYv#.#.csv, where YYv#.# is the version number. See the PLUTO change file readme document for more information. |
| **notes** | `notes` | `text` | A text field containing notes of importance to one or more lots. |
| **bct2020** | `bct2020` | `text` | The 2020 census tract in which the tax lot is located.  This field contains a seven-digit code representing the one-digit borough code followed by the six-digit census tract number.  2020 census tracts are geographic areas defined by the U.S. Census Bureau for the 2020 Census. Census tracts are comprised of census blocks.  Each census tract is unique within a borough (see BOROUGH).  Examples: Census Tract 4062600 Census Tract 4063200  CENSUS TRACT 2020 contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, CENSUS TRACT 2020 is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **bctcb2020** | `bctcb2020` | `text` | The 2020 census block in which the tax lot is located.  This field contains an eleven-digit code representing the one-digit borough code followed by the six-digit census tract number and then the four-digit census block number.  2020 census blocks are the smallest geographic areas defined by the U.S. Census Bureau.  Each census block number is unique within a census tract (see CENSUS TRACT).  Examples: Census Block 20350001000 Census Block 30403001002  CENSUS BLOCK 2020 contains the value returned by Geosupport for one of the addresses assigned to the lot. If Geosupport does not return a value, CENSUS BLOCK 2020 is calculated spatially using the tax lot's XY COORDINATES and DCP's Administrative District Base Map files. |
| **mihopt1** | `mih_opt1` | `checkbox` | Flag set to “1” if MIH Option 1 applies to tax lot. Under Option 1, 25 percent of the residential floor area must be affordable to households earning an average of 60 percent of Area Median Income, of which 10 percent shall be affordable to families earning 40 percent of Area Median Income.  Users should consult Section 27-131 of the Zoning Resolution for more information. |
| **mihopt2** | `mih_opt2` | `checkbox` | Flag set to “1” if MIH Option 2 applies to tax lot. Under Option 2, 30 percent of the residential floor area must be affordable to households earning an average of 80 percent of Area Median Income.  Users should consult Section 27-131 of the Zoning Resolution for more information. |
| **mihopt3** | `mih_opt3` | `checkbox` | Flag set to “1” if MIH Option 3 (deep affordability) applies to tax lot. Under Option 3, 20 percent of the residential floor area must be affordable to households earning an average of 40 percent of Area Median Income.  Users should consult Section 27-131 of the Zoning Resolution for more information. |
| **mihopt4** | `mih_opt4` | `checkbox` | Flag set to “1” if MIH Option 4 (workforce option) applies to tax lot. Under Option 4, 30 percent of the residential floor area must be affordable to families earning an average of 115 percent of Area Median Income, of which 5 percent must be affordable to families earning 90 percent of Area Median Income and another 5 percent must be affordable to families earning 70 percent of Area Median Income.  Users should consult Section 27-131 of the Zoning Resolution for more information. |
| **transitzone** | `transitzone` | `text` | The Transit Zone classification of the tax lot. Under the Zoning Resolution, the map of New York City is apportioned into areas that generally govern residential parking. These include the Manhattan Core, LIC Parking Area, and Inner Transit Zone, where no residential parking is required. In addition, these include the Outer Transit Zone and the area Beyond the Greater Transit Zone where residential parking is required.  Users should consult Section 13-20 of the Zoning Resolution for more information on the Manhattan Core, Section 16-20 for more information on the LIC Parking Area, and Section 25-20 for more information on the other listed Transit Zone areas. |
| **geom** | `geom` | `text` |  |
| **basempdate** | `basempdate` | `text` |  |
| **dcasdate** | `dcasdate` | `text` |  |
| **edesigdate** | `edesigdate` | `text` |  |
| **landmkdate** | `landmkdate` | `text` |  |
| **masdate** | `masdate` | `text` |  |
| **polidate** | `polidate` | `text` |  |
| **rpaddate** | `rpaddate` | `text` |  |
| **zoningdate** | `zoningdate` | `text` |  |

---
### 311 Service Requests from 2020 to Present (`complaints_311`)

> <b>NOTE:</b> Learn more about the latest changes to this dataset: https://opendata.cityofnewyork.us/311-service-requests-from-2010-to-present-updates/

311 responds to thousands of inquiries, comments and requests from customers every single day. This dataset represents only service requests that can be directed to specific agencies.

This dataset is updated daily and expected values for many fields will change over time. The lists of expected values associated with each column are not exhaustive.

Each row of data contains information about the service request, including complaint type, responding agency, and geographic location. However the data does not reveal any personally identifying information about the customer who made the request.

For data from 2010-2019 see: https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-2019/76ig-c548/about_data

| Field Name | API Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **Unique Key** | `unique_key` | `text` | Unique identifier of a Service Request (SR) in the open data set |
| **Created Date** | `created_date` | `calendar_date` | Date SR  was created |
| **Closed Date** | `closed_date` | `calendar_date` | Date SR was closed by responding agency |
| **Agency** | `agency` | `text` | Acronym of responding City Government Agency |
| **Agency Name** | `agency_name` | `text` | Full Agency name of responding City Government Agency |
| **Problem (formerly Complaint Type)** | `complaint_type` | `text` | This is the first level of a hierarchy identifying the topic of the incident or condition.  Problem (formerly Complaint Type) broadly describes the topic of the incident or condition and are defined by the responding agencies. New Problems may be added in response to changes in customer demand. |
| **Problem Detail (formerly Descriptor)** | `descriptor` | `text` | This is associated to the Problem (formerly Complaint Type), and provides further detail on the incident or condition. Problem Detail (formerly Descriptor) values are dependent on the Problem, and are not always required in the service request. |
| **Additional Details** | `descriptor_2` | `text` | A third level of detail about the Problem (formerly Complaint Type) beyond the Problem Detail (formerly Descriptor). This is not used by every category of issue. |
| **Location Type** | `location_type` | `text` | Describes the type of location used in the address information |
| **Incident Zip** | `incident_zip` | `text` | Incident location zip code, provided by geo validation. |
| **Incident Address** | `incident_address` | `text` | House number of incident address provided by submitter. |
| **Street Name** | `street_name` | `text` | Street name of incident address provided by the submitter |
| **Cross Street 1** | `cross_street_1` | `text` | First Cross street based on the geo validated incident location |
| **Cross Street 2** | `cross_street_2` | `text` | Second Cross Street based on the geo validated incident location |
| **Intersection Street 1** | `intersection_street_1` | `text` | First intersecting street based on geo validated incident location |
| **Intersection Street 2** | `intersection_street_2` | `text` | Second intersecting street based on geo validated incident location |
| **Address Type** | `address_type` | `text` | Type of incident location information available. |
| **City** | `city` | `text` | City of the incident location provided by geovalidation. |
| **Landmark** | `landmark` | `text` | If the incident location is identified as a Landmark the name of the landmark will display here |
| **Facility Type** | `facility_type` | `text` | If available, this field describes the type of city facility associated to the SR |
| **Status** | `status` | `text` | Status of SR submitted |
| **Due Date** | `due_date` | `calendar_date` | Date when responding agency is expected to update the SR.  This is based on the Complaint Type and internal Service Level Agreements (SLAs). |
| **Resolution Description** | `resolution_description` | `text` | Describes the last action taken on the SR by the responding agency.  May describe next or future steps. |
| **Resolution Action Updated Date** | `resolution_action_updated_date` | `calendar_date` | Date when responding agency last updated the SR. |
| **Community Board** | `community_board` | `text` | Provided by geovalidation. |
| **Council District** | `council_district` | `text` | The City Council district where the service request is located. |
| **Police Precinct** | `police_precinct` | `text` | The NYPD precinct where the service request is located. |
| **BBL** | `bbl` | `text` | Borough Block and Lot, provided by geovalidation. Parcel number to identify the location of location of buildings and properties in NYC. |
| **Borough** | `borough` | `text` | Provided by the submitter and confirmed by geovalidation. |
| **X Coordinate (State Plane)** | `x_coordinate_state_plane` | `number` | Geo validated, X coordinate of the incident location. |
| **Y Coordinate (State Plane)** | `y_coordinate_state_plane` | `number` | Geo validated,  Y coordinate of the incident location. |
| **Open Data Channel Type** | `open_data_channel_type` | `text` | Indicates how the SR was submitted to 311.  i.e. By Phone, Online, Mobile, Other or Unknown. |
| **Park Facility Name** | `park_facility_name` | `text` | If the incident location is a Parks Dept facility, the Name of the facility will appear here |
| **Park Borough** | `park_borough` | `text` | The borough of incident if it is a Parks Dept facility |
| **Vehicle Type** | `vehicle_type` | `text` | If the incident is a taxi, this field describes the type of TLC vehicle. |
| **Taxi Company Borough** | `taxi_company_borough` | `text` | If the incident is identified as a taxi, this field will display the borough of the taxi company. |
| **Taxi Pick Up Location** | `taxi_pick_up_location` | `text` | If the incident is identified as a taxi, this field displays the taxi pick up location |
| **Bridge Highway Name** | `bridge_highway_name` | `text` | If the incident is identified as a Bridge/Highway, the name will be displayed here. |
| **Bridge Highway Direction** | `bridge_highway_direction` | `text` | If the incident is identified as a Bridge/Highway, the direction where the issue took place would be displayed here. |
| **Road Ramp** | `road_ramp` | `text` | If the incident location was Bridge/Highway this column differentiates if the issue was on the Road or the Ramp. |
| **Bridge Highway Segment** | `bridge_highway_segment` | `text` | Additional information on the section of the Bridge/Highway were the incident took place. |
| **Latitude** | `latitude` | `number` | Geo based Lat of the incident location |
| **Longitude** | `longitude` | `number` | Geo based Long of the incident location |
| **Location** | `location` | `point` | Combination of the geo based lat & long of the incident location |
| **Community Districts** | `:@computed_region_f5dn_yrer` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Community Districts' (f5dn-yrer) the point in column 'location' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **Borough Boundaries** | `:@computed_region_yeji_bk3q` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Borough Boundaries' (yeji-bk3q) the point in column 'location' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **Police Precincts** | `:@computed_region_sbqj_enih` | `number` | This column was automatically created in order to record in what polygon from the dataset 'Police Precincts' (sbqj-enih) the point in column 'location' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |
| **City Council Districts** | `:@computed_region_92fq_4b7q` | `number` | This column was automatically created in order to record in what polygon from the dataset 'City Council Districts' (92fq-4b7q) the point in column 'location' is located.  This enables the creation of region maps (choropleths) in the visualization canvas and data lens. |

---

---

## 🛠️ Automated Discovery Workflow

To discover and integrate a new dataset, run:
```bash
python scripts/discover_socrata.py --id [FOUR-FOUR]
```
