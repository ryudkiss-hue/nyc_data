/**
 * PostGIS Spatial Database Migration for NYC DOT Sidewalk Toolkit
 * 
 * Creates spatial tables, indexes, and functions for geographic analysis.
 * Uses SRID 4326 (WGS84) for NYC coordinates: 40.7128°N, 74.0060°W
 * 
 * Prerequisites:
 *   - PostgreSQL 12+
 *   - PostGIS 3.0+ extension enabled
 * 
 * Run with: psql -U postgres -d sidewalk_db -f 010_postgis_schema.sql
 */

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- Verify PostGIS installation
SELECT PostGIS_version();

-- ============================================================================
-- SPATIAL REFERENCE SYSTEMS
-- ============================================================================

-- NYC uses WGS84 (SRID 4326) for public data
-- NAD83 NY Long Island (SRID 2263) used for some NYC GIS data
INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text)
VALUES 
  (4326, 'EPSG', 4326, 
   'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]',
   '+proj=longlat +datum=WGS84 +no_defs')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- SIDEWALK SEGMENTS TABLE (Main spatial entity)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sidewalk_segments (
    segment_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(LINESTRING, 4326) NOT NULL,
    
    -- Geometry metadata
    length_meters FLOAT GENERATED ALWAYS AS 
        (ST_Length(geography(geometry)::geography)) STORED,
    
    -- Segment classification
    material_type VARCHAR(50),  -- asphalt, concrete, brick, stone, other
    condition_score FLOAT CHECK (condition_score >= 0 AND condition_score <= 100),
    defects INT DEFAULT 0,
    
    -- Geographic hierarchy
    borough VARCHAR(50),  -- Manhattan, Brooklyn, Queens, Bronx, Staten Island
    block_id VARCHAR(50),
    district VARCHAR(50),
    council_district VARCHAR(50),
    community_board VARCHAR(50),
    
    -- Inspection metadata
    last_inspection TIMESTAMP,
    last_inspector_id VARCHAR(50),
    inspection_count INT DEFAULT 0,
    
    -- Data quality
    gps_accuracy_meters FLOAT,
    data_source VARCHAR(100),
    
    -- Auditing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_borough CHECK (borough IN 
        ('Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island')),
    CONSTRAINT valid_material CHECK (material_type IN 
        ('asphalt', 'concrete', 'brick', 'stone', 'other', NULL))
);

-- Primary spatial index on geometry (GiST - Generalized Search Tree)
CREATE INDEX idx_sidewalk_segments_geom 
    ON sidewalk_segments USING GIST(geometry)
    WITH (FILLFACTOR=70);

-- BRIN index for time-series spatial queries
CREATE INDEX idx_sidewalk_segments_brin 
    ON sidewalk_segments USING BRIN(last_inspection, geometry);

-- Secondary indexes for filtering
CREATE INDEX idx_sidewalk_segments_material 
    ON sidewalk_segments(material_type);

CREATE INDEX idx_sidewalk_segments_condition 
    ON sidewalk_segments(condition_score);

CREATE INDEX idx_sidewalk_segments_borough 
    ON sidewalk_segments(borough);

CREATE INDEX idx_sidewalk_segments_block 
    ON sidewalk_segments(block_id);

CREATE INDEX idx_sidewalk_segments_last_inspection 
    ON sidewalk_segments(last_inspection DESC);

-- Composite index for common queries
CREATE INDEX idx_sidewalk_segments_borough_material 
    ON sidewalk_segments(borough, material_type);

-- ============================================================================
-- BLOCKS TABLE (Polygon boundaries)
-- ============================================================================

CREATE TABLE IF NOT EXISTS blocks (
    block_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(POLYGON, 4326) NOT NULL,
    
    -- Area calculation
    area_square_meters FLOAT GENERATED ALWAYS AS 
        (ST_Area(geography(geometry)::geography)) STORED,
    
    -- Geographic hierarchy
    borough VARCHAR(50),
    district VARCHAR(50),
    council_district VARCHAR(50),
    
    -- Segment counts
    total_segments INT DEFAULT 0,
    segments_with_data INT DEFAULT 0,
    segments_inspected INT DEFAULT 0,
    
    -- Data quality
    coverage_percentage FLOAT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_borough CHECK (borough IN 
        ('Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'))
);

-- Spatial index on block polygons
CREATE INDEX idx_blocks_geom 
    ON blocks USING GIST(geometry);

CREATE INDEX idx_blocks_borough 
    ON blocks(borough);

-- ============================================================================
-- INSPECTIONS TABLE (Point-based inspection records)
-- ============================================================================

CREATE TABLE IF NOT EXISTS inspections (
    inspection_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    
    -- Segment reference
    segment_id VARCHAR(50) NOT NULL REFERENCES sidewalk_segments(segment_id)
        ON DELETE CASCADE,
    
    -- Inspector metadata
    inspector_id VARCHAR(50),
    inspection_timestamp TIMESTAMP NOT NULL,
    
    -- Defect information
    defect_type VARCHAR(100),  -- pothole, crack, heave, settlement, etc.
    severity VARCHAR(20) CHECK (severity IN 
        ('low', 'medium', 'high', 'critical')),
    condition_score INT CHECK (condition_score >= 0 AND condition_score <= 100),
    
    -- Field data
    gps_accuracy_meters FLOAT DEFAULT 5.0,
    photo_url TEXT,
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_severity CHECK (severity IN 
        ('low', 'medium', 'high', 'critical'))
);

-- Spatial index on inspection locations
CREATE INDEX idx_inspections_geom 
    ON inspections USING GIST(geometry);

-- Temporal index for recent inspections
CREATE INDEX idx_inspections_timestamp 
    ON inspections(inspection_timestamp DESC);

-- Segment-based index for inspection queries
CREATE INDEX idx_inspections_segment 
    ON inspections(segment_id);

-- Composite for severity analysis
CREATE INDEX idx_inspections_severity_timestamp 
    ON inspections(severity, inspection_timestamp DESC);

-- ============================================================================
-- MATERIAL ZONES TABLE (MultiPolygon zones of uniform material)
-- ============================================================================

CREATE TABLE IF NOT EXISTS material_zones (
    zone_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    
    -- Material classification
    material_type VARCHAR(50) NOT NULL,
    
    -- Zone statistics
    area_square_meters FLOAT GENERATED ALWAYS AS 
        (ST_Area(geography(geometry)::geography)) STORED,
    segment_count INT DEFAULT 0,
    average_condition FLOAT,
    
    -- Coverage
    borough VARCHAR(50),
    district VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spatial index on material zones
CREATE INDEX idx_material_zones_geom 
    ON material_zones USING GIST(geometry);

CREATE INDEX idx_material_zones_material 
    ON material_zones(material_type);

CREATE INDEX idx_material_zones_borough 
    ON material_zones(borough);

-- ============================================================================
-- HOTSPOTS TABLE (Problem areas identified through analysis)
-- ============================================================================

CREATE TABLE IF NOT EXISTS hotspots (
    hotspot_id VARCHAR(50) PRIMARY KEY,
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    
    -- Hotspot classification
    severity VARCHAR(20) CHECK (severity IN 
        ('low', 'medium', 'high', 'critical')),
    
    -- Analysis results
    density FLOAT,  -- segments or defects per unit area
    average_condition FLOAT,
    segment_count INT,
    defect_count INT,
    
    -- Extent of impact
    buffer_radius_meters INT,
    affected_area_geom GEOMETRY(POLYGON, 4326),
    
    -- Geographic
    borough VARCHAR(50),
    district VARCHAR(50),
    
    -- Temporal
    detected_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority INT DEFAULT 5,  -- 1=critical, 10=low
    
    CONSTRAINT valid_severity CHECK (severity IN 
        ('low', 'medium', 'high', 'critical'))
);

-- Spatial index
CREATE INDEX idx_hotspots_geom 
    ON hotspots USING GIST(geometry);

CREATE INDEX idx_hotspots_severity 
    ON hotspots(severity);

-- Buffer geometry index
CREATE INDEX idx_hotspots_buffer_geom 
    ON hotspots USING GIST(affected_area_geom);

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Segment statistics by borough
CREATE MATERIALIZED VIEW mv_segments_by_borough AS
SELECT 
    borough,
    COUNT(*) as segment_count,
    SUM(length_meters) as total_length_meters,
    AVG(condition_score) as average_condition,
    MIN(condition_score) as min_condition,
    MAX(condition_score) as max_condition,
    COUNT(CASE WHEN last_inspection IS NOT NULL THEN 1 END) as inspected_count,
    COUNT(DISTINCT material_type) as material_types,
    ST_Union(geometry) as union_geometry
FROM sidewalk_segments
GROUP BY borough;

CREATE INDEX idx_mv_segments_by_borough_borough 
    ON mv_segments_by_borough(borough);

-- Segment statistics by material
CREATE MATERIALIZED VIEW mv_segments_by_material AS
SELECT 
    material_type,
    borough,
    COUNT(*) as segment_count,
    SUM(length_meters) as total_length_meters,
    AVG(condition_score) as average_condition,
    MIN(condition_score) as min_condition,
    MAX(condition_score) as max_condition,
    ST_Union(geometry) as union_geometry
FROM sidewalk_segments
WHERE material_type IS NOT NULL
GROUP BY material_type, borough;

-- Block coverage metrics
CREATE MATERIALIZED VIEW mv_block_coverage AS
SELECT 
    b.block_id,
    b.borough,
    b.district,
    b.geometry,
    COUNT(ss.segment_id) as segments_with_data,
    ROUND(100.0 * COUNT(ss.segment_id)::FLOAT / 
        NULLIF(b.total_segments, 0), 2) as coverage_percentage,
    AVG(ss.condition_score) as average_condition,
    b.last_updated
FROM blocks b
LEFT JOIN sidewalk_segments ss ON ST_Intersects(b.geometry, ss.geometry)
GROUP BY b.block_id, b.geometry, b.borough, b.district, b.total_segments, b.last_updated;

-- ============================================================================
-- SPATIAL FUNCTIONS
-- ============================================================================

-- Function: Find segments within distance of a point
CREATE OR REPLACE FUNCTION find_segments_nearby(
    p_point GEOMETRY,
    p_distance_meters FLOAT DEFAULT 50
) 
RETURNS TABLE (
    segment_id VARCHAR(50),
    distance_meters FLOAT,
    material_type VARCHAR(50),
    condition_score FLOAT,
    borough VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.segment_id,
        ST_Distance(s.geometry::geography, p_point::geography)::FLOAT as distance_m,
        s.material_type,
        s.condition_score,
        s.borough
    FROM sidewalk_segments s
    WHERE ST_DWithin(s.geometry::geography, p_point::geography, p_distance_meters)
    ORDER BY distance_m ASC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Segments in polygon
CREATE OR REPLACE FUNCTION segments_in_polygon(p_polygon GEOMETRY)
RETURNS TABLE (
    segment_id VARCHAR(50),
    material_type VARCHAR(50),
    condition_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.segment_id, s.material_type, s.condition_score
    FROM sidewalk_segments s
    WHERE ST_Intersects(s.geometry, p_polygon);
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Calculate material distribution statistics
CREATE OR REPLACE FUNCTION material_distribution_stats(p_borough VARCHAR DEFAULT NULL)
RETURNS TABLE (
    material_type VARCHAR(50),
    segment_count BIGINT,
    total_length_meters FLOAT,
    percentage FLOAT,
    average_condition FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH totals AS (
        SELECT SUM(length_meters) as total_length
        FROM sidewalk_segments
        WHERE (p_borough IS NULL OR borough = p_borough)
    )
    SELECT 
        s.material_type,
        COUNT(*) as seg_count,
        SUM(s.length_meters) as total_length,
        ROUND(100.0 * SUM(s.length_meters) / 
            NULLIF((SELECT total_length FROM totals), 0), 2) as pct,
        ROUND(AVG(s.condition_score), 2) as avg_cond
    FROM sidewalk_segments s
    WHERE (p_borough IS NULL OR s.borough = p_borough)
    GROUP BY s.material_type
    ORDER BY total_length DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Condition statistics by geography
CREATE OR REPLACE FUNCTION condition_statistics(
    p_borough VARCHAR DEFAULT NULL,
    p_material_type VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    min_score FLOAT,
    max_score FLOAT,
    avg_score FLOAT,
    median_score FLOAT,
    segment_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        MIN(condition_score)::FLOAT,
        MAX(condition_score)::FLOAT,
        ROUND(AVG(condition_score)::NUMERIC, 2)::FLOAT,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY condition_score)::FLOAT,
        COUNT(*)
    FROM sidewalk_segments
    WHERE (p_borough IS NULL OR borough = p_borough)
        AND (p_material_type IS NULL OR material_type = p_material_type);
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Service area (reachable segments within distance)
CREATE OR REPLACE FUNCTION service_area(
    p_center_point GEOMETRY,
    p_distance_meters FLOAT
)
RETURNS TABLE (
    segment_id VARCHAR(50),
    distance_meters FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.segment_id,
        ST_Distance(s.geometry::geography, p_center_point::geography)::FLOAT
    FROM sidewalk_segments s
    WHERE ST_DWithin(s.geometry::geography, p_center_point::geography, p_distance_meters)
    ORDER BY ST_Distance(s.geometry::geography, p_center_point::geography);
END;
$$ LANGUAGE plpgsql STABLE;

-- Function: Inspection density (inspections per km²)
CREATE OR REPLACE FUNCTION inspection_density(p_polygon GEOMETRY)
RETURNS FLOAT AS $$
DECLARE
    area_km2 FLOAT;
    inspection_count INT;
BEGIN
    SELECT ST_Area(p_polygon::geography) / 1000000.0 INTO area_km2;
    SELECT COUNT(*) INTO inspection_count
    FROM inspections i
    WHERE ST_Intersects(i.geometry, p_polygon);
    
    RETURN CASE 
        WHEN area_km2 > 0 THEN inspection_count::FLOAT / area_km2
        ELSE 0
    END;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- TRIGGERS FOR AUDIT AND MAINTENANCE
-- ============================================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sidewalk_segments_update
BEFORE UPDATE ON sidewalk_segments
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_material_zones_update
BEFORE UPDATE ON material_zones
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- ============================================================================
-- CONSTRAINTS AND VALIDATIONS
-- ============================================================================

-- Ensure geometries are valid
ALTER TABLE sidewalk_segments 
    ADD CONSTRAINT chk_segment_geometry_valid 
    CHECK (ST_IsValid(geometry));

ALTER TABLE blocks 
    ADD CONSTRAINT chk_block_geometry_valid 
    CHECK (ST_IsValid(geometry));

ALTER TABLE inspections 
    ADD CONSTRAINT chk_inspection_geometry_valid 
    CHECK (ST_IsValid(geometry));

-- ============================================================================
-- CLUSTER TABLES FOR SPATIAL PERFORMANCE
-- ============================================================================

-- Cluster segments by geometry (improves range query performance)
CLUSTER sidewalk_segments USING idx_sidewalk_segments_geom;

CLUSTER blocks USING idx_blocks_geom;

CLUSTER inspections USING idx_inspections_geom;

-- ============================================================================
-- STATISTICS AND VACUUM CONFIGURATION
-- ============================================================================

-- Analyze tables for query planning
ANALYZE sidewalk_segments;
ANALYZE blocks;
ANALYZE inspections;
ANALYZE material_zones;
ANALYZE hotspots;

-- Set aggressive autovacuum for spatial tables
ALTER TABLE sidewalk_segments SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

ALTER TABLE inspections SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE sidewalk_segments IS 'Primary table for sidewalk segment geometries and attributes';
COMMENT ON COLUMN sidewalk_segments.geometry IS 'LineString geometry in WGS84 (SRID 4326)';
COMMENT ON COLUMN sidewalk_segments.condition_score IS 'Condition score 0-100 where 0=poor, 100=excellent';
COMMENT ON INDEX idx_sidewalk_segments_geom IS 'GiST spatial index for fast geographic queries';

COMMENT ON TABLE blocks IS 'City blocks as polygon geometries';
COMMENT ON TABLE inspections IS 'Point-based inspection records with timestamps';
COMMENT ON TABLE material_zones IS 'Areas of uniform sidewalk material type';
COMMENT ON TABLE hotspots IS 'Problem areas detected through spatial analysis';

-- ============================================================================
-- REFRESH MATERIALIZED VIEWS
-- ============================================================================

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_segments_by_borough;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_segments_by_material;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_block_coverage;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify spatial setup
SELECT 
    current_database() as database,
    PostGIS_version() as postgis_version,
    (SELECT count(*) FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_name LIKE '%sidewalk%') as spatial_tables,
    (SELECT count(*) FROM pg_indexes 
     WHERE schemaname = 'public' AND tablename LIKE '%sidewalk%') as spatial_indexes;

-- Report
\echo 'PostGIS Spatial Schema Migration Complete'
\echo 'Sidewalk segments table created with spatial indexes'
\echo 'Materialized views created for performance'
\echo 'Spatial functions available for queries'
