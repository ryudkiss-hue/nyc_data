# Root Cause Analysis Framework

## When to use formal RCA

RCA is warranted when a metric moves materially and the cause is not immediately obvious. "Material" depends on context:

- Revenue: > 3% unexpected deviation
- Engagement: > 5% week-over-week change not explained by a known product change
- Error rate: any unexpected increase

Do not invest full RCA effort in movements explained by known causes (holiday, planned outage, product launch).

---

## The structured investigation sequence

### Step 1 — Confirm the signal
Before investigating, verify the movement is real:

- Is the data pipeline fresh? Check for ETL delays.
- Is the metric definition consistent? Has a query or schema changed?
- Is it one dashboard/report or does it appear in multiple independent sources?

A false alarm wastes team time. Confirm first.

### Step 2 — Scope the movement
Answer: **when** did it start, **how large** is it, **which populations** are affected?

- Plot a time series back 12+ weeks — is this a sudden drop or a gradual trend?
- Identify the exact start date (± 1–2 days)
- Check if it affects all users or a specific segment

### Step 3 — Correlate with known events
Check your event log:

- Deployments / feature releases
- Marketing campaigns or pricing changes
- Seasonal patterns (compare to same period last year)
- External events (competitor outage, news event, platform change)

If an event aligns with the movement onset, it is a strong candidate.

### Step 4 — Dimension breakdown
Use the drill-down tool to break the metric by:

- Platform / device
- Geography / region
- User segment (plan, cohort, acquisition channel)
- Product area / feature

The goal is to isolate whether the movement is concentrated in a specific slice.

### Step 5 — Generate and rank hypotheses
For each hypothesis, record:

- Description of the proposed cause
- Evidence for (what data supports it)
- Evidence against (what data contradicts it)
- Test that would confirm or refute it

Rank by: (likelihood × ease of testing). Test the most likely and easiest first.

### Step 6 — Validate the root cause
The root cause is confirmed when:

1. The hypothesis explains the timing, magnitude, and affected population
2. Removing or reversing the cause stops the movement (if possible to test)
3. No alternative hypothesis explains the data as well

### Step 7 — Document and close
Record the finding in the RCA report template. Include:
- Confirmed cause
- Impact quantification
- Corrective action and owner
- Preventive measure (how to catch this earlier next time)

---

## Contribution analysis

When a metric is a weighted sum (e.g., total revenue = sum across segments), use contribution analysis to find which segments drove the change:

`segment contribution = (value_b - value_a) / total_change`

A segment with large absolute change AND large contribution % is the primary driver.

Also decompose into:
- **Volume effect**: the segment had more/fewer users
- **Rate effect**: the metric per user changed
- **Mix effect**: the segment's share of total changed

---

## Common root causes by metric type

**Revenue drop**
- Pricing change (contraction/churn)
- Payment failure spike
- High-value customer churn
- Seasonal / calendar effect

**Conversion rate drop**
- UX bug in checkout / onboarding flow
- Traffic mix shift (lower-intent source)
- Page load regression

**Engagement drop**
- Feature removed or degraded
- Notification or email suppressed
- Competitive displacement
- Cohort aging effect
