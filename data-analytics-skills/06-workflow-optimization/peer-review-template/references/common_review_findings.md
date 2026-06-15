# Common Review Findings in SIM Analytics

A reference of issues that appear repeatedly in NYC DOT SIM analyses.
Reviewers should check for these first; they account for ~80% of findings.

---

## Category 1 — Statistical errors

### Finding: Normal approximation CI used instead of Wilson Score
**Pattern:** `rate ± 1.96 * sqrt(p*(1-p)/n)` in code or narrative
**Why it matters:** For small boroughs (SI often n<50 in monthly cuts), normal CI is wildly incorrect and can produce negative lower bounds.
**Fix:** Use `proportion_confint(count, n, method='wilson')` from `statsmodels.stats.proportion` or the toolkit's built-in Wilson CI.
**Review note:** "must-fix — Wilson CI required per team standard"

### Finding: n= missing from borough breakdown table
**Pattern:** Table shows `[borough, rate%]` without count column
**Why it matters:** Reader cannot assess reliability; SI with n=12 looks identical to MN with n=2,400.
**Fix:** Add `n` column immediately after `borough`; flag rows where n < 30 with an asterisk footnote.

### Finding: Join fan-out inflating counts
**Pattern:** Two datasets joined on a non-unique key; row count in output exceeds expected maximum
**Why it matters:** Produces double- or triple-counted rows; rates and totals are wrong.
**Fix:** Check uniqueness of join key with `SELECT objectid, COUNT(*) FROM ... GROUP BY objectid HAVING COUNT(*) > 1`. Add DISTINCT or pre-aggregate.
**Review note:** "must-fix — verify join key uniqueness before joining"

---

## Category 2 — Data access errors

### Finding: ramp_locations used instead of ramp_progress
**Pattern:** Code references `ufzp-rrqu` or `ramp_locations`
**Why it matters:** ramp_locations has not been updated since 2021; all ramp status data will be 5+ years stale.
**Fix:** Replace with `ramp_progress` (e7gc-ub6z).

### Finding: Borough code fan-out in GROUP BY
**Pattern:** Query groups by `borough` without normalization; result has rows for 'MANHATTAN', 'Manhattan', 'MN', and 'manhattan'
**Why it matters:** Counts are split across variants; borough totals are wrong.
**Fix:**
```sql
SELECT
  CASE
    WHEN upper(trim(borough)) IN ('MN', 'MANHATTAN') THEN 'MN'
    WHEN upper(trim(borough)) IN ('BX', 'BRONX')     THEN 'BX'
    WHEN upper(trim(borough)) IN ('BK', 'BROOKLYN')  THEN 'BK'
    WHEN upper(trim(borough)) IN ('QN', 'QUEENS')    THEN 'QN'
    WHEN upper(trim(borough)) IN ('SI', 'STATEN ISLAND') THEN 'SI'
    ELSE 'UNKNOWN'
  END AS borough_code,
  COUNT(*) AS n
FROM ...
GROUP BY 1
```

### Finding: Relative date in SOQL WHERE clause
**Pattern:** `WHERE created_date > 'last 30 days'` or similar non-ISO string
**Why it matters:** Socrata SOQL requires ISO 8601 timestamps; relative dates may silently return no rows or produce API errors.
**Fix:** Use absolute ISO 8601: `created_date > '2026-05-14T00:00:00'`

### Finding: Full-corpus fetch without token
**Pattern:** `fetch_dataframe` called with no `$where` filter on a dataset with >50K rows, and SOCRATA_APP_TOKEN is unset
**Why it matters:** Socrata returns max 2,000 rows silently; analysis appears to complete but is based on a 2K truncated sample.
**Fix:** Either set token, or add explicit `$where` filter to limit rows, and document sample size.

---

## Category 3 — Presentation errors

### Finding: Rate reported without data freshness date
**Pattern:** "Brooklyn completion rate: 71.3%" with no date context
**Fix:** Add footer: "Data as of: [last_modified from dataset metadata]"

### Finding: "Zero violations" vs "no data for this period"
**Pattern:** Borough shows 0 in table; reader assumes no violations, but actual cause is empty filter result
**Fix:** Distinguish with a note: "0 rows matched filter" vs "0 violations found in matching rows"

### Finding: Mixed precision in rate column
**Pattern:** One row shows "73%" another shows "73.4%" another shows "0.734"
**Fix:** Standardize: all rates as 1 decimal percentage string (e.g. "73.4%")

---

## Anti-patterns to call out explicitly in review

These are patterns that are technically "working" but produce misleading results:

1. **Reporting rates without noting sample size** — always a must-fix
2. **Using `capital_blocks` (empty dataset)** — silently returns 0 rows
3. **Comparing across time windows of different length** (e.g. Q4 has 92 days, Q1 has 90) without normalizing
4. **Using `weekly_construction` for current construction data** — data is from 2017
5. **Excluding NULL borough rows without noting the exclusion** — can make citywide totals wrong
