"""A/B test framework for SIM program analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class ABTestResult:
    test_name: str
    group_a_label: str
    group_b_label: str
    metric: str
    n_a: int
    n_b: int
    mean_a: float
    mean_b: float
    effect_size: float  # Cohen's d for continuous, relative risk for proportions
    p_value: float
    ci_lower: float  # 95% CI on difference (a - b)
    ci_upper: float
    test_type: str  # "t_test", "mann_whitney", "chi_square", "proportion_z"
    significant: bool  # p < alpha
    alpha: float = 0.05
    correction: str | None = None  # "bonferroni", "fdr_bh", None
    power: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def compare_groups(
    df: pd.DataFrame,
    group_col: str,
    group_a: str,
    group_b: str,
    metric_col: str,
    metric_type: str = "continuous",  # "continuous" | "proportion" | "count"
    alpha: float = 0.05,
    correction: str | None = None,
) -> ABTestResult:
    """
    Compare metric between two groups with appropriate statistical test.

    For continuous metrics: Welch t-test with Cohen's d effect size.
    For proportions: z-test with relative risk.
    For counts: Mann-Whitney U (non-parametric).
    """
    if group_col not in df.columns:
        raise ValueError(f"Column '{group_col}' not in DataFrame")
    if metric_col not in df.columns:
        raise ValueError(f"Column '{metric_col}' not in DataFrame")

    a = df[df[group_col] == group_a][metric_col].dropna()
    b = df[df[group_col] == group_b][metric_col].dropna()

    if len(a) == 0 or len(b) == 0:
        raise ValueError(f"One or both groups empty after filtering: n_a={len(a)}, n_b={len(b)}")

    if metric_type == "continuous":
        _t_stat, p_value = stats.ttest_ind(a, b, equal_var=False)
        pooled_std = np.sqrt((a.std() ** 2 + b.std() ** 2) / 2)
        effect_size = (a.mean() - b.mean()) / pooled_std if pooled_std > 0 else 0.0
        diff = a.mean() - b.mean()
        se = np.sqrt(a.var() / len(a) + b.var() / len(b))
        ci_lower = diff - 1.96 * se
        ci_upper = diff + 1.96 * se
        test_type = "t_test"
    elif metric_type == "proportion":
        p_a, p_b = a.mean(), b.mean()
        count_a, count_b = int(a.sum()), int(b.sum())
        n_a_len, n_b_len = len(a), len(b)
        # Two-proportion z-test using pooled proportion under H0
        p_pool = (count_a + count_b) / (n_a_len + n_b_len)
        se_h0 = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a_len + 1 / n_b_len))
        z_stat = (p_a - p_b) / se_h0 if se_h0 > 0 else 0.0
        p_value = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
        effect_size = p_a / p_b if p_b > 0 else float("inf")  # relative risk
        se = np.sqrt(p_a * (1 - p_a) / n_a_len + p_b * (1 - p_b) / n_b_len)
        ci_lower = (p_a - p_b) - 1.96 * se
        ci_upper = (p_a - p_b) + 1.96 * se
        test_type = "proportion_z"
    else:  # count / non-parametric
        stat, p_value = stats.mannwhitneyu(a, b, alternative="two-sided")
        effect_size = float(stat) / (len(a) * len(b))  # rank-biserial correlation
        diff = a.median() - b.median()
        ci_lower = diff - 1.96 * (a.std() + b.std()) / 2
        ci_upper = diff + 1.96 * (a.std() + b.std()) / 2
        test_type = "mann_whitney"

    return ABTestResult(
        test_name=f"{group_a}_vs_{group_b}_{metric_col}",
        group_a_label=group_a,
        group_b_label=group_b,
        metric=metric_col,
        n_a=len(a),
        n_b=len(b),
        mean_a=float(a.mean()),
        mean_b=float(b.mean()),
        effect_size=float(effect_size),
        p_value=float(p_value),
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        test_type=test_type,
        significant=bool(p_value < alpha),
        alpha=alpha,
        correction=correction,
    )


def compare_boroughs(
    df: pd.DataFrame,
    metric_col: str,
    borough_col: str = "borough",
    metric_type: str = "continuous",
    alpha: float = 0.05,
) -> list[ABTestResult]:
    """Run pairwise borough comparisons with Bonferroni correction."""
    boroughs = [b for b in df[borough_col].dropna().unique() if b]
    pairs = [
        (boroughs[i], boroughs[j])
        for i in range(len(boroughs))
        for j in range(i + 1, len(boroughs))
    ]
    n_comparisons = len(pairs)
    adj_alpha = alpha / n_comparisons if n_comparisons > 1 else alpha

    results = []
    for a, b in pairs:
        try:
            r = compare_groups(
                df, borough_col, a, b, metric_col, metric_type, adj_alpha, "bonferroni"
            )
            results.append(r)
        except ValueError:
            continue
    return results
