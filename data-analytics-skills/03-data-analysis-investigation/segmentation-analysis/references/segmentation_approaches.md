# Segmentation Approaches — NYC DOT Reference

## When to use each method

| Method | Use when | Avoid when |
|--------|----------|------------|
| **Rule-based / risk tiers** | Business already knows the meaningful thresholds (SLA days, defect count cutoffs); stakeholders need explainable groups | Groups are genuinely unknown and data should drive discovery |
| **K-means clustering** | Exploring unknown natural groupings in behavioural data; n ≥ 100 per expected segment | Data is mostly categorical; segments need to be stable over time |
| **RFM (Recency/Frequency/Monetary)** | E-commerce or service-request data with temporal activity | Static snapshot data with no activity dimension |

## Risk-tier thresholds for sidewalk inspection data

```
defect_count per unit:
  > 66th percentile  →  HIGH RISK   (prioritise for repair)
  33rd–66th          →  MEDIUM RISK (schedule next cycle)
  < 33rd percentile  →  LOW RISK    (routine monitoring)
  null / 0 records   →  NEW/UNKNOWN (flag for baseline inspection)
```

Adjust percentile thresholds in `segmentation_engine.py` to match operational capacity.

## Silhouette score interpretation (k-means)

| Score | Interpretation |
|-------|---------------|
| > 0.70 | Strong, well-separated clusters |
| 0.50–0.70 | Reasonable structure |
| 0.30–0.50 | Weak but usable — document caveats |
| < 0.30 | Poor fit — reduce n_clusters or switch to rule-based |

## Segment naming conventions

- **Name for the dominant behaviour**, not the cluster number: "High-volume repeat violators" beats "Cluster 2".
- **Limit to 3–7 segments** — more than 7 is operationally unactionable.
- **Pair every segment with a strategic action** from: Prioritise / Schedule / Monitor / Investigate / Archive.

## NYC DOT segmentation examples

### Sidewalk units (inspection dataset)
- Variables: `defect_count`, `days_since_last_inspection`, `material_type` (encoded), `violation_count`
- Goal: prioritise field crew dispatch
- Recommended: rule-based tiers (HIGH/MED/LOW) — explainable, stable, SLA-aligned

### Ramp progress (ramp_progress dataset)
- Variables: `completion_rate`, `days_in_queue`, `borough` (encoded), `num_complaints`
- Goal: identify boroughs/units at risk of missing ramp SLA
- Recommended: k-means (k=4) if exploring; rule-based if reporting to Council

### 311 complaint clusters (complaints_311 dataset)
- Variables: `complaint_type` (encoded), `hour_of_day`, `borough`, `resolution_days`
- Goal: classify complaint types for routing
- Recommended: k-means (k=5–7) with TF-IDF on descriptor text if available
