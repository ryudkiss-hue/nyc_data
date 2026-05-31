# Audience Depth Guide for Analysis Documentation

## Calibrating documentation depth

The same analysis can be documented at three different levels depending on who will read it. Over-documenting wastes time; under-documenting creates ambiguity that surfaces as repeated questions.

---

## Level 1 — Executive / Stakeholder

**Who reads this:** VP, Director, non-technical business owner.

**What they need:**
- The answer, not the method
- Confidence that the analysis is trustworthy
- What decision this enables, and what it does not

**Format guidance:**
- Max 1 page (or equivalent)
- Lead with the key finding, follow with supporting evidence
- One chart maximum; no SQL, no technical terminology
- Explicit recommendation or next step

**Avoid:**
- Methodological detail ("we used a z-test at alpha=0.05")
- Data caveats beyond the most critical one
- Intermediate steps or alternative approaches considered

---

## Level 2 — Analytical Peer / Manager

**Who reads this:** Senior analyst, analytics manager, product manager with data literacy.

**What they need:**
- Methodology at a level that lets them evaluate whether it is sound
- Key assumptions and their confidence level
- How to reproduce or extend the analysis

**Format guidance:**
- 2–4 pages
- Context → Approach → Findings → Caveats → Next steps
- Include the main SQL or code references (not the full script)
- Explicit assumption log with confidence ratings

**Avoid:**
- Full code dumps inline
- Raw table dumps; use summarised outputs
- Over-explaining standard techniques

---

## Level 3 — Future Analyst / Handover

**Who reads this:** Someone who will extend, debug, or re-run this analysis in 6+ months.

**What they need:**
- Complete reproducibility: where data lives, how to run the code, expected outputs
- All design decisions and alternatives considered
- Known issues and workarounds

**Format guidance:**
- No page limit
- Every query, script, and file path referenced
- Step-by-step instructions to reproduce
- Change log if the analysis is run repeatedly

**Avoid:**
- Assuming context that is obvious now but won't be later
- Skipping the "why" behind non-obvious decisions

---

## Choosing the right level

| Trigger | Level |
|---|---|
| One-time ad-hoc for a meeting | 1 |
| Recurring report or dashboard | 2 |
| Strategic decision with board visibility | 1 + summary of 2 |
| Handover to another team | 3 |
| Reusable analysis template | 3 |
| Internal methodology reference | 2–3 |

---

## Reusable sections across levels

These sections appear in all levels, just at different depths:

- **Question** — what business question this answers
- **Data sources** — tables, systems, date ranges used
- **Key finding** — the headline answer in one sentence
- **Caveats** — what could be wrong or missing
- **Next steps** — what action follows from this
