-- ============================================================================
-- Phase 1B: Verification Gates - Real Data Quality Validation
-- ============================================================================
-- 4 mandatory gates with actual data checks (not hardcoded values)
-- All gates must PASS for pipeline to succeed (exit code enforcement)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS verification;

-- GATE 1: Data Load Verification
-- Validates that raw ingestion loaded minimum expected row counts
CREATE OR REPLACE TABLE verification.gate_1_data_load AS
WITH raw_table_counts AS (
  SELECT
    table_name,
    CAST(
      (SELECT COUNT(*) FROM information_schema.tables
       WHERE table_schema = 'raw' AND table_type = 'BASE TABLE') AS INTEGER
    ) as raw_table_count,
    CAST(
      (SELECT SUM(CAST(row_count AS BIGINT))
       FROM information_schema.tables
       WHERE table_schema = 'raw' AND table_type = 'BASE TABLE') AS BIGINT
    ) as total_rows
  FROM information_schema.tables
  WHERE table_schema = 'raw'
  LIMIT 1
)
SELECT
  'gate_1_data_load' as gate_name,
  CASE
    WHEN raw_table_count = 0 THEN 'FAIL'
    WHEN total_rows = 0 THEN 'FAIL'
    WHEN total_rows < 100000 THEN 'WARN'
    ELSE 'PASS'
  END as status,
  raw_table_count as tables_loaded,
  total_rows as raw_row_count,
  CURRENT_TIMESTAMP as verified_at;

-- GATE 2: Staging Schema Validation
CREATE OR REPLACE TABLE verification.gate_2_schema_validation AS
WITH staging_checks AS (
  SELECT
    COUNT(DISTINCT table_name) as staging_table_count
  FROM information_schema.columns
  WHERE table_schema = 'staging'
)
SELECT
  'gate_2_schema_validation' as gate_name,
  CASE
    WHEN staging_table_count = 0 THEN 'FAIL'
    WHEN staging_table_count < 20 THEN 'WARN'
    ELSE 'PASS'
  END as status,
  staging_table_count,
  CURRENT_TIMESTAMP as verified_at
FROM staging_checks;

-- GATE 3: KPI Materialization Validation
CREATE OR REPLACE TABLE verification.gate_3_kpi_materialization AS
SELECT
  'gate_3_kpi_materialization' as gate_name,
  CASE
    WHEN (SELECT COUNT(*) FROM serving.kpi_borough_results) = 0 THEN 'FAIL'
    WHEN (SELECT COUNT(*) FROM serving.kpi_borough_results) < 255 THEN 'WARN'
    ELSE 'PASS'
  END as status,
  (SELECT COUNT(*) FROM serving.kpi_borough_results) as kpi_records,
  255 as expected_records,
  CURRENT_TIMESTAMP as verified_at;

-- GATE 4: No Silent Failures - Cross-stage consistency
CREATE OR REPLACE TABLE verification.gate_4_consistency AS
WITH stage_rows AS (
  SELECT
    COALESCE((SELECT SUM(CAST(row_count AS BIGINT)) FROM information_schema.tables WHERE table_schema = 'raw'), 0) as raw_rows,
    COALESCE((SELECT SUM(CAST(row_count AS BIGINT)) FROM information_schema.tables WHERE table_schema = 'staging'), 0) as staging_rows
)
SELECT
  'gate_4_consistency' as gate_name,
  CASE
    WHEN raw_rows = 0 THEN 'FAIL'
    WHEN staging_rows = 0 THEN 'FAIL'
    WHEN staging_rows > raw_rows THEN 'FAIL'
    ELSE 'PASS'
  END as status,
  raw_rows,
  staging_rows,
  CURRENT_TIMESTAMP as verified_at
FROM stage_rows;

-- GATE 5: Per-Dataset Validation (all 57 datasets)
-- Validates that each dataset has been loaded with minimum rows
CREATE OR REPLACE TABLE verification.gate_5_dataset_validation AS
WITH dataset_counts AS (
  SELECT 'inspection' as dataset_key, COUNT(*) as row_count FROM raw.inspection
  UNION ALL SELECT 'capital_intersections', COUNT(*) FROM raw.capital_intersections
  UNION ALL SELECT 'built', COUNT(*) FROM raw.built
  UNION ALL SELECT 'pedestrian_demand', COUNT(*) FROM raw.pedestrian_demand
  UNION ALL SELECT 'mappluto', COUNT(*) FROM raw.mappluto
  UNION ALL SELECT 'capital_blocks', COUNT(*) FROM raw.capital_blocks
  UNION ALL SELECT 'tree_damage', COUNT(*) FROM raw.tree_damage
  UNION ALL SELECT 'correspondences', COUNT(*) FROM raw.correspondences
  UNION ALL SELECT 'step_streets', COUNT(*) FROM raw.step_streets
  UNION ALL SELECT 'curb_metal_protruding', COUNT(*) FROM raw.curb_metal_protruding
  UNION ALL SELECT 'lot_info', COUNT(*) FROM raw.lot_info
  UNION ALL SELECT 'ramp_complaints', COUNT(*) FROM raw.ramp_complaints
  UNION ALL SELECT 'ramp_locations', COUNT(*) FROM raw.ramp_locations
  UNION ALL SELECT 'ramp_progress', COUNT(*) FROM raw.ramp_progress
  UNION ALL SELECT 'reinspection', COUNT(*) FROM raw.reinspection
  UNION ALL SELECT 'street_closures_block', COUNT(*) FROM raw.street_closures_block
  UNION ALL SELECT 'sidewalk_planimetric', COUNT(*) FROM raw.sidewalk_planimetric
  UNION ALL SELECT 'street_resurfacing_schedule', COUNT(*) FROM raw.street_resurfacing_schedule
  UNION ALL SELECT 'violations', COUNT(*) FROM raw.violations
  UNION ALL SELECT 'weekly_construction', COUNT(*) FROM raw.weekly_construction
  UNION ALL SELECT 'inspection_history', COUNT(*) FROM raw.inspection_history
  UNION ALL SELECT 'inspection_metrics', COUNT(*) FROM raw.inspection_metrics
  UNION ALL SELECT 'violation_photos', COUNT(*) FROM raw.violation_photos
  UNION ALL SELECT 'violation_attachments', COUNT(*) FROM raw.violation_attachments
  UNION ALL SELECT 'ramp_inventory', COUNT(*) FROM raw.ramp_inventory
  UNION ALL SELECT 'ramp_specifications', COUNT(*) FROM raw.ramp_specifications
  UNION ALL SELECT 'ramp_maintenance_log', COUNT(*) FROM raw.ramp_maintenance_log
  UNION ALL SELECT 'permit_status_history', COUNT(*) FROM raw.permit_status_history
  UNION ALL SELECT 'permit_amendments', COUNT(*) FROM raw.permit_amendments
  UNION ALL SELECT 'construction_progress', COUNT(*) FROM raw.construction_progress
  UNION ALL SELECT 'street_segment_inventory', COUNT(*) FROM raw.street_segment_inventory
  UNION ALL SELECT 'block_face_data', COUNT(*) FROM raw.block_face_data
  UNION ALL SELECT 'spatial_geometry', COUNT(*) FROM raw.spatial_geometry
  UNION ALL SELECT 'tree_inventory', COUNT(*) FROM raw.tree_inventory
  UNION ALL SELECT 'tree_maintenance', COUNT(*) FROM raw.tree_maintenance
  UNION ALL SELECT 'curb_inventory', COUNT(*) FROM raw.curb_inventory
  UNION ALL SELECT 'surface_condition_history', COUNT(*) FROM raw.surface_condition_history
  UNION ALL SELECT 'project_scheduling', COUNT(*) FROM raw.project_scheduling
  UNION ALL SELECT 'project_budget', COUNT(*) FROM raw.project_budget
  UNION ALL SELECT 'project_resources', COUNT(*) FROM raw.project_resources
  UNION ALL SELECT 'vendor_data', COUNT(*) FROM raw.vendor_data
  UNION ALL SELECT 'equipment_inventory', COUNT(*) FROM raw.equipment_inventory
  UNION ALL SELECT 'safety_incidents', COUNT(*) FROM raw.safety_incidents
  UNION ALL SELECT 'environmental_compliance', COUNT(*) FROM raw.environmental_compliance
  UNION ALL SELECT 'traffic_impact', COUNT(*) FROM raw.traffic_impact
  UNION ALL SELECT 'noise_monitoring', COUNT(*) FROM raw.noise_monitoring
  UNION ALL SELECT 'air_quality', COUNT(*) FROM raw.air_quality
  UNION ALL SELECT 'public_complaints', COUNT(*) FROM raw.public_complaints
  UNION ALL SELECT 'community_outreach', COUNT(*) FROM raw.community_outreach
  UNION ALL SELECT 'contractor_performance', COUNT(*) FROM raw.contractor_performance
  UNION ALL SELECT 'cost_tracking', COUNT(*) FROM raw.cost_tracking
  UNION ALL SELECT 'funding_sources', COUNT(*) FROM raw.funding_sources
  UNION ALL SELECT 'regulatory_approvals', COUNT(*) FROM raw.regulatory_approvals
  UNION ALL SELECT 'accessibility_audits', COUNT(*) FROM raw.accessibility_audits
  UNION ALL SELECT 'service_requests', COUNT(*) FROM raw.service_requests
  UNION ALL SELECT 'performance_metrics', COUNT(*) FROM raw.performance_metrics
  UNION ALL SELECT 'stakeholder_feedback', COUNT(*) FROM raw.stakeholder_feedback
),
dataset_status AS (
  SELECT
    dataset_key,
    row_count,
    CASE
      WHEN row_count = 0 THEN 'FAIL'
      WHEN row_count < 100 THEN 'WARN'
      ELSE 'PASS'
    END as status
  FROM dataset_counts
)
SELECT
  'gate_5_dataset_validation' as gate_name,
  CASE
    WHEN COUNT(CASE WHEN status = 'FAIL' THEN 1 END) > 0 THEN 'FAIL'
    WHEN COUNT(CASE WHEN status = 'WARN' THEN 1 END) > 0 THEN 'WARN'
    ELSE 'PASS'
  END as status,
  COUNT(*) as datasets_checked,
  COUNT(CASE WHEN status = 'PASS' THEN 1 END) as datasets_passed,
  COUNT(CASE WHEN status = 'WARN' THEN 1 END) as datasets_warned,
  COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as datasets_failed,
  CURRENT_TIMESTAMP as verified_at
FROM dataset_status;

-- GATE SUMMARY VIEW (Updated to include Gate 5)
CREATE OR REPLACE VIEW verification.all_gates_summary AS
SELECT
  gate_name,
  status,
  CASE WHEN status = 'PASS' THEN 0 WHEN status = 'WARN' THEN 1 ELSE 2 END as exit_code
FROM (
  SELECT gate_name, status FROM verification.gate_1_data_load
  UNION ALL
  SELECT gate_name, status FROM verification.gate_2_schema_validation
  UNION ALL
  SELECT gate_name, status FROM verification.gate_3_kpi_materialization
  UNION ALL
  SELECT gate_name, status FROM verification.gate_4_consistency
  UNION ALL
  SELECT gate_name, status FROM verification.gate_5_dataset_validation
);
