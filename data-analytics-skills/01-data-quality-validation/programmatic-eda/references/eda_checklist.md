# EDA Checklist (40-Item)

Work through this list before declaring a dataset "profiled." Tick each item; note findings inline.

## 1. Data Loading & Structure
- [ ] File loaded without errors (encoding, delimiter, schema issues noted)
- [ ] Row count confirmed and plausible for the expected population
- [ ] Column count matches expected schema documentation
- [ ] Column names are unambiguous (no unnamed columns, no duplicated names)
- [ ] Grain is identified: what does one row represent?
- [ ] Primary key / unique identifier identified and verified as unique
- [ ] Data types are correct for each column (dates as dates, IDs as strings, etc.)
- [ ] Multi-file joins (if applicable) executed without fan-out (row count inflation)

## 2. Completeness
- [ ] Null counts reviewed for every column
- [ ] Null % compared against thresholds (see `quality_thresholds.md`)
- [ ] Columns with >30% nulls flagged and business justification confirmed
- [ ] Structural zeros (0 vs null) verified — are zeros meaningful or stand-ins for missing?
- [ ] Optional columns have documented expected null rate

## 3. Uniqueness & Duplicates
- [ ] Full-row duplicates checked
- [ ] Key-level duplicates checked (same entity_id appearing multiple times)
- [ ] Partial duplicates investigated (same ID, different timestamps — intentional versioning?)
- [ ] Duplicate rate below 1% or business explanation documented

## 4. Validity
- [ ] Numeric columns within plausible business range (e.g. age 0–120, revenue >= 0)
- [ ] Categorical columns have expected value set (no unexpected categories)
- [ ] Date columns within expected range (no future dates, no dates before system launch)
- [ ] Referential integrity: foreign keys join without orphans (or orphan rate is documented)
- [ ] Boolean columns contain only True/False/null (not 0/1/Y/N mix without mapping)

## 5. Distributions
- [ ] Numeric columns: descriptive stats (mean, median, std, p5, p95) reviewed
- [ ] Skewness flag: |skew| > 2 noted for potential transformation before modeling
- [ ] Outliers reviewed via IQR and z-score; each flagged value is real data or error
- [ ] Categorical distributions reviewed: no single category dominates unexpectedly (>90%)
- [ ] Date distribution: is coverage continuous or are there unexpected gaps?

## 6. Correlations & Relationships
- [ ] Pairwise correlations computed for numeric columns
- [ ] Strong pairs (|r| ≥ 0.8) flagged and explained (multicollinearity risk noted)
- [ ] Known business relationships confirmed (e.g. revenue should correlate with orders)
- [ ] Surprising zero-correlations investigated (might indicate a filtering problem)

## 7. Time-Series Integrity (if applicable)
- [ ] Time column is monotonically increasing or gaps are documented
- [ ] Recency: most recent record is within expected lag
- [ ] Volume by time period reviewed for sudden drops (pipeline outage) or spikes (data backfill)
- [ ] Weekend/holiday effects noted if data is daily

## 8. Business Logic Checks
- [ ] Revenue/profit margin relationship is directionally correct
- [ ] Derived columns (computed from other columns) verified against source columns
- [ ] Segment totals sum to expected aggregate (reconciliation check)
- [ ] Known data issues or pipeline quirks from the data team are documented

## 9. Sign-off
- [ ] All FAIL-threshold items resolved or risk-accepted with business owner
- [ ] WARN-threshold items noted in `assets/findings_summary.md`
- [ ] EDA report (`assets/eda_report_template.md`) is completed
- [ ] Next analysis step confirmed (ready to proceed / needs data fix first)
