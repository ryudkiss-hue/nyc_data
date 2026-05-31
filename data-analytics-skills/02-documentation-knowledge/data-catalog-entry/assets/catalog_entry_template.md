# [table_name]

## Overview

**Name:** `[schema.table_name]`
**Type:** table / view / materialized view
**Domain:** [Finance / Product / Marketing / Operations / Other]
**Criticality:** critical / high / medium / low

**Description:**
[One sentence: what business process or entity does this table represent?]

**Grain:** [What does one row represent? e.g., "One row per order, captured at the time of placement"]

---

## Ownership

- **Business Owner:** [name / team]
- **Technical Owner:** [name / team]
- **Last reviewed:** [YYYY-MM-DD]

---

## Schema

**Row Count (at extraction):** [n]
**Extracted:** [YYYY-MM-DD HH:MM UTC]

| Column | Type | Nullable | Keys | Description | Example values |
| --- | --- | --- | --- | --- | --- |
| [column] | [type] | Yes / No | PK / FK / — | [business meaning] | [example] |

---

## Relationships

**Primary key:** `[column(s)]`

**Foreign keys:**

| Column | References |
|---|---|
| [column] | [schema.table.column] |

---

## Data Quality

- **Completeness:** [%] — [notes on which fields may be NULL and why]
- **Freshness:** [Last updated: / Refresh schedule: ]
- **Known issues:**
  - [Issue 1 — e.g., "Records before 2022-01-01 use a different status enum"]
  - [none]

---

## Lineage

**Upstream sources:**
- [source table or system]

**Downstream consumers:**
- [dashboard / report / dbt model / ML feature]

---

## Access & Governance

**Access level:** public / restricted / confidential
**Sensitivity:** none / PII / financial / health
**Compliance tags:** SOX / GDPR / HIPAA / CCPA / none

**Access instructions:**
[How to request access — e.g., "Submit a request via the data access portal, approved by [team]"]

---

## Sample query

```sql
SELECT *
FROM [schema].[table_name]
LIMIT 10;
```

---

*Template: catalog_entry_template.md*
