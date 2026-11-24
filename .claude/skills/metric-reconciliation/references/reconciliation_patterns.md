# Reconciliation Patterns Reference — NYC DOT SIM

Common discrepancy patterns encountered in NYC DOT Socrata data pipelines,
with root causes and resolution steps.

---

## Pattern 1: API vs. DuckDB Cache Mismatch

**Symptom:** Live API returns 312,450 violations; local Parquet cache shows 311,980.

**Root causes (in order of likelihood):**
1. Cache is stale — last refreshed > 24 h ago and new rows arrived
2. Partial fetch — API was called with a row limit that truncated results
3. Delta fetch gap — incremental cache fetch missed rows inserted between polling windows

**Resolution:**
```bash
# Check cache age
socrata db-status

# Force full refresh
socrata cache refresh violations

# Re-run reconciliation
python reconcile.py --key violations --metric-col objectid --agg count \
    --source-a api --source-b cache:data/cache/violations.parquet
```

**Acceptable tolerance:** ≤ 0.1% for count metrics on HIGH SLA datasets.

---

## Pattern 2: Borough Rollup Discrepancy

**Symptom:** Dashboard shows MN = 48,200 violations; report says MN = 47,900.

**Root causes:**
1. Borough normalization differs — dashboard uses `upper(borough) = 'MANHATTAN'`;
   report uses borough code `'MN'`
2. NULL borough rows — some records have null borough and are excluded in one source but
   counted as "unknown" in another
3. Date filter boundary — one source uses `>=` and the other uses `>`

**Resolution:**
- Standardize on borough codes (MN/BX/BK/QN/SI) across all queries
- Decide on null borough treatment upfront and document it
- Use ISO 8601 timestamps with explicit time components to avoid boundary ambiguity:
  ```
  created_date >= '2026-05-01T00:00:00' AND created_date < '2026-06-01T00:00:00'
  ```

---

## Pattern 3: Status Filter Drift

**Symptom:** Open violation count from CLI ≠ open violation count from dashboard.

**Root causes:**
1. Dashboard filters on `status = 'OPEN'`; CLI doesn't filter status at all
2. A new status value (`'IN PROGRESS'`) was added to the schema after dashboard was built
3. Case sensitivity — `'Open'` vs. `'OPEN'`

**Resolution:**
- Document the canonical set of "open" statuses: `OPEN`, `IN PROGRESS`, `PENDING`
- Add explicit status filter to all queries; use `upper(status) IN (...)` for safety
- Run `query-validation` skill on affected queries

---

## Pattern 4: Ramp Completion Rate Discrepancy

**Symptom:** Borough completion rates differ between two reports by > 2%.

**Root causes:**
1. Denominator definition — total ramps vs. eligible ramps vs. funded ramps
2. Completion definition — `status = 'COMPLETED'` vs. `completion_date IS NOT NULL`
3. Stale `ramp_locations` dataset — known stale since 2021; using it as denominator
   inflates the true count of locations

**Resolution:**
- Always use `ramp_progress` (not `ramp_locations`) as the primary source
- Denominator = total rows in `ramp_progress` where `status != 'CANCELLED'`
- Numerator = rows where `status = 'COMPLETED'`
- Document Wilson Score CI as the uncertainty band, not the raw rate

---

## Pattern 5: Timing Lag (Extract vs. Report Time)

**Symptom:** Monday morning report shows fewer records than Friday afternoon extract.

**Root causes:**
1. Weekend processing at source — NYC Open Data pipelines may batch-process on weekends
2. Report generated before nightly scheduler ran
3. ETL lag — records processed in source system before hitting Socrata

**Resolution:**
- Always record and display the extract timestamp alongside the metric
- For time-sensitive metrics, fetch fresh from API at report time
- Add "Data as of: {{extract_timestamp}}" to every report output

---

## Reconciliation Decision Matrix

| Discrepancy % | Action |
|---|---|
| 0% | No action — sources agree |
| < tolerance (default 0.5%) | Document and accept — within operational noise |
| tolerance – 5× tolerance | INVESTIGATE — identify root cause before proceeding |
| > 5× tolerance | CRITICAL — halt report; do not publish until resolved |

---

## Standard Comparison Grains

| Analysis Type | Recommended Group-By | Join Key |
|---|---|---|
| Borough rollup | borough | borough code |
| Daily trend | inspection_date (date part) | date |
| Status breakdown | status | status |
| Monthly summary | year_month (truncated date) | year_month |
