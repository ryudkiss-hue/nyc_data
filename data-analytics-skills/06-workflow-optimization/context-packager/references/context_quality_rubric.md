# Context Quality Rubric

Score a context package before sending it to an AI session. Target: 70+ points.
A package below 50 will produce inconsistent or hallucinated results.

---

## Scoring dimensions (100 points total)

### Dimension 1 — Clarity of goal (20 pts)

| Score | Criterion |
|---|---|
| 20 | Goal is stated as a precise, data-answerable question with metric, population, and time window |
| 15 | Goal is clear but missing one of: metric, population, or time window |
| 10 | Goal is a business question without data specification |
| 5 | Goal is vague ("analyze the data", "look at trends") |
| 0 | No goal stated |

### Dimension 2 — Schema coverage (25 pts)

| Score | Criterion |
|---|---|
| 25 | All columns used in analysis are defined with type and business meaning; fourfour is provided |
| 20 | Key columns defined; one or two minor columns missing |
| 15 | Dataset identified but only generic column descriptions |
| 5 | Dataset name only, no schema |
| 0 | No dataset information |

### Dimension 3 — Metric precision (25 pts)

| Score | Criterion |
|---|---|
| 25 | Formula stated with exact numerator, denominator, and filter; CI method specified |
| 20 | Formula stated; CI method missing or vague |
| 15 | Metric named but formula implicit |
| 5 | Metric named but undefined |
| 0 | No metric defined |

### Dimension 4 — Constraints and guardrails (15 pts)

| Score | Criterion |
|---|---|
| 15 | Known-bad datasets explicitly excluded; row limit and token status noted; output structure specified |
| 10 | Some constraints stated; one or two gaps |
| 5 | Output format stated but no data constraints |
| 0 | No constraints |

### Dimension 5 — Token efficiency (15 pts)

| Score | Criterion |
|---|---|
| 15 | Package is within budget; no redundant restatement; pre-written snippets used where available |
| 10 | Within budget but contains some repetition |
| 5 | Over budget (estimate > ceiling) but still usable |
| 0 | Severely over budget or contains entire raw files |

---

## Quick self-check (before scoring formally)

Answer YES or NO:

- [ ] Does a reader know exactly what metric to compute from the context alone?
- [ ] Is the dataset fourfour included?
- [ ] Is the borough normalization strategy stated?
- [ ] Is the CI method stated for any proportion or rate?
- [ ] Are known-stale or known-empty datasets explicitly excluded?
- [ ] Is the output format (table columns, precision) stated?

If any answer is NO, fix before sending.

---

## Score interpretation

| Score | Quality | Recommendation |
|---|---|---|
| 90–100 | Excellent | Send as-is |
| 70–89 | Good | Minor gaps; acceptable for most analyses |
| 50–69 | Adequate | Will produce usable results but expect follow-up clarifications |
| 30–49 | Poor | High risk of incorrect results; fix schema or metric sections |
| 0–29 | Inadequate | Do not use; rebuild from context_layering_guide.md |

---

## Common failure modes

| Failure | Effect | Fix |
|---|---|---|
| No fourfour provided | AI may confuse datasets with similar names | Always include fourfour |
| Date field ambiguity | AI filters on wrong column; counts are wrong | State "date field = created_date (not inspection_date)" |
| Borough encoding not stated | AI produces fan-out by borough name variant | Add "normalize with upper(borough)" |
| No CI method | AI uses normal approximation for small n | Add "Wilson Score 95% CI for all proportions" |
| Stale dataset not excluded | AI uses ramp_locations (2021 data) | Add explicit exclusion list |
