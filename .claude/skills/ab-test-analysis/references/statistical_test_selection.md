# Statistical Test Selection — NYC DOT SIM Experiments

Decision tree for choosing the correct significance test for sidewalk inspection workflow experiments.

---

## Decision Tree

```
What is your primary metric?
│
├── BINARY / RATE (completed: yes/no, violated: yes/no, resolved: yes/no)
│   └── Use: Two-proportion z-test
│       Script flag: --metric-type proportion
│       Formula: z = (p_t - p_c) / sqrt(p_pool*(1-p_pool)*(1/n_c + 1/n_t))
│
├── CONTINUOUS (days-to-close, inspection lag, count of defects)
│   ├── Normal distribution assumed (n > 30 per arm)?
│   │   └── Use: Welch's t-test (unequal variance)
│   │       Script flag: --metric-type continuous
│   ├── Heavily skewed (lag times, dollar amounts)?
│   │   └── Consider: Mann-Whitney U test (rank-based)
│   └── Small samples (n < 30 per arm)?
│       └── Use: Welch's t-test with caution; report exact p-value
│
└── COUNT / RATE WITH EXPOSURE (violations per 1000 inspections)
    └── Use: Poisson rate test or negative binomial regression
```

---

## NYC DOT Metric Guide

| Metric | Column | Type | Recommended Test |
|---|---|---|---|
| Inspection completion rate | `status = 'COMPLETED'` | Proportion | z-test |
| Violation rate | violations / inspections | Proportion | z-test |
| Days to close | `completion_date - created_date` | Continuous | Welch's t |
| Ramp completion rate | `ramp_progress.status` | Proportion | z-test |
| Inspections per inspector | count(objectid) per unit_id | Count | Welch's t or Poisson |
| Defect detection rate | defects found / inspections | Proportion | z-test |
| SLA breach rate | lag > SLA_threshold | Proportion | z-test |

---

## Effect Size Reference

| Metric | Cohen's d | Relative Risk | Practical Significance |
|---|---|---|---|
| Negligible | < 0.2 | < 1.05 | Not worth shipping |
| Small | 0.2–0.5 | 1.05–1.20 | Worth shipping if low cost |
| Medium | 0.5–0.8 | 1.20–1.50 | Ship |
| Large | > 0.8 | > 1.50 | Strong evidence, ship |

For NYC DOT completion rates, a **3–5 percentage point** improvement is operationally meaningful.
For inspection lag, a **2+ day reduction** in median days-to-close is practically significant.

---

## SRM (Sample Ratio Mismatch) Causes

SRM (chi2 test p < 0.05) means variant assignment is unbalanced. Common causes:

1. **Bot traffic** — non-human inspectors entering the dataset
2. **Assignment bug** — hash collision or off-by-one in randomisation logic
3. **Unit mismatch** — randomising at district level but analysing at inspection level
4. **Exclusion criteria applied post-assignment** — filters applied differently per variant
5. **Mid-experiment changes** — variant definitions changed after assignment

**Always resolve SRM before interpreting results.** An SRM of even 1% can flip significance conclusions.

---

## Multiple Testing Corrections

When testing 3+ metrics simultaneously:

- **Bonferroni**: alpha_adjusted = alpha / k (most conservative)
- **Benjamini-Hochberg**: controls False Discovery Rate — recommended for exploratory analyses
- **Rule of thumb for NYC DOT**: declare one primary metric per experiment; apply Bonferroni if more than 3 secondary metrics are tested

```python
# Bonferroni example (scipy)
from statsmodels.stats.multitest import multipletests
reject, p_adj, _, _ = multipletests(p_values, alpha=0.05, method='bonferroni')
```
