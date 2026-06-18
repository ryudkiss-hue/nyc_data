-- ============================================================================
-- Phase 1B: Staging Schema - Deduplication & Type Casting (Auto-generated)
-- ============================================================================
-- Generated from pipeline/config/socrata_datasets.json
-- Uses actual primary_key from config for each dataset
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE TABLE staging.inspection AS
SELECT * FROM raw.inspection
QUALIFY ROW_NUMBER() OVER (PARTITION BY inspection_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.capital_intersections AS
SELECT * FROM raw.capital_intersections
QUALIFY ROW_NUMBER() OVER (PARTITION BY intersection_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.built AS
SELECT * FROM raw.built
QUALIFY ROW_NUMBER() OVER (PARTITION BY lot_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.pedestrian_demand AS
SELECT * FROM raw.pedestrian_demand
QUALIFY ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.mappluto AS
SELECT * FROM raw.mappluto
QUALIFY ROW_NUMBER() OVER (PARTITION BY bblid ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.capital_blocks AS
SELECT * FROM raw.capital_blocks
QUALIFY ROW_NUMBER() OVER (PARTITION BY block_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.tree_damage AS
SELECT * FROM raw.tree_damage
QUALIFY ROW_NUMBER() OVER (PARTITION BY tree_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.correspondences AS
SELECT * FROM raw.correspondences
QUALIFY ROW_NUMBER() OVER (PARTITION BY correspondence_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.step_streets AS
SELECT * FROM raw.step_streets
QUALIFY ROW_NUMBER() OVER (PARTITION BY step_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.curb_metal_protruding AS
SELECT * FROM raw.curb_metal_protruding
QUALIFY ROW_NUMBER() OVER (PARTITION BY violation_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.lot_info AS
SELECT * FROM raw.lot_info
QUALIFY ROW_NUMBER() OVER (PARTITION BY lot_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.ramp_complaints AS
SELECT * FROM raw.ramp_complaints
QUALIFY ROW_NUMBER() OVER (PARTITION BY complaint_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.ramp_locations AS
SELECT * FROM raw.ramp_locations
QUALIFY ROW_NUMBER() OVER (PARTITION BY ramp_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.ramp_progress AS
SELECT * FROM raw.ramp_progress
QUALIFY ROW_NUMBER() OVER (PARTITION BY progress_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.reinspection AS
SELECT * FROM raw.reinspection
QUALIFY ROW_NUMBER() OVER (PARTITION BY reinspection_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.street_closures_block AS
SELECT * FROM raw.street_closures_block
QUALIFY ROW_NUMBER() OVER (PARTITION BY closure_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.sidewalk_planimetric AS
SELECT * FROM raw.sidewalk_planimetric
QUALIFY ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.street_resurfacing_schedule AS
SELECT * FROM raw.street_resurfacing_schedule
QUALIFY ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.violations AS
SELECT * FROM raw.violations
QUALIFY ROW_NUMBER() OVER (PARTITION BY violation_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.weekly_construction AS
SELECT * FROM raw.weekly_construction
QUALIFY ROW_NUMBER() OVER (PARTITION BY construction_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.inspection_history AS
SELECT * FROM raw.inspection_history
QUALIFY ROW_NUMBER() OVER (PARTITION BY history_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.inspection_metrics AS
SELECT * FROM raw.inspection_metrics
QUALIFY ROW_NUMBER() OVER (PARTITION BY metric_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.violation_photos AS
SELECT * FROM raw.violation_photos
QUALIFY ROW_NUMBER() OVER (PARTITION BY photo_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.violation_attachments AS
SELECT * FROM raw.violation_attachments
QUALIFY ROW_NUMBER() OVER (PARTITION BY attachment_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.ramp_inventory AS
SELECT * FROM raw.ramp_inventory
QUALIFY ROW_NUMBER() OVER (PARTITION BY inventory_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.ramp_specifications AS
SELECT * FROM raw.ramp_specifications
QUALIFY ROW_NUMBER() OVER (PARTITION BY spec_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.ramp_maintenance_log AS
SELECT * FROM raw.ramp_maintenance_log
QUALIFY ROW_NUMBER() OVER (PARTITION BY log_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.permit_status_history AS
SELECT * FROM raw.permit_status_history
QUALIFY ROW_NUMBER() OVER (PARTITION BY status_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.permit_amendments AS
SELECT * FROM raw.permit_amendments
QUALIFY ROW_NUMBER() OVER (PARTITION BY amendment_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.construction_progress AS
SELECT * FROM raw.construction_progress
QUALIFY ROW_NUMBER() OVER (PARTITION BY progress_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.street_segment_inventory AS
SELECT * FROM raw.street_segment_inventory
QUALIFY ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.block_face_data AS
SELECT * FROM raw.block_face_data
QUALIFY ROW_NUMBER() OVER (PARTITION BY face_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.spatial_geometry AS
SELECT * FROM raw.spatial_geometry
QUALIFY ROW_NUMBER() OVER (PARTITION BY geom_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.tree_inventory AS
SELECT * FROM raw.tree_inventory
QUALIFY ROW_NUMBER() OVER (PARTITION BY tree_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.tree_maintenance AS
SELECT * FROM raw.tree_maintenance
QUALIFY ROW_NUMBER() OVER (PARTITION BY maintenance_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.curb_inventory AS
SELECT * FROM raw.curb_inventory
QUALIFY ROW_NUMBER() OVER (PARTITION BY curb_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.surface_condition_history AS
SELECT * FROM raw.surface_condition_history
QUALIFY ROW_NUMBER() OVER (PARTITION BY condition_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.project_scheduling AS
SELECT * FROM raw.project_scheduling
QUALIFY ROW_NUMBER() OVER (PARTITION BY schedule_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.project_budget AS
SELECT * FROM raw.project_budget
QUALIFY ROW_NUMBER() OVER (PARTITION BY budget_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.project_resources AS
SELECT * FROM raw.project_resources
QUALIFY ROW_NUMBER() OVER (PARTITION BY resource_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.vendor_data AS
SELECT * FROM raw.vendor_data
QUALIFY ROW_NUMBER() OVER (PARTITION BY vendor_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.equipment_inventory AS
SELECT * FROM raw.equipment_inventory
QUALIFY ROW_NUMBER() OVER (PARTITION BY equipment_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.safety_incidents AS
SELECT * FROM raw.safety_incidents
QUALIFY ROW_NUMBER() OVER (PARTITION BY incident_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.environmental_compliance AS
SELECT * FROM raw.environmental_compliance
QUALIFY ROW_NUMBER() OVER (PARTITION BY compliance_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.traffic_impact AS
SELECT * FROM raw.traffic_impact
QUALIFY ROW_NUMBER() OVER (PARTITION BY impact_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.noise_monitoring AS
SELECT * FROM raw.noise_monitoring
QUALIFY ROW_NUMBER() OVER (PARTITION BY noise_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.air_quality AS
SELECT * FROM raw.air_quality
QUALIFY ROW_NUMBER() OVER (PARTITION BY quality_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.public_complaints AS
SELECT * FROM raw.public_complaints
QUALIFY ROW_NUMBER() OVER (PARTITION BY complaint_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.community_outreach AS
SELECT * FROM raw.community_outreach
QUALIFY ROW_NUMBER() OVER (PARTITION BY outreach_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.contractor_performance AS
SELECT * FROM raw.contractor_performance
QUALIFY ROW_NUMBER() OVER (PARTITION BY performance_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.cost_tracking AS
SELECT * FROM raw.cost_tracking
QUALIFY ROW_NUMBER() OVER (PARTITION BY cost_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.funding_sources AS
SELECT * FROM raw.funding_sources
QUALIFY ROW_NUMBER() OVER (PARTITION BY fund_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.regulatory_approvals AS
SELECT * FROM raw.regulatory_approvals
QUALIFY ROW_NUMBER() OVER (PARTITION BY approval_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.accessibility_audits AS
SELECT * FROM raw.accessibility_audits
QUALIFY ROW_NUMBER() OVER (PARTITION BY audit_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.service_requests AS
SELECT * FROM raw.service_requests
QUALIFY ROW_NUMBER() OVER (PARTITION BY request_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.performance_metrics AS
SELECT * FROM raw.performance_metrics
QUALIFY ROW_NUMBER() OVER (PARTITION BY metric_id ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging.stakeholder_feedback AS
SELECT * FROM raw.stakeholder_feedback
QUALIFY ROW_NUMBER() OVER (PARTITION BY feedback_id ORDER BY 1 DESC) = 1;
