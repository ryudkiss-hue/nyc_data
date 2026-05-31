---
name: time-series-analysis
description: Temporal pattern detection and forecasting. Use when analyzing trends over time, detecting seasonality, identifying anomalies in time series, or building simple forecasting models for planning.
---

# Time Series Analysis

# When to use
- Building a forecast for operational planning (staffing, inventory, infrastructure capacity)
- Identifying whether a trend is genuine or driven by seasonality
- Detecting anomalies in a metric stream (traffic spikes, revenue dips, error rate surges)
- Providing a "what would have happened" baseline for measuring initiative impact
- Presenting year-over-year growth in a way that accounts for seasonal patterns

# Process
1. **Load and inspect the time series** — confirm regular intervals (fill gaps if needed), check for obvious data quality issues (negative values, zeros in non-zero series), and identify the natural granularity (daily, weekly, monthly).
2. **Test for stationarity** — run an ADF test. If non-stationary (trend or seasonality present), note this — it informs decomposition and model choice rather than blocking analysis. See `references/ts_patterns_guide.md`.
3. **Decompose into components** — separate the time series into trend, seasonal, and residual using additive or multiplicative decomposition. Measure the strength of each component (0–1). Strong seasonality (>0.6) means raw values are misleading without seasonal adjustment.
4. **Detect anomalies** — flag points more than 3 standard deviations from the rolling median. Investigate the top 5 anomalies against the event log (product releases, campaigns, incidents). Use `scripts/ts_analyzer.py --detect-anomalies`.
5. **Fit a forecast model** — fit an ARIMA model (or simpler moving average if data is short). Validate on a held-out 20% test set and report MAPE. Generate point estimates and 95% confidence intervals for the forecast horizon.
6. **Produce the analysis report** — summarise trend direction and strength, seasonal patterns and their business implications, anomaly findings, and the forecast with uncertainty. Use `assets/ts_report_template.md`.

# Inputs the skill needs
- Time series data: date column + one numeric metric column, minimum 2 full seasonal cycles
- Granularity of the data (daily, weekly, monthly)
- Forecast horizon required (days, weeks, months ahead)
- Event log or change log for anomaly investigation
- Business context: what drives this metric, known seasonal patterns

# Output
- `scripts/ts_analyzer.py` — decomposes, detects anomalies, and fits an ARIMA forecast; outputs charts and CSV
- `references/ts_patterns_guide.md` — stationarity, seasonality types, model selection guide, and common pitfalls
- `assets/ts_report_template.md` — report template: characteristics, decomposition summary, anomaly list, forecast table, insights
