-- Layer 2: STAGING
-- Purpose: Deduplicate, window, and rank for quantile computation
-- Rows: 90
-- Logic: Latest record per KPI-borough; add ranking for windowed stats

CREATE TABLE IF NOT EXISTS analytics.kpi_metrics_staged (
  -- Identity
  metric_id                     VARCHAR(36)       COMMENT 'FK to analytics.kpi_metrics',
  kpi_name                      VARCHAR(255)      COMMENT 'KPI name',
  borough                       VARCHAR(2)        COMMENT 'Borough code',

  -- Raw Value & Dedup
  kpi_value                     DECIMAL(18, 6)    COMMENT 'Latest KPI value for this borough',
  analytics_timestamp           TIMESTAMP         COMMENT 'Latest computation timestamp',
  is_latest_record              BOOLEAN           DEFAULT TRUE COMMENT 'TRUE if most recent for borough',

  -- Window Context (90-day recent window)
  recent_90day_min              DECIMAL(18, 6)    COMMENT 'Min value last 90 days',
  recent_90day_max              DECIMAL(18, 6)    COMMENT 'Max value last 90 days',
  recent_90day_count            INTEGER           COMMENT 'Record count last 90 days',

  -- Ranking for Quantile Computation
  rank_asc                      INTEGER           COMMENT 'ROW_NUMBER() ascending by kpi_value within borough',
  rank_desc                     INTEGER           COMMENT 'ROW_NUMBER() descending by kpi_value within borough',
  percentile_rank               DECIMAL(5, 2)     COMMENT 'PERCENT_RANK() for KPI value distribution',

  -- Data Quality
  is_provisional                BOOLEAN           DEFAULT FALSE,
  created_at                    TIMESTAMP         DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staged_kpi_borough
  ON analytics.kpi_metrics_staged(kpi_name, borough);

COMMENT ON TABLE analytics.kpi_metrics_staged IS
  'Staging: deduplicated, ranked for quantile computation. 90 rows × ranked for windowed stats.';
