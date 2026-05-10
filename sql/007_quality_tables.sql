-- Data Quality Framework Tables
-- PostgreSQL schema for quality expectations, profiles, validations, SLAs, metrics, and anomalies
-- Created: 2026-05-10

-- quality_expectations: Store expectation suites and individual expectations
CREATE TABLE IF NOT EXISTS quality_expectations (
    expectation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_name VARCHAR(255) NOT NULL,
    expectation_type VARCHAR(100) NOT NULL,
    expectation_name VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL DEFAULT 'HIGH',
    config JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    INDEX idx_suite_name (suite_name),
    INDEX idx_expectation_type (expectation_type)
);

-- quality_profiles: Store column-level and table-level statistics
CREATE TABLE IF NOT EXISTS quality_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255),
    profile_version VARCHAR(50),
    data_type VARCHAR(50),
    column_count INT,
    row_count BIGINT,
    null_count INT,
    null_percentage FLOAT,
    cardinality INT,
    cardinality_ratio FLOAT,
    min_value VARCHAR(255),
    max_value VARCHAR(255),
    mean_value FLOAT,
    median_value FLOAT,
    std_dev_value FLOAT,
    outlier_count INT,
    profile_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset (dataset_id),
    INDEX idx_column (dataset_id, column_name),
    INDEX idx_created (created_at DESC)
);

-- quality_validations: Validation results and history
CREATE TABLE IF NOT EXISTS quality_validations (
    validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(255) NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    suite_name VARCHAR(255),
    validation_status VARCHAR(50) NOT NULL,
    total_expectations INT,
    passed_expectations INT,
    failed_expectations INT,
    warning_expectations INT,
    pass_rate FLOAT,
    validation_details JSONB,
    failed_rows_sample JSONB,
    validation_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset (dataset_id),
    INDEX idx_status (validation_status),
    INDEX idx_timestamp (validation_timestamp DESC),
    INDEX idx_created (created_at DESC)
);

-- quality_sla_config: SLA definitions and configuration
CREATE TABLE IF NOT EXISTS quality_sla_config (
    sla_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(255) NOT NULL UNIQUE,
    metric_type VARCHAR(100) NOT NULL,
    target_value FLOAT NOT NULL,
    window VARCHAR(50) NOT NULL,
    dataset_id VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL DEFAULT 'HIGH',
    materialization_mode VARCHAR(50) DEFAULT 'SOFT',
    owner_email VARCHAR(255),
    grace_period_minutes INT DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true,
    INDEX idx_metric_name (metric_name),
    INDEX idx_dataset (dataset_id),
    INDEX idx_active (active)
);

-- quality_metrics: Time-series quality metrics for SLA tracking
CREATE TABLE IF NOT EXISTS quality_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_type VARCHAR(100),
    dataset_id VARCHAR(255),
    window VARCHAR(50),
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tags JSONB,
    INDEX idx_metric_name (metric_name),
    INDEX idx_dataset (dataset_id),
    INDEX idx_measured (measured_at DESC),
    INDEX idx_metric_date (measured_at DESC, metric_name)
) PARTITION BY RANGE (measured_at);

-- Create partitions for quality_metrics (monthly)
CREATE TABLE quality_metrics_2026_01 PARTITION OF quality_metrics
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE quality_metrics_2026_02 PARTITION OF quality_metrics
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE quality_metrics_2026_03 PARTITION OF quality_metrics
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE quality_metrics_2026_04 PARTITION OF quality_metrics
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE quality_metrics_2026_05 PARTITION OF quality_metrics
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE quality_metrics_2026_06 PARTITION OF quality_metrics
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- quality_anomalies: Detected data quality anomalies
CREATE TABLE IF NOT EXISTS quality_anomalies (
    anomaly_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(255) NOT NULL,
    anomaly_type VARCHAR(100) NOT NULL,
    anomaly_value FLOAT,
    expected_range_min FLOAT,
    expected_range_max FLOAT,
    z_score FLOAT,
    severity VARCHAR(50) NOT NULL,
    explanation TEXT,
    dataset_id VARCHAR(255),
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    INDEX idx_metric (metric_name),
    INDEX idx_dataset (dataset_id),
    INDEX idx_severity (severity),
    INDEX idx_detected (detected_at DESC),
    INDEX idx_status (status)
);

-- quality_catalog: Dataset quality profiles in data catalog
CREATE TABLE IF NOT EXISTS quality_catalog (
    catalog_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(255) NOT NULL UNIQUE,
    dataset_name VARCHAR(255) NOT NULL,
    quality_score_overall FLOAT,
    quality_score_completeness FLOAT,
    quality_score_validity FLOAT,
    quality_score_consistency FLOAT,
    quality_score_timeliness FLOAT,
    quality_score_accuracy FLOAT,
    trend VARCHAR(50),
    last_validation TIMESTAMP WITH TIME ZONE,
    validation_count INT DEFAULT 0,
    anomaly_count INT DEFAULT 0,
    violation_summary JSONB,
    sla_compliance JSONB,
    catalog_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset (dataset_id),
    INDEX idx_quality_score (quality_score_overall DESC),
    INDEX idx_trend (trend),
    INDEX idx_updated (updated_at DESC)
);

-- quality_sla_breaches: Track SLA breaches over time
CREATE TABLE IF NOT EXISTS quality_sla_breaches (
    breach_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sla_id UUID NOT NULL REFERENCES quality_sla_config(sla_id),
    metric_name VARCHAR(255) NOT NULL,
    actual_value FLOAT NOT NULL,
    target_value FLOAT NOT NULL,
    breach_start TIMESTAMP WITH TIME ZONE NOT NULL,
    breach_end TIMESTAMP WITH TIME ZONE,
    breach_duration INTERVAL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sla_id) REFERENCES quality_sla_config(sla_id),
    INDEX idx_sla (sla_id),
    INDEX idx_metric (metric_name),
    INDEX idx_status (status),
    INDEX idx_start (breach_start DESC)
);

-- quality_rules_violations: Track business rule violations
CREATE TABLE IF NOT EXISTS quality_rules_violations (
    violation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id VARCHAR(255) NOT NULL,
    rule_id VARCHAR(255) NOT NULL,
    rule_name VARCHAR(255),
    severity VARCHAR(50),
    violation_count INT,
    affected_records JSONB,
    remediation_suggestion TEXT,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'OPEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset (dataset_id),
    INDEX idx_rule (rule_id),
    INDEX idx_severity (severity),
    INDEX idx_status (status),
    INDEX idx_detected (detected_at DESC)
);

-- quality_audit_trail: Audit trail for quality system operations
CREATE TABLE IF NOT EXISTS quality_audit_trail (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    dataset_id VARCHAR(255),
    actor VARCHAR(255),
    details JSONB,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action (action),
    INDEX idx_dataset (dataset_id),
    INDEX idx_actor (actor),
    INDEX idx_created (created_at DESC)
);

-- Create indexes for common queries
CREATE INDEX idx_quality_metrics_rolling ON quality_metrics(measured_at DESC, metric_name)
    WHERE measured_at > CURRENT_TIMESTAMP - INTERVAL '30 days';

CREATE INDEX idx_quality_validations_recent ON quality_validations(created_at DESC)
    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days';

CREATE INDEX idx_quality_anomalies_active ON quality_anomalies(dataset_id, status)
    WHERE status = 'ACTIVE' AND resolved_at IS NULL;

-- Grant permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO data_quality_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO data_quality_service;

-- Comments for documentation
COMMENT ON TABLE quality_expectations IS 'Stores expectation suites and individual expectations for data quality validation';
COMMENT ON TABLE quality_profiles IS 'Stores statistical profiles of columns and tables over time';
COMMENT ON TABLE quality_validations IS 'Records validation results against expectation suites';
COMMENT ON TABLE quality_sla_config IS 'Configuration for data quality SLAs';
COMMENT ON TABLE quality_metrics IS 'Time-series storage of quality metrics (partitioned by month)';
COMMENT ON TABLE quality_anomalies IS 'Detected anomalies in quality metrics';
COMMENT ON TABLE quality_catalog IS 'Dataset quality profiles for data catalog integration';
COMMENT ON TABLE quality_sla_breaches IS 'Records of SLA breaches and their resolution';
COMMENT ON TABLE quality_rules_violations IS 'Records of business rule violations';
COMMENT ON TABLE quality_audit_trail IS 'Audit trail of all quality system operations';
