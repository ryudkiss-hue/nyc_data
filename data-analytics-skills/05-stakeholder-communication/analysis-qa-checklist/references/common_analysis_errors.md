# Common Analysis Errors Reference

High-frequency mistakes found across analytical work. Review this list as the last step before any delivery.

---

## Calculation Errors

### 1. Double-counting via incorrect joins
**What happens:** A LEFT JOIN to a one-to-many table inflates the row count; aggregated metrics are then overstated.  
**How to catch:** After every join, check `SELECT COUNT(*)` before and after; verify the count matches your mental model.  
**Fix:** Use `DISTINCT` on the grain key after the join, or aggregate the many-side before joining.

### 2. Wrong denominator in rate calculations
**What happens:** "Conversion rate" divides by total events when it should divide by unique visitors, or vice versa.  
**How to catch:** Print the denominator and ask: "Is this the population I want to measure against?"  
**Fix:** Define the denominator explicitly in the requirements doc before writing the query.

### 3. Null propagation surprises
**What happens:** `SUM(revenue)` silently ignores nulls; `AVG(score)` denominator excludes nulls; `revenue - cost` returns null if either is null.  
**How to catch:** Check null counts for every column used in calculations; add `COALESCE` or `IFNULL` deliberately.

### 4. Timezone mismatch
**What happens:** Events recorded in UTC are compared to dates in local time, causing off-by-one day errors in daily aggregations.  
**How to catch:** Confirm the timezone of every timestamp column; convert all to a single zone before grouping.

---

## Logical Errors

### 5. Survivorship bias
**What happens:** Analysis only looks at customers/products/users that still exist, missing churned or discontinued ones.  
**Example:** "Average tenure of active customers" excludes churned customers who had short tenures.  
**Fix:** Explicitly include the full cohort and flag what is excluded.

### 6. Confusing correlation with causation
**What happens:** A correlation between two metrics is presented as evidence that one drives the other.  
**How to catch:** Ask "could a third variable explain both?" before every causal claim.  
**Fix:** Add a caveat; recommend an experiment if causal claim is needed.

### 7. Simpson's paradox
**What happens:** A trend that appears in aggregate reverses when data is segmented (e.g., overall conversion up but down in every individual segment).  
**How to catch:** Always check key segments separately; compare to the aggregate.

### 8. Anchoring on the wrong baseline
**What happens:** A metric looks impressive vs. last week but terrible vs. last year; the chosen baseline drives the narrative.  
**Fix:** Show multiple baselines; be explicit about why the chosen baseline is the most appropriate.

---

## Communication Errors

### 9. Burying the lede
**What happens:** The key finding appears on slide 8 after five slides of methodology.  
**Fix:** State the headline finding in the first paragraph or slide; let the detail follow.

### 10. Precision theatre
**What happens:** Reporting "conversion rate: 3.847362%" when the underlying data only supports "~4%".  
**Fix:** Round to the precision warranted by sample size and measurement accuracy.

### 11. Missing the "so what"
**What happens:** The analysis describes what happened but makes no recommendation.  
**Fix:** Every finding should be paired with a recommended action or explicit statement that no action is needed.

### 12. Undocumented assumptions
**What happens:** Assumptions embedded in calculations are invisible to reviewers and stakeholders.  
**Fix:** List every assumption in a dedicated section; flag which ones have high sensitivity.
