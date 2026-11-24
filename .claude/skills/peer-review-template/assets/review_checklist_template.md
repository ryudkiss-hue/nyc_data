# Peer Review Checklist

**Analysis title:** <!-- e.g. Q1 2026 Ramp Completion SLA Audit -->
**Author:** <!-- name -->
**Reviewer:** <!-- name -->
**Review date:** <!-- YYYY-MM-DD -->
**Review scope:** Tier 1 only / Tiers 1–2 / Full (all tiers)
**Analytical output type:** Notebook / Report / SQL query / Dashboard / Script

---

## Tier 1 — Must-fix (check all that apply to this analysis)

### Statistical correctness

| # | Check | Pass / Fail / N/A | Finding (if fail) |
|---|---|---|---|
| 1.1 | Wilson Score CI used for all proportion/rate calculations (not normal approximation) | | |
| 1.2 | n= shown for every quantitative claim; n < 30 rows flagged as "insufficient sample" | | |
| 1.3 | Denominators exclude nulls correctly (or null exclusion is documented) | | |
| 1.4 | Join keys verified as unique before joining; no fan-out | | |
| 1.5 | Date filters use ISO 8601 in SOQL (e.g. `created_date > '2026-01-01T00:00:00'`) | | |

### Data integrity

| # | Check | Pass / Fail / N/A | Finding (if fail) |
|---|---|---|---|
| 1.6 | Dataset health checked before analysis (not stale beyond SLA) | | |
| 1.7 | Known-problem datasets NOT used: ramp_locations (stale), capital_blocks (empty), permit_stipulations (403) | | |
| 1.8 | Borough codes normalized before grouping (upper/trim + CASE statement) | | |
| 1.9 | Row counts in output plausible vs. expected dataset size | | |
| 1.10 | No synthetic or fabricated data values in output | | |

### Conclusions

| # | Check | Pass / Fail / N/A | Finding (if fail) |
|---|---|---|---|
| 1.11 | Every conclusion is supported by data shown in the analysis | | |
| 1.12 | "No data found" distinguished from "data shows zero" | | |
| 1.13 | Stale datasets used (if any) are flagged with their last_modified date | | |
| 1.14 | Uncertainty communicated: CIs shown for rates, caveats for small n | | |

**Tier 1 result:** PASS / FAIL (must resolve all FAILs before delivery)

---

## Tier 2 — Should-fix (standard delivery review and above)

### Code and reproducibility

| # | Check | Pass / Fail / N/A | Finding (if fail) |
|---|---|---|---|
| 2.1 | Script runs end-to-end from clean environment with documented commands | | |
| 2.2 | No hardcoded credentials, tokens, or absolute local paths | | |
| 2.3 | Column names in code match actual dataset schema | | |
| 2.4 | Fetch uses `$where` and `$select` projections | | |

### Presentation

| # | Check | Pass / Fail / N/A | Finding (if fail) |
|---|---|---|---|
| 2.5 | Borough order consistent: MN, BX, BK, QN, SI | | |
| 2.6 | Units labeled on all table columns and chart axes | | |
| 2.7 | Rates formatted consistently to 1 decimal percent (e.g. 73.4%) | | |
| 2.8 | Summary finding stated in first sentence of write-up | | |
| 2.9 | Data freshness date shown in output heading or footer | | |

### Methodology documentation

| # | Check | Pass / Fail / N/A | Finding (if fail) |
|---|---|---|---|
| 2.10 | Date field used for time filtering is explicitly stated | | |
| 2.11 | Metric formulas documented or referenced | | |
| 2.12 | Any exclusions / cleaning steps documented with before/after row counts | | |

**Tier 2 result:** PASS / PASS WITH NOTES / FAIL

---

## Structured feedback

### Must-fix findings

| # | Location | Finding | Severity | Suggested fix |
|---|---|---|---|---|
| F1 | <!-- e.g. "Table 2, SI row" --> | | must-fix | |
| F2 | | | must-fix | |

### Should-fix findings

| # | Location | Finding | Severity | Suggested fix |
|---|---|---|---|---|
| F3 | | | should-fix | |

### Nice-to-have suggestions

- <!-- optional improvements for a future iteration -->

---

## Author response log

| Finding # | Resolution | Resolved by | Date |
|---|---|---|---|
| F1 | Resolved / Won't fix (rationale) / Deferred | | |
| F2 | | | |

---

## Overall recommendation

- [ ] **APPROVE** — all must-fix items resolved; ready for delivery
- [ ] **APPROVE WITH NOTES** — no must-fix items; should-fix items are acknowledged and deferred
- [ ] **REQUEST CHANGES** — must-fix items remain; re-review required after author fixes

**Reviewer signature:** <!-- name --> **Date:** <!-- YYYY-MM-DD -->
