# Query Optimization Recommendations: [Query Name]

**Date:** [YYYY-MM-DD]  
**Original runtime:** [e.g. 45 s]  
**Target runtime:** [e.g. < 5 s]

---

## Priority 1 — [High-impact fix title]

**Problem:** [What is the bottleneck — e.g. full table scan on 500M row table]  
**Root cause:** [e.g. WHERE clause applies a function to the partition column, preventing pruning]  
**Recommendation:**

```sql
-- Before
WHERE DATE(created_at) = '2024-01-01'

-- After
WHERE created_at >= '2024-01-01' AND created_at < '2024-01-02'
```

**Expected impact:** [e.g. Scan reduced from 500M rows to ~1.4M rows — runtime ~30× faster]  
**Risk:** [Low / Medium — semantically equivalent for non-NULL values]

---

## Priority 2 — [Second fix title]

**Problem:**  
**Root cause:**  
**Recommendation:**

```sql
-- Before

-- After

```

**Expected impact:**  
**Risk:**

---

## Priority 3 — [Third fix title]

**Problem:**  
**Root cause:**  
**Recommendation:**  
**Expected impact:**  
**Risk:**

---

## Changes NOT Recommended

| Suggestion | Why skipped |
|---|---|
| [e.g. Pre-aggregate events into a summary table] | [Would require pipeline change — out of scope for this review] |

---

## Benchmark Results (after fixes)

| Version | Runtime | Bytes scanned | Notes |
|---|---|---|---|
| Original | | | |
| After Priority 1 fix | | | |
| After all fixes | | | |
