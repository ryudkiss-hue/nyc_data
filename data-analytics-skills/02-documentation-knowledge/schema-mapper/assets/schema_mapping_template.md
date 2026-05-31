# Schema Mapping Document

**Project:** [project or migration name]
**Source system:** [system name / table]
**Target system:** [system name / table]
**Analyst:** [name]
**Date:** [YYYY-MM-DD]
**Version:** [1.0]

---

## Overview

**Purpose of mapping:** [Why this mapping is being created — migration, integration, new data model]
**Total source columns:** [n]
**Total target columns:** [n]
**Direct matches:** [n]
**Requiring transformation:** [n]
**Target columns with no source:** [n]

---

## Column mapping

| Source column | Source type | Target column | Target type | Transformation | Notes |
|---|---|---|---|---|---|
| source.col_a | VARCHAR | target.col_a | VARCHAR | Direct | — |
| source.col_b | INTEGER | target.amount_usd | DECIMAL | `col_b / 100.0` | Convert cents to dollars |
| source.first_name + last_name | VARCHAR | target.full_name | VARCHAR | `CONCAT(first_name, ' ', last_name)` | — |
| source.col_c | TIMESTAMP | target.event_date | DATE | `DATE(col_c)` | Time component dropped |
| — | — | target.created_at | TIMESTAMP | `CURRENT_TIMESTAMP` | System-generated on insert |
| source.legacy_flag | BOOLEAN | *(dropped)* | — | Not included in target | Deprecated |

---

## Unmapped target columns (need derivation or default)

| Target column | Type | Derivation plan | Owner | Status |
|---|---|---|---|---|
| [column] | [type] | [how to populate] | [owner] | [open/resolved] |

---

## Type mismatch summary

| Column | Source type | Target type | Required CAST | Risk |
|---|---|---|---|---|
| [column] | [type] | [type] | `CAST(col AS target_type)` | [truncation / precision loss / format error] |

---

## Validation rules

| Target column | Rule | Test query |
|---|---|---|
| [column] | NOT NULL | `SELECT COUNT(*) FROM target WHERE col IS NULL` |
| [column] | Value in accepted set | `SELECT DISTINCT col FROM target WHERE col NOT IN ('a','b','c')` |
| [column] | Referential integrity | `SELECT * FROM target t LEFT JOIN dim d ON t.fk = d.pk WHERE d.pk IS NULL` |

---

## Sign-off

| Role | Name | Date | Status |
|---|---|---|---|
| Source data owner | | | |
| Target schema owner | | | |
| Engineering lead | | | |
| Analytics reviewer | | | |

---

*Template: schema_mapping_template.md*
