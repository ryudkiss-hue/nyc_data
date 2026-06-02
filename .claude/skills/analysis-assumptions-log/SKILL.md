---
name: analysis-assumptions-log
description: Track and document analytical assumptions and decisions. Use when making analytical choices, documenting trade-offs, ensuring transparency, or creating audit trails for analytical work.
---

# Analysis Assumptions Log

# When to use
- Starting an analysis with significant scope, method, or data quality choices
- Preparing work for peer review or stakeholder sign-off
- Returning to an old analysis and needing to understand prior decisions
- Working in a regulated environment where auditability is required
- Handing off an analysis to another analyst

# Process
1. **Initialize the log** — create a log entry for the analysis with its name, date, analyst, and the decision it informs. Use `scripts/assumptions_tracker.py` to initialise a structured JSON log.
2. **Enumerate data assumptions** — document representativeness, completeness, how missing values are handled, and any known quality issues. For each assumption, record the rationale and confidence level (high/medium/low). See `references/assumption_categories.md` for the full taxonomy.
3. **Enumerate business logic assumptions** — record metric definitions, time windows, inclusion/exclusion rules, and any definitions provided by stakeholders. Note alternatives considered.
4. **Enumerate statistical assumptions** — record distribution assumptions, independence claims, stationarity, or model assumptions relevant to the methods used.
5. **Assess impact and flag critical assumptions** — for each low-confidence assumption with high impact if wrong, create a validation plan. Run `scripts/assumptions_tracker.py --report` to surface the critical list.
6. **Validate and close** — as validation occurs, update the log with results. Export `assets/assumptions_log_template.md` for peer review sign-off before delivery.

# Inputs the skill needs
- Analysis name and the decision it informs
- Data sources, time period, and population being analysed
- Key methodological choices made (and alternatives considered)
- Stakeholder-provided business rule definitions
- Any known data quality issues

# Output
- `scripts/assumptions_tracker.py` — CLI tool to log assumptions, flag critical ones, and export a summary
- `assets/assumptions_log_template.md` — completed log for peer review and audit trail
