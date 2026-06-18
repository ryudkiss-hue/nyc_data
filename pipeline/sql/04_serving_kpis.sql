-- Stage 4: SERVING - KPI Materialization
-- 255 KPI records (51 KPIs × 5 boroughs)
-- 57 quality scorecards (0-100 composite scores)
-- 25 borough-level aggregates
-- Daily time-series snapshots

CREATE SCHEMA IF NOT EXISTS serving;

-- Create KPI materialized table
-- 51 KPIs × 5 boroughs (Manhattan, Brooklyn, Queens, Bronx, Staten Island) = 255 records

-- Example KPI structure:
-- kpi_id | kpi_name | borough | period | value | threshold | status
-- 1      | Inspections Completed | manhattan | 2026-06-18 | 245 | 250 | at_risk
-- 2      | Average Response Time | brooklyn | 2026-06-18 | 3.2 | 3.0 | below_threshold

-- CREATE TABLE serving.kpi_metrics (
--     kpi_id INTEGER,
--     kpi_name VARCHAR,
--     borough VARCHAR,
--     measurement_date DATE,
--     value DOUBLE,
--     threshold DOUBLE,
--     status VARCHAR,
--     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Quality scorecard: 57 datasets × 0-100 composite score
-- Dimensions: completeness, uniqueness, validity, timeliness

-- CREATE TABLE serving.quality_scorecards (
--     dataset_name VARCHAR,
--     completeness_score DOUBLE,      -- % non-null rows
--     uniqueness_score DOUBLE,        -- % unique PKs / total rows
--     validity_score DOUBLE,          -- % rows passing type validation
--     timeliness_score DOUBLE,        -- (1 - days_stale / max_acceptable_days)
--     composite_score DOUBLE,         -- Average of above
--     measurement_date DATE,
--     last_updated TIMESTAMP
-- );

-- Borough aggregates: 5 boroughs × 5 metrics = 25 records
-- CREATE TABLE serving.borough_aggregates (
--     borough VARCHAR,
--     metric_name VARCHAR,
--     value DOUBLE,
--     measurement_date DATE
-- );

-- Daily time-series snapshot
-- CREATE TABLE serving.daily_snapshots (
--     measurement_date DATE,
--     kpi_count INTEGER,
--     avg_kpi_value DOUBLE,
--     datasets_loaded INTEGER,
--     row_count BIGINT
-- );

-- Materialization verification
-- SELECT
--     'kpi_metrics' as table_name,
--     COUNT(*) as record_count,
--     COUNT(DISTINCT borough) as boroughs,
--     COUNT(DISTINCT kpi_name) as unique_kpis
-- FROM serving.kpi_metrics
-- UNION ALL
-- SELECT
--     'quality_scorecards',
--     COUNT(*),
--     1,
--     COUNT(DISTINCT dataset_name)
-- FROM serving.quality_scorecards;
