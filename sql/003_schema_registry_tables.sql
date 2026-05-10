-- Migration: Schema Registry Tables
-- Purpose: Create persistent storage for schema versions and evolution tracking
-- Date: 2026-05-10
-- Version: 1

-- Main schemas table: tracks all registered schemas
CREATE TABLE IF NOT EXISTS public.schemas (
    id BIGSERIAL PRIMARY KEY,
    schema_id VARCHAR(256) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(128),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT schemas_id_check CHECK (schema_id ~ '^[a-zA-Z0-9_\-\.]+$')
);

-- Schema versions table: tracks all versions of each schema
CREATE TABLE IF NOT EXISTS public.schema_versions (
    id BIGSERIAL PRIMARY KEY,
    schema_id VARCHAR(256) NOT NULL REFERENCES public.schemas(schema_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    schema_json JSONB NOT NULL,
    changes_json JSONB DEFAULT '[]',
    is_compatible_with_previous BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(128),
    row_count INTEGER DEFAULT 0,
    notes TEXT,
    UNIQUE(schema_id, version_number),
    CONSTRAINT version_number_positive CHECK (version_number > 0)
);

-- Audit log table: tracks all schema registry operations
CREATE TABLE IF NOT EXISTS public.schema_audit_log (
    id BIGSERIAL PRIMARY KEY,
    schema_id VARCHAR(256),
    operation VARCHAR(64) NOT NULL,
    version_number INTEGER,
    details JSONB DEFAULT '{}',
    breaking_change_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(128),
    severity VARCHAR(32) DEFAULT 'INFO'
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_schemas_id ON public.schemas(schema_id);
CREATE INDEX IF NOT EXISTS idx_schema_versions_schema_id ON public.schema_versions(schema_id);
CREATE INDEX IF NOT EXISTS idx_schema_versions_version ON public.schema_versions(schema_id, version_number);
CREATE INDEX IF NOT EXISTS idx_schema_versions_created_at ON public.schema_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_schema_audit_log_schema_id ON public.schema_audit_log(schema_id);
CREATE INDEX IF NOT EXISTS idx_schema_audit_log_operation ON public.schema_audit_log(operation);
CREATE INDEX IF NOT EXISTS idx_schema_audit_log_created_at ON public.schema_audit_log(created_at);

-- Create a view for the latest schema version per dataset
CREATE OR REPLACE VIEW public.v_latest_schemas AS
SELECT 
    s.schema_id,
    sv.version_number,
    sv.schema_json,
    sv.created_at,
    sv.created_by,
    sv.row_count,
    s.description,
    sv.notes
FROM public.schemas s
LEFT JOIN LATERAL (
    SELECT * 
    FROM public.schema_versions 
    WHERE schema_id = s.schema_id 
    ORDER BY version_number DESC 
    LIMIT 1
) sv ON TRUE;

-- Create a view for schema change history
CREATE OR REPLACE VIEW public.v_schema_history AS
SELECT 
    sv.schema_id,
    sv.version_number as from_version,
    LEAD(sv.version_number) OVER (PARTITION BY sv.schema_id ORDER BY sv.version_number) as to_version,
    sv.created_at,
    sv.created_by,
    sv.is_compatible_with_previous,
    jsonb_array_length(sv.changes_json) as change_count,
    sv.changes_json
FROM public.schema_versions sv
ORDER BY sv.schema_id, sv.version_number;

-- Grant permissions (adjust role names based on your database setup)
-- GRANT SELECT ON public.schemas TO app_reader;
-- GRANT SELECT ON public.schema_versions TO app_reader;
-- GRANT SELECT ON public.schema_audit_log TO app_reader;
-- GRANT ALL ON public.schemas TO app_writer;
-- GRANT ALL ON public.schema_versions TO app_writer;
-- GRANT ALL ON public.schema_audit_log TO app_writer;
-- GRANT SELECT ON public.v_latest_schemas TO app_reader;
-- GRANT SELECT ON public.v_schema_history TO app_reader;
