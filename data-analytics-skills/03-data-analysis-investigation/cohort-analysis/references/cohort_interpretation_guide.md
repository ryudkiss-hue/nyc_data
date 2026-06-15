# Cohort Interpretation Guide — NYC DOT SIM

Pattern recognition guide for reading cohort retention matrices in inspection and ramp workflow analyses.

---

## Reading the Retention Matrix

Each cell = **fraction of cohort that completed by period N** from their start date.

```
         Period 0   Period 1   Period 3   Period 6   Period 12
Jan-25     100%       52%        71%        78%        81%
Feb-25     100%       49%        68%        75%        80%
Mar-25     100%       56%        74%        81%        84%
```

- **Period 0** = completions that occurred in the same period as creation (quick resolves)
- **Period 1** = completions within 1 month of creation
- **Cumulative** — values generally increase over time as backlog clears

---

## NYC DOT Retention Benchmarks

| Period | Inspection Resolution | Ramp Completion | Violation Closure |
|---|---|---|---|
| Period 1 (30d) | 45–55% | 15–25% | 50–65% |
| Period 3 (90d) | 65–75% | 35–50% | 70–80% |
| Period 6 (6M) | 75–82% | 55–70% | 78–85% |
| Period 12 (1Y) | 82–88% | 68–80% | 85–90% |

_These are estimates based on typical SIM unit workflow data. Validate against live baselines._

---

## Common Patterns and What They Mean

### 1. Healthy Improving Curve
```
Period:   0    1    3    6   12
Rate:    35%  55%  72%  80%  85%
```
- Gradual increase that plateaus — normal pattern
- Early completions (period 0–1) reflect quick-wins; late completions are complex cases
- Action: monitor for cliff drops; set SLA based on period where 80% threshold is reached

### 2. Cliff Drop
```
Period:   0    1    3    6   12
Rate:    48%  52%  54%  55%  55%
```
- Plateau very early followed by flat line — large fraction never resolved
- Indicates a structural backlog or systematic blocking issue
- Action: investigate what separates the ~45% that never complete

### 3. Cohort Divergence (Recent Cohorts Worse)
```
         P0   P1   P3
Jan-25   48%  68%  79%
Jun-25   42%  58%  --
Nov-25   35%  --   --
```
- Recent cohorts start worse — possible: increased volume, staffing changes, seasonal factors
- Be cautious: recent cohorts have less time to accumulate completions (right-censoring bias)

### 4. Seasonal Dip Cohorts
- Cohorts starting in **December or January** often show lower period-1 retention
- NYC DOT: winter months reduce outdoor inspection activity
- Correct by: comparing same-period cohorts across years, not adjacent months

### 5. Step Improvement After Policy Change
```
         P1
Jan-25   50%  ← pre-policy
Apr-25   62%  ← post-policy
```
- Abrupt improvement in recent cohorts suggests a positive process change
- Confirm timing aligns with known interventions (new workflow, training, staffing)

---

## Right-Censoring Warning

Recent cohorts have **less time to accumulate completions** than older cohorts.

- Always note: "Period-3 data for cohorts < 3 months old is incomplete"
- For fair comparison, use only period offsets within the cohort's age
- Mark immature cells in the matrix as `--` or grey

---

## Segmentation Priorities

When breaking cohorts by segment, prioritise:

1. **Borough** — operational capacity varies significantly (MN vs SI)
2. **Defect type** — structural defects take longer than surface defects
3. **Material type** — concrete vs. asphalt have different repair timelines
4. **Unit ID** — inspector-level cohorts can reveal workload imbalance

---

## Retention Glossary

| Term | Definition |
|---|---|
| Cohort | Group of records created in the same time period |
| Cohort size | Total records entering in period 0 |
| Retention rate | % of cohort that completed by period N |
| Period offset | Periods elapsed since cohort start |
| Cliff drop | ≥ 15pp drop in median retention between two adjacent periods |
| Right-censoring | Incompleteness in recent cohorts due to insufficient elapsed time |
| Quick-resolve rate | % completing within period 0 (same month as creation) |
