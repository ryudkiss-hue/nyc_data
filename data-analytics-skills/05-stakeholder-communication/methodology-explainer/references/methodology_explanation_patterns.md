# Methodology Explanation Patterns

Reusable structures for explaining how an analysis was done, tailored to different communication contexts.

---

## Pattern 1: The One-Paragraph Summary (Executive)

Use when the audience needs enough to trust the output without wanting the detail.

**Structure:**
1. What question were we answering?
2. What data did we use, and for what time period?
3. What method did we apply (in plain English)?
4. What is the key limitation?

**Example:**
> To understand whether the new onboarding flow improved activation, we compared users who experienced the redesign (n=4,200) against a matched control group (n=4,100) over a 6-week period using our product analytics data. We measured 7-day activation rate for both groups and tested whether the difference was larger than chance. One limitation: the groups were matched on signup channel but not on company size, so enterprise accounts may be slightly over-represented in the treatment group.

**Plain-language swaps for this pattern:**
- "A/B test" → "We split users randomly into two groups and compared them"
- "Matched control group" → "A comparison group selected to be as similar as possible to the treatment group"
- "Statistical significance" → "We tested whether the difference was larger than random chance"

---

## Pattern 2: The Layered Writeup (Business Analyst)

Use for reports where some readers want the summary and others want the detail.

**Structure:**
- **Section 1:** 1-paragraph summary (Pattern 1 above)
- **Section 2:** Data and scope — what data, what time period, any filters applied
- **Section 3:** Method — how the calculation or model works, at a level that lets a smart non-statistician follow the logic
- **Section 4:** Assumptions — explicit list with rationale
- **Section 5:** Limitations — what this analysis cannot answer
- **Appendix:** Technical detail for peer reviewers

---

## Pattern 3: The Q&A Format (Stakeholder Presentation)

Use in slide decks or meeting notes where readers will have questions.

Structure as a list of anticipated questions:

- *How did you decide who to include?* → [answer]
- *Why did you use that time period?* → [answer]
- *Could this result be a coincidence?* → [answer on statistical confidence]
- *What would change the conclusion?* → [answer on key assumptions]
- *What isn't this analysis telling us?* → [honest limitation]

---

## Plain-Language Translation Table

| Technical term | Plain-language equivalent |
|---|---|
| p-value < 0.05 | We're 95% confident this difference isn't random chance |
| Confidence interval | The range we'd expect the true value to fall within |
| Regression | A formula that shows how much one thing changes when another changes |
| Correlation coefficient | A score showing how closely two things move together (−1 to +1) |
| Outlier | A data point that is unusually different from the rest |
| Cohort | A group of users who all started at the same time |
| Time series | Data tracked over time to show trends |
| Normalised / indexed | Adjusted so that different things can be compared fairly |
| Lookalike model | An algorithm that finds new customers who behave like your best existing customers |
| Lift | The improvement above the baseline — what the change added |
| Holdout group | A group kept from receiving the change so we can measure the impact |
| Feature importance | How much each input variable contributed to the model's predictions |

---

## Limitations Language Templates

Adapt these for specific analyses:

- "This analysis is based on observed behaviour; we cannot rule out that [third variable] explains part of the result."
- "The sample covers [period/segment], so conclusions may not apply to [out-of-scope period/segment]."
- "Correlation is shown, not causation; an experiment would be needed to confirm the causal relationship."
- "Data was sourced from [system]; any reporting gaps in that system would affect this analysis."
- "The model has an accuracy of [X%] on the test set; real-world performance may differ."
