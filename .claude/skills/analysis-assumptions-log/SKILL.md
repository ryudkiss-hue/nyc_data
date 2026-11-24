---
name: analysis-assumptions-log
description: Track and document analytical assumptions and decisions. Use when making analytical choices, documenting trade-offs, ensuring transparency, or creating audit trails for analytical work.
---

# When to use
- Starting any significant analysis where assumptions will influence conclusions
- Preparing work for peer review or stakeholder presentation
- Returning to an analysis after a break and needing to reconstruct decisions
- In regulated or high-stakes environments requiring audit trails
- Handing off an analysis to another analyst

# Process
1. **Initialise the log** — create a structured JSON entry via `scripts/assumptions_tracker.py` with analysis name, author, date, and data sources
2. **Document data assumptions** — for each data source: record what population is included/excluded, how nulls are handled, what time period is used, and confidence level (high / medium / low)
3. **Document business logic assumptions** — record how business terms are defined, which calculation approach was chosen and why, and what alternatives were considered
4. **Document statistical assumptions** — note any statistical assumptions relevant to the methods used (e.g. normality for t-tests, independence of observations)
5. **Assess impact** — for each assumption, estimate impact if wrong (high / medium / low); flag high-impact assumptions for validation before finalising conclusions

# Inputs the skill needs
- Required: analysis name and data sources being used
- Required: methodological choices made so far
- Optional: stakeholder-provided definitions for business terms
- Optional: known data quality issues

# Output
- `scripts/assumptions_tracker.py` — CLI tool for logging assumptions and flagging critical ones
- `assets/assumptions_log_template.md` (filled) — structured log for peer review and audit trail
