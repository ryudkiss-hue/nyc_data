-- Stage 3: ANALYTICS - 5 Domain Schemas
-- sim_core, accessibility, coordination, overlays, extended
-- 100+ views with proper relationships and join keys

-- Create domain schemas
CREATE SCHEMA IF NOT EXISTS sim_core;
CREATE SCHEMA IF NOT EXISTS accessibility;
CREATE SCHEMA IF NOT EXISTS coordination;
CREATE SCHEMA IF NOT EXISTS overlays;
CREATE SCHEMA IF NOT EXISTS extended;

-- sim_core: Core inspection & management
-- Key tables: inspection, reinspection, inspection_history
-- Primary join key: inspection_id

-- accessibility: ADA & accessibility violations
-- Key tables: violations (accessibility-focused), ramp_locations, ramp_complaints, ramp_progress
-- Primary join key: ramp_id

-- coordination: Permit coordination & intersections
-- Key tables: capital_intersections, capital_blocks, correspondences, street_closures_block
-- Primary join key: lot_id, block_id

-- overlays: Spatial enrichment & tree data
-- Key tables: mappluto, sidewalk_planimetric, tree_damage, curb_metal_protruding
-- Primary join key: lot_id, bblid (Building Block Lot ID)

-- extended: Derived metrics & time-series
-- Key tables: street_resurfacing_schedule, built, pedestrian_demand, step_streets
-- Computed columns: trends, aggregations, rates

-- Example view: sim_core.inspections_detailed
-- CREATE OR REPLACE VIEW sim_core.inspections_detailed AS
-- SELECT
--     i.inspection_id,
--     i.inspection_date,
--     i.location,
--     r.reinspection_date,
--     COUNT(v.violation_id) as violation_count,
--     bool_or(v.accessibility_related) as has_accessibility_issues
-- FROM staging.inspection i
-- LEFT JOIN staging.reinspection r USING (inspection_id)
-- LEFT JOIN staging.violations v ON i.inspection_id = v.inspection_id
-- GROUP BY i.inspection_id, i.inspection_date, i.location, r.reinspection_date;

-- Relationship verification
-- SELECT
--     'join_key_validation' as check_type,
--     COUNT(DISTINCT inspection_id) as unique_keys,
--     COUNT(*) as total_rows
-- FROM staging.inspection
-- HAVING COUNT(DISTINCT inspection_id) = COUNT(*);
