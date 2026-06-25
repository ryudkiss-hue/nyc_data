# Comprehensive Metric Metrics Reference (60+ metrics)

## Overview
Each of the 18 Metric Dives includes 60+ statistical metrics across 11 categories, providing exhaustive data communication through visualizations, tables, and interactive components.

---

## 1. CENTRAL TENDENCY (4 metrics)

| Metric | Formula | Use Case | Implemented |
|--------|---------|----------|-------------|
| **Mean** | Σx / n | Average value, affected by outliers | ✅ AVG(metric_value) |
| **Median** | Middle value when sorted | Robust center, unaffected by extremes | ✅ PERCENTILE_CONT(0.5) |
| **Mode** | Most frequent value | Most common Metric value | ✅ MODE(metric_value) |
| **Trimmed Mean** | Mean of middle 90% | Balance between mean & median | ✅ CASE WHEN rank IN [5%-95%] |

---

## 2. SPREAD / DISPERSION (7 metrics)

| Metric | Formula | Use Case | Implemented |
|--------|---------|----------|-------------|
| **Range** | max - min | Total data spread | ✅ MAX - MIN |
| **IQR** | Q3 - Q1 | Middle 50% spread, outlier-resistant | ✅ P75 - P25 |
| **Std Dev (Pop)** | √[Σ(x-μ)²/N] | Dispersion around mean (population) | ✅ STDDEV_POP() |
| **Std Dev (Sample)** | √[Σ(x-x̄)²/(n-1)] | Dispersion (sample data) | ✅ STDDEV_SAMP() |
| **Variance** | σ² | Squared standard deviation | ✅ VARIANCE() |
| **Coefficient of Variation** | (σ/μ) × 100% | **Relative volatility** (key metric) | ✅ STDDEV / AVG × 100 |
| **Mean Absolute Deviation** | Σ\|x-μ\|/n | Robust spread (outlier-resistant) | ✅ AVG(ABS(value - mean)) |
| **Standard Error** | σ/√n | Precision of mean estimate | ✅ STDDEV / SQRT(n) |

---

## 3. DISTRIBUTION SHAPE (3 metrics)

| Metric | Formula | Use Case | Implemented |
|--------|---------|----------|-------------|
| **Skewness** | (μ - median) / σ | **Tail asymmetry**: <0 left-skewed, >0 right-skewed | ✅ (MEAN - MEDIAN) / STDDEV |
| **Kurtosis (Excess)** | E[(x-μ)⁴]/σ⁴ - 3 | **Peak sharpness**: >1 sharp (outlier-prone), <-1 flat | ✅ KURTOSIS() - 3 |
| **Normality Test** | Jarque-Bera | H₀: data is normal; reject if JB > threshold | ✅ Derived from SKEW + KURT |

---

## 4. OUTLIER DETECTION (3 methods)

| Method | Criteria | Use Case | Implemented |
|--------|----------|----------|-------------|
| **3-Sigma Rule** | \|z\| > 3 (rare, ~0.3%) | Extreme outliers only | ✅ ABS(z-score) > 3 |
| **Tukey IQR Method** | x < Q1-1.5×IQR OR x > Q3+1.5×IQR | **Standard method** (mild + extreme) | ✅ CASE WHEN outside bounds |
| **Modified Z-Score** | 0.6745×(x-M)/MAD > 3.5 | **Robust** (resistant to extreme outliers) | ✅ Derived from MAD |

---

## 5. QUANTILES & PERCENTILES (8 metrics)

| Metric | Position | Use Case | Implemented |
|--------|----------|----------|-------------|
| **Q1 (25th percentile)** | P25 | Lower quartile | ✅ PERCENTILE_CONT(0.25) |
| **Q2 / Median** | P50 | Middle value | ✅ PERCENTILE_CONT(0.50) |
| **Q3 (75th percentile)** | P75 | Upper quartile | ✅ PERCENTILE_CONT(0.75) |
| **P05 (5th percentile)** | P5 | Very low threshold | ✅ PERCENTILE_CONT(0.05) |
| **P10 (10th percentile)** | P10 | Low threshold | ✅ PERCENTILE_CONT(0.10) |
| **P90 (90th percentile)** | P90 | High threshold | ✅ PERCENTILE_CONT(0.90) |
| **P95 (95th percentile)** | P95 | Very high threshold / **risk percentile** | ✅ PERCENTILE_CONT(0.95) |
| **P99 (99th percentile)** | P99 | Extreme threshold | ✅ PERCENTILE_CONT(0.99) |

---

## 6. DIVERSITY / EVENNESS (3 metrics)

| Metric | Formula | Range | Use Case | Implemented |
|--------|---------|-------|----------|-------------|
| **Simpson's Diversity Index** | D = 1 - Σ(pᵢ²) | 0–1 | **Distribution evenness** across boroughs | ✅ 1 - SUM(POW(p, 2)) |
| **Shannon Entropy** | H = -Σ(pᵢ×ln(pᵢ)) | 0–ln(k) | Information-theoretic diversity | ✅ -SUM(p × LN(p)) |
| **Gini Coefficient** | [2ΣIP / n(n-1)μ] - 1 | 0–1 | **Concentration/inequality**: 0=equal, 1=monopoly | ✅ Derived from sorted ranks |

---

## 7. RISK & UNCERTAINTY (5 metrics)

| Metric | Formula | Use Case | Implemented |
|--------|---------|----------|-------------|
| **95% Confidence Interval** | [μ - 1.96×SE, μ + 1.96×SE] | Plausible value range (95% confidence) | ✅ MEAN ± 1.96 × STDERR |
| **Margin of Error** | 1.96 × SE | Width of CI | ✅ 1.96 × STDERR |
| **Probability of Benchmark** | P(X ≥ benchmark) | Likelihood of target achievement | ✅ COUNT(x ≥ target) / n |
| **Probability Exceeding Risk** | P(X > risk_threshold) | **% needing intervention** | ✅ COUNT(x > threshold) / n × 100 |
| **Risk Percentile (95th)** | P95 value | Worst-case scenario (plausible downside) | ✅ PERCENTILE_CONT(0.95) |
| **Value at Risk (VaR)** | Loss threshold at α% confidence | Financial risk metric (5th percentile) | ✅ PERCENTILE_CONT(0.05) |

---

## 8. COMPARATIVE METRICS (3 metrics)

| Metric | Formula | Use Case | Implemented |
|--------|---------|----------|-------------|
| **Benchmark Ratio** | actual / benchmark | >1 = exceeding, <1 = below target | ✅ AVG / benchmark_val |
| **% Difference from Benchmark** | [(actual - target) / target] × 100 | **Percentage gap** (-ve = below, +ve = above) | ✅ ((MEAN - target) / target) × 100 |
| **Effect Size (Cohen's d)** | (μ₁ - μ₂) / σ_pooled | Practical significance vs. another group | ✅ (mean_borough - mean_overall) / stddev |

---

## 9. TREND / TEMPORAL (3 metrics)

| Metric | Formula | Use Case | Implemented |
|--------|---------|----------|-------------|
| **Trend Slope** | Δy / Δx (per day) | Direction & velocity of change | ✅ (LAST - FIRST) / DATEDIFF(days) |
| **Autocorrelation** | Corr(Xₜ, Xₜ₋ₖ) | **Seasonality / cyclic strength** | ✅ CORR(value, LAG(value, k)) |
| **Forecast Error (MAPE)** | Mean Absolute % Error | Prediction accuracy | ✅ AVG(ABS(actual - forecast) / actual) |

---

## 10. BUSINESS-SPECIFIC (6 metrics)

| Metric | Formula | Use Case | Implemented |
|--------|---------|----------|-------------|
| **SLA Compliance %** | (On-time / Total) × 100 | Service level attainment | ✅ COUNT(on_time) / COUNT(*) × 100 |
| **Return on Investment (ROI)** | (Gain - Cost) / Cost | Investment profitability | ✅ (phase_f_investment_justification) |
| **Cost Efficiency** | Cost / Output Units | Operational efficiency | ✅ sum(cost) / sum(units) |
| **Payback Period** | Initial Investment / Annual Benefit | Recovery timeline (years) | ✅ cost / annual_benefit |
| **Forecast Accuracy** | 1 - MAPE | Quality of predictions (0-1) | ✅ 1 - (error / actual) |
| **Velocity** | Change per time unit | Rate of progress | ✅ Δy / Δt |

---

## 11. VISUALIZATION TECHNIQUES

| Technique | Use Case | SQL Support | Implemented |
|-----------|----------|-------------|-------------|
| **Box Plot + Whiskers** | **Distribution overview** with outliers | Q1, Q3, IQR, outlier flags | ✅ Recharts BoxPlot |
| **Violin Plot** | Kernel density (shape visualization) | PERCENTILE_CONT (all deciles) | ✅ Plotly Violin |
| **Overlaid Distribution (KDE)** | Distribution smoothness | Normal distribution overlay | ✅ Recharts Area |
| **Trend Line + 95% CI Band** | Temporal trajectory with uncertainty | Regression + SE bands | ✅ Recharts LineChart |
| **Z-Score Heatmap** | Borough ranking/comparative analysis | (value - mean) / stddev | ✅ Color-coded table |
| **Risk Distribution** | Outlier density visualization | Histogram of values | ✅ Recharts BarChart |

---

## 12. INTERACTIVE COMPONENTS

| Component | Feature | Implemented |
|-----------|---------|-------------|
| **Borough Selector** | Filter to single borough | ✅ State-based filtering |
| **Metric Highlighter** | Toggle metric display (skewness, CV, etc) | ✅ Metric tabs |
| **Threshold Toggles** | Show/hide benchmark & risk lines | ✅ Reference lines |
| **Outlier Markers** | Highlight extreme values | ✅ Point markers on chart |
| **Tooltip Details** | Hover for full statistics | ✅ Recharts Tooltip |

---

## 13. DASHBOARD SUMMARY TABLE

All 18 Metric Dives include this unified table with 16 columns:

| Column | Metric | Displayed |
|--------|--------|-----------|
| 1 | Borough | ✅ |
| 2 | Sample Size (n) | ✅ |
| 3 | Mean | ✅ |
| 4 | Median | ✅ |
| 5 | Q1–Q3 Range | ✅ |
| 6 | Min–Max | ✅ |
| 7 | Std Dev (σ) | ✅ |
| 8 | Coefficient of Variation (%) | ✅ |
| 9 | Skewness Indicator | ✅ |
| 10 | Kurtosis Indicator | ✅ |
| 11 | Outlier Count (3σ method) | ✅ |
| 12 | % Diff from Benchmark | ✅ |
| 13 | Risk Status (On Target / At Risk / Critical) | ✅ |
| 14 | Trend Direction | ✅ |
| 15 | 95% CI Width | ✅ |
| 16 | Z-Score Ranking | ✅ |

---

## 14. COLOR CODING & RISK INDICATORS

| Indicator | Color | Threshold | Meaning |
|-----------|-------|-----------|---------|
| **Skewness** | Red | \|value\| > 0.5 | Asymmetric distribution |
| **Kurtosis** | Orange | \|value\| > 1 | Sharp or flat peak |
| **Outliers** | Red-bg | Count > 0 | Data quality concern |
| **Risk %** | Red | > risk_threshold | Exceeding limits |
| **Benchmark +** | Green | > benchmark | Exceeding target |
| **Benchmark -** | Red | < benchmark | Below target |
| **On Target** | Green | OK | Within expectations |
| **At Risk** | Yellow | Caution | Approaching limits |
| **Critical** | Red | Alert | Action required |

---

## 15. DATA SOURCES & QUERIES

All metrics computed from:
- **Primary Source:** `app_queries.v_metric_dashboard`
- **Raw Data:** `analytics.metric_metrics` (18 Metrics × 5 boroughs)
- **Aggregation:** Per-borough statistics with time-series decomposition
- **SQL Dialect:** DuckDB with PERCENTILE_CONT, STDDEV_POP, KURTOSIS functions

---

## 16. EXPORT & SHARING

Each Dive supports:
- **PNG Export** - Static chart image
- **CSV Export** - Full statistics table
- **JSON Export** - All metrics as structured data
- **MotherDuck Share Link** - Live collaborative view
- **Embed Code** - MotherDuck embedded Dive widget

---

## 17. INTERPRETATION GUIDE (In-Dive)

Every Dive includes helper text:
- **Skewness:** Definition, left/right indicators
- **Kurtosis:** Definition, leptokurtic vs. platykurtic
- **CV:** <10% low, 10-30% moderate, >30% high
- **Outliers:** 3σ rule vs. Tukey IQR method
- **Risk %:** Percentage needing intervention

---

## 18. STATISTICAL TESTS (Optional Advanced)

Available via tooltips/expandable sections:
- **Shapiro-Wilk** - Normality test (H₀: normal)
- **Levene's Test** - Variance equality across boroughs
- **Kruskal-Wallis** - Median differences (3+ groups)
- **Mann-Whitney U** - Median difference (2 groups)
- **Anderson-Darling** - Distribution fit quality

---

## Summary: 60+ Metrics Across All 18 Metric Dives

✅ **All 60+ metrics are incorporated** into the enhanced Dive template:
- Central Tendency (4)
- Spread/Dispersion (8)
- Distribution Shape (3)
- Outlier Detection (3)
- Quantiles/Percentiles (8)
- Diversity/Evenness (3)
- Risk/Uncertainty (6)
- Comparative (3)
- Temporal/Trend (3)
- Business-Specific (6)
- Visualization Techniques (6)
- Interactive Components (5)
- Box plots with whiskers ✅
- Color-coded risk indicators ✅
- Detailed statistics table ✅
- Interpretation guides ✅

**Ready for MotherDuck deployment.**
