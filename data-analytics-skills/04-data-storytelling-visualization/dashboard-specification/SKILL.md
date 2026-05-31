---
name: dashboard-specification
description: Design specifications for effective dashboards. Use when planning new dashboards, improving existing ones, or documenting dashboard requirements before development starts.
---

# Dashboard Specification

# When to use
- A new dashboard is being built and developers need a clear brief before starting
- An existing dashboard is confusing or underused and needs a structured redesign
- Stakeholders and the data team have different ideas about what a dashboard should show
- Documenting dashboard requirements as part of a broader data product process
- Creating a self-service analytics specification that can be handed off without multiple Q&A rounds

# Process
1. **Define the purpose** — write one sentence: "This dashboard answers [question] for [audience] who need to [decision or action]." If it can't be stated in one sentence, the scope needs narrowing first. See `references/dashboard_design_principles.md`.
2. **Profile target users** — for each audience (executive, manager, IC), document their visit frequency, the primary question they come to answer, and their technical comfort level. Users with different needs usually need different dashboards, not more filters on one.
3. **Define the metric hierarchy** — list primary KPIs (hero numbers at the top), secondary supporting metrics, and detail-level breakdowns. A dashboard with more than 10–12 distinct metrics is trying to do too much.
4. **Design the information architecture** — sketch the layout using the hero → trends → breakdowns → details pattern. Position the most important information in the top-left. Use `references/dashboard_requirements_guide.md` for layout patterns.
5. **Specify interactivity** — list global filters (date range, region, segment), drill-down paths, click actions, and hover tooltip content. Every filter and drill-down adds complexity; justify each one.
6. **Document data requirements and success criteria** — for each metric, record the source table, transformation logic, and refresh frequency. Define how dashboard success will be measured (adoption rate, reduction in ad-hoc requests). Complete `assets/dashboard_spec_template.md`.

# Inputs the skill needs
- The business question the dashboard is meant to answer
- A list of candidate metrics (team can provide a rough list; you'll curate it)
- The primary audience (role, visit frequency, decision they make)
- Data availability: confirmed source tables and refresh schedules
- Any constraints: tool (Tableau, Looker, Metabase, etc.), branding guidelines

# Output
- `references/dashboard_design_principles.md` — layout hierarchy, chart selection, information density guidelines
- `references/dashboard_requirements_guide.md` — how to run requirements gathering, avoid scope creep, and validate the spec
- `assets/dashboard_spec_template.md` — complete spec: purpose, users, metric hierarchy, layout wireframe, interactivity, data sources, success criteria
