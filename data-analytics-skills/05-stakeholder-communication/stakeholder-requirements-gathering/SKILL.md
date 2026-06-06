---
name: stakeholder-requirements-gathering
description: Structure and clarify analysis requests before work begins. Activate when a request is vague, has multiple stakeholders with potentially different needs, or when the analysis is non-trivial and rework would be costly.
---

# When to use
- A request is vague ("can you look into our churn?") and needs clarification
- Multiple stakeholders are involved and may have different definitions of success
- The analysis is non-trivial and misunderstanding requirements would waste days of work
- A high-stakes decision will be made based on the analysis output

# Process
1. **Conduct intake interview** — use `references/intake_interview_guide.md` to surface: the business question, the decision it will inform, the stakeholder who will act on it, the timeline, and what "done" looks like
2. **Classify the decision type** — use `references/decision_maker_framework.md` to determine whether the decision is exploratory, confirmatory, or operational; this sets the required rigor level
3. **Document requirements** — fill `assets/requirements_template.md` covering: scope, data sources, output format, success criteria, and known constraints
4. **Resolve ambiguities** — use `references/elicitation_techniques.md` to address unclear points (e.g. "what would you do differently if X was 10% vs 50%?")
5. **Get sign-off** — share `assets/analysis_brief_template.md` with the stakeholder; confirm understanding before any data is pulled

# Inputs the skill needs
- Required: stakeholder's initial request (even if vague)
- Optional: stakeholder names and roles
- Optional: known timeline

# Output
- `assets/requirements_template.md` (filled) — scope, data, output format, success criteria
- `assets/analysis_brief_template.md` (filled) — authoritative scope document shared with stakeholder for sign-off
- Optional: interview notes for complex or multi-stakeholder requests
