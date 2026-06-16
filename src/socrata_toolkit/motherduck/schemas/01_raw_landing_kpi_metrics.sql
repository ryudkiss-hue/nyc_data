-- Layer 1: RAW LANDING
-- Purpose: Ingest raw KPI values from Socrata/MQTT sources
-- Rows: 90 (18 KPIs × 5 boroughs × 1 record each)
-- Refresh: Append-only with deduplication in staging

CREATE TABLE IF NOT EXISTS analytics.kpi_metrics (
  -- Identity & Time
  metric_id                     VARCHAR(36)       COMMENT 'UUID: kpi_name + borough + timestamp hash',
  kpi_name                      VARCHAR(255)      COMMENT '18 standard KPI names (e.g., clustering_strength, completion_rate)',
  borough                       VARCHAR(2)        COMMENT 'NYC borough: MN, BK, BX, QN, SI',
  analytics_timestamp           TIMESTAMP         COMMENT 'Time of computation or ingestion (UTC)',

  -- Raw Value
  kpi_value                     DECIMAL(18, 6)    COMMENT 'Raw KPI value (unit depends on kpi_name)',
  data_source                   VARCHAR(128)      COMMENT 'Source system: socrata, mqtt, manual',

  -- Metadata
  is_provisional                BOOLEAN           COMMENT 'TRUE if preliminary; FALSE if finalized',
  data_quality_score            DECIMAL(5, 2)     COMMENT '0-100 data quality rating',
  notes                         VARCHAR(1024)     COMMENT 'Data validation notes or anomalies',

  -- Audit
  created_at                    TIMESTAMP         DEFAULT CURRENT_TIMESTAMP COMMENT 'Record insert time',
  created_by                    VARCHAR(128)      COMMENT 'Source system identifier'
);

-- Primary key for uniqueness
ALTER TABLE analytics.kpi_metrics ADD CONSTRAINT pk_kpi_metrics
  PRIMARY KEY (metric_id);

-- Indexes for serving layer queries
CREATE INDEX IF NOT EXISTS idx_kpi_metrics_kpi_borough
  ON analytics.kpi_metrics(kpi_name, borough, analytics_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_kpi_metrics_timestamp
  ON analytics.kpi_metrics(analytics_timestamp DESC);

COMMENT ON TABLE analytics.kpi_metrics IS
  'Raw KPI landing zone: 18 KPIs × 5 boroughs = 90 base rows. Append-only, deduplicated upstream.';
