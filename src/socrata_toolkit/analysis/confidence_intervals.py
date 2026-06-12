"""
Confidence Interval Computations for NYC DOT Analysts

This module provides statistically rigorous uncertainty quantification methods:
- Wilson Score CI: for proportions and completion rates (accurate for small samples)
- Bootstrap CI: non-parametric for any statistic (mean, median, custom)
- T-test CI: for continuous metrics (assumes normality)

All methods return consistent dict structures with bounds, standard error, and metadata.
"""

from typing import Any, Callable, Dict, Optional, Union

import numpy as np
from scipy import stats


def wilson_score_confidence_interval(
    successes: int,
    total: int,
    confidence_level: float = 0.95,
) -> dict[str, Union[float, int]]:
    """
    Compute Wilson Score confidence interval for a proportion.

    Wilson Score is more accurate than normal approximation, especially for small samples
    (n < 1000). Used for completion rates, pass/fail metrics, and binary outcomes.

    Mathematical formulation:
    - p_hat = successes / total
    - z = norm.ppf((1 + confidence_level) / 2)
    - denominator = 1 + z^2 / total
    - center = (p_hat + z^2 / (2*total)) / denominator
    - margin = z * sqrt(p_hat * (1 - p_hat) / total + z^2 / (4*total^2)) / denominator

    Args:
        successes: Number of successes in sample
        total: Total sample size
        confidence_level: Confidence level (default 0.95 for 95% CI)

    Returns:
        Dict with keys:
        - point_estimate: p_hat (successes / total)
        - lower_bound: Lower confidence bound
        - upper_bound: Upper confidence bound
        - standard_error: Estimated SE
        - margin_of_error: Half-width of CI
        - confidence_level: Input confidence level
        - sample_size: Total sample size

    Raises:
        ValueError: If successes > total, total <= 0, or confidence_level not in (0, 1)

    Example:
        >>> result = wilson_score_confidence_interval(350, 400, confidence_level=0.95)
        >>> result['point_estimate']
        0.875
        >>> result['lower_bound'] < 0.875 < result['upper_bound']
        True
    """
    if total <= 0:
        raise ValueError("total must be > 0")
    if successes < 0 or successes > total:
        raise ValueError("successes must be in [0, total]")
    if not (0 < confidence_level < 1):
        raise ValueError("confidence_level must be in (0, 1)")

    p_hat = successes / total
    z = stats.norm.ppf((1 + confidence_level) / 2)

    # Wilson Score formula
    denominator = 1 + (z**2 / total)
    center = (p_hat + (z**2 / (2 * total))) / denominator
    margin_term = z * np.sqrt(
        (p_hat * (1 - p_hat) / total) + (z**2 / (4 * total**2))
    )
    margin = margin_term / denominator

    lower_bound = center - margin
    upper_bound = center + margin

    # Clamp bounds to [0, 1] for proportions
    lower_bound = max(0.0, lower_bound)
    upper_bound = min(1.0, upper_bound)

    # Standard error estimate (simplified, based on normal approximation near p_hat)
    se = np.sqrt(p_hat * (1 - p_hat) / total)

    return {
        "point_estimate": p_hat,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "standard_error": se,
        "margin_of_error": margin,
        "confidence_level": confidence_level,
        "sample_size": total,
    }


def bootstrap_confidence_interval(
    data: Union[np.ndarray, list],
    statistic_func: Callable[[Union[np.ndarray, list]], float],
    confidence_level: float = 0.95,
    n_bootstrap: int = 1000,
    random_state: Optional[int] = None,
) -> dict[str, Any]:
    """
    Compute bootstrap confidence interval for any statistic.

    Non-parametric method that works for any statistic (mean, median, custom function).
    Uses percentile method to construct CI from bootstrap samples.

    Algorithm:
    1. Compute point estimate on original data
    2. Generate n_bootstrap samples (with replacement)
    3. Compute statistic on each sample
    4. Extract lower and upper percentiles

    Args:
        data: Input data array or list
        statistic_func: Callable that computes statistic on data (e.g., np.mean, np.median)
        confidence_level: Confidence level (default 0.95 for 95% CI)
        n_bootstrap: Number of bootstrap samples (default 1000)
        random_state: Random seed for reproducibility

    Returns:
        Dict with keys:
        - point_estimate: Statistic computed on original data
        - lower_bound: Lower CI bound (percentile method)
        - upper_bound: Upper CI bound (percentile method)
        - standard_error: Standard deviation of bootstrap samples
        - confidence_level: Input confidence level
        - n_bootstrap: Number of bootstrap samples used
        - bootstrap_samples: Array of bootstrap statistics

    Raises:
        ValueError: If n_bootstrap <= 0 or confidence_level not in (0, 1)

    Example:
        >>> data = np.array([1.5, 2.3, 1.8, 2.5, 2.1])
        >>> result = bootstrap_confidence_interval(data, np.mean, confidence_level=0.95)
        >>> result['point_estimate']
        2.04
        >>> len(result['bootstrap_samples'])
        1000
    """
    if n_bootstrap <= 0:
        raise ValueError("n_bootstrap must be > 0")
    if not (0 < confidence_level < 1):
        raise ValueError("confidence_level must be in (0, 1)")

    rng = np.random.RandomState(random_state)
    data_array = np.asarray(data)
    n = len(data_array)

    # Compute point estimate on original data
    point_estimate = statistic_func(data_array)

    # Generate bootstrap samples and compute statistics
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        bootstrap_sample = rng.choice(data_array, size=n, replace=True)
        bootstrap_stat = statistic_func(bootstrap_sample)
        bootstrap_stats.append(bootstrap_stat)

    bootstrap_stats = np.array(bootstrap_stats)

    # Percentile method for CI bounds
    lower_percentile = (1 - confidence_level) / 2 * 100
    upper_percentile = (1 + confidence_level) / 2 * 100

    lower_bound = np.percentile(bootstrap_stats, lower_percentile)
    upper_bound = np.percentile(bootstrap_stats, upper_percentile)

    # Standard error from bootstrap distribution
    se = np.std(bootstrap_stats, ddof=1)

    return {
        "point_estimate": point_estimate,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "standard_error": se,
        "confidence_level": confidence_level,
        "n_bootstrap": n_bootstrap,
        "bootstrap_samples": bootstrap_stats,
    }


def mean_confidence_interval(
    data: Union[np.ndarray, list],
    confidence_level: float = 0.95,
) -> dict[str, Union[float, int]]:
    """
    Compute t-test confidence interval for mean of continuous data.

    Assumes data is approximately normally distributed. Uses Student's t-distribution
    to account for sample size and uncertainty in standard deviation.

    Mathematical formulation:
    - n = len(data)
    - mean = np.mean(data)
    - se = scipy.stats.sem(data)  (standard error of mean)
    - df = n - 1  (degrees of freedom)
    - t_crit = t.ppf((1 + confidence_level) / 2, df=df)
    - margin = t_crit * se

    Args:
        data: Input data array or list
        confidence_level: Confidence level (default 0.95 for 95% CI)

    Returns:
        Dict with keys:
        - point_estimate: Sample mean
        - lower_bound: Lower CI bound
        - upper_bound: Upper CI bound
        - standard_error: Standard error of mean
        - margin_of_error: Half-width of CI
        - confidence_level: Input confidence level
        - sample_size: Sample size
        - degrees_of_freedom: n - 1

    Raises:
        ValueError: If data has < 2 observations or confidence_level not in (0, 1)

    Example:
        >>> data = np.array([22.5, 23.1, 21.8, 22.9, 23.3])
        >>> result = mean_confidence_interval(data, confidence_level=0.95)
        >>> result['point_estimate']
        22.72
        >>> result['lower_bound'] < 22.72 < result['upper_bound']
        True
    """
    data_array = np.asarray(data)
    n = len(data_array)

    if n < 2:
        raise ValueError("data must have at least 2 observations")
    if not (0 < confidence_level < 1):
        raise ValueError("confidence_level must be in (0, 1)")

    mean = np.mean(data_array)
    se = stats.sem(data_array)  # Standard error of mean
    df = n - 1

    # t-critical value
    t_crit = stats.t.ppf((1 + confidence_level) / 2, df=df)
    margin = t_crit * se

    lower_bound = mean - margin
    upper_bound = mean + margin

    return {
        "point_estimate": mean,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "standard_error": se,
        "margin_of_error": margin,
        "confidence_level": confidence_level,
        "sample_size": n,
        "degrees_of_freedom": df,
    }
