from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class SidewalkKPI:
    defect_density: float
    throughput_velocity: float
    burn_variance: float
    first_pass_yield: float
    rework_factor: float


def compute_sidewalk_kpis(
    df: pd.DataFrame,
    defect_col: str = "violations",
    curb_miles_col: str = "curb_miles",
    built_linear_feet_col: str = "built_linear_feet",
    days_col: str = "days",
    actual_spend_col: str = "actual_spend",
    planned_spend_col: str = "planned_spend",
    first_pass_col: str = "first_pass",
    total_inspections_col: str = "total_inspections",
    rework_spend_col: str = "rework_spend",
) -> SidewalkKPI:
    dsum = float(df.get(defect_col, pd.Series([0])).fillna(0).sum())
    miles = float(df.get(curb_miles_col, pd.Series([1])).fillna(0).sum()) or 1.0
    defect_density = dsum / miles

    built = float(df.get(built_linear_feet_col, pd.Series([0])).fillna(0).sum())
    days = float(df.get(days_col, pd.Series([1])).fillna(0).sum()) or 1.0
    throughput_velocity = built / days

    actual = float(df.get(actual_spend_col, pd.Series([0])).fillna(0).sum())
    planned = float(df.get(planned_spend_col, pd.Series([1])).fillna(0).sum()) or 1.0
    burn_variance = actual - planned

    fp = float(df.get(first_pass_col, pd.Series([0])).fillna(0).sum())
    ti = float(df.get(total_inspections_col, pd.Series([1])).fillna(0).sum()) or 1.0
    first_pass_yield = fp / ti

    rework = float(df.get(rework_spend_col, pd.Series([0])).fillna(0).sum())
    rework_factor = rework / (actual or 1.0)

    return SidewalkKPI(defect_density, throughput_velocity, burn_variance, first_pass_yield, rework_factor)


def sql_templates() -> dict[str, str]:
    return {
        "defect_density": "SELECT SUM(violations)/NULLIF(SUM(curb_miles),0) AS defect_density FROM sidewalk_contracts;",
        "throughput_velocity": "SELECT SUM(built_linear_feet)/NULLIF(SUM(days),0) AS throughput_velocity FROM sidewalk_progress;",
        "burn_variance": "SELECT SUM(actual_spend)-SUM(planned_spend) AS burn_variance FROM sidewalk_budget;",
        "first_pass_yield": "SELECT SUM(first_pass)::float/NULLIF(SUM(total_inspections),0) AS first_pass_yield FROM inspections;",
        "rework_factor": "SELECT SUM(rework_spend)/NULLIF(SUM(actual_spend),0) AS rework_factor FROM contracts;",
    }


def python_templates() -> dict[str, str]:
    return {
        "poisson_defect_model": "from scipy.stats import poisson\n# lambda = defects/curb_miles\n",
        "topic_modeling": "from sklearn.decomposition import LatentDirichletAllocation\nfrom sklearn.feature_extraction.text import CountVectorizer\n",
        "timeseries": "import statsmodels.api as sm\n# sm.tsa.seasonal_decompose(series)\n",
        "chi_square": "from scipy.stats import chi2_contingency\n# chi2_contingency(contingency_table)\n",
        "bayesian_efficiency": "import pymc as pm\n# model contractor rework probability\n",
    }
