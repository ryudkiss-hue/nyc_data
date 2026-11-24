# Peer Review Standards for SIM Analytics

Standards that all analytical work must meet before delivery to stakeholders.
Used by reviewers to calibrate their feedback and by authors to self-review.

---

## Tier 1 — Must-fix (blocks delivery)

Any of these findings must be resolved before the analysis is delivered.

### Statistical correctness
- [ ] Rates and proportions use Wilson Score CI, not normal approximation, for all n (this dataset has many small borough/period slices)
- [ ] Sample size n= is shown for every quantitative claim; n < 30 is flagged as "insufficient sample"
- [ ] Denominators are correct: rate calculations exclude null / missing values from denominator unless absence is meaningful
- [ ] No join fan-out: verify joining on unique keys (objectid); add DISTINCT or aggregate if key is non-unique
- [ ] Time filters use ISO 8601 in SOQL (e.g. `created_date > '2026-01-01T00:00:00'`), not relative dates

### Data integrity
- [ ] Dataset health was checked before analysis (dataset is not stale beyond SLA)
- [ ] Known-problem datasets were not used (ramp_locations stale, capital_blocks empty, permit_stipulations 403)
- [ ] Borough codes were normalized (upper(trim(borough))) before grouping — raw codes produce fan-out
- [ ] Row count in the analysis output plausibly matches expected dataset size (±20%)
- [ ] No synthetic or fabricated data in the output (test fixtures are exempt)

### Conclusions and framing
- [ ] Every conclusion is supported by data shown in the analysis
- [ ] "No data found" is distinguished from "data shows zero"
- [ ] Stale datasets that were used are flagged in the output with their last_modified date
- [ ] Uncertainty is communicated: CIs shown for rates, caveats for small n

---

## Tier 2 — Should-fix (quality issue, not a blocker)

These issues degrade quality and should be fixed unless there is a documented reason not to.

### Code and reproducibility
- [ ] Script can be run end-to-end from a clean environment with documented commands
- [ ] No hardcoded credentials, API tokens, or absolute local paths in code
- [ ] Column names referenced in code match the actual dataset schema
- [ ] Fetch uses `$where` and `$select` projections (no unbounded full-corpus pulls without justification)

### Presentation and clarity
- [ ] Borough order is consistent: MN, BX, BK, QN, SI
- [ ] Units are labeled on all table columns and chart axes (count, %, days, USD)
- [ ] Numbers are formatted consistently (rates to 1 decimal, counts with comma separator)
- [ ] Summary finding is stated in the first sentence of the write-up (not buried in a table)
- [ ] Data freshness date is shown in the output heading or footer

### Methodology documentation
- [ ] Date field used for time filtering is explicitly stated (created_date vs. inspection_date)
- [ ] Metric formulas are documented or referenced (not just shown as code)
- [ ] Any exclusions or data-cleaning steps are documented with row counts (before and after)

---

## Tier 3 — Nice-to-have (enhancements)

Log these for future iterations but do not block delivery.

- Spatial visualization of borough-level results
- Comparison to prior period (QoQ or YoY)
- Trend line or forecast added to time-series charts
- Executive summary paragraph at the top
- PDF or Excel export for archival

---

## Review scope agreement

Before starting a review, agree with the author on which tiers apply:

| Scope | Tiers reviewed |
|---|---|
| Quick turnaround / exploratory | Tier 1 only |
| Standard delivery review | Tiers 1 and 2 |
| Full production review | All tiers |
| Dashboard promotion to prod | All tiers + sign-off required |
