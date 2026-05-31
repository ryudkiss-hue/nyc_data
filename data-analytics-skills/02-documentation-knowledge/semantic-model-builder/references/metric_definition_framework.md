# Metric Definition Framework

A metric definition is complete only when it can answer all of the questions below unambiguously. Use this framework as an interview guide when gathering inputs from data owners.

---

## The 7 Questions Every Metric Definition Must Answer

### 1. What is it? (Plain-English definition)
One sentence a non-technical stakeholder can read and immediately understand.

> **Bad:** "MRR is the sum of MRR."  
> **Good:** "Monthly Recurring Revenue (MRR) is the predictable revenue generated each month from active subscriptions, excluding one-time fees and refunds."

---

### 2. How is it calculated? (Calculation logic)
Provide the SQL, formula, or numbered plain-English steps.

```sql
-- MRR example
SELECT
  DATE_TRUNC('month', billing_date) AS month,
  SUM(subscription_amount)          AS mrr
FROM subscriptions
WHERE status = 'active'
  AND billing_frequency = 'monthly'
GROUP BY 1
```

For derived metrics (e.g. MoM growth rate), show how it builds on a base metric:
```
MoM Growth Rate = (MRR_this_month - MRR_last_month) / MRR_last_month
```

---

### 3. What is the grain? (One row = what?)
Clearly state the level of aggregation the metric is reported at.

> "One row per account per month" — not "one row per event."

---

### 4. What is included / excluded?
List explicit inclusions and exclusions that are not obvious from the SQL alone.

| Include | Exclude |
|---|---|
| Monthly subscriptions | Annual subscriptions |
| Active status | Trial, churned, paused |
| Base subscription fee | Add-ons, overages, refunds |

---

### 5. What are the known edge cases?
Document any business rules that required special handling.

Examples:
- Upgraded subscriptions are counted at the new price from the upgrade date, not pro-rated
- Accounts with payment failures but not yet churned are included until 30 DPD
- Multi-currency: converted to USD using the exchange rate on the billing date

---

### 6. Who uses it and for what decision?
Name the consumer (person, team, dashboard) and the decision they use this metric to make.

> "Used by the CFO and Revenue Operations team in the monthly board deck to assess subscription revenue health and inform hiring decisions."

---

### 7. What does "good" look like?
Provide a business benchmark or target range, if known.

> "Healthy: > $2M / month. Alert threshold: < $1.5M (triggers exec review). Current YoY growth target: 40%."

---

## Metric Types

| Type | Definition | Example |
|---|---|---|
| **Simple** | Direct aggregate of a single measure | Total orders |
| **Ratio** | Numerator ÷ denominator (both aggregates) | Conversion rate = paid / visited |
| **Cumulative** | Running total from a start date | Cumulative revenue since launch |
| **Derived** | Arithmetic on other defined metrics | Net Revenue Retention = (Starting MRR + Expansion − Churn) / Starting MRR |

---

## Common Metric Anti-Patterns to Avoid

- **Undefined scope:** "Active users" without specifying what "active" means (login? purchase? any event?)
- **Ambiguous time attribution:** when a subscription started vs. when it billed vs. when revenue is recognised
- **Double-counting:** joining non-unique tables without aggregating first
- **Hardcoded business rules in SQL:** status = 'active' without documenting what other status values mean
- **Missing denominator definition:** "Conversion rate" without specifying the denominator population
