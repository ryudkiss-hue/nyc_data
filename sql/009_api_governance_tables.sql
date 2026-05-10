/**
 * SQL Migration: API Governance, Authentication, and Versioning Tables
 * Phase 2, Weeks 11-12: API Security & Governance
 * 
 * Creates tables for:
 * - User and Service Principal authentication
 * - API keys and JWT token management
 * - Role-based access control (RBAC)
 * - Rate limiting and quota management
 * - API usage tracking and audit logs
 * - Data governance policies
 * - PII field mappings and masking rules
 * - API versioning and schema tracking
 * 
 * This migration supports production-grade API security with:
 * - Stateless JWT authentication
 * - Stateful API key authentication
 * - Role and permission hierarchy
 * - Redis-backed rate limiting with database fallback
 * - Complete audit trail of API requests
 * - Data masking and classification
 * - API version lifecycle management
 */

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ====================================================================
-- A. API USERS & AUTHENTICATION
-- ====================================================================

/**
 * api_users: Core user account table
 * Stores authenticated users with roles and permissions
 */
CREATE TABLE IF NOT EXISTS api_users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, suspended, revoked, inactive
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP,
    api_key_count INT DEFAULT 0,
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX IF NOT EXISTS idx_api_users_email ON api_users(email);
CREATE INDEX IF NOT EXISTS idx_api_users_status ON api_users(status);
CREATE INDEX IF NOT EXISTS idx_api_users_created_at ON api_users(created_at);

/**
 * api_service_principals: Service accounts for programmatic access
 * Used for background jobs, third-party integrations, etc.
 */
CREATE TABLE IF NOT EXISTS api_service_principals (
    service_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    owner_user_id UUID NOT NULL REFERENCES api_users(user_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, suspended, revoked
    rate_limit_tier VARCHAR(50) DEFAULT 'standard',  -- guest, standard, premium, custom
    custom_rate_limit INT,  -- requests per hour, if tier=custom
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb  -- extra config as JSON
);

CREATE INDEX IF NOT EXISTS idx_service_principals_name ON api_service_principals(name);
CREATE INDEX IF NOT EXISTS idx_service_principals_status ON api_service_principals(status);
CREATE INDEX IF NOT EXISTS idx_service_principals_owner ON api_service_principals(owner_user_id);

-- ====================================================================
-- B. API KEYS & CREDENTIALS
-- ====================================================================

/**
 * api_keys: API key storage (secrets hashed with bcrypt)
 * Supports stateful authentication independent of JWT
 */
CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_prefix VARCHAR(8) NOT NULL UNIQUE,  -- First 8 chars, for UI display
    key_hash VARCHAR(255) NOT NULL UNIQUE,  -- bcrypt hash, never exposed
    user_id UUID REFERENCES api_users(user_id) ON DELETE CASCADE,
    service_id UUID REFERENCES api_service_principals(service_id) ON DELETE CASCADE,
    name VARCHAR(255),  -- User-friendly name
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, revoked, expired
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    usage_count INT DEFAULT 0,
    created_by_user_id UUID REFERENCES api_users(user_id),
    CONSTRAINT key_belongs_to_someone CHECK (
        (user_id IS NOT NULL AND service_id IS NULL) OR
        (user_id IS NULL AND service_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_service_id ON api_keys(service_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);
CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON api_keys(created_at);

-- ====================================================================
-- C. ROLES & PERMISSIONS
-- ====================================================================

/**
 * api_roles: Role definitions
 * Defines role names and their permission bundles
 */
CREATE TABLE IF NOT EXISTS api_roles (
    role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,  -- Cannot be modified if TRUE
    permissions_json JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Array of permission strings
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_roles_name ON api_roles(name);

-- Insert default system roles
INSERT INTO api_roles (name, description, is_system_role, permissions_json) VALUES
    ('GUEST', 'Limited READ on public data', TRUE, '["datasets:read:public"]'::jsonb),
    ('DATA_CONSUMER', 'READ on all data', TRUE, '["datasets:read", "reports:read"]'::jsonb),
    ('DATA_ENGINEER', 'READ+WRITE on assigned datasets', TRUE, '["datasets:read", "datasets:write", "records:write", "reports:read"]'::jsonb),
    ('ADMIN', 'Full access to all resources', TRUE, '["*"]'::jsonb),
    ('SERVICE_ACCOUNT', 'Programmatic access with specific permissions', TRUE, '["datasets:read"]'::jsonb)
ON CONFLICT (name) DO NOTHING;

/**
 * api_permissions: Individual permission definitions
 * Fine-grained permissions that map to resource + action combinations
 */
CREATE TABLE IF NOT EXISTS api_permissions (
    permission_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource VARCHAR(100) NOT NULL,  -- datasets, records, reports, admin, etc.
    action VARCHAR(50) NOT NULL,  -- read, write, delete, admin, export
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_resource_action UNIQUE (resource, action)
);

CREATE INDEX IF NOT EXISTS idx_api_permissions_resource ON api_permissions(resource);
CREATE INDEX IF NOT EXISTS idx_api_permissions_action ON api_permissions(action);

-- Insert default permissions
INSERT INTO api_permissions (resource, action, description) VALUES
    ('datasets', 'read', 'Read dataset metadata and records'),
    ('datasets', 'write', 'Create and modify datasets'),
    ('datasets', 'delete', 'Delete datasets'),
    ('datasets', 'admin', 'Administer datasets'),
    ('datasets', 'export', 'Export dataset data'),
    ('records', 'read', 'Read individual records'),
    ('records', 'write', 'Create and modify records'),
    ('records', 'delete', 'Delete records'),
    ('reports', 'read', 'Read reports'),
    ('reports', 'write', 'Create and modify reports'),
    ('admin', 'manage_users', 'Manage API users'),
    ('admin', 'manage_keys', 'Manage API keys'),
    ('admin', 'view_audit_logs', 'View audit logs'),
    ('admin', 'manage_quotas', 'Manage rate limits and quotas')
ON CONFLICT (resource, action) DO NOTHING;

/**
 * api_user_roles: Junction table mapping users to roles
 * Users can have multiple roles
 */
CREATE TABLE IF NOT EXISTS api_user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES api_users(user_id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES api_roles(role_id) ON DELETE CASCADE,
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    granted_by_user_id UUID REFERENCES api_users(user_id),
    revoked_at TIMESTAMP,
    revoked_by_user_id UUID REFERENCES api_users(user_id),
    CONSTRAINT unique_user_role UNIQUE (user_id, role_id),
    CONSTRAINT revoke_consistency CHECK (
        (revoked_at IS NULL AND revoked_by_user_id IS NULL) OR
        (revoked_at IS NOT NULL AND revoked_by_user_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON api_user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON api_user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_granted_at ON api_user_roles(granted_at);

/**
 * api_service_principal_roles: Roles for service principals
 */
CREATE TABLE IF NOT EXISTS api_service_principal_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_id UUID NOT NULL REFERENCES api_service_principals(service_id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES api_roles(role_id) ON DELETE CASCADE,
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_service_role UNIQUE (service_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_service_roles_service_id ON api_service_principal_roles(service_id);
CREATE INDEX IF NOT EXISTS idx_service_roles_role_id ON api_service_principal_roles(role_id);

-- ====================================================================
-- D. RATE LIMITING & QUOTAS
-- ====================================================================

/**
 * api_rate_limits: Per-user rate limit configuration
 * Stores current quota tier and limits
 */
CREATE TABLE IF NOT EXISTS api_rate_limits (
    rate_limit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES api_users(user_id) ON DELETE CASCADE,
    service_id UUID UNIQUE REFERENCES api_service_principals(service_id) ON DELETE CASCADE,
    tier VARCHAR(50) NOT NULL DEFAULT 'standard',  -- guest, standard, premium, unlimited
    requests_per_hour INT NOT NULL DEFAULT 1000,
    requests_per_day INT NOT NULL DEFAULT 10000,
    requests_per_month INT NOT NULL DEFAULT 500000,
    concurrent_requests INT DEFAULT 10,
    burst_capacity INT DEFAULT 100,  -- Token bucket burst size
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT limit_belongs_to_someone CHECK (
        (user_id IS NOT NULL AND service_id IS NULL) OR
        (user_id IS NULL AND service_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_user_id ON api_rate_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_rate_limits_service_id ON api_rate_limits(service_id);

/**
 * api_quota_usage: Current usage tracking (for analytics, may be in Redis in production)
 * This is a fallback when Redis is unavailable
 */
CREATE TABLE IF NOT EXISTS api_quota_usage (
    usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES api_users(user_id) ON DELETE CASCADE,
    service_id UUID REFERENCES api_service_principals(service_id) ON DELETE CASCADE,
    hour_key VARCHAR(20) NOT NULL,  -- YYYY-MM-DD-HH format
    day_key VARCHAR(20) NOT NULL,   -- YYYY-MM-DD format
    month_key VARCHAR(20) NOT NULL,  -- YYYY-MM format
    requests_this_hour INT DEFAULT 0,
    requests_this_day INT DEFAULT 0,
    requests_this_month INT DEFAULT 0,
    last_request_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT usage_belongs_to_someone CHECK (
        (user_id IS NOT NULL AND service_id IS NULL) OR
        (user_id IS NULL AND service_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_quota_usage_user_id ON api_quota_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_quota_usage_service_id ON api_quota_usage(service_id);
CREATE INDEX IF NOT EXISTS idx_quota_usage_hour_key ON api_quota_usage(hour_key);

-- ====================================================================
-- E. API USAGE TRACKING & METRICS
-- ====================================================================

/**
 * api_usage_log: Comprehensive logging of all API requests
 * Used for:
 * - Usage analytics and chargeback
 * - Performance monitoring
 * - Security auditing
 * - Consumer-specific insights
 */
CREATE TABLE IF NOT EXISTS api_usage_log (
    usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES api_users(user_id) ON DELETE SET NULL,
    service_id UUID REFERENCES api_service_principals(service_id) ON DELETE SET NULL,
    api_key_id UUID REFERENCES api_keys(key_id) ON DELETE SET NULL,
    request_id VARCHAR(100) NOT NULL UNIQUE,  -- Correlation ID
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    method VARCHAR(10) NOT NULL,  -- GET, POST, etc.
    endpoint VARCHAR(500) NOT NULL,
    api_version VARCHAR(20),  -- v1, v2, etc.
    status_code INT,
    latency_ms FLOAT,  -- Response time in milliseconds
    records_returned INT,
    records_processed INT,
    request_size_bytes INT,
    response_size_bytes INT,
    error_message TEXT,
    rate_limit_remaining INT,
    rate_limit_reset TIMESTAMP,
    dataset_ids TEXT[],  -- Datasets accessed
    user_agent VARCHAR(1000),
    ip_address INET,
    metadata JSONB DEFAULT '{}'::jsonb  -- Extra request metadata
);

CREATE INDEX IF NOT EXISTS idx_usage_log_user_id ON api_usage_log(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_log_service_id ON api_usage_log(service_id);
CREATE INDEX IF NOT EXISTS idx_usage_log_timestamp ON api_usage_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_usage_log_endpoint ON api_usage_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_usage_log_status_code ON api_usage_log(status_code);
CREATE INDEX IF NOT EXISTS idx_usage_log_request_id ON api_usage_log(request_id);

-- ====================================================================
-- F. API AUDIT TRAIL
-- ====================================================================

/**
 * api_audit_log: Complete audit trail of authentication and authorization decisions
 * Immutable log for compliance and forensics
 */
CREATE TABLE IF NOT EXISTS api_audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    actor_user_id UUID REFERENCES api_users(user_id) ON DELETE SET NULL,
    actor_service_id UUID REFERENCES api_service_principals(service_id) ON DELETE SET NULL,
    actor_type VARCHAR(20) NOT NULL,  -- user, service, system
    action VARCHAR(100) NOT NULL,  -- auth_attempt, role_grant, key_revoke, etc.
    resource VARCHAR(255),  -- What was affected (user_id, api_key_id, etc.)
    result VARCHAR(50) NOT NULL,  -- success, failure, denied
    reason TEXT,  -- Why it succeeded or failed
    ip_address INET,
    user_agent VARCHAR(1000),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_actor CHECK (actor_user_id IS NOT NULL OR actor_service_id IS NOT NULL OR actor_type = 'system')
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON api_audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor_user ON api_audit_log(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor_service ON api_audit_log(actor_service_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON api_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_result ON api_audit_log(result);

-- ====================================================================
-- G. DATA GOVERNANCE & CLASSIFICATION
-- ====================================================================

/**
 * governance_policies: Data governance policy per dataset
 * Defines how data should be handled, classified, and protected
 */
CREATE TABLE IF NOT EXISTS governance_policies (
    policy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id VARCHAR(255) NOT NULL UNIQUE,  -- Socrata ID or internal dataset name
    classification VARCHAR(50) NOT NULL DEFAULT 'internal',  -- PUBLIC, INTERNAL, SENSITIVE, RESTRICTED
    min_quality_score FLOAT DEFAULT 0.0,  -- 0-100, data must meet this quality
    encryption_required BOOLEAN DEFAULT FALSE,
    owner_email VARCHAR(255) NOT NULL,
    owner_name VARCHAR(255),
    retention_days INT DEFAULT 2555,  -- ~7 years default
    approval_workflow VARCHAR(50),  -- optional workflow requirement
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by_user_id UUID REFERENCES api_users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_governance_dataset_id ON governance_policies(dataset_id);
CREATE INDEX IF NOT EXISTS idx_governance_classification ON governance_policies(classification);
CREATE INDEX IF NOT EXISTS idx_governance_owner_email ON governance_policies(owner_email);

/**
 * governance_pii_mappings: PII field identification and masking rules
 * Defines which fields contain PII and how to mask them
 */
CREATE TABLE IF NOT EXISTS governance_pii_mappings (
    pii_mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    pii_type VARCHAR(50) NOT NULL,  -- EMAIL, PHONE, SSN, ADDRESS, CUSTOM, etc.
    masking_type VARCHAR(50) NOT NULL,  -- HIDE, MASK, REDACT, CUSTOM
    masking_pattern VARCHAR(255),  -- Custom masking pattern if needed
    min_role_to_see_unmasked VARCHAR(50),  -- Role required to see unmasked data
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_dataset_field UNIQUE (dataset_id, field_name)
);

CREATE INDEX IF NOT EXISTS idx_pii_dataset_id ON governance_pii_mappings(dataset_id);
CREATE INDEX IF NOT EXISTS idx_pii_field_name ON governance_pii_mappings(field_name);
CREATE INDEX IF NOT EXISTS idx_pii_type ON governance_pii_mappings(pii_type);

-- ====================================================================
-- H. API VERSIONING
-- ====================================================================

/**
 * api_versions: API version lifecycle and schema tracking
 * Manages version deprecation, sunset dates, and schema changes
 */
CREATE TABLE IF NOT EXISTS api_versions (
    version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_version VARCHAR(20) NOT NULL UNIQUE,  -- v1, v2, v3, etc.
    schema_id VARCHAR(255),  -- Reference to schema registry (W1)
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, deprecated, sunset
    release_date TIMESTAMP NOT NULL,
    deprecation_date TIMESTAMP,
    sunset_date TIMESTAMP,  -- After this date, version no longer supported
    release_notes TEXT,
    breaking_changes JSONB DEFAULT '[]'::jsonb,  -- Array of breaking change descriptions
    schema_changes JSONB DEFAULT '[]'::jsonb,  -- Array of schema change details
    documentation_url VARCHAR(1000),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_versions_api_version ON api_versions(api_version);
CREATE INDEX IF NOT EXISTS idx_api_versions_status ON api_versions(status);
CREATE INDEX IF NOT EXISTS idx_api_versions_release_date ON api_versions(release_date);
CREATE INDEX IF NOT EXISTS idx_api_versions_sunset_date ON api_versions(sunset_date);

-- Insert initial API versions
INSERT INTO api_versions (api_version, status, release_date, release_notes) VALUES
    ('v1', 'active', NOW() - INTERVAL '6 months', 'Initial API release'),
    ('v2', 'active', NOW() - INTERVAL '3 months', 'Added versioning support'),
    ('v3', 'active', NOW() - INTERVAL '1 month', 'Enhanced authentication'),
    ('v4', 'active', NOW(), 'Comprehensive governance and security')
ON CONFLICT (api_version) DO NOTHING;

-- ====================================================================
-- I. API CONSUMERS (for multi-tenant scenarios)
-- ====================================================================

/**
 * api_consumers: External organizations/applications consuming the API
 */
CREATE TABLE IF NOT EXISTS api_consumers (
    consumer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    contact_email VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    organization VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, suspended, revoked
    quota_tier VARCHAR(50) DEFAULT 'standard',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by_user_id UUID REFERENCES api_users(user_id),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_api_consumers_name ON api_consumers(name);
CREATE INDEX IF NOT EXISTS idx_api_consumers_status ON api_consumers(status);
CREATE INDEX IF NOT EXISTS idx_api_consumers_contact_email ON api_consumers(contact_email);

/**
 * api_consumer_usage_summary: Aggregated usage by consumer
 */
CREATE TABLE IF NOT EXISTS api_consumer_usage_summary (
    summary_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consumer_id UUID NOT NULL REFERENCES api_consumers(consumer_id) ON DELETE CASCADE,
    month_key VARCHAR(20) NOT NULL,  -- YYYY-MM format
    total_requests INT DEFAULT 0,
    total_bytes_transferred BIGINT DEFAULT 0,
    avg_latency_ms FLOAT,
    error_rate_percent FLOAT,
    datasets_accessed TEXT[],
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_consumer_month UNIQUE (consumer_id, month_key)
);

CREATE INDEX IF NOT EXISTS idx_consumer_usage_consumer_id ON api_consumer_usage_summary(consumer_id);
CREATE INDEX IF NOT EXISTS idx_consumer_usage_month_key ON api_consumer_usage_summary(month_key);

-- ====================================================================
-- VIEWS FOR COMMON QUERIES
-- ====================================================================

/**
 * v_api_user_permissions: Denormalized view of user permissions
 */
CREATE OR REPLACE VIEW v_api_user_permissions AS
SELECT 
    u.user_id,
    u.email,
    ar.role_id,
    ar.name as role_name,
    ap.permission_id,
    ap.resource,
    ap.action
FROM api_users u
LEFT JOIN api_user_roles ur ON u.user_id = ur.user_id AND ur.revoked_at IS NULL
LEFT JOIN api_roles ar ON ur.role_id = ar.role_id
LEFT JOIN api_permissions ap ON TRUE
WHERE ar.name IS NOT NULL;

/**
 * v_active_api_keys: Currently valid API keys only
 */
CREATE OR REPLACE VIEW v_active_api_keys AS
SELECT 
    k.key_id,
    k.key_prefix,
    k.user_id,
    k.service_id,
    k.name,
    k.created_at,
    k.expires_at,
    k.last_used,
    k.usage_count,
    u.email as user_email,
    sp.name as service_name
FROM api_keys k
LEFT JOIN api_users u ON k.user_id = u.user_id
LEFT JOIN api_service_principals sp ON k.service_id = sp.service_id
WHERE k.status = 'active' AND (k.expires_at IS NULL OR k.expires_at > NOW());

/**
 * v_api_usage_daily_summary: Daily usage summary by user
 */
CREATE OR REPLACE VIEW v_api_usage_daily_summary AS
SELECT 
    DATE(timestamp) as request_date,
    user_id,
    service_id,
    COUNT(*) as total_requests,
    AVG(latency_ms) as avg_latency_ms,
    MAX(latency_ms) as max_latency_ms,
    SUM(records_returned) as total_records,
    ROUND(100.0 * SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_percent
FROM api_usage_log
GROUP BY DATE(timestamp), user_id, service_id;

-- ====================================================================
-- SECURITY & MAINTENANCE
-- ====================================================================

-- Prevent accidental truncation of audit logs
ALTER TABLE api_audit_log ENABLE ROW LEVEL SECURITY;

-- Create role for API service
DO $$ BEGIN
    CREATE ROLE api_service WITH PASSWORD 'changeme' LOGIN;
EXCEPTION WHEN DUPLICATE_OBJECT THEN
    -- Role already exists, no action needed
END $$;

-- Grant minimal permissions to API service role
GRANT USAGE ON SCHEMA public TO api_service;
GRANT SELECT, INSERT, UPDATE ON api_users TO api_service;
GRANT SELECT, INSERT, UPDATE ON api_keys TO api_service;
GRANT SELECT ON api_roles TO api_service;
GRANT SELECT ON api_permissions TO api_service;
GRANT SELECT ON api_user_roles TO api_service;
GRANT SELECT, INSERT, UPDATE ON api_rate_limits TO api_service;
GRANT SELECT, INSERT, UPDATE ON api_quota_usage TO api_service;
GRANT SELECT, INSERT ON api_usage_log TO api_service;
GRANT SELECT, INSERT ON api_audit_log TO api_service;
GRANT SELECT ON governance_policies TO api_service;
GRANT SELECT ON governance_pii_mappings TO api_service;
GRANT SELECT ON api_versions TO api_service;

-- Create audit trigger function to log updates
CREATE OR REPLACE FUNCTION audit_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO api_audit_log (actor_type, action, resource, result, reason)
    VALUES ('system', 'data_modification', TG_TABLE_NAME || ':' || NEW.user_id::text, 'success', 'Automatic audit trigger');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach audit trigger to sensitive tables
CREATE TRIGGER trg_audit_user_changes
AFTER UPDATE ON api_users
FOR EACH ROW
EXECUTE FUNCTION audit_user_changes();

CREATE TRIGGER trg_audit_key_changes
AFTER UPDATE ON api_keys
FOR EACH ROW
EXECUTE FUNCTION audit_user_changes();

-- ====================================================================
-- COMMENTS
-- ====================================================================

COMMENT ON TABLE api_users IS 'Core user account table for API authentication';
COMMENT ON TABLE api_service_principals IS 'Service accounts for programmatic access without user credentials';
COMMENT ON TABLE api_keys IS 'Hashed API keys for stateless authentication (stateful without JWT)';
COMMENT ON TABLE api_roles IS 'Role definitions that bundle permissions for RBAC';
COMMENT ON TABLE api_permissions IS 'Individual fine-grained permissions (resource + action)';
COMMENT ON TABLE api_rate_limits IS 'Current rate limit configuration per user/service';
COMMENT ON TABLE api_usage_log IS 'Complete request log for analytics, monitoring, and chargeback';
COMMENT ON TABLE api_audit_log IS 'Immutable audit trail for compliance and security investigation';
COMMENT ON TABLE governance_policies IS 'Data classification and governance policies per dataset';
COMMENT ON TABLE governance_pii_mappings IS 'PII field identification and masking rules';
COMMENT ON TABLE api_versions IS 'API version lifecycle management and schema tracking';

COMMIT;
