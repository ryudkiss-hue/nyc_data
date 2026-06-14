# Common Analysis Errors — NYC DOT SIM Toolkit

Reference guide for analysis-type-specific mistakes. Review the section matching your analysis type before delivery.

---

## Borough-Level Comparisons

**Ecological fallacy** — Drawing conclusions about individual inspection sites from borough-level aggregates.
- Wrong: "Manhattan has the highest completion rate, so Manhattan inspectors are more productive."
- Right: "Manhattan's borough-level rate is highest; site-level variation within Manhattan is not captured here."

**Population size confounding** — Staten Island's small absolute counts can produce extreme rates (100% or 0%) with small samples.
- Fix: Always report n alongside rates; apply Wilson Score CI; flag reliability as "low" when n < 30.

**Missing borough = no data vs. filtered out** — A missing borough in results could mean zero matching records OR that the borough was excluded by a filter.
- Fix: Run an unfiltered count by borough first; explicitly note "BX had 0 records matching this filter" vs. "BX was excluded from analysis."

---

## Time-Series & Trend Analysis

**Survivorship bias in inspections** — Closed or resolved records may drop out of the dataset, making active caseloads appear smaller over time.
- Affected datasets: `violations` (resolved violations archived), `ramp_progress` (completed ramps)
- Fix: Use a snapshot approach or filter for status = active vs. all statuses.

**Day-of-week effects** — Inspection volumes are lower on weekends. Weekly totals are safer than daily comparisons.

**Data lag masking recent trends** — `inspection` and `violations` update daily but with a 1–3 day lag. Avoid reporting "this week's" numbers as current.

**Comparing different base periods** — Q2 FY2025 vs. Q2 FY2024 is valid. Q2 vs. Q1 is confounded by seasonality (winter reduces fieldwork).

---

## Rate & Percentage Calculations

**Double-counting from joins** — Joining `inspection` to `ramp_progress` on a non-unique key can multiply rows.
- Fix: Check row count before and after join; should never exceed the larger table.

**Percentage vs. decimal confusion** — `completion_rate = 0.72` means 72%. If displayed as 72.0 without a % sign, readers may think it's 72 out of 100 possible points.
- Fix: Always include the `%` symbol or label the column "Completion Rate (%)".

**Denominator choice matters** — "Completion rate" for ramps: denominator could be total ramps ever identified, ramps currently in progress, or ramps scheduled for this fiscal year. Each produces a different number.
- Fix: Define denominator explicitly in the analysis brief and every output.

---

## Spatial / Geospatial Analysis

**Coordinate reference system mismatch** — NYC DOT data uses WGS84 (lat/lng); buffer distances calculated in degrees, not feet.
- Fix: Project to EPSG:2263 (NY State Plane, feet) before computing buffers.

**Conflict detection false positives** — A 50-foot buffer around a street permit will overlap inspection sites on adjacent streets, not just the permitted block.
- Fix: Verify spatial joins with a sample of flagged conflicts on a map before reporting counts.

**Null geometries** — Some `inspection` records have null `the_geom`. They are silently excluded from spatial joins.
- Fix: Report null geometry count; determine if exclusion biases borough representation.

---

## Quality Score Analysis

**Score denominator shift** — Quality scores (0–100 composite: 35% completeness, 25% validity, 25% consistency, 15% freshness) will drop when a new column is added to the dataset (more null opportunities). Report score changes with dataset schema version.

**Freshness component decay** — A dataset that was fresh last week will score lower today even with no data change. Cache the score date alongside the score.

---

## A/B Tests & Statistical Claims

**Multiple comparison inflation** — Testing completion rates for 5 boroughs simultaneously inflates Type I error. Use Bonferroni correction or report uncorrected p-values with a note.

**Small n in borough subsets** — Staten Island (SI) frequently has n < 50 for specific violation types. A two-proportion z-test is invalid below n=30 per group; use Fisher's exact test.

**Confusing statistical significance with practical significance** — A difference of 0.3 pp in completion rate may be statistically significant with n=100K but operationally irrelevant.
