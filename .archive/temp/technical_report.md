# Technical Analysis: Violation Closure Rate Trends by Borough

## Executive Overview

A linear regression analysis of violation closure rates across five NYC boroughs (January-June 2026) reveals statistically significant differences in resolution velocity. The model explains 78% of the variance (R-squared=0.78) in closure times across boroughs.

## Methodology

We fitted an ordinary least squares (OLS) regression with borough as the independent variable and days-to-closure as the dependent variable. The null hypothesis (H0: beta-1 = 0) was tested at alpha=0.05. Heteroskedasticity was detected (Breusch-Pagan test, p=0.003), so we applied Huber-White robust standard errors.

## Key Findings

### Finding 1: Manhattan Performance
Manhattan exhibits the shortest mean closure time at 12.3 days (95% confidence interval: [10.1, 14.5], n=4,872). The coefficient for Manhattan in the regression is the reference category (beta-0 = 12.3).

### Finding 2: Brooklyn Underperformance
Brooklyn's closure time is significantly longer than Manhattan's: beta-1 = +18.7 days (p < 0.001, standard error=2.1). This represents a 152% increase from the Manhattan baseline. The IQR for Brooklyn violations is [8, 31] days, with outliers (Z-score > 2.5) representing 7.2% of cases.

### Finding 3: Seasonal Autocorrelation
The Durbin-Watson statistic (1.32) suggests positive autocorrelation in residuals. An ADF test (p=0.042) rejects stationarity, indicating a potential temporal trend requiring ARIMA modeling for forecasting.

### Finding 4: Data Quality Issue
Schema drift was detected on 2026-04-15 when Socrata changed the borough code format from full names to abbreviations (e.g., "BK" vs. "Brooklyn"). This introduced duplicate records (n=312) that were excluded from analysis.

## Statistical Significance

All borough effects are statistically significant at p < 0.05. Confidence intervals do not overlap, indicating reliable differences. The model diagnostics (Q-Q plot, residual scatterplot) show no violations of normality assumptions.

## Recommendations

1. Investigate root causes of Brooklyn's 19-day closure lag
2. Implement an ARIMA forecast to predict Q3 backlog levels
3. Re-examine data pipeline for the 2026-04-15 schema change
4. Stratify analysis by violation type to detect category-specific delays
