# Executive Writing Style Guide
## NYC DOT Sidewalk Inspection & Management — Leadership Briefings

---

## Core Principle: Answer First

The single most important rule in executive writing: state the conclusion before the evidence.

Executives make dozens of decisions per day. They do not read documents to learn — they read to confirm or change a decision. Give them the conclusion immediately, then support it.

### Wrong (inverted pyramid)

> We reviewed inspection records from all five boroughs over the past 90 days. We compared completion rates against the Q2 target and adjusted for seasonal variation. After reviewing these trends, we identified that Brooklyn showed the largest deviation. Our analysis indicates that Brooklyn's ramp completion rate is now 62%, which is below the 75% target.

### Right (pyramid principle)

> Brooklyn's ramp completion rate has fallen to 62% — 13 percentage points below target and the largest single-quarter decline in three years. Without intervention, the borough will miss its fiscal-year target. We recommend reallocating 15 inspector-weeks to Brooklyn immediately.

---

## Audience Calibration by Role

### DOT Commissioner / Deputy Commissioner

- **What they need:** Program-level status, risk flags, resource decisions
- **Time budget:** 3 minutes; often reading on a phone or in a car
- **Language:** No internal acronyms (SIM is fine; fourfour is not). Borough names, not codes.
- **Metrics they track:** Citywide completion rate, ADA grievance volume, 311 complaint trends, budget variance
- **Avoid:** Data quality scores, schema drift details, DuckDB or API terminology

### Borough Operations Manager

- **What they need:** Borough-specific status, crew utilisation, backlog by type
- **Time budget:** 5–10 minutes; usually at a desk
- **Language:** Moderate — can reference inspection types, borough codes (MN, BK, etc.), SLA tiers
- **Metrics they track:** Inspections completed vs. scheduled, open violations, ramp backlog count
- **Avoid:** Statistical methods details (just give the result and CI); governance audit details

### City Council Member / Committee Staff

- **What they need:** District-level outcomes, ADA commitments, accountability
- **Time budget:** 3 minutes; often in a meeting context
- **Language:** Plain language only — no DOT jargon, no acronyms without spell-out, no "SIM"
- **Metrics they track:** How many ramps completed in my district, open violations near schools/subways
- **Avoid:** Internal program structure, data quality, technical methodology

### DOT Data / Analytics Team

- **What they need:** Data health, SLA compliance, pipeline issues, quality trend
- **Time budget:** 10 minutes; deep technical reader
- **Language:** Full technical vocabulary — dataset keys, fourfours, DuckDB, quality score dimensions
- **Metrics they track:** Quality score (0–100), SLA breach rate, schema drift events, cache hit rate
- **Avoid:** Non-technical framing that obscures technical precision

---

## The Pyramid Principle — Applied to NYC DOT

Apply at three levels: document, section, paragraph.

### Document level

1. **Title:** States the topic
2. **Bottom line (first paragraph):** States the key finding and recommendation
3. **Key findings table:** Top 3–5 findings, quantified
4. **Recommendations:** Specific, owned, time-bound
5. **Decision block:** Explicit ask with owner, deadline, investment, risk if no action
6. **What was excluded:** Manages expectations

### Section level

First sentence of each section states the section's conclusion. The rest provides evidence.

- Wrong: "In Q2, we saw a variety of trends across the boroughs..."
- Right: "Brooklyn is the borough most at risk: completion rate at 62%, vs. a 75% target."

### Paragraph level

Every paragraph = one point. Topic sentence states it. Supporting sentences prove it.

---

## Quantification Rules

Every insight must include a number. Vague language is not acceptable in executive summaries.

| Vague (not acceptable) | Specific (required) |
|-----------------------|---------------------|
| "Significant decline" | "12 percentage point decline, from 74% to 62%" |
| "Notable improvement" | "Completion rate increased from 58% to 74%, a 16 pp gain" |
| "Several boroughs at risk" | "Three of five boroughs (BK, QN, BX) are below the 75% target" |
| "High violation rate" | "Brooklyn violation rate is 23% above the citywide average" |
| "Data quality issues" | "Inspection dataset quality score: 62/100 — 15 points below the 77/100 benchmark" |
| "Upcoming SLA breach" | "Violations dataset last updated 11 days ago; HIGH-tier SLA threshold is 14 days" |

---

## Recommendations — Format Requirements

Every recommendation must specify all four elements:

1. **What to do** (specific action, not "improve" or "address")
2. **Who is responsible** (named role, not "the team")
3. **Expected outcome** (quantified where possible)
4. **By when** (specific date, not "soon" or "ASAP")

### Wrong recommendation

> "More resources should be allocated to address the Brooklyn backlog."

### Right recommendation

> "The Brooklyn Borough Manager should reassign 15 inspector-weeks from non-priority street inspections to ramp-only orders, beginning July 7, 2026. This is projected to clear 120 backlogged ramp orders and restore the completion rate to 72% by Q3 end."

---

## The Decision Block

Every executive summary must close with an explicit decision block. Executives who receive ambiguous asks do not act.

### Required elements

- **Decision required:** The specific choice or approval needed
- **Decision owner:** The person who must decide (not "leadership")
- **Deadline:** The date by which a decision is needed and why
- **Investment required:** Budget, headcount, approval authority, or other resource
- **Expected return:** Quantified outcome if the action is taken
- **Risk if no action:** Consequence in concrete terms

### Example decision block

| Element | Detail |
|---------|--------|
| Decision required | Approve reallocation of 15 inspector-weeks from Queens general inspections to Brooklyn ramp orders |
| Decision owner | Deputy Commissioner, Field Operations |
| Deadline | July 7, 2026 — to allow schedule adjustment before the July 14 inspection cycle |
| Investment required | Overtime budget: ~$42K (15 inspector-weeks × $2,800/week OT rate) |
| Expected return | Restores Brooklyn completion rate from 62% to 72% by September 30 |
| Risk if no action | Brooklyn misses fiscal-year target for the first time in 5 years; estimated 8,400 residents affected |

---

## Common Executive Summary Mistakes

| Mistake | Fix |
|---------|-----|
| Burying the key finding | Lead with it — first sentence of the document |
| More than 5 insights | Cut to the 3–5 that directly affect the decision |
| Vague recommendations | Add owner, action, date, outcome to every recommendation |
| No decision block | Always end with an explicit ask |
| Jargon for wrong audience | Check audience profile; remove all internal acronyms for leadership and council |
| Missing confidence note | State n= and whether CI was computed for every quantitative claim |
| Appendix in the body | Put supporting detail in a separate linked document |
