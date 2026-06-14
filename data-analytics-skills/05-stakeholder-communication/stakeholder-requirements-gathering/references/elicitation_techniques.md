# Elicitation Techniques — Resolving Ambiguity in Analysis Requests

Quick reference for common ambiguous situations in NYC DOT analysis requests.
Each technique includes the exact question to ask.

---

## Technique 1: The Range Test

**Use when:** The requester isn't sure what "good" looks like or what threshold matters.

**Ask:** "What would you do if the answer is 70%? What about 80%? What about 90%?"

If all three produce the same action: the exact number doesn't matter — report directionally.
If 70% vs. 80% produces different actions: precision matters; confirm the decision threshold before scoping.

**NYC DOT example:**
Requester asks: "What's our ramp completion rate?"
→ "If it's 74%, does that change anything vs. if it's 79%?" (The 80% ADA target threshold matters here — confirm whether they need to know if they're above or below it, or the exact rate.)

---

## Technique 2: The Newspaper Test

**Use when:** The requester seems to want validation rather than analysis; risk of cherry-picking.

**Ask:** "If I found that [the thing you want to show] is not actually true, would you still want me to include that in the output?"

If "no": flag that the analysis needs to be objective; agree on the question before starting.
If "yes": proceed normally.

---

## Technique 3: The Decision Reversal

**Use when:** The requester hasn't articulated what action follows from the finding.

**Ask:** "Suppose the analysis shows [X]. What do you do next? Now suppose it shows [opposite of X] — what do you do then?"

If the action is identical: the analysis may not be needed; redirect to what would actually change behavior.
If the actions differ: document both as the success criteria.

---

## Technique 4: The Metric Definition Lock

**Use when:** The request involves a metric that could be defined multiple ways.

**Ask:** "When you say 'violation closure rate,' do you mean:
(a) share of all violations ever opened that are now closed,
(b) share of violations opened in [period] that were closed within [SLA],
(c) share of violations that were open at the start of [period] that are now closed,
or something else?"

**Common ambiguous metrics in NYC DOT context:**

| Metric | Common ambiguities |
|---|---|
| Ramp completion rate | Denominator: total ramps ever, or ramps in current program? Includes partial completions? |
| Violation closure rate | Open-at-start vs. opened-in-period; within-SLA vs. ever-closed |
| Data quality score | Which dataset? Which version? Which quality dimensions included? |
| SLA compliance | Per record, or per dataset? Which SLA tier (HIGH/MED/LOW)? |
| Inspection backlog | Active status only? Or all open regardless of age? |
| Borough performance | Per capita (population) or absolute count? Or rate vs. baseline? |

---

## Technique 5: The Constraint Surface

**Use when:** The requester's deadline or scope seems inconsistent with the data reality.

**Ask:** "Just to calibrate — the violations dataset has ~312K rows. A full borough-level analysis takes about [X hours]. Given your [date] deadline, would a 10K-row sample be accurate enough, or do you need the full dataset?"

Surface these constraints proactively:
- Full dataset pull requires `SOCRATA_APP_TOKEN` (>2K rows)
- Spatial joins on 11.5M `street_construction_inspections` rows take minutes, not seconds
- `ramp_locations` is stale since 2021 — using it for current state will mislead

---

## Technique 6: The Prior Work Check

**Use when:** The request sounds like something that may have been done before.

**Ask:** "Has anyone looked at this before? Is there a previous report or dashboard we should align with — or is this a fresh look?"

If prior analysis exists: confirm whether to update it or start fresh; avoid inadvertently contradicting a prior number without explanation.

---

## Technique 7: The Stakeholder Map

**Use when:** Multiple people are named in the request, or you suspect competing priorities.

**Ask:** "Besides you, who else will see this output? Is there anyone who might interpret the question differently or need a different level of detail?"

Document any conflicting definitions or priorities before starting. Do not produce one analysis that tries to serve incompatible audiences — propose separate outputs or a layered document.
