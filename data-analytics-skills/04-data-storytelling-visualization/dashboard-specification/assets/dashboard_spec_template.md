# Dashboard Specification: [DASHBOARD NAME]

**Version:** 1.0-draft
**Created:** [DATE]
**Author:** [NAME, TITLE]
**Status:** Draft | In Review | Approved
**Replaces:** [prior report or dashboard, if any]

---

## 1. Purpose Statement

> This dashboard answers **"[CENTRAL QUESTION]"**
> for **[AUDIENCE]**
> who need to **[DECISION OR ACTION THIS ENABLES]**.

---

## 2. User Profiles

### [Audience 1]

- **Visit frequency:** [Daily / Weekly / Monthly / Quarterly]
- **Primary questions:**
  - [Question 1]
  - [Question 2]
  - [Question 3]
- **Key decisions:** [What does this person do differently after viewing the dashboard?]
- **Technical comfort:** [Low / Medium / High]
- **Access context:** [Desktop browser / Mobile / Projected in meetings / Printed]

### [Audience 2 — add if truly distinct; otherwise build separate dashboard]

- **Visit frequency:**
- **Primary questions:**
- **Key decisions:**
- **Technical comfort:**

---

## 3. Metric Hierarchy

### Primary KPIs (max 5 — visible above the fold)

| # | Metric Name | Definition | Source Dataset | Fourfour | Refresh | Units |
|---|------------|-----------|---------------|----------|---------|-------|
| 1 | [e.g. Citywide Ramp Completion Rate] | Completed ramps / total ramps × 100 | ramp_progress | e7gc-ub6z | Daily | % |
| 2 | [e.g. Open Violations] | Count of violations with status = 'OPEN' | violations | 6kbp-uz6m | Daily | count |
| 3 | [e.g. Data Quality Score] | Composite 0–100 (35% completeness, 25% validity, 25% consistency, 15% freshness) | inspection | dntt-gqwq | Daily | score (0–100) |
| 4 | | | | | | |
| 5 | | | | | | |

### Secondary Metrics (supporting context, shown below hero)

| Metric | Definition | Source | Units |
|--------|-----------|--------|-------|
| [e.g. Inspections completed this week] | Count of inspection records with completed_date in last 7 days | inspection | count |
| [e.g. SLA compliance rate] | Datasets refreshed within SLA threshold / total datasets | — (computed) | % |
| | | | |

### Detail Breakdowns

- Borough breakdown: all 5 boroughs (MN, BX, BK, QN, SI) shown simultaneously
- [Breakdown 2 — e.g. by inspection type]
- [Breakdown 3 — e.g. by month / quarter]

---

## 4. Information Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ HERO: Primary KPI 1   │ Primary KPI 2   │ Primary KPI 3         │
│       [large number]  │  [large number] │  [gauge or sparkline] │
├─────────────────────────────────────────────────────────────────┤
│ TREND: [Metric] over last [90 days / 12 months]                 │
│        Borough toggle  │  Annotate SLA threshold                 │
├──────────────────────────────┬──────────────────────────────────┤
│ BREAKDOWN: Borough bar chart │ [Secondary chart — e.g. map]     │
│  Click borough → drill down  │                                   │
├─────────────────────────────────────────────────────────────────┤
│ DETAIL TABLE: [metric by block / record]   [Export CSV/Excel]   │
└─────────────────────────────────────────────────────────────────┘
```

**Layout notes:**
- Most important KPI: top-left
- Alerts and at-risk indicators: left column
- Detail table: optional on executive views (omit if audience is leadership)

---

## 5. Interactivity

| Interaction | Type | Default value | Decision it enables | Include? |
|-------------|------|--------------|---------------------|---------|
| Borough filter | Dropdown (multi-select) | All boroughs | Scope to operational area | [Yes / No] |
| Date range picker | Date range | Last 90 days | Trend comparison | [Yes / No] |
| SLA tier filter | Radio (HIGH / MED / LOW / All) | All | Manage by tier | [Yes / No] |
| Drill-down on borough | Click → detail view | — | Root cause investigation | [Yes / No] |
| [Add row for each interaction] | | | | |

**Removed interactions (with rationale):**
- [Interaction removed] — [reason, e.g. "not tied to a key decision"]

---

## 6. Data Requirements

| Dataset key | Fourfour | Source | Rows (approx) | Refresh | SLA tier | Known issues |
|------------|----------|--------|--------------|---------|----------|-------------|
| ramp_progress | e7gc-ub6z | data.cityofnewyork.us | ~187K | Daily | HIGH (14d) | — |
| violations | 6kbp-uz6m | data.cityofnewyork.us | ~312K | Daily | HIGH (14d) | — |
| inspection | dntt-gqwq | data.cityofnewyork.us | ~398K | Daily | HIGH (14d) | — |
| [add rows] | | | | | | |

**Refresh strategy:** Nightly APScheduler prefetch → DuckDB L2 Parquet cache → fall back to live Socrata API on cache miss.

**Quality gate:** Run `compute_quality_score()` on each dataset before rendering. If overall score < 60, display data quality warning banner.

---

## 7. Visual Design

**Color palette:** Follow semantic palette in `references/dashboard_design_principles.md`
- Green: on track / healthy
- Amber: at risk / warning
- Red: critical / breached
- Blue: neutral / informational

**Chart title convention:** State the finding, not the variable name.
- Wrong: "Ramp completion by borough"
- Right: "Staten Island ramp completion lags citywide average by 18 pp"

**Accessibility:** WCAG AA, greyscale-safe, icons alongside color coding.

---

## 8. Success Criteria

- [ ] Dashboard answers the purpose statement question in under 60 seconds for the target audience
- [ ] Primary KPIs visible without scrolling on a 1080p display
- [ ] All data sources refresh within their SLA threshold
- [ ] Chart titles state the finding, not the variable name
- [ ] All charts pass greyscale / WCAG AA accessibility check
- [ ] At least one member of the target audience has completed a usability walkthrough
- [ ] Stakeholder sign-off: _____________ Date: _____________

---

## 9. Out of Scope

(Explicitly list to prevent future scope creep)

- [Item 1 excluded — with brief rationale]
- [Item 2 excluded]

---

## 10. Open Questions

| # | Question | Owner | Due date | Resolution |
|---|---------|-------|---------|-----------|
| 1 | | | | |
| 2 | | | | |

---

## 11. Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0-draft | [DATE] | [NAME] | Initial draft |
