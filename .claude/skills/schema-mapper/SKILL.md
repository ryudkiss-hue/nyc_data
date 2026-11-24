---
name: schema-mapper
description: Discover, document, and visualize database schemas including tables, columns, relationships, and join paths. Use when working with an unfamiliar database, creating ERD documentation, or understanding how tables connect before writing queries.
---

# When to use
- Starting work on an unfamiliar database and need to understand the structure
- Writing a multi-table query and need to find the correct join path
- Creating or updating ERD documentation for a team or audit
- Onboarding a new analyst who needs a database overview

# Process
1. **Connect and discover** — list all tables in scope using `scripts/schema_extractor.py`; confirm access permissions
2. **Extract table metadata** — for each table: column names, data types, nullable flags, primary keys, foreign keys, row counts, and sample values
3. **Infer relationships** — identify explicit foreign keys from schema; infer implicit relationships from naming patterns (e.g. `user_id` in multiple tables); document confidence level
4. **Generate data dictionary** — create per-column descriptions using `scripts/data_dictionary_generator.py`; include data type, sample values, null rate, and business context where available
5. **Find join paths** — use `scripts/join_path_finder.py` (BFS on relationship graph) to identify how any two tables can be joined; document intermediate tables
6. **Create ERD** — generate Mermaid ERD diagram using `scripts/erd_generator.py`; include cardinality notation
7. **Produce quick reference** — generate `assets/schema_quick_reference.md` with most-used tables, key columns, and common join patterns

# Inputs the skill needs
- Required: database connection details or schema export (SQL DDL, information_schema dump, or dbt manifest)
- Required: scope — which schemas or tables to map
- Required: documentation goal — ERD, data dictionary, join paths, or quick reference guide
- Optional: known relationships to validate
- Optional: tables to exclude (staging, temp, audit logs)

# Output
- Mermaid ERD diagram (.mmd file) — entity-relationship diagram with cardinality
- CSV data dictionary — per-column metadata with descriptions
- `assets/schema_quick_reference.md` — human-readable quick reference guide
- JSON relationship graph — machine-readable for downstream tooling
