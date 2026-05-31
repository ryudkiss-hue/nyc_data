---
name: analysis-planning
description: Structure analysis approach before starting work. Use when receiving new analysis requests, breaking down complex questions into steps, or planning iterative analysis workflows.
---

# When to use

After requirements are gathered and before any data is touched. Planning is especially important when the analysis involves multiple steps, uncertain data availability, or a tight deadline where sequencing matters. A 15-minute planning session prevents hours of wrong-direction work.

# Process

1. **Decompose the question** — break the business question into sub-questions using `references/scoping_framework.md`; each sub-question should be answerable with a single data pull or calculation.
2. **Identify data dependencies** — for each sub-question, list the required tables/datasets and assess availability (confirmed / likely / unknown); flag blockers early.
3. **Sequence the work** — order sub-questions so that each output feeds the next; identify which steps can run in parallel.
4. **Estimate effort** — use `references/effort_estimation.md` to assign time estimates per step; sum to a total and compare against the deadline.
5. **Log risks and dependencies** — use `references/risks_dependencies.md` to document anything that could delay or invalidate the plan (data gaps, external approvals, methodology uncertainty).
6. **Produce the plan** — fill in `assets/analysis_plan_template.md`; for projects with stakeholder kickoffs use `assets/kickoff_doc_template.md`.

# Inputs the skill needs

- Analysis brief or requirements doc (from `stakeholder-requirements-gathering` skill)
- Available data sources
- Deadline and resource constraints

# Output

- Completed analysis plan with sequenced steps and time estimates (`analysis_plan_template.md`)
- Kickoff doc for stakeholder alignment (optional, `kickoff_doc_template.md`)
- Risk / dependency log
