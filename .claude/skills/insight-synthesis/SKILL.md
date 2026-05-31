---
name: insight-synthesis
description: Transform data findings into compelling insights. Use when converting analysis results into actionable insights, connecting findings to business impact, or preparing insights for stakeholder communication.
---

# Insight Synthesis

# When to use
- An analysis has produced many statistics but no clear "so what"
- The team has findings but is struggling to prioritise which ones to act on
- Stakeholders are asking "what does this mean for us?" rather than "what did you find?"
- Multiple analyses need to be synthesised into a unified set of recommendations
- Preparing an insight briefing for a team that doesn't have time to review the full analysis

# Process
1. **List all findings** — enumerate every statistically meaningful finding: trends, comparisons, correlations, anomalies, surprises. Write each as a factual statement. Don't interpret yet.
2. **Apply So What → Why → Now What to each finding** — convert each fact into an insight by answering: So what (why does this matter to the business?), Why (what is the most likely explanation?), Now what (what specific action should follow?). See `references/insight_framework.md`.
3. **Quantify business impact** — for each insight, estimate the financial, customer, or operational magnitude. An insight without a number is an observation. Use order-of-magnitude estimates if precise data is not available.
4. **Prioritise by impact × confidence × actionability** — score each insight on these three dimensions (1–3 scale). Insights that score high on all three are the ones to lead with. Deprioritise insights that are high-impact but low-confidence until validated.
5. **Group and resolve conflicts** — cluster related insights and check for contradictions. If two findings point in opposite directions, document the tension and state what additional data would resolve it.
6. **Produce the insight brief** — present the top 3–5 insights in priority order, each with the finding, So What / Why / Now What, business impact, and confidence level. Use `assets/insight_brief_template.md`.

# Inputs the skill needs
- All analysis findings (statistics, charts, model outputs, anomalies)
- Business context: current goals, OKRs, strategic priorities
- Audience who will act on the insights (role and decision authority)
- Confidence levels for the findings (based on sample size, method, data quality)
- Known constraints on action (budget, timeline, team capacity)

# Output
- `references/insight_framework.md` — So What / Why / Now What pattern, insight quality rubric, prioritisation matrix
- `references/prioritization_guide.md` — scoring insights by impact, confidence, and actionability; how to present trade-offs
- `assets/insight_brief_template.md` — structured brief: top insights in priority order, each with impact, explanation, recommendation, and confidence level
