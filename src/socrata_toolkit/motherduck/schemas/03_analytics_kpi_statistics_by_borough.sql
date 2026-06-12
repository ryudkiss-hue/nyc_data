-- Layer 3: ANALYTICS (COMPUTATION)
-- Purpose: Compute all 60+ metrics in ONE denormalized table
-- Rows: 90 (one row per KPI per borough)
-- Columns: 75+ (all computed metrics)

CREATE TABLE IF NOT EXISTS analytics.kpi_statistics_by_borough (
  -- Identity (composite key)
  kpi_name                      VARCHAR(255)      PRIMARY KEY(kpi_name, borough),
  borough                       VARCHAR(2)        PRIMARY KEY(kpi_name, borough),

  -- ===== CENTRAL TENDENCY (5 metrics) =====
  n                             INTEGER           COMMENT 'Sample count',
  mean_value                    DECIMAL(18, 6)    COMMENT 'Arithmetic mean',
  median_value                  DECIMAL(18, 6)    COMMENT 'Median (50th percentile)',
  mode_value                    DECIMAL(18, 6)    COMMENT 'Most frequent value (mode)',
  trimmed_mean_90               DECIMAL(18, 6)    COMMENT 'Trimmed mean (5% tails removed)',

  -- ===== SPREAD/DISPERSION (11 metrics) =====
  min_value                     DECIMAL(18, 6)    COMMENT 'Minimum value',
  max_value                     DECIMAL(18, 6)    COMMENT 'Maximum value',
  range_value                   DECIMAL(18, 6)    COMMENT 'Max - Min',
  q1_value                      DECIMAL(18, 6)    COMMENT '25th percentile (Q1)',
  q3_value                      DECIMAL(18, 6)    COMMENT '75th percentile (Q3)',
  iqr_value                     DECIMAL(18, 6)    COMMENT 'Interquartile range (Q3 - Q1)',
  stddev_pop                    DECIMAL(18, 6)    COMMENT 'Population standard deviation',
  stddev_samp                   DECIMAL(18, 6)    COMMENT 'Sample standard deviation',
  variance_value                DECIMAL(18, 6)    COMMENT 'Variance (σ²)',
  coeff_variation               DECIMAL(18, 6)    COMMENT 'Coefficient of variation (σ/μ)',
  standard_error                DECIMAL(18, 6)    COMMENT 'Standard error of mean (σ/√n)',
  mad_value                     DECIMAL(18, 6)    COMMENT 'Mean Absolute Deviation (robust)',

  -- ===== DISTRIBUTION SHAPE (2 metrics) =====
  skewness_index                DECIMAL(18, 6)    COMMENT 'Skewness: (mean - median) / σ',
  kurtosis_excess               DECIMAL(18, 6)    COMMENT 'Excess kurtosis (normal = 0)',

  -- ===== OUTLIER DETECTION (2 metrics + flags) =====
  outlier_count_3sd             INTEGER           COMMENT 'Count of values > 3σ from mean',
  outlier_count_iqr             INTEGER           COMMENT 'Count beyond 1.5×IQR fence',
  is_outlier_3sd                BOOLEAN           COMMENT 'TRUE if any 3σ outliers present',
  is_outlier_iqr                BOOLEAN           COMMENT 'TRUE if any IQR outliers present',

  -- ===== QUANTILES & PERCENTILES (7 metrics) =====
  p05_value                     DECIMAL(18, 6)    COMMENT '5th percentile',
  p10_value                     DECIMAL(18, 6)    COMMENT '10th percentile',
  p90_value                     DECIMAL(18, 6)    COMMENT '90th percentile',
  p95_value                     DECIMAL(18, 6)    COMMENT '95th percentile',
  p99_value                     DECIMAL(18, 6)    COMMENT '99th percentile',

  -- ===== DIVERSITY METRICS (3 metrics) =====
  simpsons_diversity            DECIMAL(18, 6)    COMMENT 'Simpson''s Diversity Index (0-1, higher = more diverse)',
  gini_coefficient              DECIMAL(18, 6)    COMMENT 'Gini Coefficient (0-1, higher = more unequal)',
  shannon_entropy               DECIMAL(18, 6)    COMMENT 'Shannon Entropy (information content)',

  -- ===== RISK/PERFORMANCE METRICS (5 metrics) =====
  pct_exceeding_risk_threshold  DECIMAL(5, 2)     COMMENT 'Percent of values exceeding risk threshold',
  risk_percentile_95            DECIMAL(18, 6)    COMMENT 'Value at 95th percentile (tail risk)',
  value_at_risk_95              DECIMAL(18, 6)    COMMENT 'VaR: loss at 95% confidence',
  tail_ratio                    DECIMAL(18, 6)    COMMENT 'Ratio of tail values (>95th / <5th percentile)',
  expected_shortfall            DECIMAL(18, 6)    COMMENT 'Expected Shortfall (avg of tail)',

  -- ===== TREND ANALYSIS (3 metrics) =====
  trend_slope_per_day           DECIMAL(18, 6)    COMMENT 'Linear trend slope (Δvalue/Δday)',
  trend_direction               VARCHAR(32)       COMMENT 'INCREASING, DECREASING, STABLE',
  autocorrelation_lag1          DECIMAL(18, 6)    COMMENT 'Autocorrelation at lag 1 (0-1)',

  -- ===== FORECASTING (2 metrics) =====
  forecast_next_period          DECIMAL(18, 6)    COMMENT 'Predicted value for next period',
  forecast_error_mape           DECIMAL(18, 6)    COMMENT 'Mean Absolute Percentage Error (%)',

  -- ===== BENCHMARKING & RATIOS (3 metrics) =====
  benchmark_value               DECIMAL(18, 6)    COMMENT 'Target or benchmark KPI value',
  benchmark_ratio               DECIMAL(18, 6)    COMMENT 'Current mean / benchmark',
  pct_diff_benchmark            DECIMAL(18, 6)    COMMENT 'Percent difference from benchmark',

  -- ===== CONFIDENCE INTERVALS (2 metrics) =====
  ci_lower_95                   DECIMAL(18, 6)    COMMENT '95% CI lower bound',
  ci_upper_95                   DECIMAL(18, 6)    COMMENT '95% CI upper bound',

  -- ===== METADATA & AUDIT =====
  analytics_timestamp           TIMESTAMP         COMMENT 'When these statistics were computed',
  computation_duration_seconds  DECIMAL(10, 2)    COMMENT 'Time to compute all metrics (sec)',
  computation_status            VARCHAR(32)       COMMENT 'SUCCESS, PARTIAL, FAILED',
  last_updated                  TIMESTAMP         DEFAULT CURRENT_TIMESTAMP COMMENT 'Record update time'
);

CREATE INDEX IF NOT EXISTS idx_kpi_stats_timestamp
  ON analytics.kpi_statistics_by_borough(analytics_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_kpi_stats_trend
  ON analytics.kpi_statistics_by_borough(trend_direction, borough);

COMMENT ON TABLE analytics.kpi_statistics_by_borough IS
  'Analytics layer: 60+ statistical metrics for 18 KPIs × 5 boroughs. One row per KPI-borough pair. Denormalized wide table.';
