# Dashboard Requirements Guide

## Why requirements matter

Dashboards built without structured requirements are rebuilt. The most common failure modes: the audience is wrong (analysts built for executives), the primary question is unclear (15 charts but no obvious headline), the refresh cadence is wrong (daily data in a weekly-viewed dashboard), or the data isn't trusted (no lineage or last-updated timestamp).

Spend 30 minutes capturing requirements before building. It saves days.

---

## Requirements capture template

### 1. Audience and use case

- **Primary audience:** Who is this built for? (role, technical level)
- **Secondary audience:** Who else will use it?
- **Primary question:** The one question the dashboard must answer
- **Decision supported:** What decision or action does this enable?
- **Usage frequency:** Daily / weekly / monthly
- **Access method:** Desktop browser / mobile / embedded in product

### 2. Metrics specification

For each metric on the dashboard:

| Metric | Definition | Data source | Owner | Refresh | Acceptable lag |
|---|---|---|---|---|---|
| [name] | [business definition] | [table/pipeline] | [team] | [cadence] | [hours/days] |

### 3. Filtering and interaction requirements

- What filters must be available? (date range, segment, geography)
- Should filters affect all charts or specific ones?
- Are drill-down views needed? If so, which charts?
- Export or download needed?

### 4. Alerting requirements

- Which metrics need alerts?
- Alert thresholds and conditions
- Alert recipients and channels (email, Slack)

### 5. Data and governance

- What tables / data sources feed this dashboard?
- What is the data freshness requirement?
- Does the dashboard contain PII or sensitive financial data? If yes, who has access?
- Is row-level security needed (e.g., each regional manager sees only their region)?

---

## Sign-off checklist before build

- [ ] Primary question confirmed with the requester in writing
- [ ] All metrics have a written definition and a designated owner
- [ ] Data sources are confirmed accessible with appropriate permissions
- [ ] Refresh cadence and acceptable lag agreed
- [ ] Stakeholder confirmed they will use it (don't build dashboards that no one will open)
- [ ] Existing dashboards checked — does this already exist?

---

## Iteration and maintenance

**Version 1 must be usable, not complete.** Build for the primary question with 2–3 charts. Get feedback before adding more.

**Deprecate proactively.** After 90 days without a view, contact the owner to confirm it is still needed. Dashboard sprawl is a real maintenance burden.

**Ownership is required.** A dashboard without an owner becomes stale and untrustworthy. Every dashboard must have a named owner who is accountable for accuracy.
