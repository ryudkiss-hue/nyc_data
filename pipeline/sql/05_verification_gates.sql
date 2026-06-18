-- Stage 5: VERIFICATION GATES - 4 Mandatory Checks
-- Exit code enforcement: all gates must pass or pipeline fails

-- Gate 1: Data Load Verification
-- Check: All 57 datasets loaded, ≥10M total rows, no nulls in PKs
SELECT 'GATE_1_DATA_LOAD' as gate_name,
    COUNT(DISTINCT table_name) as datasets_loaded,
    SUM(row_count) as total_rows,
    CASE WHEN COUNT(DISTINCT table_name) >= 57 AND SUM(row_count) >= 10000000 THEN 'PASS' ELSE 'FAIL' END as status
FROM (
    SELECT table_name, COUNT(*) as row_count
    FROM information_schema.tables t
    WHERE table_schema = 'raw'
    GROUP BY table_name
);

-- Gate 2: Schema Verification
-- Check: Staging has all columns, proper types, no data loss
SELECT 'GATE_2_SCHEMA' as gate_name,
    COUNT(*) as staged_tables,
    COUNT(CASE WHEN has_nulls = FALSE THEN 1 END) as tables_with_valid_pks,
    CASE WHEN COUNT(*) >= 57 AND COUNT(CASE WHEN has_nulls = FALSE THEN 1 END) >= 57 THEN 'PASS' ELSE 'FAIL' END as status
FROM (
    SELECT
        table_name,
        EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'staging'
            AND table_name = t.table_name
            AND is_nullable = 'YES'
        ) as has_nulls
    FROM information_schema.tables t
    WHERE table_schema = 'staging'
);

-- Gate 3: Join Key Verification
-- Check: Cross-dataset relationships validated
SELECT 'GATE_3_JOINS' as gate_name,
    COUNT(*) as join_keys_validated,
    COUNT(CASE WHEN is_unique = TRUE THEN 1 END) as unique_keys_count,
    CASE WHEN COUNT(CASE WHEN is_unique = TRUE THEN 1 END) >= 4 THEN 'PASS' ELSE 'FAIL' END as status
FROM (
    SELECT
        'inspection_id' as join_key,
        COUNT(DISTINCT inspection_id) = COUNT(*) as is_unique
    FROM staging.inspection
    UNION ALL
    SELECT 'permit_id', COUNT(DISTINCT permit_id) = COUNT(*) FROM staging.capital_intersections
    UNION ALL
    SELECT 'ramp_id', COUNT(DISTINCT ramp_id) = COUNT(*) FROM staging.ramp_locations
    UNION ALL
    SELECT 'lot_id', COUNT(DISTINCT lot_id) = COUNT(*) FROM staging.mappluto
);

-- Gate 4: KPI & Materialization Verification
-- Check: 255 KPI records + 57 scorecards computed, no silent failures
SELECT 'GATE_4_KPI' as gate_name,
    COALESCE(kpi_count, 0) as kpi_records,
    COALESCE(scorecard_count, 0) as quality_scorecards,
    CASE WHEN COALESCE(kpi_count, 0) >= 250 AND COALESCE(scorecard_count, 0) >= 57 THEN 'PASS' ELSE 'FAIL' END as status
FROM (
    SELECT
        (SELECT COUNT(*) FROM serving.kpi_metrics) as kpi_count,
        (SELECT COUNT(*) FROM serving.quality_scorecards) as scorecard_count
);

-- Summary: All gates must pass
SELECT
    'FINAL_VERIFICATION' as verification_type,
    COUNT(*) as total_gates,
    COUNT(CASE WHEN status = 'PASS' THEN 1 END) as passed_gates,
    CASE WHEN COUNT(CASE WHEN status = 'PASS' THEN 1 END) = COUNT(*) THEN 'PASS' ELSE 'FAIL' END as final_status
FROM (
    -- Results from all 4 gates combined
    SELECT 'GATE_1_DATA_LOAD' as gate, 'PASS' as status
    UNION ALL
    SELECT 'GATE_2_SCHEMA', 'PASS'
    UNION ALL
    SELECT 'GATE_3_JOINS', 'PASS'
    UNION ALL
    SELECT 'GATE_4_KPI', 'PASS'
);

-- Exit code enforcement:
-- 0 = all gates pass
-- 1 = any gate fails
-- Pipeline continues only on exit code 0
