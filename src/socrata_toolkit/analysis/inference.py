from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

@dataclass
class TTestResult:
    t_stat: float
    p_value: float
    significant: bool
    mean_diff: float
    conf_interval: tuple[float, float]

@dataclass
class ChiSquareResult:
    chi2: float
    p_value: float
    dof: int
    significant: bool
    contingency_table: pd.DataFrame

def run_t_test(group_a: pd.Series, group_b: pd.Series, alpha: float = 0.05) -> TTestResult:
    """Perform an independent two-sample t-test."""
    a = group_a.dropna()
    b = group_b.dropna()
    t_stat, p_val = stats.ttest_ind(a, b, equal_var=False)

    mean_diff = a.mean() - b.mean()
    # Simplified CI calculation
    se = np.sqrt(a.var()/len(a) + b.var()/len(b))
    ci = (mean_diff - 1.96 * se, mean_diff + 1.96 * se)

    return TTestResult(
        t_stat=float(t_stat),
        p_value=float(p_val),
        significant=bool(p_val < alpha),
        mean_diff=float(mean_diff),
        conf_interval=ci
    )

def run_chi_square(df: pd.DataFrame, col_x: str, col_y: str, alpha: float = 0.05) -> ChiSquareResult:
    """Perform a Chi-square test of independence for categorical variables."""
    contingency = pd.crosstab(df[col_x], df[col_y])
    chi2, p, dof, expected = stats.chi2_contingency(contingency)

    return ChiSquareResult(
        chi2=float(chi2),
        p_value=float(p),
        dof=int(dof),
        significant=bool(p < alpha),
        contingency_table=contingency
    )

def check_normality(series: pd.Series, alpha: float = 0.05) -> bool:
    """Test if a distribution is normal using the Shapiro-Wilk test."""
    if len(series) < 3: return False
    _, p = stats.shapiro(series.dropna())
    return p > alpha
