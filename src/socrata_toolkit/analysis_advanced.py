"""Advanced data analysis utilities.

This module extends the basic profiling in `analysis.py` with:
- Outlier detection (IQR and Z-score methods)
- Correlation analysis with significance filtering
- Time series decomposition and trend detection
- Distribution classification (normal, skewed, uniform, etc.)
- Automated anomaly flagging across columns
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Outlier Detection
# ---------------------------------------------------------------------------

@dataclass
class OutlierReport:
    """Results from outlier detection on a single numeric column."""
    column: str
    method: str
    total_rows: int
    outlier_count: int
    outlier_pct: float
    lower_bound: float | None
    upper_bound: float | None
    outlier_indices: list[int]

def detect_outliers_iqr(
    df: pd.DataFrame,
    column: str,
    factor: float = 1.5,
) -> OutlierReport:
    """Detect outliers using the Inter-Quartile Range method.

    Values below Q1 - factor*IQR or above Q3 + factor*IQR are flagged.
    """
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    mask = (series < lower) | (series > upper)
    indices = series[mask].index.tolist()
    return OutlierReport(
        column=column,
        method="iqr",
        total_rows=len(series),
        outlier_count=len(indices),
        outlier_pct=round(len(indices) / max(len(series), 1) * 100, 2),
        lower_bound=lower,
        upper_bound=upper,
        outlier_indices=indices,
    )

def detect_outliers_zscore(
    df: pd.DataFrame,
    column: str,
    threshold: float = 3.0,
) -> OutlierReport:
    """Detect outliers using the Z-score method.

    Values with |z| > threshold are flagged.
    """
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    mean = float(series.mean())
    std = float(series.std())
    if std == 0:
        return OutlierReport(
            column=column, method="zscore", total_rows=len(series),
            outlier_count=0, outlier_pct=0.0, lower_bound=mean, upper_bound=mean,
            outlier_indices=[],
        )
    z = ((series - mean) / std).abs()
    mask = z > threshold
    indices = series[mask].index.tolist()
    return OutlierReport(
        column=column,
        method="zscore",
        total_rows=len(series),
        outlier_count=len(indices),
        outlier_pct=round(len(indices) / max(len(series), 1) * 100, 2),
        lower_bound=mean - threshold * std,
        upper_bound=mean + threshold * std,
        outlier_indices=indices,
    )

def detect_all_outliers(
    df: pd.DataFrame,
    method: str = "iqr",
    **kwargs: Any,
) -> list[OutlierReport]:
    """Run outlier detection on every numeric column in the DataFrame."""
    fn = detect_outliers_iqr if method == "iqr" else detect_outliers_zscore
    reports = []
    for col in df.select_dtypes(include="number").columns:
        reports.append(fn(df, col, **kwargs))
    return reports

# ---------------------------------------------------------------------------
# Correlation Analysis
# ---------------------------------------------------------------------------

@dataclass
class CorrelationResult:
    """Filtered correlation pairs above a significance threshold."""
    pairs: list[dict[str, Any]]
    method: str
    threshold: float

def correlation_analysis(
    df: pd.DataFrame,
    method: str = "pearson",
    threshold: float = 0.5,
) -> CorrelationResult:
    """Compute pairwise correlations and return pairs above the threshold.

    method: 'pearson', 'spearman', or 'kendall'
    threshold: minimum absolute correlation to include (0-1)
    """
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return CorrelationResult(pairs=[], method=method, threshold=threshold)

    corr = numeric.corr(method=method)
    pairs: list[dict[str, Any]] = []
    seen: set = set()
    for i, col_a in enumerate(corr.columns):
        for j, col_b in enumerate(corr.columns):
            if i >= j:
                continue
            val = float(corr.iloc[i, j])
            if abs(val) >= threshold and not math.isnan(val):
                key = tuple(sorted([col_a, col_b]))
                if key not in seen:
                    seen.add(key)
                    pairs.append({
                        "column_a": col_a,
                        "column_b": col_b,
                        "correlation": round(val, 4),
                        "strength": _strength_label(abs(val)),
                    })

    pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)
    return CorrelationResult(pairs=pairs, method=method, threshold=threshold)

def _strength_label(r: float) -> str:
    if r >= 0.9:
        return "very_strong"
    if r >= 0.7:
        return "strong"
    if r >= 0.5:
        return "moderate"
    if r >= 0.3:
        return "weak"
    return "negligible"

# ---------------------------------------------------------------------------
# Time Series Helpers
# ---------------------------------------------------------------------------

@dataclass
class TimeSeriesSummary:
    """Summary statistics for a time-indexed numeric series."""
    date_column: str
    value_column: str
    start: str
    end: str
    count: int
    trend_direction: str  # "increasing", "decreasing", "flat"
    trend_slope: float
    mean: float
    std: float
    monthly_counts: dict[str, int]

def time_series_summary(
    df: pd.DataFrame,
    date_column: str,
    value_column: str,
) -> TimeSeriesSummary:
    """Compute a lightweight time series summary with trend detection.

    Uses a simple linear regression on ordinal dates to estimate trend.
    """
    tmp = df[[date_column, value_column]].copy()
    tmp[date_column] = pd.to_datetime(tmp[date_column], errors="coerce")
    tmp = tmp.dropna()
    if tmp.empty:
        return TimeSeriesSummary(
            date_column=date_column, value_column=value_column,
            start="", end="", count=0, trend_direction="flat",
            trend_slope=0.0, mean=0.0, std=0.0, monthly_counts={},
        )

    tmp = tmp.sort_values(date_column).reset_index(drop=True)
    dates = tmp[date_column]
    values = pd.to_numeric(tmp[value_column], errors="coerce").fillna(0)

    # ordinal representation for linear fit
    ordinals = np.array([(d - dates.min()).days for d in dates], dtype=float)
    if ordinals.max() == 0:
        slope = 0.0
    else:
        # simple least-squares slope
        x_mean = ordinals.mean()
        y_mean = values.mean()
        num = ((ordinals - x_mean) * (values - y_mean)).sum()
        den = ((ordinals - x_mean) ** 2).sum()
        slope = float(num / den) if den != 0 else 0.0

    if slope > 0.001:
        direction = "increasing"
    elif slope < -0.001:
        direction = "decreasing"
    else:
        direction = "flat"

    # monthly aggregation
    monthly = tmp.set_index(date_column).resample("ME").size()
    monthly_counts = {str(k.date()): int(v) for k, v in monthly.items()}

    return TimeSeriesSummary(
        date_column=date_column,
        value_column=value_column,
        start=str(dates.min().date()),
        end=str(dates.max().date()),
        count=len(tmp),
        trend_direction=direction,
        trend_slope=round(slope, 6),
        mean=round(float(values.mean()), 4),
        std=round(float(values.std()), 4),
        monthly_counts=monthly_counts,
    )

# ---------------------------------------------------------------------------
# Distribution Classification
# ---------------------------------------------------------------------------

@dataclass
class DistributionInfo:
    """Classification of a numeric column's distribution shape."""
    column: str
    skewness: float
    kurtosis: float
    classification: str  # "normal", "right_skewed", "left_skewed", "heavy_tailed", "uniform", "sparse"
    unique_ratio: float
    sample_size: int

def classify_distribution(df: pd.DataFrame, column: str) -> DistributionInfo:
    """Classify the distribution shape of a numeric column."""
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    n = len(series)
    if n < 5:
        return DistributionInfo(
            column=column, skewness=0.0, kurtosis=0.0,
            classification="sparse", unique_ratio=0.0, sample_size=n,
        )

    skew = float(series.skew())
    kurt = float(series.kurtosis())  # excess kurtosis (Fisher)
    unique_ratio = series.nunique() / max(n, 1)

    if unique_ratio < 0.02:
        classification = "sparse"
    elif abs(skew) < 0.5 and abs(kurt) < 1.0:
        classification = "normal"
    elif skew > 1.0:
        classification = "right_skewed"
    elif skew < -1.0:
        classification = "left_skewed"
    elif kurt > 3.0:
        classification = "heavy_tailed"
    elif abs(kurt) < 0.5 and unique_ratio > 0.5:
        classification = "uniform"
    else:
        classification = "normal"

    return DistributionInfo(
        column=column,
        skewness=round(skew, 4),
        kurtosis=round(kurt, 4),
        classification=classification,
        unique_ratio=round(unique_ratio, 4),
        sample_size=n,
    )

def classify_all_distributions(df: pd.DataFrame) -> list[DistributionInfo]:
    """Classify distributions for all numeric columns."""
    return [classify_distribution(df, col) for col in df.select_dtypes(include="number").columns]

# ---------------------------------------------------------------------------
# Anomaly Flagging
# ---------------------------------------------------------------------------

@dataclass
class AnomalyReport:
    """Summary of anomalies detected across the entire DataFrame."""
    total_rows: int
    flagged_rows: int
    flagged_pct: float
    column_reports: list[OutlierReport]

def flag_anomalies(
    df: pd.DataFrame,
    method: str = "iqr",
    **kwargs: Any,
) -> tuple[pd.DataFrame, AnomalyReport]:
    """Add an `_anomaly` boolean column and return a summary report.

    A row is flagged as anomalous if it is an outlier in any numeric column.
    """
    reports = detect_all_outliers(df, method=method, **kwargs)
    flagged = set()
    for r in reports:
        flagged.update(r.outlier_indices)

    out = df.copy()
    out["_anomaly"] = out.index.isin(flagged)
    report = AnomalyReport(
        total_rows=len(df),
        flagged_rows=len(flagged),
        flagged_pct=round(len(flagged) / max(len(df), 1) * 100, 2),
        column_reports=reports,
    )
    return out, report
