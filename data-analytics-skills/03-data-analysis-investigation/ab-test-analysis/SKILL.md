---
name: ab-test-analysis
description: Rigorous statistical analysis of A/B test results. Activate when experiment results need validation, significance is unclear, test duration decisions need justification, or disputed results require documented statistical analysis.
---

# When to use
- Experiment results look promising but significance is unclear
- A test has been running a long time without a winner — should it be extended or stopped?
- Pre-test sample size planning to ensure adequate power
- Results are disputed and require documented, reproducible statistical analysis
- Post-experiment review for learning documentation

# Process
1. **Validate experimental design** — confirm: clear hypothesis, control and treatment variants, randomisation unit (user, session, etc.), primary and guardrail metrics, and pre-defined sample size
2. **Check sample ratio mismatch (SRM)** — run chi-square test on variant assignment; SRM (p < 0.05) invalidates the experiment and must be investigated before interpreting results
3. **Compute per-variant metrics** — calculate mean, variance, and 95% confidence intervals for primary and secondary metrics
4. **Run significance tests** — apply z-test for conversion rates or Welch's t-test for continuous metrics; calculate p-value, effect size (Cohen's d or relative lift), and statistical power
5. **Check guardrail metrics** — verify no guardrail metric degraded significantly; document findings even if primary metric is positive
6. **Produce decision summary** — synthesise SRM, power, significance, and guardrail results into a ship / no-ship / extend recommendation with business impact quantification

# Inputs the skill needs
- Required: variant assignment data (user ID, variant) and metric values per user, OR summary statistics (n, mean, std per variant)
- Required: pre-defined hypothesis and primary metric
- Optional: guardrail metrics
- Optional: minimum detectable effect and desired statistical power

# Output
- `scripts/ab_test_analyzer.py` — processes raw or summary data; outputs SRM check, significance tests, effect size, and power
- `references/statistical_test_selection.md` — decision tree for test selection
- `references/experiment_design_guide.md` — SRM causes, sample size formulas, power calculation
- `assets/ab_test_report_template.md` (filled) — design, results, validation checks, and ship recommendation
