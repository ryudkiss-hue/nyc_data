# Scoping Framework for Analysis

A structured approach to decomposing a business question into a workable analysis plan.

---

## Phase 1: Clarify the Business Question

Before decomposing, verify the question is specific enough to act on.

A well-formed business question has:
- A **subject** (who or what is being measured — customers, products, events)
- A **metric** (what we're measuring — churn rate, revenue, conversion)
- A **context** (when, where, which segment)
- A **decision** it will inform (what will change based on the answer)

**Test:** If the answer could be "it depends" without any further context, the question isn't specific enough.

Bad: "Why is revenue down?"  
Better: "Why did enterprise MRR decline by 8% between January and March 2024 relative to the same period last year?"

---

## Phase 2: Decompose into Sub-Questions

Break the main question into independent, answerable sub-questions.

**Decomposition patterns:**

**Drill-down:** Move from aggregate to segment
- Main: Is churn increasing?
- Sub-questions: Is it in enterprise or SMB? Newer or older cohorts? A specific geography?

**Time-comparison:** What changed and when?
- Sub-questions: What was the trend before? When did it change? What else changed at the same time?

**Causal chain:** What could explain the outcome?
- Sub-questions: Are there fewer new customers? Are existing ones churning faster? Are expansions declining?

**Component decomposition:** What does the metric consist of?
- Revenue = Volume × Price → check both separately

**Rule:** Each sub-question should be answerable with a single query, calculation, or model pass.

---

## Phase 3: Map Data Requirements

For each sub-question, identify:

| Sub-question | Tables needed | Joins required | Filters | Known issues |
|---|---|---|---|---|
| [question] | [table list] | [join type] | [date range, segment] | [data gap, nulls] |

**Availability check:**
- Confirmed available: proceed
- Likely available — check: flag as dependency before starting
- Unknown: block until resolved

---

## Phase 4: Sequence the Work

Order sub-questions to minimise rework:

1. **Data exploration first** — run a quick scan before committing to the full approach; bad data discovered early saves time
2. **Blockers before detail** — resolve data availability questions before investing in detailed analysis
3. **High-certainty steps before uncertain ones** — build on confirmed results; pivot if an early step fails
4. **Parallel where possible** — independent sub-questions can run in parallel if two analysts are available

---

## Phase 5: Define Scope Boundaries

Explicitly write down what is out of scope and why. This prevents mid-project scope creep.

| Out of scope | Reason |
|---|---|
| [Excluded segment / time period] | [Data not available / outside the decision window / separate project] |

**Scope change rule:** Any addition to scope requires an explicit conversation with the requestor about timeline impact.

---

## Common Decomposition Mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Sub-questions that answer each other (redundant) | Wasted work | Merge or drop the duplicate |
| Sub-questions that can't be answered with available data | Blocked analysis | Resolve data availability first |
| Too many sub-questions for the deadline | Partial delivery | Apply MoSCoW — identify the 2–3 that matter most |
| Sub-questions that assume the answer | Confirmation bias | Make each sub-question genuinely testable |
