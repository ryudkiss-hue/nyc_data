"""
ab_test_analyzer.py — NYC DOT SIM A/B Test Analyzer

Processes raw or summary data for inspection workflow experiments.
Outputs: SRM check, significance tests, effect size, power analysis.

Usage:
    python ab_test_analyzer.py --summary \
        --control-n 4200 --control-mean 0.73 --control-std 0.44 \
        --treatment-n 4150 --treatment-mean 0.78 --treatment-std 0.41 \
        --metric-type proportion --alpha 0.05 --mde 0.05

    python ab_test_analyzer.py --input data/experiment_results.csv \
        --variant-col variant --metric-col completed --user-col objectid
"""

import argparse
import math
import sys
from typing import Optional

try:
    import numpy as np
    import pandas as pd
    from scipy import stats
except ImportError:
    print("ERROR: requires numpy, pandas, scipy — pip install numpy pandas scipy")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Core statistical functions
# ---------------------------------------------------------------------------


def check_srm(n_control: int, n_treatment: int, expected_split: float = 0.5) -> dict:
    """Chi-square test for Sample Ratio Mismatch."""
    n_total = n_control + n_treatment
    expected_control = n_total * expected_split
    expected_treatment = n_total * (1 - expected_split)
    chi2 = (n_control - expected_control) ** 2 / expected_control + (
        n_treatment - expected_treatment
    ) ** 2 / expected_treatment
    p_value = 1 - stats.chi2.cdf(chi2, df=1)
    actual_split = n_control / n_total
    return {
        "n_control": n_control,
        "n_treatment": n_treatment,
        "expected_split": expected_split,
        "actual_split": round(actual_split, 4),
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 4),
        "srm_detected": p_value < 0.05,
    }


def z_test_proportions(n_c: int, p_c: float, n_t: int, p_t: float, alpha: float = 0.05) -> dict:
    """Two-proportion z-test for conversion/completion rates."""
    p_pool = (p_c * n_c + p_t * n_t) / (n_c + n_t)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_t))
    if se == 0:
        return {"error": "Standard error is zero — check inputs"}
    z = (p_t - p_c) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = (p_t - p_c) - z_crit * se
    ci_upper = (p_t - p_c) + z_crit * se
    relative_lift = (p_t - p_c) / p_c if p_c > 0 else None
    return {
        "z_statistic": round(z, 4),
        "p_value": round(p_value, 4),
        "significant": p_value < alpha,
        "absolute_diff": round(p_t - p_c, 4),
        "relative_lift": round(relative_lift, 4) if relative_lift else None,
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
    }


def welch_t_test(
    n_c: int,
    mean_c: float,
    std_c: float,
    n_t: int,
    mean_t: float,
    std_t: float,
    alpha: float = 0.05,
) -> dict:
    """Welch's t-test for continuous metrics (e.g. days-to-close, inspection lag)."""
    se = math.sqrt(std_c**2 / n_c + std_t**2 / n_t)
    if se == 0:
        return {"error": "Standard error is zero — check inputs"}
    t = (mean_t - mean_c) / se
    # Welch–Satterthwaite degrees of freedom
    num = (std_c**2 / n_c + std_t**2 / n_t) ** 2
    denom = (std_c**2 / n_c) ** 2 / (n_c - 1) + (std_t**2 / n_t) ** 2 / (n_t - 1)
    df = num / denom if denom > 0 else min(n_c, n_t) - 1
    p_value = 2 * stats.t.sf(abs(t), df=df)
    t_crit = stats.t.ppf(1 - alpha / 2, df=df)
    ci_lower = (mean_t - mean_c) - t_crit * se
    ci_upper = (mean_t - mean_c) + t_crit * se
    cohens_d = (mean_t - mean_c) / math.sqrt((std_c**2 + std_t**2) / 2)
    return {
        "t_statistic": round(t, 4),
        "degrees_of_freedom": round(df, 1),
        "p_value": round(p_value, 4),
        "significant": p_value < alpha,
        "mean_diff": round(mean_t - mean_c, 4),
        "cohens_d": round(cohens_d, 4),
        "effect_size_label": _effect_label(abs(cohens_d)),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
    }


def compute_power(
    n: int, mde: float, baseline: float, alpha: float = 0.05, metric_type: str = "proportion"
) -> float:
    """Statistical power given n per arm and MDE."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    if metric_type == "proportion":
        p_c = baseline
        p_t = baseline + mde
        se_h0 = math.sqrt(2 * baseline * (1 - baseline) / n)
        se_h1 = math.sqrt(p_c * (1 - p_c) / n + p_t * (1 - p_t) / n)
    else:
        se_h0 = baseline / math.sqrt(n)
        se_h1 = se_h0
    if se_h1 == 0:
        return 0.0
    z_beta = (abs(mde) / se_h1) - z_alpha
    return float(stats.norm.cdf(z_beta))


def required_sample_size(
    baseline: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.80,
    metric_type: str = "proportion",
) -> int:
    """Minimum n per arm for desired power."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    if metric_type == "proportion":
        p_c = baseline
        p_t = baseline + mde
        n = (z_alpha + z_beta) ** 2 * (p_c * (1 - p_c) + p_t * (1 - p_t)) / mde**2
    else:
        # baseline treated as std dev for continuous
        n = 2 * ((z_alpha + z_beta) * baseline / mde) ** 2
    return math.ceil(n)


def _effect_label(d: float) -> str:
    if d < 0.2:
        return "negligible"
    if d < 0.5:
        return "small"
    if d < 0.8:
        return "medium"
    return "large"


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------


def print_report(
    srm: dict,
    test_result: dict,
    power: float,
    n_required: Optional[int],
    metric_type: str,
    alpha: float,
) -> None:
    print("\n" + "=" * 60)
    print("NYC DOT SIM — A/B Test Analysis Report")
    print("=" * 60)

    print("\n[1] Sample Ratio Mismatch Check")
    print(f"  Control n:   {srm['n_control']:,}")
    print(f"  Treatment n: {srm['n_treatment']:,}")
    print(f"  Expected split: {srm['expected_split']:.0%} / Actual: {srm['actual_split']:.1%}")
    print(f"  chi2={srm['chi2']:.3f}  p={srm['p_value']:.4f}")
    if srm["srm_detected"]:
        print("  ⚠ SRM DETECTED (p < 0.05) — results are INVALID. Investigate assignment.")
    else:
        print("  ✓ No SRM detected. Assignment appears balanced.")

    print(f"\n[2] Significance Test (alpha={alpha})")
    if "error" in test_result:
        print(f"  ERROR: {test_result['error']}")
    else:
        if metric_type == "proportion":
            print(f"  z={test_result['z_statistic']:.4f}  p={test_result['p_value']:.4f}")
            print(f"  Absolute diff: {test_result['absolute_diff']:+.4f}")
            print(
                f"  Relative lift: {test_result['relative_lift']:+.2%}"
                if test_result["relative_lift"]
                else ""
            )
        else:
            print(
                f"  t={test_result['t_statistic']:.4f}  df={test_result['degrees_of_freedom']:.0f}  p={test_result['p_value']:.4f}"
            )
            print(f"  Mean diff:   {test_result['mean_diff']:+.4f}")
            print(
                f"  Cohen's d:   {test_result['cohens_d']:.4f} ({test_result['effect_size_label']})"
            )
        print(f"  95% CI: [{test_result['ci_lower']:.4f}, {test_result['ci_upper']:.4f}]")
        sig = test_result["significant"]
        print(f"  Result: {'✓ SIGNIFICANT' if sig else '✗ NOT SIGNIFICANT'}")

    print("\n[3] Statistical Power")
    print(f"  Observed power: {power:.1%}")
    if power < 0.80:
        print("  ⚠ Underpowered (<80%). Extend test or increase sample.")
    if n_required:
        print(f"  Required n per arm (80% power): {n_required:,}")

    print("\n[4] Decision Guidance")
    if srm["srm_detected"]:
        print("  RECOMMENDATION: DO NOT SHIP — SRM invalidates results.")
    elif "significant" in test_result and test_result["significant"] and power >= 0.80:
        print("  RECOMMENDATION: SHIP — statistically significant with adequate power.")
    elif "significant" in test_result and not test_result["significant"] and power >= 0.80:
        print("  RECOMMENDATION: NO SHIP — well-powered test found no effect.")
    else:
        print("  RECOMMENDATION: EXTEND — insufficient power to draw conclusions.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(
        description="NYC DOT SIM A/B Test Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--summary", action="store_true", help="Use pre-computed summary stats")
    mode.add_argument("--input", help="Path to raw CSV with user-level data")

    # Summary mode args
    p.add_argument("--control-n", type=int)
    p.add_argument("--control-mean", type=float, help="Mean or rate for control")
    p.add_argument("--control-std", type=float, help="Std dev (continuous only)")
    p.add_argument("--treatment-n", type=int)
    p.add_argument("--treatment-mean", type=float)
    p.add_argument("--treatment-std", type=float)

    # Raw CSV mode args
    p.add_argument("--variant-col", default="variant", help="Column identifying control/treatment")
    p.add_argument("--metric-col", default="completed", help="Column with metric value")
    p.add_argument("--user-col", default="objectid", help="User/record identifier column")

    # Common args
    p.add_argument(
        "--metric-type",
        choices=["proportion", "continuous"],
        default="proportion",
        help="proportion = completion/conversion rates; continuous = lag days, counts",
    )
    p.add_argument("--alpha", type=float, default=0.05, help="Significance level (default 0.05)")
    p.add_argument(
        "--mde", type=float, default=0.05, help="Minimum detectable effect for power calculation"
    )
    p.add_argument(
        "--expected-split",
        type=float,
        default=0.5,
        help="Expected fraction assigned to control (default 0.5)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if args.input:
        df = pd.read_csv(args.input)
        variants = df[args.variant_col].unique()
        if len(variants) != 2:
            print(f"ERROR: Expected exactly 2 variants, found: {variants}")
            sys.exit(1)
        control_label = [v for v in variants if "control" in str(v).lower()]
        control_label = control_label[0] if control_label else variants[0]
        treatment_label = [v for v in variants if v != control_label][0]

        ctl = df[df[args.variant_col] == control_label][args.metric_col].dropna()
        trt = df[df[args.variant_col] == treatment_label][args.metric_col].dropna()

        n_c, mean_c, std_c = len(ctl), float(ctl.mean()), float(ctl.std())
        n_t, mean_t, std_t = len(trt), float(trt.mean()), float(trt.std())
        print(
            f"Loaded: control='{control_label}' (n={n_c}), treatment='{treatment_label}' (n={n_t})"
        )
    else:
        n_c, mean_c = args.control_n, args.control_mean
        n_t, mean_t = args.treatment_n, args.treatment_mean
        std_c = args.control_std or 0.0
        std_t = args.treatment_std or 0.0

    srm = check_srm(n_c, n_t, expected_split=args.expected_split)

    if args.metric_type == "proportion":
        test_result = z_test_proportions(n_c, mean_c, n_t, mean_t, alpha=args.alpha)
        power = compute_power(n_c, args.mde, mean_c, alpha=args.alpha, metric_type="proportion")
        n_req = required_sample_size(mean_c, args.mde, alpha=args.alpha, metric_type="proportion")
    else:
        test_result = welch_t_test(n_c, mean_c, std_c, n_t, mean_t, std_t, alpha=args.alpha)
        power = compute_power(n_c, args.mde, std_c, alpha=args.alpha, metric_type="continuous")
        n_req = required_sample_size(std_c, args.mde, alpha=args.alpha, metric_type="continuous")

    print_report(srm, test_result, power, n_req, args.metric_type, args.alpha)


if __name__ == "__main__":
    main()
