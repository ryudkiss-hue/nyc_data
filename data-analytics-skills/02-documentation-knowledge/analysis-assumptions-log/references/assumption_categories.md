# Assumption Categories and Examples

## Why categorise assumptions?

Different assumption types carry different validation paths. A data assumption is validated with a SQL query; a statistical assumption requires a diagnostic test; a business logic assumption requires stakeholder sign-off.

---

## Data assumptions

Beliefs about how the underlying data was collected, recorded, and cleaned.

**Examples:**
- "NULL in the `cancelled_at` field means the order was not cancelled."
- "The `events` table contains one row per user action with no deduplication needed."
- "Missing values in `referrer_source` represent direct traffic, not a tracking gap."
- "Data before 2022-01-01 uses a different session definition and should be excluded."

**Validation methods:**
- COUNT(*) vs COUNT(field) to check NULL rates
- Spot-check with raw data or source system
- Confirm with data engineering team
- Check pipeline documentation / changelog

---

## Business logic assumptions

Beliefs about how business rules, definitions, and processes work.

**Examples:**
- "A customer is 'active' if they have made a purchase in the last 90 days."
- "Revenue is recognised at the point of invoice, not payment."
- "A 'conversion' requires completing checkout, not just adding to cart."
- "Refunds are netted out of the month they occurred, not the original sale month."

**Validation methods:**
- Stakeholder interview or written confirmation
- Comparison with existing metric definitions in the data catalog
- Review of finance/product specification documents

---

## Statistical assumptions

Beliefs about the mathematical properties required for the analytical method chosen.

**Examples:**
- "The outcome variable is approximately normally distributed for the t-test."
- "Observations are independent (no clustering by customer)."
- "The treatment and control groups are comparable on observed confounders."
- "The relationship between X and Y is linear (for regression)."

**Validation methods:**
- Histogram / Q-Q plot for normality
- Variance Inflation Factor (VIF) for multicollinearity
- Levene's test for equal variances
- Durbin-Watson for autocorrelation

---

## Technical assumptions

Beliefs about how systems, pipelines, and infrastructure behave.

**Examples:**
- "The ETL job runs at 06:00 UTC and data is complete by 07:00."
- "The API de-duplicates events before writing to the events table."
- "The `updated_at` timestamp reliably captures all row changes (no silent updates)."
- "Cross-border transactions use the exchange rate at the time of sale, not today's rate."

**Validation methods:**
- Pipeline log review
- Row count comparison pre/post ETL
- Spot-check timestamps on known events
- Engineering team confirmation

---

## Risk scoring guide

| Confidence | Impact if wrong | Risk score | Action |
|---|---|---|---|
| Low | Critical | 9 | Block delivery until validated |
| Low | High | 8 | Validate before presenting |
| Medium | Critical | 7 | Validate before presenting |
| Low | Medium | 5 | Document; validate if time allows |
| Medium | High | 6 | Document and flag in deliverable |
| High | Critical | 6 | Document; spot-check |
| Medium | Medium | 4 | Document only |
| High | High | 5 | Document only |
| High | Medium | 3 | Document only |
| Any | Low | 1–3 | Document only |
