# SQL Anti-Patterns Reference

Each entry: what the pattern is, why it's a problem, and the preferred alternative.

---

## Correctness Anti-Patterns

### 1. Implicit type conversion in JOIN / WHERE
```sql
-- Bad: comparing VARCHAR id to INT — engine may cast every row
WHERE user_id = 12345

-- Good: match the column type explicitly
WHERE user_id = '12345'
```
**Risk:** Silent mis-joins or full table scans if the cast prevents index use.

---

### 2. NULL comparison without IS NULL
```sql
-- Bad: always false — NULL ≠ anything including NULL
WHERE cancelled_at = NULL

-- Good
WHERE cancelled_at IS NULL
```

---

### 3. Aggregate without GROUP BY (or wrong grain)
```sql
-- Bad: mixing aggregate and non-aggregate without grouping
SELECT user_id, SUM(revenue)
FROM orders
-- Missing: GROUP BY user_id
```

---

### 4. Fan-out from many-to-many JOIN
```sql
-- Bad: users joined to two non-unique tables inflates row count
SELECT u.id, SUM(o.revenue)
FROM users u
JOIN orders o ON u.id = o.user_id
JOIN refunds r ON u.id = r.user_id  -- refunds also non-unique per user
GROUP BY u.id
-- Revenue will be over-counted if a user has multiple refunds
```
**Fix:** Aggregate one side first before joining, or use DISTINCT carefully.

---

### 5. NOT IN with a subquery that can return NULL
```sql
-- Bad: if the subquery returns any NULL, NOT IN returns no rows
WHERE user_id NOT IN (SELECT user_id FROM churned_users)

-- Good: use NOT EXISTS or filter NULLs in the subquery
WHERE NOT EXISTS (
  SELECT 1 FROM churned_users c WHERE c.user_id = u.user_id
)
```

---

### 6. USING instead of ON for ambiguous joins
```sql
-- Risky in multi-dialect environments — stick to ON for portability
JOIN orders USING (user_id)

-- Preferred
JOIN orders o ON u.id = o.user_id
```

---

## Performance Anti-Patterns

### 7. SELECT *
```sql
-- Bad: pulls all columns including large/unused ones
SELECT * FROM events

-- Good: enumerate what you need
SELECT user_id, event_type, occurred_at FROM events
```

---

### 8. Function on a column in WHERE (prevents index use)
```sql
-- Bad: CAST forces a full scan in most engines
WHERE CAST(created_at AS DATE) = '2024-01-01'

-- Good: use a range on the original type
WHERE created_at >= '2024-01-01' AND created_at < '2024-01-02'
```

---

### 9. Correlated subquery in SELECT
```sql
-- Bad: executes the subquery once per row
SELECT u.id,
  (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count
FROM users u

-- Good: pre-aggregate and JOIN
SELECT u.id, COALESCE(agg.order_count, 0)
FROM users u
LEFT JOIN (SELECT user_id, COUNT(*) AS order_count FROM orders GROUP BY user_id) agg
  ON u.id = agg.user_id
```

---

### 10. Unbounded CROSS JOIN / missing join condition
```sql
-- Bad: Cartesian product — M × N rows
SELECT * FROM dimension_a, dimension_b

-- Always use explicit JOIN ... ON
```

---

### 11. ORDER BY in a CTE or subquery
```sql
-- Bad: ORDER BY inside a CTE is usually ignored and wastes resources
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (...) rn FROM events ORDER BY occurred_at
)
-- The ORDER BY in the CTE is discarded; apply it in the outer query if needed
```

---

### 12. DISTINCT as a crutch for fan-out
```sql
-- Bad: DISTINCT is hiding a join that produces duplicates
SELECT DISTINCT u.id FROM users u JOIN events e ON u.id = e.user_id

-- Better: understand and fix the join; or use EXISTS
SELECT u.id FROM users u WHERE EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.id)
```

---

## Style Anti-Patterns (lower severity)

### 13. Unqualified column references in multi-table queries
Always prefix `table.column` or use CTE aliases — avoids ambiguity errors when schemas change.

### 14. Magic numbers in WHERE / CASE
```sql
-- Bad
WHERE status = 3

-- Good: use named constants or comment the meaning
WHERE status = 3  -- 3 = 'churned'
```

### 15. Deeply nested subqueries > 3 levels
Refactor into CTEs for readability and debuggability.
