---
name: schema-mapper
description: Document column-level mappings between source and target schemas. Use when integrating data from multiple systems, designing ETL transformations, or documenting how raw fields become analytical assets.
---

# Schema Mapper

# When to use
- Integrating a new data source and need to map its fields to the existing data model
- Designing an ETL or dbt transformation and need to document the logic
- Auditing what happened to a field during a migration
- Onboarding a new analyst who needs to understand where columns come from
- Preparing a data catalog entry that requires lineage at the column level

# Process
1. **Collect the source schema** — list every column name, data type, nullable flag, and a brief description. Pull from `INFORMATION_SCHEMA`, a data dictionary, or the source API documentation.
2. **Collect the target schema** — same structure for the destination table or model. If the target doesn't exist yet, draft it based on the analytical requirements.
3. **Map source columns to target columns** — for each target column, identify the source column(s) that feed it. Record direct mappings (rename only) and derived mappings (calculation, type cast, lookup join). Use `scripts/schema_compare.py` to automate direct-name matches.
4. **Document transformation rules** — for each derived mapping, write the exact transformation (e.g., `CAST(amount_cents AS FLOAT) / 100.0`, `COALESCE(first_name, email)`).
5. **Flag gaps** — identify target columns with no source (need to be created or defaulted) and source columns with no target (dropped or deferred). Record a decision for each.
6. **Produce the mapping document** — complete `assets/schema_mapping_template.md` with the full column inventory and share for review before implementation.

# Inputs the skill needs
- Source schema: table name, column names, data types, and descriptions
- Target schema: same, or the analytical requirements that define it
- Any existing transformation logic (SQL, dbt models, Python code)
- Business rules that govern how values should be transformed or defaulted
- Stakeholder who can resolve ambiguous fields

# Output
- `scripts/schema_compare.py` — compares two schemas and finds direct-name matches and type mismatches
- `assets/schema_mapping_template.md` — completed column-by-column mapping with transformation rules, gaps, and decisions
- Optional: transformation SQL or dbt YAML generated from the mapping
