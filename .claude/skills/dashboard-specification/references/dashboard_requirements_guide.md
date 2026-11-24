# Dashboard Requirements Guide
## Stakeholder Question Frameworks for NYC DOT Dashboards

---

## The Single-Sentence Purpose Test

Before specifying any dashboard, complete this sentence:

> "This dashboard answers **[central question]** for **[audience]** who need to **[decision or action]**."

If you cannot complete it in one sentence, the scope needs narrowing. Examples:

- "This dashboard answers *which boroughs are behind on ramp completion targets* for *DOT operations managers* who need to *reallocate field inspection crews weekly*."
- "This dashboard answers *are any inspection datasets going stale* for *DOT data stewards* who need to *trigger cache refreshes before SLA breach*."
- "This dashboard answers *how many ADA ramps were completed in each Council district this quarter* for *City Council members* who need to *assess DOT program performance at oversight hearings*."

---

## Stakeholder Interview Questions

Use these questions when gathering requirements from DOT stakeholders:

### Understanding the problem

1. What decision do you make that this dashboard should support?
2. How often do you make that decision — daily, weekly, monthly?
3. What data do you currently use to make that decision, and where do you find it?
4. What's the most frustrating gap in your current reporting?
5. What would "good" look like? What metric would tell you things are on track?

### Scoping the content

6. If you could only see three numbers when you open this dashboard, what would they be?
7. Is there a borough, inspection type, or date range you always filter to first?
8. Do you ever need to drill into individual records, or is aggregate enough?
9. Are there any calculations or metrics that are controversial or contested on your team?
10. Who else uses this data, and do they need the same view or a different one?

### Understanding constraints

11. Does this replace an existing report or supplement it?
12. Is there a refresh frequency requirement (e.g., data must be current as of this morning)?
13. Will this be projected in meetings or used at a desk? (affects font size and color choices)
14. Is there a print or export requirement?
15. Who approves the final version before launch?

---

## Audience-to-Dashboard Mapping

### Field Inspector Dashboard
- **Central question:** What do I need to inspect today, and where are the urgent issues?
- **Primary KPIs:** My open inspections (count), overdue inspections (count), violations flagged today (count)
- **Key interactions:** Map-first (borough → block → address), no date filters needed
- **Not needed:** Quality scores, dataset freshness, borough comparisons
- **Refresh:** Must be current as of 6am each day

### Operations Manager Dashboard
- **Central question:** Is the borough meeting its inspection and ramp completion targets?
- **Primary KPIs:** Completion rate % (vs target), inspections completed this week, SLA-at-risk datasets
- **Key interactions:** Borough filter, date range (last 30/90/365 days), drill to block level
- **Not needed:** Individual record lookup, raw API metadata
- **Refresh:** Nightly (acceptable)

### DOT Leadership / Executive Dashboard
- **Central question:** Is the program on track citywide, and where are the biggest risks?
- **Primary KPIs:** Citywide ramp completion rate (with 95% CI), open violation rate, data quality composite score
- **Key interactions:** None required — default view should answer the question; max one filter (date range)
- **Not needed:** Individual records, technical data quality detail, raw row counts
- **Refresh:** Weekly acceptable; nightly preferred

### City Council / Public Dashboard
- **Central question:** How is the DOT performing on ADA and sidewalk commitments in my district?
- **Primary KPIs:** District ramp completion rate, open violations, dismissal rate
- **Key interactions:** Council district or borough filter
- **Not needed:** Internal quality scores, schema drift alerts, cache status
- **Refresh:** Weekly (monthly acceptable)

---

## Common Scope Creep Patterns — and How to Resist

| Creep pattern | How it presents | Counter-question |
|--------------|----------------|-----------------|
| "Can you also add..." | Stakeholder keeps adding metrics beyond the core 5 | "Which of the current KPIs would you remove to make room?" |
| "We need every filter" | Request for 6+ filters "just in case" | "Which filter do you use in 80% of your visits?" |
| "Make it work for everyone" | Trying to serve field inspectors and leadership in one dashboard | "What's the one decision this dashboard supports?" |
| "Just show the raw data" | Request for a full data table as the primary view | "What question does a specific row answer that an aggregate can't?" |
| "Real-time" | Request for live updates when nightly is sufficient | "What decision requires data fresher than nightly?" |

---

## Metric Readiness Checklist

Before adding a metric to a dashboard spec, verify:

- [ ] Source table and field name are known
- [ ] Calculation is documented (numerator / denominator for rates)
- [ ] Refresh frequency matches the dashboard's refresh requirement
- [ ] Known data quality issues are flagged (e.g. `ramp_locations` stale since 2021)
- [ ] At least one stakeholder has confirmed the metric answers their question
- [ ] Units are specified (count, %, days, USD)
- [ ] Historical baseline exists for trend charts (minimum 3 months of data)
