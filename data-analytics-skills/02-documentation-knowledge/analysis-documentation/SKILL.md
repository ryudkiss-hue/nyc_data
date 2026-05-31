---
name: analysis-documentation
description: Structured, reproducible analysis documentation. Use when documenting analysis findings, creating analysis notebooks, ensuring reproducibility, or building analysis archives for future reference.
---

# Analysis Documentation

# When to use
- Finalising an analysis before sharing it with stakeholders
- Handing off an analysis to another team member or to a future self
- Archiving recurring analyses so they can be run again consistently
- Preparing for peer review or a formal audit
- Converting an exploratory notebook into a reference document

# Process
1. **Confirm audience and scope** — determine whether the primary reader is technical (data team), business (stakeholders), or both. For mixed audiences, use a tiered structure. See `references/audience_depth_guide.md` for calibration.
2. **Write the business context section** — state the business question, the stakeholders who requested the analysis, the decisions it informs, and the success criteria.
3. **Document data sources** — for each source, record the table or file, date range, row count, key columns, and any known quality issues or exclusions applied.
4. **Write the methodology section** — describe the analytical approach, tools and library versions, key assumptions, and important decisions made (and alternatives considered). Reference the assumptions log if one exists.
5. **Record results** — include key metrics and statistics, embed or link visualisations with descriptive captions, and present findings in order of importance.
6. **Write the insights, recommendations, and reproducibility section** — connect each finding to a business implication and a next action. Document the steps required to reproduce the analysis (data access, environment, execution order). Use `assets/analysis_doc_template.md` as the structure.

# Inputs the skill needs
- Final code (SQL, Python, notebook) and outputs (charts, tables)
- Business question and stakeholder context
- Key findings and recommendations already identified
- Data source details (tables, date ranges, sample sizes)
- Library and tool versions used

# Output
- `assets/analysis_doc_template.md` — completed analysis document covering context, data, methodology, results, and reproducibility
- Linked or embedded visualisations and code references
