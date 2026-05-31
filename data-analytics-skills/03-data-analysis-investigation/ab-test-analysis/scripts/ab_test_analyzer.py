"""
A/B Test Analyzer

Calculates conversion rates, relative lift, statistical significance (z-test),
and Sample Ratio Mismatch (SRM) check for binary metrics.

Usage:
    python ab_test_analyzer.py --control-n 5000 --control-conv 480 \
        --treatment-n 5100 --treatment-conv 530
    python ab_test_analyzer.py --csv results.csv --metric converted --group variant
    python ab_test_analyzer.py --control-n 5000 --control-conv 480 \
        --treatment-n 5100 --treatment-conv 530 --alpha 0.05
"""

import argparse
import math
import sys


def srm_check(n_control: int, n_treatment: int, expected_split: float = 0.5) -> dict:
    """
    Chi-squared SRM check.
    Returns chi2 statistic, p-value approximation, and whether SRM is detected.
    """
    total = n_control + n_treatment
    expected_control = total * expected_split
    expected_treatment = total * (1 - expected_split)

    chi2 = ((n_control - expected_control) ** 2 / expected_control +
            (n_treatment - expected_treatment) ** 2 / expected_treatment)

    # Approximate p-value for chi2 with df=1 using survival function approximation
    # For chi2 df=1: p ≈ erfc(sqrt(chi2/2))
    p_value = math.erfc(math.sqrt(chi2 / 2))
    srm_detected = p_value < 0.01

    return {
        "n_control": n_control,
        "n_treatment": n_treatment,
        "expected_control": round(expected_control, 1),
        "expected_treatment": round(expected_treatment, 1),
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 6),
        "srm_detected": srm_detected,
    }


def analyze_binary_metric(n_control: int, conv_control: int,
                           n_treatment: int, conv_treatment: int,
                           alpha: float = 0.05) -> dict:
    """
    Two-proportion z-test for a binary metric (e.g. conversion rate).

    Returns rate for each group, absolute/relative lift, z-score, p-value,
    confidence interval for the difference, and significance verdict.
    """
    rate_c = conv_control / n_control
    rate_t = conv_treatment / n_treatment
    absolute_diff = rate_t - rate_c
    relative_lift = absolute_diff / rate_c if rate_c > 0 else float("inf")

    # Pooled proportion for z-test
    p_pool = (conv_control + conv_treatment) / (n_control + n_treatment)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_control + 1 / n_treatment))
    z = absolute_diff / se if se > 0 else 0.0

    # Two-tailed p-value via complementary error function
    p_value = math.erfc(abs(z) / math.sqrt(2))

    # 95% CI for the difference (unpooled SE)
    se_unpooled = math.sqrt(rate_c * (1 - rate_c) / n_control +
                            rate_t * (1 - rate_t) / n_treatment)
    # z-critical for alpha
    z_crit = _z_critical(alpha)
    ci_lower = absolute_diff - z_crit * se_unpooled
    ci_upper = absolute_diff + z_crit * se_unpooled

    significant = p_value < alpha

    return {
        "rate_control": round(rate_c, 6),
        "rate_treatment": round(rate_t, 6),
        "absolute_diff": round(absolute_diff, 6),
        "relative_lift_pct": round(relative_lift * 100, 2),
        "z_score": round(z, 4),
        "p_value": round(p_value, 6),
        "ci_lower": round(ci_lower, 6),
        "ci_upper": round(ci_upper, 6),
        "alpha": alpha,
        "significant": significant,
    }


def _z_critical(alpha: float) -> float:
    """Approximate inverse normal for two-tailed test."""
    # Common values
    table = {0.10: 1.645, 0.05: 1.960, 0.01: 2.576, 0.001: 3.291}
    return table.get(alpha, 1.960)


def format_report(srm: dict, result: dict, metric_name: str = "conversion") -> str:
    lines = [
        "=" * 60,
        "A/B TEST ANALYSIS REPORT",
        "=" * 60,
        "",
        "--- Sample Ratio Mismatch (SRM) Check ---",
        f"  Control:   {srm['n_control']:,}  (expected {srm['expected_control']:,.0f})",
        f"  Treatment: {srm['n_treatment']:,}  (expected {srm['expected_treatment']:,.0f})",
        f"  Chi2: {srm['chi2']}  |  p-value: {srm['p_value']}",
        f"  SRM detected: {'YES — investigate before trusting results' if srm['srm_detected'] else 'No'}",
        "",
        f"--- Metric: {metric_name} ---",
        f"  Control rate:   {result['rate_control']:.4%}",
        f"  Treatment rate: {result['rate_treatment']:.4%}",
        f"  Absolute diff:  {result['absolute_diff']:+.4%}",
        f"  Relative lift:  {result['relative_lift_pct']:+.2f}%",
        f"  Z-score: {result['z_score']}  |  p-value: {result['p_value']}",
        f"  {(1 - result['alpha']):.0%} CI for diff: [{result['ci_lower']:+.4%}, {result['ci_upper']:+.4%}]",
        "",
        f"  VERDICT: {'SIGNIFICANT' if result['significant'] else 'NOT SIGNIFICANT'} "
        f"at alpha={result['alpha']}",
    ]

    if result["significant"] and result["relative_lift_pct"] > 0:
        lines.append("  Recommendation: Treatment shows a positive, statistically significant lift.")
    elif result["significant"] and result["relative_lift_pct"] < 0:
        lines.append("  Recommendation: Treatment shows a statistically significant negative effect. Do not ship.")
    else:
        lines.append("  Recommendation: No significant difference detected. Consider running longer or revisiting design.")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze an A/B test result.")
    parser.add_argument("--control-n", type=int, help="Control group size")
    parser.add_argument("--control-conv", type=int, help="Control conversions")
    parser.add_argument("--treatment-n", type=int, help="Treatment group size")
    parser.add_argument("--treatment-conv", type=int, help="Treatment conversions")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance level (default 0.05)")
    parser.add_argument("--metric", default="conversion", help="Metric name for display")
    parser.add_argument("--split", type=float, default=0.5, help="Expected traffic split (default 0.5)")
    args = parser.parse_args()

    if not all([args.control_n, args.control_conv, args.treatment_n, args.treatment_conv]):
        parser.error("Provide --control-n, --control-conv, --treatment-n, --treatment-conv")

    srm = srm_check(args.control_n, args.treatment_n, args.split)
    result = analyze_binary_metric(args.control_n, args.control_conv,
                                   args.treatment_n, args.treatment_conv,
                                   args.alpha)
    print(format_report(srm, result, args.metric))
    sys.exit(0 if result["significant"] else 1)


if __name__ == "__main__":
    # Demo: checkout flow redesign
    srm = srm_check(10_000, 10_142)
    result = analyze_binary_metric(
        n_control=10_000, conv_control=850,
        n_treatment=10_142, conv_treatment=940,
        alpha=0.05,
    )
    print(format_report(srm, result, "checkout_conversion"))
    print()
    print("Significant:", result["significant"])
    print("Relative lift:", f"{result['relative_lift_pct']:+.2f}%")
