# Query Review — {{query_name}}

**Reviewed:** {{review_date}}
**Reviewer:** {{reviewer_name}}
**Target engine:** {{engine}}
**Purpose:** {{query_purpose}}

---

## Query Under Review

```sql
{{query_text}}
```

---

## Verdict: {{verdict}}

| Dimension | Status | Issues Found |
|---|---|---|
| Syntax | {{syntax_status}} | {{syntax_issue_count}} |
| Correctness | {{correctness_status}} | {{correctness_issue_count}} |
| Performance | {{performance_status}} | {{perf_issue_count}} |
| Style | {{style_status}} | {{style_issue_count}} |

---

## Findings

### Critical (must fix before promotion)

| # | Finding | Location | Recommendation |
|---|---|---|---|
| 1 | {{critical_1_finding}} | {{critical_1_location}} | {{critical_1_fix}} |

### Major (fix before next release)

| # | Finding | Location | Recommendation |
|---|---|---|---|
| 1 | {{major_1_finding}} | {{major_1_location}} | {{major_1_fix}} |

### Minor (backlog)

| # | Finding | Location | Recommendation |
|---|---|---|---|
| 1 | {{minor_1_finding}} | {{minor_1_location}} | {{minor_1_fix}} |

---

## Correctness Checks

- [ ] Join type is correct (INNER vs LEFT vs FULL OUTER)
- [ ] All non-aggregated SELECT columns appear in GROUP BY
- [ ] Date comparisons use ISO 8601 format (Socrata) or explicit CAST (DuckDB)
- [ ] Borough filter uses `upper(borough)` or normalized values
- [ ] NULL handling is explicit (COALESCE, IS NOT NULL) where needed
- [ ] `NOT IN` subqueries replaced with `NOT EXISTS` if subquery may return NULLs
- [ ] Row limit present on queries touching datasets > 50K rows

---

## Performance Notes

**Estimated row count:** {{estimated_rows}}
**EXPLAIN output:** {{explain_notes}}

| Concern | Severity | Recommendation |
|---|---|---|
| Full table scan | {{fts_severity}} | {{fts_recommendation}} |
| Missing index | {{index_severity}} | {{index_recommendation}} |
| Sort spill | {{sort_severity}} | {{sort_recommendation}} |

---

## Revised Query (if changes needed)

```sql
{{revised_query}}
```

---

## Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Reviewer | {{reviewer_name}} | {{review_date}} | {{decision}} |
| Author | | | |

*Reviewed using `query-validation/scripts/sql_lint.py`. Anti-pattern reference: `references/sql_anti_patterns.md`.*
