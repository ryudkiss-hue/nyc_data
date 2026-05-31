# Data Quality Scorecard: [Dataset / Table Name]

**Assessed by:** [Name]  
**Date:** [YYYY-MM-DD]  
**Table / dataset:** [schema.table_name or file path]  
**Pipeline / source:** [data source and ingestion frequency]  
**Assessment scope:** [full table / sample of N rows / specific date range]

---

## Quality Dimension Scores

Rate each dimension 0–10 based on check results. See `references/quality_dimensions.md` for scoring guide.

| Dimension | Weight | Score (0–10) | Weighted | Key Issues |
|---|---|---|---|---|
| Completeness | 20% | | | |
| Accuracy | 20% | | | |
| Consistency | 20% | | | |
| Timeliness | 15% | | | |
| Uniqueness | 15% | | | |
| Validity | 10% | | | |
| **Overall** | **100%** | | **/10** | |

**Overall verdict:** PASS (≥ 7.0) / CONDITIONAL (5.0–6.9) / FAIL (< 5.0)

---

## Critical Findings (must fix before production use)

| # | Dimension | Finding | Rows affected | Impact |
|---|---|---|---|---|
| 1 | | | | |

## High Severity (fix within 5 business days)

| # | Dimension | Finding | Rows affected | Impact |
|---|---|---|---|---|
| 1 | | | | |

## Medium / Low (document and monitor)

| # | Dimension | Finding | Notes |
|---|---|---|---|
| 1 | | | |

---

## Checks Performed

| Check | Script | Result | Details |
|---|---|---|---|
| Null audit | `null_counter.py` | PASS / FAIL | N columns exceed threshold |
| Duplicate detection | `duplicate_finder.py` | PASS / FAIL | N duplicate rows found |
| Referential integrity | `referential_integrity.py` | PASS / FAIL | N orphan records |
| Value range validation | `value_range_validator.py` | PASS / FAIL | N rule violations |
| Freshness | `freshness_check.py` | PASS / FAIL | Lag: Xh (SLA: Yh) |

---

## Sign-off

**Approved for use in:** [dashboards / reports / ML features / all uses / none — pending fix]

**Approver:** [Name]  
**Review date:** [Next audit scheduled for YYYY-MM-DD or "on next pipeline update"]

**Action items:**

| Action | Owner | Due date | Status |
|---|---|---|---|
| Fix [issue] | [team] | [date] | Open |
