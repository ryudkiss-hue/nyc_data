---
name: dashboard-specification
description: Define complete requirements for a data dashboard before development begins. Use when a new dashboard is requested, when an existing dashboard needs redesign, or when stakeholder alignment is needed before building.
---

# When to use
- A stakeholder requests a new dashboard and you need to capture requirements clearly
- An existing dashboard is misaligned with user needs and needs redesign
- Multiple stakeholders have conflicting ideas about what the dashboard should show
- A developer needs a clear spec before building

# Process
1. **Define dashboard purpose** — articulate the single sentence: "This dashboard answers [question] for [audience] who need to [decision or action]." If this can't be expressed in one sentence, the scope needs narrowing.
2. **Profile the users** — for each user type, document: visit frequency, primary questions, key decisions, and technical comfort. Different audiences typically warrant separate dashboards rather than extra filters.
3. **Define the metric hierarchy** — organise into: primary KPIs (top of page, max 3–5), secondary metrics (supporting context), and detail breakdowns. Flag scope creep if total metrics exceed 10–12.
4. **Design information architecture** — follow hero → trends → breakdowns → details pattern; place most important content top-left; define sections and their purpose
5. **Specify interactivity** — list every filter, drill-down, and toggle; justify each one (adds decision value vs. adds complexity)
6. **Document data requirements** — for each metric: source table, calculation, refresh frequency, and any known data quality issues

# Inputs the skill needs
- Required: stakeholder's business question or use case
- Required: intended users and their roles
- Optional: existing dashboard or report to build on
- Optional: refresh frequency requirements and data source constraints

# Output
- `references/dashboard_design_principles.md` — layout, hierarchy, and interactivity guidelines
- `references/dashboard_requirements_guide.md` — stakeholder question frameworks
- `assets/dashboard_spec_template.md` (filled) — complete spec: purpose, users, metrics, layout, interactivity, data sources, and success criteria
