# Decision-Maker Framework — Classifying Analysis Requests by Decision Type

Use this framework during intake to set the appropriate rigor level, timeline, and output format.

---

## Decision Type Classification

### Type 1: Exploratory
**Definition:** No decision is imminent. The goal is to understand a situation, surface patterns, or identify where to look next.

**Characteristics:**
- "We just want to understand what's happening with [topic]"
- No named decision-maker or deadline
- Output will inform future scoping, not direct action

**Appropriate rigor:**
- Quick, directional analysis is acceptable
- Wilson Score CIs are nice-to-have, not required
- Draft-quality output OK; annotate as "preliminary"
- Timeframe: hours to 1–2 days

**NYC DOT examples:**
- "Give me a sense of ramp completion trends across boroughs"
- "What does our violation data look like this month?"
- "Are there any patterns in tree damage complaints?"

---

### Type 2: Confirmatory
**Definition:** A hypothesis or decision is partially formed. The analysis will confirm or refute a belief before action is taken.

**Characteristics:**
- Stakeholder already has a direction in mind
- Analysis may validate or push back on that direction
- Output will be shared with leadership or used in a formal recommendation

**Appropriate rigor:**
- Full QA checklist required
- CIs required for all rates (Wilson Score for n < 1,000)
- Methodology documented for potential scrutiny
- Timeframe: 2–5 days depending on data complexity

**NYC DOT examples:**
- "We think Brooklyn is outperforming the Bronx — can you confirm that?"
- "The Commissioner wants to know if we're on track to hit 80% ramp completion by Q4"
- "City Council asked if violations in [district] are being resolved within SLA"

---

### Type 3: Operational
**Definition:** The analysis directly informs a recurring operational workflow. Accuracy and freshness matter more than depth.

**Characteristics:**
- Analysis runs regularly (daily, weekly, monthly)
- Output goes directly into a field or management process
- Errors have immediate operational consequences

**Appropriate rigor:**
- Automated QA checks on every run
- Strict freshness requirements (within HIGH SLA = 14 days)
- Alerts on anomalies before output is consumed
- Documentation for handoff (another analyst may inherit this)
- Timeframe: must meet the operational cadence

**NYC DOT examples:**
- Weekly violation backlog report for borough superintendents
- Daily data freshness dashboard for data team
- Monthly ramp completion report for Commissioner's office
- Nightly SLA breach alerts via `AlertManager`

---

## Matching Decision Type to Analysis Skill

| Decision type | Primary skills | Secondary skills |
|---|---|---|
| Exploratory | programmatic-eda, root-cause-investigation | data-quality-audit, time-series-analysis |
| Confirmatory | ab-test-analysis, cohort-analysis | analysis-qa-checklist, methodology-explainer |
| Operational | metric-reconciliation, data-quality-audit | analysis-qa-checklist, semantic-model-builder |

---

## Stakeholder Persona × Decision Type Matrix

| Stakeholder | Typical decision type | Key priority | Output format |
|---|---|---|---|
| DOT Commissioner | Confirmatory, Operational | Strategic direction, accountability | 1-page brief + chart |
| Deputy Commissioner | Confirmatory | Program performance, risk | Summary table + narrative |
| Borough Superintendent | Operational | Field resource allocation | Dashboard / weekly report |
| Operations Manager | Operational | Daily workflow | Table + alert |
| Program Manager | Confirmatory, Exploratory | Planning, trend spotting | Slide deck + appendix |
| Field Inspector | Operational | What to do next | Simple list / route |
| City Council member | Confirmatory | Constituent accountability | 1-page memo + map |
| Borough President | Confirmatory | Equity, resource allocation | Borough comparison table |
| Press / Media | Exploratory | Story angle | Simple number + context |
| Public | Exploratory | Transparency | Plain language summary |

---

## Rigor Escalation Triggers

Upgrade rigor level (add CI, full QA, peer review) when:
- Analysis will be cited in a public document, press release, or Council testimony
- A budget or staffing decision depends on the finding
- The finding contradicts what stakeholders expect (more likely to be challenged)
- The dataset has known quality issues (see CLAUDE.md ⚠️ section)
- Sample size is small (n < 200 for any subgroup)
