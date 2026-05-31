---
name: root-cause-investigation
description: Systematic investigation of metric changes and anomalies. Use when a metric unexpectedly changes, investigating business metric drops, explaining performance variations, or drilling into aggregated metric drivers.
---

# Root Cause Investigation

# When to use
- A key metric dropped (or spiked) unexpectedly and the team needs an explanation
- Stakeholders are asking "why did X happen?" and need an evidence-based answer
- A metric change has been observed but the team is unsure whether it's noise or signal
- Preparing a post-mortem after an incident that affected business metrics
- A trend change happened weeks ago and needs retrospective investigation

# Process
1. **Validate the change** — confirm the metric changed beyond normal variance using a z-score or simple comparison to the rolling average. If the change is within ±1.5 standard deviations, document it as within normal range and close. Use `scripts/drilldown_analyzer.py --validate`.
2. **Establish a timeline** — plot the metric over time to pinpoint when the change started. A sudden step change suggests a specific event; a gradual drift suggests a structural shift.
3. **Decompose the metric** — break the metric into its constituent parts (e.g., revenue = volume × price × mix). Determine which component is driving the change before drilling into dimensions.
4. **Drill down systematically** — compare the metric before vs. after the change across available dimensions (geography, platform, channel, product category, user segment). Sort by absolute contribution to identify the primary driver. Use `scripts/drilldown_analyzer.py --drilldown`. See `references/rca_framework.md` for the structured approach.
5. **Test hypotheses** — generate explicit hypotheses (volume drop, mix shift, per-unit quality change, data issue) and accept or reject each with evidence. Correlate the timeline with known events from `references/hypothesis_testing_guide.md`.
6. **Write the root cause report** — document the primary driver (quantified share of impact), supporting evidence, rejected hypotheses, and tiered recommendations (immediate / short-term / long-term). Use `assets/rca_report_template.md`.

# Inputs the skill needs
- Metric name and historical values (at least 30 days before the change)
- Granular data with dimensional breakdowns (geography, platform, segment, etc.)
- The date or date range when the change was noticed
- A change log or incident log for the same period (product releases, campaigns, outages)
- The business context: what decisions depend on this metric

# Output
- `scripts/drilldown_analyzer.py` — validates the change, computes dimensional drill-downs, and ranks contributors by impact
- `references/rca_framework.md` — structured five-step RCA method with decision rules
- `references/hypothesis_testing_guide.md` — checklist of common root causes and how to test each
- `assets/rca_report_template.md` — report template: what changed, when, primary driver, supporting evidence, timeline, recommendations
