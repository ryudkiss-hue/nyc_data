# QA Checklist Master — NYC DOT Analysis Pre-Delivery Gate

Complete every section before sharing any analysis with stakeholders.
Mark each item: [P] Pass | [F] Fail (requires fix) | [N/A] Not applicable

---

## Section 1: Question Framing

- [ ] The analysis directly answers the original question or brief
- [ ] Scope matches what was agreed (borough, date range, dataset, row filter)
- [ ] Out-of-scope findings are labeled as supplementary, not as the primary result
- [ ] The question is stated explicitly at the top of the output

**NYC DOT specifics:**
- [ ] Borough scope is stated (all 5, or named subset)
- [ ] SIM unit vs. citywide distinction is clear if relevant
- [ ] Dataset key and fourfour are cited (e.g. `inspection` / dntt-gqwq)

---

## Section 2: Data Sourcing & Freshness

- [ ] Data source is named (dataset key + fourfour + row count)
- [ ] Pull date and `last_modified` timestamp are recorded
- [ ] Freshness is within SLA (HIGH=14d, MED=30d, LOW=60d)
- [ ] Known stale/broken datasets are flagged if used (see CLAUDE.md ⚠️ section)
- [ ] Row count matches expected range (e.g. `inspection` ~398K, not 5 rows)
- [ ] Any `$where` filters are documented and logically correct

**NYC DOT specifics:**
- [ ] `ramp_locations` (ufzp-rrqu) usage flagged — stale since 2021
- [ ] `capital_blocks` (jvk9-k4re) usage flagged — 0 rows
- [ ] `permit_stipulations` (gsgx-6efw) usage flagged — API 403

---

## Section 3: Transformations & Logic

- [ ] Every derived column or metric is defined (formula or description)
- [ ] Aggregations match the intended grain (row = borough, inspection, date?)
- [ ] Joins documented: which tables, on what key, join type (inner/left/right)
- [ ] No unintended row multiplication from many-to-many joins
- [ ] Date math accounts for timezone (NYC = UTC-5 / UTC-4 DST)
- [ ] Division operations are guarded against divide-by-zero
- [ ] Rates are expressed consistently (0–1 decimal OR 0–100 percent — not mixed)

---

## Section 4: Statistical Validity

- [ ] Sample size n is stated for every rate or percentage
- [ ] Wilson Score CI used for rates where n < 1,000 (not normal approximation)
- [ ] Confidence level stated (default 95%)
- [ ] No causal language ("caused", "drove") when showing correlation
- [ ] Comparison groups are compatible (same time period, same filter set)
- [ ] Outliers are investigated (removed only if documented and justified)
- [ ] Multiple comparisons: if testing 5+ boroughs, note potential for false positives

---

## Section 5: Finding Statements

- [ ] Lead finding is in plain language, not jargon
- [ ] Numbers include units (%, days, count, USD — never bare numbers)
- [ ] Comparisons have explicit baselines ("vs. last quarter", "vs. citywide avg")
- [ ] "Significant" is not used unless statistical significance is defined
- [ ] Findings distinguish observed data from inferences
- [ ] Uncertainty is communicated (e.g. "±3 pp margin of error")

---

## Section 6: Presentation Quality

- [ ] Chart axes have labels with units
- [ ] Chart titles describe the finding, not just the variable ("Manhattan Completion Up 12% in Q2" not "Completion Rate")
- [ ] Color is not the only encoding (pattern/label for accessibility)
- [ ] Tables have headers and no merged cells that break copy-paste
- [ ] Borough codes decoded for general audiences (MN → Manhattan)
- [ ] Data pull date appears in footer or notes

---

## Section 7: Assumptions & Caveats

- [ ] Every assumption is listed explicitly
- [ ] Assumptions sourced from data, SME, or documented as estimates
- [ ] At least one sensitivity test run on the most uncertain assumption
- [ ] Caveats section present in the output document
- [ ] Known data issues (stale datasets, nulls, API errors) disclosed

---

## Section 8: Recommendations

- [ ] At least one specific, actionable recommendation follows from the findings
- [ ] Recommendations name the responsible team or role
- [ ] Next analytical steps are suggested
- [ ] Recommendations do not over-claim (stay within scope of data)

---

## Quick-Fail Conditions (stop delivery immediately)

Any of these must be resolved before the analysis leaves the team:

1. Row count is 0 and no explanation is given
2. Completion rate or quality score exceeds 100%
3. A known-broken dataset is used without a warning
4. Rates from different time periods are compared without adjustment
5. No data source citation in the output
6. Causal claim made from observational data only
