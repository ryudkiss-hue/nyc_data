---
name: time-series-analysis
description: Analyse temporal patterns in data including trends, seasonality, anomalies, and forecasting. Activate when you need to understand trends over time, detect seasonality, identify anomalies in time series, or build simple forecasting models for planning.
---

# When to use
- Detecting whether a KPI trend is improving, declining, or flat
- Identifying seasonal patterns to set appropriate targets
- Flagging anomalous data points that warrant investigation
- Building a simple forecast for planning or capacity purposes
- Comparing a current period to a historical baseline

# Process
1. **Data validation** — verify regular time intervals; identify and address gaps; assess series length and quality
2. **Stationarity testing** — apply ADF test to understand underlying patterns (trend-stationary vs. difference-stationary)
3. **Component decomposition** — separate trend, seasonal, and residual components using `scripts/time_series_analyzer.py`
4. **Anomaly identification** — flag statistical outliers; cross-reference with an event log to explain anomalies
5. **Model fitting** — implement ARIMA or moving average models; validate with hold-out period
6. **Report generation** — fill `assets/time_series_report_template.md` with findings, visualisations, and forecast

# Inputs the skill needs
- Required: historical time series data with timestamps and metric values
- Required: minimum 2 full seasonal cycles for reliable decomposition
- Optional: event log of known drivers (campaigns, outages, policy changes)
- Optional: forecast horizon and confidence interval requirements

# Output
- `scripts/time_series_analyzer.py` — decomposition, anomaly detection, ARIMA fitting
- `references/time_series_patterns.md` — pattern recognition guide for trends and seasonality
- `assets/time_series_report_template.md` (filled) — findings with component charts and forecast
