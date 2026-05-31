# Data Catalog Standards

## What belongs in a catalog entry

A data catalog entry answers four questions anyone might ask about a table before using it:

1. **What is this?** — business purpose, entity represented
2. **Who owns it?** — accountable teams for content and technical health
3. **Can I trust it?** — freshness, completeness, known issues
4. **Can I access it?** — permissions, sensitivity, compliance

---

## Required fields

| Field | Description |
|---|---|
| Name | Fully qualified table name (schema.table) |
| Description | One sentence: what business process or entity this table represents |
| Business Owner | Team or person responsible for the data's accuracy |
| Technical Owner | Team or person responsible for the pipeline |
| Refresh frequency | How often the table is updated (real-time / hourly / daily / weekly) |
| Row count | Approximate, with date of measurement |
| Grain | What one row represents |
| Primary key | Column(s) that uniquely identify a row |

---

## Column-level documentation

For each column:

- **Name** — as it appears in the schema
- **Type** — data type
- **Description** — what it means in business terms (not just the technical name)
- **Nullable** — Yes / No
- **Keys** — PK / FK / unique constraint
- **Accepted values** — for categorical columns, list the valid values or a reference to a lookup table
- **Example values** — 2–3 realistic examples

---

## Data quality standards

**Completeness:** Percentage of non-NULL values for required fields. Flag any column with > 5% NULLs where NULLs are not expected.

**Freshness:** How stale can the data be before it causes problems? Express as a maximum acceptable lag (e.g., "data must be < 2 hours old for real-time dashboards").

**Consistency:** Are values consistent across systems? Cross-reference with the reconciliation log if known discrepancies exist.

**Known issues:** Document openly. A blank "Known issues" field is a red flag — if the table is in production, someone has found something.

---

## Lineage documentation standards

**Upstream:** Every immediate data source feeding this table (table name, system, or file). One level up is sufficient unless the table is a critical shared asset.

**Downstream:** The 5–10 most important consumers (dashboards, models, reports). Stale lineage is worse than no lineage — set a review cadence.

---

## Sensitivity and governance

| Sensitivity level | Description | Examples |
|---|---|---|
| Public | No restrictions | Aggregated, anonymised data |
| Internal | Employees only | Transaction summaries |
| Confidential | Need-to-know | Individual-level financial data |
| Restricted | Named approvals | Health data, authentication data |

**Compliance tags to record:** GDPR (if EU personal data), HIPAA (health), SOX (financial controls), CCPA (California personal data), PCI-DSS (payment card data).

---

## Maintenance cadence

- Review descriptions annually or after major schema changes
- Update row counts and freshness metrics quarterly
- Re-validate known issues after each major pipeline upgrade
- Retire entries for deprecated tables within 30 days of decommission
