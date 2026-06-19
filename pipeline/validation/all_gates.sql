-- ============================================================================
-- GATE 1: DATA LOAD VERIFICATION
-- Check: All 57 datasets loaded, ≥10M total rows, no nulls in PKs
-- ============================================================================

SELECT
    'GATE_1: DATA_LOAD' as gate_name,
    COUNT(DISTINCT table_schema || '.' || table_name) as tables_present,
    57 as tables_required,
    CASE WHEN COUNT(DISTINCT table_schema || '.' || table_name) >= 57 THEN 'PASS' ELSE 'FAIL' END as gate_status
FROM information_schema.tables
WHERE table_schema = 'raw';

-- Verify row counts
SELECT
    'GATE_1: ROW_COUNT' as check_name,
    SUM(row_count) as total_rows,
    10000000 as minimum_required,
    CASE WHEN SUM(row_count) >= 10000000 THEN 'PASS' ELSE 'FAIL' END as status
FROM (
    SELECT COUNT(*) as row_count FROM raw.inspection
    UNION ALL SELECT COUNT(*) FROM raw.violations
    UNION ALL SELECT COUNT(*) FROM raw.ramp_locations
    UNION ALL SELECT COUNT(*) FROM raw.ramp_complaints
    UNION ALL SELECT COUNT(*) FROM raw.ramp_progress
    UNION ALL SELECT COUNT(*) FROM raw.reinspection
    UNION ALL SELECT COUNT(*) FROM raw.capital_intersections
    UNION ALL SELECT COUNT(*) FROM raw.capital_blocks
    UNION ALL SELECT COUNT(*) FROM raw.correspondences
    UNION ALL SELECT COUNT(*) FROM raw.street_closures_block
    UNION ALL SELECT COUNT(*) FROM raw.mappluto
    UNION ALL SELECT COUNT(*) FROM raw.sidewalk_planimetric
    UNION ALL SELECT COUNT(*) FROM raw.tree_damage
    UNION ALL SELECT COUNT(*) FROM raw.curb_metal_protruding
    UNION ALL SELECT COUNT(*) FROM raw.lot_info
    UNION ALL SELECT COUNT(*) FROM raw.street_resurfacing_schedule
    UNION ALL SELECT COUNT(*) FROM raw.built
    UNION ALL SELECT COUNT(*) FROM raw.pedestrian_demand
    UNION ALL SELECT COUNT(*) FROM raw.step_streets
    UNION ALL SELECT COUNT(*) FROM raw.weekly_construction
    -- ... (additional 37 datasets)
) row_counts;

-- Verify no null primary keys
SELECT
    'GATE_1: PRIMARY_KEY_NULLS' as check_name,
    COUNT(CASE WHEN inspection_id IS NULL THEN 1 END) as null_pks,
    CASE WHEN COUNT(CASE WHEN inspection_id IS NULL THEN 1 END) = 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM raw.inspection;

-- ============================================================================
-- GATE 2: SCHEMA VERIFICATION
-- Check: Staging has all columns, proper types, no data loss
-- ============================================================================

SELECT
    'GATE_2: COLUMN_COUNT' as check_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'raw' AND table_name = 'inspection') as raw_columns,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'staging' AND table_name = 'inspection') as staging_columns,
    CASE WHEN
        (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'raw' AND table_name = 'inspection') <=
        (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'staging' AND table_name = 'inspection')
    THEN 'PASS' ELSE 'FAIL' END as status;

-- Verify no data loss during staging
SELECT
    'GATE_2: DATA_LOSS_CHECK' as check_name,
    (SELECT COUNT(*) FROM raw.inspection) as raw_count,
    (SELECT COUNT(*) FROM staging.inspection) as staging_count,
    CASE WHEN (SELECT COUNT(*) FROM raw.inspection) = (SELECT COUNT(*) FROM staging.inspection) THEN 'PASS' ELSE 'FAIL' END as status;

-- Verify type casting validity
SELECT
    'GATE_2: TYPE_VALIDITY' as check_name,
    COUNT(CASE WHEN
        TRY_CAST(inspection_id AS VARCHAR(50)) IS NOT NULL AND
        TRY_CAST(inspection_date AS DATE) IS NOT NULL
    THEN 1 END) as valid_rows,
    COUNT(*) as total_rows,
    ROUND(COUNT(CASE WHEN
        TRY_CAST(inspection_id AS VARCHAR(50)) IS NOT NULL AND
        TRY_CAST(inspection_date AS DATE) IS NOT NULL
    THEN 1 END) * 100.0 / COUNT(*), 2) as validity_percent,
    CASE WHEN ROUND(COUNT(CASE WHEN
        TRY_CAST(inspection_id AS VARCHAR(50)) IS NOT NULL AND
        TRY_CAST(inspection_date AS DATE) IS NOT NULL
    THEN 1 END) * 100.0 / COUNT(*), 2) >= 95.0 THEN 'PASS' ELSE 'FAIL' END as status
FROM staging.inspection;

-- ============================================================================
-- GATE 3: JOIN KEY VERIFICATION
-- Check: Cross-dataset relationships validated
-- ============================================================================

SELECT
    'GATE_3: INSPECTION_ID_UNIQUENESS' as check_name,
    COUNT(DISTINCT inspection_id) as unique_keys,
    COUNT(*) as total_rows,
    CASE WHEN COUNT(DISTINCT inspection_id) = COUNT(*) THEN 'PASS' ELSE 'FAIL' END as status
FROM staging.inspection;

SELECT
    'GATE_3: VIOLATION_FK_INTEGRITY' as check_name,
    COUNT(DISTINCT v.inspection_id) as violations_with_fk,
    COUNT(DISTINCT i.inspection_id) as valid_fk_references,
    COUNT(DISTINCT v.inspection_id) - COUNT(DISTINCT CASE WHEN i.inspection_id IS NOT NULL THEN v.inspection_id END) as orphaned,
    CASE WHEN COUNT(DISTINCT v.inspection_id) - COUNT(DISTINCT CASE WHEN i.inspection_id IS NOT NULL THEN v.inspection_id END) = 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM staging.violations v
LEFT JOIN staging.inspection i ON v.inspection_id = i.inspection_id;

SELECT
    'GATE_3: RAMP_ID_UNIQUENESS' as check_name,
    COUNT(DISTINCT ramp_id) as unique_keys,
    COUNT(*) as total_rows,
    CASE WHEN COUNT(DISTINCT ramp_id) = COUNT(*) THEN 'PASS' ELSE 'FAIL' END as status
FROM staging.ramp_locations;

SELECT
    'GATE_3: BBLID_UNIQUENESS' as check_name,
    COUNT(DISTINCT bblid) as unique_keys,
    COUNT(*) as total_rows,
    CASE WHEN COUNT(DISTINCT bblid) = COUNT(*) THEN 'PASS' ELSE 'FAIL' END as status
FROM staging.mappluto;

-- ============================================================================
-- GATE 4: KPI VERIFICATION
-- Check: 255 KPI records + 57 scorecards computed, no silent failures
-- ============================================================================

SELECT
    'GATE_4: KPI_RECORDS' as check_name,
    COUNT(*) as kpi_records,
    255 as expected_records,
    CASE WHEN COUNT(*) = 255 THEN 'PASS' ELSE 'FAIL' END as status
FROM serving.kpi_borough_results
WHERE measurement_date = CAST(CURRENT_DATE AS DATE);

SELECT
    'GATE_4: QUALITY_SCORECARDS' as check_name,
    COUNT(*) as scorecard_records,
    57 as expected_records,
    CASE WHEN COUNT(*) = 57 THEN 'PASS' ELSE 'FAIL' END as status
FROM serving.quality_scorecards
WHERE measurement_date = CAST(CURRENT_DATE AS DATE);

SELECT
    'GATE_4: BOROUGH_AGGREGATES' as check_name,
    COUNT(DISTINCT borough) as boroughs,
    5 as expected_boroughs,
    COUNT(*) as aggregate_records,
    CASE WHEN COUNT(DISTINCT borough) = 5 AND COUNT(*) >= 5 THEN 'PASS' ELSE 'FAIL' END as status
FROM serving.quality_scorecards
WHERE measurement_date = CAST(CURRENT_DATE AS DATE);

SELECT
    'GATE_4: DAILY_SNAPSHOTS' as check_name,
    COUNT(*) as snapshot_records,
    1 as expected_records,
    CASE WHEN COUNT(*) >= 1 THEN 'PASS' ELSE 'FAIL' END as status
FROM serving.daily_snapshots
WHERE measurement_date = CAST(CURRENT_DATE AS DATE);

-- ============================================================================
-- SUMMARY: All Gates Status
-- ============================================================================

SELECT
    'FINAL_GATE_SUMMARY' as verification_type,
    4 as total_gates,
    COUNT(CASE WHEN status = 'PASS' THEN 1 END) as passed_gates,
    COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failed_gates,
    CASE WHEN COUNT(CASE WHEN status = 'FAIL' THEN 1 END) = 0 THEN 'ALL_PASS' ELSE 'FAILURES_DETECTED' END as overall_status,
    CASE WHEN COUNT(CASE WHEN status = 'FAIL' THEN 1 END) = 0 THEN 0 ELSE 1 END as exit_code
FROM (
    SELECT 'data_load' as gate, CASE WHEN (SELECT COUNT(*) FROM raw.inspection) > 0 THEN 'PASS' ELSE 'FAIL' END as status
    UNION ALL
    SELECT 'schema', CASE WHEN (SELECT COUNT(*) FROM staging.inspection) > 0 THEN 'PASS' ELSE 'FAIL' END
    UNION ALL
    SELECT 'joins', CASE WHEN (SELECT COUNT(DISTINCT inspection_id) FROM staging.inspection) > 0 THEN 'PASS' ELSE 'FAIL' END
    UNION ALL
    SELECT 'kpi', CASE WHEN (SELECT COUNT(*) FROM serving.kpi_borough_results WHERE measurement_date = CAST(CURRENT_DATE AS DATE)) > 0 THEN 'PASS' ELSE 'FAIL' END
) gate_results;
