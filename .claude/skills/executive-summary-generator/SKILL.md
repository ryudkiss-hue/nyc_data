---
name: executive-summary-generator
description: Create concise executive summaries from detailed analysis. Use when preparing board decks, executive briefings, or condensing complex analysis into decision-ready formats for senior audiences.
---

# Executive Summary Generator

# When to use
- A detailed analysis needs to be condensed to 1–2 pages for a senior audience
- An executive asks "what's the bottom line?" and a full report won't be read
- Preparing a board deck section that summarises a longer analytical workstream
- A recurring report needs to lead with the key message rather than data tables
- A decision needs to be made by end of day and the executive has 10 minutes

# Process
1. **Extract the top 3–5 insights** — go through the full analysis and identify only the findings that change or reinforce a decision. Filter out interesting-but-not-actionable findings. If you have more than 5 insights, you haven't prioritised yet.
2. **Quantify the business impact of each insight** — every insight must carry a number: revenue at risk, cost saving, users affected, time to payback. Vague impact ("significant") does not belong in an executive summary. See `references/executive_communication.md`.
3. **Write a one-paragraph situation statement** — explain why this analysis was done, what the question was, and why the timing matters. One paragraph, no jargon.
4. **Apply the pyramid principle** — lead each insight with the conclusion ("Mobile churn is causing $800K ARR loss"), then the evidence, then the supporting detail. Never bury the finding at the end of a paragraph.
5. **State recommendations as specific actions** — each recommendation must name what to do, who is responsible, what the expected outcome is, and by when. "Improve the app" is not a recommendation.
6. **Write the decision block** — the final section names the explicit decision or approval the executive needs to give, the investment or resource required, the expected return, and the deadline. Use `assets/executive_summary_template.md` to assemble the document.

# Inputs the skill needs
- The full analysis or report to be summarised
- Knowledge of the executive audience (role, priorities, decisions they're responsible for)
- Quantified business impact for each major finding
- Recommended actions already identified
- Format constraints (one page, two pages, specific slide count)

# Output
- `references/pyramid_principle_guide.md` — answer-first structure, BLUF writing, how to edit a bottom-up draft into top-down
- `references/executive_communication.md` — adapting tone, removing jargon, quantifying everything, avoiding hedge language
- `assets/executive_summary_template.md` — 1–2 page template: situation, key insights (with impact), recommendations (with outcomes), decision needed
