-- Migration: Data Lineage and Transformation DAG Tracking
-- Purpose: Create persistent storage for complete data lineage, transformation history, and impact analysis
-- Date: 2026-05-10
-- Version: 1

-- Main lineage nodes table: represents data sources, transformations, and sinks
CREATE TABLE IF NOT EXISTS public.lineage_nodes (
    id BIGSERIAL PRIMARY KEY,
    node_id VARCHAR(256) NOT NULL UNIQUE,
    name VARCHAR(512) NOT NULL,
    node_type VARCHAR(64) NOT NULL,
    description TEXT,
    owner VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    configuration JSONB DEFAULT '{}',
    schema_version VARCHAR(256),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    CONSTRAINT node_type_valid CHECK (node_type IN ('ingestion', 'transformation', 'sink', 'validation', 'materialization', 'aggregation')),
    CONSTRAINT node_id_format CHECK (node_id ~ '^[a-zA-Z0-9_\-]+$')
);

-- Lineage edges table: represents dependencies between nodes
CREATE TABLE IF NOT EXISTS public.lineage_edges (
    id BIGSERIAL PRIMARY KEY,
    source_node_id VARCHAR(256) NOT NULL REFERENCES public.lineage_nodes(node_id) ON DELETE CASCADE,
    target_node_id VARCHAR(256) NOT NULL REFERENCES public.lineage_nodes(node_id) ON DELETE CASCADE,
    edge_type VARCHAR(64) NOT NULL DEFAULT 'data_flow',
    cardinality VARCHAR(32) DEFAULT '1:1',
    join_keys JSONB DEFAULT '[]',
    filter_conditions TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT edge_type_valid CHECK (edge_type IN ('dependency', 'data_flow', 'schema_dependency')),
    CONSTRAINT cardinality_valid CHECK (cardinality IN ('1:1', '1:N', 'N:1', 'N:N')),
    UNIQUE(source_node_id, target_node_id)
);

-- Execution history table: tracks every execution of a transformation
CREATE TABLE IF NOT EXISTS public.lineage_execution_history (
    id BIGSERIAL PRIMARY KEY,
    execution_id VARCHAR(256) NOT NULL UNIQUE,
    node_id VARCHAR(256) NOT NULL REFERENCES public.lineage_nodes(node_id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DOUBLE PRECISION DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    input_row_count BIGINT DEFAULT 0,
    output_row_count BIGINT DEFAULT 0,
    error_message TEXT,
    data_quality_metrics JSONB DEFAULT '{}',
    executed_by VARCHAR(256),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT status_valid CHECK (status IN ('running', 'success', 'failed', 'partial', 'skipped'))
);

-- Lineage audit log table: tracks all changes to lineage structure
CREATE TABLE IF NOT EXISTS public.lineage_audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    node_id VARCHAR(256),
    edge_source_id VARCHAR(256),
    edge_target_id VARCHAR(256),
    old_value JSONB,
    new_value JSONB,
    change_details JSONB DEFAULT '{}',
    created_by VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT event_type_valid CHECK (event_type IN ('node_created', 'node_updated', 'node_deleted', 'edge_created', 'edge_deleted', 'execution_recorded'))
);

-- Data quality metrics snapshots table
CREATE TABLE IF NOT EXISTS public.lineage_quality_metrics (
    id BIGSERIAL PRIMARY KEY,
    execution_id VARCHAR(256) NOT NULL REFERENCES public.lineage_execution_history(execution_id) ON DELETE CASCADE,
    node_id VARCHAR(256) NOT NULL,
    metric_name VARCHAR(128) NOT NULL,
    metric_value DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    is_anomaly BOOLEAN DEFAULT FALSE,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Impact analysis cache table: stores pre-computed impact analysis results
CREATE TABLE IF NOT EXISTS public.lineage_impact_analysis (
    id BIGSERIAL PRIMARY KEY,
    node_id VARCHAR(256) NOT NULL REFERENCES public.lineage_nodes(node_id) ON DELETE CASCADE,
    affected_nodes JSONB NOT NULL DEFAULT '[]',
    affected_users JSONB DEFAULT '[]',
    critical_paths JSONB DEFAULT '[]',
    estimated_impact_score DOUBLE PRECISION DEFAULT 0,
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(node_id)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_id ON public.lineage_nodes(node_id);
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_type ON public.lineage_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_owner ON public.lineage_nodes(owner);
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_created ON public.lineage_nodes(created_at);

CREATE INDEX IF NOT EXISTS idx_lineage_edges_source ON public.lineage_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_target ON public.lineage_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_type ON public.lineage_edges(edge_type);

CREATE INDEX IF NOT EXISTS idx_execution_node ON public.lineage_execution_history(node_id);
CREATE INDEX IF NOT EXISTS idx_execution_status ON public.lineage_execution_history(status);
CREATE INDEX IF NOT EXISTS idx_execution_started ON public.lineage_execution_history(started_at);
CREATE INDEX IF NOT EXISTS idx_execution_id ON public.lineage_execution_history(execution_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_event ON public.lineage_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_node ON public.lineage_audit_log(node_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON public.lineage_audit_log(created_at);

CREATE INDEX IF NOT EXISTS idx_quality_metrics_execution ON public.lineage_quality_metrics(execution_id);
CREATE INDEX IF NOT EXISTS idx_quality_metrics_node ON public.lineage_quality_metrics(node_id);
CREATE INDEX IF NOT EXISTS idx_quality_metrics_anomaly ON public.lineage_quality_metrics(is_anomaly);

-- Create JSON GIN indexes for advanced queries
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_tags ON public.lineage_nodes USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_lineage_nodes_config ON public.lineage_nodes USING GIN (configuration);
CREATE INDEX IF NOT EXISTS idx_execution_metrics ON public.lineage_execution_history USING GIN (data_quality_metrics);
