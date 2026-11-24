# Impact Quantification Frameworks — NYC DOT

## Public-sector value categories

Unlike commercial firms, NYC DOT impact is measured in:

| Category | Description | Metric |
|----------|-------------|--------|
| **Cost avoidance** | Claims, litigation, emergency repairs prevented | USD saved |
| **Cost efficiency** | Same output with fewer resources | Cost per inspection, cost per closure |
| **Service equity** | Distribution of service across boroughs/populations | Gini coefficient, borough deviation |
| **Compliance** | Meeting legal, regulatory, or SLA obligations | % within SLA, breach count |
| **Time to service** | How quickly residents receive response | Mean/median days to closure |

---

## Core formulas

### Cost per inspection
```
cost_per_inspection = total_inspection_budget / total_inspections_conducted
```
Benchmark: track quarterly; flag if > 15% above prior-year same quarter.

### Cost avoidance (trip-and-fall claims prevented)
```
avg_claim_cost = 75_000  # USD — NYC Law Department average settlement
risk_reduction_rate = 0.40  # % reduction in high-risk locations resolved vs. unresolved

avoided_claims = (high_risk_locations_resolved * risk_reduction_rate)
cost_avoidance_usd = avoided_claims * avg_claim_cost
```
**Source:** NYC Law Department annual report. Update `avg_claim_cost` annually.

### Ramp program ROI
```
# ADA compliance cost-avoidance
avg_ada_lawsuit_cost = 150_000  # USD
ramps_completed = df[df['status'] == 'COMPLETED'].shape[0]
compliance_value = ramps_completed * avg_ada_lawsuit_cost * 0.05  # 5% lawsuit rate estimate
```

### Borough equity index
```python
import numpy as np

def gini(values):
    """Gini coefficient: 0 = perfect equity, 1 = total inequality."""
    arr = np.sort(np.array(values, dtype=float))
    n = len(arr)
    return (2 * np.sum((np.arange(1, n + 1)) * arr) - (n + 1) * np.sum(arr)) / (n * np.sum(arr))

# Usage: gini([inspections_per_borough]) → interpret < 0.1 as equitable
```

### Cost efficiency delta
```
delta_efficiency = (baseline_cost_per_unit - current_cost_per_unit) / baseline_cost_per_unit * 100
# Positive = improvement; negative = regression
```

---

## NYC DOT impact quantification examples

### Example 1: Violation closure backlog reduction
- **Baseline:** 5,200 open violations (April 2026)
- **After:** 4,100 open violations (June 2026)
- **Reduction:** 1,100 violations × $75,000 avg claim risk × 40% risk factor = **$33M cost avoidance**
- **Caveat:** Risk factor (40%) is an estimate; range $20M–$50M at 80% CI.

### Example 2: Data pipeline improvement
- **Before:** Inspectors spend 2 hrs/week on manual data entry corrections
- **After:** Automated validation reduces corrections to 20 min/week
- **Time saved:** 1.67 hrs/week × 35 inspectors × 52 weeks = **3,038 hours/year**
- **Dollar value:** 3,038 × $55/hr (loaded rate) = **$167K/year**

### Example 3: Ramp completion program
- **Ramps completed in Q1 2026:** 312
- **Estimated ADA compliance value:** 312 × $150,000 × 5% = **$2.3M** in avoided litigation
- **Borough equity:** Gini coefficient fell from 0.18 to 0.12 — materially more equitable distribution

---

## Confidence and uncertainty guidance

- Always present a range, not a point estimate, for avoided-cost calculations.
- Use **80% confidence intervals** for planning; **95% CI** for formal reports.
- State assumptions explicitly: which cost rates, risk factors, and discount rates were used.
- Round to nearest $10K for reports to leadership — false precision undermines credibility.
