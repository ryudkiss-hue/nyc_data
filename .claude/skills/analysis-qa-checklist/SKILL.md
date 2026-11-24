---
name: analysis-qa-checklist
description: Pre-delivery quality gate for analytical work. Activate before sharing any analysis, dashboard, or query result with stakeholders. Catches logic errors, presentation issues, and assumption gaps before they reach the audience.
---

# When to use
- Before delivering any analysis, report, dashboard, or query result to stakeholders
- After completing a peer review to confirm all issues are resolved
- When returning to an analysis after a break to verify nothing was missed
- Any output that will inform a business decision

# Process
1. **Run automated checks** — execute `scripts/qa_runner.py` on the output file; flags numeric anomalies (unexpected nulls, out-of-range values, division results), structural issues, and formatting problems
2. **Complete the logic checklist** — work through `references/qa_checklist_master.md` covering: question framing, data sourcing, transformations, statistical validity, finding statements, and presentation
3. **Check for common errors** — review `references/common_analysis_errors.md` for analysis-type-specific mistakes (e.g. survivorship bias in cohort analysis, multiple comparison issues in A/B tests)
4. **Validate assumptions** — confirm every assumption is documented, sourced, and has been sensitivity-tested where uncertain
5. **Review the narrative** — verify: the conclusion follows logically from the data, all caveats are stated, and recommendations are specific and actionable
6. **Sign off** — complete `assets/qa_signoff_template.md` documenting the reviewer, issues found, resolutions, and delivery decision

# Inputs the skill needs
- Required: output file (CSV, notebook, SQL result, or document)
- Required: the original analysis question or brief
- Required: reviewer name and intended audience

# Output
- QA runner report with automated flags
- Completed checklist with pass/fail for each section
- `assets/qa_signoff_template.md` (filled) — formal sign-off confirming the output is ready for delivery
