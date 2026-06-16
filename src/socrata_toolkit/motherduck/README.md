# MotherDuck KPI Statistics Schema

Complete 4-tier data warehouse schema for computing and serving 60+ statistical metrics across 18 KPIs and 5 NYC boroughs.

## Architecture Overview

```
Layer 1: RAW_LANDING (90 rows)
  └─ analytics.kpi_metrics
     (raw KPI values from Socrata/MQTT)

Layer 2: STAGING (90 rows)
  └─ analytics.kpi_metrics_staged
     (deduplicated, ranked for quantile computation)

Layer 3: ANALYTICS (90 rows, 75+ columns)
  └─ analytics.kpi_statistics_by_borough
     (all 60+ metrics computed)

Layer 4: SERVING (90 rows, pre-computed)
  └─ analytics.kpi_metrics_comprehensive (materialized CTAS)
  └─ app_queries.v_kpi_statistics (view for Dives)
```

## Data Model

### Key Facts
- **Grain:** 1 row per KPI per borough (18 KPIs × 5 boroughs = 90 base rows)
- **Metrics:** 60+ statistical measures per row
- **Refresh:** Nightly (3 AM → 4 AM)
- **Consumption:** 18 MotherDuck Dives (zero-latency queries)

### 60+ Metrics Computed

#### Central Tendency (5)
- Mean, Median, Mode, Trimmed Mean

#### Spread/Dispersion (11)
- Range, IQR, StdDev (pop & sample), Variance, CV, MAD, SE

#### Distribution Shape (2)
- Skewness, Excess Kurtosis

#### Outlier Detection (2 + flags)
- 3-Sigma count, IQR count, Boolean flags

#### Quantiles & Percentiles (7)
- P05, P10, P25, P50, P75, P90, P95, P99

#### Diversity/Evenness (3)
- Simpson's Diversity Index, Gini Coefficient, Shannon Entropy

#### Risk/Uncertainty (5)
- % Exceeding Risk Threshold, Risk Percentile (95th), VaR, Tail Ratio, Expected Shortfall

#### Benchmarking & Ratios (3)
- Benchmark Ratio, % Diff from Benchmark

#### Trend/Temporal (3)
- Trend Slope, Trend Direction, Autocorrelation (Lag 1)

#### Forecasting (2)
- Forecast Next Period, Forecast Error (MAPE)

#### Confidence Intervals (2)
- 95% CI Lower, 95% CI Upper

### Advanced Statistical Tests (Optional, scipy/statsmodels, computed weekly)

#### Normality Tests (3)
- **Shapiro-Wilk p-value:** Most powerful for small samples
- **Jarque-Bera p-value:** Uses skewness + kurtosis
- **Anderson-Darling statistic:** Omnibus distribution test
- **Boolean flag:** is_normal (TRUE if Shapiro-Wilk p > 0.05)

#### Variance Equality Tests (2)
- **Levene's p-value (across boroughs):** Test if variance differs by borough
- **Boolean flag:** variances_equal (TRUE if p > 0.05)

#### Effect Size & Comparative (1)
- **Cohen's d vs. benchmark:** Standardized difference from target (effect size in σ units)

#### Seasonal Analysis (1)
- **Seasonal strength (STL):** 0-1 scale, higher = stronger seasonality (STL decomposition)

#### Autocorrelation Significance (1)
- **Ljung-Box p-value:** Is autocorrelation statistically significant? (p > 0.05 = not significant)

#### Robust Regression (2)
- **Robust regression slope (Huber M-estimator):** Slope less affected by outliers
- **Outlier sensitivity ratio:** Abs(robust_slope - linear_slope) / abs(linear_slope), 0-1 scale

## Files

### Schema Definitions (DDL)

| File | Purpose | Rows | Columns |
|------|---------|------|---------|
| `01_raw_landing_kpi_metrics.sql` | Raw landing table | 90 | 11 |
| `02_staging_kpi_metrics_staged.sql` | Staging: deduplicated + ranked | 90 | 13 |
| `03_analytics_kpi_statistics_by_borough.sql` | Full metrics computation | 90 | 75+ |
| `04_serving_kpi_metrics_comprehensive.sql` | Materialized serving + view | 90 | 50+ |

### Configuration

| File | Purpose |
|------|---------|
| `model_manifest.yml` | DAG definition, refresh schedule, validation checks |
| `kpi_statistics_engine.py` | Python orchestrator for metrics computation |

## Execution Schedule

### Nightly (3 AM – 4 AM Window)

```
9:30 PM  │ Layer 2: Staging (deduplicate, rank)
         │ Duration: 30 seconds
         │
10:00 PM │ Layer 3: Analytics (compute 60+ metrics)
         │ Duration: 120 seconds
         │ Includes: mean, median, stdev, CV, skewness, kurtosis, outliers,
         │           quantiles, diversity, risk, trend, benchmarking, CI
         │
10:05 PM │ Layer 4: Serving (materialize CTAS + view)
         │ Duration: 15 seconds
         │
10:10 PM │ Verification (check 90 rows, all metrics non-NULL)
         │ Duration: 5 seconds
         │
10:15 PM │ READY FOR DIVE QUERIES (zero-latency)
```

### Weekly (Sunday 11 PM)

Optional advanced metrics from scipy/statsmodels (can be disabled):

```
11:00 PM │ Normality tests (Shapiro-Wilk, Jarque-Bera, Anderson-Darling)
         │ Duration: 30 seconds | Requires: scipy
         │
11:00 PM │ Levene's test (variance equality across boroughs)
         │ Duration: 10 seconds | Requires: scipy
         │
11:00 PM │ Effect size (Cohen's d vs. benchmark)
         │ Duration: 5 seconds | Requires: scipy
         │
11:01 PM │ Seasonal decomposition (STL: trend + seasonal + residual)
         │ Duration: 20 seconds | Requires: statsmodels
         │
11:01 PM │ Autocorrelation significance (Ljung-Box test)
         │ Duration: 15 seconds | Requires: statsmodels
         │
11:02 PM │ Robust regression (Huber M-estimator)
         │ Duration: 20 seconds | Requires: statsmodels
         │
11:03 PM │ ADVANCED METRICS COMPLETE (~100 seconds total)
         │ Status stored in: advanced_metrics_status, advanced_metrics_timestamp
```

**Note:** Advanced metrics are optional. If scipy/statsmodels are not installed, they remain NULL and `advanced_metrics_status = 'SKIPPED'`. The core 60+ metrics are always computed.

## Usage

### Execute Full Pipeline

```bash
python src/socrata_toolkit/motherduck/kpi_statistics_engine.py
```

### Query KPI Statistics

```sql
-- All 18 KPIs, all 5 boroughs
SELECT kpi_name, borough, mean_value, median, std_dev, skewness, kurtosis
FROM app_queries.v_kpi_statistics
ORDER BY borough, kpi_name;

-- Single KPI across boroughs
SELECT borough, mean_value, median, q1_value, q3_value, outlier_count_3sd
FROM app_queries.v_kpi_statistics
WHERE kpi_name = 'phase_b_clustering_strength'
ORDER BY borough;

-- Risk summary
SELECT kpi_name, borough, pct_at_risk, var_95, risk_percentile_95
FROM app_queries.v_kpi_statistics
WHERE pct_at_risk > 10
ORDER BY pct_at_risk DESC;
```

### Advanced Metrics (Optional, Computed Weekly)

```sql
-- Is data normally distributed?
SELECT kpi_name, borough, is_normal, shapiro_wilk_p, skewness, kurtosis
FROM app_queries.v_kpi_statistics
WHERE is_normal = FALSE
ORDER BY shapiro_wilk_p;

-- Which KPIs have significantly different variance by borough?
SELECT DISTINCT kpi_name, variances_equal, levene_p
FROM app_queries.v_kpi_statistics
WHERE variances_equal = FALSE
ORDER BY levene_p;

-- Effect size vs. benchmark (in standard deviations)
SELECT kpi_name, borough, cohens_d, benchmark_ratio
FROM app_queries.v_kpi_statistics
WHERE ABS(cohens_d) > 1.0  -- Large effect size (>1 σ from target)
ORDER BY ABS(cohens_d) DESC;

-- Seasonal patterns (if applicable)
SELECT kpi_name, borough, seasonal_strength
FROM app_queries.v_kpi_statistics
WHERE seasonal_strength > 0.4  -- Strong seasonality
ORDER BY seasonal_strength DESC;

-- Trend sensitivity to outliers (is robust slope very different?)
SELECT kpi_name, borough, outlier_sensitivity, robust_slope, trend_slope
FROM app_queries.v_kpi_statistics
WHERE outlier_sensitivity > 0.2  -- Trend significantly affected by outliers
ORDER BY outlier_sensitivity DESC;

-- Advanced metrics computation status
SELECT DISTINCT advanced_metrics_status, COUNT(*) AS kpi_borough_pairs
FROM analytics.kpi_metrics_comprehensive
GROUP BY advanced_metrics_status;
```

### Data Quality Checks

```sql
-- Verify row count (should be 90)
SELECT COUNT(*) FROM analytics.kpi_metrics_comprehensive;

-- Check for NULL metrics
SELECT
  COUNT(CASE WHEN mean_value IS NULL THEN 1 END) AS null_mean,
  COUNT(CASE WHEN stddev_samp IS NULL THEN 1 END) AS null_stddev,
  COUNT(CASE WHEN skewness_index IS NULL THEN 1 END) AS null_skewness
FROM analytics.kpi_statistics_by_borough;

-- Verify freshness
SELECT
  MAX(analytics_timestamp) AS latest_timestamp,
  DATEDIFF('minutes', MAX(analytics_timestamp), CURRENT_TIMESTAMP) AS minutes_ago
FROM analytics.kpi_metrics_comprehensive;
```

## KPI Metadata (18 KPIs)

The `analytics.kpi_metadata` table defines all 18 KPIs:

| KPI Name | Phase | Unit | Benchmark | Risk Threshold |
|----------|-------|------|-----------|-----------------|
| phase_b_clustering_strength | B | 0-100 | 60 | 40 |
| phase_b_confidence | B | 0-1 | 0.85 | 0.6 |
| phase_b_resource_gap | B | % | 10 | 30 |
| phase_c_concentration_index | C | % | 70 | 50 |
| phase_c_segmentation_potential | C | 0-100 | 70 | 50 |
| phase_c_type_certainty | C | 0-1 | 0.85 | 0.7 |
| phase_c_distribution_balance | C | 0-1 | 0.9 | 0.5 |
| phase_d_outlier_concentration | D | count | 2 | 10 |
| phase_d_adoption_rate | D | % | 80 | 30 |
| phase_d_priority_score | D | 1-10 | 8 | 5 |
| phase_e_trend_direction | E | violations/day | -0.5 | 0.5 |
| phase_e_seasonality_strength | E | 0-1 | 0.3 | 0.7 |
| phase_e_resource_gap | E | % | 5 | 25 |
| phase_e_forecast_confidence | E | 0-1 | 0.85 | 0.5 |
| phase_f_sla_probability | F | % | 10 | 25 |
| phase_f_risk_score | F | 0-100 | 40 | 70 |
| phase_f_ci_coverage | F | % | 15 | 35 |
| phase_f_investment_justification | F | violations/$1K | 5 | 2 |

## Integration with Dives

All 18 KPI Dives query the serving layer:

```sql
SELECT * FROM app_queries.v_kpi_statistics
WHERE kpi_name = 'phase_b_clustering_strength'
```

Each Dive receives:
- **Summary cards:** Mean, Median, StdDev, CV, Skewness, Kurtosis, Outliers, Risk %, IQR
- **Box plot:** Q1, Median, Q3, Min, Max, Outlier markers
- **Detailed table:** 16 columns (n, mean, median, quartiles, range, σ, CV%, skew, kurt, outliers, vs_benchmark)
- **Risk indicators:** Color-coded status (Green/Yellow/Red)
- **Borough comparison:** Z-score ranking across MN, BK, BX, QN, SI

## Performance

- **Raw landing:** Append-only (30-minute increments)
- **Staging:** ~30 seconds
- **Analytics:** ~120 seconds (60+ metrics, DuckDB SQL functions)
- **Serving:** ~15 seconds (CTAS + view)
- **Dive query latency:** <100ms (materialized, pre-computed)

## Validation

Post-computation validation checks:
- ✅ 90 rows (18 KPIs × 5 boroughs)
- ✅ 75+ columns populated
- ✅ No NULL in computed metrics
- ✅ Uniqueness by (kpi_name, borough)
- ✅ Freshness: analytics_timestamp within last 30 minutes

## Future Enhancements

1. **Time-series metrics:** Trend slope, autocorrelation (LAG function + window)
2. **Bootstrap confidence intervals:** PyMC integration for Bayesian metrics
3. **Streaming refresh:** Event-driven updates vs. nightly batch
4. **Real-time alerts:** SLA breach detection, outlier notifications
5. **Custom aggregations:** User-requested statistical tests (Shapiro-Wilk, Levene's, etc.)

## References

- `model_manifest.yml` — DAG definition and refresh schedule
- `docs/KPI_METRICS_REFERENCE.md` — Complete metric glossary
- `scripts/create_kpi_dives_comprehensive.py` — Dive template using this schema
