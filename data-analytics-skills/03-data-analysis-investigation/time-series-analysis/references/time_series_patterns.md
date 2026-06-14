# Time-Series Patterns — NYC DOT Reference

## NYC DOT operational seasonality

### Weekly cycle (inspections dataset)
- **Mon–Fri:** Peak activity — field crews operate standard hours.
- **Sat–Sun:** Near-zero inspections — expect gaps; fill or exclude from rolling averages.
- **Holiday gaps:** Memorial Day, Labor Day, Thanksgiving cause multi-day gaps. Log as known events.

### Annual cycle (inspections + violations)
- **Mar–May:** Spring surge — freeze-thaw damage surfaces; highest new violation open rate.
- **Jun–Sep:** Steady state — high volume, manageable closure rate.
- **Oct–Nov:** Pre-winter push — crews close backlog before weather restrictions.
- **Dec–Feb:** Low volume — weather constraints; data gaps are operational, not data quality issues.

### 311 complaints (complaints_311)
- Peaks track heatwaves and major rain events (pooling water complaints).
- Friday afternoon spike in complaint submission (pre-weekend discovery).

---

## Pattern recognition guide

### Trend types

| Pattern | Visual signature | ADF result | Action |
|---------|-----------------|------------|--------|
| **Upward linear** | Steadily rising mean | Non-stationary (p>0.05) | Difference once; fit ARIMA(0,1,0) |
| **Downward linear** | Steadily falling mean | Non-stationary | Same as above |
| **Stationary** | Mean-reverting around constant | Stationary (p<0.05) | ARIMA(p,0,q) or moving average |
| **Step change** | Sudden level shift | Non-stationary | Split series at changepoint; model separately |
| **Seasonal only** | Regular wave with flat trend | Stationary | Seasonal decomposition (STL or additive) |
| **Trend + seasonal** | Rising/falling with waves | Non-stationary | SARIMA or STL + linear trend |

### Anomaly types

| Type | Description | NYC DOT example |
|------|-------------|-----------------|
| **Spike** | Single-point value >> 2σ above mean | Batch data upload after system outage |
| **Dip** | Single-point value << 2σ below mean | Holiday data gap reported as zero |
| **Level shift** | Persistent step up or down | New inspection crew added to a borough |
| **Variance change** | Spread widens/narrows | New data collection process introduced |

---

## ADF stationarity test interpretation

**Null hypothesis:** The series has a unit root (is non-stationary).

| ADF p-value | Interpretation | Remediation |
|-------------|---------------|-------------|
| p < 0.01 | Strongly stationary | Model as-is |
| 0.01–0.05 | Stationary | Model as-is with caution |
| 0.05–0.10 | Borderline | Apply single differencing, re-test |
| p > 0.10 | Non-stationary | Difference series; consider log transform for exponential growth |

---

## Rolling window selection

| Data frequency | Recommended window | Rationale |
|---------------|--------------------|-----------|
| Daily | 7 days | Removes weekly seasonality |
| Daily | 28 days | Removes monthly effects |
| Weekly | 4 weeks | Removes monthly cycle |
| Monthly | 3 months | Smooths quarterly variation |

For NYC DOT inspection data (daily), use **window=7** as default.
Use **window=28** when presenting to leadership (smoother, less noise).

---

## Forecast caveats for public-sector data

1. **Operational constraints cap the series.** Inspector headcount limits daily volume — forecasts can overshoot.
2. **Policy changes break model assumptions.** A new contractor or SLA change creates a structural break.
3. **Seasonal models need ≥ 2 full cycles.** Do not fit SARIMA on < 2 years of daily data.
4. **Always report a range, not a point.** 80% and 95% prediction intervals communicate uncertainty honestly.
