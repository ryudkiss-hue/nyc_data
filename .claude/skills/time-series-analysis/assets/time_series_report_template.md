# Time-Series Analysis: [Metric Name]

**Dataset:** [e.g., inspections / violations / ramp_progress]
**Period:** YYYY-MM-DD → YYYY-MM-DD
**Analyst:** [Name]
**Date:** YYYY-MM-DD

---

## Key Finding

> [One sentence. E.g., "Daily sidewalk violations in Brooklyn increased 18% over the past 90 days, with a structural step-change visible in late April coinciding with new contractor onboarding."]

---

## Trend Summary

| Metric | Value |
|--------|-------|
| Overall direction | Upward / Downward / Flat |
| Slope (units/day) | |
| Period mean | |
| Period std dev | |
| Min (date) | |
| Max (date) | |
| Rolling window used | ___ days |

## Stationarity

- ADF test result: ___
- Interpretation: ___
- Differencing applied: Yes / No

---

## Seasonal Patterns

| Pattern | Observed | Notes |
|---------|----------|-------|
| Day-of-week peak | | |
| Day-of-week trough | | |
| Peak month | | |
| Holiday gap handling | | |

---

## Anomalies

| Date | Value | Type (spike/dip) | Likely cause |
|------|-------|-----------------|-------------|
| | | | |
| | | | |

Total anomalies outside 2σ band: ___

---

## Month-over-Month Change (last 6 months)

| Month | Value | MoM % |
|-------|-------|--------|
| | | |
| | | |
| | | |
| | | |
| | | |
| | | |

---

## Forecast (if applicable)

**Horizon:** ___ days / weeks / months
**Method:** Moving average / ARIMA / SARIMA

| Period | Point Forecast | 80% PI | 95% PI |
|--------|---------------|--------|--------|
| | | | |
| | | | |

**Assumptions:**
- [ ] No structural breaks in forecast period
- [ ] Seasonal pattern holds
- [ ] Operational capacity unchanged

---

## Known Events / Caveats

- [Date]: [Event that affected the series]
- [Date]: [Data quality issue]

---

## Recommended Actions

1. [ ] [Action with owner and due date]
2. [ ] [Action with owner and due date]
3. [ ] Set alert at rolling_mean ± 2σ for ongoing monitoring
