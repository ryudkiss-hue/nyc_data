# Time Series Analysis Report

**Metric:** [metric name]
**Period:** [start date] to [end date]
**Frequency:** daily / weekly / monthly
**Analyst:** [name]
**Date:** [YYYY-MM-DD]

---

## Summary

**Trend:** [upward / downward / flat] — approximately [+/-]% per [period]
**Overall change:** [first period value] → [last period value] ([+/-]% total)
**Notable anomalies:** [n] detected ([list dates])
**Seasonal pattern:** [identified / not present / unknown]

---

## Statistical summary

| Statistic | Value |
|---|---|
| Periods | [n] |
| Mean | [value] |
| Median | [value] |
| Min | [value] ([date]) |
| Max | [value] ([date]) |
| Std deviation | [value] |
| Coefficient of variation | [%] |

---

## Trend analysis

**Direction:** [upward / downward / flat]
**Slope:** approximately [+/-]% per [period]
**Consistency:** [consistent / volatile / inflected at [date]]

**Interpretation:** [2–3 sentences on what the trend implies for the business]

---

## Seasonality

**Weekly pattern:** [e.g., "Consistently lower on weekends — avg 30% below weekday level"]
**Monthly pattern:** [e.g., "End-of-month spike in last 3 days — billing cycle effect"]
**YoY comparison:** [e.g., "Q4 consistently 25% above Q3 — holiday seasonality confirmed"]

---

## Anomalies

| Date | Value | Direction | Z-score | Likely explanation |
|---|---|---|---|---|
| [date] | [value] | Spike / Dip | [z] | [explanation or "unknown"] |

---

## Period-over-period growth rates

| Period | Value | WoW | MoM | YoY |
|---|---|---|---|---|
| [period] | [value] | [%] | [%] | [%] |
| [period] | [value] | [%] | [%] | [%] |

---

## Forecast (if applicable)

**Method:** [Seasonal naive / Rolling average / [model name]]
**Horizon:** [n] [periods]

| Period | Forecast | Lower bound | Upper bound |
|---|---|---|---|
| [period] | [value] | [value] | [value] |

**Key assumption:** [e.g., "Assumes current trend continues with no major product changes"]

---

## Recommendations

1. [Action — e.g., "Investigate the dip on [date] — aligns with a deployment; confirm if causal"]
2. [Action — e.g., "Set an alert for WoW change > 10% to catch future anomalies early"]
3. [Action — e.g., "Repeat analysis in [n] periods to confirm trend direction"]

---

*Template: ts_report_template.md*
