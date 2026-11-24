# Intake Interview Guide — NYC DOT Analysis Requests

Use this guide when receiving a new analysis request. Run through these questions
before pulling any data. A 15-minute intake call prevents days of rework.

---

## Opening (set expectations)

"Before I start pulling data, I want to make sure I'm answering the right question.
Can I ask you a few quick questions? It'll take about 10–15 minutes and will help
me get you something useful the first time."

---

## Section 1: The Business Question

**1a. What is the decision this analysis will inform?**
(If they say "I just want to know the numbers," push for: "What will you do differently based on what you learn?")

Target answers:
- "We're deciding whether to add inspectors to [borough]"
- "We need to respond to a City Council inquiry about [topic]"
- "We want to know if the new routing software is working"

Red flag: "I'm not sure — just curious about the data."
→ Probe harder or schedule a follow-up with the decision-maker.

**1b. Who will act on this finding?**
(Name the person or role who will make the decision.)

**1c. What would you do if the answer is [X]? What would you do if it's [Y]?**
(Forces clarity on what range of outcomes matters. If both X and Y produce the same action, the analysis may not be needed.)

---

## Section 2: Scope

**2a. Which boroughs should be included?**
- [ ] All 5 (MN, BX, BK, QN, SI)
- [ ] Specific: ___________
- [ ] Citywide aggregate only

**2b. What time period?**
- Specific date range: ________________
- Rolling window: last N days / weeks / months
- Fiscal year: FY ____

**2c. Which dataset(s) are most relevant?**
(Offer options if they don't know)
- Inspections (dntt-gqwq, ~398K rows)
- Violations (6kbp-uz6m, ~312K rows)
- Ramp progress (e7gc-ub6z, ~187K rows)
- Other: ___________

**2d. Are there records to exclude?**
(E.g. "only active violations, not closed ones" / "exclude tree damage records")

---

## Section 3: Output

**3a. What format do you need the output in?**
- [ ] Data table / spreadsheet
- [ ] Chart or visualization
- [ ] Map
- [ ] Slide(s)
- [ ] Written summary / memo
- [ ] PDF report
- [ ] Dashboard update

**3b. Who is the final audience?**
- [ ] Field inspectors / operations team (technical OK)
- [ ] Operations manager / program manager (semi-technical)
- [ ] Commissioner / Deputy Commissioner (executive — plain language only)
- [ ] City Council / elected official (public-facing — plain language only)
- [ ] Press / media (plain language; NYC Open Data citation required)
- [ ] Public / residents (plain language; no jargon)

**3c. What does "done" look like for you?**
("If I send you [X] by [date], would that answer your question fully?")

---

## Section 4: Constraints

**4a. What is the deadline?**
- Hard deadline (external meeting, Council hearing, press inquiry): ___________
- Soft target (internal planning): ___________

**4b. Are there known data limitations I should flag?**
(Share relevant ones proactively:)
- `ramp_locations` is stale since 2021 → use `ramp_progress` instead
- `capital_blocks` is empty
- `permit_stipulations` returns API errors

**4c. Has this question been analyzed before?**
(Avoid duplicating work; find the prior analysis if it exists.)

**4d. Are there other stakeholders who have a view on this question?**
(Identify anyone whose definition of "ramp completion" or "violation closure" might differ from the requester's.)

---

## Section 5: Success Criteria

**5a. How will you evaluate whether the analysis was useful?**

**5b. What would make you share this with your team / leadership?**

**5c. Is there a "close enough" answer that still works, or does precision matter?**
(E.g. "Is ±5 pp accuracy OK, or do you need exact figures?")

---

## Closing

"Based on what you've told me, here's what I'm going to produce: [restate scope in 2–3 sentences].
I'll send you a brief confirmation before I start work. Does that match what you need?"

→ Follow up with `assets/analysis_brief_template.md` within 24 hours.

---

## Red Flags That Require Escalation

- Requester can't describe the decision the analysis will inform
- Multiple stakeholders have conflicting definitions of the key metric
- Deadline is < 24 hours with n > 50K rows needed
- Request involves comparing data across years with known schema changes
- Requester asks to "make the numbers look better" — decline; flag to manager
