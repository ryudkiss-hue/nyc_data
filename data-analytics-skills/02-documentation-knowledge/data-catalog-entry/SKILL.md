---
name: data-catalog-entry
description: Create standardized metadata for data assets. Use when documenting new datasets, building data catalogs, improving data discoverability, or creating data dictionaries for teams.
---

# When to use
- A new table, view, or dataset needs to be discoverable by other teams
- Analysts keep asking the same questions about what a table means or who owns it
- Compliance or audit requirements mandate documentation of sensitive data
- Onboarding a new team member who needs to understand available data assets
- Auditing the data catalog for undocumented tables

# Process
1. **Extract technical metadata** — use `scripts/catalog_extractor.py` to pull schema, column types, row counts, and sample values from the database
2. **Collect business context** — interview the data owner to document: business purpose, update frequency, upstream sources, downstream consumers, and known limitations
3. **Write column descriptions** — for each column, write a plain-language description including what it represents, valid values, and any business rules
4. **Assess data quality** — document known quality issues, null rates for key columns, and any data quality SLAs
5. **Document lineage** — identify upstream sources and downstream consumers; note any transformations applied
6. **Publish governance details** — document data owner, steward, sensitivity classification, and access policy using `assets/catalog_entry_template.md`

# Inputs the skill needs
- Required: database connection or export for technical metadata
- Required: data owner contact
- Optional: knowledge of upstream sources and downstream consumers
- Optional: applicable governance or compliance policies
- Optional: existing partial documentation to build on

# Output
- `scripts/catalog_extractor.py` — automated schema extraction
- `assets/catalog_entry_template.md` (filled) — complete catalog entry with technical metadata, business context, column descriptions, lineage, and governance details
