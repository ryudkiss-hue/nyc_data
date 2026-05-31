# Time Series Patterns Guide

## Core components of a time series

**Trend:** The long-term direction of the metric. Identified by smoothing out noise (rolling average) and looking at the slope over 4+ periods.

**Seasonality:** Repeating patterns tied to a fixed calendar period — weekly (Monday dips), monthly (end-of-quarter spikes), or yearly (holiday peaks).

**Cyclical variation:** Longer, irregular fluctuations not tied to a calendar (economic cycles, product maturity phases). Harder to distinguish from trend changes.

**Noise / residual:** Random variation after accounting for trend, seasonality, and known events.

---

## Detecting each pattern

### Trend detection
- Plot the series with a rolling average (window = 4–8 periods)
- A consistently rising or falling rolling average indicates trend
- Compare first-third vs last-third of the series mean

### Seasonality detection
- Plot the same metric across multiple years on the same axis
- Compare average value by day of week, week of year, or month
- High coefficient of variation within each year but low across years suggests seasonality

### Anomaly detection
- Z-score: `(value - mean) / std`. |z| > 2.5 is a common threshold
- IQR method: flag values outside `[Q1 - 1.5×IQR, Q3 + 1.5×IQR]`
- Residual method: fit a trend + seasonal model; anomalies are large residuals

---

## Period-over-period comparisons

| Comparison | Use case | Caveat |
|---|---|---|
| WoW (week over week) | Operational monitoring | Affected by day-of-week composition |
| MoM (month over month) | Business performance | Affected by different month lengths |
| YoY (year over year) | Strategy, removes seasonality | Affected by prior-year anomalies |
| Rolling 4-week average | Smoothed trend | Lags behind actual changes |

**YoY comparisons** are the most useful for metrics with strong seasonality. MoM and WoW are better for operational monitoring.

---

## Common time series patterns and their interpretations

**Step change:** A sudden level shift at a point in time. Usually caused by a product change, policy change, or data pipeline change. Investigate what changed on that date.

**Gradual decline:** Slow but consistent downward trend. Often indicates product decay, customer churn accumulation, or competitive erosion. Requires understanding the cohort structure.

**Hockey stick:** Slow growth followed by rapid acceleration. Usually tied to a product or market inflection point. Validate that it's not a data artefact.

**Sawtooth pattern:** Regular sharp rises followed by drops. Common in metrics driven by monthly billing cycles, quota-based sales activity, or batch processing.

**Spike and return:** A one-period anomaly that returns to baseline. Usually a one-off event (outage, campaign, holiday). Lower investigation priority than persistent shifts.

---

## Forecasting expectations

For most analytical contexts, a simple forecast is sufficient:

1. **Baseline extrapolation:** Extend the recent trend forward
2. **Seasonal naive:** Next period = same period last year × recent trend adjustment
3. **Rolling average:** Next period ≈ last N-period average

For production forecasting systems, use proper time-series models (ARIMA, ETS, Prophet). For one-off analyses, the above are usually sufficient and far more explainable.

---

## Documentation checklist for time series analysis

- [ ] Period covered, data source, and refresh cadence stated
- [ ] Seasonal adjustment applied or explicitly skipped (with reason)
- [ ] Trend direction and approximate rate quantified
- [ ] All anomalies flagged with known or hypothesised explanation
- [ ] Forecast produced with explicit assumptions and uncertainty range
- [ ] YoY context provided for any metric with visible seasonality
