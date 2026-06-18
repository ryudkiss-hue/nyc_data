-- Stage 1: RAW Schema Setup
-- Creates raw schema and prepares for data landing

-- Create raw schema
CREATE SCHEMA IF NOT EXISTS raw;

-- Load cached Parquet files from local cache directory
-- Tables: capital_intersections, built, pedestrian_demand, mappluto, capital_blocks,
--         tree_damage, correspondences, step_streets, curb_metal_protruding, inspection,
--         lot_info, ramp_complaints, ramp_locations, ramp_progress, reinspection,
--         street_closures_block, sidewalk_planimetric, street_resurfacing_schedule,
--         violations, weekly_construction (20 tables)

-- Note: Implementation uses DuckDB's read_parquet() function to bulk-load from cache
-- SELECT * FROM read_parquet('/path/to/cache/raw/*.parquet');

-- Verify raw tables loaded
SELECT
    COUNT(*) as raw_tables_count,
    SUM(row_count) as total_rows
FROM (
    SELECT table_name, COUNT(*) as row_count
    FROM raw.*
    GROUP BY table_name
);
