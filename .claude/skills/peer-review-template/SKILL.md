---
name: peer-review-template
description: Structured peer review for analytical work. Use when reviewing teammates' analysis, providing constructive feedback, or establishing analysis quality standards.
---

# When to use

Before any analysis that will influence a significant decision is delivered to stakeholders. Peer review should be part of the standard delivery checklist for: dashboards going into production, reports used for strategic decisions, A/B test conclusions, and any analysis that will be cited externally.

# Process

1. **Agree scope of review** — clarify with the author what kind of review is needed: logic check, statistical validity, code review, or presentation clarity. Use `references/peer_review_framework.md` to set expectations.
2. **Review analytical rigour** — work through `references/analytical_rigor_checklist.md`: are the question and method aligned? Are assumptions valid? Is the conclusion supported by the data?
3. **Review code or SQL** — if the analysis involves code, apply `references/code_review_for_analysis.md`: reproducibility, correctness, readability, and performance.
4. **Write feedback** — use the feedback structure in `assets/peer_review_template.md`: must-fix issues, should-fix suggestions, and optional improvements. Be specific; "this is unclear" is not actionable.
5. **Author responds** — the author addresses each point and notes disposition (fixed / accepted as-is with rationale / deferred); use `assets/review_response_template.md`.
6. **Close the review** — reviewer confirms must-fix items are resolved and signs off; document the outcome in `assets/peer_review_template.md`.

# Inputs the skill needs

- Analysis output to review (notebook, report, dashboard spec, or SQL)
- Review scope agreed with author
- Reviewer name and role

# Output

- Completed review with categorised feedback (`peer_review_template.md`)
- Author response log (`review_response_template.md`)
- Sign-off confirmation
