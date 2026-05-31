# A/B Test Design Guide

## Before the test starts

A well-designed test is analysed once. Repeatedly checking results and stopping early invalidates the p-value. Document every decision before looking at results.

### Required pre-registration
- **Hypothesis** — one sentence: what change do you expect and why?
- **Primary metric** — single metric used to determine the winner
- **Guardrail metrics** — metrics that must not regress (e.g., latency, error rate, revenue per user for a non-revenue test)
- **Minimum detectable effect (MDE)** — smallest lift that is practically significant
- **Traffic split** — usually 50/50; document if asymmetric and why
- **Duration** — calculated from power analysis; must include at least one full weekly cycle

---

## Sample size calculation

Required sample size per group:

```
n = 2 * (z_alpha/2 + z_beta)^2 * p * (1 - p) / MDE^2
```

Where:
- `p` = baseline conversion rate
- `MDE` = minimum detectable effect (absolute)
- `z_alpha/2` = 1.96 for alpha=0.05 (two-tailed)
- `z_beta` = 0.84 for 80% power

**Rule of thumb for small MDE:** If you want to detect a 10% relative lift on a 5% baseline (0.5% absolute), you need ~15,000 users per group. Use a power calculator to verify.

---

## Sample Ratio Mismatch (SRM)

SRM occurs when the actual traffic split differs materially from the intended split. It is a sign of an instrumentation bug — not a real treatment effect — and invalidates the test.

**Check:** Chi-squared test on actual vs expected allocation. Flag if p < 0.01.

**Common SRM causes:**
- Bot traffic filtered on one side but not the other
- Stickiness failure (users re-assigned on return visits)
- Triggered experiment (only a subset qualifies post-assignment)
- Cache or CDN serving stale experience to some users

**If SRM detected:** Do not interpret results. Investigate assignment mechanism before re-running.

---

## Metric selection

**Primary metric:** Must be directly influenced by the change, measurable within the test window, and sensitive enough to detect the MDE.

**Guardrail metrics:** Things that must stay stable. Failed guardrail = do not ship even if primary metric wins. Examples: session length (for engagement tests), page load time (for UI tests), support ticket rate.

**North star vs proxy:** If the north star metric (e.g., revenue) needs weeks to move, use a leading proxy (e.g., add-to-cart rate) as the primary with north star as a secondary signal.

---

## Analysis checklist

1. [ ] SRM check passes (p > 0.01 for allocation chi-squared)
2. [ ] Test ran for the pre-specified duration
3. [ ] Primary metric result and 95% CI computed
4. [ ] All guardrail metrics checked
5. [ ] Segment breakdowns reviewed for heterogeneous treatment effects
6. [ ] Result is consistent across device types / regions (or difference is explained)
7. [ ] Decision documented and shared

---

## Interpretation guidance

| Result | Recommendation |
|---|---|
| Significant positive primary, guardrails pass | Ship |
| Significant positive primary, guardrail fails | Do not ship; investigate the regression |
| Not significant | Do not ship; revisit hypothesis or MDE |
| Significant negative | Do not ship; understand the harm before iterating |
| SRM detected | Re-run; do not interpret |
