---
name: data-catalog-entry
description: Create standardized metadata for data assets. Use when documenting new datasets, building data catalogs, improving data discoverability, or creating data dictionaries for teams.
---

# Data Catalog Entry

# When to use
- A new table, view, or dataset has been created and needs to be discoverable
- Analysts keep asking the same questions about a table's meaning or ownership
- A compliance or audit requirement mandates documentation of sensitive data
- Onboarding new team members who need to understand available data assets
- Auditing catalog completeness to find undocumented tables

# Process
1. **Extract technical metadata** — pull schema, column names, types, primary keys, foreign keys, and row count from `INFORMATION_SCHEMA` or the source system. Use `scripts/catalog_extractor.py` to automate this for database tables.
2. **Collect business context** — interview the data owner to capture the business purpose, owning team, criticality (critical / high / medium / low), and known use cases. Record the business-friendly display name.
3. **Write column descriptions** — for each column, write a one-sentence plain-language description, note example values, and document any business rules (valid values, constraints, format requirements).
4. **Assess data quality** — calculate or estimate completeness, freshness (hours since last update), and duplicate rate. Document known issues and how they affect downstream use.
5. **Document lineage** — record upstream sources (where the data comes from) and downstream consumers (dashboards, models, reports that depend on it).
6. **Add governance details and publish** — specify access level (public/restricted/confidential), sensitivity (PII, financial, health), compliance tags, retention policy, and access instructions. Complete `assets/catalog_entry_template.md` and submit to the catalog.

# Inputs the skill needs
- Connection or export from the database/source system for technical metadata
- Data owner contact for business context interview
- Knowledge of upstream sources and downstream consumers
- Applicable governance policies (PII classification, retention rules)
- Any existing partial documentation or data dictionary

# Output
- `scripts/catalog_extractor.py` — extracts schema and basic stats from a database table
- `assets/catalog_entry_template.md` — completed catalog entry with technical, business, quality, lineage, and governance sections
