-- Observability tables for structured logging, metrics, tracing, and SLA tracking
-- Migration: 005_observability_tables.sql

-- Table: observability_logs
-- Stores structured JSON logs with full-text search capability
CREATE TABLE IF NOT EXISTS observability_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) NOT NULL,
    logger_name VARCHAR(255) NOT NULL,
    correlation_id UUID NOT NULL,
    message TEXT NOT NULL,
    context JSONB,
    user_id VARCHAR(255),
    exception TEXT,
    duration_ms NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_observability_logs_timestamp 
    ON observability_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_observability_logs_level 
    ON observability_logs(level);
CREATE INDEX IF NOT EXISTS idx_observability_logs_logger_name 
    ON observability_logs(logger_name);
CREATE INDEX IF NOT EXISTS idx_observability_logs_correlation_id 
    ON observability_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_observability_logs_context 
    ON observability_logs USING GIN(context);
CREATE INDEX IF NOT EXISTS idx_observability_logs_message_fts 
    ON observability_logs USING GIN(to_tsvector('english', message));

-- Table: observability_metrics_hourly
-- Stores aggregated metrics at hourly granularity
CREATE TABLE IF NOT EXISTS observability_metrics_hourly (
    id BIGSERIAL PRIMARY KEY,
    hour TIMESTAMP WITH TIME ZONE NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,  -- counter, gauge, histogram, summary
    labels JSONB,  -- {dataset_id: '...', node_id: '...'}
    value_min NUMERIC,
    value_max NUMERIC,
    value_avg NUMERIC,
    value_sum NUMERIC,
    value_count INTEGER,
    p50 NUMERIC,
    p95 NUMERIC,
    p99 NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for metrics queries
CREATE INDEX IF NOT EXISTS idx_observability_metrics_hourly_hour 
    ON observability_metrics_hourly(hour DESC);
CREATE INDEX IF NOT EXISTS idx_observability_metrics_hourly_metric_name 
    ON observability_metrics_hourly(metric_name);
CREATE INDEX IF NOT EXISTS idx_observability_metrics_hourly_metric_hour 
    ON observability_metrics_hourly(metric_name, hour DESC);
CREATE INDEX IF NOT EXISTS idx_observability_metrics_hourly_labels 
    ON observability_metrics_hourly USING GIN(labels);

-- Table: observability_sla_violations
-- History of SLA breaches for compliance tracking
CREATE TABLE IF NOT EXISTS observability_sla_violations (
    id BIGSERIAL PRIMARY KEY,
    sla_name VARCHAR(255) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    target NUMERIC NOT NULL,
    actual NUMERIC NOT NULL,
    violation_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    time_window VARCHAR(50) NOT NULL,  -- 5m, 1h, 1d
    severity VARCHAR(50) NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for SLA queries
CREATE INDEX IF NOT EXISTS idx_observability_sla_violations_violation_time 
    ON observability_sla_violations(violation_time DESC);
CREATE INDEX IF NOT EXISTS idx_observability_sla_violations_sla_name 
    ON observability_sla_violations(sla_name);
CREATE INDEX IF NOT EXISTS idx_observability_sla_violations_severity 
    ON observability_sla_violations(severity);
CREATE INDEX IF NOT EXISTS idx_observability_sla_violations_unresolved 
    ON observability_sla_violations(sla_name) 
    WHERE resolved_at IS NULL;

-- Table: observability_traces
-- Distributed tracing events
CREATE TABLE IF NOT EXISTS observability_traces (
    id BIGSERIAL PRIMARY KEY,
    trace_id UUID NOT NULL,
    span_id UUID NOT NULL,
    parent_span_id UUID,
    operation_name VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_ms NUMERIC,
    status VARCHAR(50),  -- ok, error, unset
    attributes JSONB,
    error_message TEXT,
    events JSONB,  -- Array of {timestamp, name, attributes}
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for tracing queries
CREATE INDEX IF NOT EXISTS idx_observability_traces_trace_id 
    ON observability_traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_observability_traces_span_id 
    ON observability_traces(span_id);
CREATE INDEX IF NOT EXISTS idx_observability_traces_parent_span_id 
    ON observability_traces(parent_span_id) 
    WHERE parent_span_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_observability_traces_operation_name 
    ON observability_traces(operation_name);
CREATE INDEX IF NOT EXISTS idx_observability_traces_start_time 
    ON observability_traces(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_observability_traces_status 
    ON observability_traces(status);

-- Table: observability_sla_config
-- SLA configuration definitions
CREATE TABLE IF NOT EXISTS observability_sla_config (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL UNIQUE,
    target NUMERIC NOT NULL,
    time_window VARCHAR(50) NOT NULL,  -- 5m, 1h, 1d
    severity VARCHAR(50) NOT NULL,
    channels JSONB,  -- ["email", "slack", "pagerduty"]
    description TEXT,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: observability_health_checks
-- Historical health check results
CREATE TABLE IF NOT EXISTS observability_health_checks (
    id BIGSERIAL PRIMARY KEY,
    component_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- HEALTHY, DEGRADED, UNHEALTHY
    message TEXT,
    duration_ms NUMERIC,
    details JSONB,
    checked_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for health checks
CREATE INDEX IF NOT EXISTS idx_observability_health_checks_component 
    ON observability_health_checks(component_name, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_observability_health_checks_status 
    ON observability_health_checks(status);

-- Table: observability_log_aggregates
-- Daily log summaries for performance
CREATE TABLE IF NOT EXISTS observability_log_aggregates (
    id BIGSERIAL PRIMARY KEY,
    log_date DATE NOT NULL,
    logger_name VARCHAR(255),
    level VARCHAR(20),
    total_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    avg_duration_ms NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for aggregates
CREATE INDEX IF NOT EXISTS idx_observability_log_aggregates_log_date 
    ON observability_log_aggregates(log_date DESC);
CREATE INDEX IF NOT EXISTS idx_observability_log_aggregates_logger_level 
    ON observability_log_aggregates(logger_name, level);

-- Cleanup function: Remove old logs and metrics
CREATE OR REPLACE FUNCTION cleanup_observability_data(days_retention INT DEFAULT 30)
RETURNS TABLE (deleted_logs BIGINT, deleted_metrics BIGINT, deleted_traces BIGINT) AS $$
DECLARE
    cutoff_date TIMESTAMP WITH TIME ZONE;
    logs_deleted BIGINT;
    metrics_deleted BIGINT;
    traces_deleted BIGINT;
BEGIN
    cutoff_date := CURRENT_TIMESTAMP - (days_retention || ' days')::INTERVAL;
    
    DELETE FROM observability_logs WHERE created_at < cutoff_date;
    GET DIAGNOSTICS logs_deleted = ROW_COUNT;
    
    DELETE FROM observability_metrics_hourly WHERE created_at < cutoff_date;
    GET DIAGNOSTICS metrics_deleted = ROW_COUNT;
    
    DELETE FROM observability_traces WHERE created_at < cutoff_date;
    GET DIAGNOSTICS traces_deleted = ROW_COUNT;
    
    RETURN QUERY SELECT logs_deleted, metrics_deleted, traces_deleted;
END;
$$ LANGUAGE plpgsql;

-- View: Recent errors
CREATE OR REPLACE VIEW observability_recent_errors AS
SELECT 
    timestamp,
    correlation_id,
    logger_name,
    message,
    exception,
    duration_ms
FROM observability_logs
WHERE level IN ('ERROR', 'CRITICAL')
    AND timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- View: SLA compliance summary
CREATE OR REPLACE VIEW observability_sla_summary AS
SELECT 
    DATE_TRUNC('hour', violation_time) as hour,
    COUNT(*) as violation_count,
    COUNT(DISTINCT sla_name) as affected_slas,
    COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_count
FROM observability_sla_violations
WHERE resolved_at IS NULL
GROUP BY DATE_TRUNC('hour', violation_time)
ORDER BY hour DESC;

-- View: Performance metrics by hour
CREATE OR REPLACE VIEW observability_performance_hourly AS
SELECT 
    hour,
    metric_name,
    value_avg as avg_value,
    p95 as p95_value,
    p99 as p99_value,
    value_count as observation_count
FROM observability_metrics_hourly
WHERE metric_type IN ('histogram', 'summary')
ORDER BY hour DESC, metric_name;

-- Grants for read-only access (if using separate monitoring user)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO observability_reader;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA public TO observability_reader;
