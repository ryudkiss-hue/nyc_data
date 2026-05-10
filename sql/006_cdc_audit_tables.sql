-- PostgreSQL Migration: CDC and Audit Trail Tables
-- Created: 2026-05-10
-- Purpose: Implement Change Data Capture and SCD Type 2 patterns with audit trails

-- 1. Audit Trail Table (Immutable Event Log)
CREATE TABLE IF NOT EXISTS public.audit_trail (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_name VARCHAR(255) NOT NULL DEFAULT 'SYSTEM',
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(255) NOT NULL,
    entity_id VARCHAR(1024) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    diff JSONB,
    reason TEXT,
    lineage_node_id UUID,
    correlation_id UUID,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit trail queries
CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON public.audit_trail(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trail_entity ON public.audit_trail(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_user ON public.audit_trail(user_name);
CREATE INDEX IF NOT EXISTS idx_audit_trail_action ON public.audit_trail(action);
CREATE INDEX IF NOT EXISTS idx_audit_trail_change_type ON public.audit_trail(change_type);
CREATE INDEX IF NOT EXISTS idx_audit_trail_correlation ON public.audit_trail(correlation_id);

-- Create GIN index for JSONB search
CREATE INDEX IF NOT EXISTS idx_audit_trail_old_values ON public.audit_trail USING GIN(old_values);
CREATE INDEX IF NOT EXISTS idx_audit_trail_new_values ON public.audit_trail USING GIN(new_values);

-- Partitioning strategy for large tables (monthly)
CREATE TABLE IF NOT EXISTS public.audit_trail_partition_template () PARTITION OF public.audit_trail DEFAULT;

-- Make audit_trail immutable (prevent updates/deletes)
CREATE OR REPLACE RULE audit_trail_no_update AS ON UPDATE TO public.audit_trail
    DO INSTEAD NOTHING;
CREATE OR REPLACE RULE audit_trail_no_delete AS ON DELETE TO public.audit_trail
    DO INSTEAD NOTHING;

-- 2. CDC Events Table (Immutable Change Log)
CREATE TABLE IF NOT EXISTS public.cdc_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_dataset VARCHAR(255) NOT NULL,
    operation VARCHAR(20) NOT NULL,
    record_id VARCHAR(1024) NOT NULL,
    timestamp_ms BIGINT NOT NULL,
    before_values JSONB,
    after_values JSONB,
    metadata JSONB,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for CDC queries
CREATE INDEX IF NOT EXISTS idx_cdc_events_dataset ON public.cdc_events(source_dataset);
CREATE INDEX IF NOT EXISTS idx_cdc_events_operation ON public.cdc_events(operation);
CREATE INDEX IF NOT EXISTS idx_cdc_events_timestamp ON public.cdc_events(timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_cdc_events_record ON public.cdc_events(record_id);
CREATE INDEX IF NOT EXISTS idx_cdc_events_created ON public.cdc_events(created_at DESC);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_cdc_events_dataset_operation ON public.cdc_events(source_dataset, operation, timestamp_ms DESC);

-- Make CDC events immutable
CREATE OR REPLACE RULE cdc_events_no_update AS ON UPDATE TO public.cdc_events
    DO INSTEAD NOTHING;
CREATE OR REPLACE RULE cdc_events_no_delete AS ON DELETE TO public.cdc_events
    DO INSTEAD NOTHING;

-- 3. CDC Watermarks Table (Track Processing Position)
CREATE TABLE IF NOT EXISTS public.cdc_watermarks (
    watermark_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_dataset VARCHAR(255) NOT NULL UNIQUE,
    last_processed_event_id UUID,
    last_processed_timestamp_ms BIGINT,
    checkpoint_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cdc_watermarks_dataset ON public.cdc_watermarks(source_dataset);

-- 4. SCD Type 2 Template Table
-- This is a template; actual tables will be created per dataset
CREATE TABLE IF NOT EXISTS public.scd_type2_template (
    scd_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_key VARCHAR(1024) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    scd_hash VARCHAR(32),
    data_values JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for SCD Type 2
CREATE INDEX IF NOT EXISTS idx_scd_template_business_key ON public.scd_type2_template(business_key);
CREATE INDEX IF NOT EXISTS idx_scd_template_current ON public.scd_type2_template(business_key, is_current);
CREATE INDEX IF NOT EXISTS idx_scd_template_dates ON public.scd_type2_template(business_key, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_scd_template_hash ON public.scd_type2_template(scd_hash);

-- 5. Soft Delete Tracking Table
CREATE TABLE IF NOT EXISTS public.soft_delete_log (
    soft_delete_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(255) NOT NULL,
    record_id VARCHAR(1024) NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_by VARCHAR(255) DEFAULT 'SYSTEM',
    delete_reason TEXT,
    retention_days INT DEFAULT 90,
    hard_delete_scheduled_at TIMESTAMP WITH TIME ZONE,
    backup_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_soft_delete_table_record ON public.soft_delete_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_soft_delete_deleted_at ON public.soft_delete_log(deleted_at DESC);
CREATE INDEX IF NOT EXISTS idx_soft_delete_scheduled ON public.soft_delete_log(hard_delete_scheduled_at);

-- 6. Change Detection Tracking Table
-- Tracks which records have changed and need SCD updates
CREATE TABLE IF NOT EXISTS public.change_detection_log (
    detection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(255) NOT NULL,
    last_check TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    records_changed INT DEFAULT 0,
    records_added INT DEFAULT 0,
    records_deleted INT DEFAULT 0,
    detection_status VARCHAR(50) DEFAULT 'SUCCESS',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_change_detection_dataset ON public.change_detection_log(dataset_id, last_check DESC);

-- 7. Views for Common Queries

-- View: Current records (not soft-deleted, is_current = true)
CREATE OR REPLACE VIEW public.v_current_records AS
SELECT 
    table_name,
    record_id,
    COUNT(*) as count
FROM public.cdc_events
WHERE operation IN ('INSERT', 'UPDATE')
GROUP BY table_name, record_id
ORDER BY table_name, record_id;

-- View: Deleted records (soft deleted)
CREATE OR REPLACE VIEW public.v_deleted_records AS
SELECT 
    sdl.table_name,
    sdl.record_id,
    sdl.deleted_at,
    sdl.deleted_by,
    sdl.delete_reason,
    CURRENT_TIMESTAMP - sdl.deleted_at as deletion_age_days
FROM public.soft_delete_log sdl
WHERE sdl.hard_delete_scheduled_at IS NULL OR sdl.hard_delete_scheduled_at > CURRENT_TIMESTAMP
ORDER BY sdl.deleted_at DESC;

-- View: Change summary (counts by type, date)
CREATE OR REPLACE VIEW public.v_change_summary AS
SELECT 
    DATE(at.timestamp) as change_date,
    at.action,
    at.change_type,
    COUNT(*) as total_changes,
    COUNT(DISTINCT at.entity_id) as unique_entities,
    COUNT(DISTINCT at.user_name) as unique_users
FROM public.audit_trail at
GROUP BY DATE(at.timestamp), at.action, at.change_type
ORDER BY change_date DESC, action, change_type;

-- View: Audit trail by entity
CREATE OR REPLACE VIEW public.v_audit_by_entity AS
SELECT 
    at.entity_type,
    at.entity_id,
    COUNT(*) as total_changes,
    MAX(at.timestamp) as last_change,
    COUNT(DISTINCT at.user_name) as users_modified,
    ARRAY_AGG(DISTINCT at.action) as actions
FROM public.audit_trail at
GROUP BY at.entity_type, at.entity_id
ORDER BY last_change DESC;

-- 8. Helper Functions

-- Function to calculate hash of data for SCD
CREATE OR REPLACE FUNCTION public.calculate_scd_hash(data JSONB)
RETURNS VARCHAR(32) AS $$
BEGIN
    RETURN MD5(data::TEXT);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to get current version of SCD record
CREATE OR REPLACE FUNCTION public.get_scd_current(
    p_table_name VARCHAR,
    p_business_key VARCHAR
)
RETURNS TABLE(
    scd_id UUID,
    business_key VARCHAR,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN,
    scd_hash VARCHAR,
    data_values JSONB
) AS $$
BEGIN
    -- This is a template function; actual implementation per table
    RETURN QUERY
    SELECT 
        st.scd_id::UUID,
        st.business_key::VARCHAR,
        st.start_date,
        st.end_date,
        st.is_current,
        st.scd_hash,
        st.data_values
    FROM public.scd_type2_template st
    WHERE st.business_key = p_business_key
      AND st.is_current = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get SCD record as of date
CREATE OR REPLACE FUNCTION public.get_scd_as_of(
    p_table_name VARCHAR,
    p_business_key VARCHAR,
    p_as_of_date TIMESTAMP WITH TIME ZONE
)
RETURNS TABLE(
    scd_id UUID,
    business_key VARCHAR,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN,
    scd_hash VARCHAR,
    data_values JSONB
) AS $$
BEGIN
    -- This is a template function; actual implementation per table
    RETURN QUERY
    SELECT 
        st.scd_id::UUID,
        st.business_key::VARCHAR,
        st.start_date,
        st.end_date,
        st.is_current,
        st.scd_hash,
        st.data_values
    FROM public.scd_type2_template st
    WHERE st.business_key = p_business_key
      AND st.start_date <= p_as_of_date
      AND (st.end_date IS NULL OR st.end_date > p_as_of_date)
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get SCD history
CREATE OR REPLACE FUNCTION public.get_scd_history(
    p_table_name VARCHAR,
    p_business_key VARCHAR
)
RETURNS TABLE(
    scd_id UUID,
    business_key VARCHAR,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN,
    scd_hash VARCHAR,
    data_values JSONB
) AS $$
BEGIN
    -- This is a template function; actual implementation per table
    RETURN QUERY
    SELECT 
        st.scd_id::UUID,
        st.business_key::VARCHAR,
        st.start_date,
        st.end_date,
        st.is_current,
        st.scd_hash,
        st.data_values
    FROM public.scd_type2_template st
    WHERE st.business_key = p_business_key
    ORDER BY st.start_date DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- 9. Grants
GRANT SELECT ON ALL TABLES IN SCHEMA public TO PUBLIC;
GRANT SELECT ON ALL VIEWS IN SCHEMA public TO PUBLIC;

-- End of Migration 006
