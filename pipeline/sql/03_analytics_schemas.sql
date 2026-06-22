-- ============================================================================
-- Analytics Schemas - REAL domain views (auto-generated 2026-06-22)
-- ============================================================================
-- Computed from staging tables using ACTUAL Socrata columns (verified live).
-- Replaces prior version that referenced invented columns (inspection_id,
-- remediation_status, violation_id) which do not exist in the real data.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS sim_core;
CREATE SCHEMA IF NOT EXISTS accessibility;
CREATE SCHEMA IF NOT EXISTS coordination;

-- SIM Core: Inspection summary -----------------------------------------------
CREATE OR REPLACE VIEW sim_core.inspection_summary AS
SELECT
  COUNT(*)                                                           AS total_inspections,
  COUNT(*) FILTER (WHERE noviolationfound = 'Yes')                   AS no_violation_found,
  ROUND(100.0 * COUNT(*) FILTER (WHERE noviolationfound = 'Yes') / NULLIF(COUNT(*),0), 1) AS pct_no_violation,
  COUNT(*) FILTER (WHERE is_311_inspection = 'Yes')                  AS inspections_311,
  ROUND(100.0 * COUNT(*) FILTER (WHERE is_311_inspection = 'Yes') / NULLIF(COUNT(*),0), 1) AS pct_311_driven
FROM staging.inspection;

-- SIM Core: Violation summary ------------------------------------------------
CREATE OR REPLACE VIEW sim_core.violation_summary AS
SELECT
  COUNT(*)                                                           AS total_violations,
  COUNT(*) FILTER (WHERE vdismissdate IS NOT NULL AND vdismissdate <> '') AS resolved_violations,
  COUNT(*) FILTER (WHERE vdismissdate IS NULL OR vdismissdate = '')  AS open_violations,
  ROUND(100.0 * COUNT(*) FILTER (WHERE vdismissdate IS NOT NULL AND vdismissdate <> '') / NULLIF(COUNT(*),0), 1) AS resolution_rate_pct,
  ROUND(SUM(TRY_CAST(sq_feet AS DOUBLE)))                            AS total_defect_sqft
FROM staging.violations;

-- SIM Core: Violation distress breakdown (x-marked flags) ---------------------
CREATE OR REPLACE VIEW sim_core.violation_distress AS
SELECT 'trip_hazard'     AS distress_type, COUNT(*) FILTER (WHERE lower(trip_haz)  = 'x') AS violation_count FROM staging.violations
UNION ALL SELECT 'sidewalk_missing', COUNT(*) FILTER (WHERE lower(sw_missing) = 'x') FROM staging.violations
UNION ALL SELECT 'undermined',       COUNT(*) FILTER (WHERE lower(undermined) = 'x') FROM staging.violations
UNION ALL SELECT 'slope',            COUNT(*) FILTER (WHERE lower(slope)      = 'x') FROM staging.violations
UNION ALL SELECT 'patchwork',        COUNT(*) FILTER (WHERE lower(patchwork)  = 'x') FROM staging.violations
UNION ALL SELECT 'broken',           COUNT(*) FILTER (WHERE lower(broken)     = 'x') FROM staging.violations
UNION ALL SELECT 'hardware',         COUNT(*) FILTER (WHERE lower(hardware)   = 'x') FROM staging.violations;

-- SIM Core: Dismissal (repair-completion) outcomes ---------------------------
CREATE OR REPLACE VIEW sim_core.dismissal_outcomes AS
SELECT
  COUNT(*)                                                                          AS total_dismissals,
  COUNT(*) FILTER (WHERE upper(pass_fail) LIKE 'PASS%')                             AS passed,
  COUNT(*) FILTER (WHERE upper(pass_fail) LIKE 'FAIL%')                             AS failed,
  ROUND(100.0 * COUNT(*) FILTER (WHERE upper(pass_fail) LIKE 'PASS%')
        / NULLIF(COUNT(*) FILTER (WHERE pass_fail IS NOT NULL),0), 1)              AS pass_rate_pct
FROM staging.dismissals;

CREATE OR REPLACE VIEW sim_core.dismissals_by_borough AS
SELECT UPPER(TRIM(borough)) AS borough, COUNT(*) AS dismissals,
       ROUND(100.0 * COUNT(*) FILTER (WHERE upper(pass_fail) LIKE 'PASS%') / NULLIF(COUNT(*),0),1) AS pass_rate_pct
FROM staging.dismissals WHERE borough IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;

-- Accessibility: Ramp program ------------------------------------------------
CREATE OR REPLACE VIEW accessibility.ramps_by_borough AS
SELECT UPPER(TRIM(borough)) AS borough, COUNT(*) AS ramps_tracked
FROM staging.ramp_progress WHERE borough IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;

CREATE OR REPLACE VIEW accessibility.ramp_program_summary AS
SELECT
  (SELECT COUNT(*) FROM staging.ramp_progress)  AS total_ramps_tracked,
  (SELECT COUNT(*) FROM staging.ramp_complaints) AS total_ramp_complaints,
  (SELECT COUNT(*) FROM staging.ramp_locations)  AS total_ramp_locations;

-- Coordination: Capital construction outcomes -------------------------------
CREATE OR REPLACE VIEW coordination.construction_summary AS
SELECT
  COUNT(*)                                                  AS built_records,
  ROUND(SUM(TRY_CAST(totalcosttoconstruct AS DOUBLE)))      AS total_construct_cost,
  ROUND(SUM(TRY_CAST(totalsqftsidewalkrepaired AS DOUBLE))) AS total_sqft_repaired,
  ROUND(SUM(TRY_CAST(totallfcurbrepaired AS DOUBLE)))       AS total_lf_curb_repaired
FROM staging.built;
