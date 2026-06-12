-- Time Series Analysis Schema Extensions
-- Add stationarity test results and ARIMA/VAR columns to analytics layer

-- ALTER TABLE to add time series columns (DuckDB format)
-- Note: Execute this after 03_analytics_kpi_statistics_by_borough.sql

ALTER TABLE analytics.kpi_statistics_by_borough ADD COLUMN IF NOT EXISTS (
    adf_p_value                   DECIMAL(5, 4)     DEFAULT NULL COMMENT 'ADF stationarity test p-value',
    adf_is_stationary             BOOLEAN           DEFAULT NULL COMMENT 'TRUE if ADF test suggests stationary',
    kpss_p_value                  DECIMAL(5, 4)     DEFAULT NULL COMMENT 'KPSS stationarity test p-value',
    kpss_is_stationary            BOOLEAN           DEFAULT NULL COMMENT 'TRUE if KPSS test suggests stationary',
    arima_order                   VARCHAR(20)       DEFAULT NULL COMMENT 'Best ARIMA order as string (p,d,q)',
    arima_aic                     DECIMAL(12, 2)    DEFAULT NULL COMMENT 'ARIMA model AIC',
    forecast_value                DECIMAL(18, 6)    DEFAULT NULL COMMENT 'Forecasted value next period',
    forecast_ci_lower             DECIMAL(18, 6)    DEFAULT NULL COMMENT '95% CI lower bound',
    forecast_ci_upper             DECIMAL(18, 6)    DEFAULT NULL COMMENT '95% CI upper bound',
    var_lag_order                 INTEGER           DEFAULT NULL COMMENT 'VAR model optimal lag order',
    var_aic                       DECIMAL(12, 2)    DEFAULT NULL COMMENT 'VAR model AIC',
    timeseries_computation_date   TIMESTAMP         DEFAULT NULL COMMENT 'When time series metrics were computed'
);

-- Create index on time series columns for queries
CREATE INDEX IF NOT EXISTS idx_timeseries_stationarity
  ON analytics.kpi_statistics_by_borough(adf_is_stationary, kpss_is_stationary);

CREATE INDEX IF NOT EXISTS idx_timeseries_forecast
  ON analytics.kpi_statistics_by_borough(forecast_value, forecast_ci_upper);

CREATE INDEX IF NOT EXISTS idx_timeseries_computation
  ON analytics.kpi_statistics_by_borough(timeseries_computation_date);

-- View for serving layer (optional: materialized for zero-latency queries)
CREATE OR REPLACE VIEW app_queries.v_kpi_timeseries AS
SELECT
    kpi_name,
    borough,
    adf_p_value,
    adf_is_stationary,
    kpss_p_value,
    kpss_is_stationary,
    arima_order,
    arima_aic,
    forecast_value,
    forecast_ci_lower,
    forecast_ci_upper,
    var_lag_order,
    var_aic,
    timeseries_computation_date
FROM analytics.kpi_statistics_by_borough
WHERE timeseries_computation_date IS NOT NULL
ORDER BY kpi_name, borough;
