# Analysis Brief

*A concise one-page scope document. Derived from the requirements doc after stakeholder sign-off. This is the working reference for the analyst during the project.*

---

**Project:** [name]  
**Analyst:** [name]  
**Requestor:** [name and team]  
**Approved:** [YYYY-MM-DD]  
**Delivery date:** [YYYY-MM-DD]

---

## The Question

> [The business question in one sentence — copied from the approved requirements doc]

---

## What "Done" Looks Like

1. [Success criterion 1]
2. [Success criterion 2]
3. [Success criterion 3]

---

## Scope

| In scope | Out of scope |
|---|---|
| [e.g. Enterprise and Mid-Market tiers] | [e.g. SMB tier — insufficient data volume] |
| [e.g. Jan 2024 – Mar 2024] | [e.g. historical periods before Jan 2024] |

---

## Data Plan

| Step | Data needed | Source | Status |
|---|---|---|---|
| 1 | [e.g. Customer login events] | [prod.events] | Confirmed |
| 2 | [e.g. Subscription data] | [prod.subscriptions] | Confirmed |
| 3 | [e.g. CRM segment tags] | [Salesforce] | Access requested |

---

## Approach (high level)

1. [Step 1 — e.g. Pull 90-day activity data for all accounts]
2. [Step 2 — e.g. Compute engagement score per account]
3. [Step 3 — e.g. Segment by risk tier]
4. [Step 4 — e.g. Produce ranked list with recommended actions]

---

## Output Format

**Deliverable:** [e.g. CSV + one-page summary]  
**Audience:** [e.g. CS team leads]  
**Delivery channel:** [e.g. Slack + Confluence]

---

## Constraints and Risks

- [e.g. Salesforce access not yet confirmed — blocks step 3; fallback is to use CRM data from DW export]
- [e.g. Timeline is tight — if data pull takes > 1 day, delivery date will slip]

---

## Not In Scope (explicitly)

- [Item 1]
- [Item 2]

*Any additions to scope require requestor approval and a revised delivery date.*
