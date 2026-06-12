-- Layer 4: SERVING (READY FOR DIVES)
-- Purpose: Pre-computed, materialized for zero-latency Dive queries
-- Rows: 90
-- Refresh: Nightly CTAS after Layer 3 completes
-- Rationale: Dives query this table directly; no post-materialization computation

-- Reference table for KPI metadata (18 rows)
CREATE TABLE IF NOT EXISTS analytics.kpi_metadata (
  kpi_name                      VARCHAR(255)      PRIMARY KEY,
  kpi_id                        VARCHAR(36)       COMMENT 'Unique identifier',
  phase                         VARCHAR(32)       COMMENT 'Phase: B, C, D, E, F (analysis phases)',
  unit                          VARCHAR(128)      COMMENT 'Unit of measurement (e.g., %, count, days)',
  description                   VARCHAR(1024)     COMMENT 'Business meaning of KPI',
  risk_threshold                DECIMAL(18, 6)    COMMENT 'Threshold above which KPI is at risk',
  benchmark_value               DECIMAL(18, 6)    COMMENT 'Target value for this KPI',
  data_source                   VARCHAR(256)      COMMENT 'Source dataset(s)',
  refresh_frequency             VARCHAR(64)       COMMENT 'e.g., DAILY, WEEKLY',
  owner                         VARCHAR(128)      COMMENT 'Data owner team',
  created_at                    TIMESTAMP         DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE analytics.kpi_metadata IS
  'KPI reference metadata: definitions, units, benchmarks for 18 KPIs.';

-- Materialized serving table (materialized CTAS nightly)
CREATE TABLE IF NOT EXISTS analytics.kpi_metrics_comprehensive (
  -- Identity
  kpi_id                        VARCHAR(36),
  kpi_name                      VARCHAR(255),
  borough                       VARCHAR(2),

  -- Current Value & Benchmarking
  current_mean                  DECIMAL(18, 6)    COMMENT 'Mean value (current period)',
  median_value                  DECIMAL(18, 6),
  benchmark_value               DECIMAL(18, 6),
  benchmark_ratio               DECIMAL(18, 6),
  pct_diff_benchmark            DECIMAL(18, 6),

  -- Distribution Stats
  sample_count                  INTEGER,
  standard_deviation            DECIMAL(18, 6),
  coeff_variation               DECIMAL(18, 6),
  range_value                   DECIMAL(18, 6),

  -- Percentiles (for box plots in Dives)
  min_value                     DECIMAL(18, 6),
  q1_value                      DECIMAL(18, 6),
  q2_value                      DECIMAL(18, 6),
  q3_value                      DECIMAL(18, 6),
  max_value                     DECIMAL(18, 6),
  p05_value                     DECIMAL(18, 6),
  p10_value                     DECIMAL(18, 6),
  p90_value                     DECIMAL(18, 6),
  p95_value                     DECIMAL(18, 6),
  p99_value                     DECIMAL(18, 6),

  -- Shape & Outliers
  skewness_index                DECIMAL(18, 6),
  kurtosis_excess               DECIMAL(18, 6),
  outlier_count_3sd             INTEGER,
  outlier_count_iqr             INTEGER,
  is_outlier_3sd                BOOLEAN,
  is_outlier_iqr                BOOLEAN,

  -- Risk & Tail
  pct_exceeding_risk_threshold  DECIMAL(5, 2),
  risk_percentile_95            DECIMAL(18, 6),
  value_at_risk_95              DECIMAL(18, 6),
  expected_shortfall            DECIMAL(18, 6),

  -- Diversity
  simpsons_diversity            DECIMAL(18, 6),
  gini_coefficient              DECIMAL(18, 6),
  shannon_entropy               DECIMAL(18, 6),

  -- Trend
  trend_slope_per_day           DECIMAL(18, 6),
  trend_direction               VARCHAR(32),
  autocorrelation_lag1          DECIMAL(18, 6),

  -- Forecasting
  forecast_next_period          DECIMAL(18, 6),
  forecast_error_mape           DECIMAL(18, 6),

  -- Confidence
  ci_lower_95                   DECIMAL(18, 6),
  ci_upper_95                   DECIMAL(18, 6),

  -- Advanced Statistical Tests (optional, computed weekly via statsmodels)
  shapiro_wilk_p                DECIMAL(5, 4)     COMMENT 'Normality test p-value',
  jarque_bera_p                 DECIMAL(5, 4),
  anderson_statistic            DECIMAL(18, 6),
  is_normal                     BOOLEAN,
  levene_p_across_boroughs      DECIMAL(5, 4)     COMMENT 'Variance equality p-value',
  variances_equal               BOOLEAN,
  cohens_d_vs_benchmark         DECIMAL(18, 6)    COMMENT 'Effect size vs. benchmark',
  seasonal_strength             DECIMAL(5, 4)     COMMENT 'Seasonality strength (0-1)',
  ljung_box_p                   DECIMAL(5, 4)     COMMENT 'Autocorrelation significance',
  robust_regression_slope       DECIMAL(18, 6)    COMMENT 'Outlier-resistant slope',
  outlier_sensitivity_ratio     DECIMAL(5, 4)     COMMENT 'Sensitivity to outliers',

  -- Metadata
  kpi_unit                      VARCHAR(128),
  phase                         VARCHAR(32),
  kpi_description               VARCHAR(1024),
  risk_threshold                DECIMAL(18, 6),
  analytics_timestamp           TIMESTAMP,
  advanced_metrics_timestamp    TIMESTAMP,
  materialized_at               TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comprehensive_kpi_borough
  ON analytics.kpi_metrics_comprehensive(kpi_name, borough);

CREATE INDEX IF NOT EXISTS idx_comprehensive_timestamp
  ON analytics.kpi_metrics_comprehensive(analytics_timestamp DESC);

COMMENT ON TABLE analytics.kpi_metrics_comprehensive IS
  'Serving table: materialized for zero-latency KPI Dive queries. 90 rows pre-computed nightly.';

-- Serving view (optimized for Dive consumption)
CREATE OR REPLACE VIEW app_queries.v_kpi_statistics AS
SELECT
  -- Identity
  c.kpi_id,
  c.kpi_name,
  c.borough,

  -- Display Values (formatted for Dives)
  ROUND(c.current_mean, 2) AS mean_value,
  ROUND(c.median_value, 2) AS median,
  ROUND(c.standard_deviation, 4) AS std_dev,
  ROUND(c.coeff_variation, 4) AS cv,

  -- Risk Summary
  ROUND(c.pct_exceeding_risk_threshold, 1) AS pct_at_risk,
  ROUND(c.value_at_risk_95, 2) AS var_95,

  -- Distribution
  ROUND(c.skewness_index, 4) AS skewness,
  ROUND(c.kurtosis_excess, 4) AS kurtosis,
  c.outlier_count_3sd,
  c.outlier_count_iqr,

  -- Trend
  ROUND(c.trend_slope_per_day, 6) AS trend_slope,
  c.trend_direction,

  -- Forecast
  ROUND(c.forecast_next_period, 2) AS forecast,
  ROUND(c.forecast_error_mape, 1) AS mape,

  -- Benchmark
  ROUND(c.benchmark_ratio, 4) AS vs_benchmark,
  ROUND(c.pct_diff_benchmark, 1) AS pct_from_benchmark,

  -- Advanced Statistical Tests
  ROUND(c.shapiro_wilk_p, 4) AS shapiro_wilk_p,
  ROUND(c.jarque_bera_p, 4) AS jarque_bera_p,
  ROUND(c.anderson_statistic, 6) AS anderson_statistic,
  c.is_normal,
  ROUND(c.levene_p_across_boroughs, 4) AS levene_p,
  c.variances_equal,
  ROUND(c.cohens_d_vs_benchmark, 6) AS cohens_d,
  ROUND(c.seasonal_strength, 4) AS seasonal_strength,
  ROUND(c.ljung_box_p, 4) AS ljung_box_p,
  ROUND(c.robust_regression_slope, 6) AS robust_slope,
  ROUND(c.outlier_sensitivity_ratio, 4) AS outlier_sensitivity,

  -- Metadata
  m.unit AS kpi_unit,
  m.phase,
  m.risk_threshold,

  c.analytics_timestamp,
  c.advanced_metrics_timestamp,
  c.materialized_at
FROM analytics.kpi_metrics_comprehensive c
LEFT JOIN analytics.kpi_metadata m ON c.kpi_name = m.kpi_name
ORDER BY c.borough, c.kpi_name;

COMMENT ON VIEW app_queries.v_kpi_statistics IS
  'Serving view for KPI Dives: formatted statistics for display.';
