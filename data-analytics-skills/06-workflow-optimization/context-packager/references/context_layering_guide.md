# Context Layering Guide

How to structure context for AI-assisted analysis so the model has exactly what it needs — no more, no less.

---

## The Six Context Layers

Listed in priority order (highest to lowest — trim from the bottom when over budget):

### Layer 1: Task (always include)
**What:** What you need the AI to do. One clear ask.  
**Format:** 2–5 sentences: goal, output format, key constraints.  
**Size:** < 200 tokens  
**Never trim this.** A missing task description produces vague outputs.

### Layer 2: Business Context
**What:** The business situation, metric definitions, and domain knowledge the AI needs.  
**Includes:** Company/product description, how metrics are defined, known business rules.  
**Size:** 300–800 tokens  
**Trim by:** Removing background that isn't directly relevant to this specific task.

### Layer 3: Data Schema
**What:** Table names, column names, types, and relationships relevant to the task.  
**Includes:** CREATE TABLE statements, dbt model descriptions, data dictionary excerpts.  
**Size:** 200–1000 tokens (depends on complexity)  
**Trim by:** Including only tables and columns referenced in the task.

### Layer 4: Prior Findings
**What:** Results from previous analyses that the AI should be aware of or build on.  
**Includes:** Key metrics from past reports, hypotheses already tested, known patterns.  
**Size:** 200–600 tokens  
**Trim by:** Summarising rather than pasting full reports; include only findings directly relevant to the task.

### Layer 5: Constraints
**What:** Boundaries the analysis must respect.  
**Includes:** Time period limits, excluded segments, approved methods, style preferences.  
**Size:** < 200 tokens  
**Trim by:** Removing constraints that apply to future iterations, not this task.

### Layer 6: Output Format
**What:** Instructions on how to structure the response.  
**Includes:** Desired format (table, narrative, SQL), length, terminology preferences.  
**Size:** < 150 tokens  
**Trim by:** Removing format instructions already implied by the task.

---

## Token Budget Allocation

For a 100K token budget:

| Layer | Allocation | Notes |
|---|---|---|
| Task | 1–2% | ~200 tokens |
| Business context | 5–10% | ~800 tokens |
| Data schema | 5–15% | ~1,500 tokens for large schemas |
| Prior findings | 3–8% | ~600 tokens |
| Constraints | 1–2% | ~150 tokens |
| Output format | 1% | ~100 tokens |
| **Reserved for response** | **~65%** | Leave room for the model to respond |

Rule of thumb: spend no more than 30–35% of the context window on input; leave the rest for the response.

---

## Trimming Priority

When over budget, trim in this order:

1. **Format** — usually redundant if task is well-specified
2. **Constraints** — trim to only must-have restrictions
3. **Prior findings** — summarise to key numbers; cut narrative
4. **Schema** — remove tables/columns not needed for this task
5. **Business context** — reduce to the single most relevant paragraph
6. **Task** — shorten wording, never remove

---

## Quality Checklist

Before sending a context bundle:

- [ ] The task is stated in the first 500 characters
- [ ] Every table mentioned in the task is in the schema layer
- [ ] Metric definitions match what the business uses (not Wikipedia's definitions)
- [ ] No contradictions between layers (e.g. schema says `user_id`; task says `customer_id`)
- [ ] Token count is under 35% of context window
- [ ] Output format instructions are included if a specific format is needed
