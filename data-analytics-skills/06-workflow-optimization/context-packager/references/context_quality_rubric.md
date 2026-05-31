# Context Quality Rubric

Score a context bundle out of 10 before sending it for AI-assisted analysis. A score below 7 indicates the bundle needs work before use.

---

## Scoring Dimensions

### 1. Completeness (0–3 points)

Does the bundle contain everything the AI needs to answer the question?

| Score | Criteria |
|---|---|
| 3 | Task, relevant schema, metric definitions, and any necessary prior context are all present |
| 2 | One important element is missing but the task is still largely answerable |
| 1 | Multiple elements are missing; AI will need to ask clarifying questions |
| 0 | Task only, no supporting context |

### 2. Clarity (0–3 points)

Is the task unambiguous? Could a capable analyst follow these instructions without asking questions?

| Score | Criteria |
|---|---|
| 3 | Task is specific, measurable, and scoped; success criteria are clear |
| 2 | Task is mostly clear with 1–2 ambiguities that probably won't matter |
| 1 | Task is vague; multiple reasonable interpretations exist |
| 0 | Task is absent or entirely unclear |

### 3. Relevance (0–2 points)

Is the context tightly scoped to what's needed, without noise?

| Score | Criteria |
|---|---|
| 2 | Every section is directly relevant; no filler |
| 1 | Some content is tangentially related; a bit bloated |
| 0 | Large sections have no relevance to the current task |

### 4. Token Efficiency (0–2 points)

Is the bundle within a sensible token budget?

| Score | Criteria |
|---|---|
| 2 | Under 30% of context window |
| 1 | 30–50% of context window |
| 0 | Over 50% of context window (leaves little room for response) |

---

## Total Score Interpretation

| Score | Interpretation |
|---|---|
| 9–10 | Excellent — send as-is |
| 7–8 | Good — minor improvements possible but won't materially affect output |
| 5–6 | Adequate — expect follow-up questions or incomplete responses |
| 3–4 | Poor — invest 15 minutes improving before sending |
| 0–2 | Not ready — significant gaps that will produce low-quality output |

---

## Quick-Fix Checklist

If your score is below 7, apply these fixes in order:

1. **Add a missing task statement** — if the task layer is absent, add it first
2. **Add metric definitions** — if the task mentions a metric, define it in business context
3. **Add relevant table definitions** — if the task mentions a table, put the schema in
4. **Remove irrelevant sections** — trim anything that isn't referenced in the task
5. **Rewrite vague task language** — replace "look into X" with "identify the top 3 causes of X in Y segment between dates A and B"
