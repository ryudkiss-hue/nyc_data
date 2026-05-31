# Query Documentation

**Query name:** [descriptive name]
**Owner:** [name / team]
**Date:** [YYYY-MM-DD]
**Location:** [link to file or BI tool]

---

## Business purpose

[One sentence: what business question does this query answer?]

**Used by:** [dashboard name / report / downstream model]
**Audience:** [team or role that consumes this]

---

## Plain-language explanation

### What is being calculated (SELECT)

- [Column 1 — business meaning]
- [Column 2 — business meaning]
- [Column 3 — aggregation: e.g., "Sum of revenue from completed orders"]

### Data source (FROM)

- Start with: [table name and what it represents]
- Joined with: [table and join type — e.g., "LEFT JOIN customers — keeps all orders, even those with no customer match"]

### Filters applied (WHERE)

- [Filter 1 — e.g., "status equals 'completed'"]
- [Filter 2 — e.g., "order_date on or after 2024-01-01"]

### Grouping (GROUP BY)

- [Grouping dimension — e.g., "Calculate separately for each month and region"]

### Sorting (ORDER BY)

- [Sort description — e.g., "Most recent month first"]

---

## SQL

```sql
-- [query name]
-- Owner: [name]  |  Last updated: [YYYY-MM-DD]

SELECT
    [col1],
    [col2],
    [aggregation]
FROM [table]
[JOIN type] [table2] ON [condition]
WHERE [filter conditions]
GROUP BY [dimensions]
ORDER BY [sort];
```

---

## Key assumptions

| Assumption | Confidence | Impact if wrong |
|---|---|---|
| [e.g., NULL in cancelled_at means not cancelled] | High / Medium / Low | Low / Medium / High |

---

## Validation questions

- [ ] Are filter conditions correct for the intended population?
- [ ] Does the GROUP BY grain match what one row should represent?
- [ ] Are NULL values handled explicitly in aggregations?
- [ ] Has the result been cross-checked against another source?

---

## Change log

| Date | Author | Change |
|---|---|---|
| [YYYY-MM-DD] | [name] | [what changed and why] |

---

*Template: query_documentation_template.md*
