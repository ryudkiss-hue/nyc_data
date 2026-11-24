# Retrospective Frameworks Reference

Two frameworks for structured post-project reflection. Choose based on session type.

---

## Framework 1 — Start / Stop / Continue

Best for: team retrospectives, 30–60 minute sessions, recurring project types.

| Category | Question | Prompt for NYC DOT context |
|---|---|---|
| **Start** | What should we begin doing on future analyses? | Did we check all known dataset issues before starting? Did we run a quality score before drawing conclusions? Should we add a peer review step? |
| **Stop** | What wasted time or produced poor results? | Did we pull full-corpus when a 10K sample would have done? Did we use stale ramp_locations instead of ramp_progress? Did we skip Wilson CI for small boroughs? |
| **Continue** | What worked well and should be standard practice? | Did we decompose sub-questions before touching data? Did we confirm token access early? Did we include n= and data date in every table? |

Timebox: 10 min per category. Write everything; don't filter during brainstorm.

---

## Framework 2 — 4Ls (Liked / Lacked / Learned / Longed for)

Best for: individual retrospectives, post-mortems after a problematic project, onboarding debrief.

| L | Question | Example response |
|---|---|---|
| **Liked** | What was satisfying or worked well? | "Wilson CI caught that Staten Island n=23 was too small to report — we flagged it instead of presenting a misleading rate." |
| **Lacked** | What was missing or frustrating? | "No agreed definition of 'completion' — ramp_progress uses 3 different status values. Wasted 45 min reconciling." |
| **Learned** | What new knowledge did the project produce? | "street_permits borough codes use community board numbers, not MN/BX/BK/QN/SI. Document this." |
| **Longed for** | What would have made the project significantly better? | "A pre-built SOQL filter library for common SIM queries. Would save 20 min per analysis." |

---

## 5-Whys for Root Cause Analysis

Apply to any significant issue that delayed or degraded the analysis.

**Template:**
```
Issue: <state the observable problem>
Why 1: <first-level cause>
Why 2: <cause of the cause>
Why 3: <deeper cause>
Why 4: <systemic cause>
Why 5: <root cause — actionable>
Action: <specific fix that addresses the root cause>
```

**Worked example — "Violation trend numbers didn't match PM's spreadsheet":**
```
Issue: Our borough violation counts differed from PM's tracking sheet by 8–15%.
Why 1: We filtered on created_date; PM filters on inspection_date.
Why 2: No agreed date field definition existed for violation trend analysis.
Why 3: The column definitions in the dataset aren't self-documenting.
Why 4: No SIM-specific data dictionary was distributed at project kickoff.
Why 5: Kickoff template didn't include "agree on date field" as a required step.
Action: Add "confirm date field definition" to kickoff_doc_template.md as a mandatory line item.
```

---

## Categorizing learnings for reuse

Every learning should produce a concrete artifact. Assign each to one category:

| Category | What to create | Example |
|---|---|---|
| Template | Add or update a template file | Add "date field" row to kickoff_doc_template.md |
| Reference | Add a paragraph to a reference doc | Add borough code normalization note to scoping_framework.md |
| Checklist item | Add a line to qa_checklist | "Confirm n ≥ 30 before reporting a borough rate" |
| Team norm | Propose a team practice | "Always run `dataset health` before any analysis, even routine ones" |
| Skip | Learning is too project-specific to generalize | "PM prefers numbers in absolute counts, not percentages" → note in project file only |
