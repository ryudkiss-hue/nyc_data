# Analysis Requirements — [Request Name]

**Intake date:** [YYYY-MM-DD]
**Analyst:** [Name]
**Requestor:** [Name, role, team]
**Decision-maker (if different):** [Name, role]
**Decision type:** Exploratory / Confirmatory / Operational

---

## The Business Question

[State in one sentence what question the analysis will answer. This is the analyst's interpretation — confirm with requestor.]

**Decision this informs:**
[What action or decision depends on the outcome of this analysis?]

**If the answer is X, the decision is:**
[...]

**If the answer is Y, the decision is:**
[...]

---

## Scope

### Boroughs
- [ ] Manhattan (MN)
- [ ] Bronx (BX)
- [ ] Brooklyn (BK)
- [ ] Queens (QN)
- [ ] Staten Island (SI)
- [ ] Citywide aggregate only

### Time Period
- Start date: ________________
- End date: ________________
- Note: ________________

### Data Sources

| Dataset key | Fourfour | Confirmed available? | Known issues? |
|---|---|---|---|
| | | Yes / No | |
| | | Yes / No | |

### Inclusions / Exclusions
- Include only: [e.g. active violations, not closed]
- Exclude: [e.g. tree damage records, Staten Island pilot sites]

---

## Metric Definitions

| Metric | Definition agreed with requestor | Denominator | Time basis |
|---|---|---|---|
| | | | |
| | | | |

---

## Output Requirements

**Format:** Table / Chart / Map / Slides / Memo / Dashboard / PDF report

**Audience:** [Role(s) and technical level]

**Level of detail:** Summary / Borough breakdown / Inspection-district level / Record-level

**Confidence intervals required?** Yes / No
- If yes: method = Wilson Score (for n < 1,000) / Normal approximation
- Confidence level: 95% / 90%

**Success criteria (from requestor):**
[What would the requestor need to see to consider this analysis complete and useful?]

---

## Constraints

**Hard deadline:** [Date — e.g. City Council hearing, Commissioner briefing]
**Soft target:** [Internal planning date]

**Row limit / API token available?**
- [ ] `SOCRATA_APP_TOKEN` available (full corpus)
- [ ] Token unavailable — limit to 2,000 rows per dataset

**Compute / time budget:** [E.g. "quick turn — 4 hours max" vs. "full analysis — 3 days"]

---

## Open Questions / Ambiguities

| # | Question | Who resolves it | By when |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

---

## Sign-Off

**Requestor confirms this matches their need:**

Requestor signature / reply: ______________________

Date confirmed: ______________________

→ Proceed to `analysis_brief_template.md` for formal scope document.
