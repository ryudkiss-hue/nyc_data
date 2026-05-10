-- NYC Data Toolkit PostgreSQL Initialization
-- This script runs automatically on first startup
-- Includes all schema migrations and sample data seeding

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS jsonb_utils;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create sample demo users and API keys
CREATE TABLE IF NOT EXISTS demo_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS demo_api_keys (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES demo_users(id),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert demo users
INSERT INTO demo_users (username, email) VALUES 
    ('demo_admin', 'admin@nyc.local'),
    ('demo_developer', 'dev@nyc.local'),
    ('demo_analyst', 'analyst@nyc.local')
ON CONFLICT (username) DO NOTHING;

-- Insert demo API keys
INSERT INTO demo_api_keys (key, user_id, description) VALUES 
    ('sk_test_demo_admin_abc123', 1, 'Demo admin API key'),
    ('sk_test_demo_developer_def456', 2, 'Demo developer API key'),
    ('sk_test_demo_analyst_ghi789', 3, 'Demo analyst API key')
ON CONFLICT (key) DO NOTHING;

-- Create sample dataset tracking tables
CREATE TABLE IF NOT EXISTS sample_datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    record_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample: Sidewalk Inspections
CREATE TABLE IF NOT EXISTS sidewalk_inspections (
    id SERIAL PRIMARY KEY,
    inspection_id VARCHAR(255) UNIQUE,
    block_id INTEGER,
    lot_id INTEGER,
    bin VARCHAR(20),
    location GEOGRAPHY(POINT, 4326),
    inspection_date DATE,
    inspector_id VARCHAR(50),
    material_type VARCHAR(100),
    condition_rating VARCHAR(20),
    ada_compliant BOOLEAN,
    defect_count INTEGER DEFAULT 0,
    repair_priority VARCHAR(20),
    estimated_repair_cost NUMERIC(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sidewalk_inspection_date ON sidewalk_inspections(inspection_date);
CREATE INDEX IF NOT EXISTS idx_sidewalk_material ON sidewalk_inspections(material_type);
CREATE INDEX IF NOT EXISTS idx_sidewalk_ada ON sidewalk_inspections(ada_compliant);
CREATE INDEX IF NOT EXISTS idx_sidewalk_location ON sidewalk_inspections USING GIST(location);

-- Sample: 311 Complaints
CREATE TABLE IF NOT EXISTS complaints_311 (
    id SERIAL PRIMARY KEY,
    complaint_id VARCHAR(255) UNIQUE,
    complaint_type VARCHAR(100),
    location GEOGRAPHY(POINT, 4326),
    created_date DATE,
    status VARCHAR(50),
    resolution_date DATE,
    agency VARCHAR(100),
    zip_code VARCHAR(10),
    borough VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_complaints_type ON complaints_311(complaint_type);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints_311(status);
CREATE INDEX IF NOT EXISTS idx_complaints_date ON complaints_311(created_date);
CREATE INDEX IF NOT EXISTS idx_complaints_location ON complaints_311 USING GIST(location);

-- Sample: Contractors
CREATE TABLE IF NOT EXISTS contractors (
    id SERIAL PRIMARY KEY,
    contractor_id VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    license_number VARCHAR(50),
    license_status VARCHAR(50),
    specialty VARCHAR(100),
    years_active INTEGER,
    projects_completed INTEGER DEFAULT 0,
    quality_score NUMERIC(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample sidewalk inspection data (1000 records)
INSERT INTO sidewalk_inspections (
    inspection_id, block_id, lot_id, bin, location, inspection_date,
    inspector_id, material_type, condition_rating, ada_compliant,
    defect_count, repair_priority, estimated_repair_cost
)
SELECT
    'INSP_' || LPAD((ROW_NUMBER() OVER ())::text, 6, '0'),
    (RANDOM() * 10000)::INTEGER,
    (RANDOM() * 1000)::INTEGER,
    'BIN_' || LPAD((RANDOM() * 100000)::INTEGER::text, 8, '0'),
    ST_SetSRID(ST_MakePoint(-74.0 + (RANDOM() * 0.04), 40.7 + (RANDOM() * 0.04)), 4326),
    CURRENT_DATE - (RANDOM() * 365)::INTEGER,
    'INSP_' || (RANDOM() * 100)::INTEGER,
    CASE (RANDOM() * 4)::INTEGER
        WHEN 0 THEN 'Concrete'
        WHEN 1 THEN 'Asphalt'
        WHEN 2 THEN 'Granite'
        ELSE 'Brick'
    END,
    CASE (RANDOM() * 3)::INTEGER
        WHEN 0 THEN 'Good'
        WHEN 1 THEN 'Fair'
        ELSE 'Poor'
    END,
    (RANDOM() > 0.3),
    (RANDOM() * 20)::INTEGER,
    CASE (RANDOM() * 3)::INTEGER
        WHEN 0 THEN 'High'
        WHEN 1 THEN 'Medium'
        ELSE 'Low'
    END,
    (RANDOM() * 10000)::NUMERIC(12,2)
FROM GENERATE_SERIES(1, 1000);

-- Insert sample 311 complaint data (500 records)
INSERT INTO complaints_311 (
    complaint_id, complaint_type, location, created_date,
    status, resolution_date, agency, zip_code, borough
)
SELECT
    'COMPL_' || LPAD((ROW_NUMBER() OVER ())::text, 6, '0'),
    CASE (RANDOM() * 5)::INTEGER
        WHEN 0 THEN 'Sidewalk Damage'
        WHEN 1 THEN 'Pothole'
        WHEN 2 THEN 'Street Light'
        WHEN 3 THEN 'Illegal Dumping'
        ELSE 'Curb Damage'
    END,
    ST_SetSRID(ST_MakePoint(-74.0 + (RANDOM() * 0.04), 40.7 + (RANDOM() * 0.04)), 4326),
    CURRENT_DATE - (RANDOM() * 180)::INTEGER,
    CASE (RANDOM() * 3)::INTEGER
        WHEN 0 THEN 'Open'
        WHEN 1 THEN 'In Progress'
        ELSE 'Closed'
    END,
    CASE WHEN RANDOM() > 0.5 THEN CURRENT_DATE - (RANDOM() * 180)::INTEGER ELSE NULL END,
    'NYC DOT',
    LPAD((10000 + (RANDOM() * 10000)::INTEGER)::text, 5, '0'),
    CASE (RANDOM() * 5)::INTEGER
        WHEN 0 THEN 'Manhattan'
        WHEN 1 THEN 'Brooklyn'
        WHEN 2 THEN 'Queens'
        WHEN 3 THEN 'Bronx'
        ELSE 'Staten Island'
    END
FROM GENERATE_SERIES(1, 500);

-- Insert sample contractor data (50 records)
INSERT INTO contractors (
    contractor_id, name, license_number, license_status,
    specialty, years_active, projects_completed, quality_score
)
SELECT
    'CONTR_' || LPAD((ROW_NUMBER() OVER ())::text, 4, '0'),
    'Contractor ' || (ROW_NUMBER() OVER ()),
    'LIC_' || LPAD((RANDOM() * 100000)::INTEGER::text, 8, '0'),
    CASE WHEN RANDOM() > 0.2 THEN 'Active' ELSE 'Inactive' END,
    CASE (RANDOM() * 3)::INTEGER
        WHEN 0 THEN 'Sidewalk Repair'
        WHEN 1 THEN 'Street Construction'
        ELSE 'Utility Work'
    END,
    (RANDOM() * 20)::INTEGER + 1,
    (RANDOM() * 500)::INTEGER,
    ROUND((RANDOM() * 0.5 + 0.5)::NUMERIC, 2)
FROM GENERATE_SERIES(1, 50);

-- Update sample datasets table
INSERT INTO sample_datasets (name, description, record_count) VALUES
    ('Sidewalk Inspections', 'Sample sidewalk inspection records from NYC DOT', 1000),
    ('311 Complaints', 'Sample 311 service requests', 500),
    ('Contractors', 'Sample contractor master data', 50)
ON CONFLICT DO NOTHING;

-- Create audit logging table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255),
    operation VARCHAR(10),
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create quality metrics table
CREATE TABLE IF NOT EXISTS quality_metrics (
    id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(255),
    metric_name VARCHAR(255),
    metric_value NUMERIC(10, 4),
    measurement_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample quality metrics
INSERT INTO quality_metrics (dataset_name, metric_name, metric_value) VALUES
    ('sidewalk_inspections', 'completeness', 99.2),
    ('sidewalk_inspections', 'validity', 98.8),
    ('sidewalk_inspections', 'consistency', 99.5),
    ('complaints_311', 'completeness', 97.5),
    ('complaints_311', 'validity', 98.2),
    ('complaints_311', 'consistency', 98.0);

-- Create data lineage tracking table
CREATE TABLE IF NOT EXISTS data_lineage (
    id SERIAL PRIMARY KEY,
    source_dataset VARCHAR(255),
    target_dataset VARCHAR(255),
    transformation VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample lineage
INSERT INTO data_lineage (source_dataset, target_dataset, transformation) VALUES
    ('sidewalk_inspections', 'compliance_metrics', 'ADA compliance calculation'),
    ('sidewalk_inspections', 'material_analytics', 'Material type aggregation'),
    ('complaints_311', 'complaint_metrics', 'Status aggregation'),
    ('contractors', 'contractor_metrics', 'Quality score analysis');

COMMIT;
