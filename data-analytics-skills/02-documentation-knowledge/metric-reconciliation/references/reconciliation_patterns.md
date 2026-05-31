# Metric Reconciliation Patterns

## Why metrics diverge

### 1. Filter differences
The most common cause. Two queries pulling from the same table but with different WHERE clauses produce different numbers. Check: status filters, date truncation (>= vs BETWEEN), NULL handling, deleted record exclusion.

### 2. Join type mismatches
LEFT JOIN vs INNER JOIN silently adds or drops rows. A revenue figure joined LEFT to a customer table will count orders with no matching customer; INNER will drop them.

### 3. Grain mismatch
One query aggregates at order level; another at order-line level. Duplicate rows in one source inflates the total.

### 4. Time zone handling
UTC vs local time causes rows to land in different periods depending on the system. Common in global dashboards.

### 5. Definition drift
The business definition changed (e.g., "active user" now requires two sessions, not one) but not all pipelines were updated simultaneously.

### 6. Refresh lag
One source reflects yesterday's snapshot; another is near-real-time. Comparing them during an intra-day reconciliation produces a spurious gap.

---

## Reconciliation investigation sequence

1. **Confirm the numbers** — pull both values from authoritative sources, not cached dashboards.
2. **Check the grain** — what does one row represent in each source?
3. **Align the period** — are both using the same start/end boundary and time zone?
4. **Compare filters** — list all WHERE conditions side by side.
5. **Compare joins** — trace every JOIN and its type.
6. **Sample-level check** — pull 20 rows present in A but not B, and vice versa.
7. **Document the root cause** — record in `assets/reconciliation_report_template.md`.

---

## Tolerance thresholds by metric type

| Metric type | Acceptable gap | Notes |
|---|---|---|
| Financial totals (reported) | 0% | Must match exactly for audit |
| Financial totals (operational) | < 0.1% | Rounding from currency conversion |
| Marketing metrics | < 1% | Attribution window differences |
| Product engagement | < 2% | Session vs event counting differences |
| ML training labels | < 0.5% | Label leakage risk if higher |

---

## Documentation checklist after resolution

- Root cause identified (one sentence)
- Which source is designated as the single source of truth
- Whether a pipeline fix is needed, or a definition clarification
- Date the discrepancy was observed and resolved
- Whether downstream consumers need recalculation
