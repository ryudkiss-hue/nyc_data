-- ============================================================================
-- Verification Gates - REAL data-quality checks (rewritten 2026-06-22)
-- ============================================================================
-- 4 gates computed from actual table contents. The prior version referenced
-- information_schema.row_count (does not exist in DuckDB) and was missing a
-- FROM clause, so it never ran. Each gate writes one row with status PASS/FAIL.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS verification;

-- GATE 1: Raw data loaded — core tables must hold real rows -------------------
CREATE OR REPLACE TABLE verification.gate_1_data_load AS
SELECT
  'gate_1_data_load' AS gate_name,
  (SELECT COUNT(*) FROM raw.inspection)
  + (SELECT COUNT(*) FROM raw.violations)
  + (SELECT COUNT(*) FROM raw.ramp_progress) AS core_row_count,
  CASE WHEN (SELECT COUNT(*) FROM raw.inspection) > 0
        AND (SELECT COUNT(*) FROM raw.violations) > 0
        AND (SELECT COUNT(*) FROM raw.ramp_progress) > 0
       THEN 'PASS' ELSE 'FAIL' END AS status,
  CURRENT_TIMESTAMP AS verified_at;

-- GATE 2: Staging built — staging mirrors raw for core tables ----------------
CREATE OR REPLACE TABLE verification.gate_2_staging AS
SELECT
  'gate_2_staging' AS gate_name,
  (SELECT COUNT(*) FROM staging.inspection) AS staging_inspection_rows,
  CASE WHEN (SELECT COUNT(*) FROM staging.inspection) > 0
        AND (SELECT COUNT(*) FROM staging.violations) > 0
       THEN 'PASS' ELSE 'FAIL' END AS status,
  CURRENT_TIMESTAMP AS verified_at;

-- GATE 3: Analytics views return data, not errors ----------------------------
CREATE OR REPLACE TABLE verification.gate_3_analytics AS
SELECT
  'gate_3_analytics' AS gate_name,
  (SELECT total_inspections FROM sim_core.inspection_summary) AS total_inspections,
  (SELECT total_violations  FROM sim_core.violation_summary)  AS total_violations,
  CASE WHEN (SELECT total_inspections FROM sim_core.inspection_summary) > 0
        AND (SELECT total_violations  FROM sim_core.violation_summary)  > 0
       THEN 'PASS' ELSE 'FAIL' END AS status,
  CURRENT_TIMESTAMP AS verified_at;

-- GATE 4: Metrics materialized with real, non-null values -----------------------
CREATE OR REPLACE TABLE verification.gate_4_metrics AS
SELECT
  'gate_4_metrics' AS gate_name,
  (SELECT COUNT(*) FROM serving.metric_summary) AS metric_count,
  (SELECT COUNT(*) FROM serving.metric_summary WHERE value IS NULL) AS null_value_metrics,
  CASE WHEN (SELECT COUNT(*) FROM serving.metric_summary) >= 10
        AND (SELECT COUNT(*) FROM serving.metric_summary WHERE value IS NULL) = 0
       THEN 'PASS' ELSE 'FAIL' END AS status,
  CURRENT_TIMESTAMP AS verified_at;

-- Consolidated gate status ---------------------------------------------------
CREATE OR REPLACE TABLE verification.gate_results AS
SELECT gate_name, status, verified_at FROM verification.gate_1_data_load
UNION ALL SELECT gate_name, status, verified_at FROM verification.gate_2_staging
UNION ALL SELECT gate_name, status, verified_at FROM verification.gate_3_analytics
UNION ALL SELECT gate_name, status, verified_at FROM verification.gate_4_metrics;
