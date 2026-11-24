# Root Cause Analysis Framework — NYC DOT SIM

Structured methodology for diagnosing unexpected metric changes in sidewalk inspection and ramp workflows.

---

## RCA Decision Tree

```
METRIC MOVED SIGNIFICANTLY?
│
├── NO (within ±2σ of rolling average)
│   └── Not a real signal. Document and close. No RCA needed.
│
└── YES
    │
    ├── [Step 1] DATA QUALITY CHECK
    │   ├── Is the data pipeline current? (check last_modified vs. today)
    │   ├── Are there unusual null rates in key columns?
    │   ├── Are row counts as expected? (check dataset health)
    │   └── If data issue found → fix data, re-measure, then RCA if change persists
    │
    ├── [Step 2] TIMING ANALYSIS
    │   ├── Sudden shift (single period) → likely external event or system change
    │   ├── Gradual trend → likely structural/capacity or seasonal
    │   └── Reverting pattern → likely one-time event or data artifact
    │
    ├── [Step 3] METRIC DECOMPOSITION
    │   Formula: Overall Rate = Σ (segment_rate × segment_weight)
    │   ├── Decompose: borough, defect_type, material_type, unit_id
    │   ├── Which segments changed most vs. baseline?
    │   └── Are segment weights (mix) changing, or rates within segments?
    │
    ├── [Step 4] DIMENSION DRILLDOWN
    │   ├── Rank segments by: |change| × weight = weighted contribution
    │   ├── Investigate top 3 contributors
    │   └── Correlate timing with known events (see hypothesis_testing_guide.md)
    │
    └── [Step 5] HYPOTHESIS VALIDATION
        ├── State hypothesis as falsifiable claim
        ├── Test against data (correlation, before/after comparison)
        └── Document: supported / not supported / inconclusive
```

---

## NYC DOT Metric Decomposition Map

| Primary Metric | Component A | Component B | Segment Dimensions |
|---|---|---|---|
| Completion rate | Completed count | Total inspections | Borough, unit_id, defect_type |
| Violation rate | Violations issued | Inspections conducted | Borough, material_type |
| SLA compliance | Records within SLA | Total closed records | Borough, SLA tier |
| Ramp completion | Completed ramps | Total ramps in scope | Borough, ramp type |
| Resolution rate | Violations resolved | Violations issued | Borough, violation severity |

---

## Mix Effect vs. Rate Effect

When an aggregate rate changes, it can be driven by:

1. **Rate effect** — the rate within a segment genuinely changed
   - Example: Bronx completion rate dropped from 72% to 62%

2. **Mix effect** — the composition of segments shifted
   - Example: High-defect Bronx records make up a larger share this period

```python
# Detect mix vs. rate effect
# Fix weights at baseline, apply current rates:
mix_adjusted = sum(current_rate[seg] * baseline_weight[seg] for seg in segments)
# If mix_adjusted ≈ current_overall → mostly rate effect
# If mix_adjusted ≈ baseline_overall → mostly mix effect
```

---

## Sigma Thresholds for NYC DOT Metrics

| Metric | Normal Variance (σ) | Flag Threshold (2σ) | Investigate (3σ) |
|---|---|---|---|
| Completion rate (monthly) | ~2–3 pp | ±5 pp | ±7 pp |
| SLA breach rate (monthly) | ~2–4 pp | ±6 pp | ±9 pp |
| Ramp completion rate (borough) | ~3–5 pp | ±8 pp | ±12 pp |
| Violation rate | ~3–4 pp | ±7 pp | ±10 pp |

_These are estimates. Calculate actual σ from your historical baseline._

---

## Evidence Quality Levels

| Level | Description | Example |
|---|---|---|
| Confirmed | Causal chain fully traceable | System outage log + metric drop exactly aligned |
| Supported | Strong correlation + plausible mechanism | Inspector headcount drop + proportional completion rate drop |
| Plausible | Hypothesis fits data, not yet verified | Winter weather + outdoor inspection drop |
| Speculative | No supporting data, logical only | "Maybe there was a policy change" |

Only escalate findings rated **Supported** or better.

---

## RCA Time Budget

| Phase | Time | Output |
|---|---|---|
| Change validation + timing | 30 min | Confirmed: real signal, when it started |
| Metric decomposition | 45 min | Top 3 contributing dimensions |
| Hypothesis generation | 30 min | 3–5 falsifiable hypotheses, prioritised |
| Hypothesis testing | 60 min | Each hypothesis: supported / not supported |
| Report drafting | 30 min | Filled `rca_report_template.md` |
| **Total** | **~3 hours** | Evidence-based findings, tiered recommendations |
