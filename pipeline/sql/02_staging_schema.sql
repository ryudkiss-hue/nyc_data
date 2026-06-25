-- Staging Schema - AUTO-GENERATED from live columns by regenerate_from_registry.py
-- Do not edit by hand; rerun the regenerator after any registry/data change.
-- Dedup on real natural keys; geometry/keyless tables promoted as-is.

CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE TABLE staging."inspection" AS
SELECT * FROM raw."inspection"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "inspectionid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."violations" AS
SELECT * FROM raw."violations"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "violationid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."reinspection" AS
SELECT * FROM raw."reinspection"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "reinspectionid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."lot_info" AS
SELECT * FROM raw."lot_info"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "bblid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."built" AS
SELECT * FROM raw."built"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "bblid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."dismissals" AS
SELECT * FROM raw."dismissals"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "sr" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."tree_damage" AS
SELECT * FROM raw."tree_damage"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "inspectionid" ORDER BY 1 DESC) = 1;

-- correspondences: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."correspondences" AS SELECT * FROM raw."correspondences";

-- ramp_progress: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."ramp_progress" AS SELECT * FROM raw."ramp_progress";

CREATE OR REPLACE TABLE staging."ramp_complaints" AS
SELECT * FROM raw."ramp_complaints"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "cmt_corner_id" ORDER BY 1 DESC) = 1;

-- ramp_locations: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."ramp_locations" AS SELECT * FROM raw."ramp_locations";

CREATE OR REPLACE TABLE staging."curb_metal_protruding" AS
SELECT * FROM raw."curb_metal_protruding"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "sr" ORDER BY 1 DESC) = 1;

-- step_streets: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."step_streets" AS SELECT * FROM raw."step_streets";

CREATE OR REPLACE TABLE staging."street_resurfacing_schedule" AS
SELECT * FROM raw."street_resurfacing_schedule"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "workscheduleprojectlocationid" ORDER BY 1 DESC) = 1;

-- weekly_construction: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."weekly_construction" AS SELECT * FROM raw."weekly_construction";

-- pedestrian_demand: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."pedestrian_demand" AS SELECT * FROM raw."pedestrian_demand";

-- vzv_enhanced_crossings: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_enhanced_crossings" AS SELECT * FROM raw."vzv_enhanced_crossings";

-- holiday_construction_embargo_intersection: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."holiday_construction_embargo_intersection" AS SELECT * FROM raw."holiday_construction_embargo_intersection";

-- vzv_street_improvement_projects_sip_corridor: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_street_improvement_projects_sip_corridor" AS SELECT * FROM raw."vzv_street_improvement_projects_sip_corridor";

-- bi_annual_pedestrian_counts: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."bi_annual_pedestrian_counts" AS SELECT * FROM raw."bi_annual_pedestrian_counts";

CREATE OR REPLACE TABLE staging."bikes_in_buildings_requests" AS
SELECT * FROM raw."bikes_in_buildings_requests"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "requestid" ORDER BY 1 DESC) = 1;

-- vzv_priority_intersections: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_priority_intersections" AS SELECT * FROM raw."vzv_priority_intersections";

-- street_pavement_ratings: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."street_pavement_ratings" AS SELECT * FROM raw."street_pavement_ratings";

-- vzv_bike_priority_areas: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_bike_priority_areas" AS SELECT * FROM raw."vzv_bike_priority_areas";

-- accessible_pedestrian_signal_locations: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."accessible_pedestrian_signal_locations" AS SELECT * FROM raw."accessible_pedestrian_signal_locations";

-- parking_permit_for_people_with_disabilities_pppd: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."parking_permit_for_people_with_disabilities_pppd" AS SELECT * FROM raw."parking_permit_for_people_with_disabilities_pppd";

-- vzv_leading_pedestrian_interval_signals: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_leading_pedestrian_interval_signals" AS SELECT * FROM raw."vzv_leading_pedestrian_interval_signals";

-- seating_locations: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."seating_locations" AS SELECT * FROM raw."seating_locations";

-- vzv_safe_streets_for_seniors: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_safe_streets_for_seniors" AS SELECT * FROM raw."vzv_safe_streets_for_seniors";

-- exclusive_pedestrian_signal_barnes_dance_locatio: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."exclusive_pedestrian_signal_barnes_dance_locatio" AS SELECT * FROM raw."exclusive_pedestrian_signal_barnes_dance_locatio";

-- street_direction_change_requests_2019_present: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."street_direction_change_requests_2019_present" AS SELECT * FROM raw."street_direction_change_requests_2019_present";

-- vzv_street_improvement_projects_sip_intersection: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_street_improvement_projects_sip_intersection" AS SELECT * FROM raw."vzv_street_improvement_projects_sip_intersection";

-- street_construction_permits_cranes: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."street_construction_permits_cranes" AS SELECT * FROM raw."street_construction_permits_cranes";

-- bicycle_parking_shelters: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."bicycle_parking_shelters" AS SELECT * FROM raw."bicycle_parking_shelters";

-- protected_streets_intersection_dataset: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."protected_streets_intersection_dataset" AS SELECT * FROM raw."protected_streets_intersection_dataset";

CREATE OR REPLACE TABLE staging."bicycle_and_pedestrian_count_sensors" AS
SELECT * FROM raw."bicycle_and_pedestrian_count_sensors"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "id" ORDER BY 1 DESC) = 1;

-- nyc_dot_pedestrian_plazas_point_feature: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."nyc_dot_pedestrian_plazas_point_feature" AS SELECT * FROM raw."nyc_dot_pedestrian_plazas_point_feature";

-- shared_e_scooter_parking_corrals: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."shared_e_scooter_parking_corrals" AS SELECT * FROM raw."shared_e_scooter_parking_corrals";

-- pedestrian_space_added: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."pedestrian_space_added" AS SELECT * FROM raw."pedestrian_space_added";

-- parking_permit_for_people_with_disabilities_pppd_2: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."parking_permit_for_people_with_disabilities_pppd_2" AS SELECT * FROM raw."parking_permit_for_people_with_disabilities_pppd_2";

-- street_closures_due_to_construction_activities_b: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."street_closures_due_to_construction_activities_b" AS SELECT * FROM raw."street_closures_due_to_construction_activities_b";

-- vzv_street_team_flyers: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_street_team_flyers" AS SELECT * FROM raw."vzv_street_team_flyers";

CREATE OR REPLACE TABLE staging."intercity_bus_stop_permits" AS
SELECT * FROM raw."intercity_bus_stop_permits"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "applicationtrackingid" ORDER BY 1 DESC) = 1;

-- street_closures_due_to_construction_activities_b_2: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."street_closures_due_to_construction_activities_b_2" AS SELECT * FROM raw."street_closures_due_to_construction_activities_b_2";

-- open_streets_locations: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."open_streets_locations" AS SELECT * FROM raw."open_streets_locations";

-- parking_meters_parknyc_block_faces: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."parking_meters_parknyc_block_faces" AS SELECT * FROM raw."parking_meters_parknyc_block_faces";

CREATE OR REPLACE TABLE staging."dot_in_house_street_resurfacing_projects" AS
SELECT * FROM raw."dot_in_house_street_resurfacing_projects"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "project_id" ORDER BY 1 DESC) = 1;

-- protected_streets_block_dataset: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."protected_streets_block_dataset" AS SELECT * FROM raw."protected_streets_block_dataset";

-- bicycle_parking: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."bicycle_parking" AS SELECT * FROM raw."bicycle_parking";

-- street_closures_due_to_construction_activities_b_3: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."street_closures_due_to_construction_activities_b_3" AS SELECT * FROM raw."street_closures_due_to_construction_activities_b_3";

-- bus_lanes_local_streets: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."bus_lanes_local_streets" AS SELECT * FROM raw."bus_lanes_local_streets";

-- street_pothole_work_orders_closed_dataset: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."street_pothole_work_orders_closed_dataset" AS SELECT * FROM raw."street_pothole_work_orders_closed_dataset";

-- new_york_city_bike_routes: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."new_york_city_bike_routes" AS SELECT * FROM raw."new_york_city_bike_routes";

-- carshare_locations_curbside: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."carshare_locations_curbside" AS SELECT * FROM raw."carshare_locations_curbside";

-- street_and_highway_capital_reconstruction_projec: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."street_and_highway_capital_reconstruction_projec" AS SELECT * FROM raw."street_and_highway_capital_reconstruction_projec";

-- temporary_parking_permit_for_people_with_disabil: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."temporary_parking_permit_for_people_with_disabil" AS SELECT * FROM raw."temporary_parking_permit_for_people_with_disabil";

-- street_seats_2021_2024: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."street_seats_2021_2024" AS SELECT * FROM raw."street_seats_2021_2024";

-- holiday_construction_embargo_block: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."holiday_construction_embargo_block" AS SELECT * FROM raw."holiday_construction_embargo_block";

-- street_and_highway_capital_reconstruction_projec_2: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."street_and_highway_capital_reconstruction_projec_2" AS SELECT * FROM raw."street_and_highway_capital_reconstruction_projec_2";

-- street_network_changes: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."street_network_changes" AS SELECT * FROM raw."street_network_changes";

CREATE OR REPLACE TABLE staging."newsrack_inspections" AS
SELECT * FROM raw."newsrack_inspections"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "newsracklocationid" ORDER BY 1 DESC) = 1;

-- nyc_dot_pedestrian_plazas_polygon: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."nyc_dot_pedestrian_plazas_polygon" AS SELECT * FROM raw."nyc_dot_pedestrian_plazas_polygon";

CREATE OR REPLACE TABLE staging."encroachments_and_defacements" AS
SELECT * FROM raw."encroachments_and_defacements"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "complaintid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."complaints_311" AS
SELECT * FROM raw."complaints_311"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "unique_key" ORDER BY 1 DESC) = 1;

-- street_centerline: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."street_centerline" AS SELECT * FROM raw."street_centerline";

-- nta_2020: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."nta_2020" AS SELECT * FROM raw."nta_2020";

-- census_demographics_nta: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."census_demographics_nta" AS SELECT * FROM raw."census_demographics_nta";

-- heat_vulnerability_index: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."heat_vulnerability_index" AS SELECT * FROM raw."heat_vulnerability_index";

CREATE OR REPLACE TABLE staging."motor_vehicle_collisions_crashes" AS
SELECT * FROM raw."motor_vehicle_collisions_crashes"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "collision_id" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."motor_vehicle_collisions_person" AS
SELECT * FROM raw."motor_vehicle_collisions_person"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "unique_id" ORDER BY 1 DESC) = 1;

-- sidewalk_cafes: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."sidewalk_cafes" AS SELECT * FROM raw."sidewalk_cafes";

CREATE OR REPLACE TABLE staging."street_tree_census_2015" AS
SELECT * FROM raw."street_tree_census_2015"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "tree_id" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."forestry_inspections" AS
SELECT * FROM raw."forestry_inspections"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "objectid" ORDER BY 1 DESC) = 1;

-- water_sewer_permits: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."water_sewer_permits" AS SELECT * FROM raw."water_sewer_permits";

CREATE OR REPLACE TABLE staging."street_construction_permits" AS
SELECT * FROM raw."street_construction_permits"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "applicationtrackingid" ORDER BY 1 DESC) = 1;

-- dob_stalled_construction_sites: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."dob_stalled_construction_sites" AS SELECT * FROM raw."dob_stalled_construction_sites";

-- sidewalk_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."sidewalk_planimetric" AS SELECT * FROM raw."sidewalk_planimetric";

-- curbs_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."curbs_planimetric" AS SELECT * FROM raw."curbs_planimetric";

-- roadbed_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."roadbed_planimetric" AS SELECT * FROM raw."roadbed_planimetric";

-- median_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."median_planimetric" AS SELECT * FROM raw."median_planimetric";

-- boardwalk_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."boardwalk_planimetric" AS SELECT * FROM raw."boardwalk_planimetric";

-- open_space_parks_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."open_space_parks_planimetric" AS SELECT * FROM raw."open_space_parks_planimetric";

-- elevation_points_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."elevation_points_planimetric" AS SELECT * FROM raw."elevation_points_planimetric";

-- vzv_arterial_slow_zones: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_arterial_slow_zones" AS SELECT * FROM raw."vzv_arterial_slow_zones";

-- vzv_neighborhood_slow_zones: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_neighborhood_slow_zones" AS SELECT * FROM raw."vzv_neighborhood_slow_zones";

-- vzv_priority_corridors: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_priority_corridors" AS SELECT * FROM raw."vzv_priority_corridors";

-- vzv_priority_zones_areas: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_priority_zones_areas" AS SELECT * FROM raw."vzv_priority_zones_areas";

-- vzv_speed_humps: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_speed_humps" AS SELECT * FROM raw."vzv_speed_humps";

CREATE OR REPLACE TABLE staging."speed_reducer_tracking_srts" AS
SELECT * FROM raw."speed_reducer_tracking_srts"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "segmentid" ORDER BY 1 DESC) = 1;

-- vzv_speed_limits: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_speed_limits" AS SELECT * FROM raw."vzv_speed_limits";

-- vzv_turn_traffic_calming: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_turn_traffic_calming" AS SELECT * FROM raw."vzv_turn_traffic_calming";

-- vzv_signal_timing_25mph: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_signal_timing_25mph" AS SELECT * FROM raw."vzv_signal_timing_25mph";

-- vzv_senior_centers: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_senior_centers" AS SELECT * FROM raw."vzv_senior_centers";

-- vzv_workshops_locations: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."vzv_workshops_locations" AS SELECT * FROM raw."vzv_workshops_locations";

-- vision_zero_base_report: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."vision_zero_base_report" AS SELECT * FROM raw."vision_zero_base_report";

CREATE OR REPLACE TABLE staging."raised_crosswalk_locations" AS
SELECT * FROM raw."raised_crosswalk_locations"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "nodeid" ORDER BY 1 DESC) = 1;

-- public_plazas_planimetric: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."public_plazas_planimetric" AS SELECT * FROM raw."public_plazas_planimetric";

-- privately_owned_public_spaces_pops: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."privately_owned_public_spaces_pops" AS SELECT * FROM raw."privately_owned_public_spaces_pops";

-- bus_stop_shelters: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."bus_stop_shelters" AS SELECT * FROM raw."bus_stop_shelters";

-- bicycle_pedestrian_counts (ct66, 20.5M) is ingested as a daily aggregate
-- (raw.bicycle_pedestrian_counts_daily), not staged here. See pipeline/ingest_ct66_daily.py.

-- walk_to_a_park_service_area: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."walk_to_a_park_service_area" AS SELECT * FROM raw."walk_to_a_park_service_area";

-- mbpo_pedestrian_ramp_report: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."mbpo_pedestrian_ramp_report" AS SELECT * FROM raw."mbpo_pedestrian_ramp_report";

CREATE OR REPLACE TABLE staging."capital_projects_dashboard" AS
SELECT * FROM raw."capital_projects_dashboard"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "fms_id" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."cpdb_projects" AS
SELECT * FROM raw."cpdb_projects"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "maprojid" ORDER BY 1 DESC) = 1;

-- cpdb_projects_points: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."cpdb_projects_points" AS SELECT * FROM raw."cpdb_projects_points";

-- cpdb_projects_polygons: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."cpdb_projects_polygons" AS SELECT * FROM raw."cpdb_projects_polygons";

CREATE OR REPLACE TABLE staging."cpdb_commitments" AS
SELECT * FROM raw."cpdb_commitments"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "maprojid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."capital_dashboard_budget_spend_fy" AS
SELECT * FROM raw."capital_dashboard_budget_spend_fy"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "fms_id" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."capital_dashboard_spend_history" AS
SELECT * FROM raw."capital_dashboard_spend_history"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "fms_id" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."capital_dashboard_schedule_history" AS
SELECT * FROM raw."capital_dashboard_schedule_history"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "pid" ORDER BY 1 DESC) = 1;

-- state_of_good_repair_needs: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."state_of_good_repair_needs" AS SELECT * FROM raw."state_of_good_repair_needs";

CREATE OR REPLACE TABLE staging."interagency_coordination_construction_permits" AS
SELECT * FROM raw."interagency_coordination_construction_permits"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "construction_permit_id" ORDER BY 1 DESC) = 1;

-- capital_commitment_plan: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."capital_commitment_plan" AS SELECT * FROM raw."capital_commitment_plan";

-- capital_commitment_actuals: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."capital_commitment_actuals" AS SELECT * FROM raw."capital_commitment_actuals";

-- capital_budget: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."capital_budget" AS SELECT * FROM raw."capital_budget";

CREATE OR REPLACE TABLE staging."capital_project_detail_dollars" AS
SELECT * FROM raw."capital_project_detail_dollars"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "project_id" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."capital_project_detail_milestones" AS
SELECT * FROM raw."capital_project_detail_milestones"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "project_id" ORDER BY 1 DESC) = 1;

-- ten_year_capital_strategy: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."ten_year_capital_strategy" AS SELECT * FROM raw."ten_year_capital_strategy";
