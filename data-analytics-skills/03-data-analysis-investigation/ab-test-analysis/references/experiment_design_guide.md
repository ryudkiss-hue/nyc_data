# Experiment Design Guide — NYC DOT SIM

Reference for designing valid A/B tests on sidewalk inspection and ramp workflow processes.

---

## Sample Size Formulas

### Proportion metric (completion rate, violation rate)

```
n_per_arm = (z_α/2 + z_β)² * [p_c(1-p_c) + p_t(1-p_t)] / MDE²
```

Where:
- z_α/2 = 1.96 (two-tailed, α=0.05)
- z_β = 0.842 (80% power) or 1.282 (90% power)
- p_c = baseline rate in control
- MDE = minimum detectable effect (absolute percentage points)

### Continuous metric (lag days, counts)

```
n_per_arm = 2 * [(z_α/2 + z_β) * σ / MDE]²
```

Where σ = pooled standard deviation.

---

## Baseline Rates for NYC DOT Metrics

| Metric | Approximate Baseline | Source Dataset |
|---|---|---|
| Inspection completion rate | ~72–76% | `inspection` (dntt-gqwq) |
| Violation resolution rate (30d) | ~58–64% | `violations` (6kbp-uz6m) |
| Ramp completion rate (borough avg) | ~61–68% | `ramp_progress` (e7gc-ub6z) |
| SLA breach rate (HIGH tier) | ~18–24% | `inspection` + SLA config |
| Dismissal rate | ~21–27% | `dismissals` (p4u2-3jgx) |

_These baselines are estimates for planning. Always measure current baseline from live data before finalising sample size._

---

## Recommended MDE by Metric Type

| Metric | Recommended MDE | Rationale |
|---|---|---|
| Completion rate | 3–5 pp | Operationally meaningful change per quarter |
| Lag (days-to-close) | 1–2 days | Aligned with SLA tier thresholds |
| Ramp completion rate | 4–6 pp | Borough-level significance |
| Violation resolution | 4 pp | Below this, staffing impact is negligible |

---

## Power & Duration Planning

### Required n per arm at common baselines (α=0.05, power=80%)

| Baseline Rate | MDE 3pp | MDE 5pp | MDE 10pp |
|---|---|---|---|
| 60% | 5,139 | 1,879 | 474 |
| 70% | 4,682 | 1,712 | 432 |
| 75% | 4,414 | 1,613 | 407 |

### Duration estimate

```
days_required = n_per_arm * 2 / daily_inspections_per_variant
```

Example: 4,700 per arm, 300 inspections/day total, 50/50 split → ~31 days minimum.

---

## Pre-Experiment Checklist

- [ ] Hypothesis stated as one-sentence prediction (X intervention will increase Y metric by Z%)
- [ ] Randomisation unit defined (inspection record, inspector, district)
- [ ] Primary metric pre-registered (only one)
- [ ] Guardrail metrics listed (e.g. don't let dismissal rate rise >2pp)
- [ ] Sample size calculated and experiment duration confirmed
- [ ] SRM monitoring in place before full launch
- [ ] AA test completed (confirm no pre-existing difference between variants)

---

## Post-Experiment Checklist

- [ ] SRM check passed (chi2 p > 0.05)
- [ ] Primary metric significance evaluated
- [ ] All guardrail metrics reviewed
- [ ] Novelty effects considered (if treatment involves a new UI/process)
- [ ] Segment heterogeneity reviewed (did effect vary significantly by borough?)
- [ ] Decision documented in `ab_test_report_template.md`
