---
name: sql-to-business-logic
description: Translate a SQL query into a plain-language explanation of what the business logic does. Use when documenting queries, onboarding analysts, preparing code reviews, or explaining logic to non-technical stakeholders.
---

# When to use
- A stakeholder asks "what does this query actually calculate?"
- Documenting a library of production queries for future maintainability
- Reviewing a query written by someone else and need to understand the intent
- Onboarding a new analyst who needs to understand existing logic
- Refactoring legacy SQL where original intent is unclear

# Process
1. **Parse and gather context** — collect the SQL, the business question it answers, schema descriptions, and the intended audience
2. **Describe data sources and joins** — explain what tables are combined, how they're joined, and what each join produces (inner = only matching, left = all from left + matches, etc.)
3. **Translate filter conditions** — convert WHERE and HAVING clauses into business rules ("only include customers who signed up before X", "only orders above $100")
4. **Explain aggregations and grouping** — describe what the GROUP BY produces and what each aggregate function calculates in business terms
5. **Document output columns** — for each output column, describe what it represents and any edge cases (nulls, division by zero guards, coalesces)
6. **Flag potential issues** — identify implicit null propagation, unexpected fan-out from joins, hardcoded dates, and generate validation questions for the query author

# Inputs the skill needs
- Required: the complete SQL query
- Required: the business question the query answers
- Optional: table and column descriptions (schema context)
- Optional: business rules or definitions relevant to the logic
- Optional: target audience (technical analyst vs. business stakeholder)
- Optional: the decision or action this query informs

# Output
- `scripts/sql_explainer.py` — automated SQL parsing and explanation generation
- Plain-language documentation using the standard template
- Optional: flowchart representation of query logic
