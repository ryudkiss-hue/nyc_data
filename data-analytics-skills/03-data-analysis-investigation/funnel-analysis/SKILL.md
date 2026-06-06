---
name: funnel-analysis
description: Analyse conversion through a multi-step process, identify where users drop off, and diagnose why. Activate when conversion is low, when comparing conversion across segments, or when optimising a user journey.
---

# When to use
- Conversion is low and the team needs to know where users are dropping off
- Comparing conversion rates across channels, devices, or user segments
- A product change was made and you need to measure its effect on funnel completion
- Building a business case for investing in a specific funnel step

# Process
1. **Define funnel steps and timeframe** — list ordered steps (e.g. Visit → Signup → Activate → Purchase); define completion window (e.g. must complete within 7 days). Ambiguous definitions here will invalidate the analysis.
2. **Build user-level dataset** — extract first occurrence of each event per user within the completion window using `scripts/funnel_analyzer.py`
3. **Calculate conversion metrics** — compute absolute counts, step-to-step conversion rates, and overall funnel conversion rate
4. **Analyse time-to-convert** — calculate median and distribution of time between steps; identify whether slow converters have lower overall completion
5. **Segment the funnel** — break conversion by available dimensions (channel, device, geography, user segment); identify highest-impact differences
6. **Prioritise recommendations** — rank drop-off points by (users lost × revenue impact per user); fill `assets/funnel_report_template.md`

# Inputs the skill needs
- Required: event log data with user ID, event name, and timestamp
- Required: ordered list of funnel steps
- Required: completion window (e.g. 30 days from first step)
- Optional: segmentation dimensions
- Optional: estimated revenue value of a completed conversion

# Output
- `scripts/funnel_analyzer.py` — computes step-by-step conversions and drop-offs from event logs
- `references/funnel_design_guide.md` — funnel definition patterns and common measurement pitfalls
- `assets/funnel_report_template.md` (filled) — funnel table, segment comparison, and ranked recommendations
