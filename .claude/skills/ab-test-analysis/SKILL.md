---
name: ab-test-analysis
description: Rigorous A/B test statistical analysis. Use when analyzing experiment results, calculating statistical significance, checking for sample ratio mismatch, or validating test design before launch.
---

# A/B Test Analysis

# When to use
- An experiment has finished and the team needs a ship / no-ship recommendation
- Results look directionally positive but the team is unsure if they're statistically significant
- A test has been running for weeks without a clear winner and someone needs to decide whether to continue
- A new experiment needs sample-size planning before launch
- Results are disputed and need a rigorous, documented analysis

# Process
1. **Confirm test design** — verify the hypothesis, the control and treatment definitions, the randomisation unit (user/session/device), the primary metric, any guardrail metrics, and the target split ratio.
2. **Check for sample ratio mismatch (SRM)** — run a chi-square test on the actual vs. expected split. If SRM is detected, stop and investigate the randomisation pipeline before interpreting results. Use `scripts/ab_test_analyzer.py --check-srm`.
3. **Calculate per-variant metrics** — compute the rate (or mean) and 95% confidence interval for the primary metric in each variant. Document absolute and relative difference.
4. **Run the significance test** — execute a two-proportion z-test (for rates) or Welch's t-test (for means). Record z-score, p-value, and 95% CI for the effect. Use `references/statistical_tests_reference.md` if unsure which test applies.
5. **Check guardrail metrics** — run the same significance test for each guardrail metric. A significant degradation on any guardrail is a blocker regardless of primary metric results.
6. **Produce the recommendation** — synthesise SRM result, power, significance, and guardrail checks into a clear ship / no-ship / extend decision. Quantify the expected business impact if shipped. Record in `assets/ab_test_report_template.md`.

# Inputs the skill needs
- Test plan or hypothesis document (variant definitions, randomisation unit, primary metric)
- Data with at minimum: user_id, variant assignment, primary metric outcome
- Optional: guardrail metric values per user, daily aggregate data for temporal validity checks
- Target split ratio (e.g., 50/50)
- Minimum detectable effect or business threshold for "worth shipping"

# Output
- `scripts/ab_test_analyzer.py` — runs SRM check, significance test, power analysis, and guardrail checks from a CSV or summary stats input
- `references/statistical_tests_reference.md` — which test to use and when
- `references/ab_test_design_guide.md` — SRM causes, power planning, peeking and multiple testing
- `assets/ab_test_report_template.md` — structured report: design, results, checks, recommendation, expected impact
