# Learning Capture Guide

How to decide which learnings from a retrospective are worth preserving — and where to put them.

---

## Is This Learning Worth Capturing?

Ask: "Would this learning change how I or a teammate approaches a future project?"

| Yes, capture it if... | Skip it if... |
|---|---|
| It would have saved > 30 minutes if known earlier | It's obvious in hindsight to anyone with context |
| It reveals a pattern (this has happened before) | It was a one-off caused by exceptional circumstances |
| It changes an assumption baked into a template or process | The project context no longer applies |
| It reveals a data quality issue or system behaviour that will recur | The system or process that caused it has already been fixed |

---

## Where to Put Learnings

| Learning type | Where it goes |
|---|---|
| Process improvement | Update the relevant skill's SKILL.md or checklist |
| Template gap or deficiency | Update the relevant asset template |
| Data quality pattern | Add to the relevant dataset's quality notes or data catalog entry |
| Estimation insight | Update `effort_estimation.md` |
| Stakeholder communication pattern | Add to `stakeholder_personas.md` or `translation_pattern_library.md` |
| One-time note for the team | Post to team Slack / wiki; no permanent file needed |
| Reusable analysis pattern | Create a new reference doc or script in the relevant skill folder |

---

## Learning Entry Format

When writing a learning entry for permanent capture:

```
## [Short title]

**Context:** [What project or situation revealed this]
**What happened:** [Brief description of the problem or insight]
**Learning:** [The transferable rule or principle]
**Where applied:** [Which template / doc / process was updated]
**Date:** [YYYY-MM-DD]
```

---

## Anti-Patterns in Learning Capture

**Capturing everything** — a learnings log with 50 entries is never read. Be selective; capture the 2–3 things that would have saved the most time.

**Vague entries** — "better planning" is not a learning. "Add a data availability check to the analysis plan before committing to a deadline" is.

**Capturing without acting** — if the learning implies a process change, make the change immediately. Don't log learnings and then forget to update the templates.

**Individual learning only** — learnings that stay in one person's head aren't durable. The point is to externalise them so teammates benefit.

---

## Quarterly Learning Review

Every quarter, review the learnings log and ask:
- Which learnings have we actually applied?
- Which learnings turned out to be wrong or situational?
- Are there patterns across multiple learnings that suggest a bigger process change?
- Which learnings should be promoted into a skill reference or team norm?
