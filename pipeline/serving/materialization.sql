-- Daily Time-Series Materialization
-- Snapshot creation for KPI tracking and trend analysis

-- ============================================================================
-- Daily KPI Snapshot
-- ============================================================================

INSERT INTO serving.daily_snapshots (measurement_date, kpi_count, avg_kpi_value, datasets_loaded, row_count)
SELECT
    CAST(CURRENT_DATE AS DATE) as measurement_date,
    COUNT(DISTINCT kpi_id * 5) as kpi_count,  -- 51 KPIs × 5 boroughs
    ROUND(AVG(value), 2) as avg_kpi_value,
    57 as datasets_loaded,
    (SELECT SUM(row_count) FROM (
        SELECT COUNT(*) as row_count FROM staging.inspection
        UNION ALL SELECT COUNT(*) FROM staging.violations
        UNION ALL SELECT COUNT(*) FROM staging.ramp_locations
        -- ... union all other 54 datasets
    ) rc) as row_count
FROM serving.kpi_borough_results
WHERE measurement_date = CAST(CURRENT_DATE AS DATE);

-- ============================================================================
-- Monthly KPI Trend
-- ============================================================================

CREATE OR REPLACE VIEW serving.kpi_monthly_trend AS
SELECT
    kpi_id,
    kpi_name,
    borough,
    EXTRACT(YEAR FROM  measurement_date) as year,
    EXTRACT(MONTH FROM  measurement_date) as month,
    ROUND(AVG(value), 2) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    ROUND(STDDEV(value), 2) as std_dev
FROM serving.kpi_borough_results
GROUP BY kpi_id, kpi_name, borough, EXTRACT(YEAR FROM  measurement_date), EXTRACT(MONTH FROM  measurement_date);

-- ============================================================================
-- Borough-Level Time Series
-- ============================================================================

CREATE OR REPLACE VIEW serving.borough_performance_trend AS
SELECT
    borough,
    measurement_date,
    COUNT(DISTINCT kpi_id) as kpis_tracked,
    ROUND(AVG(value), 2) as avg_performance,
    COUNT(CASE WHEN status = 'on_target' THEN 1 END) as on_target_count,
    COUNT(CASE WHEN status = 'at_risk' THEN 1 END) as at_risk_count,
    ROUND(COUNT(CASE WHEN status = 'on_target' THEN 1 END) * 100.0 / COUNT(*), 2) as on_target_percentage
FROM serving.kpi_borough_results
GROUP BY borough, measurement_date
ORDER BY measurement_date DESC, borough;

-- ============================================================================
-- Quality Score Time Series
-- ============================================================================

CREATE OR REPLACE VIEW serving.quality_trend_analysis AS
SELECT
    dataset_name,
    measurement_date,
    completeness_score,
    uniqueness_score,
    validity_score,
    timeliness_score,
    composite_score,
    LAG(composite_score) OVER (PARTITION BY dataset_name ORDER BY measurement_date) as previous_score,
    composite_score - LAG(composite_score) OVER (PARTITION BY dataset_name ORDER BY measurement_date) as score_change
FROM serving.quality_scorecards
ORDER BY measurement_date DESC, dataset_name;

-- ============================================================================
-- Inspection Completion Trend (daily)
-- ============================================================================

CREATE OR REPLACE VIEW serving.inspection_completion_daily AS
SELECT
    CAST(i.inspection_date AS DATE) as inspection_day,
    i.borough,
    COUNT(DISTINCT i.inspection_id) as inspections_completed,
    COUNT(DISTINCT v.violation_id) as violations_found,
    ROUND(COUNT(DISTINCT v.violation_id) * 1.0 / NULLIF(COUNT(DISTINCT i.inspection_id), 0), 2) as avg_violations_per_inspection
FROM staging.inspection i
LEFT JOIN staging.violations v ON i.inspection_id = v.inspection_id
GROUP BY CAST(i.inspection_date AS DATE), i.borough
ORDER BY inspection_day DESC;

-- ============================================================================
-- Violation Resolution Trend (by week)
-- ============================================================================

CREATE OR REPLACE VIEW serving.violation_resolution_weekly AS
SELECT
    EXTRACT(YEAR FROM  v.violation_date) as year,
    EXTRACT(WEEK FROM  v.violation_date) as week,
    v.borough,
    COUNT(DISTINCT v.violation_id) as violations_created,
    COUNT(DISTINCT CASE WHEN v.remediation_status = 'completed' THEN v.violation_id END) as violations_resolved,
    ROUND(COUNT(DISTINCT CASE WHEN v.remediation_status = 'completed' THEN v.violation_id END) * 100.0 / COUNT(*), 2) as resolution_rate
FROM staging.violations v
GROUP BY EXTRACT(YEAR FROM  v.violation_date), EXTRACT(WEEK FROM  v.violation_date), v.borough
ORDER BY year DESC, week DESC;

-- ============================================================================
-- Ramp Work Completion Tracking (monthly)
-- ============================================================================

CREATE OR REPLACE VIEW serving.ramp_work_monthly AS
SELECT
    rl.borough,
    EXTRACT(YEAR FROM  rp.completion_date) as year,
    EXTRACT(MONTH FROM  rp.completion_date) as month,
    COUNT(DISTINCT rl.ramp_id) as ramps_worked_on,
    COUNT(DISTINCT CASE WHEN rl.accessibility_compliant = TRUE THEN rl.ramp_id END) as now_compliant,
    ROUND(COUNT(DISTINCT CASE WHEN rl.accessibility_compliant = TRUE THEN rl.ramp_id END) * 100.0 / COUNT(*), 2) as compliance_rate
FROM staging.ramp_locations rl
LEFT JOIN staging.ramp_progress rp ON rl.ramp_id = rp.ramp_id
WHERE rp.completion_date IS NOT NULL
GROUP BY rl.borough, EXTRACT(YEAR FROM  rp.completion_date), EXTRACT(MONTH FROM  rp.completion_date)
ORDER BY year DESC, month DESC;

-- ============================================================================
-- Data Freshness Monitoring
-- ============================================================================

CREATE OR REPLACE VIEW serving.data_freshness_status AS
SELECT
    'inspection' as source_table,
    MAX(inspection_date) as latest_update,
    DATEDIFF(DAY, MAX(inspection_date), CURRENT_DATE) as days_since_update,
    COUNT(*) as total_records
FROM staging.inspection
UNION ALL
SELECT 'violations', MAX(violation_date), DATEDIFF(DAY, MAX(violation_date), CURRENT_DATE), COUNT(*) FROM staging.violations
UNION ALL
SELECT 'ramp_locations', MAX(created_date), DATEDIFF(DAY, MAX(created_date), CURRENT_DATE), COUNT(*) FROM staging.ramp_locations
UNION ALL
SELECT 'ramp_complaints', MAX(created_date), DATEDIFF(DAY, MAX(created_date), CURRENT_DATE), COUNT(*) FROM staging.ramp_complaints
-- ... (continue for all 57 datasets)
ORDER BY days_since_update;

-- ============================================================================
-- Dashboard-Ready Aggregates
-- ============================================================================

CREATE OR REPLACE VIEW serving.dashboard_summary AS
SELECT
    CAST(CURRENT_DATE AS DATE) as date,
    (SELECT COUNT(DISTINCT inspection_id) FROM staging.inspection WHERE EXTRACT(MONTH FROM  inspection_date) = EXTRACT(MONTH FROM  CURRENT_DATE)) as inspections_this_month,
    (SELECT COUNT(DISTINCT violation_id) FROM staging.violations WHERE violation_date >= (30, CURRENT_DATE)) as violations_last_30_days,
    (SELECT COUNT(DISTINCT ramp_id) FROM staging.ramp_locations WHERE accessibility_compliant = TRUE) as compliant_ramps,
    (SELECT COUNT(DISTINCT ramp_id) FROM staging.ramp_locations) as total_ramps,
    (SELECT AVG(composite_score) FROM serving.quality_scorecards WHERE measurement_date = CAST(CURRENT_DATE AS DATE)) as avg_quality_score,
    (SELECT COUNT(*) FROM serving.kpi_borough_results WHERE measurement_date = CAST(CURRENT_DATE AS DATE) AND status = 'on_target') as kpis_on_target,
    255 as total_kpis,
    57 as datasets_loaded;

-- ============================================================================
-- Weekly Performance Report
-- ============================================================================

CREATE OR REPLACE VIEW serving.weekly_performance_report AS
SELECT
    EXTRACT(YEAR FROM  CURRENT_DATE) as year,
    EXTRACT(WEEK FROM  CURRENT_DATE) as week,
    'Inspections' as metric,
    COUNT(DISTINCT i.inspection_id) as value
FROM staging.inspection i
WHERE EXTRACT(WEEK FROM  i.inspection_date) = EXTRACT(WEEK FROM  CURRENT_DATE)
AND EXTRACT(YEAR FROM  i.inspection_date) = EXTRACT(YEAR FROM  CURRENT_DATE)
UNION ALL
SELECT
    EXTRACT(YEAR FROM  CURRENT_DATE),
    EXTRACT(WEEK FROM  CURRENT_DATE),
    'Violations',
    COUNT(DISTINCT v.violation_id)
FROM staging.violations v
WHERE EXTRACT(WEEK FROM  v.violation_date) = EXTRACT(WEEK FROM  CURRENT_DATE)
AND EXTRACT(YEAR FROM  v.violation_date) = EXTRACT(YEAR FROM  CURRENT_DATE)
UNION ALL
SELECT
    EXTRACT(YEAR FROM  CURRENT_DATE),
    EXTRACT(WEEK FROM  CURRENT_DATE),
    'Ramps',
    COUNT(DISTINCT rl.ramp_id)
FROM staging.ramp_locations rl
WHERE EXTRACT(WEEK FROM  rl.created_date) = EXTRACT(WEEK FROM  CURRENT_DATE)
AND EXTRACT(YEAR FROM  rl.created_date) = EXTRACT(YEAR FROM  CURRENT_DATE);

-- ============================================================================
-- Archive Historical Snapshots (rotate weekly)
-- ============================================================================

-- Move KPI records older than 90 days to archive
CREATE OR REPLACE VIEW serving.kpi_archive_candidates AS
SELECT *
FROM serving.kpi_borough_results
WHERE measurement_date < (90, CURRENT_DATE);

-- Move quality records older than 180 days to archive
CREATE OR REPLACE VIEW serving.quality_archive_candidates AS
SELECT *
FROM serving.quality_scorecards
WHERE measurement_date < (180, CURRENT_DATE);
