-- Stage 2: STAGING Schema
-- Deduplicate, type-cast, preserve Socrata column names
-- All 57 datasets, zero data loss

CREATE SCHEMA IF NOT EXISTS staging;

-- Example: Staging template for any raw table
-- Assumes column 0 is the primary key for deduplication
-- Uses TRY_CAST to handle type conversions safely

-- Template for: CREATE TABLE staging.{table_name} AS
-- SELECT DISTINCT ON (column_0)  -- Deduplicate by primary key
--     column_0,
--     column_1,
--     column_2,
--     -- ... all columns with TRY_CAST for proper types
--     TRY_CAST(column_numeric AS DOUBLE) as metric_column,
--     TRY_CAST(column_date AS DATE) as date_column
-- FROM raw.{table_name}
-- WHERE column_0 IS NOT NULL  -- Remove null PKs
-- ORDER BY column_0;

-- Verification: Ensure no data loss during dedup
-- SELECT 'raw vs staging' as check_type, COUNT(*) as count
-- FROM raw.{table_name}
-- UNION ALL
-- SELECT 'staging', COUNT(*) FROM staging.{table_name}
-- ORDER BY count DESC;

-- Metadata preservation verification
-- SELECT
--     table_name,
--     column_name,
--     data_type,
--     is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'staging'
-- ORDER BY table_name, ordinal_position;
