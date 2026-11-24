# Context Layering Guide

When starting an AI-assisted analysis session, context should be assembled in layers from most-stable to most-specific. Each layer is only included if it is relevant to the current analytical goal.

---

## The 5 context layers

### Layer 1 — Business context (always include)
- What program or project this supports (e.g. SIM ramp compliance review)
- Who the stakeholder is and what decision the analysis informs
- The specific question being answered in plain language
- The time window and geographic scope (boroughs, date range)

Typical token budget: 150–300 tokens

### Layer 2 — Data schema (include when joining or filtering on columns)
- Dataset name, fourfour, approximate row count
- Column names, types, and business definitions for columns the analysis will touch
- Known null rates and quality issues for those columns
- Borough encoding used in that dataset (full name vs. code)

Typical token budget: 200–500 tokens per dataset

### Layer 3 — Metric definitions (include when computing KPIs)
- Precise formula for each metric (numerator, denominator, filters)
- Agreed time basis (created_date vs. inspection_date vs. date_closed)
- SLA thresholds if freshness is relevant (HIGH=14d, MED=30d, LOW=60d)
- CI method to use (always Wilson Score for proportions, n < 1000)

Typical token budget: 100–200 tokens per metric

### Layer 4 — Analytical constraints (include for complex or risky analyses)
- Datasets that must NOT be used (stale, empty, or erroring — see CLAUDE.md known issues)
- Row limits and token access status (SOCRATA_APP_TOKEN set?)
- Required output structure (borough table, time-series, map)
- Peer review or sign-off required before delivery?

Typical token budget: 100–200 tokens

### Layer 5 — Output format preferences (always include, keep short)
- Response format: markdown table / JSON / .xlsx
- Precision: rates to 1 decimal, counts as integers
- Always include: n=, data freshness date, CI bounds for rates

Typical token budget: 50–100 tokens

---

## Layer selection guide

| Analysis type | Layers to include |
|---|---|
| Quick metric lookup | 1, 3, 5 |
| Borough breakdown table | 1, 2, 3, 5 |
| Time-series trend | 1, 2, 3, 4, 5 |
| Spatial conflict analysis | 1, 2, 4, 5 |
| Quality scorecard | 1, 2, 3, 4, 5 |
| NL → SoQL translation | 2, 5 |
| Executive summary | 1, 3, 5 |

---

## Trimming strategy when over budget

Priority order for trimming (remove lower-priority items first):

1. Remove full column lists — keep only columns the analysis will touch
2. Replace row counts with "~Xk" approximations
3. Collapse metric formulas to one-liner references ("Wilson CI for proportions")
4. Remove Layer 4 constraints that don't apply to the specific analysis
5. If still over: split into two sessions — schema context first, then analysis context

---

## NYC DOT context snippets (pre-written, ready to paste)

### Minimal SIM ramp context (~120 tokens)
```
Dataset: ramp_progress (e7gc-ub6z, ~187K rows, updates daily).
Borough column: borough (normalize: upper(trim(borough))).
Key metric: completion_rate = rows where status='CLOSED' / total rows.
CI method: Wilson Score 95% (always, n may be small for SI).
Boroughs: MN, BX, BK, QN, SI.
Output: markdown table with [borough, n, rate%, ci_lower%, ci_upper%].
```

### Minimal SIM violations context (~110 tokens)
```
Dataset: violations (6kbp-uz6m, ~312K rows, updates daily).
Date filter field: created_date (ISO 8601 in SOQL: created_date > '2026-01-01T00:00:00').
Borough column: borough (normalize with upper()).
Key metric: violation count per borough per month.
Output: markdown table with [month, borough, n_violations, mom_change%].
```
