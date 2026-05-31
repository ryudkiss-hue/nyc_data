# Dashboard Specification

**Dashboard name:** [name]
**Owner:** [name / team]
**Date:** [YYYY-MM-DD]
**Status:** Draft / Approved / Built / Deprecated

---

## Purpose

**Primary question this dashboard answers:**
[One sentence]

**Primary audience:** [role, technical level]
**Secondary audience:** [if any]
**Usage frequency:** Daily / Weekly / Monthly / Ad-hoc

---

## Metrics

| Metric | Definition | Source table | Owner | Refresh | Acceptable lag |
|---|---|---|---|---|---|
| [metric] | [business definition] | [schema.table] | [team] | [cadence] | [hours/days] |

---

## Layout specification

### Page 1: [page name]

**Primary question:** [what this page answers]

| Position | Chart type | Metric | Dimensions | Filters |
|---|---|---|---|---|
| Top-left (hero) | KPI card | [metric] | — | [default filters] |
| Top-right | KPI card | [metric] | — | — |
| Centre | Line chart | [metric] | Over time | Date range |
| Bottom-left | Bar chart | [metric] | By [dimension] | — |
| Bottom-right | Table | [metrics] | By [dimension] | — |

**Default time range:** [last 30 days / current month / etc.]
**Sticky filters:** [date range, region, segment — which apply to all charts]

---

### Page 2: [page name — if applicable]

[Repeat layout table]

---

## Interactivity

| Feature | Required | Notes |
|---|---|---|
| Date range filter | Yes / No | Default: [value] |
| Segment filter | Yes / No | Options: [list] |
| Drill-down | Yes / No | Which charts / to what level |
| Cross-filter | Yes / No | Which charts are linked |
| Export / download | Yes / No | CSV / PDF |
| Alerts | Yes / No | Conditions and recipients |

---

## Access and governance

**Access level:** public / team-only / restricted
**Sensitive data present:** Yes / No — [type if yes]
**Row-level security needed:** Yes / No — [logic if yes]
**Who approves access requests:** [name / team]

---

## Data and infrastructure

**BI tool:** [Tableau / Looker / Power BI / Metabase / Other]
**Connection:** [data warehouse / database]
**Refresh schedule:** [cadence]
**Data owner sign-off:** [name] — [date]

---

## Acceptance criteria

- [ ] All metrics match definitions in the data catalog
- [ ] Default view loads in < [n] seconds
- [ ] Numbers cross-checked against source query output
- [ ] Stakeholder review completed
- [ ] Owner confirmed (not "analytics team")

---

*Template: dashboard_spec_template.md*
