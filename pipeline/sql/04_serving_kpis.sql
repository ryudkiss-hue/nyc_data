-- ============================================================================
-- Serving KPIs - REAL computed values (auto-generated 2026-06-22)
-- ============================================================================
-- Every value below is COMPUTED from live staging data. This replaces the
-- prior version, which hardcoded 255 synthetic rows (value = threshold * 0.95)
-- and computed nothing — a violation of the no-synthetic-data mandate.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS serving;

-- Citywide KPI summary: one row per KPI, value computed from real data --------
CREATE OR REPLACE TABLE serving.kpi_summary AS
WITH ins AS (SELECT * FROM sim_core.inspection_summary),
     vio AS (SELECT * FROM sim_core.violation_summary),
     dis AS (SELECT * FROM sim_core.dismissal_outcomes),
     con AS (SELECT * FROM coordination.construction_summary),
     rmp AS (SELECT * FROM accessibility.ramp_program_summary)
SELECT * FROM (
  VALUES
    ('KPI-01','Total Inspections',          'volume',       'sim_core',      (SELECT total_inspections      FROM ins),  'count',   CURRENT_DATE),
    ('KPI-02','Inspections No-Violation %',  'quality',      'sim_core',      (SELECT pct_no_violation       FROM ins),  'percent', CURRENT_DATE),
    ('KPI-03','311-Driven Inspection %',     'demand',       'sim_core',      (SELECT pct_311_driven         FROM ins),  'percent', CURRENT_DATE),
    ('KPI-04','Total Violations',            'volume',       'sim_core',      (SELECT total_violations       FROM vio),  'count',   CURRENT_DATE),
    ('KPI-05','Violation Resolution Rate',   'operations',   'sim_core',      (SELECT resolution_rate_pct    FROM vio),  'percent', CURRENT_DATE),
    ('KPI-06','Open Violations',             'operations',   'sim_core',      (SELECT open_violations        FROM vio),  'count',   CURRENT_DATE),
    ('KPI-07','Total Defect SqFt',           'condition',    'sim_core',      (SELECT total_defect_sqft      FROM vio),  'sqft',    CURRENT_DATE),
    ('KPI-08','Dismissal Pass Rate',         'operations',   'sim_core',      (SELECT pass_rate_pct          FROM dis),  'percent', CURRENT_DATE),
    ('KPI-09','Total Repair Completions',    'operations',   'sim_core',      (SELECT total_dismissals       FROM dis),  'count',   CURRENT_DATE),
    ('KPI-10','Total Construct Cost',        'budget',       'coordination',  (SELECT total_construct_cost   FROM con),  'usd',     CURRENT_DATE),
    ('KPI-11','SqFt Sidewalk Repaired',      'output',       'coordination',  (SELECT total_sqft_repaired    FROM con),  'sqft',    CURRENT_DATE),
    ('KPI-12','Total Ramps Tracked',         'accessibility','accessibility', (SELECT total_ramps_tracked    FROM rmp),  'count',   CURRENT_DATE),
    ('KPI-13','Total Ramp Complaints',       'accessibility','accessibility', (SELECT total_ramp_complaints  FROM rmp),  'count',   CURRENT_DATE)
) AS t(kpi_id, kpi_name, category, domain, value, unit, measurement_date);

COMMENT ON TABLE serving.kpi_summary IS 'REAL KPIs computed from live staging data (NYC Open Data, LL251-verified IDs). 13 citywide KPIs across volume/quality/operations/budget/accessibility. No synthetic values.';

-- Borough-dimensioned KPIs (only where a clean borough column exists) ---------
CREATE OR REPLACE TABLE serving.kpi_by_borough AS
SELECT 'Ramps Tracked' AS kpi_name, borough, ramps_tracked AS value, 'count' AS unit, CURRENT_DATE AS measurement_date
FROM accessibility.ramps_by_borough
UNION ALL
SELECT 'Repair Dismissals', borough, dismissals, 'count', CURRENT_DATE FROM sim_core.dismissals_by_borough
UNION ALL
SELECT 'Dismissal Pass Rate', borough, pass_rate_pct, 'percent', CURRENT_DATE FROM sim_core.dismissals_by_borough;

COMMENT ON TABLE serving.kpi_by_borough IS 'Borough-level KPIs computed from datasets with a clean borough column (ramp_progress, dismissals). Inspection/violation lack a direct borough field, so borough attribution there requires a future geocode join.';
