---
name: root-cause-investigation
description: Systematically diagnose why a metric changed unexpectedly. Activate when a KPI moves significantly, a stakeholder asks "why did X drop/spike?", or a post-incident review requires evidence-based root cause documentation.
---

# When to use
- A key metric moved significantly and the team needs an explanation
- A stakeholder challenges a number and you need to trace the cause
- Post-incident review requires documented root cause analysis
- Distinguishing real signal from noise in a reported metric change

# Process
1. **Validate the change** — confirm the metric movement exceeds normal variance (use rolling average ± 2σ); rule out data quality issues before proceeding
2. **Establish timing** — plot the full metric history; identify exactly when the change began; distinguish sudden shift from gradual trend
3. **Decompose the metric** — break the metric into its components (e.g. revenue = volume × price × mix); use `scripts/drilldown_analyzer.py` to identify which component(s) drove the change
4. **Drill down by dimension** — compare performance across geography, platform, user segment, product; rank contributors by impact (absolute + % of total change)
5. **Generate and test hypotheses** — correlate the change timing against a list of known events (releases, campaigns, incidents); use `references/hypothesis_testing_guide.md`
6. **Document findings** — fill `assets/rca_report_template.md` with: change magnitude, timing, component analysis, dimension drilldown, validated hypothesis, and tiered recommendations

# Inputs the skill needs
- Required: metric name, time period, and magnitude of change
- Required: historical data sufficient to establish a baseline
- Optional: dimensional breakdown data (by segment, geography, channel)
- Optional: event log of potential causal events (releases, campaigns, outages)

# Output
- `scripts/drilldown_analyzer.py` — metric decomposition and dimensional contribution analysis
- `references/rca_framework.md` — structured RCA methodology and decision tree
- `references/hypothesis_testing_guide.md` — common root cause patterns and diagnostic tests
- `assets/rca_report_template.md` (filled) — evidence-based findings with tiered recommendations
