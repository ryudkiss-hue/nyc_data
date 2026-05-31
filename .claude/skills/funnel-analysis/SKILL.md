---
name: funnel-analysis
description: Conversion funnel analysis with drop-off investigation. Use when analyzing multi-step processes, identifying conversion bottlenecks, comparing segments through a funnel, or optimizing user journeys.
---

# Funnel Analysis

# When to use
- Conversion is low and the team needs to know where users are dropping off
- A product change may have affected a specific funnel step
- Comparing conversion rates across channels, devices, or user cohorts
- Designing an A/B test and needing a baseline to set a meaningful MDE
- Building a regular funnel monitoring report

# Process
1. **Define funnel steps and time window** — list the ordered sequence of events or pages that constitute the funnel. Agree on how long a user has to complete the funnel (session, 24 hours, 7 days). Ambiguous definitions here will invalidate the analysis.
2. **Build the user-level funnel dataset** — for each user who reached step 1, record which subsequent steps they completed and when, within the time window. Use `scripts/funnel_analyzer.py` to compute this from an events log.
3. **Calculate conversion rates** — compute step-to-step conversion (users reaching step N ÷ users reaching step N−1) and overall conversion (step 1 to last step). Record absolute drop-off counts at each step.
4. **Analyse time-to-convert** — for users who completed each step, calculate median, P75, and P95 time between steps. Long gaps can signal friction even without high drop-off.
5. **Segment the funnel** — run the funnel separately by channel, device type, user cohort, or other dimensions. Rank segments by overall conversion rate and identify where the worst-performing segment diverges from the best. See `references/funnel_design_guide.md`.
6. **Prioritise and report** — rank drop-off points by absolute users lost × estimated revenue impact. Produce `assets/funnel_report_template.md` with the funnel table, segment comparison, and ranked recommendations.

# Inputs the skill needs
- Event log data with at minimum: user_id, event_name, timestamp
- Ordered list of funnel steps (event names in sequence)
- Time window for funnel completion
- Segmentation columns if a comparative analysis is needed (channel, device, plan)
- Estimated revenue value of a conversion (for impact sizing)

# Output
- `scripts/funnel_analyzer.py` — builds user-level funnel from an event log, computes step conversions, drop-offs, and time-to-convert
- `references/funnel_design_guide.md` — how to define funnels, choose time windows, and avoid common measurement mistakes
- `assets/funnel_report_template.md` — report template: funnel overview table, drop-off analysis, segment comparison, time-to-convert, recommendations
