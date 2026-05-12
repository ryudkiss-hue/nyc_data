-- Entity Resolution and Deduplication Tables
-- Week 9-10 implementation for master data management, deduplication, and reconciliation

-- Master Entities (canonical representations)
CREATE TABLE IF NOT EXISTS master_entities (
    entity_id VARCHAR(255) PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    canonical_record JSONB NOT NULL,
    confidence_by_field JSONB DEFAULT '{}',
    field_provenance JSONB DEFAULT '{}',
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(255) DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_master_entities_type ON master_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_master_entities_created_at ON master_entities(created_at);
CREATE INDEX IF NOT EXISTS idx_master_entities_type_updated ON master_entities(entity_type, last_updated);

-- Mapping of source records to master entities
CREATE TABLE IF NOT EXISTS entity_record_mapping (
    mapping_id VARCHAR(255) PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    source_record_id VARCHAR(255) NOT NULL,
    source_dataset VARCHAR(100) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(source_record_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_record_mapping_entity_id ON entity_record_mapping(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_record_mapping_source_record_id ON entity_record_mapping(source_record_id);
CREATE INDEX IF NOT EXISTS idx_entity_record_mapping_source_dataset ON entity_record_mapping(source_dataset);

-- Duplicate groups (sets of records identified as duplicates)
CREATE TABLE IF NOT EXISTS duplicate_groups (
    group_id VARCHAR(255) PRIMARY KEY,
    duplicate_record_ids JSONB NOT NULL,
    confidence_score FLOAT NOT NULL,
    matching_strategy VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'unresolved',  -- unresolved, auto_resolved, manual_resolved, rejected
    potential_canonical_id VARCHAR(255),
    user_decision VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_duplicate_groups_status ON duplicate_groups(status);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_strategy ON duplicate_groups(matching_strategy);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_created_at ON duplicate_groups(created_at);

-- Entity review cases (for manual validation)
CREATE TABLE IF NOT EXISTS entity_review_cases (
    case_id VARCHAR(255) PRIMARY KEY,
    record1_id VARCHAR(255) NOT NULL,
    record2_id VARCHAR(255) NOT NULL,
    record1_data JSONB,
    record2_data JSONB,
    matching_score FLOAT NOT NULL,
    matching_strategy VARCHAR(100),
    
    -- Review details
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed, disputed
    decision VARCHAR(50),  -- match, not_match, unsure, skip
    reviewer VARCHAR(255),
    review_timestamp TIMESTAMP,
    time_to_review_seconds FLOAT,
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entity_review_cases_status ON entity_review_cases(status);
CREATE INDEX IF NOT EXISTS idx_entity_review_cases_reviewer ON entity_review_cases(reviewer);
CREATE INDEX IF NOT EXISTS idx_entity_review_cases_created_at ON entity_review_cases(created_at);

-- Entity merge history (audit trail)
CREATE TABLE IF NOT EXISTS entity_merge_log (
    merge_id VARCHAR(255) PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    action VARCHAR(100),  -- created, added_record, resolved_conflict, etc.
    records_merged JSONB,
    strategy_used VARCHAR(100),
    field_conflicts JSONB DEFAULT '{}',
    merged_by VARCHAR(255) DEFAULT 'system',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (entity_id) REFERENCES master_entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entity_merge_log_entity_id ON entity_merge_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_merge_log_timestamp ON entity_merge_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_entity_merge_log_action ON entity_merge_log(action);

-- Field-level conflicts discovered during merging
CREATE TABLE IF NOT EXISTS entity_conflicts (
    conflict_id VARCHAR(255) PRIMARY KEY,
    entity_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    values JSONB NOT NULL,  -- {value1, value2, ...}
    resolution VARCHAR(255),
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES master_entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entity_conflicts_entity_id ON entity_conflicts(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_conflicts_field_name ON entity_conflicts(field_name);
CREATE INDEX IF NOT EXISTS idx_entity_conflicts_created_at ON entity_conflicts(created_at);

-- Entity relationships (contains, belongs_to, adjacent_to, etc.)
CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id VARCHAR(255) PRIMARY KEY,
    source_entity_id VARCHAR(255) NOT NULL,
    target_entity_id VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(100) NOT NULL,  -- contains, belongs_to, adjacent_to, etc.
    confidence FLOAT DEFAULT 1.0,
    attributes JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) DEFAULT 'system',
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_type ON entity_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_source_target ON entity_relationships(source_entity_id, target_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_created_at ON entity_relationships(created_at);

-- Links to external master data sources
CREATE TABLE IF NOT EXISTS external_master_links (
    link_id VARCHAR(255) PRIMARY KEY,
    local_entity_id VARCHAR(255) NOT NULL,
    external_source VARCHAR(100) NOT NULL,
    external_entity_id VARCHAR(255) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    status VARCHAR(50) DEFAULT 'active',  -- active, superseded, conflicting, pending_verification, broken
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) DEFAULT 'system',
    notes TEXT,
    
    FOREIGN KEY (local_entity_id) REFERENCES master_entities(entity_id) ON DELETE CASCADE,
    UNIQUE(local_entity_id, external_source)
);

CREATE INDEX IF NOT EXISTS idx_external_master_links_local_id ON external_master_links(local_entity_id);
CREATE INDEX IF NOT EXISTS idx_external_master_links_source ON external_master_links(external_source);
CREATE INDEX IF NOT EXISTS idx_external_master_links_external_id ON external_master_links(external_entity_id);
CREATE INDEX IF NOT EXISTS idx_external_master_links_status ON external_master_links(status);
CREATE INDEX IF NOT EXISTS idx_external_master_links_verified ON external_master_links(last_verified);

-- External master data cache (for reconciliation)
CREATE TABLE IF NOT EXISTS external_master_data (
    external_record_id VARCHAR(255),
    external_source VARCHAR(100) NOT NULL,
    external_data JSONB NOT NULL,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (external_source, external_record_id)
);

CREATE INDEX IF NOT EXISTS idx_external_master_data_source ON external_master_data(external_source);
CREATE INDEX IF NOT EXISTS idx_external_master_data_imported_at ON external_master_data(imported_at);

-- Reconciliation reports
CREATE TABLE IF NOT EXISTS reconciliation_reports (
    report_id VARCHAR(255) PRIMARY KEY,
    external_source VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Counts
    total_internal_entities INT,
    total_external_entities INT,
    matched_count INT,
    unlinked_local INT,
    unlinked_external INT,
    
    -- Quality metrics
    match_confidence FLOAT,
    conflict_count INT,
    
    -- Recommendations
    recommendations JSONB DEFAULT '[]',
    
    -- Metadata
    created_by VARCHAR(255) DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_reports_source ON reconciliation_reports(external_source);
CREATE INDEX IF NOT EXISTS idx_reconciliation_reports_timestamp ON reconciliation_reports(timestamp);

-- Review workflow statistics (for monitoring reviewer performance)
CREATE TABLE IF NOT EXISTS review_statistics (
    stat_id VARCHAR(255) PRIMARY KEY,
    reviewer VARCHAR(255) NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    
    -- Case counts
    total_reviewed INT DEFAULT 0,
    match_rate FLOAT DEFAULT 0.0,
    
    -- Performance
    avg_review_time_seconds FLOAT,
    accuracy_vs_auto FLOAT,
    
    UNIQUE(reviewer, date)
);

CREATE INDEX IF NOT EXISTS idx_review_statistics_reviewer ON review_statistics(reviewer);
CREATE INDEX IF NOT EXISTS idx_review_statistics_date ON review_statistics(date);

-- Matching decision log (track all decisions for audit)
CREATE TABLE IF NOT EXISTS matching_decisions (
    decision_id VARCHAR(255) PRIMARY KEY,
    record_id VARCHAR(255) NOT NULL,
    entity_id VARCHAR(255),
    decision_type VARCHAR(50),  -- auto_assigned, queued_for_review, manual_override, unmatched
    confidence FLOAT,
    user_decision VARCHAR(255),
    user VARCHAR(255),
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_matching_decisions_record_id ON matching_decisions(record_id);
CREATE INDEX IF NOT EXISTS idx_matching_decisions_entity_id ON matching_decisions(entity_id);
CREATE INDEX IF NOT EXISTS idx_matching_decisions_user ON matching_decisions("user");
CREATE INDEX IF NOT EXISTS idx_matching_decisions_timestamp ON matching_decisions(timestamp);

-- Incremental matching queue
CREATE TABLE IF NOT EXISTS incremental_matching_queue (
    queue_id VARCHAR(255) PRIMARY KEY,
    record_id VARCHAR(255) NOT NULL,
    record_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, matched, unmatched, queued_for_review
    best_match_entity_id VARCHAR(255),
    best_match_confidence FLOAT,
    candidates JSONB,  -- List of (entity_id, confidence) tuples
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    
    UNIQUE(record_id)
);

CREATE INDEX IF NOT EXISTS idx_incremental_matching_queue_status ON incremental_matching_queue(status);
CREATE INDEX IF NOT EXISTS idx_incremental_matching_queue_created ON incremental_matching_queue(created_at);

-- Entity merge history audit trail (detailed tracking)
CREATE TABLE IF NOT EXISTS entity_merge_audit (
    audit_id VARCHAR(255) PRIMARY KEY,
    merge_id VARCHAR(255),
    entity_id VARCHAR(255) NOT NULL,
    action VARCHAR(100),
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (entity_id) REFERENCES master_entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entity_merge_audit_entity_id ON entity_merge_audit(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_merge_audit_changed_at ON entity_merge_audit(changed_at);
CREATE INDEX IF NOT EXISTS idx_entity_merge_audit_merge_id ON entity_merge_audit(merge_id);

-- Blocking statistics (for performance monitoring)
CREATE TABLE IF NOT EXISTS blocking_statistics (
    stat_id VARCHAR(255) PRIMARY KEY,
    algorithm VARCHAR(100),
    dataset_size INT,
    total_possible_pairs INT,
    candidate_pairs INT,
    reduction_ratio FLOAT,
    execution_time_seconds FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_blocking_statistics_algorithm ON blocking_statistics(algorithm);
CREATE INDEX IF NOT EXISTS idx_blocking_statistics_timestamp ON blocking_statistics(timestamp);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_master_entities_type_timestamp 
    ON master_entities(entity_type, last_updated DESC);

CREATE INDEX IF NOT EXISTS idx_entity_record_mapping_dataset_record 
    ON entity_record_mapping(source_dataset, source_record_id);

CREATE INDEX IF NOT EXISTS idx_duplicate_groups_confidence 
    ON duplicate_groups(confidence_score DESC);

CREATE INDEX IF NOT EXISTS idx_review_cases_reviewer_status 
    ON entity_review_cases(reviewer, status);

CREATE INDEX IF NOT EXISTS idx_relationships_type_source 
    ON entity_relationships(relationship_type, source_entity_id);

CREATE INDEX IF NOT EXISTS idx_external_links_source_status 
    ON external_master_links(external_source, status);

-- Helper views for common queries

-- View: Entities with unresolved duplicates
CREATE OR REPLACE VIEW v_unresolved_duplicates AS
SELECT 
    dg.group_id,
    dg.duplicate_record_ids,
    dg.confidence_score,
    dg.matching_strategy,
    COUNT(DISTINCT erm.entity_id) as mapped_entities,
    dg.created_at
FROM duplicate_groups dg
LEFT JOIN entity_record_mapping erm 
    ON erm.source_record_id = ANY(SELECT jsonb_array_elements(dg.duplicate_record_ids)::text)
WHERE dg.status = 'unresolved'
GROUP BY dg.group_id, dg.duplicate_record_ids, dg.confidence_score, 
         dg.matching_strategy, dg.created_at
ORDER BY dg.confidence_score DESC;

-- View: Review cases pending resolution
CREATE OR REPLACE VIEW v_pending_reviews AS
SELECT 
    rc.case_id,
    rc.record1_id,
    rc.record2_id,
    rc.matching_score,
    rc.matching_strategy,
    rc.reviewer,
    rc.created_at,
    (EXTRACT(EPOCH FROM (NOW() - rc.created_at)) / 3600)::INT as hours_pending
FROM entity_review_cases
WHERE status IN ('pending', 'in_progress')
ORDER BY rc.created_at ASC;

-- View: Entity coverage metrics
CREATE OR REPLACE VIEW v_entity_coverage AS
SELECT 
    me.entity_type,
    COUNT(DISTINCT me.entity_id) as master_entities,
    COUNT(DISTINCT erm.source_record_id) as source_records,
    AVG(erm.confidence) as avg_mapping_confidence,
    COUNT(DISTINCT erm.source_dataset) as datasets_contributing
FROM master_entities me
LEFT JOIN entity_record_mapping erm ON me.entity_id = erm.entity_id
GROUP BY me.entity_type;

-- View: External reconciliation status
CREATE OR REPLACE VIEW v_reconciliation_status AS
SELECT 
    eml.external_source,
    COUNT(DISTINCT eml.local_entity_id) as linked_local_entities,
    COUNT(DISTINCT CASE WHEN eml.status = 'active' THEN eml.link_id END) as active_links,
    AVG(eml.confidence) as avg_link_confidence,
    MAX(eml.last_verified) as last_verified
FROM external_master_links eml
GROUP BY eml.external_source;
