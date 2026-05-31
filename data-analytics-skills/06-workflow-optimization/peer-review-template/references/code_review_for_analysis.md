# Code Review Guide for Analysis Work

Checklist and guidance for reviewing SQL, Python, and notebooks used in analytical work. Analytical code has different priorities from production software — correctness and reproducibility matter most.

---

## Priority Order for Analytical Code Reviews

1. **Correctness** — does it produce the right answer?
2. **Reproducibility** — can someone else run it and get the same result?
3. **Readability** — can someone understand what it does?
4. **Performance** — does it run in reasonable time?
5. **Style** — cosmetic preferences (lowest priority)

---

## SQL Review Checklist

### Correctness
- [ ] Join types are intentional: INNER (drops unmatched rows), LEFT (keeps all from left), FULL (keeps all)
- [ ] Aggregation grain is correct — what does one row represent after the final GROUP BY?
- [ ] No unintentional fan-out from one-to-many joins
- [ ] Null handling is explicit: `COALESCE`, `NULLIF`, or intentional exclusion
- [ ] Date/timestamp arithmetic is correct; timezone handling is consistent
- [ ] Filters in WHERE vs. JOIN ON are placed intentionally
- [ ] Window functions use the correct PARTITION BY and ORDER BY
- [ ] `DISTINCT` is used intentionally, not to mask a join problem

### Reproducibility
- [ ] All CTEs or subqueries are named clearly
- [ ] No hardcoded dates that will silently become wrong later (use parameters or relative dates)
- [ ] Source tables are fully qualified (schema.table)
- [ ] Any sampling is seeded for reproducibility

### Performance
- [ ] No `SELECT *` in production queries
- [ ] Filters are applied early (not after an expensive join)
- [ ] No functions applied to indexed columns in WHERE clauses
- [ ] Large cross-joins are justified

---

## Python / Notebook Review Checklist

### Correctness
- [ ] Pandas/Polars operations produce the expected output — spot-check with `print()` / `assert`
- [ ] Merge/join keys are verified before and after the merge
- [ ] Index is reset after filtering; no accidental use of stale indexes
- [ ] Null handling is explicit (`dropna`, `fillna`, or intentional inclusion)
- [ ] Off-by-one errors in date ranges checked
- [ ] Random seeds set for any shuffling, sampling, or model training

### Reproducibility
- [ ] A notebook can be run top-to-bottom in a clean kernel and produce the same result
- [ ] No inline manual corrections ("I just changed this cell to fix the number")
- [ ] Data inputs are versioned or pinned (specific date, snapshot)
- [ ] Library versions that matter are noted (e.g. scikit-learn, statsmodels)

### Readability
- [ ] Variable names describe content (`churn_rate_by_segment`, not `df3`)
- [ ] Long cells are broken into logical steps
- [ ] Magic numbers are replaced with named constants
- [ ] Functions are used for repeated operations

---

## Common Analytical Code Bugs

| Bug | How to spot it |
|---|---|
| Row count explodes after a join | Check `len(df)` before and after; or `COUNT(*)` at each CTE |
| Metric is `None` / `NaN` unexpectedly | Check for nulls in the columns used for the calculation |
| Percentage > 100% | Wrong denominator; check the divisor |
| Negative count or rate | Check for double-subtraction or wrong sign |
| Duplicate rows in final output | Check for missing DISTINCT or GROUP BY |
| Wrong time period included | Print the min/max date after applying date filters |
