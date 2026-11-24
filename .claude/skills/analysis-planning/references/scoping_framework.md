# Analysis Scoping Framework

Use this framework to decompose a business question into answerable sub-questions before touching any data.

## Step 1 — Restate the question precisely

Rewrite the stakeholder question in data terms. Replace vague words with measurable ones.

| Vague | Data-precise |
|---|---|
| "Are ramps getting done on time?" | "What fraction of ramp_progress records have `date_closed` within 90 days of `date_opened`, by borough, for calendar year 2025?" |
| "Are violations trending up?" | "What is the month-over-month change in new violations rows (violations, 6kbp-uz6m) from 2025-01 to 2026-06, grouped by `violation_type`?" |
| "Is the data fresh?" | "What is the `last_modified` timestamp on each registered dataset, and which exceed their SLA threshold (HIGH=14d, MED=30d, LOW=60d)?" |

## Step 2 — Decompose into sub-questions

Each sub-question must be answerable with **one data pull or one calculation**. If it needs two, split it.

Template:
```
SQ1: [What metric?] for [which population?] over [which time window?]
SQ2: [What comparison?] between [which segments?]
SQ3: [What root cause?] when [condition from SQ1/SQ2]
```

Worked example — "Ramp completion SLA audit for Q1 2026":
```
SQ1: Completion rate per borough from ramp_progress where date_opened >= 2026-01-01
SQ2: Compare Q1 2026 rate to Q4 2025 baseline
SQ3: For boroughs below 70%, which inspectors have the most open items?
SQ4: Are open items clustered spatially (DBSCAN on lat/lon)?
```

## Step 3 — Map sub-questions to datasets

| Sub-question | Dataset key | Fourfour | Availability | Filter needed |
|---|---|---|---|---|
| SQ1 | ramp_progress | e7gc-ub6z | Confirmed | date_opened >= '2026-01-01' |
| SQ2 | ramp_progress | e7gc-ub6z | Confirmed | date_opened >= '2025-10-01' |
| SQ3 | inspection | dntt-gqwq | Confirmed | status = 'OPEN' |
| SQ4 | ramp_progress | e7gc-ub6z | Confirmed | status != 'CLOSED' |

## Step 4 — Identify blockers early

Check each dataset against known issues before committing to a plan:
- `ramp_locations` (ufzp-rrqu) — stale since 2021, do not use for current ramp data
- `capital_blocks` (jvk9-k4re) — empty, use `capital_intersections` instead
- `permit_stipulations` (gsgx-6efw) — API 403, unavailable
- `weekly_construction` (r528-jcks) — stale since 2017

## Step 5 — Define done

State explicitly what the output looks like so you know when to stop:

```
Output: markdown table with columns [borough, n_ramps, completion_rate, ci_lower, ci_upper, vs_prior_quarter]
Delivery: pasted into Slack #dot-analytics + attached as .xlsx
Accepted when: PM confirms numbers match their tracking sheet within ±2%
```
