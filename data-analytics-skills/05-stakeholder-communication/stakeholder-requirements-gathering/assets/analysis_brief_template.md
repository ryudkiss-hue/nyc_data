# Scope Confirmation Document — [Title]

**Version:** 1.0
**Analyst:** [Name]
**Requestor:** [Name, role]
**Date:** [YYYY-MM-DD]
**Status:** Pending sign-off / Approved / In progress

---

## Business Question

> [One sentence: the single question this analysis answers.]

**Decision context:** Informs [specific decision] made by [Name / role] by [date].

---

## Scope: What We Will Deliver

| Deliverable | Description | Format | Audience |
|---|---|---|---|
| Borough completion table | Ramp completion rate + CI per borough | Excel + Slide | Commissioner |
| Summary memo | Key findings, 1 page | PDF | Deputy Commissioner |

**Not in scope:**
- Root cause analysis of borough differences
- Individual inspection record detail

---

## Data Sources

| Dataset | Key | Fourfour | Rows | Filters applied |
|---|---|---|---|---|
| | | | | |

Freshness: stale datasets flagged before delivery per SLA thresholds (HIGH=14d, MED=30d, LOW=60d).

---

## Agreed Metric Definitions

| Metric | Definition agreed with requestor |
|---|---|
| Ramp completion rate | Share of ramps in ramp_progress (e7gc-ub6z) with status=complete, by borough |
| Violation closure rate | Share of violations opened in [period] closed within SLA threshold days |
| Data quality score | 0-100 composite: 35% completeness, 25% validity, 25% consistency, 15% freshness |

---

## Timeline

| Milestone | Target date | Owner |
|---|---|---|
| Sign-off | | Requestor |
| Data pull | | Analyst |
| Draft delivery | | Analyst |
| Requestor review | | Requestor |
| Final delivery | | Analyst |

---

## Known Risks

| Risk | Mitigation |
|---|---|
| ramp_locations stale since 2021 | Use ramp_progress (e7gc-ub6z) instead |
| Staten Island sample may be small | Report n; use Wilson Score CI for n < 1,000 |
| Full corpus requires SOCRATA_APP_TOKEN | Confirm token availability before pull |
| capital_blocks is empty | Use capital_intersections (97nd-ff3i) as fallback |

---

## Sign-Off

Requestor confirms: (1) business question matches need, (2) scope inclusions and exclusions accepted, (3) deliverable format fits intended audience, (4) timeline is workable.

**Requestor:** ______________________  **Date:** ______________

**Analyst:** ______________________  **Date:** ______________
