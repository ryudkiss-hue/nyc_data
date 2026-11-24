---
name: peer-review-template
description: Structure a peer review of analytical work before stakeholder delivery. Use when reviewing a colleague's analysis, dashboard, or query for quality, correctness, and clarity.
---

# When to use
- Reviewing analytical work before it reaches stakeholders or goes into production
- A dashboard is being promoted to production and needs a formal review
- An analysis will inform a strategic decision and independent validation is warranted
- Any analysis that will be cited externally or used in a regulated context

# Process
1. **Clarify review scope** — agree with the author on what the review covers: analytical logic, statistical methods, code quality, presentation, or all of the above
2. **Assess analytical rigour** — verify: the research question maps to the methodology, assumptions are documented, data supports conclusions, and uncertainty is communicated
3. **Technical review** — if code is included: check reproducibility, correctness of logic, code readability, and performance; run `scripts/qa_runner.py` if applicable
4. **Provide structured feedback** — categorise findings as: must-fix (blocks delivery), should-fix (quality issue), or nice-to-have (enhancement); be specific and actionable — "line 47: join produces fan-out, add DISTINCT or aggregate first"
5. **Author response** — author addresses each item and documents: resolved, won't fix (with rationale), or deferred
6. **Sign off** — reviewer confirms critical items are resolved; document in `assets/review_signoff_template.md`

# Inputs the skill needs
- Required: the analytical output (notebook, report, dashboard spec, or SQL)
- Required: agreed review scope
- Required: reviewer name and relationship to the work

# Output
- Completed review document with categorised feedback (must-fix / should-fix / nice-to-have)
- Author response log documenting resolutions
- `assets/review_signoff_template.md` (filled) — formal sign-off confirming critical items resolved
