---
name: sql-to-business-logic
description: Translate SQL queries into plain language business logic. Use when documenting queries, explaining analysis to non-technical stakeholders, code reviewing for correctness, or building a query catalog.
---

# SQL to Business Logic Translator

# When to use
- A stakeholder asks "what exactly does this query calculate?"
- Documenting a query library or a dbt model for non-technical readers
- Reviewing a query for correctness by comparing its logic to the business requirement
- Onboarding new analysts to existing SQL patterns
- Translating legacy undocumented queries before refactoring

# Process
1. **Receive the query and context** — obtain the SQL and the business question it answers. Also collect any schema notes (what the key tables and columns represent in business terms).
2. **Translate the FROM/JOIN structure** — describe in plain language which data sources are combined and what type of join is used (inner keeps only matches; left keeps all rows from the left side). Note if the join type seems inconsistent with the stated purpose.
3. **Translate WHERE filters** — list each filter condition as a business rule in plain language (e.g., `status = 'completed'` → "only includes orders that have been paid and fulfilled").
4. **Explain GROUP BY and aggregations** — describe what each aggregation computes and at what grain. Use `scripts/sql_explainer.py` to automate a first-pass structural parse.
5. **Summarise output columns** — for each output column, state its business meaning and any edge cases (nulls, rounding, currency units).
6. **Flag issues and write validation questions** — identify potential problems (implicit null propagation, unexpected fan-out, hardcoded dates). Generate 3–5 questions the query author should confirm. Use `assets/query_documentation_template.md` to record the full translation.

# Inputs the skill needs
- The complete SQL query (SELECT through ORDER BY)
- The business question the query is intended to answer
- Table and column descriptions (or a data catalog entry)
- Any business rules for key status values, date handling, or currency
- The intended output: who reads the result and for what decision

# Output
- `scripts/sql_explainer.py` — parses a SQL query and generates a structured plain-language explanation
- `assets/query_documentation_template.md` — completed translation covering purpose, step-by-step logic, output columns, business rules, and validation questions
- Optionally: a flowchart representation of the query logic
