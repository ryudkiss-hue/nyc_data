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

-- GATE SUMMARY VIEW
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
);
