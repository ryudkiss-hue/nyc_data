---
name: analysis-qa-checklist
description: Pre-delivery quality assurance for analysis work. Use when reviewing analysis before sharing with stakeholders, checking for completeness, validating assumptions, or ensuring clarity of recommendations.
---

# When to use

Before sharing any analysis output with a stakeholder — dashboard, report, ad-hoc query result, model output, or written findings. Run this every time, not just for big projects. The cost of a post-delivery correction is always higher than the cost of a pre-delivery check.

# Process

1. **Run automated checks** — use `scripts/qa_runner.py` against the output file to catch numeric, structural, and formatting issues programmatically.
2. **Complete the logic checklist** — work through `references/qa_checklist_master.md` section by section: question framing, data sourcing, transformations, statistical validity, findings, and presentation.
3. **Review for common errors** — cross-check against `references/common_analysis_errors.md`; pay special attention to the top-frequency mistakes for the analysis type.
4. **Validate assumptions explicitly** — for every assumption in the analysis, verify it has a source, is documented, and the output is sensitivity-tested where the assumption is uncertain.
5. **Check the narrative** — confirm the conclusion follows from the data, caveats are stated, and the recommendation is actionable.
6. **Record sign-off** — complete `assets/qa_signoff_template.md` with reviewer, issues found, resolution status, and delivery decision.

# Inputs the skill needs

- Output file to review (CSV, notebook, SQL result, or written doc)
- Original analysis question / brief
- Name of reviewer and intended audience

# Output

- QA runner report (automated flags)
- Completed checklist with pass/fail per section
- Signed-off `qa_signoff_template.md` confirming delivery readiness
