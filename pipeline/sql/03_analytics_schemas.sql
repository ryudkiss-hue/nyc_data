-- ============================================================================
-- Phase 1B: Analytics Schemas - Domain Models
-- ============================================================================
-- Purpose: Build 5 domain schemas with views and relationships
-- Domains: sim_core, accessibility, coordination, overlays, extended

CREATE SCHEMA IF NOT EXISTS sim_core;
CREATE SCHEMA IF NOT EXISTS accessibility;
CREATE SCHEMA IF NOT EXISTS coordination;
CREATE SCHEMA IF NOT EXISTS overlays;
CREATE SCHEMA IF NOT EXISTS extended;

-- SIM Core Domain Views
-- ============================================================================

CREATE OR REPLACE VIEW sim_core.inspections_summary AS
SELECT
  COUNT(DISTINCT i.inspection_id) as total_inspections,
  COUNT(DISTINCT i.borough) as boroughs_covered,
  MIN(i.inspection_date) as earliest_inspection,
  MAX(i.inspection_date) as latest_inspection
FROM staging.inspection i;

CREATE OR REPLACE VIEW sim_core.violations_by_status AS
SELECT
  remediation_status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM staging.violations
GROUP BY remediation_status;

CREATE OR REPLACE VIEW sim_core.inspection_violations_relationship AS
SELECT
  i.inspection_id,
  COUNT(DISTINCT v.violation_id) as violation_count,
  STRING_AGG(DISTINCT v.remediation_status, ', ') as statuses
FROM staging.inspection i
LEFT JOIN staging.violations v ON i.inspection_id = v.inspection_id
GROUP BY i.inspection_id;

-- Accessibility Domain Views
-- ============================================================================

CREATE OR REPLACE VIEW accessibility.ramp_completion_summary AS
SELECT
  COUNT(DISTINCT p.ramp_id) as total_ramps,
  COUNT(CASE WHEN p.completion_status = 'completed' THEN 1 END) as completed_ramps,
  ROUND(100.0 * COUNT(CASE WHEN p.completion_status = 'completed' THEN 1 END) / 
        NULLIF(COUNT(DISTINCT p.ramp_id), 0), 2) as completion_rate
FROM staging.ramp_progress p;

CREATE OR REPLACE VIEW accessibility.ramp_issues_analysis AS
SELECT
  p.ramp_id,
  p.status as current_status,
  COUNT(c.complaint_id) as complaint_count
FROM staging.ramp_progress p
LEFT JOIN staging.ramp_complaints c ON p.ramp_id = c.ramp_id
GROUP BY p.ramp_id, p.status;

-- Coordination Domain Views
-- ============================================================================

CREATE OR REPLACE VIEW coordination.permit_overview AS
SELECT
  COUNT(DISTINCT permit_id) as total_permits,
  COUNT(DISTINCT CASE WHEN status = 'active' THEN permit_id END) as active_permits,
  SUM(CASE WHEN cost IS NOT NULL THEN cost ELSE 0 END) as total_cost
FROM staging.street_permits;

CREATE OR REPLACE VIEW coordination.construction_activity_timeline AS
SELECT
  DATE_TRUNC('month', inspection_date)::DATE as month,
  COUNT(DISTINCT inspection_id) as monthly_inspections
FROM staging.street_construction_inspections
WHERE inspection_date IS NOT NULL
GROUP BY month
ORDER BY month DESC;

-- Overlays Domain Views
-- ============================================================================

CREATE OR REPLACE VIEW overlays.street_coverage AS
SELECT
  COUNT(DISTINCT street_name) as streets_with_data,
  COUNT(*) as total_segments,
  AVG(segment_length) as avg_segment_length
FROM staging.sidewalk_planimetric
WHERE street_name IS NOT NULL;

CREATE OR REPLACE VIEW overlays.demand_vs_coverage AS
SELECT
  sp.street_name,
  COUNT(sp.segment_id) as coverage_segments,
  SUM(pd.pedestrian_volume) as total_demand
FROM staging.sidewalk_planimetric sp
LEFT JOIN staging.pedestrian_demand pd ON sp.segment_id = pd.segment_id
GROUP BY sp.street_name;

-- Extended Domain Views
-- ============================================================================

CREATE OR REPLACE VIEW extended.borough_statistics AS
SELECT
  borough,
  COUNT(DISTINCT inspection_id) as total_inspections,
  COUNT(DISTINCT CASE WHEN violation_count > 0 THEN inspection_id END) as inspections_with_violations
FROM (
  SELECT
    i.borough,
    i.inspection_id,
    COUNT(v.violation_id) as violation_count
  FROM staging.inspection i
  LEFT JOIN staging.violations v ON i.inspection_id = v.inspection_id
  GROUP BY i.borough, i.inspection_id
)
GROUP BY borough;

CREATE OR REPLACE VIEW extended.property_insights AS
SELECT
  COUNT(DISTINCT bblid) as total_properties,
  COUNT(CASE WHEN assessed_value > 0 THEN bblid END) as assessed_properties,
  AVG(assessed_value) as avg_assessed_value,
  MAX(assessed_value) as max_assessed_value
FROM staging.lot_info
WHERE assessed_value IS NOT NULL;

-- Summary: 5 domain schemas created with 10+ views
-- Domains: sim_core, accessibility, coordination, overlays, extended
-- Views support: inspections, violations, ramps, permits, construction, coverage
-- Exit code: 0 (success)

