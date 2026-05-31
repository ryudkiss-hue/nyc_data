# Visualization Specification

**Chart title (finding):** [state the finding, not the description]
**Owner:** [name]
**Date:** [YYYY-MM-DD]
**Destination:** [dashboard name / slide deck / report]

---

## Purpose

**Question this chart answers:** [one sentence]
**Primary audience:** [role / technical level]
**Decision or action it supports:** [what will the viewer do after seeing this?]

---

## Chart specification

**Chart type:** [bar / line / scatter / histogram / funnel / donut / other]
**Justification:** [why this type for this data — e.g., "Line because data is continuous over time"]

| Axis / Element | Field | Aggregation | Format |
|---|---|---|---|
| X-axis | [field name] | [none / month / category] | [date format / label] |
| Y-axis | [metric name] | [SUM / AVG / COUNT] | [$, % / number] |
| Colour | [field or fixed] | — | [palette or single colour] |
| Size | [field or fixed] | — | [if bubble chart] |
| Tooltip | [fields to show on hover] | — | — |

**Y-axis starts at:** 0 / [other value — state reason if not 0]

---

## Data

**Source:** [schema.table or pipeline]
**Filter conditions:** [e.g., "status = 'completed' AND date >= '2024-01-01'"]
**Grouping:** [e.g., "GROUP BY month, region"]
**Sample size / row count:** [n]

---

## Design instructions

**Highlight:** [which bar / point / line to accent — e.g., "Highlight the current month in dark blue"]
**Annotation:** [what to call out — e.g., "Add callout on March dip: 'Server outage Mar 14'"]
**Reference line:** [e.g., "Add horizontal line at target = $120K"]
**Legend:** [position / not needed — explain if removing]
**Colour palette:** [specific colours or palette name]

---

## Accessibility

- [ ] Colour-blind safe (no red-green contrast)
- [ ] Axes labelled
- [ ] Data labels included where chart will be printed or exported
- [ ] Alt text written for embedded use

---

## Acceptance criteria

- [ ] Title states the finding, not the description
- [ ] Numbers match the source query output
- [ ] Reviewed by [name] before publication

---

*Template: viz_spec_template.md*
