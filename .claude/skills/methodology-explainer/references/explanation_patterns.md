# Explanation Patterns — Choosing the Right Format by Audience

Use this reference to select the explanation pattern before writing a methodology section.

---

## Audience Tier Classification

| Tier | Who | Needs | Avoid |
|---|---|---|---|
| **Executive** | Commissioner, Borough President, Deputy Commissioner, City Council member | Bottom line first, decision implications, risk | Method names, formulas, p-values, model metrics |
| **Analyst** | Operations manager, program manager, senior inspector, DOT planner | Plain summary + option to dig deeper, enough to validate | Unnecessary hedging, over-simplification that loses precision |
| **Technical peer** | Data engineer, fellow analyst, Socrata team | Full method, assumptions, edge cases, reproducibility | Dumbed-down language; they will lose trust |

---

## Pattern 1: Narrative (for Executives)

**When to use:** Commissioner briefings, Borough President presentations, City Council testimony, press releases with data backing.

**Structure:**
1. The question we were asked
2. What we found (the number + what it means for decisions)
3. How confident we are (plain language)
4. What we did NOT measure (one-sentence limitation)

**Example (ramp completion analysis):**
> "We looked at all 187,000 ramp records in the city's database to see which boroughs are on track to meet ADA targets. Brooklyn is currently at 74% completion — on pace to hit the 80% goal by Q4. The Bronx is at 61% and needs attention. Our estimate has a ±3 percentage point margin of error because not all ramps have been physically confirmed. We did not analyze why some boroughs lag — that would require a separate field audit."

**Rules:**
- No method names (do not say "Wilson Score", "CUSUM", "KMeans")
- Lead with the number; explain how you got it only if asked
- Never use the word "significant" without defining it
- One sentence only on limitations (not a full caveat section)

---

## Pattern 2: Layered Technical (for Analysts)

**When to use:** Operations managers reviewing dashboards, program managers signing off on analysis, senior inspectors interpreting field metrics.

**Structure:**
1. Plain-language summary (3–5 sentences, same as executive version)
2. "How we calculated this" section (method in everyday terms)
3. "If you want the details" accordion / collapsible or appendix

**Example (quality score):**
> **Summary:** The data quality score for the inspections dataset is 81/100, above our 75-point target. The main drag is a 12% null rate in the `x_coord` field, which affects spatial mapping.
>
> **How we calculated this:** The score combines four factors — completeness (are all fields filled in?), validity (are values in the right format?), consistency (do related fields agree?), and freshness (how recently was the data updated?). Completeness gets the most weight (35%) because missing data is the most common problem. Each factor is scored 0–100 and averaged with these weights.
>
> **Details:** Formula: `0.35×completeness + 0.25×validity + 0.25×consistency + 0.15×freshness`. Completeness = 1 − (null_count / total_cells). Validity uses a rule set defined in `quality/rules.py`. Freshness uses days since `last_modified` vs. SLA thresholds (HIGH=14d, MED=30d, LOW=60d).

---

## Pattern 3: Q&A Format (for Technical Peers / Peer Review)

**When to use:** Internal peer review, handing off analysis to another analyst, documentation for reproducibility, code review of analytical logic.

**Structure:** Anticipate the 5 most likely "how did you..." questions and answer them directly.

**Standard Q&A set for NYC DOT analyses:**

1. **What data did you use?** [Dataset key, fourfour, row count, pull date, filters applied]
2. **How did you handle nulls?** [Imputed / excluded / flagged — and what effect did that have]
3. **What method did you use and why that method?** [Name it; explain why vs. alternatives]
4. **What are the key assumptions?** [List them; note which are estimated vs. measured]
5. **What would change the conclusion?** [Sensitivity: if assumption X changes by Y%, conclusion changes to Z]

---

## Anti-Patterns to Avoid

| Anti-pattern | Problem | Fix |
|---|---|---|
| "The model shows..." | Implies a black box; erodes trust | "We calculated..." or "The data shows..." |
| "Statistically significant" without definition | Means nothing to non-statisticians | "We're 95% confident this result is real, not random variation" |
| Full formula in executive section | Eyes glaze; question the analyst | Move to appendix; reference it |
| "Preliminary results suggest..." | Weasel phrase; sounds unconfident | State the finding; note uncertainty separately |
| All caveats upfront | Buries the finding | State finding first; caveat after |
| "As you can see in the chart..." | Forces audience to find it | Describe the key number in the text |
