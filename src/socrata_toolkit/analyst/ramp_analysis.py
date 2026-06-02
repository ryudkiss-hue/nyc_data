"""Borough aggregation and completion rates analysis for DOT sidewalk program.

Provides ramp analysis workflows including per-borough completion rates,
95% confidence intervals, and statistical power analysis.

Example::

    from socrata_toolkit.analyst.ramp_analysis import compute_borough_completion_rates

    df = pd.DataFrame({
        'borough': ['MN']*100 + ['BK']*100,
        'total_complaints': [10]*200,
        'resolved_complaints': [8]*100 + [6]*100
    })
    rates = compute_borough_completion_rates(df)
    print(f"MN completion rate: {rates['MN']['completion_rate']}")
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from scipy import stats


def compute_borough_completion_rates(
    df: pd.DataFrame,
    borough_col: str = "borough",
    total_col: str = "total_complaints",
    resolved_col: str = "resolved_complaints",
    confidence_level: float = 0.95,
    effect_size: float = 0.08,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Compute completion rates and statistical metrics by borough.

    Groups sidewalk complaints by borough, calculating completion rates
    (resolved / total), 95% binomial confidence intervals, and power analysis
    to determine if sample size is sufficient for detecting the target effect size.

    Args:
        df: DataFrame with complaint data
        borough_col: Column name for borough (default: "borough")
        total_col: Column name for total complaint count (default: "total_complaints")
        resolved_col: Column name for resolved complaint count (default: "resolved_complaints")
        confidence_level: Confidence level for binomial CI (default: 0.95)
        effect_size: Minimum detectable effect size for power analysis (default: 0.08)
        alpha: Significance level for power analysis (default: 0.05)

    Returns:
        Dictionary with keys:
        - Per-borough data: borough name -> dict with keys:
          - completion_rate: float (0-1)
          - resolved_count: int
          - total_count: int
          - ci_lower: float (confidence interval lower bound)
          - ci_upper: float (confidence interval upper bound)
          - sample_size: int (corner/location count)
          - has_power: bool (True if n sufficient for effect_size at alpha)
        - "comparison_table": pd.DataFrame with per-borough summary
        - "overall_completion_rate": float (weighted average)

    Example::

        df = pd.DataFrame({
            'borough': ['MN']*100 + ['BK']*100,
            'total_complaints': [10]*200,
            'resolved_complaints': [8]*100 + [6]*100
        })
        rates = compute_borough_completion_rates(df)
        print(rates['MN']['completion_rate'])  # e.g., 0.8
        print(rates['comparison_table'])
    """
    if df.empty:
        return {
            "comparison_table": pd.DataFrame(
                columns=[
                    "borough",
                    "completion_rate",
                    "resolved_count",
                    "total_count",
                    "ci_lower",
                    "ci_upper",
                    "sample_size",
                    "has_power",
                ]
            ),
            "overall_completion_rate": 0.0,
        }

    # Validate required columns
    if borough_col not in df.columns:
        raise ValueError(f"Column '{borough_col}' not found in DataFrame")
    if total_col not in df.columns:
        raise ValueError(f"Column '{total_col}' not found in DataFrame")
    if resolved_col not in df.columns:
        raise ValueError(f"Column '{resolved_col}' not found in DataFrame")

    # Initialize result containers
    borough_results: dict[str, dict[str, Any]] = {}

    # Compute total counts across all records
    total_all_resolved = 0
    total_all_complaints = 0

    # Group by borough
    for borough, group in df.groupby(borough_col):
        borough = str(borough)

        # Aggregate complaint counts
        resolved_count = int(group[resolved_col].sum())
        total_count = int(group[total_col].sum())

        # Sample size: number of unique locations/corners (row count as proxy)
        sample_size = len(group)

        # Completion rate
        completion_rate = (
            resolved_count / total_count if total_count > 0 else 0.0
        )

        # Binomial 95% confidence interval
        if total_count > 0:
            ci_lower, ci_upper = stats.binom.interval(
                confidence_level,
                total_count,
                completion_rate,
            )
            # Normalize to proportion
            ci_lower = ci_lower / total_count
            ci_upper = ci_upper / total_count
        else:
            ci_lower = ci_upper = 0.0

        # Power analysis: check if sample size sufficient for effect size
        # Minimum detectable difference from baseline (0.5) is effect_size
        # Using simple check: is sample size sufficient for two-tailed test?
        # For binomial, rough approximation: n >= (2 * z_alpha + z_beta)^2 / effect_size^2
        # For 80% power (z_beta ~= 0.84) and alpha=0.05 (z_alpha ~= 1.96):
        # n >= (2 * 1.96 + 0.84)^2 / effect_size^2 ~ 7.84^2 / effect_size^2
        min_sample_for_power = (
            max(10, int((7.84**2) / (effect_size**2)))
            if effect_size > 0
            else 30
        )
        has_power = sample_size >= min_sample_for_power

        # Store results
        borough_results[borough] = {
            "completion_rate": round(float(completion_rate), 4),
            "resolved_count": resolved_count,
            "total_count": total_count,
            "ci_lower": round(float(ci_lower), 4),
            "ci_upper": round(float(ci_upper), 4),
            "sample_size": sample_size,
            "has_power": has_power,
        }

        total_all_resolved += resolved_count
        total_all_complaints += total_count

    # Compute overall completion rate
    overall_completion_rate = (
        total_all_resolved / total_all_complaints
        if total_all_complaints > 0
        else 0.0
    )

    # Build comparison table from borough results
    rows = [
        {"borough": borough, **metrics}
        for borough, metrics in borough_results.items()
    ]
    comparison_table = pd.DataFrame(rows)

    return {
        **borough_results,
        "comparison_table": comparison_table,
        "overall_completion_rate": round(float(overall_completion_rate), 4),
    }
